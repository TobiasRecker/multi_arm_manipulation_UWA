#!/usr/bin/env python3
"""Generate continuous-state goal chains with explicit arm/table constraints."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import multiprocessing


def arguments():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('parent',type=Path)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--legs',type=int,default=6)
    p.add_argument('--maxiter',type=int,default=20);p.add_argument('--table-regression',action='store_true')
    a=p.parse_args()
    if not 1<=a.legs<=20 or not 1<=a.maxiter<=100:p.error('legs in [1,20], maxiter in [1,100] required')
    return a


if __name__=='__main__' and os.environ.get('UWA_EPISODE_FROZEN')!='1':
    args=arguments();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);code=out/'code'
    if not code.exists():
        code.mkdir()
        for name in ('generate_teacher_episodes.py','teacher_episode_core.py','review_teacher_episodes.py'):
            shutil.copy2(Path(__file__).with_name(name),code/name)
    frozen=(args.parent/'frozen-source').resolve();env=dict(os.environ)
    env.update(UWA_EPISODE_FROZEN='1',UWA_TEACHER_FROZEN='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    env['UWA_EPISODE_BASE_TOOLS']=str(frozen/'tools')
    packages=['uwa_cell_motion','uwa_cell_calibration','uwa_cell_control','uwa_cell_description','uwa_cell_gazebo']
    env['PYTHONPATH']=os.pathsep.join([str(code),str(frozen/'tools')]+[str(frozen/p) for p in packages]+[env.get('PYTHONPATH','')])
    raise SystemExit(subprocess.call([sys.executable,str(code/Path(__file__).name),*sys.argv[1:]],env=env))

if os.environ.get('UWA_EPISODE_BASE_TOOLS'):sys.path.append(os.environ['UWA_EPISODE_BASE_TOOLS'])
import numpy as np
from scipy.spatial.transform import Rotation
from teacher_episode_core import EpisodeTeacher,screen
from generate_diverse_teacher_dataset import diverse_bindings
from generate_teacher_dataset import sha
from uwa_cell_motion.teacher_starts import state_check
from uwa_cell_motion.teacher_dataset import atomic_json,digest,transitions,validate_export
from uwa_cell_motion.two_arm_teacher import specification
from uwa_cell_motion.smooth_paths import sample_segment


def direct_task(name,start,goal):
    return specification(name,goal_m=goal[:3,3]-start[:3,3],
        goal_rotation_deg=np.rad2deg(Rotation.from_matrix(goal[:3,:3]@start[:3,:3].T).as_rotvec()))


def goal_proposals(initial,anchor,banks,seed):
    rng=np.random.default_rng(seed);goals=[]
    for bank in banks:
        goal=np.array(bank['initial_pose'])
        if np.linalg.norm(goal[:3,3]-initial[:3,3])>=.10:goals.append(goal)
    for _ in range(10):
        direction=rng.normal(size=3);direction[2]*=.5;direction/=np.linalg.norm(direction)
        goal=initial.copy();goal[:3,3]+=rng.uniform(.10,.24)*direction
        goal[:3,3]=np.clip(goal[:3,3],anchor[:3,3]+[-.28,-.28,0],anchor[:3,3]+[.30,.28,.24])
        rotation=rng.normal(size=3);rotation/=np.linalg.norm(rotation)
        goal[:3,:3]=Rotation.from_rotvec(rotation*np.deg2rad(rng.uniform(15,45))).as_matrix()@initial[:3,:3]
        if np.linalg.norm(goal[:3,3]-initial[:3,3])>=.09:goals.append(goal)
    return goals


def run_episode(config,manifest,out):
    os.nice(max(0,10-os.nice(0)));out=Path(out);path=out/'episodes'/f"{config['id']}.json"
    if path.exists():
        report=json.loads(path.read_text())
        if report['manifest_sha256']!=digest(manifest):raise ValueError('Episode binding changed')
        if report['status']!='RUNNING':return report
    else:report=dict(id=config['id'],group_id=config['id'],split='unassigned',manifest_sha256=digest(manifest),
        status='RUNNING',initial_pose=config['pose'],initial_state=config['state'],steps=[],attempts=[],executable=False)
    begun=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='uwa-teacher-episode-') as directory:
        p=EpisodeTeacher(directory,Path(manifest['bindings']['source_path']))
        if diverse_bindings(p,p.source)!=manifest['bindings']:raise ValueError('Base model/configuration changed')
        p.initial=np.array(config['pose']);p.start=dict(config['state'])
        if report['steps']:
            p.initial=np.array(report['steps'][-1]['end_pose']);p.start=dict(report['steps'][-1]['end_state'])
        report['start_check']=state_check(p,p.initial,p.start)
        if not report['start_check']['passed'] or p.arm_table_gaps(p.initial,p.start).min()<.004:
            report['status']='INVALID_INITIAL_STATE';atomic_json(path,report);return report
        for leg in range(len(report['steps']),manifest['legs']):
            preferred=('free','near','collision')[leg%3];candidates=[]
            for i,goal in enumerate(goal_proposals(p.initial,np.array(manifest['anchor_pose']),manifest['goal_banks'],config['seed']+leg*101)):
                task=direct_task(f"{config['id']}/goal-{leg}/proposal-{i}",p.initial,goal)
                check=screen(p,task);attempt=dict(goal_index=leg,proposal=i,task=task,screen=check)
                report['attempts'].append(attempt)
                if check['eligible']:
                    novelty=min(np.linalg.norm(goal[:3,3]-np.array(s['initial_pose'])[:3,3]) for s in report['steps']) if report['steps'] else 1.
                    radius=float(np.linalg.norm(goal[:3,3]-np.array(manifest['anchor_pose'])[:3,3]))
                    candidates.append((check['category']!=preferred,-novelty,-radius,attempt,goal))
            candidates.sort(key=lambda x:x[:3]);accepted=False;atomic_json(path,report)
            for _,_,_,attempt,goal in candidates[:3]:
                task=attempt['task'];before_pose=p.initial.copy();before_state=dict(p.start)
                step=dict(goal_index=leg,task=task,initial_pose=before_pose.tolist(),initial_state=before_state,
                          reference_screen=attempt['screen'],requested_category=preferred)
                try:
                    opt=p.optimize(task,count=81,maxiter=manifest['maxiter']);step['optimization']=opt
                    if opt.get('controls') is None:raise ValueError('No teacher controls')
                    trajectory=p.trajectory(task,np.array(opt['controls']));step['trajectory']=trajectory
                    step['validation']=p.validate(trajectory,dt=.005)
                    if not step['validation']['passed']:raise ValueError('Trajectory rejected by full validation')
                    records=transitions(p.initial,trajectory);step['export_validation']=validate_export(p,records)
                    export_table=min(float(p.arm_table_gaps(pose,dict(p.start,**dict(zip(p.names,q)))).min()) for pose,q in
                        zip(np.concatenate([records['object_pose'],records['object_pose_next'][-1:]]),np.concatenate([records['q'],records['q_next'][-1:]])))
                    step['export_validation']['min_arm_table_gap_m']=export_table
                    if not step['export_validation']['passed'] or export_table<.003-1e-8:raise ValueError('Export grid rejected')
                    end_pose,end_state,_=p.sample(trajectory,trajectory['duration_s'])
                    rest=max(float(np.max(abs(sample_segment(trajectory['segment'],[0,trajectory['duration_s']],d)))) for d in (1,2,3))
                    if rest>1e-8:raise ValueError('Goal switch is not at shared rest')
                    step.update(end_pose=end_pose.tolist(),end_state=end_state,endpoint_derivative_max=rest,
                                status='VALIDATED',duration_s=trajectory['duration_s'])
                    records['goal_terminal']=records.pop('terminal')
                    dest=out/'transitions'/f"{config['id']}-goal-{leg}.npz"
                    with dest.with_suffix('.tmp').open('wb') as stream:np.savez_compressed(stream,**records)
                    dest.with_suffix('.tmp').replace(dest);step.update(records_path=str(dest.relative_to(out)),records_sha256=sha(dest))
                    report['steps'].append(step);attempt['teacher_status']='VALIDATED'
                    # The only state advance: use the checked interpolant endpoint.
                    p.initial=end_pose.copy();p.start=dict(end_state);accepted=True;atomic_json(path,report)
                    print(config['id'],'GOAL',leg+1,'VALIDATED',attempt['screen']['category'],flush=True);break
                except (ValueError,np.linalg.LinAlgError) as error:
                    attempt['teacher_status']='REJECTED';attempt['teacher_reason']=str(error)
                    attempt['teacher_diagnostics']=step
                    p.initial=before_pose;p.start=before_state;atomic_json(path,report)
            if not accepted:
                report['status']='NO_NEXT_VALIDATED_GOAL';break
        else:report['status']='COMPLETE'
    report['processing_s']=time.monotonic()-begun;report['duration_s']=sum(s['duration_s'] for s in report['steps'])
    report['transitions']=100*len(report['steps']);atomic_json(path,report);return report


def main():
    args=arguments();out=args.output_dir.resolve()
    for name in ('episodes','transitions'):(out/name).mkdir(exist_ok=True)
    parent=args.parent.resolve();base=json.loads((parent/'manifest.json').read_text())
    banks=[json.loads(p.read_text()) for p in sorted((parent/'starts').glob('*.json'))]
    banks=[b for b in banks if b['selected']]
    configs=[dict(id='episode-000',seed=20261117,pose=base['anchor_pose'],state=base['anchor_state']),
             dict(id='episode-001',seed=20261201,pose=next(b for b in banks if b['family']['id']=='east_high')['initial_pose'],
                  state=next(b for b in banks if b['family']['id']=='east_high')['selected']['state'])]
    manifest=dict(schema_version=1,bindings=base['bindings'],parent_manifest_sha256=digest(base),parent_path=str(parent),
        code_sha256={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},configs=configs,legs=args.legs,maxiter=args.maxiter,
        goal_banks=banks,anchor_pose=base['anchor_pose'],executable=False,
        scope='Offline stop-at-goal episodes; continuous state, fixed grasps, no resets/branch switching; unassigned grouping pool')
    path=out/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=manifest:raise ValueError('Episode manifest changed')
    else:atomic_json(path,manifest)
    if args.table_regression:
        record=json.loads((parent.parents[1]/'teacher-collision-mining-20261117/recheck01/teachers/north-ik3-random-011.json').read_text())
        with tempfile.TemporaryDirectory(prefix='uwa-table-regression-') as directory:
            p=EpisodeTeacher(directory,Path(base['bindings']['source_path']));p.initial=np.array(record['initial_pose']);p.start=dict(record['initial_state'])
            task=record['case']['task'];result=dict(reference=p.inspect(task,count=81))
            result['optimization']=p.optimize(task,count=81,maxiter=args.maxiter)
            if result['optimization'].get('controls') is not None:
                result['trajectory']=p.trajectory(task,np.array(result['optimization']['controls']))
                result['validation']=p.validate(result['trajectory'],dt=.005)
            atomic_json(out/'table-regression.json',result)
            print('TABLE REGRESSION',result.get('validation',{}).get('passed'),flush=True)
        return
    with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
        results=list(pool.map(run_episode,configs,[manifest]*len(configs),[str(out)]*len(configs)))
    summary=dict(episodes=[dict(id=r['id'],status=r['status'],goals=len(r['steps']),duration_s=r.get('duration_s',0),transitions=r.get('transitions',0)) for r in results])
    atomic_json(out/'summary.json',summary);print('SUMMARY',json.dumps(summary),flush=True)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Screen direct SE(3) connections before spending teacher optimization time."""
import argparse
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor,as_completed
from collections import Counter
import json
import multiprocessing
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


def arguments():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('parent',type=Path)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--teachers',type=int,default=2)
    p.add_argument('--random-targets',type=int,default=0,help='Additional deterministic broad orientation targets per start IK state')
    p.add_argument('--mode',choices=('direct','local-reference'),default='direct')
    p.add_argument('--candidate-record',type=Path,help='Re-screen one retained candidate, preserving the original record')
    a=p.parse_args()
    if not 0<=a.teachers<=10:p.error('teachers must be in [0,10]')
    if not 0<=a.random_targets<=128:p.error('random-targets must be in [0,128]')
    return a


if __name__=='__main__' and os.environ.get('UWA_MINING_FROZEN')!='1':
    args=arguments();root=(args.parent/'frozen-source').resolve();env=dict(os.environ)
    env.update(UWA_MINING_FROZEN='1',UWA_TEACHER_FROZEN='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    env['UWA_MINING_TOOLS']=str(root/'tools')
    packages=['uwa_cell_motion','uwa_cell_calibration','uwa_cell_control','uwa_cell_description','uwa_cell_gazebo']
    env['PYTHONPATH']=os.pathsep.join([str(root/'tools')]+[str(root/p) for p in packages]+[env.get('PYTHONPATH','')])
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],env=env))

if os.environ.get('UWA_MINING_TOOLS'):sys.path.insert(0,os.environ['UWA_MINING_TOOLS'])
import numpy as np
from scipy.spatial.transform import Rotation
from generate_diverse_teacher_dataset import diverse_bindings
from generate_teacher_dataset import sha
from uwa_cell_motion.teacher_dataset import atomic_json,digest
from uwa_cell_motion.teacher_starts import state_check
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher,specification,pose_at
from uwa_cell_motion.smooth_paths import progress,sample_segment


def checked_progress(value):
    if not np.isfinite(value) or value < -1e-12 or value > 1+1e-12:
        raise ValueError('Progress outside [0,1] beyond rounding tolerance')
    return float(np.clip(value,0,1))


class MiningTeacher(TwoArmTeacher):
    def sample(self,trajectory,t):
        # Long time laws can yield 1+2e-16 near the end. Only round-off is
        # clamped; geometry, margins and large range errors remain unchanged.
        segment=trajectory['segment'];s=checked_progress(float(progress(segment['time_law'],t)[0]))
        pose=pose_at(self.initial,trajectory['task'],s,trajectory['controls'])
        state=dict(self.start,**dict(zip(self.names,sample_segment(segment,t))))
        return pose,state,s


def direct_task(name,start,goal):
    return specification(name,goal_m=(goal[:3,3]-start[:3,3]).tolist(),
        goal_rotation_deg=np.rad2deg(Rotation.from_matrix(goal[:3,:3]@start[:3,:3].T).as_rotvec()).tolist())


def contact_categories(pairs):
    categories=set()
    def arm(name):
        return next((a for a in ('right_front','right_rear','left_front','left_rear') if name.startswith(a+'_')),None)
    for a,b in pairs:
        aa,bb=arm(a),arm(b)
        if aa and bb:categories.add('active_arm_arm' if {aa,bb}=={'right_front','right_rear'} else 'self_collision' if aa==bb else 'other_arm_arm')
        elif 'offline_carried_carton' in (a,b):categories.add('object_arm' if aa or bb else 'object_environment')
        else:categories.add('robot_environment')
    return sorted(categories)


def screen_status(collision_count,arm_gap):
    if collision_count:return 'FCL_COLLISION'
    if arm_gap<0:return 'ARM_HULL_OVERLAP'
    if arm_gap<.02:return 'MARGIN_ONLY'
    return 'NO_FCL_OR_ARM_MARGIN_HIT'


def contact_witness(p,pose,state,path):
    """Capture native FCL link names; this binding cannot marshal Contact values."""
    p.update_object(pose);sys.stdout.flush();sys.stderr.flush()
    saved=[os.dup(fd) for fd in (1,2)]
    try:
        with path.open('w') as stream:
            os.dup2(stream.fileno(),1);os.dup2(stream.fileno(),2)
            clear,_=p.collision.check(state,contacts=True)
    finally:
        for fd,old in zip((1,2),saved):os.dup2(old,fd);os.close(old)
    raw=path.read_text();pairs=sorted(set(re.findall(r"contacts between '([^']+)' .*? and '([^']+)'",raw)))
    return dict(fcl_clear=bool(clear),contact_pairs=[list(x) for x in pairs],
                contact_categories=contact_categories(pairs),native_log=path.name)


def screen_one(p,case,out,count=61):
    begun=time.monotonic();r=dict(case=case,status='IK_FAILED',samples=0)
    initial=np.array(case['initial_pose']);p.initial=initial;p.start=dict(case['initial_state']);state=dict(p.start)
    rows=[]
    try:
        for s in np.linspace(0,1,count):
            pose=pose_at(initial,case['task'],float(s),np.zeros((6,6)));state=p.solve(pose,state)
            clear=p.full_check(pose,state);pairs=p.distances(pose,state)
            rows.append(dict(s=float(s),pose=pose,state=dict(state),clear=clear,
                             gap=min(v['clearance_m'] for v in pairs)))
        end=state_check(p,rows[-1]['pose'],rows[-1]['state']);r['endpoint_check']=end
        if not end['passed']:r['status']='ENDPOINT_INVALID'
        else:
            collisions=[i for i,row in enumerate(rows) if not row['clear']]
            r.update(status=screen_status(len(collisions),min(x['gap'] for x in rows)),
                fcl_collision_samples=len(collisions),min_arm_gap_m=min(x['gap'] for x in rows),
                goal_state=rows[-1]['state'],witnesses=[])
            if collisions:
                indices=sorted({collisions[0],collisions[len(collisions)//2],collisions[-1],min(collisions,key=lambda i:rows[i]['gap'])})
                for i in indices:
                    row=rows[i];path=out/'contacts'/f"{case['id']}-{i}.log"
                    witness=contact_witness(p,row['pose'],row['state'],path)
                    witness.update(s=row['s'],pose=row['pose'].tolist(),state=row['state'],arm_gap_m=row['gap'])
                    r['witnesses'].append(witness)
                r['contact_categories']=sorted({c for w in r['witnesses'] for c in w['contact_categories']})
    except (ValueError,np.linalg.LinAlgError) as error:r['reason']=str(error)
    r['samples']=len(rows);r['screening_s']=time.monotonic()-begun
    return r


def screen_group(cases,manifest,out):
    os.nice(max(0,10-os.nice(0)));out=Path(out);results=[]
    with tempfile.TemporaryDirectory(prefix='uwa-collision-mining-') as directory:
        p=MiningTeacher(directory,Path(manifest['bindings']['source_path']))
        if diverse_bindings(p,p.source)!=manifest['bindings']:raise ValueError('Frozen model/configuration changed')
        for case in cases:
            path=out/'screening'/f"{case['id']}.json"
            if path.exists():
                r=json.loads(path.read_text())
                if r['manifest_sha256']!=digest(manifest):raise ValueError('Screening binding mismatch')
            else:
                p.initial=np.array(case['initial_pose']);p.start=dict(case['initial_state'])
                start=state_check(p,p.initial,p.start)
                r=screen_one(p,case,out) if start['passed'] else dict(case=case,status='START_INVALID',screening_s=0)
                r['start_check']=start;r['manifest_sha256']=digest(manifest);atomic_json(path,r)
            results.append(r)
    return results


def solve_candidate(p,record,out):
    begun=time.monotonic();case=record['case'];p.initial=np.array(case['initial_pose']);p.start=dict(case['initial_state'])
    r=dict(case=case,screening_path=f"screening/{case['id']}.json",status='NO_VALIDATED_TEACHER',executable=False,
           initial_pose=p.initial.tolist(),initial_state=dict(p.start),reference_contact_categories=record['contact_categories'])
    try:
        r['reference_check']=p.inspect(case['task'],count=121)
        if not r['reference_check']['complete']:raise ValueError('Dense reference continuation failed')
        r['optimization']=p.optimize(case['task'],count=121,maxiter=30)
        controls=r['optimization'].get('controls')
        if controls is None:raise ValueError('No controls returned')
        r['trajectory']=p.trajectory(case['task'],np.array(controls));r['validation']=p.validate(r['trajectory'],dt=.005)
        if r['validation']['passed']:r['status']='VALIDATED_TEACHER'
    except (ValueError,np.linalg.LinAlgError) as error:r['reason']=str(error)
    r['processing_s']=time.monotonic()-begun;atomic_json(out/'teachers'/f"{case['id']}.json",r)
    return r


def main():
    args=arguments();parent=args.parent.resolve();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ('screening','contacts','teachers'):(out/name).mkdir(exist_ok=True)
    source=json.loads((parent/'manifest.json').read_text())
    banks=[json.loads(p.read_text()) for p in sorted((parent/'starts').glob('*.json'))]
    valid=[b for b in banks if b['selected']];cases=[]
    rng=np.random.default_rng(20261117)
    for start in valid:
        candidates=sorted((c for c in start['combined_candidates'] if c['check']['passed']),key=lambda c:c['check']['pair_gap_m'])[:3]
        for candidate in candidates:
            for goal in valid:
                if start['family']['id']==goal['family']['id']:continue
                name=f"{start['family']['id']}-ik{candidate['id']}-to-{goal['family']['id']}"
                cases.append(dict(id=name,start_family=start['family']['id'],goal_family=goal['family']['id'],
                    initial_pose=start['initial_pose'],initial_state=candidate['state'],
                    task=direct_task(name,np.array(start['initial_pose']),np.array(goal['initial_pose']))))
            for i in range(args.random_targets):
                initial=np.array(start['initial_pose']);goal=initial.copy()
                direction=rng.normal(0,1,3)
                if i%2==0:direction=np.eye(3)[i%3]*(1 if i%4==0 else -1)+.12*direction
                direction/=np.linalg.norm(direction);angle=np.deg2rad(rng.uniform(70,175))
                goal[:3,:3]=Rotation.from_rotvec(direction*angle).as_matrix()@initial[:3,:3]
                goal[:3,3]+=rng.uniform([-.16,-.16,-.04],[.16,.16,.16])
                name=f"{start['family']['id']}-ik{candidate['id']}-random-{i:03d}"
                cases.append(dict(id=name,start_family=start['family']['id'],goal_family=f'random-{i}',
                    initial_pose=start['initial_pose'],initial_state=candidate['state'],
                    task=direct_task(name,initial,goal)))
    if args.mode=='local-reference':
        start=next(b for b in valid if b['family']['id']=='east_high')
        base=next(c for c in source['cases'] if c['id']=='east_high-v0');cases=[]
        for i,factor in enumerate((2.6,3.,3.4,3.8)):
            task=deepcopy(base['task']);name=f'east_high-contact-probe-{i}'
            task['name']=name;task['rotation_vector_deg']=[factor*v for v in task['rotation_vector_deg']]
            cases.append(dict(id=name,start_family='east_high',goal_family='local_reference_probe',
                initial_pose=start['initial_pose'],initial_state=start['selected']['state'],task=task,
                parent_case_id=base['id'],rotation_excursion_factor=factor,reference_type='soft_reference_tracking'))
    if args.candidate_record:cases=[json.loads(args.candidate_record.read_text())['case']]
    manifest=dict(schema_version=1,artifact_type='collision_first_screening_pool',executable=False,mode=args.mode,
        parent_path=str(parent),parent_manifest_sha256=digest(source),bindings=source['bindings'],
        mining_code_sha256=sha(Path(__file__)),start_bank_sha256={p.name:sha(p) for p in sorted((parent/'starts').glob('*.json'))},
        candidate_record_sha256=sha(args.candidate_record) if args.candidate_record else None,
        cases=cases,screening_samples=61,teacher_budget=args.teachers,random_targets_per_start=args.random_targets,
        assumptions=[('Direct position interpolation and shortest SO(3) interpolation, no excursions' if args.mode=='direct'
                      else 'Soft reference tracking with enlarged requested intermediate rotation; not a blocked direct start-goal benchmark'),
            'Goal pose fixed; goal arm state obtained by continuation from selected start branch',
            'Coarse screening detects collisions, does not certify free paths',
            'Unassigned research pool; shared endpoints/IK siblings must be grouped before train/test split',
            'Contact labels from sampled native FCL witnesses, not exhaustive contact census'])
    path=out/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=manifest:raise ValueError('Manifest changed; use a new output directory')
    else:atomic_json(path,manifest)
    begun=time.monotonic();records=[]
    groups=[[c for c in cases if c['start_family']==b['family']['id']] for b in valid]
    groups=[g for g in groups if g]
    with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(screen_group,g,manifest,str(out)) for g in groups]
        for future in as_completed(futures):
            records.extend(future.result());print('SCREENED',len(records),'/',len(cases),dict(Counter(r['status'] for r in records)),flush=True)
    wall=time.monotonic()-begun
    summary=dict(candidates=len(cases),statuses=dict(Counter(r['status'] for r in records)),screening_wall_s=wall,
        summed_candidate_screening_s=sum(r['screening_s'] for r in records),
        contact_categories=dict(Counter(c for r in records for c in r.get('contact_categories',[]))),
        screening_candidates_per_s=len(cases)/wall,manifest_sha256=digest(manifest))
    atomic_json(out/'summary.json',summary)
    candidates=[r for r in records if r['status']=='FCL_COLLISION']
    order=['active_arm_arm','other_arm_arm','object_arm','object_environment','robot_environment','self_collision']
    candidates.sort(key=lambda r:(min((order.index(c) for c in r['contact_categories'] if c in order),default=99),r['fcl_collision_samples'],r['case']['id']))
    selected=[];families=set()
    for r in candidates:
        if args.mode=='direct' and r['case']['start_family'] in families:continue
        selected.append(r);families.add(r['case']['start_family'])
        if len(selected)>=args.teachers:break
    if args.teachers==0:selected=[]
    atomic_json(out/'teacher-selection.json',[r['case']['id'] for r in selected])
    teachers=[]
    if selected:
        with tempfile.TemporaryDirectory(prefix='uwa-mined-teacher-') as directory:
            p=MiningTeacher(directory,Path(source['bindings']['source_path']))
            for r in selected:
                path=out/'teachers'/f"{r['case']['id']}.json"
                result=json.loads(path.read_text()) if path.exists() else solve_candidate(p,r,out)
                teachers.append(result);print('TEACHER',r['case']['id'],result['status'],flush=True)
    summary['teachers_attempted']=len(teachers);summary['teachers_validated']=sum(r['status']=='VALIDATED_TEACHER' for r in teachers)
    atomic_json(out/'summary.json',summary);print('RESULT',json.dumps(summary),flush=True)


if __name__=='__main__':main()

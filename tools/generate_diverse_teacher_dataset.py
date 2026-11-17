#!/usr/bin/env python3
"""Freeze Python sources, discover diverse starts and generate checked BC paths."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def freeze_and_run():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--output-dir',type=Path,required=True)
    args,_=parser.parse_known_args();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    frozen=out/'frozen-source';root=Path(__file__).resolve().parents[1]
    packages=['uwa_cell_motion','uwa_cell_calibration','uwa_cell_control','uwa_cell_description','uwa_cell_gazebo']
    if not frozen.exists():
        staging=out/'frozen-source.tmp';staging.mkdir(exist_ok=False)
        for package in packages:
            for source in (root/package/package).rglob('*.py'):
                dest=staging/source.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        for name in ['generate_teacher_dataset.py','plan_two_arm_teacher.py','review_teacher_dataset.py',
                     'generate_diverse_teacher_dataset.py','review_diverse_teacher_dataset.py','preview_two_arm_teacher.html']:
            dest=staging/'tools'/name;dest.parent.mkdir(exist_ok=True);shutil.copy2(root/'tools'/name,dest)
        staging.rename(frozen)
    env=dict(os.environ);env['UWA_TEACHER_FROZEN']='1'
    env['OPENBLAS_NUM_THREADS']=env['OMP_NUM_THREADS']='1'
    env['PYTHONPATH']=os.pathsep.join([str(frozen/p) for p in packages]+[env.get('PYTHONPATH','')])
    return subprocess.call([sys.executable,str(frozen/'tools'/Path(__file__).name),*sys.argv[1:]],env=env)


if __name__=='__main__' and os.environ.get('UWA_TEACHER_FROZEN')!='1':
    raise SystemExit(freeze_and_run())

import numpy as np
from generate_teacher_dataset import bindings,sha,load_completed,summarize,save_case
from uwa_cell_motion.teacher_dataset import SCHEMA,atomic_json,digest,transitions,validate_export
from uwa_cell_motion.teacher_starts import start_families,discover_start,state_check,coverage
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher


def diverse_bindings(p,source):
    result=bindings(p,source);root=Path(__file__).resolve().parents[1]
    result['frozen_python_sha256']={str(f.relative_to(root)):sha(f) for f in sorted(root.rglob('*.py'))}
    result['configuration']=p.problem.cfg
    return result


def run_family(family,manifest,out,bank_only):
    os.nice(max(0,10-os.nice(0)));out=Path(out);completed=[]
    with tempfile.TemporaryDirectory(prefix='uwa-diverse-start-') as directory:
        p=TwoArmTeacher(directory,Path(manifest['bindings']['source_path']))
        if diverse_bindings(p,p.source)!=manifest['bindings']:raise ValueError('Frozen model/configuration changed')
        path=out/'starts'/f"{family['id']}.json"
        if path.exists():
            bank=json.loads(path.read_text())
            if bank['manifest_sha256']!=digest(manifest):raise ValueError('Start bank binding mismatch')
        else:
            bank=discover_start(p,family,seed=20261117+manifest['families'].index(family))
            bank['manifest_sha256']=digest(manifest);atomic_json(path,bank)
        if bank_only:return dict(family=family['id'],bank=bank,completed=[])
        for case in (c for c in manifest['cases'] if c['family']==family['id']):
            result_path=out/'cases'/f"{case['id']}.json"
            if result_path.exists():
                completed.append(json.loads(result_path.read_text()));continue
            begun=time.monotonic();r=dict(case=case,manifest_sha256=digest(manifest),executable=False,
                                        status='START_INVALID',stage='initialization',start_bank_path=str(path.relative_to(out)))
            if not bank['selected']:
                r['reason']='No acceptable coupled initial IK candidate';completed.append(save_case(out,r,begun));continue
            p.initial=np.array(bank['initial_pose']);p.start=dict(bank['selected']['state'])
            r.update(initial_pose=p.initial.tolist(),initial_state=dict(p.start),start_candidate=bank['selected']['id'])
            try:
                r['start_check']=state_check(p,p.initial,p.start)
                if not r['start_check']['passed']:raise ValueError('Start failed revalidation')
                r['stage']='reference';r['reference_check']=p.inspect(case['task'],count=121)
                if not r['reference_check']['complete']:
                    r['status']='REFERENCE_IK_FAILED';completed.append(save_case(out,r,begun));continue
                r['stage']='optimization';r['status']='NO_VALIDATED_TRAJECTORY'
                r['optimization']=p.optimize(case['task'],count=121,maxiter=manifest['maxiter'])
                controls=r['optimization'].get('controls')
                if controls is None:completed.append(save_case(out,r,begun));continue
                r['stage']='trajectory_validation';r['trajectory']=p.trajectory(case['task'],np.array(controls))
                r['validation']=p.validate(r['trajectory'],dt=.005)
                if not r['validation']['passed']:completed.append(save_case(out,r,begun));continue
                r['stage']='export_validation';records=transitions(p.initial,r['trajectory'])
                r['export_validation']=validate_export(p,records)
                if not r['export_validation']['passed']:completed.append(save_case(out,r,begun));continue
                npz=out/'cases'/f"{case['id']}.npz"
                with npz.with_suffix('.npz.tmp').open('wb') as stream:np.savez_compressed(stream,**records)
                npz.with_suffix('.npz.tmp').replace(npz)
                r.update(status='VALIDATED',stage='complete',transitions=100,records_path=str(npz.relative_to(out)),records_sha256=sha(npz))
            except (ValueError,np.linalg.LinAlgError) as error:
                r['reason']=str(error)
                if r['stage']!='initialization':r['status']='NO_VALIDATED_TRAJECTORY'
            completed.append(save_case(out,r,begun))
    return dict(family=family['id'],bank=bank,completed=completed)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path)
    parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--workers',type=int,choices=(1,2),default=2)
    parser.add_argument('--maxiter',type=int,default=30);parser.add_argument('--bank-only',action='store_true')
    args=parser.parse_args()
    if not 1<=args.maxiter<=200:parser.error('maxiter must be in [1,200]')
    out=args.output_dir.resolve()
    for name in ('starts','cases'):(out/name).mkdir(parents=True,exist_ok=True)
    families=start_families();cases=[]
    for family in families:
        for i,item in enumerate(family['tasks']):
            cases.append(dict(id=family['id']+f'-v{i}',family=family['id'],split=family['split'],variant=i,**item))
    with tempfile.TemporaryDirectory(prefix='uwa-diverse-manifest-') as directory:
        p=TwoArmTeacher(directory,args.source)
        manifest=dict(schema_version=2,artifact_type='diverse_initial_state_bc_pilot',executable=False,maxiter=args.maxiter,
            bindings=diverse_bindings(p,args.source),families=families,cases=cases,bc_schema=SCHEMA,validation_dt_s=.005,
            anchor_pose=p.initial.tolist(),anchor_state=p.start,arms=list(p.arms),joint_names=p.names,
            dimensions_m=p.dimensions.tolist(),grasp_sides=p.grasp_sides,
            grasp_offsets={a:v.tolist() for a,v in p.offsets.items()},tcp_offsets={a:v.tolist() for a,v in p.tcp_offsets.items()},
            assumptions=['Hypothetical independently initialized rigid grasps; no approach/IK-branch-change proof',
                'Fixed bases/object/grasp/parked arms; no hardware or network training',
                'Start families and two goals each fixed before IK/trajectory solving; failures retained',
                'Minimum-clearance valid IK pair selected from bounded multi-start search; no completeness claim',
                'Separate pilot splits, not automatically mergeable with earlier near-anchor dataset'])
    path=out/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=manifest:raise ValueError('Manifest changed; use a new output directory')
    else:atomic_json(path,manifest)
    done=load_completed(out,manifest);banks={};summarize(out,manifest,done)
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(run_family,f,manifest,str(out),args.bank_only) for f in families]
        for future in as_completed(futures):
            result=future.result();banks[result['family']]=result['bank']
            done.update((r['case']['id'],r) for r in result['completed']);summary=summarize(out,manifest,done)
            report=coverage(list(banks.values()),np.array(manifest['anchor_pose']));atomic_json(out/'start-coverage.json',report)
            print('FAMILY',result['family'],result['bank']['status'],'IK PAIRS',result['bank']['valid_candidates'],
                  'CASES',[(r['case']['id'],r['status']) for r in result['completed']],
                  'PROGRESS',len(banks),'/',len(families),'ACCEPTED',summary['accepted'],flush=True)
    print('COVERAGE',json.dumps(report),'SUMMARY',json.dumps({k:summary[k] for k in ('planned','completed','accepted','repaired','transitions')}),flush=True)


if __name__=='__main__':main()

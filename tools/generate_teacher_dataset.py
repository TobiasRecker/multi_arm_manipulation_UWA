#!/usr/bin/env python3
"""Generate/resume a fixed 32-task offline pilot with family-level data splits."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time

import numpy as np

from uwa_cell_motion.teacher_dataset import (SCHEMA,atomic_json,digest,families,
    set_initial,transitions,validate_export)
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bindings(p,source):
    root=Path(__file__).resolve().parents[1]
    files=[Path(__file__).resolve()]
    # Bind the computational path, not unrelated live-hardware/GUI modules
    # which may legitimately change in this shared workspace during a batch.
    sources={
        'uwa_cell_motion':['teacher_dataset','two_arm_teacher','object_transport',
                           'smooth_paths','carton_paths','planning','geometry','common'],
        'uwa_cell_calibration':['model'],
        'uwa_cell_control':['parallel_scan','scan_separation','view_geometry','parking'],
        'uwa_cell_description':['configuration','scene_assets'],
        'uwa_cell_gazebo':['configuration','charuco','charuco_views'],
    }
    files+=[root/package/package/(name+'.py') for package,names in sources.items() for name in names]
    return dict(source_path=str(source.resolve()),source_sha256=sha(source),
                code_sha256={str(f):sha(f) for f in sorted(files)},
                model_signature=p.problem.signature,mesh_sha256=p.problem.spheres.geometry.assets,
                object_mesh_sha256=p.saved['object_mesh_sha256'])


def run_case(case,manifest,out):
    os.nice(max(0,10-os.nice(0)))
    begun=time.monotonic();out=Path(out);result=dict(case=case,manifest_sha256=digest(manifest),
        executable=False,status='START_INVALID',stage='initialization')
    with tempfile.TemporaryDirectory(prefix='uwa-bc-case-') as directory:
        p=TwoArmTeacher(directory,Path(manifest['bindings']['source_path']))
        if bindings(p,Path(p.source))!=manifest['bindings']:
            raise ValueError('Source/code/model bindings changed during batch')
        try:
            result['start_check']=set_initial(p,case,p.initial.copy(),dict(p.start))
            result['initial_pose']=p.initial.tolist();result['initial_state']=p.start
            if not result['start_check']['passed']:
                result['reason']='Perturbed initial state did not pass';return save_case(out,result,begun)
            result['stage']='reference';result['reference_check']=p.inspect(case['task'],count=121)
            if not result['reference_check']['complete']:
                result['status']='REFERENCE_IK_FAILED';return save_case(out,result,begun)
            result['stage']='optimization'
            result['optimization']=p.optimize(case['task'],count=121,maxiter=manifest['maxiter'])
            controls=result['optimization'].get('controls')
            result['status']='NO_VALIDATED_TRAJECTORY'
            if controls is None:return save_case(out,result,begun)
            result['stage']='trajectory_validation'
            trajectory=p.trajectory(case['task'],np.array(controls));result['trajectory']=trajectory
            result['validation']=p.validate(trajectory,dt=manifest['validation_dt_s'])
            if not result['validation']['passed']:return save_case(out,result,begun)
            result['stage']='export_validation';records=transitions(p.initial,trajectory)
            result['export_validation']=validate_export(p,records)
            if not result['export_validation']['passed']:return save_case(out,result,begun)
            npz=out/'cases'/f"{case['id']}.npz"
            with npz.with_suffix('.npz.tmp').open('wb') as stream:np.savez_compressed(stream,**records)
            npz.with_suffix('.npz.tmp').replace(npz)
            result.update(status='VALIDATED',stage='complete',transitions=len(records['actions']),
                          records_path=str(npz.relative_to(out)),records_sha256=sha(npz))
        except (ValueError,np.linalg.LinAlgError) as error:
            if result['stage']!='initialization':result['status']='NO_VALIDATED_TRAJECTORY'
            result['reason']=str(error)
        return save_case(out,result,begun)


def save_case(out,result,begun):
    result['processing_s']=time.monotonic()-begun
    atomic_json(out/'cases'/f"{result['case']['id']}.json",result)
    return result


def load_completed(out,manifest):
    completed={}
    for case in manifest['cases']:
        path=out/'cases'/f"{case['id']}.json"
        if not path.exists():continue
        result=json.loads(path.read_text())
        if result['manifest_sha256']!=digest(manifest) or result['case']!=case:
            raise ValueError(f'Resume metadata mismatch: {path}')
        if result['status']=='VALIDATED':
            if not result['validation']['passed'] or not result['export_validation']['passed']:
                raise ValueError('Accepted case without both checks')
            if sha(out/result['records_path'])!=result['records_sha256']:
                raise ValueError('Export modified since acceptance')
        completed[case['id']]=result
    return completed


def summarize(out,manifest,completed):
    groups=[]
    for category in ('translation3d','rotation3d','mixed6d'):
        for split in ('train','validation','test'):
            planned=[c for c in manifest['cases'] if c['category']==category and c['split']==split]
            done=[completed[c['id']] for c in planned if c['id'] in completed]
            valid=[r for r in done if r['status']=='VALIDATED']
            groups.append(dict(category=category,split=split,planned=len(planned),completed=len(done),
                accepted=len(valid),repaired=sum(not r['reference_check']['passed'] for r in valid),
                transitions=sum(r['transitions'] for r in valid)))
    results=[completed[c['id']] for c in manifest['cases'] if c['id'] in completed]
    summary=dict(manifest_sha256=digest(manifest),planned=len(manifest['cases']),completed=len(results),
        accepted=sum(r['status']=='VALIDATED' for r in results),
        repaired=sum(r['status']=='VALIDATED' and not r['reference_check']['passed'] for r in results),
        transitions=sum(r.get('transitions',0) for r in results),groups=groups,
        cases=[dict(id=r['case']['id'],category=r['case']['category'],split=r['case']['split'],
                    status=r['status'],result_path=f"cases/{r['case']['id']}.json") for r in results])
    atomic_json(out/'summary.json',summary)
    for split in ('train','validation','test'):
        accepted=[r for r in results if r['status']=='VALIDATED' and r['case']['split']==split]
        atomic_json(out/f'{split}.json',dict(schema=SCHEMA,manifest_sha256=digest(manifest),split=split,
            cases=[dict(id=r['case']['id'],family=r['case']['family'],category=r['case']['category'],
                        path=r['records_path'],sha256=r['records_sha256'],transitions=r['transitions']) for r in accepted]))
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=20261117)
    parser.add_argument('--maxiter',type=int,default=30)
    parser.add_argument('--workers',type=int,choices=(1,2),default=2)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    if not 1<=args.maxiter<=200:parser.error('maxiter must be in [1,200]')
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);(out/'cases').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='uwa-bc-manifest-') as directory:
        p=TwoArmTeacher(directory,args.source)
        manifest=dict(schema_version=1,artifact_type='offline_geometric_bc_pilot',executable=False,
            seed=args.seed,maxiter=args.maxiter,validation_dt_s=.005,bindings=bindings(p,args.source),
            cases=families(args.seed),bc_schema=SCHEMA,
            arms=list(p.arms),joint_names=p.names,dimensions_m=p.dimensions.tolist(),
            grasp_sides=p.grasp_sides,grasp_offsets={a:v.tolist() for a,v in p.offsets.items()},
            tcp_offsets={a:v.tolist() for a,v in p.tcp_offsets.items()},
            anchor_pose=p.initial.tolist(),anchor_state=p.start,
            assumptions=['Fixed bases, object and grasp transforms; left arms parked',
                'Hypothetical rigid open-finger grasp, no contact physics or pickup proof',
                'Discrete model validation; no hardware execution or safety guarantee',
                'Family split fixed before solving; rejected cases retained without resampling',
                'Small pilot, not a qualified training corpus or generalization measurement'])
    path=out/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=manifest:raise ValueError('Immutable manifest mismatch; use a new output directory')
    else:atomic_json(path,manifest)
    completed=load_completed(out,manifest);summary=summarize(out,manifest,completed)
    print('MANIFEST',digest(manifest),'RESUMED',len(completed),'PLANNED',len(manifest['cases']),flush=True)
    if args.prepare_only:return
    # Spawn fresh native model contexts; never fork MoveIt/FCL thread state.
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(run_case,c,manifest,str(out)):c for c in manifest['cases'] if c['id'] not in completed}
        for future in as_completed(futures):
            result=future.result();completed[result['case']['id']]=result
            summary=summarize(out,manifest,completed)
            print(result['case']['id'],result['status'],f"{result['processing_s']:.1f}s",
                  'PROGRESS',summary['completed'],'/',summary['planned'],'ACCEPTED',summary['accepted'],flush=True)
    print('FINISHED',json.dumps({k:summary[k] for k in ('planned','completed','accepted','repaired','transitions')}),flush=True)


if __name__=='__main__':main()

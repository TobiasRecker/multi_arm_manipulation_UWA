#!/usr/bin/env python3
"""Build and validate offline two-arm examples for a future BC teacher."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

import numpy as np
from scipy.spatial.transform import Rotation
from uwa_cell_motion.common import ROBOT_IDS,dump
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher,specification,pose_at


def examples():
    return [
        specification('Transfer + yaw',goal_m=[.10,.03,.01],goal_rotation_deg=[0,0,35]),
        specification('Long-axis rotation -100 deg',[.15,0,0],[0,-100,0]),
        specification('Long-axis rotation +70 deg',[.15,0,0],[0,70,0]),
        specification('IK limit example',[0,0,0],[0,0,100]),
    ]


def preview(p,trajectory):
    frames=[]
    for t in np.linspace(0,trajectory['duration_s'],241):
        pose,state,s=p.sample(trajectory,float(t));pairs=p.distances(pose,state)
        reference=pose_at(p.initial,trajectory['task'],s,np.zeros((6,6)))
        rv=Rotation.from_matrix(pose[:3,:3]@p.initial[:3,:3].T).as_rotvec()
        frames.append(dict(time_s=float(t),s=s,object_origin=p.object_origin(pose).tolist(),
            reference_origin=p.object_origin(reference).tolist(),centre=pose[:3,3].tolist(),
            reference_centre=reference[:3,3].tolist(),rotation_vector_deg=np.rad2deg(rv).tolist(),
            world={a:v.round(6).tolist() for a,v in p.problem.spheres.world(state).items()},
            fcl_clear=p.full_check(pose,state),object_box_gap_mm=1000*float(p.environment_gaps(pose).min()),
            object_arm_gap_mm=1000*float(p.object_arm_gaps(pose,state).min()),
            gaps=[dict(arms=v['arms'],gap_mm=1000*v['clearance_m']) for v in pairs]))
    return frames


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Existing smoothed four-side result.json')
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--tasks',type=Path,help='Optional JSON array using the documented task schema')
    parser.add_argument('--candidate-report',type=Path,help='Reuse candidate controls by case index; always revalidate')
    parser.add_argument('--dt',type=float,default=.005)
    parser.add_argument('--maxiter',type=int,default=50)
    args=parser.parse_args()
    if not 0<args.dt<=.01 or not 1<=args.maxiter<=200:parser.error('dt in (0,.01], maxiter in [1,200] required')
    tasks=json.loads(args.tasks.read_text()) if args.tasks else examples()
    # Normalize and validate external task records before creating outputs.
    tasks=[specification(t['name'],t['excursion_m'],t['rotation_vector_deg'],t['goal_m'],t['goal_rotation_vector_deg']) for t in tasks]
    candidate=json.loads(args.candidate_report.read_text()) if args.candidate_report else None
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='uwa-two-arm-teacher-') as directory:
        p=TwoArmTeacher(directory,args.source);report=dict(schema_version=1,executable=False,
            artifact_type='offline_two_arm_teacher_examples',source_path=str(p.source),source_sha256=p.source_sha256,
            model_signature=p.problem.signature,mesh_sha256=p.problem.spheres.geometry.assets,
            object_mesh_sha256=p.saved['object_mesh_sha256'],arms=list(p.arms),stationary_arms=[a for a in ROBOT_IDS if a not in p.arms],
            grasp_sides=p.grasp_sides,dimensions_m=p.dimensions.tolist(),initial_pose=p.initial.tolist(),
            initial_state=p.start,tcp_offsets={a:v.tolist() for a,v in p.tcp_offsets.items()},
            grasp_offsets={a:v.tolist() for a,v in p.offsets.items()},elevation_m=p.elevation,
            limits=dict(arm_clearance_m=.02,object_surrogate_clearance_m=.003,optimization_buffer_m=.001,
                        scaled_arm_sigma_floor=.05,closure_position_m=1e-6,closure_angle_rad=1e-5),
            assumptions=['Hypothetical fixed short-side grasps with open-finger model; no contact/load proof',
                         'Fixed bases and stationary other arms; no second part or tool task yet',
                         'No certified stopping envelope, no real robot commands',
                         'Local bounded optimizer; rejection is not an infeasibility proof'],cases=[])
        import uwa_cell_motion.two_arm_teacher as teacher
        root=Path(__file__).resolve().parents[1]
        files=[Path(teacher.__file__).resolve(),root/'uwa_cell_motion/uwa_cell_motion/object_transport.py',
               root/'uwa_cell_motion/uwa_cell_motion/smooth_paths.py',root/'uwa_cell_motion/uwa_cell_motion/geometry.py',
               root/'uwa_cell_motion/uwa_cell_motion/carton_paths.py',
               root/'uwa_cell_calibration/uwa_cell_calibration/model.py',Path(__file__).resolve()]
        report['code_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        sets=[]
        for index,task in enumerate(tasks):
            case=dict(id=index,task=task,variants=[]);report['cases'].append(case)
            case['reference_check']=p.inspect(task,count=241);dump(out/'result.json',report)
            print('CASE',index,task['name'],'reference',case['reference_check'].get('passed'),flush=True)
            if not case['reference_check']['complete']:
                case['status']='REFERENCE_IK_FAILED';dump(out/'result.json',report);continue
            begun=time.monotonic()
            if candidate:
                old=candidate['cases'][index]
                if old['task']!=task:raise ValueError('Candidate task mismatch')
                optimization=dict(old['optimization'],reused_candidate=True)
                controls=np.array(optimization['controls']);limits=optimization['limits']
                if controls.shape!=(6,6) or not np.isfinite(controls).all() or np.max(abs(controls[:,:3]))>limits['translation_m']+1e-9 or np.max(abs(controls[:,3:]))>np.deg2rad(limits['rotation_deg'])+1e-9:
                    raise ValueError('Invalid candidate controls')
            else:
                optimization=p.optimize(task,count=121,maxiter=args.maxiter)
            case['optimization']=optimization;dump(out/'result.json',report)
            for label,controls in [('Reference',np.zeros((6,6))),('Teacher',optimization.get('controls'))]:
                if controls is None:continue
                controls=np.asarray(controls,float)
                if label=='Teacher' and np.max(abs(controls))<1e-12:
                    case['reference_retained']=True;continue
                variant=dict(label=label);case['variants'].append(variant)
                try:
                    trajectory=p.trajectory(task,controls);variant['trajectory']=trajectory
                    variant['validation']=p.validate(trajectory,dt=args.dt)
                except (ValueError,np.linalg.LinAlgError) as error:
                    variant['validation']=dict(passed=False,reason=str(error));dump(out/'result.json',report);continue
                dump(out/'result.json',report)
                print(label,'duration',trajectory['duration_s'],'PASS',variant['validation']['passed'],
                      'gap',variant['validation']['min_pair_gap_m'],'FCL failures',sum(not v.get('fcl_clear',True) for v in variant['validation']['failures']),flush=True)
                sets.append(dict(case_id=index,label=task['name']+' / '+label,variant=label,
                    duration_s=trajectory['duration_s'],validation=variant['validation'],frames=preview(p,trajectory)))
            valid=[v for v in case['variants'] if v['validation']['passed']]
            case['accepted_variant']=valid[-1]['label'] if valid else None
            case['status']='VALIDATED_EXAMPLE' if valid else 'NO_VALIDATED_EXAMPLE'
            case['total_processing_s']=time.monotonic()-begun;dump(out/'result.json',report)
        report['summary']=dict(cases=len(report['cases']),accepted=sum(c.get('accepted_variant') is not None for c in report['cases']),
            repaired=sum(c.get('accepted_variant')=='Teacher' and not c['reference_check']['passed'] for c in report['cases']))
        boxes=[]
        for _,T,half in p.environment_boxes:
            corners=np.array(list(__import__('itertools').product(*[[-h,h] for h in half])))
            boxes.append((corners@T[:3,:3].T+T[:3,3]).tolist())
        data=dict(arms=list(ROBOT_IDS),active_arms=list(p.arms),boxes=boxes,triangles=p.triangles.tolist(),
                  radii={a:v.tolist() for a,v in p.problem.spheres.radii.items()},sets=sets,
                  summary=[dict(name=c['task']['name'],status=c['status'],accepted=c.get('accepted_variant'),
                                reason=c.get('reference_check',{}).get('reason')) for c in report['cases']])
        template=Path(__file__).with_name('preview_two_arm_teacher.html').read_text()
        (out/'viewer.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
        dump(out/'result.json',report)
        print('RESULT',json.dumps(report['summary']),'VIEWER',out/'viewer.html',flush=True)


if __name__=='__main__':main()

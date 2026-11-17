#!/usr/bin/env python3
"""Run offline stages 1–3 for four fixed top-down avocado-carton corner goals."""
import argparse
import json
from pathlib import Path
import tempfile
import time

import yaml

from uwa_cell_description.configuration import default_layout_path
from uwa_cell_motion.common import ROBOT_IDS, config, dump
from uwa_cell_motion.carton_paths import (CartonProblem, corner_targets, diagnose_parallel,
                                        independent_paths, pose_goal, upright_start)
from uwa_cell_motion.candidates import enumerate_candidates
from uwa_cell_motion.selection import select_goals
from uwa_cell_motion.carton_sides import side_targets


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True);parser.add_argument('--layout')
    parser.add_argument('--config')
    parser.add_argument('--grasp-pattern',choices=['corners','sides'],default='corners')
    parser.add_argument('--endpoint-policy',choices=['stop_reserve','static_margin'],default='stop_reserve',
                        help='Offline geometry policy; stopping reserves remain separate diagnostics')
    args=parser.parse_args()
    out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=False)
    path=Path(args.layout or default_layout_path()).resolve();layout=yaml.safe_load(path.read_text())
    profile=layout.get('calibration_profile')
    if 'base_layout' in layout:layout=yaml.safe_load((path.parent/layout['base_layout']).read_text())
    if profile:layout['calibration_profile']=str((path.parent/profile).resolve())
    (out/'layout.yaml').write_text(yaml.safe_dump(layout,sort_keys=False))
    cfg=config(args.config);(out/'motion.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
    with tempfile.TemporaryDirectory(prefix='uwa-carton-paths-') as d:
        p=CartonProblem(d,cfg,out/'layout.yaml',endpoint_policy=args.endpoint_policy);(out/'model.urdf').write_text(p.description)
        start=upright_start(p.layout);targets=(side_targets if args.grasp_pattern=='sides' else corner_targets)(p)
        if not p.collision.check(start)[0]:raise ValueError('Upright start collides in this model')
        task=dict(start=start,targets=targets,grasp_pattern=args.grasp_pattern,object_pose=p.carton['T_world_object'].tolist(),
                  dimensions_m=p.carton['manifest']['dimensions_m'],
                  object_mesh_sha256=p.carton['manifest']['files'][p.carton['manifest']['solid_mesh']],
                  entry_depth_m=.015,pregrasp_m=.12,
                  tcp_definition='Nominal gripper-base +Z 145 mm; not calibrated grasp TCP',
                  contact_status='Open gripper geometry only; no closing, holding or lift validation')
        dump(out/'task.json',task)
        request=dict(start=start,goals={arm:pose_goal(arm,t['tool0_target']) for arm,t in targets.items()})
        dump(out/'request.json',request)
        candidates=enumerate_candidates(p,request,seeds=96,budget_s=120,max_per_arm=12,
                                        max_combinations=16,max_checks=4096)
        candidates['offline_endpoint_policy']=args.endpoint_policy
        dump(out/'candidates.json',candidates)
        selection=select_goals(p,candidates,budget_s=60,max_checks=20736,shortlist_size=6)
        selection['offline_endpoint_policy']=args.endpoint_policy
        dump(out/'selection.json',selection)
        compatible_ids={cid for c in selection['evaluated_combinations'] for cid in c['candidate_ids']}
        begun=time.monotonic()
        paths,failures=independent_paths(p,start,candidates['candidates'],targets,compatible_ids,
                                        max_paths=12,progress=lambda arm,msg:print(arm,msg,flush=True))
        byid={path['candidate_id']:path for ps in paths.values() for path in ps};compatible=[]
        for c in selection['evaluated_combinations']:
            if all(cid in byid for cid in c['candidate_ids']):
                compatible.append(dict(c,path_ids=[byid[cid]['id'] for cid in c['candidate_ids']],
                                       joint_arc_length_sum_rad=sum(byid[cid]['joint_arc_length_rad'] for cid in c['candidate_ids'])))
        compatible.sort(key=lambda c:(c['joint_arc_length_sum_rad'],c['id']))
        result=dict(schema_version=1,artifact_type='offline_carton_primitive_paths',executable=False,
                    status='INDEPENDENT_PATHS_FOUND' if compatible else 'NO_COMPATIBLE_PATH_SET_FOUND',
                    task=task,model_signature=p.signature,mesh_sha256=p.spheres.geometry.assets,
                    configuration=cfg,paths=paths,rejected_attempts=failures,combinations=compatible,
                    offline_endpoint_policy=args.endpoint_policy,
                    planning_elapsed_s=time.monotonic()-begun,
                    assumptions=['Fixed bases and open grippers; one immutable target pose per arm',
                                 'Quintic joint primitives and Cartesian-line IK spline; not native UR MoveJ/MoveL execution',
                                 'Independent paths check self, tables, carton and fixed bases, not other moving arms',
                                 'Dense sampled checks, not continuous swept-volume certification',
                                 'C2 primitives stop with zero velocity and acceleration at joins',
                                 'Sampled timing estimates are for model preview, not certified actuator bounds',
                                 'Parallel start diagnostic does not resolve timing conflicts',
                                 'Reaching open-gripper poses is not a contact or load-bearing grasp proof'])
        if compatible:
            chosen=compatible[0];result['recommended_id']=chosen['id']
            chosen_paths={arm:byid[cid] for arm,cid in zip(ROBOT_IDS,chosen['candidate_ids'])}
            result['parallel_diagnostic']=diagnose_parallel(p,start,chosen_paths)
        dump(out/'paths.json',result)
        print(json.dumps(dict(status=result['status'],paths={r:len(ps) for r,ps in paths.items()},
                              compatible_combinations=len(compatible),recommended=result.get('recommended_id'))))
    if not compatible:raise SystemExit(2)


if __name__=='__main__':main()

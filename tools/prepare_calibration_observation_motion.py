#!/usr/bin/env python3
"""Offline serial PTP plans, bound to the verified active N100 model.

Host-specific asset paths may differ. Require identical canonical collision
geometry, asset digests, operating config and planner source bytes before
binding the exported plans to the target host. Its ordinary executor still
rebuilds the hardware model and revalidates deterministic timing before motion.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import yaml

from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.common import joint_names, dump, ROBOT_IDS
from uwa_cell_control.parallel_scan import collision_signature


def prepare(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    remote=json.loads(args.context.read_text());snapshot=json.loads(args.snapshot.read_text())
    cap=args.command_cap or remote['config']['command_velocity_limit_rad_s']
    if not 0 < cap <= remote['config']['command_velocity_limit_rad_s']:
        raise ValueError('Command cap must be positive and within the active hardware profile')
    if snapshot.get('execution_mode')!='hardware':raise ValueError('Actual hardware snapshot required')
    if any(r.get('status',{}).get('robot_mode')!=7 for r in snapshot['source_records'].values()):
        raise ValueError('All drives must report actual RUNNING joints; powered-off zeros are not a start')
    for name,digest in remote['modules'].items():
        if hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()!=digest:
            raise ValueError('Planner source differs from N100: '+name)
    repo=Path(__file__).resolve().parents[1]
    problem=HardwareProblem(output/'model',remote['config'],repo/'config/hardware_inventory.yaml')
    tree=ET.fromstring(problem.description)
    for mesh in tree.iter('mesh'):
        file=Path(mesh.get('filename').removeprefix('file://'))
        mesh.set('filename','sha256:'+hashlib.sha256(file.read_bytes()).hexdigest())
    canonical=collision_signature(ET.tostring(tree,encoding='unicode'))
    if canonical!=remote['canonical_collision_signature']:
        raise ValueError('Canonical collision geometry differs from active N100 model')
    if sorted(problem.spheres.geometry.assets.values())!=sorted(remote['mesh_sha256'].values()):
        raise ValueError('Collision asset digests differ from N100')
    source=yaml.safe_load(args.targets.read_text());state=dict(snapshot['start']);segments=[]
    for number,rid in enumerate(ROBOT_IDS,1):
        q=[]
        for n,value in zip(joint_names(rid),source['targets_rad'][rid]):
            lo,hi=problem.collision.bounds[n]
            variants=[value+k*2*np.pi for k in range(-2,3) if lo<=value+k*2*np.pi<=hi]
            wanted=value if rid=='right_front' and n.endswith('shoulder_pan_joint') else min(variants,key=lambda v:abs(v-state[n]))
            q.append(wanted)
        request=dict(schema_version=1,start=state,goals={rid:q})
        plan=problem.plan(request,'rrtconnect',seed=2300+number)
        if not plan['success']:
            dump(output/f'{number:02d}-{rid}-failed.json',plan)
            raise ValueError(rid+': '+plan.get('error','planning failed'))
        # Uniform time scaling preserves the already validated geometric path,
        # reduces every commanded velocity/acceleration and changes no guard
        # configuration. This cap needs its explicit task-specific user consent.
        scale=cap/remote['config']['command_velocity_limit_rad_s']
        if scale != 1.:
            for point in plan['trajectory']['points']:
                point['time']/=scale
                point['velocities']=[v*scale for v in point['velocities']]
                point['accelerations']=[a*scale*scale for a in point['accelerations']]
            plan['trajectory']['duration_s']/=scale
            plan['metrics']['planned_duration_s']=plan['trajectory']['duration_s']
        plan['compiled_command_limit_rad_s']=cap
        plan['offline_compiler_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        # Only path strings / hashes expressing identical verified geometry
        # are rebound. All waypoints, limits, timing and checked states stay exact.
        plan.update(inventory=remote['inventory'],hardware_binding=remote['hardware_binding'],
            model_signature=remote['model_signature'],mesh_sha256=remote['mesh_sha256'],
            execution_mode='hardware',layout_path=None,
            portable_binding=dict(canonical_collision_signature=canonical,
                n100_context_sha256=hashlib.sha256(args.context.read_bytes()).hexdigest(),
                exact_planner_modules=remote['modules'],geometry_changed=False,
                user_authorization='23Nov2026: sequential observation poses after completed N100 transition'))
        file=output/f'{number:02d}-{rid}.json';dump(file,plan)
        segments.append(dict(arm=rid,plan=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),duration_s=plan['trajectory']['duration_s'],
            target_rad=q,coordination=plan['coordination'],metrics=plan['metrics']))
        state=dict(state,**dict(zip(joint_names(rid),q)))
        print(json.dumps(segments[-1]),flush=True)
    dump(output/'sequence.json',dict(kind='serial_four_arm_observation_sequence',segments=segments,
        start=snapshot['start'],target=state,command_velocity_limit_rad_s=cap,
        total_duration_s=sum(s['duration_s'] for s in segments),
        current_start_must_be_rechecked=True,robot_commands_sent=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('snapshot','context','targets','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--command-cap',type=float,help='Task-specific lower cap, only with explicit user authorization')
    prepare(p.parse_args())

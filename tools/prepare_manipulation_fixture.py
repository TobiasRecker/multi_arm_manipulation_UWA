#!/usr/bin/env python3
"""Prepare a fresh virtual pregrasp fixture from a verified completed plan.

No running world is changed. This is an initial-state experiment, never a reset
or motion command. It cannot qualify a Home approach or hardware execution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import yaml
from uwa_cell_control.parallel_scan import collision_signature
from uwa_cell_description.configuration import load_layout,joint_names
from uwa_cell_tasks.core import ARMS,verify,seal,write_json
from uwa_cell_tasks.scene import verify_scene,prepare_scene


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene',required=True,type=Path);p.add_argument('--run',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    source=verify_scene(args.scene);plan=verify(json.loads((args.run/'plan.json').read_text()))
    if plan['scene_sha256']!=source['sha256']:p.error('Plan belongs to a different scene')
    names=[n for arm in ARMS for n in joint_names(arm)]
    if plan['request']['joint_names']!=names:p.error('Exactly the two right arm targets required')
    layout=yaml.safe_load((args.scene/'model/layout.yaml').read_text())
    layout.pop('calibration_profile',None)  # The saved model layout is already calibrated.
    target=dict(zip(names,plan['request']['target']))
    for arm in ARMS:
        layout['robots'][arm]['initial_positions']=[target[n] for n in joint_names(arm)]
        layout['robots'][arm]['tools']['gripper_initial_position']=0.
    args.output.mkdir(parents=True,exist_ok=False);file=args.output/'layout.yaml'
    file.write_text(yaml.safe_dump(layout,sort_keys=False));loaded=load_layout(file)
    fixture=prepare_scene(loaded,source['cfg'],args.output/'validation_scene')
    before=collision_signature((args.scene/'robot.urdf').read_text())
    after=collision_signature((args.output/'validation_scene/robot.urdf').read_text())
    if before!=after:raise ValueError('Fixture changed collision geometry/kinematics; inspect retained files')
    report=seal(dict(kind='fresh_virtual_pregrasp_initial_state',source_scene_sha256=source['sha256'],
        source_plan_sha256=plan['sha256'],layout_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        collision_signature=after,validation_scene_sha256=fixture['sha256'],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        existing_world_changed=False,hardware_commanded=False,
        interpretation='Isolated contact experiment; no Home-approach or hardware qualification'))
    write_json(args.output/'fixture.json',report);print(file.resolve())


if __name__=='__main__':main()

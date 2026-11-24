#!/usr/bin/env python3
"""Small file-only parity replay against existing Python FK / MoveIt bindings."""
import argparse
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
from geometry_msgs.msg import Pose
from moveit.core.collision_detection import CollisionRequest, CollisionResult
from moveit.core.planning_scene import PlanningScene
from moveit.core.robot_model import RobotModel
from moveit.core.robot_state import RobotState
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import Plane
from uwa_cell_control.view_geometry import VisibilityModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--states', required=True, type=Path)
    parser.add_argument('--replay', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    resolve = lambda field: (args.config.parent/Path(config[field])).resolve()
    description = resolve('urdf_path').read_text()
    root = ET.fromstring(description)
    model = RobotModel(str(resolve('urdf_path')), str(resolve('srdf_path')))
    state = RobotState(model)
    scene = PlanningScene(model)
    floor = CollisionObject()
    floor.header.frame_id, floor.id = 'world', 'calibration_floor'
    floor.planes = [Plane(coef=[0., 0., 1., .003])]
    pose = Pose()
    pose.orientation.w = 1.
    floor.plane_poses = [pose]
    floor.operation = CollisionObject.ADD
    scene.apply_collision_object(floor)
    anchored = {'world'}
    for _ in root.findall('joint'):
        for joint in root.findall('joint'):
            if joint.get('type') == 'fixed' and joint.find('parent').get('link') in anchored:
                anchored.add(joint.find('child').get('link'))
    for name in anchored:
        scene.allowed_collision_matrix.set_entry(name, 'calibration_floor', True)
    fk = VisibilityModel(description, config['arms'])
    zeros = {j.get('name'): 0. for j in root.findall('joint')
             if j.get('type') in ('revolute', 'continuous', 'prismatic') and j.find('mimic') is None}
    names = {name for arm in config['arms'].values() for name in arm['joint_names']}
    states = json.loads(args.states.read_text())
    if isinstance(states, dict):
        states = states['states']
    native = json.loads(subprocess.check_output([args.replay, str(args.config), str(args.states)], text=True))
    rows = []
    for positions, native_row in zip(states, native['states']):
        fixed_model = dict(zeros, **{j: q for j, q in positions.items() if j in names})
        state.joint_positions = fixed_model
        state.update()
        result = CollisionResult()
        scene.check_collision(CollisionRequest(), result, state)
        native_fcl = any(row['kind'] == 'fcl_contact' for row in native_row['collisions'])
        if native_fcl != result.collision:
            raise AssertionError('C++ / existing MoveIt binding FCL decisions differ')
        frames = fk.frames(fixed_model)
        world = {arm: np.array([frames[s['link']][:3, :3]@s['centre']+frames[s['link']][:3, 3]
                               for s in spheres]) for arm, spheres in config['spheres'].items()}
        errors = []
        for pair in native_row['pairs']:
            a, b = pair['arms']
            ra = np.array([s['radius'] for s in config['spheres'][a]])
            rb = np.array([s['radius'] for s in config['spheres'][b]])
            gap = float((np.linalg.norm(world[a][:, None]-world[b][None], axis=2)-ra[:, None]-rb[None]).min())
            errors.append(abs(gap-pair['distance_m']))
        if max(errors, default=0.) > 1e-10:
            raise AssertionError('C++ / existing Python FK sphere clearance differs')
        rows.append(dict(clear=native_row['clear'], fcl_collision=native_fcl,
                         max_sphere_gap_error_m=max(errors, default=0.), duration_ms=native_row['duration_ms']))
    report = dict(model_signature=config['model_signature'], source_states=str(args.states),
                  sample_count=len(rows), sphere_count={a: len(s) for a, s in config['spheres'].items()},
                  native_load_ms=native['load_ms'], results=rows, passed=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

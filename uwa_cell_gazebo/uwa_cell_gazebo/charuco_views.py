"""Offline URDF FK/IK for reproducible initial views of the tabletop boards.

Only computes starting configurations; this is not a collision-free motion planner.
"""
import argparse
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import yaml

from .charuco import transform
from .configuration import ROBOT_IDS, default_layout_path, joint_names, load_layout, render_description


class Chain:
    def __init__(self, description, ancestor, child):
        root = ET.fromstring(description)
        parents = {joint.find('child').get('link'): joint for joint in root.findall('joint')}
        self.joints = []
        while child != ancestor:
            joint = parents[child]
            origin = joint.find('origin')
            xyz = np.fromstring(origin.get('xyz', '0 0 0'), sep=' ') if origin is not None else np.zeros(3)
            rpy = np.fromstring(origin.get('rpy', '0 0 0'), sep=' ') if origin is not None else np.zeros(3)
            axis = joint.find('axis')
            axis = np.fromstring(axis.get('xyz'), sep=' ') if axis is not None else np.array([1., 0, 0])
            self.joints.append((joint.get('name'), joint.get('type'), transform(xyz, rpy), axis))
            child = joint.find('parent').get('link')
        self.joints.reverse()

    def forward(self, positions):
        result = np.eye(4)
        for name, kind, origin, axis in self.joints:
            result = result @ origin
            if kind in ('revolute', 'continuous'):
                rotation = np.eye(4)
                rotation[:3, :3] = Rotation.from_rotvec(axis * positions.get(name, 0)).as_matrix()
                result = result @ rotation
        return result


def desired_camera_pose(layout, rid):
    robot, config = layout['robots'][rid], layout['charuco']
    board = config['boards'][robot['table']]
    centre = np.asarray(board['center_xyz'])
    side = -1 if rid.endswith('front') else 1
    eye = centre + [0, side * config['view_offset'], config['view_height']]
    z = centre - eye
    z /= np.linalg.norm(z)
    x = np.cross(z, [0, 0, 1])
    x /= np.linalg.norm(x)
    target = np.eye(4)
    target[:3, :3] = np.column_stack([x, np.cross(z, x), z])
    target[:3, 3] = eye
    return target


def solve_views(layout, description):
    result = {}
    for rid in ROBOT_IDS:
        robot = layout['robots'][rid]
        if not robot['tools']['camera_enabled']:
            continue
        chain = Chain(description, f"{robot['table']}_table_top", f'{rid}_wrist_camera_optical_frame')
        target = desired_camera_pose(layout, rid)
        names = joint_names(rid)

        def residual(q):
            actual = chain.forward(dict(zip(names, q)))
            return np.r_[actual[:3, 3] - target[:3, 3], .2 * Rotation.from_matrix(
                actual[:3, :3] @ target[:3, :3].T).as_rotvec()]

        solutions = []
        # Both elbow branches and shoulder bearings; deterministic, no random search.
        for pan in (0., np.pi/2, -np.pi/2, np.pi):
            for elbow in (1.4, -1.4):
                seed = [pan, -1.4, elbow, -1.5, -np.pi/2, 0.]
                fit = least_squares(residual, seed, bounds=(-2*np.pi, 2*np.pi),
                                    max_nfev=250, ftol=1e-11, xtol=1e-11, gtol=1e-11)
                q = (fit.x + np.pi) % (2*np.pi) - np.pi
                if np.linalg.norm(residual(q)) < 1e-6:
                    # Prefer raised elbows and short angular distance to the old pose.
                    elbow_chain = Chain(description, f"{robot['table']}_table_top", f'{rid}_forearm_link')
                    elbow_z = elbow_chain.forward(dict(zip(names, q)))[2, 3]
                    score = np.linalg.norm(q - np.asarray(robot['initial_positions'])) - 4*elbow_z
                    solutions.append((score, q))
        if not solutions:
            raise RuntimeError(f'{rid}: board view is unreachable')
        result[rid] = min(solutions, key=lambda item: item[0])[1].tolist()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout')
    parser.add_argument('--output', required=True, help='Write a new layout; never overwrites the input')
    args = parser.parse_args()
    layout = load_layout(args.layout)
    source = Path(args.layout or default_layout_path()).expanduser()
    if Path(args.output).expanduser().resolve() == source.resolve():
        parser.error('--output must be a different file')
    with tempfile.TemporaryDirectory(prefix='uwa_charuco_views_') as directory:
        poses = solve_views(layout, render_description(layout, directory)[0])
    for rid, q in poses.items():
        layout['robots'][rid]['initial_positions'] = q
    Path(args.output).write_text(yaml.safe_dump(layout, sort_keys=False))
    print(yaml.safe_dump({rid: {'initial_positions': q} for rid, q in poses.items()}))


if __name__ == '__main__':
    main()

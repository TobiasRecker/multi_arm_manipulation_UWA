#!/usr/bin/env python3
"""Export the existing hardware collision model for the C++ protection runtime.

This is an offline file operation: it never connects to robot or controller ports.
"""
import argparse
import json
from pathlib import Path

from uwa_cell_motion.common import ROBOT_IDS, config, joint_names
from uwa_cell_motion.hardware_model import HardwareProblem, inventory_path


def export_model(problem, directory, *, mode):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    arms = {}
    spheres = {}
    for arm in ROBOT_IDS:
        profile = problem.profiles[arm]
        arms[arm] = dict(ip=profile['ip'] if mode == 'hardware' else '',
                         namespace=profile['namespace'], joint_names=joint_names(arm),
                         controller=('scaled_joint_trajectory_controller' if mode == 'hardware'
                                     else 'joint_trajectory_controller'))
        spheres[arm] = [dict(link=link, centre=centre.tolist(), radius=float(radius))
                        for link, centre, radius in zip(problem.spheres.links[arm],
                            problem.spheres.local[arm], problem.spheres.radii[arm])]
    result = dict(schema_version=1, model_signature=problem.signature,
                  urdf_path=str((problem.directory/'moveit/robot.urdf').resolve()),
                  srdf_path=str((problem.directory/'moveit/robot.srdf').resolve()),
                  arms=arms, spheres=spheres, neighbor_margin_m=.04, rate_hz=20.,
                  state_timeout_s=.2, mode=mode,
                  gripper_policy='full_opening_geometry_only',
                  model_joint_defaults={j: 0. for names in problem.names.values() for j in names[6:]})
    path = directory/'model-config.json'
    path.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('mock', 'hardware'), default='mock')
    parser.add_argument('--inventory', type=Path, default=inventory_path())
    parser.add_argument('--layout', type=Path)
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1]/
                        'uwa_cell_motion/config/hardware_carton_supported_trend.yaml')
    args = parser.parse_args(argv)
    target = args.output.resolve()
    problem = HardwareProblem(target/'model', config(args.config), args.inventory, args.layout)
    print(export_model(problem, target, mode=args.mode))


if __name__ == '__main__':
    main()

"""Configuration, identity and immutable model context."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import yaml

from uwa_cell_description.configuration import ROBOT_IDS, joint_names, gripper_joint, load_layout, default_layout_path

PAIRS = (('left_front', 'right_front'), ('left_front', 'left_rear'),
         ('right_front', 'right_rear'), ('left_rear', 'right_rear'))


def config(path=None):
    if path is None:
        from ament_index_python.packages import get_package_share_directory
        path = Path(get_package_share_directory('uwa_cell_motion'))/'config/motion.yaml'
    data = yaml.safe_load(Path(path).read_text())
    for name, value in data.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
            raise ValueError('Configuration requires positive finite numbers: '+name)
    return data


def simulation_only():
    if os.environ.get('ROS_DOMAIN_ID') != '64' or os.environ.get('GZ_PARTITION') != 'uwa_cell_sim':
        raise RuntimeError('Simulation only: source scripts/env.bash (domain64, uwa_cell_sim)')


def all_names(layout):
    return {rid: joint_names(rid)+([gripper_joint(rid)] if layout['robots'][rid]['tools']['gripper'] != 'none' else [])
            for rid in ROBOT_IDS}


def nominal_state(layout):
    result = {}
    for rid in ROBOT_IDS:
        result.update(zip(joint_names(rid), layout['robots'][rid]['initial_positions']))
        result[gripper_joint(rid)] = layout['robots'][rid]['tools']['gripper_initial_position']
    return result


def model_context(directory, layout_path=None):
    from uwa_cell_gazebo.configuration import render_description
    from uwa_cell_calibration.model import CollisionModel
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    layout = load_layout(layout_path or default_layout_path())
    description, _ = render_description(layout, directory)
    model = CollisionModel(description, directory/'moveit')
    return layout, description, model


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()

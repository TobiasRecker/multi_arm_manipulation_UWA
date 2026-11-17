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

# Measured Gazebo open-stop chatter: up to5.1urad span, 5.1mrad/s peak.
# A separate, tighter displacement window prevents accepting a moving tool.
TOOL_STANDSTILL_SPAN_RAD = 1e-5


def standstill_limits(cfg,count):
    velocity=np.full(count,cfg['standstill_velocity_rad_s'])
    span=velocity*cfg['standstill_window_s']
    if count>6:
        velocity[6:]=cfg['velocity_limit_rad_s'];span[6:]=TOOL_STANDSTILL_SPAN_RAD
    return velocity,span


def config(path=None):
    if path is None:
        from ament_index_python.packages import get_package_share_directory
        path = Path(get_package_share_directory('uwa_cell_motion'))/'config/motion.yaml'
    data = yaml.safe_load(Path(path).read_text())
    for name, value in data.items():
        if name=='arm_velocity_limits_rad_s':
            if not isinstance(value,dict) or set(value)!=set(ROBOT_IDS):
                raise ValueError('Explicit velocity limits for exactly all four arms required')
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) or v<=0 for v in value.values()):
                raise ValueError('Arm velocity limits must be positive finite numbers')
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
            raise ValueError('Configuration requires positive finite numbers: '+name)
    return data


def arm_velocity_limit(cfg,rid):
    """Same bound for measured speed checks and that arm's stopping envelope."""
    values=cfg.get('arm_velocity_limits_rad_s')
    return float(cfg['velocity_limit_rad_s'] if values is None else values[rid])


def simulation_only():
    if (os.environ.get('ROS_DOMAIN_ID') != '64' or os.environ.get('GZ_PARTITION') != 'uwa_cell_sim'
            or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST'):
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


def guard_signature(cfg):
    keys=('rate_hz','state_timeout_s','heartbeat_timeout_s','stop_latency_s','braking_acceleration_rad_s2',
          'velocity_limit_rad_s','model_margin_m','reset_hysteresis_m','standstill_velocity_rad_s',
          'standstill_window_s','sphere_spacing_m')
    bounds={k:cfg[k] for k in keys}
    if 'arm_velocity_limits_rad_s' in cfg:bounds['arm_velocity_limits_rad_s']=dict(cfg['arm_velocity_limits_rad_s'])
    return sha(json.dumps(dict(interlock_protocol=5,check_timebase='steady_wall',
        tool_standstill_velocity_rule='operating_cap_and_tight_position_span',
        tool_standstill_span_rad=TOOL_STANDSTILL_SPAN_RAD,
        operating_bounds=bounds),sort_keys=True))

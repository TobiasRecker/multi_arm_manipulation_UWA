"""Validate the layout and derive all controller joints from the same IDs."""
from copy import deepcopy
import math
from pathlib import Path

import yaml

ROBOT_IDS = ('left_front', 'left_rear', 'right_front', 'right_rear')
JOINT_SUFFIXES = (
    'shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
    'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint',
)
SCAN_DEFAULTS = {
    'source': '~/GoogleDrive/UWA/UR Setup.ply', 'scale': 1.0,
    'xyz': [0.0, 0.0, 0.0], 'rpy': [0.0, 0.0, 0.0],
    'opacity_min': 0.1, 'max_splat_scale': 0.05,
    'voxel_size': 0.01, 'max_points': 200000,
}


def default_layout_path():
    from ament_index_python.packages import get_package_share_directory
    return Path(get_package_share_directory('uwa_cell_description')) / 'config/cell_layout.yaml'


def number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be a number')
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f'{label} must be finite' + (' and positive' if positive else ''))
    return float(value)


def vector(value, length, label):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f'{label} must contain {length} numbers')
    return [number(v, label) for v in value]


def load_layout(path=None):
    path = Path(path or default_layout_path()).expanduser().resolve()
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError('Layout must be a YAML mapping')
    data = deepcopy(data)
    if set(data.get('tables', {})) != {'left', 'right'}:
        raise ValueError('Layout must define the left and right tables')
    if set(data.get('robots', {})) != set(ROBOT_IDS):
        raise ValueError(f'Layout must define exactly {ROBOT_IDS}')
    for table_id, table in data['tables'].items():
        for key in ('xyz', 'rpy'):
            table[key] = vector(table.get(key), 3, f'{table_id}.{key}')
        for key in ('width', 'length', 'height', 'top_thickness', 'leg_width'):
            table[key] = number(table.get(key), f'{table_id}.{key}', positive=True)
        if table['top_thickness'] >= table['height']:
            raise ValueError(f'{table_id}: tabletop must be thinner than table height')
        if 2 * table['leg_width'] >= min(table['width'], table['length']):
            raise ValueError(f'{table_id}: legs do not fit beneath the tabletop')
    for robot_id, robot in data['robots'].items():
        if robot.get('type') not in ('ur5', 'ur7e', 'ur5e'):
            raise ValueError(f'{robot_id}: supported types are ur5, ur7e and ur5e')
        if robot.get('table') not in data['tables']:
            raise ValueError(f'{robot_id}: unknown mounting table')
        for key in ('mount_xyz', 'mount_rpy'):
            robot[key] = vector(robot.get(key), 3, f'{robot_id}.{key}')
        robot['initial_positions'] = vector(
            robot.get('initial_positions'), 6, f'{robot_id}.initial_positions')
        table = data['tables'][robot['table']]
        if (abs(robot['mount_xyz'][0]) > table['width'] / 2 or
                abs(robot['mount_xyz'][1]) > table['length'] / 2 or
                robot['mount_xyz'][2] < 0):
            raise ValueError(f'{robot_id}: mounting centre is outside its tabletop')
        calibration = robot.get('kinematics_file')
        if calibration:
            calibration = Path(calibration).expanduser()
            if not calibration.is_absolute():
                calibration = path.parent / calibration
            if not calibration.is_file():
                raise ValueError(f'{robot_id}: missing kinematics file {calibration}')
            calibration = str(calibration.resolve())
        robot['kinematics_file'] = calibration or None
    scan = {**SCAN_DEFAULTS, **data.get('scan', {})}
    for key in ('xyz', 'rpy'):
        scan[key] = vector(scan[key], 3, f'scan.{key}')
    for key in ('scale', 'max_splat_scale', 'voxel_size'):
        scan[key] = number(scan[key], f'scan.{key}', positive=True)
    scan['opacity_min'] = number(scan['opacity_min'], 'scan.opacity_min')
    if not 0 <= scan['opacity_min'] <= 1:
        raise ValueError('scan.opacity_min must be in [0, 1]')
    if (isinstance(scan['max_points'], bool) or not isinstance(scan['max_points'], int)
            or scan['max_points'] <= 0):
        raise ValueError('scan.max_points must be a positive integer')
    source = Path(scan['source']).expanduser()
    scan['source'] = str(source if source.is_absolute() else path.parent / source)
    data['scan'] = scan
    return data


def joint_names(robot_id):
    return [f'{robot_id}_{suffix}' for suffix in JOINT_SUFFIXES]


def controller_parameters(layout):
    manager = {'update_rate': 100, 'use_sim_time': True,
               'joint_state_broadcaster': {'type': 'joint_state_broadcaster/JointStateBroadcaster'}}
    result = {'/uwa_cell/controller_manager': {'ros__parameters': manager}}
    for robot_id in ROBOT_IDS:
        name = f'{robot_id}_trajectory_controller'
        manager[name] = {'type': 'joint_trajectory_controller/JointTrajectoryController'}
        result[f'/uwa_cell/{name}'] = {'ros__parameters': {
            'joints': joint_names(robot_id), 'command_interfaces': ['position'],
            'state_interfaces': ['position', 'velocity'], 'use_sim_time': True,
            'allow_partial_joints_goal': False, 'state_publish_rate': 50.0,
            'action_monitor_rate': 20.0,
            'constraints': {'goal_time': 2.0, 'stopped_velocity_tolerance': 0.05},
        }}
    return result


def render_description(layout, directory):
    """Generate only temporary launch artifacts, never edit the source layout."""
    import xacro
    from ament_index_python.packages import get_package_share_directory
    directory = Path(directory)
    layout_file, controllers_file = directory / 'layout.yaml', directory / 'controllers.yaml'
    layout_file.write_text(yaml.safe_dump(layout))
    controllers_file.write_text(yaml.safe_dump(controller_parameters(layout)))
    xacro_file = Path(get_package_share_directory('uwa_cell_description')) / 'urdf/cell.urdf.xacro'
    description = xacro.process_file(str(xacro_file), mappings={
        'layout': str(layout_file), 'controllers_file': str(controllers_file),
    }).toxml()
    return description, controllers_file

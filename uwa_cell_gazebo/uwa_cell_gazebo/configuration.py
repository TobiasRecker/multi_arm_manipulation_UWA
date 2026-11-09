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
TOOLS_KEYS = {
    'gripper', 'gripper_initial_position', 'gripper_yaw', 'camera_enabled',
    'camera_yaw', 'camera_width', 'camera_height', 'camera_rate', 'camera_horizontal_fov',
}
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
    # Tool defaults have one source: the shipped layout, also for older/custom layouts.
    defaults = yaml.safe_load(default_layout_path().read_text())
    default_tools = defaults['tools']
    if not isinstance(default_tools, dict) or set(default_tools) != TOOLS_KEYS:
        raise ValueError(f'The default layout tools must define exactly {sorted(TOOLS_KEYS)}')
    if not isinstance(data.get('tools', {}), dict):
        raise ValueError('tools must be a YAML mapping')
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
        if not isinstance(robot.get('tools', {}), dict):
            raise ValueError(f'{robot_id}: tools must be a YAML mapping')
        tools = {**default_tools, **data.get('tools', {}), **robot.get('tools', {})}
        unknown = set(tools) - TOOLS_KEYS
        if unknown:
            raise ValueError(f'{robot_id}: unknown tool settings {sorted(unknown)}')
        if tools['gripper'] not in ('2f_85', 'none'):
            raise ValueError(f'{robot_id}: gripper must be 2f_85 or none')
        if not isinstance(tools['camera_enabled'], bool):
            raise ValueError(f'{robot_id}: camera_enabled must be true or false')
        for key in ('gripper_yaw', 'camera_yaw', 'gripper_initial_position'):
            tools[key] = number(tools[key], f'{robot_id}.tools.{key}')
        if not 0 <= tools['gripper_initial_position'] <= 0.8:
            raise ValueError(f'{robot_id}: gripper_initial_position must be in [0, 0.8] rad')
        for key in ('camera_width', 'camera_height'):
            value = tools[key]
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 4096:
                raise ValueError(f'{robot_id}: {key} must be an integer in [1, 4096]')
        for key in ('camera_rate', 'camera_horizontal_fov'):
            tools[key] = number(tools[key], f'{robot_id}.tools.{key}', positive=True)
        if tools['camera_rate'] > 30 or tools['camera_horizontal_fov'] >= math.pi:
            raise ValueError(f'{robot_id}: camera rate must be <= 30 Hz and FOV < pi')
        robot['tools'] = tools
    charuco = deepcopy(defaults['charuco'])
    supplied = data.get('charuco', {})
    if not isinstance(supplied, dict) or set(supplied) - set(charuco):
        raise ValueError('charuco must be a mapping of known board settings')
    charuco.update({key: value for key, value in supplied.items() if key != 'boards'})
    if not isinstance(charuco['enabled'], bool):
        raise ValueError('charuco.enabled must be true or false')
    if charuco['dictionary'] not in ('DICT_4X4_100', 'DICT_5X5_100', 'DICT_6X6_250'):
        raise ValueError('Unsupported ChArUco dictionary')
    for key in ('squares_x', 'squares_y', 'pixels_per_square', 'min_corners', 'samples'):
        value = charuco[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise ValueError(f'charuco.{key} must be an integer >= 2')
    if max(charuco['squares_x'], charuco['squares_y']) > 20 or not 40 <= charuco['pixels_per_square'] <= 500:
        raise ValueError('ChArUco texture dimensions exceed supported limits')
    if not 4 <= charuco['min_corners'] <= (charuco['squares_x']-1)*(charuco['squares_y']-1):
        raise ValueError('charuco.min_corners exceeds available chessboard corners')
    for key in ('square_length', 'marker_length', 'margin', 'thickness', 'view_height',
                'view_offset', 'max_translation_error', 'max_rotation_error_deg', 'max_reprojection_error_px'):
        charuco[key] = number(charuco[key], f'charuco.{key}', positive=True)
    if charuco['marker_length'] >= charuco['square_length']:
        raise ValueError('ChArUco markers must be smaller than squares')
    margin_pixels = charuco['margin'] / charuco['square_length'] * charuco['pixels_per_square']
    if not math.isclose(margin_pixels, round(margin_pixels), abs_tol=1e-6):
        raise ValueError('ChArUco margin must correspond to a whole number of texture pixels')
    boards = supplied.get('boards', {})
    if not isinstance(boards, dict) or set(boards) - {'left', 'right'}:
        raise ValueError('ChArUco boards must use the left and right table IDs')
    used_ids = set()
    count = charuco['squares_x'] * charuco['squares_y'] // 2
    capacity = int(charuco['dictionary'].rsplit('_', 1)[1])
    for table_id, board in charuco['boards'].items():
        override = boards.get(table_id, {})
        if not isinstance(override, dict) or set(override) - set(board) - {'mesh_file'}:
            raise ValueError(f'{table_id}: unknown ChArUco board settings')
        board.update(override)
        board['center_xyz'] = vector(board['center_xyz'], 3, f'{table_id}.board.center_xyz')
        board['yaw'] = number(board['yaw'], f'{table_id}.board.yaw')
        first = board['marker_start']
        if isinstance(first, bool) or not isinstance(first, int) or first < 0 or first+count > capacity:
            raise ValueError(f'{table_id}: ChArUco marker IDs exceed dictionary capacity')
        ids = set(range(first, first+count))
        if used_ids & ids:
            raise ValueError('Left/right ChArUco boards must use disjoint marker IDs')
        used_ids.update(ids)
        width = charuco['squares_x'] * charuco['square_length'] + 2 * charuco['margin']
        height = charuco['squares_y'] * charuco['square_length'] + 2 * charuco['margin']
        c, s = abs(math.cos(board['yaw'])), abs(math.sin(board['yaw']))
        table = data['tables'][table_id]
        if (abs(board['center_xyz'][0]) + (width*c+height*s)/2 > table['width']/2 or
                abs(board['center_xyz'][1]) + (width*s+height*c)/2 > table['length']/2 or
                board['center_xyz'][2] < charuco['thickness']):
            raise ValueError(f'{table_id}: ChArUco board is outside or below its tabletop')
    data['charuco'] = charuco
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


def gripper_joint(robot_id):
    return f'{robot_id}_robotiq_85_left_knuckle_joint'


def controller_names(layout):
    return ['joint_state_broadcaster'] + [
        f'{rid}_trajectory_controller' for rid in ROBOT_IDS] + [
        f'{rid}_gripper_controller' for rid in ROBOT_IDS
        if layout['robots'][rid]['tools']['gripper'] != 'none']


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
        if layout['robots'][robot_id]['tools']['gripper'] != 'none':
            name = f'{robot_id}_gripper_controller'
            manager[name] = {'type': 'joint_trajectory_controller/JointTrajectoryController'}
            result[f'/uwa_cell/{name}'] = {'ros__parameters': {
                'joints': [gripper_joint(robot_id)], 'command_interfaces': ['position'],
                'state_interfaces': ['position', 'velocity'], 'use_sim_time': True,
                'constraints': {'goal_time': 2.0, 'stopped_velocity_tolerance': 0.05},
            }}
    return result


def render_description(layout, directory):
    """Generate only temporary launch artifacts, never edit the source layout."""
    import xacro
    from ament_index_python.packages import get_package_share_directory
    directory = Path(directory)
    layout = deepcopy(layout)
    if layout['charuco']['enabled']:
        from .charuco import prepare_assets
        prepare_assets(layout['charuco'], directory / 'charuco')
    layout_file, controllers_file = directory / 'layout.yaml', directory / 'controllers.yaml'
    layout_file.write_text(yaml.safe_dump(layout))
    controllers_file.write_text(yaml.safe_dump(controller_parameters(layout)))
    xacro_file = Path(get_package_share_directory('uwa_cell_description')) / 'urdf/cell.urdf.xacro'
    description = xacro.process_file(str(xacro_file), mappings={
        'layout': str(layout_file), 'controllers_file': str(controllers_file),
    }).toxml()
    return description, controllers_file

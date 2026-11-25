"""Generate an isolated Gazebo cell from the accepted wood-frame plan."""

from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation
import yaml

from uwa_cell_description.configuration import ROBOT_IDS, controller_parameters, load_layout

from .core import ARMS, digest, write_json
from .scene import contact_description, physics_description
from .wood_frame import with_tool


BEAM_MODEL = 'wood_frame_beam'
POST_MODEL = 'wood_frame_posts'
ROBOT_MODEL = 'wood_frame_cell'
GROUP_CONTROLLER = 'rigid_object_controller'


def element(parent, tag, value=None, **attributes):
    item = ET.SubElement(parent, tag, **attributes)
    if value is not None:
        item.text = str(value)
    return item


def number_string(values):
    return ' '.join(f'{value:.12g}' for value in values)


def pose_string(transform):
    transform = np.asarray(transform, dtype=float)
    angles = Rotation.from_matrix(transform[:3, :3]).as_euler('xyz')
    return number_string((*transform[:3, 3], *angles))


def geometry(link, name, kind, dimensions, color, pose=None, *, collision=True, friction=None):
    for role in ('collision', 'visual') if collision else ('visual',):
        item = element(link, role, name=f'{name}_{role}')
        if pose is not None:
            element(item, 'pose', pose_string(pose))
        shape = element(element(item, 'geometry'), kind)
        for property_name, value in dimensions.items():
            element(shape, property_name, value)
        if role == 'visual':
            material = element(item, 'material')
            element(material, 'ambient', color)
            element(material, 'diffuse', color)
        if role == 'collision' and friction is not None:
            ode = element(element(element(item, 'surface'), 'friction'), 'ode')
            element(ode, 'mu', friction)
            element(ode, 'mu2', friction)


def make_world(plan, world_name, engine, cfg):
    scene = plan['scene']
    root = ET.Element('sdf', version='1.9')
    world = element(root, 'world', name=world_name)
    physics = element(world, 'physics', name='main', type='ignored')
    element(physics, 'max_step_size', cfg['physics_step_s'])
    element(physics, 'real_time_factor', cfg['simulation_real_time_factor'])
    element(world, 'gravity', '0 0 -9.81')
    for library, plugin_name in (('physics', 'Physics'), ('user-commands', 'UserCommands'),
                                 ('scene-broadcaster', 'SceneBroadcaster'), ('contact', 'Contact')):
        plugin = element(world, 'plugin', filename=f'gz-sim-{library}-system',
                         name=f'gz::sim::systems::{plugin_name}')
        if library == 'physics':
            element(element(plugin, 'engine'), 'filename', engine)

    light = element(world, 'light', name='work_light', type='directional')
    element(light, 'direction', '-0.4 0.2 -0.9')
    element(light, 'diffuse', '0.95 0.92 0.86 1')
    element(light, 'specular', '0.25 0.25 0.25 1')
    floor = element(world, 'model', name='floor')
    element(floor, 'static', 'true')
    geometry(element(floor, 'link', name='base'), 'floor_surface', 'plane',
             {'normal': '0 0 1', 'size': '30 30'}, '0.22 0.25 0.28 1')

    posts = element(world, 'model', name=POST_MODEL)
    element(posts, 'static', 'true')
    fixture = element(posts, 'link', name='fixture')
    for post in plan['simulated_fixture']['posts']:
        geometry(fixture, post['id'], 'box', {'size': number_string(post['size_m'])},
                 '0.55 0.33 0.17 1', post['pose'])

    beam = scene['beam']
    model = element(world, 'model', name=BEAM_MODEL)
    element(model, 'pose', pose_string(plan['simulated_fixture']['beam_start_pose']))
    link = element(model, 'link', name='body')
    size = np.asarray(beam['size_m'], dtype=float)
    mass = float(beam.get('mass_kg', 500. * np.prod(size)))
    inertial = element(link, 'inertial')
    element(inertial, 'mass', mass)
    inertia = element(inertial, 'inertia')
    for i, axis in enumerate(('ixx', 'iyy', 'izz')):
        element(inertia, axis, mass * (size[(i + 1) % 3] ** 2 + size[(i + 2) % 3] ** 2) / 12.)
    geometry(link, 'wood', 'box', {'size': number_string(size)}, '0.76 0.50 0.28 1',
             friction=cfg['friction'])
    sensor = element(link, 'sensor', name='beam_contacts', type='contact')
    element(sensor, 'always_on', 'true')
    element(sensor, 'update_rate', 100)
    element(element(sensor, 'contact'), 'collision', 'wood_collision')
    return root, mass


def stage_scene(plan, description, output, namespace, world_name, cfg, packages):
    """Bind the actual planner URDF and initial joints to one private controller."""
    if tuple(plan['scene']['holders']) != ARMS:
        raise ValueError('The Gazebo contact gripper profile uses right_front and right_rear')
    output = Path(output)
    controllers = output / 'controllers.yaml'
    layout = load_layout(plan['layout_path'])
    if digest(layout) != plan['layout_sha256']:
        raise ValueError('The cell layout changed after the offline audit')
    parameters = controller_parameters(layout)
    manager = parameters['/uwa_cell/controller_manager']['ros__parameters']
    active = ['joint_state_broadcaster', *(f'{arm}_gripper_controller' for arm in ARMS), GROUP_CONTROLLER]
    types = {key: manager[key] for key in active if key in manager}
    types[GROUP_CONTROLLER] = {'type': 'joint_trajectory_controller/JointTrajectoryController'}
    staged = {
        namespace + '/controller_manager': {'ros__parameters': {
            'update_rate': 1000, 'use_sim_time': True, 'enforce_command_limits': False, **types,
        }},
        namespace + '/' + GROUP_CONTROLLER: {'ros__parameters': {
            'joints': plan['joint_names'], 'command_interfaces': ['position', 'velocity'],
            'state_interfaces': ['position', 'velocity'], 'allow_partial_joints_goal': False,
            'state_publish_rate': 100., 'action_monitor_rate': 50., 'use_sim_time': True,
            'constraints': {'goal_time': 2., 'stopped_velocity_tolerance': 0.},
        }},
    }
    for name in active[1:-1]:
        staged[namespace + '/' + name] = parameters['/uwa_cell/' + name]
    controllers.write_text(yaml.safe_dump(staged))

    tool = plan['scene']['tool']
    description = with_tool(description, tool)
    description = contact_description(
        description, controllers, cfg['finger_joint_damping_nm_s'], cfg['gripper_coarse_velocity_rad_s'],
        cfg['gripper_fine_velocity_rad_s'], cfg['gripper_fine_start_rad'],
        gear_stiffness=cfg['gripper_gear_stiffness_nm_rad'],
        motor_stiffness=cfg['gripper_motor_stiffness_nm_rad'], transmission=cfg['gripper_transmission'],
        arm_velocity=cfg['joint_velocity_rad_s'], arm_acceleration=cfg['joint_acceleration_rad_s2'],
        finger_velocity_limit=cfg['finger_velocity_limit_rad_s'], motor_torque_limit=cfg['gripper_motor_torque_limit_nm'],
        motion_arms=ROBOT_IDS, grip_contact_friction=cfg['grip_contact_friction'], fingertips_prepared=True,
    )
    root = ET.fromstring(description)
    driver = root.find(f"link[@name='{tool['arm']}_wood_frame_driver']")
    for collision, color in zip(driver.findall('collision'), ('0.25 0.30 0.35 1', '0.64 0.66 0.67 1'), strict=True):
        visual = element(driver, 'visual')
        visual.append(deepcopy(collision.find('origin')))
        visual.append(deepcopy(collision.find('geometry')))
        element(element(visual, 'material', name='driver_' + color.split()[0]), 'color', rgba=color)
    visual = element(driver, 'visual')
    tip_distance = tool['tool0_to_tip'][2][3]
    element(visual, 'origin', xyz=number_string((0., 0., (tip_distance + tool['shaft_end_m']) / 2.)))
    element(element(visual, 'geometry'), 'cylinder', radius='0.003', length=str(tip_distance-tool['shaft_end_m']))
    element(element(visual, 'material', name='driver_tip'), 'color', rgba='0.93 0.54 0.16 1')
    initial = dict(zip(plan['joint_names'], plan['phases'][0]['positions'][0]))
    arm_hardware = root.find("ros2_control[@name='ContactArms']")
    if arm_hardware is None:
        raise ValueError('Plan description does not contain the Gazebo contact arm model')
    joint_interfaces = {joint.get('name'): joint for joint in arm_hardware.findall('joint')}
    if set(initial) != set(joint_interfaces):
        raise ValueError('Plan joints differ from the Gazebo contact arm model')
    for name, position in initial.items():
        interface = joint_interfaces[name].find("state_interface[@name='position']")
        field = interface.find("param[@name='initial_value']")
        if field is None:
            field = element(interface, 'param', name='initial_value')
        field.text = str(position)

    library = packages['tasks'] / 'lib' / 'libcontact_gripper.so'
    plugin = root.find("gazebo/plugin[@name='gz_ros2_control::GazeboSimROS2ControlPlugin']")
    plugin.find('parameters').text = str(controllers)
    plugin.find('ros/namespace').text = namespace
    element(plugin.find('ros'), 'remapping', '/clock:=' + namespace + '/clock')
    servo = root.find("gazebo/plugin[@name='uwa_cell_tasks::ContactServoSystem']")
    servo.set('filename', str(library))
    telemetry = root.find("gazebo/plugin[@name='uwa_cell_tasks::TaskTelemetry']")
    telemetry.set('filename', str(library))
    telemetry.find('ros_namespace').text = namespace
    element(telemetry, 'object_model', BEAM_MODEL)
    friction = root.find("gazebo/plugin[@name='uwa_cell_tasks::GripFriction']")
    friction.set('filename', str(library.with_name('libgrip_friction.so')))
    element(friction, 'object_model', BEAM_MODEL)
    for parent in root.findall('gazebo'):
        for sensor in parent.findall('sensor'):
            parent.remove(sensor)
    description = ET.tostring(root, encoding='unicode')
    publisher_params = output / 'robot_state_publisher.yaml'
    publisher_params.write_text(yaml.safe_dump({
        namespace + '/robot_state_publisher': {'ros__parameters': {
            'use_sim_time': True, 'robot_description': description,
        }},
    }))
    robot = output / 'robot.physics.urdf'
    robot.write_text(physics_description(description))

    engine_name = 'libgz-physics-' + cfg['physics_engine'].replace('_', '-') + '-plugin.so'
    vendor = packages['physics']
    engine = next((path / engine_name for path in (vendor / 'lib', vendor / 'opt/gz_physics_vendor/lib')
                   if (path / engine_name).is_file()), None)
    if engine is None or not library.is_file():
        raise FileNotFoundError('Build uwa_cell_tasks with the Gazebo task plugins')
    world, mass = make_world(plan, world_name, engine, cfg)
    world_path = output / 'world.sdf'
    world_path.write_text(ET.tostring(world, encoding='unicode'))
    write_json(output / 'scene.json', {'cfg': cfg, 'mass_kg': mass, 'world': world_name,
        'namespace': namespace, 'plan_sha256': plan['sha256'],
        'fastening_model': 'Gazebo fixed joint added after all planned screw procedures finish'})
    return world_path, robot, controllers, publisher_params, active


def screw_marker(screw):
    """Display the completed simulated site without adding a collision body."""
    model_name = 'completed_' + screw['id']
    root = ET.Element('sdf', version='1.9')
    model = element(root, 'model', name=model_name)
    element(model, 'static', 'true')
    direction = np.asarray(screw['direction'], dtype=float)
    direction /= np.linalg.norm(direction)
    pose = np.eye(4)
    pose[:3, 3] = np.asarray(screw['entry_m']) - .001 * direction
    pose[:3, :3] = Rotation.align_vectors([direction], [[0., 0., 1.]])[0].as_matrix()
    link = element(model, 'link', name='head')
    geometry(link, 'screw_head', 'cylinder', {'radius': .004, 'length': .002},
             '0.26 0.29 0.33 1', pose, collision=False)
    return model_name, ET.tostring(root, encoding='unicode')

"""One asset, convex thin-wall contact shapes, full planning-scene geometry."""
from copy import deepcopy
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
import yaml

from uwa_cell_description.scene_assets import instances
from uwa_cell_gazebo.configuration import render_description
from uwa_cell_description.configuration import gripper_joint, joint_names
from .core import ARMS, seal, write_json


def carton_shapes(instance, directory, thickness):
    """Extrude external skin triangles inward; preserve observed upper cutouts.

    Triangular prisms are convex and dynamic-engine friendly. No convex hull
    across the complete open carton. Geometry stays pinned to source STL.
    """
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    source = instance['mesh_file'].parent / instance['manifest']['solid_mesh']
    data = source.read_bytes(); count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * count: raise ValueError('Expected binary source STL')
    triangles = np.array([[struct.unpack_from('<3f', data, 84 + k*50 + 12 + i*12)
                           for i in range(3)] for k in range(count)])
    dimensions = triangles.max(axis=(0, 1)); result = []
    for axis, side in ((2, 0), (0, 0), (0, 1), (1, 0), (1, 1)):
        plane = dimensions[axis] if side else 0.
        for triangle in triangles[np.all(abs(triangles[:, :, axis] - plane) < 1e-7, axis=1)]:
            shift = np.zeros(3); shift[axis] = thickness * (-1 if side else 1)
            vertices = np.vstack([triangle, triangle + shift])
            hull = ConvexHull(vertices); faces = hull.simplices.copy()
            for k, face in enumerate(faces):
                normal = np.cross(vertices[face[1]]-vertices[face[0]], vertices[face[2]]-vertices[face[0]])
                if normal @ hull.equations[k, :3] < 0: faces[k] = face[::-1]
            path = directory / f'part_{len(result):03d}.obj'
            path.write_text(''.join('v %.12g %.12g %.12g\n' % tuple(v) for v in vertices)
                            + ''.join('f %d %d %d\n' % tuple(f+1) for f in faces))
            result.append(dict(vertices=vertices.tolist(), triangles=faces.tolist(), uri=path.as_uri(),
                               sha256=hashlib.sha256(path.read_bytes()).hexdigest(), axis=axis, side=side))
    if len(result) < 10: raise ValueError('Source does not describe the expected thin-wall carton')
    return result


def mass_properties(shapes, mass):
    volume = 0.; first = np.zeros(3); second = np.zeros((3, 3))
    for shape in shapes:
        vertices = np.array(shape['vertices']); centre = vertices.mean(axis=0)
        for face in shape['triangles']:
            tetra = np.vstack([centre, vertices[face]])
            weight = abs(np.linalg.det((tetra[1:] - tetra[0]).T)) / 6
            total = tetra.sum(axis=0)
            volume += weight; first += weight * total / 4
            second += weight * (tetra.T @ tetra + np.outer(total, total)) / 20
    com = first / volume
    covariance = second / volume - np.outer(com, com)
    inertia = mass * (np.trace(covariance) * np.eye(3) - covariance)
    return com, inertia


def dynamic_sdf(instance, shapes, cfg, *, model_name='uwa_grasp_carton'):
    root = ET.Element('sdf', version='1.9'); model = ET.SubElement(root, 'model', name=model_name)
    ET.SubElement(model, 'static').text = 'false'
    t = instance['T_world_object']
    ET.SubElement(model, 'pose').text = ' '.join(map(str, [*t[:3, 3], *Rotation.from_matrix(t[:3, :3]).as_euler('xyz')]))
    link = ET.SubElement(model, 'link', name='body')
    com, inertia = mass_properties(shapes, cfg['mass_kg'])
    inertial = ET.SubElement(link, 'inertial'); ET.SubElement(inertial, 'mass').text = str(cfg['mass_kg'])
    ET.SubElement(inertial, 'pose').text = ' '.join(map(str, [*com, 0, 0, 0]))
    tensor = ET.SubElement(inertial, 'inertia')
    for key, i, j in [('ixx',0,0),('iyy',1,1),('izz',2,2),('ixy',0,1),('ixz',0,2),('iyz',1,2)]:
        ET.SubElement(tensor, key).text = str(inertia[i, j])
    for index, shape in enumerate(shapes):
        collision = ET.SubElement(link, 'collision', name=f'shell_{index}')
        ET.SubElement(ET.SubElement(ET.SubElement(collision, 'geometry'), 'mesh'), 'uri').text = shape['uri']
        ode = ET.SubElement(ET.SubElement(ET.SubElement(collision, 'surface'), 'friction'), 'ode')
        ET.SubElement(ode, 'mu').text = str(cfg['friction']); ET.SubElement(ode, 'mu2').text = str(cfg['friction'])
    visual = ET.SubElement(link, 'visual', name='photo_texture')
    ET.SubElement(ET.SubElement(ET.SubElement(visual, 'geometry'), 'mesh'), 'uri').text = instance['mesh_file'].as_uri()
    sensor = ET.SubElement(link, 'sensor', name='carton_contacts', type='contact')
    ET.SubElement(sensor, 'always_on').text = 'true'; ET.SubElement(sensor, 'update_rate').text = '100'
    ET.SubElement(sensor, 'topic').text = '/uwa_grasp/carton_contacts'
    contact = ET.SubElement(sensor, 'contact')
    for i in range(len(shapes)): ET.SubElement(contact, 'collision').text = f'shell_{i}'
    plugin = ET.SubElement(model, 'plugin', filename='gz-sim-pose-publisher-system', name='gz::sim::systems::PosePublisher')
    ET.SubElement(plugin, 'publish_link_pose').text = 'true'
    ET.SubElement(plugin, 'publish_model_pose').text = 'true'
    ET.SubElement(plugin, 'use_pose_vector_msg').text = 'true'
    ET.SubElement(plugin, 'update_frequency').text = '100'
    return ET.tostring(root, encoding='unicode')


def contact_description(description, controllers_path):
    """Opt-in profile; default cell description/controllers stay unchanged.

    Contact fingers are force servos with measured independent joints. URDF
    mimic is removed only in this profile so collision FK uses real fingers.
    """
    root = ET.fromstring(description)
    control = root.find('ros2_control')
    backend = ET.SubElement(root, 'ros2_control', name='ContactGrippers', type='system')
    hardware = ET.SubElement(backend, 'hardware')
    ET.SubElement(hardware, 'plugin').text = 'uwa_cell_tasks/ContactGripper'
    for name, value in [('kp','3.0'),('kd','0.12'),('max_torque','0.35')]:
        ET.SubElement(hardware, 'param', name=name).text = value
    for joint in list(control.findall('joint')):
        name = joint.get('name')
        if not any(name.startswith(a+'_robotiq_85_') for a in ARMS): continue
        control.remove(joint); backend.append(joint); joint.set('mimic', 'false')
        if joint.find("state_interface[@name='effort']") is None: ET.SubElement(joint, 'state_interface', name='effort')
        physical = root.find(f"joint[@name='{name}']")
        mimic = physical.find('mimic')
        if mimic is not None:
            for key, value in [('driver',mimic.get('joint')),('multiplier',mimic.get('multiplier','1'))]:
                ET.SubElement(joint, 'param', name=key).text = value
            physical.remove(mimic)
        else: ET.SubElement(joint, 'param', name='driver').text = name
    plugin = root.find("gazebo/plugin[@name='gz_ros2_control::GazeboSimROS2ControlPlugin']")
    plugin.find('parameters').text = str(controllers_path)
    return ET.tostring(root, encoding='unicode')


def prepare_scene(layout, cfg, directory):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    instance = next((i for i in instances(layout) if i['id'] == cfg['object_id']), None)
    if instance is None: raise ValueError('Requested object is not in the central layout')
    shapes = carton_shapes(instance, directory/'collision', cfg['wall_thickness_m'])
    description, controllers = render_description(layout, directory/'model')
    params = yaml.safe_load(controllers.read_text())
    group_name = 'rigid_object_controller'
    params['/uwa_cell/controller_manager']['ros__parameters'][group_name] = {'type':'joint_trajectory_controller/JointTrajectoryController'}
    params['/uwa_cell/'+group_name] = {'ros__parameters': dict(
        joints=[j for a in ARMS for j in joint_names(a)], command_interfaces=['position'],
        state_interfaces=['position','velocity'], allow_partial_joints_goal=False,
        action_monitor_rate=50., state_publish_rate=100.,
        constraints=dict(stopped_velocity_tolerance=.003, goal_time=2.0), use_sim_time=True)}
    controllers.write_text(yaml.safe_dump(params))
    description = contact_description(description, controllers)
    (directory/'robot.urdf').write_text(description)
    sdf = dynamic_sdf(instance, shapes, cfg); (directory/'carton.sdf').write_text(sdf)
    world = ET.Element('sdf', version='1.9'); w = ET.SubElement(world, 'world', name='uwa_grasp_lab')
    physics=ET.SubElement(w,'physics', name='default', type='ignored')
    ET.SubElement(physics,'max_step_size').text='.001'; ET.SubElement(physics,'real_time_factor').text='1'
    for filename,name in [('physics','Physics'),('user-commands','UserCommands'),('scene-broadcaster','SceneBroadcaster'),('contact','Contact')]:
        ET.SubElement(w,'plugin',filename='gz-sim-'+filename+'-system',name='gz::sim::systems::'+name)
    ET.SubElement(w,'gravity').text='0 0 -9.81'
    (directory/'world.sdf').write_text(ET.tostring(world,encoding='unicode'))
    record = seal(dict(schema_version=1, cfg=cfg, object_id=instance['id'],
        T_world_object=instance['T_world_object'], asset_sha256=instance['manifest']['files'],
        shapes=shapes, robot_sha256=hashlib.sha256(description.encode()).hexdigest(),
        mass_and_friction_measured=False, contact_model='force-limited coupled finger approximation'))
    write_json(directory/'scene.json', record)
    return record


def apply_object(model, scene, world_object, *, touching=False):
    """Explicit object plus only the intended fingertip contact exemptions."""
    from moveit_msgs.msg import CollisionObject
    from shape_msgs.msg import Mesh, MeshTriangle
    from geometry_msgs.msg import Point, Pose
    obj = CollisionObject(); obj.header.frame_id='world'; obj.id=scene['object_id']
    t=np.asarray(world_object); q=Rotation.from_matrix(t[:3,:3]).as_quat()
    for shape in scene['shapes']:
        mesh=Mesh(); mesh.vertices=[Point(x=float(v[0]),y=float(v[1]),z=float(v[2])) for v in shape['vertices']]
        mesh.triangles=[MeshTriangle(vertex_indices=face) for face in shape['triangles']]
        pose=Pose(); pose.position.x,pose.position.y,pose.position.z=map(float,t[:3,3])
        pose.orientation.x,pose.orientation.y,pose.orientation.z,pose.orientation.w=map(float,q)
        obj.meshes.append(mesh); obj.mesh_poses.append(pose)
    obj.operation=CollisionObject.ADD; model.scene.apply_collision_object(obj)
    for arm in ARMS:
        for side in ('left','right'):
            model.scene.allowed_collision_matrix.set_entry(arm+'_robotiq_85_'+side+'_finger_tip_link',obj.id,touching)

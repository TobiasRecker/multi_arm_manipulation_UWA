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
from .core import ARMS, seal, write_json, verify


def wall_strips(polygons, axis):
    """Exact vertical-envelope decomposition with a seam-free lower wall.

    Accept only a wall without internal holes: its envelope area must equal
    its source polygon area. Upper cutouts and lower bevels remain unchanged.
    The central rectangle is an analytic box in the contact simulator.
    """
    tangent=1-axis;coordinates=np.unique(np.concatenate(polygons)[:,tangent])
    lower=[];upper=[]
    for left,right in zip(coordinates,coordinates[1:]):
        coordinate=(left+right)/2;edges=[]
        for polygon in polygons:
            for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
                if min(a[tangent],b[tangent])<coordinate<max(a[tangent],b[tangent]):
                    edges.append([a[2]+(b[2]-a[2])*(x-a[tangent])/(b[tangent]-a[tangent]) for x in (left,right)])
        # Use the open interval's edges: a vertical upper-contour step has
        # distinct one-sided heights at its endpoint.
        edges.sort(key=lambda z:sum(z));lower.append(edges[0]);upper.append(edges[-1])
    source_area=sum(ConvexHull(p[:,[tangent,2]]).volume for p in polygons)
    envelope_area=sum((b-a)*np.mean(np.array(u)-l) for a,b,u,l in zip(coordinates,coordinates[1:],upper,lower))
    if not np.isclose(source_area,envelope_area,atol=1e-10,rtol=1e-7):
        raise ValueError('Carton wall has holes/overlaps; vertical decomposition would alter its geometry')
    bottom=float(np.max(lower));top=float(np.min(upper));plane=polygons[0][0,axis]
    if top<=bottom:raise ValueError('No continuous lower wall')
    def polygon(points):
        points=np.unique(points,axis=0)
        if len(points)<3:return None
        try:hull=ConvexHull(points)
        except Exception:return None
        if hull.volume<1e-12:return None
        result=np.zeros((len(hull.vertices),3));result[:,axis]=plane
        result[:,[tangent,2]]=points[hull.vertices];return result
    result=[polygon([(coordinates[0],bottom),(coordinates[-1],bottom),(coordinates[-1],top),(coordinates[0],top)])]
    for i,(a,b) in enumerate(zip(coordinates,coordinates[1:])):
        for points in [[(a,top),(b,top),(b,upper[i][1]),(a,upper[i][0])],
                       [(a,lower[i][0]),(b,lower[i][1]),(b,bottom),(a,bottom)]]:
            part=polygon(points)
            if part is not None:result.append(part)
    return result,top


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
        polygons=[triangle for triangle in triangles[np.all(abs(triangles[:, :, axis] - plane) < 1e-7, axis=1)]]
        projection=[i for i in range(3) if i!=axis]
        # Merge adjacent triangles iff their union is exactly convex. This
        # reduces dynamic collision bodies without filling a cutout or cavity.
        wall_base_top=None
        if axis!=2:polygons,wall_base_top=wall_strips(polygons,axis)
        changed=True
        while changed:
            changed=False
            for i in range(len(polygons)):
                if changed:break
                if wall_base_top is not None and i==0:continue
                for j in range(i+1,len(polygons)):
                    a,b=polygons[i],polygons[j]
                    if len({tuple(v) for v in a}.intersection(tuple(v) for v in b))<2:continue
                    combined=np.unique(np.vstack([a,b]),axis=0)
                    hull=ConvexHull(combined[:,projection])
                    area=ConvexHull(a[:,projection]).volume+ConvexHull(b[:,projection]).volume
                    if abs(hull.volume-area)>max(1e-12,area*1e-7):continue
                    polygons[i]=combined[hull.vertices];polygons.pop(j);changed=True;break
        for triangle in polygons:
            shift = np.zeros(3); shift[axis] = thickness * (-1 if side else 1)
            vertices = np.vstack([triangle, triangle + shift])
            hull = ConvexHull(vertices); faces = hull.simplices.copy()
            for k, face in enumerate(faces):
                normal = np.cross(vertices[face[1]]-vertices[face[0]], vertices[face[2]]-vertices[face[0]])
                if normal @ hull.equations[k, :3] < 0: faces[k] = face[::-1]
            path = directory / f'part_{len(result):03d}.stl'
            binary=bytearray(b'UWA convex contact prism'.ljust(80,b'\0'))
            binary.extend(struct.pack('<I',len(faces)))
            for face in faces:
                triangle=vertices[face]
                normal=np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]);normal/=np.linalg.norm(normal)
                binary.extend(struct.pack('<12fH',*normal,*triangle.ravel(),0))
            path.write_bytes(binary)
            outline=vertices[:len(vertices)//2]
            box=bool(len(outline)==4 and all(len(np.unique(outline[:,k]))==2 for k in projection))
            result.append(dict(vertices=vertices.tolist(), triangles=faces.tolist(), uri=path.as_uri(),
                               sha256=hashlib.sha256(path.read_bytes()).hexdigest(), axis=axis, side=side,
                               outline_vertices=len(vertices)//2,analytic_box=box,wall_base_top_m=wall_base_top))
    if len(result) < 5: raise ValueError('Source does not describe the expected thin-wall carton')
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
        geometry=ET.SubElement(collision,'geometry')
        if shape.get('analytic_box'):
            vertices=np.array(shape['vertices']);centre=(vertices.max(axis=0)+vertices.min(axis=0))/2
            ET.SubElement(collision,'pose').text=' '.join(map(str,[*centre,0,0,0]))
            ET.SubElement(ET.SubElement(geometry,'box'),'size').text=' '.join(map(str,np.ptp(vertices,axis=0)))
        else:ET.SubElement(ET.SubElement(geometry,'mesh'),'uri').text=shape['uri']
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


def fingertip_contact_primitives(root):
    """Conservative housing/pad boxes; preserve the source's inner pad plane.

    Split at2mm behind the innermost surface. Include clipped triangle-edge
    intersections so the union contains the original complete triangle mesh.
    Separate fixed pad links allow only actual gripping surfaces to touch.
    """
    from urllib.parse import urlparse,unquote
    metadata=[]
    for arm in ARMS:
        for side in ('left','right'):
            name=arm+'_robotiq_85_'+side+'_finger_tip_link';link=root.find(f"link[@name='{name}']")
            collision=link.find('collision');mesh=collision.find('geometry/mesh');uri=mesh.get('filename')
            path=Path(unquote(urlparse(uri).path));data=path.read_bytes();count=struct.unpack_from('<I',data,80)[0]
            if len(data)!=84+50*count:raise ValueError('Expected binary fingertip STL')
            triangles=np.array([[struct.unpack_from('<3f',data,84+k*50+12+i*12) for i in range(3)] for k in range(count)])
            triangles*=np.array(list(map(float,mesh.get('scale','1 1 1').split())))
            vertices=triangles.reshape(-1,3);direction=1 if side=='right' else -1
            cut=float((vertices[:,0]*direction).max()-.002)
            clipped=list(vertices[vertices[:,0]*direction>=cut])
            for a,b in zip(triangles.reshape(-1,3),np.roll(triangles,-1,axis=1).reshape(-1,3)):
                u,v=a[0]*direction,b[0]*direction
                if (u-cut)*(v-cut)<0:clipped.append(a+(cut-u)/(v-u)*(b-a))
            clipped=np.array(clipped);pad_bounds=[clipped.min(axis=0),clipped.max(axis=0)]
            body_bounds=[vertices.min(axis=0),vertices.max(axis=0)]
            body_bounds[1 if direction>0 else 0][0]=direction*cut
            original=collision.find('origin')
            xyz=np.array(list(map(float,original.get('xyz','0 0 0').split()))) if original is not None else np.zeros(3)
            angles=original.get('rpy','0 0 0') if original is not None else '0 0 0'
            rotation=Rotation.from_euler('xyz',list(map(float,angles.split()))).as_matrix()
            def box(target,bounds):
                for child in list(target):target.remove(child)
                centre=(bounds[0]+bounds[1])/2
                ET.SubElement(target,'origin',xyz=' '.join(map(str,xyz+rotation@centre)),rpy=angles)
                ET.SubElement(ET.SubElement(target,'geometry'),'box',size=' '.join(map(str,bounds[1]-bounds[0])))
            collision.set('name',name+'_housing_collision');box(collision,body_bounds)
            pad_name=arm+'_robotiq_85_'+side+'_finger_tip_pad_link'
            pad=ET.SubElement(root,'link',name=pad_name);box(ET.SubElement(pad,'collision',name=pad_name+'_collision'),pad_bounds)
            joint=ET.SubElement(root,'joint',name=pad_name+'_mount',type='fixed')
            ET.SubElement(joint,'parent',link=name);ET.SubElement(joint,'child',link=pad_name)
            metadata.append(dict(link=name,pad_link=pad_name,source_mesh=uri,
                source_sha256=hashlib.sha256(data).hexdigest(),housing_bounds=body_bounds,pad_bounds=pad_bounds,
                inner_plane_axis=0,inner_plane_direction=direction))
    return metadata


def contact_description(description, controllers_path, finger_damping=.04,coarse=.02,fine=.004,fine_start=.65,geometry_metadata=None,
                        gear_stiffness=10.,motor_stiffness=10.,transmission='native_gear',
                        arm_velocity=.05,arm_acceleration=.5,finger_velocity_limit=.05,motor_torque_limit=.35, motion_arms=ARMS,
                        grip_contact_friction=None):
    """Opt-in profile; default cell description/controllers stay unchanged.

    Contact fingers are force servos with measured independent joints. URDF
    mimic is removed only in this profile so collision FK uses real fingers.
    """
    root = ET.fromstring(description)
    primitives=fingertip_contact_primitives(root)
    if geometry_metadata is not None:geometry_metadata.extend(primitives)
    control = root.find('ros2_control')
    arm_backend=ET.SubElement(root,'ros2_control',name='ContactArms',type='system')
    ET.SubElement(ET.SubElement(arm_backend,'hardware'),'plugin').text='uwa_cell_tasks/ContactArms'
    for name,value in [('max_velocity',arm_velocity),('max_acceleration',arm_acceleration)]:
        ET.SubElement(arm_backend.find('hardware'),'param',name=name).text=str(value)
    for joint in list(control.findall('joint')):
        if joint.get('name') not in [name for arm in motion_arms for name in joint_names(arm)]:continue
        control.remove(joint);arm_backend.append(joint)
        for command in list(joint.findall('command_interface')):
            if command.get('name') not in ('position','velocity'):joint.remove(command)
        for state in list(joint.findall('state_interface')):
            if state.get('name')=='effort':joint.remove(state)
    backend = ET.SubElement(root, 'ros2_control', name='ContactGrippers', type='system')
    hardware = ET.SubElement(backend, 'hardware')
    ET.SubElement(hardware, 'plugin').text = 'uwa_cell_tasks/ContactGripper'
    ET.SubElement(hardware,'param',name='native_mimic').text='true' if transmission=='native_gear' else 'false'
    ET.SubElement(hardware,'param',name='velocity_limit').text=str(finger_velocity_limit)
    for name, value in [('kp',gear_stiffness),('motor_kp',motor_stiffness),('kd','0.003'),('max_torque','0.35'),('motor_max_torque',motor_torque_limit),('coarse_velocity',coarse),('fine_velocity',fine),('fine_start',fine_start)]:
        ET.SubElement(hardware, 'param', name=name).text = str(value)
    for joint in list(control.findall('joint')):
        name = joint.get('name')
        if not any(name.startswith(a+'_robotiq_85_') for a in ARMS): continue
        control.remove(joint); backend.append(joint); joint.set('mimic', 'false')
        if joint.find("state_interface[@name='effort']") is None: ET.SubElement(joint, 'state_interface', name='effort')
        physical = root.find(f"joint[@name='{name}']")
        dynamics=physical.find('dynamics')
        if dynamics is None:dynamics=ET.SubElement(physical,'dynamics')
        dynamics.set('damping',str(finger_damping))
        mimic = physical.find('mimic')
        if mimic is not None:
            for key, value in [('driver',mimic.get('joint')),('multiplier',mimic.get('multiplier','1'))]:
                ET.SubElement(joint, 'param', name=key).text = value
            physical.remove(mimic)
        else: ET.SubElement(joint, 'param', name='driver').text = name
    plugin = root.find("gazebo/plugin[@name='gz_ros2_control::GazeboSimROS2ControlPlugin']")
    plugin.find('parameters').text = str(controllers_path)
    from ament_index_python.packages import get_package_prefix
    servo_library=Path(get_package_prefix('uwa_cell_tasks'))/'lib/libcontact_gripper.so'
    ET.SubElement(ET.SubElement(root,'gazebo'),'plugin',filename=str(servo_library),name='uwa_cell_tasks::ContactServoSystem')
    telemetry=ET.SubElement(ET.SubElement(root,'gazebo'),'plugin',filename=str(servo_library),name='uwa_cell_tasks::TaskTelemetry')
    ET.SubElement(telemetry,'ros_namespace').text='/uwa_cell'
    if grip_contact_friction is not None:
        plugin = ET.SubElement(ET.SubElement(root,'gazebo'),'plugin',
                               filename=str(servo_library.with_name('libgrip_friction.so')),
                               name='uwa_cell_tasks::GripFriction')
        ET.SubElement(plugin,'coefficient').text=str(grip_contact_friction)
    return ET.tostring(root, encoding='unicode')


def physics_description(description):
    """Native solver gears only in the physical spawn model.

    Planning/TF retain independent measured finger joints. This is an internal
    mechanical constraint, never a robot/object attachment or pose reset.
    ros2_control's mimic=false keeps passive joints state-only in our backend.
    """
    root=ET.fromstring(description)
    # The unselected left grippers retain the stock kinematic driver. Do not
    # add a second physical constraint beside that driver's mimic commands.
    # Their original mimic rules remain in its robot_description parameter.
    for joint in root.findall('joint'):
        if joint.get('name').startswith(('left_front_','left_rear_')):
            for mimic in list(joint.findall('mimic')):joint.remove(mimic)
    # Bullet Featherstone supports one multibody tree per model. The ordinary
    # cell has two table trees attached to SDF's reserved world. A non-reserved
    # fixed anchor joins them without changing any physical frame or geometry.
    anchor='task_cell_anchor';link=ET.SubElement(root,'link',name=anchor)
    inertial=ET.SubElement(link,'inertial');ET.SubElement(inertial,'mass',value='1')
    ET.SubElement(inertial,'inertia',ixx='1',iyy='1',izz='1',ixy='0',ixz='0',iyz='0')
    for joint in root.findall('joint'):
        parent=joint.find('parent')
        if parent.get('link')=='world':parent.set('link',anchor)
    fixed=ET.SubElement(root,'joint',name='world_to_task_cell_anchor',type='fixed')
    ET.SubElement(fixed,'parent',link='world');ET.SubElement(fixed,'child',link=anchor)
    control=root.find("ros2_control[@name='ContactGrippers']")
    if control.find("hardware/param[@name='native_mimic']").text=='true':
        for joint in control.findall('joint'):
            name=joint.get('name');driver=joint.find("param[@name='driver']").text
            if driver==name:continue
            multiplier=joint.find("param[@name='multiplier']").text
            ET.SubElement(root.find(f"joint[@name='{name}']"),'mimic',joint=driver,multiplier=multiplier,offset='0')
    return ET.tostring(root,encoding='unicode')


def add_virtual_marker_visual(description, tool=None):
    """Show the checked virtual tool in Gazebo without adding contact forces."""
    length, radius = (tool.length_m, tool.tip_radius_m) if tool else (.30,.003)
    shaft_end = length-radius if tool else .294
    root = ET.fromstring(description)
    link = root.find("link[@name='left_front_tool0']")
    if link is None:
        raise ValueError('Drawing world needs left_front_tool0')
    visual = ET.SubElement(link,'visual',name='virtual_marker')
    ET.SubElement(visual,'origin',xyz=f'0 0 {(.18+shaft_end)/2}',rpy='0 0 0')
    geometry = ET.SubElement(visual,'geometry')
    ET.SubElement(geometry,'cylinder',radius=str(radius),length=str(shaft_end-.18))
    material = ET.SubElement(visual,'material',name='virtual_marker_orange')
    ET.SubElement(material,'color',rgba='1 0.30 0.04 1')
    tip = ET.SubElement(link,'visual',name='virtual_marker_tip')
    ET.SubElement(tip,'origin',xyz=f'0 0 {length-radius}',rpy='0 0 0')
    ET.SubElement(ET.SubElement(tip,'geometry'),'sphere',radius=str(radius))
    ET.SubElement(ET.SubElement(tip,'material',name='virtual_marker_tip_color'),
                  'color',rgba='1 0.8 0.08 1')
    return ET.tostring(root,encoding='unicode')


def prepare_scene(layout, cfg, directory, *, surface_offset_m=0.):
    directory = Path(directory).resolve()
    if (directory/'scene.json').exists():raise FileExistsError('Scene is immutable; prepare into a new directory')
    directory.mkdir(parents=True, exist_ok=True)
    from ament_index_python.packages import get_package_prefix
    force_backend=None
    if cfg.get('force_observation'):
        force_backend=(Path(get_package_prefix('uwa_cell_tasks'))/'lib/libforce_telemetry.so').resolve()
        if not force_backend.is_file():raise FileNotFoundError('Build native force telemetry first')
    vendor=Path(get_package_prefix('gz_physics_vendor'))
    library='libgz-physics-'+cfg['physics_engine'].replace('_','-')+'-plugin.so'
    engines=[base/'lib'/library for base in (vendor,vendor/'opt/gz_physics_vendor')]
    engine=next((p.resolve() for p in engines if p.is_file()),None)
    if engine is None:raise FileNotFoundError('Required contact physics engine not installed: '+library)
    instance = next((i for i in instances(layout) if i['id'] == cfg['object_id']), None)
    if instance is None: raise ValueError('Requested object is not in the central layout')
    shapes = carton_shapes(instance, directory/'collision', cfg['wall_thickness_m'])
    description, controllers = render_description(layout, directory/'model')
    params = yaml.safe_load(controllers.read_text())
    params['/uwa_cell/controller_manager']['ros__parameters']['update_rate']=1000
    # Publish telemetry at the measurement cadence.
    params.setdefault('/uwa_cell/joint_state_broadcaster',{}).setdefault('ros__parameters',{})['update_rate']=100
    motion_arms = (*ARMS, 'left_front') if cfg.get('drawing_recipe') else ARMS
    group_name = 'rigid_object_controller'
    params['/uwa_cell/controller_manager']['ros__parameters'][group_name] = {'type':'joint_trajectory_controller/JointTrajectoryController'}
    params['/uwa_cell/'+group_name] = {'ros__parameters': dict(
        joints=[j for a in motion_arms for j in joint_names(a)], command_interfaces=['position','velocity'],
        state_interfaces=['position','velocity'], allow_partial_joints_goal=False,
        action_monitor_rate=50., state_publish_rate=100.,
        constraints=dict(stopped_velocity_tolerance=0., goal_time=2.0), use_sim_time=True)}
    controllers.write_text(yaml.safe_dump(params))
    finger_geometry=[]
    description = contact_description(description, controllers, cfg['finger_joint_damping_nm_s'],
        cfg['gripper_coarse_velocity_rad_s'],cfg['gripper_fine_velocity_rad_s'],cfg['gripper_fine_start_rad'],finger_geometry,
        cfg['gripper_gear_stiffness_nm_rad'],cfg['gripper_motor_stiffness_nm_rad'],cfg['gripper_transmission'],
        max([cfg['joint_velocity_rad_s']]+list(cfg.get('joint_velocity_overrides_rad_s',{}).values())),cfg.get('braking_acceleration_rad_s2',.5),cfg.get('finger_velocity_limit_rad_s',.05),
        cfg.get('gripper_motor_torque_limit_nm',.35), motion_arms=motion_arms,
        grip_contact_friction=cfg.get('grip_contact_friction'))
    probe = None
    if cfg.get('seek_contact'):
        from .seek_contact import SeekContact, add_surface_patch
        probe = SeekContact.from_record(cfg['seek_contact'])
    if cfg.get('drawing_recipe'):
        description = add_virtual_marker_visual(description, probe.tool if probe else None)
    (directory/'robot.urdf').write_text(description)
    sdf = dynamic_sdf(instance, shapes, cfg)
    dims = np.max([v for shape in shapes for v in shape['vertices']],axis=0)
    if surface_offset_m:
        if probe is None or surface_offset_m != .002:
            raise ValueError('Unsupported contact fixture offset')
        sdf = add_surface_patch(sdf, probe, dims, surface_offset_m)
    (directory/'carton.sdf').write_text(sdf)
    world = ET.Element('sdf', version='1.9'); w = ET.SubElement(world, 'world', name='uwa_grasp_lab')
    physics=ET.SubElement(w,'physics', name='default', type='ignored')
    ET.SubElement(physics,'max_step_size').text=str(cfg.get('physics_step_s',.001))
    ET.SubElement(physics,'real_time_factor').text=str(cfg['simulation_real_time_factor'])
    for filename,name in [('physics','Physics'),('user-commands','UserCommands'),('scene-broadcaster','SceneBroadcaster'),('contact','Contact')]:
        plugin=ET.SubElement(w,'plugin',filename='gz-sim-'+filename+'-system',name='gz::sim::systems::'+name)
        if filename=='physics':ET.SubElement(ET.SubElement(plugin,'engine'),'filename').text=str(engine)
    ET.SubElement(w,'gravity').text='0 0 -9.81'
    visual_scene=ET.SubElement(w,'scene');ET.SubElement(visual_scene,'ambient').text='.7 .7 .7 1'
    light=ET.SubElement(w,'light',name='grasp_sun',type='directional')
    ET.SubElement(light,'direction').text='-.4 .2 -.9';ET.SubElement(light,'diffuse').text='.9 .9 .9 1'
    floor=ET.SubElement(w,'model',name='task_floor');ET.SubElement(floor,'static').text='true'
    floor_link=ET.SubElement(floor,'link',name='floor')
    plane=ET.SubElement(ET.SubElement(ET.SubElement(floor_link,'collision',name='floor'),'geometry'),'plane')
    ET.SubElement(plane,'normal').text='0 0 1';ET.SubElement(plane,'size').text='30 30'
    from uwa_cell_gazebo.overview import camera_config, camera_keys, model_sdf, transforms
    overview_layout=deepcopy(layout)
    overview_layout['overview_camera'].update(width=2000,height=1500,rate=10.)
    external_poses = {}
    for key in camera_keys(overview_layout):
        camera = camera_config(overview_layout, key)
        model = ET.fromstring(model_sdf(camera)).find('model')
        if key == 'oak4':
            model.set('name', 'uwa_grasp_oak')
            joint = ET.SubElement(model, 'joint', name='fixed_camera_tripod', type='fixed')
            ET.SubElement(joint, 'parent').text = 'rgb_camera'
            ET.SubElement(joint, 'child').text = 'tripod'
        w.append(model)
        external_poses[key] = transforms(camera)[1]
    if force_backend is not None:
        observer=ET.SubElement(w,'plugin',filename=str(force_backend),name='uwa_cell_tasks::ForceTelemetry')
        ET.SubElement(observer,'ros_namespace').text='/uwa_grasp_validation'
        ET.SubElement(observer,'object_model').text='uwa_grasp_carton'
        watched=[a+'_'+j+'_joint' for a in ARMS for j in ('shoulder_pan','wrist_3')]
        if probe:
            watched = [probe.sensor_joint]
            ET.SubElement(observer,'probe_joint').text = probe.sensor_joint
            ET.SubElement(observer,'position_joints').text = ' '.join(j for a in motion_arms for j in joint_names(a))
        ET.SubElement(observer,'joints').text=' '.join(watched)
    (directory/'world.sdf').write_text(ET.tostring(world,encoding='unicode'))
    from ament_index_python.packages import get_package_prefix
    backend=Path(get_package_prefix('uwa_cell_tasks'))/'lib/libcontact_gripper.so'
    clock_bridge=Path(get_package_prefix('uwa_cell_tasks'))/'lib/uwa_cell_tasks/task_clock_bridge'
    from match_cooperative_handling import rigid_object
    from uwa_cell_motion import node as motion_node
    from ament_index_python.packages import get_package_share_directory
    sources=set(Path(__file__).resolve().parent.glob('*.py'))
    sources.add(Path(rigid_object.__file__).resolve())
    sources.add(Path(motion_node.__file__).resolve())
    if 'grip_contact_friction' in cfg:
        sources.add(backend.with_name('libgrip_friction.so').resolve())
    if cfg.get('drawing_recipe'):
        sources.add(Path(cfg['drawing_recipe']).resolve())
    # Bind the local dependencies used by offline planning and playback.
    import uwa_cell_control,uwa_cell_calibration,uwa_cell_gazebo,uwa_cell_description
    dependency_groups=[(Path(motion_node.__file__).resolve().parent,
        ('common.py','geometry.py','planning.py')),
        (Path(uwa_cell_control.__file__).resolve().parent,
         ('scan_separation.py','view_geometry.py','parallel_scan.py','parking.py')),
        (Path(uwa_cell_calibration.__file__).resolve().parent,('model.py',)),
        (Path(uwa_cell_gazebo.__file__).resolve().parent,('charuco_views.py','configuration.py','charuco.py','trajectory.py')),
        (Path(uwa_cell_description.__file__).resolve().parent,('configuration.py','calibration_profile.py','scene_assets.py'))]
    for base,files in dependency_groups:
        sources.update(base/name for name in files)
    motion_prefix=Path(get_package_prefix('uwa_cell_motion'))
    sources.add((motion_prefix/'lib/uwa_cell_motion/rrt_worker').resolve())
    sources.add((Path(get_package_share_directory('uwa_cell_motion'))/'config/motion.yaml').resolve())
    sources.add((Path(get_package_share_directory('uwa_cell_tasks'))/'launch/grasp.launch.py').resolve())
    implementation={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(sources)}
    record = seal(dict(schema_version=1, cfg=cfg, object_id=instance['id'],
        asset_id=instance['manifest']['asset_id'],
        asset_manifest_sha256=hashlib.sha256((instance['mesh_file'].parent/'asset.json').read_bytes()).hexdigest(),
        backend_binary=str(backend.resolve()),backend_sha256=hashlib.sha256(backend.read_bytes()).hexdigest(),
        physics_engine_binary=str(engine),physics_engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),
        world_sha256=hashlib.sha256((directory/'world.sdf').read_bytes()).hexdigest(),
        carton_sdf_sha256=hashlib.sha256((directory/'carton.sdf').read_bytes()).hexdigest(),
        clock_bridge_binary=str(clock_bridge.resolve()),clock_bridge_sha256=hashlib.sha256(clock_bridge.read_bytes()).hexdigest(),
        implementation_sha256=implementation,
        implementation_binding_scope='task_and_local_motion_dependencies_v3',
        telemetry_source='native_physics_ecm',
        lift_reference_point_object_m=mass_properties(shapes,cfg['mass_kg'])[0],
        lift_reference_kind='uniform_material_model_centre_of_mass',
        fingertip_collision_models=finger_geometry,
        T_world_object=instance['T_world_object'], asset_sha256=instance['manifest']['files'],
        T_world_overview_optical=external_poses['oak4'], T_world_external_optical=external_poses,
        shapes=shapes, robot_sha256=hashlib.sha256(description.encode()).hexdigest(),
        controllers_sha256=hashlib.sha256(controllers.read_bytes()).hexdigest(),
        mass_and_friction_measured=False, contact_model=('torque-limited motor with native parallel gear constraints'
            if cfg['gripper_transmission']=='native_gear' else 'experimental force-limited elastic gear approximation')))
    if probe:
        table = layout['tables']['right']
        record = seal(dict(record, seek_support_height_m=float(table['height']+table['xyz'][2]),
                           fixture_surface_offset_m=surface_offset_m))
    if force_backend is not None:
        record=seal(dict(record,force_backend_binary=str(force_backend),
            force_backend_sha256=hashlib.sha256(force_backend.read_bytes()).hexdigest(),
            force_observation=dict(contact_body_attribution_trusted=False,
                contact_loads='Unsigned normal/tangential load per unique collision pair; physics-step peaks and10ms integrals.',
                joint_reactions='Joint-frame SI forces/torques; idealized arm actuation remains unqualified.',
                pad_load_reference_source='User report2026-11-16, per jaw/wall patch; no measured failure limit.')))
    write_json(directory/'scene.json', record)
    return record


def inherit_pad_adjacency(model,semantic_path=None):
    """Fixed pad parts inherit the existing four-bar hinge exemption.

    The original model already permits inner-knuckle/fingertip contact at
    their shared mechanical hinge. No environment/interarm exemption added.
    """
    semantic=ET.parse(semantic_path) if semantic_path is not None else None
    for arm in ARMS:
        for side in ('left','right'):
            pad=arm+'_robotiq_85_'+side+'_finger_tip_pad_link'
            knuckle=arm+'_robotiq_85_'+side+'_inner_knuckle_link'
            model.scene.allowed_collision_matrix.set_entry(pad,knuckle,True)
            if semantic is not None:
                ET.SubElement(semantic.getroot(),'disable_collisions',link1=pad,link2=knuckle,
                    reason='Fixed pad inherits original fingertip hinge adjacency')
    # Native RRT runs in a separate process and loads this SRDF. Its collision
    # semantics must match the in-memory Python validator exactly.
    if semantic is not None:semantic.write(semantic_path,encoding='unicode')


def apply_object(model, scene, world_object, *, touching=False):
    """Explicit object plus only the intended fingertip contact exemptions."""
    from moveit_msgs.msg import CollisionObject
    from shape_msgs.msg import Mesh, MeshTriangle
    from geometry_msgs.msg import Point, Pose
    t=np.asarray(world_object)
    cached=getattr(model,'_task_object_cache',None)
    if cached is not None and cached[0]==scene['sha256'] and np.allclose(cached[1],t,atol=1e-10,rtol=0):
        for arm in ARMS:
            for side in ('left','right'):
                model.scene.allowed_collision_matrix.set_entry(arm+'_robotiq_85_'+side+'_finger_tip_pad_link',scene['object_id'],touching)
        return
    obj = CollisionObject(); obj.header.frame_id='world'; obj.id=scene['object_id']
    t=np.asarray(world_object); q=Rotation.from_matrix(t[:3,:3]).as_quat()
    for shape in scene['shapes']:
        mesh=Mesh(); mesh.vertices=[Point(x=float(v[0]),y=float(v[1]),z=float(v[2])) for v in shape['vertices']]
        mesh.triangles=[MeshTriangle(vertex_indices=face) for face in shape['triangles']]
        pose=Pose(); pose.position.x,pose.position.y,pose.position.z=map(float,t[:3,3])
        pose.orientation.x,pose.orientation.y,pose.orientation.z,pose.orientation.w=map(float,q)
        obj.meshes.append(mesh); obj.mesh_poses.append(pose)
    obj.operation=CollisionObject.ADD; model.scene.apply_collision_object(obj)
    model._task_object_cache=(scene['sha256'],t.copy())
    for arm in ARMS:
        for side in ('left','right'):
            model.scene.allowed_collision_matrix.set_entry(arm+'_robotiq_85_'+side+'_finger_tip_pad_link',obj.id,touching)


def verify_scene(directory):
    import json
    from urllib.parse import urlparse,unquote
    directory=Path(directory)
    scene=verify(json.loads((directory/'scene.json').read_text()))
    if 'backend_sha256' not in scene:raise ValueError('Unbound development scene; prepare a new scene')
    if not scene.get('implementation_sha256'):raise ValueError('Unbound task implementation; prepare and relaunch the scene')
    for path,expected in scene['implementation_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Task implementation changed; prepare and relaunch the scene')
    if hashlib.sha256(Path(scene['backend_binary']).read_bytes()).hexdigest()!=scene['backend_sha256']:
        raise ValueError('Contact backend changed; prepare and relaunch the scene')
    if scene.get('force_backend_binary') and hashlib.sha256(Path(scene['force_backend_binary']).read_bytes()).hexdigest()!=scene['force_backend_sha256']:
        raise ValueError('Force observer changed; prepare and relaunch the scene')
    if hashlib.sha256(Path(scene['clock_bridge_binary']).read_bytes()).hexdigest()!=scene['clock_bridge_sha256']:
        raise ValueError('Clock backend changed; prepare and relaunch the scene')
    if hashlib.sha256(Path(scene['physics_engine_binary']).read_bytes()).hexdigest()!=scene['physics_engine_sha256']:
        raise ValueError('Physics engine changed; prepare and relaunch the scene')
    for filename,key in [('world.sdf','world_sha256'),('carton.sdf','carton_sdf_sha256')]:
        if hashlib.sha256((directory/filename).read_bytes()).hexdigest()!=scene[key]:
            raise ValueError('Scene physics description changed; prepare a new scene')
    if hashlib.sha256((directory/'model/controllers.yaml').read_bytes()).hexdigest()!=scene['controllers_sha256']:
        raise ValueError('Scene controller configuration changed; prepare a new scene')
    if hashlib.sha256((directory/'robot.urdf').read_bytes()).hexdigest()!=scene['robot_sha256']:
        raise ValueError('Scene robot description changed; prepare a new scene')
    for shape in scene['shapes']:
        path=Path(unquote(urlparse(shape['uri']).path))
        if hashlib.sha256(path.read_bytes()).hexdigest()!=shape['sha256']:
            raise ValueError('Contact geometry changed; prepare a new scene')
    return scene

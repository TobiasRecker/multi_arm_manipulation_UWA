"""Shared OAK CAD and an illustrative tripod for Gazebo and RViz.

Visual geometry only. The stand is a local design, not a measured collision
model; its height follows the optical pose without changing that pose.
"""
from dataclasses import dataclass
from pathlib import Path
import math
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

MESH = 'meshes/visual/oak4_pro/oak4_pro.stl'
BODY = (.32, .35, .39, 1.)
TUBE = (.25, .28, .33, 1.)
METAL = (.62, .65, .69, 1.)
RUBBER = (.045, .055, .07, 1.)
ACCENT = (.05, .48, .63, 1.)


@dataclass(frozen=True)
class Visual:
    name: str
    pose: np.ndarray
    kind: str
    size: tuple
    color: tuple
    resource: str = ''


def transform(xyz, rotation=None):
    pose = np.eye(4)
    pose[:3, 3] = xyz
    if rotation is not None:
        pose[:3, :3] = rotation
    return pose


def tube(name, start, end, radius, color):
    start, end = np.asarray(start, float), np.asarray(end, float)
    vector = end - start
    length = np.linalg.norm(vector)
    if length < 1e-6:
        raise ValueError('Tripod segment must have positive length')
    z = vector / length
    reference = [0., 1., 0.] if abs(z[1]) < .9 else [1., 0., 0.]
    x = np.cross(reference, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return Visual(name, transform((start+end)/2, np.column_stack((x,y,z))),
                  'cylinder', (radius, float(length)), color)


def camera_and_tripod(sensor_pose):
    """World poses, sensor axes +X forward/+Y left/+Z up, all lengths in m."""
    sensor_pose = np.asarray(sensor_pose, float)
    from ament_index_python.packages import get_package_share_directory
    resource = (Path(get_package_share_directory('uwa_cell_description')) / MESH).as_uri()
    visuals = [Visual('oak4_pro_cad', sensor_pose, 'mesh', (1., 1., 1.), BODY, resource)]
    # Approximate underside of housing in the normalized mesh frame. This visual
    # mounting offset is independent of the accepted optical extrinsics.
    plate = sensor_pose @ transform([-.035, 0., -.025])
    visuals.append(Visual('quick_release_plate', plate, 'box', (.065, .085, .008), METAL))
    head = plate[:3, 3].copy()
    head[2] -= .055
    x, y, z = head
    if z <= .25:
        raise ValueError('Camera is too low for the illustrative tripod')
    hub_z = min(1.05, .62*z)
    spread = min(.52, max(.30, .34*z))
    visuals.append(tube('pan_head', [x,y,z-.018], [x,y,z+.018], .042, RUBBER))
    visuals.append(tube('tilt_head', head+[-.03,0,.025], head+[.03,0,.025], .025, ACCENT))
    visuals.append(tube('centre_column', [x,y,hub_z-.08], [x,y,z-.018], .018, METAL))
    visuals.append(tube('tripod_crown', [x,y,hub_z-.045], [x,y,hub_z+.045], .052, RUBBER))
    visuals.append(tube('column_lock', [x,y,hub_z+.025], [x,y,hub_z+.055], .029, ACCENT))
    for index in range(3):
        angle = math.pi/6 + index*2*math.pi/3
        radial = np.array([math.cos(angle), math.sin(angle), 0.])
        top = np.array([x,y,hub_z]) + .045*radial
        foot = np.array([x,y,.045]) + spread*radial
        direction = foot-top
        for section, (a,b,radius,color) in enumerate(((0.,.40,.020,TUBE),(.35,.73,.016,METAL),(.68,1.,.012,TUBE))):
            visuals.append(tube(f'leg_{index}_section_{section}', top+a*direction,
                                top+b*direction, radius, color))
        for clamp, fraction in enumerate((.38,.71)):
            point = top + fraction*direction
            d = direction / np.linalg.norm(direction) * .018
            visuals.append(tube(f'leg_{index}_clamp_{clamp}', point-d, point+d, .025, RUBBER))
        foot_pose = transform([foot[0],foot[1],.0225], Rotation.from_euler('z',angle).as_matrix())
        visuals.append(Visual(f'leg_{index}_rubber_foot', foot_pose, 'box', (.08,.055,.045), RUBBER))
        brace_end = top + .62*direction
        visuals.append(tube(f'spreader_{index}', [x,y,hub_z*.55], brace_end, .006, METAL))
    return visuals


def add_visual(parent, visual, reference=None):
    pose = visual.pose if reference is None else np.linalg.inv(reference) @ visual.pose
    item = ET.SubElement(parent, 'visual', name=visual.name)
    rpy = Rotation.from_matrix(pose[:3,:3]).as_euler('xyz')
    ET.SubElement(item,'pose').text = ' '.join(map(str,[*pose[:3,3],*rpy]))
    geometry = ET.SubElement(item,'geometry')
    shape = ET.SubElement(geometry,visual.kind)
    if visual.kind == 'box':
        ET.SubElement(shape,'size').text = ' '.join(map(str,visual.size))
    elif visual.kind == 'cylinder':
        ET.SubElement(shape,'radius').text = str(visual.size[0])
        ET.SubElement(shape,'length').text = str(visual.size[1])
    else:
        ET.SubElement(shape,'uri').text = visual.resource
        ET.SubElement(shape,'scale').text = ' '.join(map(str,visual.size))
    material = ET.SubElement(item,'material')
    for key in ('ambient','diffuse'):
        ET.SubElement(material,key).text = ' '.join(map(str,visual.color))


def append_sdf_visuals(model, camera_link, sensor_pose):
    visuals = camera_and_tripod(sensor_pose)
    add_visual(camera_link, visuals[0], sensor_pose)
    stand = ET.SubElement(model,'link',name='tripod')
    for visual in visuals[1:]:
        add_visual(stand,visual)


def sdf_visual_markers(sdf):
    """Read exactly the Gazebo visuals, including meshes and cylindrical tubes."""
    from visualization_msgs.msg import Marker
    def pose_matrix(text):
        xyzrpy = np.fromstring(text or '0 0 0 0 0 0',sep=' ')
        return transform(xyzrpy[:3],Rotation.from_euler('xyz',xyzrpy[3:]).as_matrix())
    model = ET.fromstring(sdf).find('model')
    model_pose = pose_matrix(model.findtext('pose'))
    result = []
    for link in model.findall('link'):
        parent = model_pose @ pose_matrix(link.findtext('pose'))
        for visual in link.findall('visual'):
            pose = parent @ pose_matrix(visual.findtext('pose'))
            marker = Marker(ns='oak_overview',id=len(result)+1)
            marker.header.frame_id = 'world'
            marker.pose.position.x,marker.pose.position.y,marker.pose.position.z = pose[:3,3].tolist()
            q = Rotation.from_matrix(pose[:3,:3]).as_quat().tolist()
            marker.pose.orientation.x,marker.pose.orientation.y,marker.pose.orientation.z,marker.pose.orientation.w = q
            geometry = visual.find('geometry')
            if geometry.find('box') is not None:
                marker.type = Marker.CUBE
                scale = list(map(float,geometry.findtext('box/size').split()))
            elif geometry.find('cylinder') is not None:
                marker.type = Marker.CYLINDER
                radius = float(geometry.findtext('cylinder/radius'))
                scale = [2*radius,2*radius,float(geometry.findtext('cylinder/length'))]
            else:
                marker.type = Marker.MESH_RESOURCE
                marker.mesh_resource = geometry.findtext('mesh/uri')
                marker.mesh_use_embedded_materials = False
                scale = list(map(float,geometry.findtext('mesh/scale').split()))
            marker.scale.x,marker.scale.y,marker.scale.z = scale
            marker.color.r,marker.color.g,marker.color.b,marker.color.a = map(float,visual.findtext('material/diffuse').split())
            result.append(marker)
    return result

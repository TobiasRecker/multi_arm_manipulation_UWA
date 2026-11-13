"""Static OAK overview using the shared accepted registration when available."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import cv2
from scipy.spatial.transform import Rotation
import yaml

from .configuration import default_layout_path, nominal_layout_path, load_layout, number, vector
from .charuco import table_board_transform
from uwa_cell_description.overview_profile import R_SENSOR_OPTICAL
from .overview_visuals import append_sdf_visuals

MODEL = 'uwa_oak_overview'
FRAME = 'oak_overview_rgb_optical_frame'
TOPIC = '/uwa_cell/oak_overview/rgb'


def camera_config(layout):
    defaults = yaml.safe_load(nominal_layout_path().read_text())['overview_camera']
    supplied = layout.get('overview_camera', {})
    if not isinstance(supplied, dict) or set(supplied) - set(defaults):
        raise ValueError('overview_camera must contain only known settings')
    cfg = {**defaults, **supplied}
    if not isinstance(cfg['enabled'], bool):
        raise ValueError('overview_camera.enabled must be boolean')
    for key in ('xyz', 'look_at'):
        cfg[key] = vector(cfg[key], 3, f'overview_camera.{key}')
    if cfg['xyz'][2] <= .2 or np.linalg.norm(np.subtract(cfg['xyz'], cfg['look_at'])) < .01:
        raise ValueError('Camera must be above ground and look at a different point')
    cfg['roll'] = number(cfg['roll'], 'overview_camera.roll')
    for key in ('rate', 'horizontal_fov', 'near', 'far'):
        cfg[key] = number(cfg[key], f'overview_camera.{key}', positive=True)
    if cfg['horizontal_fov'] >= math.pi or cfg['near'] >= cfg['far'] or cfg['rate'] > 60:
        raise ValueError('Invalid overview FOV, clipping interval or rate')
    for key in ('width', 'height'):
        if isinstance(cfg[key], bool) or not isinstance(cfg[key], int) or not 64 <= cfg[key] <= 8192:
            raise ValueError(f'overview_camera.{key} must be an integer in [64,8192]')
    measured = layout.get('calibration', {}).get('overview_camera')
    if measured:
        cfg['world_optical'] = measured['registration']['T_world_oak_optical']
        physical = measured['factory']
        k = np.asarray(physical['camera_matrix_8000x6000']).copy()
        k[0] *= cfg['width']/8000
        k[1] *= cfg['height']/6000
        cfg['camera_matrix'] = k.tolist()
        # Jetty's installed Ogre2 backend reports Brown distortion unsupported.
        # Advertise the image geometry actually rendered, never nonzero D for
        # an undistorted image. The physical Rational14 and Brown approximation
        # remain archived separately for real image evaluation / future backends.
        cfg['distortion'] = [0.,0.,0.,0.,0.]
        cfg['rendering_model'] = 'pinhole; installed Ogre2 does not render Brown distortion'
        cfg['horizontal_fov'] = float(2*math.atan(cfg['width']/(2*k[0,0])))
        cfg['quality_status'] = measured['quality_status']
        cfg['world_registration'] = measured['registration']['world_registration']
        cfg['simulation_approximation'] = measured['simulation']
        cfg['real_frame_id'] = measured['registration']['real_optical_frame']
    return cfg


def transforms(cfg):
    """Return world<-Gazebo sensor (+X forward) and world<-REP103 optical."""
    if 'world_optical' in cfg:
        optical = np.asarray(cfg['world_optical'], float)
        sensor = optical.copy()
        sensor[:3,:3] = optical[:3,:3] @ R_SENSOR_OPTICAL.T
        return sensor, optical
    direction = np.subtract(cfg['look_at'], cfg['xyz'])
    yaw = math.atan2(direction[1], direction[0])
    pitch = math.atan2(-direction[2], math.hypot(*direction[:2]))
    sensor = np.eye(4)
    sensor[:3, :3] = Rotation.from_euler('xyz', [cfg['roll'], pitch, yaw]).as_matrix()
    sensor[:3, 3] = cfg['xyz']
    optical = sensor.copy()
    optical[:3, :3] = sensor[:3, :3] @ np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]])
    return sensor, optical


def intrinsic(cfg):
    if 'camera_matrix' in cfg:
        return np.asarray(cfg['camera_matrix'], float)
    f = cfg['width'] / (2 * math.tan(cfg['horizontal_fov'] / 2))
    return np.array([[f, 0, cfg['width']/2], [0, f, cfg['height']/2], [0, 0, 1.]])


def project(points, cfg):
    camera = np.linalg.inv(transforms(cfg)[1])
    points = np.asarray(points)
    local = points @ camera[:3, :3].T + camera[:3, 3]
    pixels = cv2.projectPoints(local.astype(float), np.zeros(3), np.zeros(3),
                              intrinsic(cfg), np.asarray(cfg.get('distortion', np.zeros(5))))[0].reshape(-1,2)
    return pixels, local[:, 2]


def coverage(layout):
    cfg = camera_config(layout)
    result = dict(camera=cfg, calibrated=False, quality_status=cfg.get('quality_status','nominal_design'),
                  occlusion_checked=False, tables={}, boards={})
    for table_id, t in layout['tables'].items():
        table = np.eye(4)
        table[:3, :3] = Rotation.from_euler('xyz', t['rpy']).as_matrix()
        table[:3, 3] = t['xyz']
        corners = np.array([[-t['width']/2, -t['length']/2, t['height']],
                            [t['width']/2, -t['length']/2, t['height']],
                            [t['width']/2, t['length']/2, t['height']],
                            [-t['width']/2, t['length']/2, t['height']]])
        corners = corners @ table[:3, :3].T + table[:3, 3]
        pixels, depth = project(corners, cfg)
        inside = ((depth > cfg['near']) & (depth < cfg['far']) &
                  (pixels[:, 0] >= 0) & (pixels[:, 0] < cfg['width']) &
                  (pixels[:, 1] >= 0) & (pixels[:, 1] < cfg['height']))
        result['tables'][table_id] = dict(all_corners_in_frame=bool(inside.all()),
                                         corners_px=pixels.tolist())
        c = layout['charuco']
        board = table.copy()
        board[:3, 3] += table[:3, :3] @ np.array([0, 0, t['height']])
        board = board @ table_board_transform(c, table_id)
        # Measure projected unit squares throughout the pattern, not just centre.
        spans = []
        for x in range(c['squares_x']):
            for y in range(c['squares_y']):
                p = np.array([[x,y,0], [x+1,y,0], [x,y+1,0]]) * c['square_length']
                p = p @ board[:3, :3].T + board[:3, 3]
                q, _ = project(p, cfg)
                spans.extend([np.linalg.norm(q[1]-q[0]), np.linalg.norm(q[2]-q[0])])
        result['boards'][table_id] = dict(min_square_edge_px=float(min(spans)),
            approximate_min_marker_edge_px=float(min(spans)*c['marker_length']/c['square_length']))
    return result


def model_sdf(cfg, *, image_sensors=True):
    root = ET.Element('sdf', version='1.9')
    model = ET.SubElement(root, 'model', name=MODEL)
    ET.SubElement(model, 'static').text = 'true'
    link = ET.SubElement(model, 'link', name='rgb_camera')
    sensor_pose, _ = transforms(cfg)
    rpy = Rotation.from_matrix(sensor_pose[:3, :3]).as_euler('xyz')
    ET.SubElement(link, 'pose').text = ' '.join(map(str, [*sensor_pose[:3,3], *rpy]))
    append_sdf_visuals(model, link, sensor_pose)
    if not image_sensors:return ET.tostring(root,encoding='unicode')
    sensor = ET.SubElement(link, 'sensor', name='oak_rgb', type='camera')
    for key, value in [('always_on','true'), ('update_rate',str(cfg['rate'])),
                       ('topic',TOPIC+'/image_raw'), ('frame_id',FRAME)]:
        ET.SubElement(sensor, key).text = value
    camera = ET.SubElement(sensor, 'camera')
    ET.SubElement(camera, 'horizontal_fov').text = str(cfg['horizontal_fov'])
    image = ET.SubElement(camera, 'image')
    for key, value in [('width',cfg['width']), ('height',cfg['height']), ('format','R8G8B8')]:
        ET.SubElement(image, key).text = str(value)
    clip = ET.SubElement(camera, 'clip')
    for key in ('near','far'):
        ET.SubElement(clip,key).text = str(cfg[key])
    ET.SubElement(camera, 'camera_info_topic').text = TOPIC+'/camera_info'
    if 'camera_matrix' in cfg:
        k = intrinsic(cfg)
        lens = ET.SubElement(camera,'lens')
        ET.SubElement(lens,'type').text = 'gnomonical'
        ET.SubElement(lens,'scale_to_hfov').text = 'false'
        intrinsics = ET.SubElement(lens,'intrinsics')
        for key,value in zip(('fx','fy','cx','cy','s'),(k[0,0],k[1,1],k[0,2],k[1,2],k[0,1])):
            ET.SubElement(intrinsics,key).text = str(value)
        if any(cfg['distortion']):
            distortion = ET.SubElement(camera,'distortion')
            for key,value in zip(('k1','k2','p1','p2','k3'),cfg['distortion']):
                ET.SubElement(distortion,key).text = str(value)
            ET.SubElement(distortion,'center').text = f'{k[0,2]/cfg["width"]} {k[1,2]/cfg["height"]}'
    return ET.tostring(root, encoding='unicode')


def main():
    parser = argparse.ArgumentParser(description='Predict OAK overview coverage; no occlusion test')
    parser.add_argument('--layout', type=Path, default=default_layout_path())
    args = parser.parse_args()
    print(json.dumps(coverage(load_layout(args.layout)), indent=2))

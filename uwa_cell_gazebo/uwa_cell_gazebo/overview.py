"""Static OAK4 overview design: nominal pinhole camera, not measured extrinsics."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation
import yaml

from .configuration import default_layout_path, load_layout, number, vector
from .charuco import table_board_transform

MODEL = 'uwa_oak_overview'
FRAME = 'oak_overview_rgb_optical_frame'
TOPIC = '/uwa_cell/oak_overview/rgb'


def camera_config(layout):
    defaults = yaml.safe_load(default_layout_path().read_text())['overview_camera']
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
    return cfg


def transforms(cfg):
    """Return world<-Gazebo sensor (+X forward) and world<-REP103 optical."""
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
    f = cfg['width'] / (2 * math.tan(cfg['horizontal_fov'] / 2))
    return np.array([[f, 0, cfg['width']/2], [0, f, cfg['height']/2], [0, 0, 1.]])


def project(points, cfg):
    camera = np.linalg.inv(transforms(cfg)[1])
    points = np.asarray(points)
    local = points @ camera[:3, :3].T + camera[:3, 3]
    pixels = local @ intrinsic(cfg).T
    return pixels[:, :2] / pixels[:, 2:3], local[:, 2]


def coverage(layout):
    cfg = camera_config(layout)
    result = dict(camera=cfg, calibrated=False, occlusion_checked=False, tables={}, boards={})
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


def model_sdf(cfg):
    root = ET.Element('sdf', version='1.9')
    model = ET.SubElement(root, 'model', name=MODEL)
    ET.SubElement(model, 'static').text = 'true'
    link = ET.SubElement(model, 'link', name='rgb_camera')
    sensor_pose, _ = transforms(cfg)
    rpy = Rotation.from_matrix(sensor_pose[:3, :3]).as_euler('xyz')
    ET.SubElement(link, 'pose').text = ' '.join(map(str, [*cfg['xyz'], *rpy]))
    # Approximate housing behind the optical centre. No proprietary CAD claimed.
    def box(parent, name, pose, size, color):
        visual = ET.SubElement(parent, 'visual', name=name)
        ET.SubElement(visual, 'pose').text = pose
        geometry = ET.SubElement(visual, 'geometry')
        ET.SubElement(ET.SubElement(geometry, 'box'), 'size').text = size
        material = ET.SubElement(visual, 'material')
        for key in ('ambient', 'diffuse'):
            ET.SubElement(material, key).text = color
    box(link, 'oak_housing', '-0.035 0 0 0 0 0', '.07 .16 .055', '.15 .18 .22 1')
    for i, y in enumerate([-.06, 0, .06]):
        box(link, f'lens_{i}', f'0 {y} 0 0 0 0', '.004 .022 .022', '.03 .05 .08 1')
    tripod = ET.SubElement(model, 'link', name='tripod')
    x,y,z = cfg['xyz']
    ET.SubElement(tripod, 'pose').text = f'{x} {y} 0 0 0 0'
    box(tripod, 'mast', f'0 0 {z/2} 0 0 0', f'.035 .035 {z}', '.22 .23 .25 1')
    for i in range(3):
        a = i*2*math.pi/3
        box(tripod, f'foot_{i}', f'{.2*math.cos(a)} {.2*math.sin(a)} .035 0 0 {a}',
            '.45 .035 .05', '.22 .23 .25 1')
    # Tripod is visual-only until included in the planning collision scene.
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
    return ET.tostring(root, encoding='unicode')


def main():
    parser = argparse.ArgumentParser(description='Predict OAK overview coverage; no occlusion test')
    parser.add_argument('--layout', type=Path, default=default_layout_path())
    args = parser.parse_args()
    print(json.dumps(coverage(load_layout(args.layout)), indent=2))

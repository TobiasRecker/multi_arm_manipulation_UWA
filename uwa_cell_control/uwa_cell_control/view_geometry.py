"""Offline visibility estimates from conservative URDF collision-body bounds.

No ROS command clients. Mesh bounding boxes intentionally overestimate occlusion;
these scores are design comparisons, not image recognition or collision checks.
"""
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from scipy.spatial.transform import Rotation


def origin(element):
    matrix = np.eye(4)
    if element is not None:
        matrix[:3, 3] = np.fromstring(element.get('xyz', '0 0 0'), sep=' ')
        matrix[:3, :3] = Rotation.from_euler(
            'xyz', np.fromstring(element.get('rpy', '0 0 0'), sep=' ')).as_matrix()
    return matrix


def stl_bounds(path):
    data = Path(path).read_bytes()
    if len(data) >= 84 and len(data) == 84 + 50 * struct.unpack_from('<I', data, 80)[0]:
        dtype = np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attr', '<u2')])
        vertices = np.frombuffer(data, dtype=dtype, offset=84)['vertices'].reshape(-1, 3)
    else:
        vertices = np.asarray([list(map(float, line.split()[1:])) for line in
                               data.decode().splitlines() if line.strip().startswith('vertex ')])
    if vertices.size == 0 or not np.isfinite(vertices).all():
        raise ValueError('Invalid STL visibility geometry')
    return np.asarray([vertices.min(axis=0), vertices.max(axis=0)])


def segment_box_hits(eye, targets, world_box, bounds, near_clip_m=.005):
    """Finite segments with5mm near clipping for approximate optical mounts."""
    inverse = np.linalg.inv(world_box)
    start = inverse[:3, :3] @ np.asarray(eye) + inverse[:3, 3]
    end = np.asarray(targets) @ inverse[:3, :3].T + inverse[:3, 3]
    direction = end - start
    parallel = np.abs(direction) < 1e-12
    outside = parallel & ((start < bounds[0]) | (start > bounds[1]))
    safe = np.where(parallel, 1., direction)
    a, b = (bounds[0] - start) / safe, (bounds[1] - start) / safe
    near = np.where(parallel, -np.inf, np.minimum(a, b)).max(axis=1)
    far = np.where(parallel, np.inf, np.maximum(a, b)).min(axis=1)
    minimum = near_clip_m / np.maximum(np.linalg.norm(direction, axis=1), 1e-12)
    return (~outside.any(axis=1) & (np.maximum(near, minimum) <=
                                    np.minimum(far, 1. - 1e-5)))


def project_points(points, world_camera, matrix, distortion, size, margin=0):
    inverse = np.linalg.inv(world_camera)
    local = np.asarray(points) @ inverse[:3, :3].T + inverse[:3, 3]
    pixels = cv2.projectPoints(local, np.zeros(3), np.zeros(3),
                              np.asarray(matrix), np.asarray(distortion))[0].reshape(-1, 2)
    inside = ((local[:, 2] > .02) & np.isfinite(pixels).all(axis=1) &
              (pixels[:, 0] >= margin) & (pixels[:, 0] < size[0] - margin) &
              (pixels[:, 1] >= margin) & (pixels[:, 1] < size[1] - margin))
    return pixels, inside


class VisibilityModel:
    def __init__(self, description, arm_ids):
        root = ET.fromstring(description)
        self.joints = []
        pending = list(root.findall('joint'))
        known = {'world'}
        while pending:
            ready = [j for j in pending if j.find('parent').get('link') in known]
            if not ready:
                raise ValueError('URDF must have a connected world tree')
            for joint in ready:
                child = joint.find('child').get('link')
                axis = joint.find('axis')
                axis = np.fromstring(axis.get('xyz'), sep=' ') if axis is not None else np.array([1., 0, 0])
                self.joints.append((joint.get('name'), joint.get('type'),
                                    joint.find('parent').get('link'), child,
                                    origin(joint.find('origin')), axis, joint.find('mimic')))
                known.add(child)
                pending.remove(joint)
        self.boxes = []
        for link in root.findall('link'):
            name = link.get('name')
            arm = next((a for a in arm_ids if name.startswith(a + '_')), None)
            if arm is None:
                continue
            for collision in link.findall('collision'):
                geometry = list(collision.find('geometry'))[0]
                if geometry.tag == 'mesh':
                    path = geometry.get('filename').removeprefix('file://')
                    bounds = stl_bounds(path)
                    scale = np.fromstring(geometry.get('scale', '1 1 1'), sep=' ')
                    bounds = np.sort(bounds * scale, axis=0)
                elif geometry.tag == 'box':
                    half = np.fromstring(geometry.get('size'), sep=' ') / 2
                    bounds = np.array([-half, half])
                elif geometry.tag in ('cylinder', 'sphere'):
                    radius = float(geometry.get('radius'))
                    height = float(geometry.get('length')) / 2 if geometry.tag == 'cylinder' else radius
                    half = np.array([radius, radius, height])
                    bounds = np.array([-half, half])
                else:
                    raise ValueError('Unsupported visibility geometry: ' + geometry.tag)
                self.boxes.append((arm, name, origin(collision.find('origin')), bounds))

    def frames(self, positions):
        frames, values = {'world': np.eye(4)}, dict(positions)
        for name, kind, parent, child, fixed, axis, mimic in self.joints:
            value = values.get(name, 0.)
            if mimic is not None:
                value = (values.get(mimic.get('joint'), 0.) * float(mimic.get('multiplier', '1')) +
                         float(mimic.get('offset', '0')))
            values[name] = value
            moving = np.eye(4)
            if kind in ('revolute', 'continuous'):
                moving[:3, :3] = Rotation.from_rotvec(axis * value).as_matrix()
            elif kind == 'prismatic':
                moving[:3, 3] = axis * value
            frames[child] = frames[parent] @ fixed @ moving
        return frames

    def blocked(self, eye, targets, frames, *, arms=None, ignore_links=()):
        blocked = np.zeros(len(targets), dtype=bool)
        for arm, name, fixed, bounds in self.boxes:
            if (arms is None or arm in arms) and name not in ignore_links:
                blocked |= segment_box_hits(eye, targets, frames[name] @ fixed, bounds)
        return blocked

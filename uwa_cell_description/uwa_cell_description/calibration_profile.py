"""Shared, immutable measured optics/kinematics; never infer a world anchor.

Only optical frames are measured by hand-eye. Housing collision geometry remains
nominal; fitting an optical axis does not measure the camera casing's pose.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation


def rigid(value):
    matrix = np.asarray(value, float)
    if (matrix.shape != (4, 4) or not np.isfinite(matrix).all() or
            not np.allclose(matrix[3], [0, 0, 0, 1]) or
            not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-6) or
            not np.isclose(np.linalg.det(matrix[:3, :3]), 1., atol=1e-6)):
        raise ValueError('Calibration must contain a finite rigid transform')
    return matrix


def read_artifact(directory, reference):
    path = (directory / reference['file']).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError('Calibration artifact must stay within its profile directory')
    if hashlib.sha256(path.read_bytes()).hexdigest() != reference['sha256']:
        raise ValueError(f'Calibration artifact checksum mismatch: {path}')
    return path


def load_profile(path):
    path = Path(path).expanduser().resolve()
    profile = json.loads(path.read_text())
    if profile.get('schema_version') != 1 or profile.get('kind') != 'hardware':
        raise ValueError('Expected a version-1 hardware calibration bundle')
    if not profile.get('robots') or set(profile['robots']) - {'left_front', 'left_rear', 'right_front', 'right_rear'}:
        raise ValueError('Unknown or empty calibration robot set')
    if 'named_poses' in profile:
        poses = json.loads(read_artifact(path.parent, profile['named_poses']).read_text())
        if poses.get('unit') != 'rad' or poses.get('schema_version') != 1:
            raise ValueError('Named poses require explicit radian units')
        from .configuration import joint_names
        for pose in poses['poses'].values():
            values = np.asarray(pose['positions'], float)
            if (pose['robot_id'] not in profile['robots'] or
                    pose['joint_names'] != joint_names(pose['robot_id']) or
                    values.shape != (6,) or not np.isfinite(values).all() or
                    pose.get('requires_new_path_check') is not True):
                raise ValueError('Invalid named pose reference')
    for rid, arm in profile['robots'].items():
        if 'kinematics' in arm:
            arm['kinematics_file'] = str(read_artifact(path.parent, arm['kinematics']))
        if 'intrinsics' in arm:
            camera = json.loads(read_artifact(path.parent, arm['intrinsics']).read_text())
            k, d = np.asarray(camera['camera_matrix'], float), np.asarray(camera['distortion'], float)
            size = camera['image_size']
            errors = np.asarray(camera['validation_rms_px'], float)
            if (camera.get('passed') is not True or camera.get('schema_version') != 1 or
                    camera.get('focusAuto') is not False or camera['fit_count'] < 20 or
                    camera['validation_count'] < 6 or errors.size != camera['validation_count'] or
                    k.shape != (3, 3) or d.shape != (5,) or len(size) != 2 or
                    not np.isfinite(k).all() or not np.isfinite(d).all() or
                    not np.isfinite(errors).all() or np.any(errors < 0) or
                    not np.allclose(k[2], [0, 0, 1]) or k[0, 0] <= 0 or k[1, 1] <= 0 or
                    not 0 < k[0, 2] < size[0] or not 0 < k[1, 2] < size[1] or
                    not 0 < camera['fit_rms_px'] <= 1 or
                    np.median(errors) > 1 or max(errors) > 1.5):
                raise ValueError(f'{rid}: invalid independent intrinsic calibration')
            arm['camera'] = camera
        if 'handeye' in arm:
            result = json.loads(read_artifact(path.parent, arm['handeye']).read_text())
            fit = result['robots'][rid]
            q = fit['validation']
            metrics = np.asarray([q['median_reprojection_rms_px'],
                                  q['board_translation_rms_m'], q['board_rotation_rms_deg']])
            if (result.get('passed') is not True or result.get('mode') != 'hardware' or
                    fit.get('passed') is not True or fit['fit_count'] < 12 or
                    fit['validation_count'] < 6 or
                    not 30 <= fit['fit_count'] + fit['validation_count'] <= 80 or
                    not np.isfinite(metrics).all() or np.any(metrics < 0) or
                    np.any(metrics > [1., .005, .5])):
                raise ValueError(f'{rid}: hand-eye calibration failed independent validation')
            matrix = rigid(fit['T_tool0_camera'])
            rigid(fit['T_base_board'])
            if np.linalg.norm(matrix[:3, 3]) > .3:
                raise ValueError('Wrist camera exceeds300mm tool offset')
            if 'camera' not in arm:
                raise ValueError('Hand-eye requires its matching intrinsic profile')
            if any(arm['camera'][key] != fit[key] for key in ('fit_count', 'validation_count')):
                raise ValueError('Hand-eye and intrinsic observation sets do not match')
            arm['fit'] = fit
        if 'rejected_handeye' in arm:
            read_artifact(path.parent, arm['rejected_handeye'])
        if 'camera_info' in arm:
            read_artifact(path.parent, arm['camera_info'])
    profile['file'] = str(path)
    profile['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return profile


def apply_layout(layout, profile):
    layout = deepcopy(layout)
    for rid, arm in profile['robots'].items():
        robot = layout['robots'][rid]
        if robot['type'] != arm['ur_type']:
            raise ValueError(f'{rid}: measured calibration belongs to another robot type')
        if 'kinematics_file' in arm:
            robot['kinematics_file'] = arm['kinematics_file']
        if 'camera' in arm and robot['tools']['camera_enabled']:
            if [robot['tools']['camera_width'], robot['tools']['camera_height']] != arm['camera']['image_size']:
                raise ValueError(f'{rid}: calibrated image mode differs from configured camera size')
    layout['calibration'] = profile
    return layout


def origin(joint, matrix):
    element = joint.find('origin')
    if element is None:
        element = ET.SubElement(joint, 'origin')
    element.set('xyz', ' '.join(map(str, matrix[:3, 3])))
    element.set('rpy', ' '.join(map(str, Rotation.from_matrix(matrix[:3, :3]).as_euler('xyz'))))


def optical_transform(arm, camera_yaw):
    """Housing stays nominal; change only housing->optical fixed joint."""
    mount = np.eye(4)
    mount[:3, :3] = Rotation.from_euler('z', camera_yaw).as_matrix()
    return np.linalg.inv(mount) @ rigid(arm['fit']['T_tool0_camera'])


def apply_description(description, layout):
    if not layout.get('calibration'):
        return description
    root = ET.fromstring(description)
    for rid, arm in layout['calibration']['robots'].items():
        tools = layout['robots'][rid]['tools']
        if not tools['camera_enabled']:
            continue
        sensor = root.find(f"gazebo[@reference='{rid}_wrist_camera_link']/sensor")
        if 'fit' in arm:
            local = optical_transform(arm, tools['camera_yaw'])
            origin(root.find(f"joint[@name='{rid}_wrist_camera_optical_joint']"), local)
            # Gazebo camera +X/+Y/+Z = optical +Z/-X/-Y.
            gz = local.copy()
            gz[:3, :3] = local[:3, :3] @ np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]])
            sensor.find('pose').text = ' '.join(map(str, [*gz[:3, 3], *Rotation.from_matrix(gz[:3, :3]).as_euler('xyz')]))
            # Measured board relation is a reference frame only, never a world/base relocation.
            ET.SubElement(root, 'link', name=rid+'_measured_board_frame')
            joint = ET.SubElement(root, 'joint', name=rid+'_measured_board_joint', type='fixed')
            ET.SubElement(joint, 'parent', link=rid+'_base_link')
            ET.SubElement(joint, 'child', link=rid+'_measured_board_frame')
            origin(joint, rigid(arm['fit']['T_base_board']))
        if 'camera' in arm:
            camera = sensor.find('camera')
            k = np.asarray(arm['camera']['camera_matrix'])
            lens = ET.SubElement(camera, 'lens')
            ET.SubElement(lens, 'type').text = 'gnomonical'
            ET.SubElement(lens, 'scale_to_hfov').text = 'false'
            intrinsics = ET.SubElement(lens, 'intrinsics')
            for key, value in zip(('fx', 'fy', 'cx', 'cy', 's'), (k[0, 0], k[1, 1], k[0, 2], k[1, 2], k[0, 1])):
                ET.SubElement(intrinsics, key).text = str(value)
            distortion = ET.SubElement(camera, 'distortion')
            for key, value in zip(('k1', 'k2', 'p1', 'p2', 'k3'), arm['camera']['distortion']):
                ET.SubElement(distortion, key).text = str(value)
            width, height = arm['camera']['image_size']
            ET.SubElement(distortion, 'center').text = f'{k[0, 2]/width} {k[1, 2]/height}'
    return ET.tostring(root, encoding='unicode')

"""Observe both ChArUco boards and compare image estimates with simulation truth.

Base calibration assumes known intrinsics, camera-to-tool extrinsics, joint
kinematics and board pose in the tabletop frame. It does not estimate those
quantities from one pose. Ground truth is used only after the PnP estimate.
"""
import argparse
import json
import os
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener

from .charuco import detect_pose, pose_error, table_board_transform
from .configuration import ROBOT_IDS, load_layout


def tf_matrix(message):
    t = message.transform
    result = np.eye(4)
    result[:3, :3] = Rotation.from_quat([t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w]).as_matrix()
    result[:3, 3] = [t.translation.x, t.translation.y, t.translation.z]
    return result


def mean_pose(poses):
    result = np.eye(4)
    result[:3, 3] = np.mean([pose[:3, 3] for pose in poses], axis=0)
    result[:3, :3] = Rotation.from_matrix(np.array([pose[:3, :3] for pose in poses])).mean().as_matrix()
    return result


class CharucoCheck(Node):
    def __init__(self, layout, directory):
        super().__init__('charuco_check', namespace='uwa_cell')
        self.layout, self.directory = layout, Path(directory)
        self.images, self.infos, self.processed, self.failures = {}, {}, {}, {}
        self.samples = {rid: [] for rid in ROBOT_IDS}
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.outputs = {}
        for rid in ROBOT_IDS:
            self.create_subscription(Image, f'/uwa_cell/{rid}/wrist_camera/image_raw',
                                     lambda msg, rid=rid: self.images.update({rid: msg}), qos_profile_sensor_data)
            self.create_subscription(CameraInfo, f'/uwa_cell/{rid}/wrist_camera/camera_info',
                                     lambda msg, rid=rid: self.infos.update({rid: msg}), qos_profile_sensor_data)
            self.outputs[rid] = self.create_publisher(
                Image, f'/uwa_cell/{rid}/charuco/image_annotated', qos_profile_sensor_data)

    def lookup(self, parent, child, stamp):
        return tf_matrix(self.buffer.lookup_transform(parent, child, stamp))

    def observe(self, rid):
        if rid not in self.images or rid not in self.infos:
            self.failures[rid] = 'Waiting for image and CameraInfo'
            return
        image, info = self.images[rid], self.infos[rid]
        key = (image.header.stamp.sec, image.header.stamp.nanosec)
        if self.processed.get(rid) == key:
            return
        self.processed[rid] = key
        if image.encoding not in ('rgb8', 'bgr8') or info.header.frame_id != image.header.frame_id:
            self.failures[rid] = 'Unsupported RGB encoding or inconsistent optical frames'
            return
        if (info.width, info.height) != (image.width, image.height):
            self.failures[rid] = 'Image/CameraInfo resolution mismatch'
            return
        pixels = np.frombuffer(image.data, dtype=np.uint8).reshape(image.height, image.step)
        pixels = pixels[:, :image.width*3].reshape(image.height, image.width, 3)
        if image.encoding == 'rgb8':
            pixels = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
        config = self.layout['charuco']
        table = self.layout['robots'][rid]['table']
        detected = detect_pose(pixels, np.array(info.k).reshape(3, 3), np.array(info.d), config, table)
        if detected is None:
            self.failures[rid] = 'Insufficient/non-collinear ChArUco corners on the assigned table board'
            cv2.imwrite(str(self.directory / f'{rid}_latest.png'), pixels)
            return
        stamp = Time.from_msg(image.header.stamp)
        try:
            # base->camera uses only the arm's internal TF chain, not its world mount.
            base_camera = self.lookup(f'{rid}_base_link', image.header.frame_id, stamp)
            camera_board_truth = self.lookup(image.header.frame_id, f'{table}_charuco', stamp)
            table_base_truth = self.lookup(f'{table}_table_top', f'{rid}_base_link', stamp)
            table_board_truth = self.lookup(f'{table}_table_top', f'{table}_charuco', stamp)
        except TransformException as error:
            self.failures[rid] = f'Waiting for timestamp-matched TF: {error}'
            return
        known_board = table_board_transform(config, table)
        # Validate the reference definition separately; it cannot select the PnP pose.
        assert pose_error(known_board, table_board_truth)['translation_m'] < 1e-6
        assert pose_error(known_board, table_board_truth)['rotation_deg'] < 1e-5
        camera_board = detected['T_camera_board']
        table_base = known_board @ np.linalg.inv(camera_board) @ np.linalg.inv(base_camera)
        sample = {'stamp': list(key), 'corners': detected['corners'],
                  'reprojection_rms_px': detected['reprojection_rms_px'],
                  'T_camera_board': camera_board.tolist(),
                  'T_camera_board_ground_truth': camera_board_truth.tolist(),
                  'board_error': pose_error(camera_board, camera_board_truth),
                  'T_table_base_estimate': table_base.tolist(),
                  'T_table_base_ground_truth': table_base_truth.tolist(),
                  'base_error': pose_error(table_base, table_base_truth)}
        self.samples[rid].append(sample)
        annotated = detected['annotated']
        cv2.imwrite(str(self.directory / f'{rid}_detected.png'), annotated)
        output = Image()
        output.header = image.header
        output.height, output.width = annotated.shape[:2]
        output.encoding, output.step, output.data = 'bgr8', annotated.shape[1]*3, annotated.tobytes()
        self.outputs[rid].publish(output)
        self.failures.pop(rid, None)

    def report(self):
        config = self.layout['charuco']
        result = {'transform_convention': 'T_A_B maps B coordinates into A',
                  'opencv_version': cv2.__version__, 'required_samples': config['samples'],
                  'reference_frame': '<table>_table_top',
                  'assumptions': ['Known intrinsics', 'Known camera-to-tool transform',
                                  'Known arm joint kinematics', 'Known board pose in tabletop frame'],
                  'robots': {}, 'relative_bases': {}, 'passed': True}
        estimates = {}
        for rid, samples in self.samples.items():
            passed = len(samples) >= config['samples'] and all(
                s['reprojection_rms_px'] <= config['max_reprojection_error_px'] and
                all(s[k]['translation_m'] <= config['max_translation_error'] and
                    s[k]['rotation_deg'] <= config['max_rotation_error_deg']
                    for k in ('board_error', 'base_error')) for s in samples)
            entry = {'passed': passed, 'sample_count': len(samples), 'samples': samples}
            if samples:
                estimate = mean_pose([np.array(s['T_table_base_estimate']) for s in samples])
                estimates[rid] = estimate
                entry['T_table_base_mean_estimate'] = estimate.tolist()
                entry['mean_base_error'] = pose_error(estimate, np.array(samples[-1]['T_table_base_ground_truth']))
            if rid in self.failures:
                entry['last_failure'] = self.failures[rid]
            result['robots'][rid] = entry
            result['passed'] &= passed
        for table in ('left', 'right'):
            front, rear = f'{table}_front', f'{table}_rear'
            if front not in estimates or rear not in estimates:
                continue
            estimate = np.linalg.inv(estimates[front]) @ estimates[rear]
            truth = (np.linalg.inv(np.array(self.samples[front][-1]['T_table_base_ground_truth'])) @
                     np.array(self.samples[rear][-1]['T_table_base_ground_truth']))
            error = pose_error(estimate, truth)
            passed = (error['translation_m'] <= config['max_translation_error'] and
                      error['rotation_deg'] <= config['max_rotation_error_deg'])
            result['relative_bases'][table] = {'parent': f'{front}_base_link', 'child': f'{rear}_base_link',
                'T_front_rear_estimate': estimate.tolist(), 'T_front_rear_ground_truth': truth.tolist(),
                'error': error, 'passed': passed}
            result['passed'] &= passed
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout')
    parser.add_argument('--output-dir', default='/tmp/uwa-charuco-check')
    parser.add_argument('--timeout', type=float, default=60)
    args = parser.parse_args()
    if os.environ.get('ROS_DOMAIN_ID') != '64':
        parser.error('Source scripts/env.bash: simulation ROS domain 64 required')
    layout = load_layout(args.layout)
    if not layout['charuco']['enabled'] or not all(layout['robots'][rid]['tools']['camera_enabled'] for rid in ROBOT_IDS):
        parser.error('This four-camera check requires both boards and all four cameras enabled')
    directory = Path(args.output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = CharucoCheck(layout, directory)
    try:
        deadline = time.monotonic() + args.timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.05)
            for rid in ROBOT_IDS:
                if len(node.samples[rid]) < layout['charuco']['samples']:
                    node.observe(rid)
            if all(len(s) >= layout['charuco']['samples'] for s in node.samples.values()):
                break
        report = node.report()
        (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        for rid, entry in report['robots'].items():
            print(rid, entry['sample_count'], 'samples;', entry.get('mean_base_error', entry.get('last_failure')))
        print('relative bases:', json.dumps(report['relative_bases'], indent=2))
        print(f"{'PASS' if report['passed'] else 'FAIL'}: {directory / 'report.json'}")
        if not report['passed']:
            raise SystemExit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

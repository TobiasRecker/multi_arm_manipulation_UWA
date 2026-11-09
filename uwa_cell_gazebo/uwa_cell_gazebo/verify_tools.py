"""Check simulated camera streams and tool TFs; optionally move/restore grippers."""
import argparse
import json
import math
import os
from pathlib import Path
import time

import numpy as np
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from trajectory_msgs.msg import JointTrajectoryPoint

from .configuration import ROBOT_IDS, controller_names, gripper_joint, load_layout
from .verify_cell import CellVerification


class ToolVerification(CellVerification):
    def __init__(self, cameras):
        super().__init__()
        self.images, self.infos, self.stamps = {}, {}, {rid: [] for rid in cameras}
        for rid in cameras:
            self.create_subscription(Image, f'/uwa_cell/{rid}/wrist_camera/image_raw',
                                     lambda message, rid=rid: self.on_image(rid, message),
                                     qos_profile_sensor_data)
            self.create_subscription(CameraInfo, f'/uwa_cell/{rid}/wrist_camera/camera_info',
                                     lambda message, rid=rid: self.infos.update({rid: message}),
                                     qos_profile_sensor_data)

    def on_image(self, rid, message):
        self.images[rid] = message
        self.stamps[rid].append(message.header.stamp.sec + message.header.stamp.nanosec * 1e-9)

    def move_gripper(self, rid, position):
        client = ActionClient(self, FollowJointTrajectory,
                             f'/uwa_cell/{rid}_gripper_controller/follow_joint_trajectory')
        try:
            assert client.wait_for_server(timeout_sec=10), f'{rid}: gripper action missing'
            goal = FollowJointTrajectory.Goal()
            goal.trajectory.joint_names = [gripper_joint(rid)]
            point = JointTrajectoryPoint()
            point.positions, point.velocities = [float(position)], [0.0]
            point.time_from_start.sec = 3
            goal.trajectory.points = [point]
            handle = self.future(client.send_goal_async(goal))
            assert handle.accepted, f'{rid}: gripper goal rejected'
            result = self.future(handle.get_result_async(), timeout=25)
            assert result.status == 4 and result.result.error_code == 0, result
            self.until(lambda: abs(self.positions[gripper_joint(rid)] - position) < .03)
        finally:
            client.destroy()

    def check_mimics(self, rid):
        q = self.positions[gripper_joint(rid)]
        for suffix, sign in [('right_knuckle', -1), ('left_inner_knuckle', 1),
                             ('right_inner_knuckle', -1), ('left_finger_tip', -1),
                             ('right_finger_tip', 1)]:
            name = f'{rid}_robotiq_85_{suffix}_joint'
            assert abs(self.positions[name] - sign * q) < .03, (name, self.positions[name], q)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout')
    parser.add_argument('--move', action='store_true', help='Close/open each gripper and restore')
    parser.add_argument('--output')
    parser.add_argument('--images', help='Optional directory for RGB PNG snapshots')
    args = parser.parse_args()
    if os.environ.get('ROS_DOMAIN_ID') != '64':
        parser.error('Source scripts/env.bash first: requires simulation ROS domain 64')
    layout = load_layout(args.layout)
    cameras = [rid for rid in ROBOT_IDS if layout['robots'][rid]['tools']['camera_enabled']]
    grippers = [rid for rid in ROBOT_IDS if layout['robots'][rid]['tools']['gripper'] != 'none']
    rclpy.init()
    node = ToolVerification(cameras)
    try:
        node.until(lambda: all(rid in node.infos and len(node.stamps[rid]) >= 3
                               for rid in cameras)
                   and all(gripper_joint(rid) in node.positions for rid in grippers), timeout=45)
        service = node.create_client(ListControllers, '/uwa_cell/controller_manager/list_controllers')
        assert service.wait_for_service(timeout_sec=10)
        deadline = time.monotonic() + 90
        while True:
            response = node.future(service.call_async(ListControllers.Request()))
            controllers = {c.name: c.state for c in response.controller}
            if all(controllers.get(name) == 'active' for name in controller_names(layout)):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f'Controllers did not become active: {controllers}')
            next_poll = time.monotonic() + .5
            node.until(lambda: time.monotonic() >= next_poll, timeout=2)
        assert all(controllers.get(name) == 'active' for name in controller_names(layout)), controllers
        result = {'controllers': controllers, 'cameras': {}, 'grippers_moved_and_restored': []}
        for rid in cameras:
            cfg, image, info = layout['robots'][rid]['tools'], node.images[rid], node.infos[rid]
            frame = f'{rid}_wrist_camera_optical_frame'
            assert image.header.frame_id == info.header.frame_id == frame
            assert (image.width, image.height) == (cfg['camera_width'], cfg['camera_height'])
            assert (info.width, info.height) == (image.width, image.height)
            assert image.encoding == 'rgb8' and image.step == image.width * 3
            assert len(image.data) == image.step * image.height
            assert node.stamps[rid][-1] > node.stamps[rid][0] > 0
            assert math.isfinite(info.k[0]) and info.k[0] > 0
            expected_fx = image.width / (2 * math.tan(cfg['camera_horizontal_fov'] / 2))
            assert abs(info.k[0] - expected_fx) < 1, (info.k[0], expected_fx)
            node.until(lambda: node.buffer.can_transform(f'{rid}_tool0', frame, Time()))
            tf = node.buffer.lookup_transform(f'{rid}_tool0', frame, Time()).transform
            expected = [-.0357 * math.sin(cfg['camera_yaw']),
                        .0357 * math.cos(cfg['camera_yaw']), -.0001]
            np.testing.assert_allclose([tf.translation.x, tf.translation.y, tf.translation.z],
                                       expected, atol=1e-6)
            pixels = np.asarray(image.data, dtype=np.uint8).reshape(image.height, image.width, 3)
            assert pixels.std() > 1, f'{rid}: blank camera image'
            result['cameras'][rid] = {'size': [image.width, image.height], 'frame': frame,
                                      'advancing_simulation_stamps': True,
                                      'pixel_stddev': float(pixels.std()), 'fx': info.k[0]}
            if args.images:
                from PIL import Image as PillowImage
                directory = Path(args.images)
                directory.mkdir(parents=True, exist_ok=True)
                PillowImage.fromarray(pixels).save(directory / f'{rid}.png')
        for rid in grippers:
            node.until(lambda: all(f'{rid}_robotiq_85_{suffix}_joint' in node.positions
                                   for suffix in ('right_knuckle', 'left_inner_knuckle',
                                                  'right_inner_knuckle', 'left_finger_tip',
                                                  'right_finger_tip')))
            node.check_mimics(rid)
            if args.move:
                before = dict(node.positions)
                original = before[gripper_joint(rid)]
                try:
                    for target in (.65, .15):
                        node.move_gripper(rid, target)
                        node.check_mimics(rid)
                        drift = max(abs(node.positions[j] - q) for j, q in before.items()
                                    if not j.startswith(f'{rid}_robotiq_85_'))
                        assert drift < .01, f'{rid}: unrelated joint moved by {drift}'
                finally:
                    node.move_gripper(rid, original)
                node.check_mimics(rid)
                result['grippers_moved_and_restored'].append(rid)
        text = json.dumps(result, indent=2)
        print(text)
        if args.output:
            Path(args.output).write_text(text + '\n')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

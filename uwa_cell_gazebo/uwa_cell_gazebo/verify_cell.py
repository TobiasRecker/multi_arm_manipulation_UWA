"""Read-only checks by default; --move explicitly tests and restores each simulated arm."""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import time

import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from controller_manager_msgs.srv import ListControllers
from control_msgs.action import FollowJointTrajectory
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint
from tf2_ros import Buffer, TransformListener

from .configuration import ROBOT_IDS, controller_names, joint_names, load_layout


def _blocks(text, field):
    """Yield non-overlapping protobuf-text blocks, skipping their nested blocks."""
    pattern = re.compile(r'(?m)^\s*' + re.escape(field) + r'\s*\{')
    offset = 0
    while match := pattern.search(text, offset):
        start = match.end()
        depth, end = 1, start
        while end < len(text) and depth:
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        if depth:
            raise ValueError('Incomplete Gazebo scene response')
        yield text[start:end - 1]
        offset = end


def gazebo_model_pose():
    """Check actual physics pose, rather than only the nominal robot TF tree."""
    response = subprocess.run([
        'gz', 'service', '-s', '/world/uwa_lab/scene/info', '--reqtype', 'gz.msgs.Empty',
        '--reptype', 'gz.msgs.Scene', '--timeout', '5000', '--req', '',
    ], capture_output=True, text=True, timeout=8, check=True).stdout
    for model in _blocks(response, 'model'):
        name = re.search(r'(?m)^\s*name:\s*"([^"]+)"', model)
        if name is None or name[1] != 'uwa_cell':
            continue
        pose = next(_blocks(model, 'pose'))
        position = next(_blocks(pose, 'position'), '')
        orientation = next(_blocks(pose, 'orientation'), '')
        def values(block):
            return {key: float(value) for key, value in re.findall(
                r'\b([xyzw]):\s*([^\s}]+)', block)}
        xyz, q = values(position), values(orientation)
        return np.array([xyz.get(key, 0.0) for key in 'xyz'] +
                        [q.get(key, 1.0 if key == 'w' else 0.0) for key in 'xyzw'])
    raise RuntimeError('Gazebo did not return the uwa_cell model')


class CellVerification(Node):
    def __init__(self):
        super().__init__('uwa_cell_verification')
        self.positions, self.clock_samples = {}, []
        self.create_subscription(JointState, '/uwa_cell/joint_states', self.on_joints,
                                 qos_profile_sensor_data)
        self.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)

    def on_joints(self, message):
        self.positions.update(zip(message.name, message.position))

    def on_clock(self, message):
        self.clock_samples.append(message.clock.sec + message.clock.nanosec * 1e-9)

    def until(self, condition, timeout=20.0):
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            if condition():
                return
        raise TimeoutError('Timed out waiting for simulated cell telemetry/action')

    def future(self, future, timeout=20.0):
        self.until(future.done, timeout)
        return future.result()

    def base_pose(self, robot_id):
        transform = self.buffer.lookup_transform('world', f'{robot_id}_base_link', Time()).transform
        return np.array([transform.translation.x, transform.translation.y, transform.translation.z])

    def move_and_wait(self, robot_id, target):
        client = ActionClient(self, FollowJointTrajectory,
                              f'/uwa_cell/{robot_id}_trajectory_controller/follow_joint_trajectory')
        try:
            if not client.wait_for_server(timeout_sec=10.0):
                raise RuntimeError(f'Action server missing for {robot_id}')
            goal = FollowJointTrajectory.Goal()
            goal.trajectory.joint_names = joint_names(robot_id)
            point = JointTrajectoryPoint()
            point.positions = [float(value) for value in target]
            point.velocities = [0.0] * 6
            point.time_from_start.sec = 3
            goal.trajectory.points = [point]
            handle = self.future(client.send_goal_async(goal))
            if not handle.accepted:
                raise RuntimeError(f'{robot_id}: trajectory was rejected')
            result = self.future(handle.get_result_async(), timeout=25.0)
            if result.status != 4 or result.result.error_code != 0:
                raise RuntimeError(f'{robot_id}: trajectory failed: {result.result.error_string}')
            self.until(lambda: max(abs(self.positions[j] - target[i])
                                   for i, j in enumerate(joint_names(robot_id))) < 0.03)
        finally:
            client.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout')
    parser.add_argument('--move', action='store_true', help='Test a 0.1-rad wrist move per arm and restore it')
    parser.add_argument('--output')
    args = parser.parse_args()
    # The check deliberately cannot connect to the real cell's ROS domain.
    import os
    if os.environ.get('ROS_DOMAIN_ID') != '64':
        parser.error('Source scripts/env.bash first: verification requires ROS_DOMAIN_ID=64')
    layout = load_layout(args.layout)
    rclpy.init()
    node = CellVerification()
    try:
        expected_joints = [j for robot_id in ROBOT_IDS for j in joint_names(robot_id)]
        node.until(lambda: all(j in node.positions for j in expected_joints)
                   and len(node.clock_samples) > 5)
        assert node.clock_samples[-1] > node.clock_samples[0], 'Simulation clock is stopped'
        assert all(math.isfinite(node.positions[j]) for j in expected_joints), 'Nonfinite joint positions'
        client = node.create_client(ListControllers, '/uwa_cell/controller_manager/list_controllers')
        assert client.wait_for_service(timeout_sec=15), 'Controller manager missing'
        response = node.future(client.call_async(ListControllers.Request()))
        controllers = {controller.name: controller.state for controller in response.controller}
        expected_controllers = controller_names(layout)
        assert all(controllers.get(name) == 'active' for name in expected_controllers), controllers
        node.until(lambda: all(node.buffer.can_transform('world', f'{rid}_base_link', Time())
                               for rid in ROBOT_IDS))
        initial_bases = {rid: node.base_pose(rid) for rid in ROBOT_IDS}
        initial_physics_pose = gazebo_model_pose()
        assert np.isfinite(initial_physics_pose).all(), 'Nonfinite Gazebo model pose'
        assert np.linalg.norm(initial_physics_pose[:3]) < 0.001, 'Cell is not anchored at its world origin'
        assert abs(abs(initial_physics_pose[6]) - 1.0) < 0.001, 'Cell root rotated unexpectedly'
        for robot_id, pose in initial_bases.items():
            robot = layout['robots'][robot_id]
            table = layout['tables'][robot['table']]
            local = np.array(robot['mount_xyz']) + [0, 0, table['height']]
            expected = Rotation.from_euler('xyz', table['rpy']).apply(local) + table['xyz']
            assert np.linalg.norm(pose - expected) < 0.001, (robot_id, pose, expected)
        moved = []
        if args.move:
            for robot_id in ROBOT_IDS:
                before = dict(node.positions)
                original = np.array([before[j] for j in joint_names(robot_id)])
                target = original.copy()
                target[5] += 0.1
                try:
                    node.move_and_wait(robot_id, target)
                    max_other_drift = max(abs(node.positions[j] - before[j])
                                         for other in ROBOT_IDS if other != robot_id
                                         for j in joint_names(other))
                    assert max_other_drift < 0.01, f'Other arm moved by {max_other_drift} rad'
                    moved.append(robot_id)
                finally:
                    node.move_and_wait(robot_id, original)
        for robot_id, pose in initial_bases.items():
            assert np.linalg.norm(node.base_pose(robot_id) - pose) < 0.001, 'Robot base drifted'
        final_physics_pose = gazebo_model_pose()
        assert np.linalg.norm(final_physics_pose - initial_physics_pose) < 0.001, 'Gazebo cell root drifted'
        result = {'joint_count': len(expected_joints), 'clock_advances': True,
                  'controllers': controllers, 'bases_match_layout': True,
                  'gazebo_cell_root_stable': True,
                  'motion_tested_and_restored': moved, 'ros_domain': 64}
        text = json.dumps(result, indent=2)
        print(text)
        if args.output:
            Path(args.output).write_text(text + '\n')
    finally:
        node.destroy_node()
        rclpy.shutdown()

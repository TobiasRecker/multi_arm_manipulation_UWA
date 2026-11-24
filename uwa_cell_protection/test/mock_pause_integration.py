#!/usr/bin/env python3
"""Load the actual plugin in a dedicated GenericSystem manager, never UR hardware.

Source the candidate install before running. Uses domain67, LOCALHOST and a
URDF containing only mock_components/GenericSystem; no robot IP is accepted.
"""
import json
import argparse
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

os.environ['ROS_DOMAIN_ID'] = '67'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
os.environ['ROS_LOCALHOST_ONLY'] = '1'
os.environ['ROS_LOG_DIR'] = '/tmp/uwa-pause-mock-ros-logs'
Path(os.environ['ROS_LOG_DIR']).mkdir(exist_ok=True)

import rclpy
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTrajectoryControllerState
from controller_manager_msgs.srv import LoadController, ConfigureController, SwitchController
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-factor', type=float, choices=(1.0, .5), default=1.0)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('pause_plugin_mock_validation')
    namespace = '/uwa_mock_validation_pause'
    controller = namespace + '/joint_trajectory_controller'
    joints = [f'mock_joint_{i}' for i in range(6)]
    state, status = [], []
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                     reliability=ReliabilityPolicy.RELIABLE)
    description = node.create_publisher(String, namespace + '/robot_description', qos)
    pause = node.create_publisher(String, controller + '/pause_command', qos)
    topic = node.create_publisher(JointTrajectory, controller + '/joint_trajectory', 10)
    node.create_subscription(String, controller + '/pause_status',
                             lambda m: status.append(json.loads(m.data)), qos)
    node.create_subscription(JointTrajectoryControllerState, controller + '/controller_state',
                             lambda m: state.append(m), 10)

    def until(predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise AssertionError('timeout; last pause status=' + repr(status[-1:] or None))
            rclpy.spin_once(node, timeout_sec=.01)

    def spin(seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.01)

    def service(kind, name, request):
        client = node.create_client(kind, namespace + '/controller_manager/' + name)
        assert client.wait_for_service(timeout_sec=10), name
        future = client.call_async(request)
        until(future.done)
        result = future.result()
        node.destroy_client(client)
        return result

    def command(generation, paused, **extra):
        pause.publish(String(data=json.dumps(dict(generation=generation, paused=paused,
                                                 reason='isolated mock test', **extra))))
        until(lambda: status and status[-1]['generation'] == generation)

    def goal(start, end, duration=4., lead=.2):
        request = FollowJointTrajectory.Goal()
        request.trajectory.joint_names = joints
        request.trajectory.header.stamp = (node.get_clock().now() +
                                          rclpy.duration.Duration(seconds=lead)).to_msg()
        for t, q in ((0., start), (duration, end)):
            point = JointTrajectoryPoint(positions=[q] * 6)
            point.time_from_start = rclpy.duration.Duration(seconds=t).to_msg()
            request.trajectory.points.append(point)
        future = action.send_goal_async(request)
        until(future.done)
        return future.result()

    links = '<link name="base"/>' + ''.join(f'<link name="link_{i}"/>' for i in range(6))
    kinematic = ''.join(f'<joint name="{j}" type="revolute"><parent link="'
                        f'{"base" if i == 0 else "link_" + str(i-1)}"/>'
                        f'<child link="link_{i}"/><axis xyz="0 0 1"/>'
                        '<limit lower="-3" upper="3" effort="10" velocity="0.1"/></joint>'
                        for i, j in enumerate(joints))
    interfaces = ''.join(f'<joint name="{j}"><command_interface name="position"/>'
                         '<state_interface name="position"><param name="initial_value">0</param>'
                         '</state_interface><state_interface name="velocity">'
                         '<param name="initial_value">0</param></state_interface></joint>'
                         for j in joints)
    gpio = ('<gpio name="native_scaling"><state_interface name="factor">'
            f'<param name="initial_value">{args.native_factor}</param>'
            '</state_interface></gpio>') if args.native_factor != 1.0 else ''
    urdf = ('<robot name="pause_mock">' + links + kinematic +
            '<ros2_control name="mock" type="system"><hardware>'
            '<plugin>mock_components/GenericSystem</plugin>'
            '<param name="calculate_dynamics">true</param></hardware>' + interfaces +
            gpio + '</ros2_control></robot>')
    config = {
        namespace + '/controller_manager': {'ros__parameters': {
            'update_rate': 100,
            'joint_trajectory_controller': {
                'type': 'uwa_cell_protection/PausableJointTrajectoryController'}}},
        controller: {'ros__parameters': {
            'joints': joints, 'command_interfaces': ['position'],
            'state_interfaces': ['position', 'velocity'],
            'pause_joint_acceleration': .2, 'pause_joint_velocity': .1,
            'allow_trajectory_replacement': False,
            'constraints': {'stopped_velocity_tolerance': .2, 'goal_time': 0.0}}}}
    if args.native_factor != 1.0:
        config[controller]['ros__parameters']['speed_scaling.state_interface'] = 'native_scaling/factor'
    with tempfile.TemporaryDirectory(prefix='uwa-pause-mock-') as directory:
        path = Path(directory)
        config[namespace + '/controller_manager']['ros__parameters'][
            'joint_trajectory_controller']['params_file'] = str(path / 'controllers.yaml')
        (path / 'controllers.yaml').write_text(yaml.safe_dump(config))
        with (path / 'manager.log').open('w+') as log:
            manager = subprocess.Popen(['ros2', 'run', 'controller_manager', 'ros2_control_node',
                '--ros-args', '--params-file', str(path / 'controllers.yaml'),
                '-r', '__ns:=' + namespace], stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
            try:
                description.publish(String(data=urdf))
                response = service(LoadController, 'load_controller',
                                   LoadController.Request(name='joint_trajectory_controller'))
                assert response.ok, 'plugin load failed'
                assert service(ConfigureController, 'configure_controller',
                               ConfigureController.Request(name='joint_trajectory_controller')).ok
                assert service(SwitchController, 'switch_controller', SwitchController.Request(
                    activate_controllers=['joint_trajectory_controller'], strictness=2)).ok
                action = ActionClient(node, FollowJointTrajectory, controller + '/follow_joint_trajectory')
                assert action.wait_for_server(timeout_sec=5)
                until(lambda: state and status)
                assert abs(state[-1].speed_scaling_factor - args.native_factor) < 1e-9
                handle = goal(0., .3)
                assert handle.accepted
                original_id = bytes(handle.goal_id.uuid)
                result = handle.get_result_async()
                spin(1.0)
                command(1, True)
                until(lambda: status[-1]['factor'] < 1e-10)
                spin(.05)  # receive the matching final state after the 10-Hz status
                held_position = state[-1].feedback.positions[0]
                held_phase = status[-1]['phase_time_s']
                assert 0.0 < held_position < .3
                mark = len(state)
                spin(1.2)
                assert max(abs(s.feedback.positions[0] - held_position) for s in state[mark:]) < 1e-9
                assert abs(status[-1]['phase_time_s'] - held_phase) < 1e-9
                assert not result.done() and status[-1]['action_active'] and status[-1]['resumable']
                assert status[-1]['active_goal'].replace('-', '') == original_id.hex()
                assert not goal(held_position, .7).accepted
                topic.publish(JointTrajectory(joint_names=joints, points=[
                    JointTrajectoryPoint(positions=[.8] * 6,
                        time_from_start=rclpy.duration.Duration(seconds=1).to_msg())]))
                command(1, True)
                spin(.2)
                assert abs(state[-1].feedback.positions[0] - held_position) < 1e-9
                command(2, False)
                until(result.done, 10)
                assert result.result().result.error_code == 0, result.result()
                until(lambda: abs(state[-1].feedback.positions[0] - .3) < 1e-6, 1.)
                # A future-start goal must remain motionless through a pause
                # longer than its original wall-clock lead, then retain it.
                second = goal(.3, .4, duration=2., lead=1.0)
                assert second.accepted
                second_result = second.get_result_async()
                command(3, True)
                until(lambda: status[-1]['factor'] < 1e-10)
                spin(.05)
                phase_before = status[-1]['phase_time_s']
                mark = len(state)
                spin(1.5)
                assert not second_result.done()
                assert max(abs(s.feedback.positions[0] - .3) for s in state[mark:]) < 1e-8
                assert abs(status[-1]['phase_time_s'] - phase_before) < 1e-9
                command(4, False)
                until(second_result.done, 8)
                assert second_result.result().result.error_code == 0
                until(lambda: abs(state[-1].feedback.positions[0] - .4) < 1e-6, 1.)
                command(5, True)
                until(lambda: status[-1]['factor'] < 1e-10)
                assert status[-1]['resumable'] and not status[-1]['action_active']
                # Reviewed recovery is the only permitted replacement while
                # paused. Never resume the original blocked path to admit it.
                command(6, False)
                until(lambda: status[-1]['factor'] > 1.-1e-9)
                old = goal(.4, .6, duration=3.)
                assert old.accepted
                old_result = old.get_result_async()
                spin(.7)
                command(7, True)
                until(lambda: status[-1]['factor'] < 1e-10)
                spin(.05)
                recovery_start = state[-1].feedback.positions[0]
                recovery_end = recovery_start - .02
                recovery_trajectory = dict(joint_names=joints, points=[
                    dict(time=0., positions=[recovery_start]*6),
                    dict(time=1., positions=[recovery_end]*6)])
                authorization = dict(recovery_trajectory=recovery_trajectory,
                                     recovery_reviewed_sha256='a'*64)
                command(8, True, **authorization)
                assert status[-1]['active_recovery_sha256'] == ''
                assert not goal(recovery_start, recovery_end + .001, duration=1.).accepted
                recovery = goal(recovery_start, recovery_end, duration=1.)
                assert recovery.accepted
                recovery_result = recovery.get_result_async()
                until(old_result.done)
                until(lambda: status[-1]['active_recovery_sha256'] == 'a'*64)
                assert old_result.result().status == 6  # normal preemption ABORTED
                spin(.3)
                assert not recovery_result.done()
                assert abs(state[-1].feedback.positions[0] - recovery_start) < 1e-8
                assert status[-1]['resumable']
                assert not goal(recovery_start, recovery_end, duration=1.).accepted
                command(9, True)  # revoke future admission, retain accepted recovery identity
                assert status[-1]['active_recovery_sha256'] == 'a'*64
                command(10, False, **authorization)
                until(recovery_result.done, 8)
                assert recovery_result.result().result.error_code == 0
                until(lambda: abs(state[-1].feedback.positions[0] - recovery_end) < 1e-6, 1.)
                until(lambda: status[-1]['active_recovery_sha256'] == '')
                # Canceling a paused action removes that action permanently.
                # Explicit Resume clears the latch for a fresh reviewed task;
                # it must not reconstruct or replay the canceled action.
                canceled = goal(recovery_end, recovery_end + .1, duration=3.)
                assert canceled.accepted
                canceled_result = canceled.get_result_async()
                spin(.5)
                command(11, True)
                until(lambda: status[-1]['factor'] < 1e-10)
                spin(.05)
                canceled_position = state[-1].feedback.positions[0]
                cancellation = canceled.cancel_goal_async()
                until(cancellation.done)
                until(canceled_result.done)
                assert canceled_result.result().status == 5
                until(lambda: not status[-1]['action_active'] and not status[-1]['resumable'])
                spin(.2)
                assert abs(state[-1].feedback.positions[0] - canceled_position) < 1e-8
                command(12, False)
                until(lambda: status[-1]['factor'] > 1.-1e-9)
                spin(.2)
                assert abs(state[-1].feedback.positions[0] - canceled_position) < 1e-8
                fresh = goal(canceled_position, canceled_position + .03, duration=1.)
                assert fresh.accepted
                fresh_result = fresh.get_result_async()
                until(lambda: status[-1]['action_active'] and status[-1]['resumable'])
                until(fresh_result.done, 5)
                assert fresh_result.result().result.error_code == 0
                print(json.dumps(dict(success=True, native_factor=args.native_factor,
                    retained_action=original_id.hex(),
                    held_position=held_position, held_phase_s=held_phase,
                    checks=['actual plugin load', 'chain-rule ramp', 'long pause',
                            'same action resumed', 'new goal rejection', 'topic rejection',
                            'idempotent command', 'future start pause', 'idle resumable',
                            'reviewed recovery admission', 'recovery cannot move before resume',
                            'recovery authorization consumed once',
                            'cancel paused action without replay', 'fresh task clears old diagnosis'])))
            except BaseException:
                log.flush()
                print((path / 'manager.log').read_text()[-14000:])
                raise
            finally:
                os.killpg(manager.pid, signal.SIGINT)
                try:
                    manager.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(manager.pid, signal.SIGKILL)
                    manager.wait()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

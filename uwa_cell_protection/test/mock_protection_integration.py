#!/usr/bin/env python3
"""Isolated Domain67 C++ protection API test; synthetic cells, no Gazebo or hardware."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

import rclpy
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from controller_manager_msgs.msg import ControllerState
from controller_manager_msgs.srv import ListControllers, SwitchController
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger

ARMS = ('left_front', 'left_rear', 'right_front', 'right_rear')


def fixture(directory):
    text = "<robot name='cell'><link name='world'/><link name='table'><collision><geometry><box size='0.2 0.2 0.2'/></geometry></collision></link><joint name='table_mount' type='fixed'><parent link='world'/><child link='table'/><origin xyz='1 0 1'/></joint>"
    config = dict(schema_version=1, model_signature='mock-model', urdf_path='robot.urdf',
                  srdf_path='robot.srdf', arms={}, spheres={}, neighbor_margin_m=.04,
                  rate_hz=20., state_timeout_s=.2)
    for index, arm in enumerate(ARMS):
        parent = 'world'
        names = []
        for j in range(6):
            joint, link = f'{arm}_joint{j}', f'{arm}_link{j}'
            names.append(joint)
            collision = "<collision><geometry><sphere radius='0.1'/></geometry></collision>" if j == 5 else ''
            origin = f"<origin xyz='{index*3} 0 1'/>" if j == 0 else ''
            kind = 'prismatic' if j == 0 else 'revolute'
            text += f"<link name='{link}'>{collision}</link><joint name='{joint}' type='{kind}'><parent link='{parent}'/><child link='{link}'/>{origin}<axis xyz='1 0 0'/><limit lower='-0.1' upper='0.1' velocity='1' effort='1'/></joint>"
            parent = link
        config['arms'][arm] = dict(ip='127.0.0.1', namespace=f'/protection_test/{arm}', joint_names=names)
        config['spheres'][arm] = [dict(link=parent, centre=[0., 0., 0.], radius=.1)]
    (directory/'robot.urdf').write_text(text+'</robot>')
    (directory/'robot.srdf').write_text("<robot name='cell'/>")
    (directory/'model-config.json').write_text(json.dumps(config))
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', required=True)
    args = parser.parse_args()
    if os.environ.get('ROS_DOMAIN_ID') != '67':
        raise RuntimeError('Test requires explicit ROS_DOMAIN_ID=67')
    with tempfile.TemporaryDirectory(prefix='uwa-protection-mock-') as tmp:
        directory = Path(tmp)
        os.environ['ROS_LOG_DIR'] = str(directory/'ros-log')
        config = fixture(directory)
        log = (directory/'node.log').open('w+')
        process = subprocess.Popen([args.node, '--ros-args', '-p', 'mode:=mock', '-p',
                                    f'model_config:={directory / "model-config.json"}'],
                                   stdout=log, stderr=subprocess.STDOUT)
        rclpy.init()
        node = rclpy.create_node('protection_core_mock_validation')
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        publishers, acknowledgements = {}, {}
        commands, inventory = [], []
        last_commands = {}
        switches = []
        fallback_mode = [False]
        ack_flags = {arm: dict(resumable=True, action_active=False) for arm in ARMS}
        services, subscriptions = [], []
        positions = {j: 0. for a in config['arms'].values() for j in a['joint_names']}
        for arm in ARMS:
            entry = config['arms'][arm]
            ns = entry['namespace']
            publishers[arm] = node.create_publisher(JointState, ns+'/joint_states', 1)
            acknowledgements[arm] = node.create_publisher(String, ns+'/joint_trajectory_controller/pause_status', qos)

            def command(message, rid=arm):
                value = json.loads(message.data)
                commands.append((rid, value))
                last_commands[rid] = value
                acknowledgements[rid].publish(String(data=json.dumps(dict(value,
                    factor=0. if value['paused'] else 1., **ack_flags[rid]))))

            subscriptions.append(node.create_subscription(String, ns+'/joint_trajectory_controller/pause_command', command, qos))

            def listing(request, response, rid=arm):
                inventory.append(rid)
                controller = ControllerState()
                fallback = fallback_mode[0] and rid == 'right_front'
                velocity = fallback and fallback_mode[0] == 'velocity'
                controller.name = 'velocity_jog_controller' if velocity else 'joint_trajectory_controller'
                controller.type = ('velocity_controllers/JointGroupVelocityController' if velocity else
                                   'joint_trajectory_controller/JointTrajectoryController' if fallback else
                                   'uwa_cell_protection/PausableJointTrajectoryController')
                controller.state = 'active'
                controller.claimed_interfaces = [j+('/velocity' if velocity else '/position')
                                                 for j in config['arms'][rid]['joint_names']]
                response.controller = [controller]
                return response

            services.append(node.create_service(ListControllers, ns+'/controller_manager/list_controllers', listing))

            def switching(request, response, rid=arm):
                switches.append((rid, request))
                response.ok = True
                return response

            services.append(node.create_service(SwitchController, ns+'/controller_manager/switch_controller', switching))

        clients = {name: node.create_client(Trigger, '/uwa_cell/protection/'+name)
                   for name in ('status', 'pause_all', 'resume_all', 'begin_recovery')}

        def pump(duration=.1, publish=True):
            end = time.monotonic()+duration
            while time.monotonic() < end:
                if process.poll() is not None:
                    raise RuntimeError('Protection node exited unexpectedly')
                if publish:
                    for rid, pub in publishers.items():
                        msg = JointState()
                        msg.header.stamp = node.get_clock().now().to_msg()
                        msg.name = config['arms'][rid]['joint_names']
                        msg.position = [positions[j] for j in msg.name]
                        msg.velocity = [0.]*6
                        pub.publish(msg)
                rclpy.spin_once(node, timeout_sec=.01)

        def call(name, publish=True):
            client = clients[name]
            deadline = time.monotonic()+5.
            while not client.service_is_ready() and time.monotonic() < deadline:
                pump(.05, publish)
            future = client.call_async(Trigger.Request())
            while not future.done() and time.monotonic() < deadline:
                pump(.02, publish)
            if not future.done():
                raise RuntimeError('Service timeout: '+name)
            response = future.result()
            return response.success, json.loads(response.message)

        try:
            okay, state = call('status', publish=False)
            assert okay and not state['paused'] and not state['collision_data_available'], state
            pump(.5)
            okay, state = call('status')
            assert okay and state['collision_data_available'] and not state['paused'], state
            # The live C++ node omits missing data and warns; no hidden stale-data stop.
            pump(.35, publish=False)
            _, state = call('status', publish=False)
            assert not state['paused'] and not state['collision_data_available'] and state['warnings'], state
            assert not commands and not inventory
            pump(.15)
            positions['right_front_joint0'] = -5.77
            pump(.2)
            _, state = call('status')
            assert state['paused'] and state['known_collisions'], state
            assert {rid for rid, value in commands if value['paused']} == set(ARMS)
            pump(.15)
            assert len(inventory) == 4, inventory
            okay, state = call('resume_all')
            assert not okay and state['command_error'] and state['paused'], state
            # A missing source never erases a known unresolved collision.
            pump(.35, publish=False)
            okay, state = call('resume_all', publish=False)
            assert not okay and state['known_collisions'], state
            pump(.15)
            # A checked recovery is the only exception and still needs explicit resume.
            start = dict(positions)
            end = dict(start, right_front_joint0=-5.70)
            recovery = dict(model_signature='mock-model', reviewed_sha256='a'*64,
                            start_tolerance_rad=.001, states=[start, end],
                            trajectories={'right_front': dict(joint_names=config['arms']['right_front']['joint_names'], points=[dict(positions=[end[j] for j in config['arms']['right_front']['joint_names']], time=1.)])})
            path = directory/'recovery.json'
            path.write_text(json.dumps(recovery))
            params = AsyncParameterClient(node, '/uwa_cell/protection')
            future = params.set_parameters([Parameter('recovery_plan_path', value=str(path))])
            while not future.done():
                pump(.02)
            assert all(r.successful for r in future.result().results)
            okay, state = call('begin_recovery')
            assert okay and state['paused'] and state['recovery_active'], state
            okay, state = call('resume_all')
            assert not okay and state['paused'] and 'replacement is not yet active' in state['command_error'], state
            ack_flags['right_front'] = dict(resumable=True, action_active=True, active_recovery_sha256='a'*64)
            acknowledgements['right_front'].publish(String(data=json.dumps(dict(
                last_commands['right_front'], factor=0., **ack_flags['right_front']))))
            pump(.1)
            okay, state = call('resume_all')
            assert okay and not state['paused'], state
            positions.update(end)
            pump(.2)
            _, state = call('status')
            assert not state['paused'] and not state['recovery_active'] and not state['known_collisions'], state
            okay, state = call('pause_all')
            assert okay and state['paused'], state
            pump(.15)
            assert len(inventory) == 8, inventory
            assert len([1 for rid, value in commands if value['paused']]) == 12
            okay, state = call('resume_all')
            assert okay and not state['paused'], state
            # Non-JTC commands take the existing hold owner, once, with the
            # competing velocity controller explicitly deactivated.
            ack_flags['right_front'] = dict(resumable=False, action_active=False)
            okay, state = call('pause_all')
            assert okay
            pump(.1)
            okay, state = call('resume_all')
            assert okay and not state['paused'], state
            assert any('previous trajectory unavailable' in w for w in state['warnings']), state
            ack_flags['right_front'] = dict(resumable=True, action_active=False)
            fallback_mode[0] = 'velocity'
            okay, state = call('pause_all')
            assert okay and state['paused']
            pump(.2)
            _, state = call('status')
            assert len(switches) == 1, switches
            rid, request = switches[0]
            assert rid == 'right_front'
            assert request.activate_controllers == ['collision_hold_controller']
            assert request.deactivate_controllers == ['velocity_jog_controller']
            assert request.strictness == SwitchController.Request.FORCE_AUTO
            assert state['arms']['right_front']['controller'] == 'collision_hold_controller', state
            okay, state = call('resume_all')
            assert okay
            fallback_mode[0] = 'stock'
            okay, state = call('pause_all')
            assert okay
            pump(.2)
            assert len(switches) == 2
            assert switches[-1][1].deactivate_controllers == ['joint_trajectory_controller']
            print('PASS: C++ mock live API, all-arm pause, one-shot inventory, missing-data warning, unresolved collision, checked recovery, explicit resume')
        except BaseException:
            log.flush(); log.seek(0)
            print(log.read())
            raise
        finally:
            node.destroy_node()
            rclpy.shutdown()
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=5.)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            log.close()


if __name__ == '__main__':
    main()

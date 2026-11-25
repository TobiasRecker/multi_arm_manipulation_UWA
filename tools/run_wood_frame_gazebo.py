#!/usr/bin/env python3
"""Run a geometrically checked wood-frame plan in its own Gazebo world."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import uuid4

from ament_index_python.packages import get_package_prefix, get_package_share_directory
import numpy as np
import rclpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'uwa_cell_tasks'))

from match_cooperative_handling.rigid_object import pose_error
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import simulation_only
from uwa_cell_tasks.core import configuration, verify, write_json
from uwa_cell_tasks.runtime import Simulation
from uwa_cell_tasks.wood_frame import MODEL_STATUS
from uwa_cell_tasks.wood_frame_gazebo import (
    BEAM_MODEL, GROUP_CONTROLLER, POST_MODEL, ROBOT_MODEL, screw_marker, stage_scene,
)


SIM_SEATING_TOLERANCE = {'position_m': .008, 'angle_deg': 3.}


def phase_trajectory(names, phase):
    return {'joint_names': names, 'points': [
        {'time': t, 'positions': q, 'velocities': dq, 'accelerations': ddq}
        for t, q, dq, ddq in zip(phase['time_s'], phase['positions'], phase['velocities'],
                                phase['accelerations'], strict=True)
    ]}


def load_checked_plan(path):
    plan = verify(json.loads(path.read_text()))
    if plan['status'] != MODEL_STATUS or plan['audit']['status'] != 'PASS':
        raise ValueError('Gazebo needs a complete, accepted offline plan')
    description_file = path.with_name('description.urdf')
    description = description_file.read_bytes()
    if hashlib.sha256(description).hexdigest() != plan['description_sha256']:
        raise ValueError('The robot description changed after the offline audit')
    return plan, description.decode()


class GazeboTransport:
    def __init__(self, world):
        from gz.transport import Node
        self.node = Node()
        self.prefix = f'/world/{world}'

    def request(self, suffix, message, reply_type, timeout_ms=5000):
        ok, reply = self.node.request(self.prefix + '/' + suffix, message, type(message),
                                      reply_type, timeout_ms)
        if not ok:
            raise RuntimeError(f'Gazebo service failed: {self.prefix}/{suffix}')
        return reply

    def create(self, name, *, file=None, sdf=None, timeout_ms=5000):
        from gz.msgs.boolean_pb2 import Boolean
        from gz.msgs.entity_factory_pb2 import EntityFactory
        request = EntityFactory(name=name, allow_renaming=False)
        if file is not None:
            request.sdf_filename = str(file)
        else:
            request.sdf = sdf
        if not self.request('create', request, Boolean, timeout_ms).data:
            raise RuntimeError(f'Gazebo did not accept creation of {name}')

    def join_beam(self):
        from gz.msgs.boolean_pb2 import Boolean
        from gz.msgs.entity_pb2 import Entity
        from gz.msgs.entity_plugin_v_pb2 import EntityPlugin_V
        from gz.msgs.empty_pb2 import Empty
        from gz.msgs.scene_pb2 import Scene
        from gz.msgs.stringmsg_pb2 import StringMsg
        from threading import Event

        # Add the built-in attachment system after all screws. On activation
        # it connects the existing links at the measured offset in physics.
        scene = self.request('scene/info', Empty(), Scene)
        fixture = next((model for model in scene.model if model.name == POST_MODEL), None)
        if fixture is None:
            raise RuntimeError('Gazebo did not report the post fixture')
        request = EntityPlugin_V(entity=Entity(id=fixture.id, type=Entity.MODEL))
        output_topic = self.prefix + '/completed_join'
        attached = Event()

        def state(message):
            if message.data == 'attached':
                attached.set()

        if not self.node.subscribe(StringMsg, output_topic, state):
            raise RuntimeError('Could not subscribe to Gazebo joint state')
        try:
            request.plugins.add(
                filename='gz-sim-detachable-joint-system', name='gz::sim::systems::DetachableJoint',
                innerxml=(f'<parent_link>fixture</parent_link><child_model>{BEAM_MODEL}</child_model>'
                          f'<child_link>body</child_link><output_topic>{output_topic}</output_topic>'))
            if not self.request('entity/system/add', request, Boolean).data:
                raise RuntimeError('Gazebo rejected the fixture attachment')
            if not attached.wait(5.):
                raise RuntimeError('Gazebo did not report the fixture attachment')
        finally:
            self.node.unsubscribe(output_topic)


@contextmanager
def managed_process(command, log_path):
    with log_path.open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            yield process
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=8.)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5.)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()


def start_controllers(output, namespace, params, active):
    with (output / 'controllers.log').open('w') as log:
        subprocess.run(['ros2', 'run', 'controller_manager', 'spawner', *active,
                        '-c', namespace + '/controller_manager', '--controller-manager-timeout', '60',
                        '--param-file', str(params), '--ros-args', '-r', '__ns:=' + namespace],
                       stdout=log, stderr=subprocess.STDOUT, timeout=75., check=True)


def beam_alignment(sim, target):
    pose = np.asarray(sim.object['T_world_object'])
    position_error, rotation_error = pose_error(target, pose)
    return {'expected_pose': target, 'measured_pose': pose, 'position_error_m': position_error,
            'angle_error_deg': float(np.degrees(rotation_error))}


def replay(plan, description, output, namespace, transport, report):
    sim = Simulation(namespace, output)
    sim.motion_arms = (*plan['scene']['holders'], plan['scene']['tool']['arm'], plan['scene']['parked'])
    screws = {site['id']: site for site in plan['scene']['screws']}
    tool = plan['scene']['tool']
    chain = Chain(description, 'world', tool['arm'] + '_tool0')
    tip = np.asarray(tool['tool0_to_tip'], dtype=float)
    target = plan['scene']['beam']['target_pose']

    def save():
        write_json(output / 'result.json', report)

    def require_seat(alignment):
        if (alignment['position_error_m'] > SIM_SEATING_TOLERANCE['position_m'] or
                alignment['angle_error_deg'] > SIM_SEATING_TOLERANCE['angle_deg']):
            raise RuntimeError('The simulated beam is outside the seating tolerance')

    try:
        sim.connect()
        report['status'] = 'running'
        report['start_beam'] = beam_alignment(sim, plan['scene']['beam']['start_pose'])
        for phase in plan['phases']:
            sim.phase = phase['id']
            print(f'Gazebo · {sim.phase}', flush=True)
            step = {'id': sim.phase, 'start_sim_s': sim.now(), 'finished': False}
            report['phases'].append(step)
            save()
            if sim.phase == 'grasp':
                sim.grippers(.8)
                report['pad_contact'] = json.loads((output / 'grasp-contact-confirmation.json').read_text())
            elif sim.phase == 'fasten':
                completed = [site['id'] for site in report['screws']]
                if completed != list(screws):
                    raise RuntimeError('Fixture attachment requires every screw procedure in recipe order')
                report['before_attachment'] = beam_alignment(sim, target)
                require_seat(report['before_attachment'])
                transport.join_beam()
                report['fixture_attachment_confirmed'] = True
            elif sim.phase == 'release':
                from std_srvs.srv import SetBool
                if not report.get('fixture_attachment_confirmed'):
                    raise RuntimeError('Fixture attachment must be confirmed before opening')
                sim.call('latch', SetBool.Request(data=False))
                sim.grippers(0.)
                report['after_release'] = beam_alignment(sim, target)
            else:
                sim.follow(phase_trajectory(plan['joint_names'], phase), GROUP_CONTROLLER)
                if sim.phase == 'seat':
                    report['seated_beam'] = beam_alignment(sim, target)
                    require_seat(report['seated_beam'])
                if phase['kind'] == 'axial_feed':
                    planned = dict(zip(plan['joint_names'], phase['positions'][-1]))
                    expected = (chain.forward(planned) @ tip)[:3, 3]
                    measured = (chain.forward(sim.q) @ tip)[:3, 3]
                    step['tip_world_m'] = measured
                    step['expected_tip_world_m'] = expected
                    step['axial_endpoint_error_m'] = float(np.linalg.norm(expected - measured))
                if phase['kind'] == 'axial_retract':
                    screw = screws[phase['screw_id']]
                    name, sdf = screw_marker(screw)
                    transport.create(name, sdf=sdf)
                    report['screws'].append({'id': screw['id'], 'side': screw['side'],
                                              'process': 'simulated axial procedure'})
            step.update(finished=True, end_sim_s=sim.now())
            save()
        report['after_retreat'] = beam_alignment(sim, target)
        require_seat(report['after_retreat'])
        report.update(status='completed', sim_duration_s=sim.now()-report['phases'][0]['start_sim_s'])
        save()
    except (Exception, KeyboardInterrupt):
        report['cancellation'] = sim.cancel()
        report['failure_phase'] = sim.phase
        report['measured_contact'] = sim.contact
        report['measured_beam'] = sim.object
        raise
    finally:
        sim.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--stage-only', action='store_true')
    parser.add_argument('--pad-friction', type=float, help='Optional modeled pad/wood coefficient')
    args = parser.parse_args()
    simulation_only()
    plan, description = load_checked_plan(args.plan)
    profile = Path(get_package_share_directory('uwa_cell_tasks')) / 'config/carton_drawing_fast.yaml'
    cfg = configuration(profile)
    if args.pad_friction is not None:
        if not np.isfinite(args.pad_friction) or args.pad_friction <= 0.:
            parser.error('--pad-friction needs a positive finite coefficient')
        cfg['grip_contact_friction'] = args.pad_friction
    suffix = uuid4().hex[:10]
    namespace = '/uwa_grasp_wood_' + suffix
    world_name = 'wood_frame_' + suffix
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    packages = {key: Path(get_package_prefix(name))
                for key, name in [('tasks', 'uwa_cell_tasks'), ('physics', 'gz_physics_vendor')]}
    world, robot, controllers, publisher_params, active = stage_scene(
        plan, description, output, namespace, world_name, cfg, packages)
    report = {'status': 'staged', 'world': world_name, 'namespace': namespace,
              'plan_sha256': plan['sha256'], 'phases': [], 'screws': [],
              'fixture_model': 'idealized Gazebo fixed joint', 'pad_friction': cfg['grip_contact_friction'],
              'seating_tolerance': SIM_SEATING_TOLERANCE}
    write_json(output / 'result.json', report)
    if args.stage_only:
        print(output / 'result.json')
        return 0
    rclpy.init()
    server_command = ['gz', 'sim', '-s', '-r', str(world), '--headless-rendering', '-v', '2']
    publisher_command = ['ros2', 'run', 'robot_state_publisher', 'robot_state_publisher', '--ros-args',
                         '-r', '__ns:=' + namespace, '-r', '/clock:=' + namespace + '/clock',
                         '-r', '/tf:=' + namespace + '/tf', '-r', '/tf_static:=' + namespace + '/tf_static',
                         '--params-file', str(publisher_params)]
    try:
        with (managed_process(publisher_command, output / 'robot_state_publisher.log'),
              managed_process(server_command, output / 'gazebo.log') as server):
            began = time.monotonic()
            transport = GazeboTransport(world_name)
            transport.create(ROBOT_MODEL, file=robot, timeout_ms=20000)
            if server.poll() is not None:
                raise RuntimeError('Gazebo server exited before controller startup')
            start_controllers(output, namespace, controllers, active)
            replay(plan, description, output, namespace, transport, report)
            report['elapsed_wall_s'] = time.monotonic() - began
    except (Exception, KeyboardInterrupt) as error:
        report.update(status='failed', error=str(error) or type(error).__name__)
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        write_json(output / 'result.json', report)
    print(f"Gazebo {report['status']} · {output / 'result.json'}")
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

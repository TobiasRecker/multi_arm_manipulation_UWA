"""Reviewed/carton consumers use the minimal API without legacy protection gates."""
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace as Box

import pytest

REPO = Path(__file__).resolve().parents[2]
for directory in ('uwa_cell_motion', 'uwa_cell_tasks', 'uwa_cell_gripper_control'):
    sys.path.insert(0, str(REPO/directory))

from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_tasks import hardware_preparation, minimal_gripper_phase, minimal_reviewed_execution
from uwa_cell_tasks import reviewed_carton_execution, minimal_snapshot


ARMS = ('right_front', 'right_rear')


def forbidden(*args, **kwargs):
    pytest.fail('Legacy runtime protection must not be called by the minimal backend')


def bundle(offset=0.):
    trajectories = {arm:dict(joint_names=joint_names(arm), duration_s=1., points=[
        dict(time=0., positions=[offset]*6, velocities=[0.]*6, accelerations=[0.]*6),
        dict(time=1., positions=[offset+.1]*6, velocities=[0.]*6, accelerations=[0.]*6)]) for arm in ARMS}
    start = {joint:offset for arm in ROBOT_IDS for joint in joint_names(arm)}
    return dict(phase='high', joint_limit_rad_s=.1, tcp_limit_m_s=1/12,
                groups=[dict(arms=list(ARMS), trajectories=trajectories, start=start, duration_s=1.)])


def test_two_reviewed_tasks_route_to_minimal_and_ignore_legacy_dependencies(tmp_path, monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND', 'minimal')
    monkeypatch.setattr(minimal_reviewed_execution, 'motion_context', nullcontext)
    checks, clients = [], []
    monkeypatch.setattr(minimal_reviewed_execution, 'speed_envelope', lambda *a:Box(
        check_trajectory=lambda arm, points:checks.append((arm, points))))
    class Client:
        def __init__(self, problem, mode, selected):
            assert mode == 'hardware' and selected == sorted(ARMS)
            self.positions = {joint:0. for arm in ROBOT_IDS for joint in joint_names(arm)}
            self.protection_status = dict(warnings=['Collision data unavailable'])
            self.service_timings, self.groups = [], []
            self.closed = False
            clients.append(self)
        def connect(self):pass
        def wait_unpaused(self):pass
        def health(self):pass
        def follow_group(self, trajectories, *, duration_s, segment):
            self.groups.append(trajectories)
            for arm, trajectory in trajectories.items():
                self.positions.update(zip(joint_names(arm), trajectory['points'][-1]['positions']))
            segment['executed'] = True
        def destroy_node(self):self.closed = True
        stop = forbidden
    monkeypatch.setattr(minimal_reviewed_execution, 'MinimalHardwareClient', Client)
    # Any attempted legacy client, observer, gripper-read or Play use fails.
    for index in range(2):
        output = tmp_path/str(index)
        output.mkdir()
        report = {}
        args = Box(review_id=None, reviewed_sha256=None, start_ros_programs=False)
        assert reviewed_carton_execution.run_bundle(Box(), bundle(), args, output, report,
            client_type=forbidden, observer_type=forbidden, read_gripper=forbidden,
            start_programs=forbidden, end_phase='HIGH_COMPLETE') == 0
        saved = json.loads((output/'result.json').read_text())
        assert saved['success'] and saved['phase'] == 'HIGH_COMPLETE'
        assert saved['finger_commands'] == [] and saved['segments'][0]['executed']
        assert saved['protection_backend'] == 'minimal'
    assert len(clients) == 2 and all(client.closed for client in clients)
    assert len(checks) == 4
    assert all(len(client.groups) == 1 for client in clients)


def test_reviewed_start_mismatch_reports_failure_without_new_global_stop(tmp_path, monkeypatch):
    monkeypatch.setattr(minimal_reviewed_execution, 'motion_context', nullcontext)
    monkeypatch.setattr(minimal_reviewed_execution, 'speed_envelope', lambda *a:Box(check_trajectory=lambda *a:None))
    class Client:
        def __init__(self, *args):
            self.positions = {joint:1. for arm in ROBOT_IDS for joint in joint_names(arm)}
            self.protection_status = dict(paused=False)
            self.service_timings = []
        def connect(self):pass
        def health(self):pass
        def wait_unpaused(self):pass
        def destroy_node(self):pass
        follow_group = forbidden
        stop = forbidden
    monkeypatch.setattr(minimal_reviewed_execution, 'MinimalHardwareClient', Client)
    report = {}
    assert minimal_reviewed_execution.run_bundle(Box(), bundle(), Box(review_id=None, start_ros_programs=False),
        tmp_path, report, end_phase='DONE') == 1
    assert 'start differs' in report['error']
    assert report['arm_commands'] == []


def observation():
    return dict(protection_backend='minimal', arms={arm:dict(observed=True,
        stationary_observed=False, samples=[dict(actual_q=[0.]*6, actual_qd=[100.]*6,
        robot_mode=3, safety_mode=3, runtime_state=1)]) for arm in ROBOT_IDS}, grippers={})


def test_minimal_planning_snapshot_needs_positions_without_stationarity_speed_or_gripper_gates():
    assert set(hardware_preparation.validate_planning_snapshot(observation())) == set(ROBOT_IDS)
    invalid = observation()
    invalid['arms']['right_front']['samples'][-1]['actual_q'][1] = float('nan')
    with pytest.raises(ValueError, match='invalid native joint positions'):
        hardware_preparation.validate_planning_snapshot(invalid)
    missing = observation()
    del missing['arms']['left_front']
    with pytest.raises(ValueError, match='left_front'):
        hardware_preparation.validate_planning_snapshot(missing)


def test_shared_snapshot_waits_for_valid_complete_current_positions_only(monkeypatch):
    monkeypatch.setenv('ROS_DOMAIN_ID', '67')
    monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST')
    callbacks, spins, alive, closed = [], [], [False], []
    class Node:
        def create_subscription(self, kind, topic, receive, qos):
            assert topic == '/uwa_cell/protection/state'
            callbacks.append(receive)
        def destroy_node(self):closed.append(True)
    monkeypatch.setattr(minimal_snapshot.rclpy, 'ok', lambda:alive[0])
    monkeypatch.setattr(minimal_snapshot.rclpy, 'init', lambda **kwargs:alive.__setitem__(0, True))
    monkeypatch.setattr(minimal_snapshot.rclpy, 'shutdown', lambda:alive.__setitem__(0, False))
    monkeypatch.setattr(minimal_snapshot.rclpy, 'create_node', lambda *a, **k:Node())
    def spin(node, timeout_sec):
        spins.append(True)
        # A future-dated first sample is not a current planning input.
        stamp = time.monotonic() + (60 if len(spins) == 1 else 0)
        records = {arm:dict(q=[.1]*6, v=[100.]*6, device_timestamp=42.,
                           received_monotonic_s=stamp) for arm in ROBOT_IDS}
        callbacks[0](Box(data=json.dumps(dict(records=records, model_signature='model-v1'))))
    monkeypatch.setattr(minimal_snapshot.rclpy, 'spin_once', spin)
    result = minimal_snapshot.observe(mode='mock', timeout=1.)
    assert len(spins) == 2 and closed and not alive[0]
    assert result['model_signature'] == 'model-v1'
    assert result['grippers'] == {} and result['commands_sent'] == []
    assert result['arms']['right_front']['samples'][0]['actual_qd'] == [100.]*6
    assert result['arms']['right_front']['samples'][0]['device_timestamp_s'] == 42.


@pytest.mark.parametrize('phase,expected', [('prepare', ['activate','open']), ('close', ['close']), ('release', ['open'])])
def test_gripper_commands_have_no_arm_or_gripper_monitoring(tmp_path, monkeypatch, phase, expected):
    calls = []
    class Gripper:
        def __init__(self, arm):self.arm = arm
        def __enter__(self):return self
        def __exit__(self, *args):pass
        def activate(self):
            calls.append((self.arm, 'activate'))
            return dict(completed=True)
        def open(self, **kwargs):
            assert kwargs == dict(force_raw=0, speed_raw=16)
            calls.append((self.arm, 'open'))
            return dict(completed=True)
        def close_gripper(self, **kwargs):
            assert kwargs == dict(force_raw=0, speed_raw=16)
            calls.append((self.arm, 'close'))
            return dict(completed=True)
    monkeypatch.setattr(minimal_gripper_phase, 'GripperClient', Gripper)
    monkeypatch.setattr(minimal_gripper_phase, 'motion_context', nullcontext)
    args = Box(output=tmp_path/'output', state=tmp_path/'state.json', phase=phase,
               review_id=None, start_ros_programs=False, execute=True)
    assert minimal_gripper_phase.run(args, b'input', dict(segments=[])) == 0
    report = json.loads((args.output/'result.json').read_text())
    assert report['success'] and report['gripper_commands_completed']
    assert report['arm_commands'] == []
    assert report['gripper_monitoring'] == 'none; collision geometry only'
    assert 'grasp_confirmed' not in report and 'standstill_confirmed' not in report
    for arm in ARMS:
        assert [name for rid, name in calls if rid == arm] == expected


def test_gripper_error_is_an_ordinary_result_and_does_not_stop_arms(tmp_path, monkeypatch):
    class Gripper:
        def __init__(self, arm):self.arm = arm
        def __enter__(self):return self
        def __exit__(self, *args):pass
        def close_gripper(self, **kwargs):
            if self.arm == 'right_front':
                raise RuntimeError('Device command rejected')
            return dict(completed=True)
    monkeypatch.setattr(minimal_gripper_phase, 'GripperClient', Gripper)
    monkeypatch.setattr(minimal_gripper_phase, 'motion_context', nullcontext)
    args = Box(output=tmp_path/'output', state=tmp_path/'state.json', phase='close',
               review_id=None, start_ros_programs=False, execute=True)
    assert minimal_gripper_phase.run(args, b'input', {}) == 1
    report = json.loads((args.output/'result.json').read_text())
    assert report['phase'] == 'GRIPPER_COMMAND_FAILED' and report['arm_commands'] == []
    assert report['errors']['right_front'] == 'Device command rejected'
    assert 'right_rear' in report['results']


def test_read_only_gripper_phase_sends_no_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(minimal_gripper_phase, 'GripperClient', forbidden)
    args = Box(output=tmp_path/'output', state=tmp_path/'state.json', phase='close',
               review_id=None, start_ros_programs=False, execute=False)
    assert minimal_gripper_phase.run(args, b'input', {}) == 0
    report = json.loads((args.output/'result.json').read_text())
    assert report['phase'] == 'READ_ONLY_READY_NO_COMMANDS'
    assert report['arm_commands'] == [] and report['finger_commands'] == []

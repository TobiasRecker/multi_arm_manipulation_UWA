"""Minimal execution keeps controller goals across pause and repeated tasks.

Transport and executor are local fakes: no ROS context, sockets or robot I/O.
"""
from concurrent.futures import Future
import json
from pathlib import Path
import sys
from types import SimpleNamespace as Box

import pytest
from action_msgs.msg import GoalStatus
from std_msgs.msg import String

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'uwa_cell_motion'))
from uwa_cell_motion import minimal_execution as execution
from uwa_cell_motion.common import ROBOT_IDS, joint_names


ARMS = ('right_front', 'right_rear')


def completed(value):
    future = Future()
    future.set_result(value)
    return future


def paths(offset=0.):
    return {arm: dict(joint_names=joint_names(arm), duration_s=1., points=[
        dict(time=0., positions=[offset]*6, velocities=[0.]*6, accelerations=[0.]*6),
        dict(time=1., positions=[offset+.1]*6, velocities=[0.]*6, accelerations=[0.]*6)])
        for arm in ARMS}


class LocalTransport:
    def __init__(self):
        self.owner = None
        self.calls = []
        self.goals = []
        self.results = []
        self.subscriptions = []
        self.wall = 0.
        self.step_count = 0
        self.controller_active = True
        self.controller_type = 'uwa_cell_protection/PausableJointTrajectoryController'
        self.result_error = None

    def step(self):
        self.step_count += 1
        paused = self.step_count in (2, 3)
        self.wall += 3600. if paused else .01
        self.owner.status(String(data=json.dumps(dict(paused=paused, warnings=['data unavailable']))))
        if not paused:
            for row in self.results:
                row['ticks'] += 1
                if row['ticks'] >= 3 and not row['future'].done():
                    row['future'].set_result(Box(status=GoalStatus.STATUS_SUCCEEDED,
                        result=Box(error_code=-1 if self.result_error else 0,
                                   error_string=self.result_error or '')))

    def rpc(self, kind, name):
        def call(request):
            self.calls.append((name, request))
            if name.endswith('list_controllers'):
                value = Box(controller=[Box(name='joint_trajectory_controller',
                    type=self.controller_type,
                    state='active' if self.controller_active else 'inactive', claimed_interfaces=[])])
            elif name.endswith('switch_controller'):
                self.controller_active = True
                value = Box(ok=True)
            elif name == execution.ROOT+'/status':
                value = Box(success=True, message=json.dumps(dict(paused=False, warnings=['data unavailable'])))
            elif name == execution.ROOT+'/pause_all':
                value = Box(success=True, message='operator pause accepted')
            else:
                pytest.fail('Unexpected legacy or extra RPC: '+name)
            return completed(value)
        return Box(service_is_ready=lambda:True, call_async=call)

    def action(self, node, kind, endpoint):
        def send(goal):
            result = Future()
            self.goals.append((endpoint, goal))
            self.results.append(dict(future=result, ticks=0))
            def forbidden_cancel():
                pytest.fail('Pause must not cancel the retained action goal')
            return completed(Box(accepted=True, get_result_async=lambda:result,
                                 cancel_goal_async=forbidden_cancel))
        return Box(server_is_ready=lambda:True, send_goal_async=send)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('ROS_DOMAIN_ID', '67')
    monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST')
    wire = LocalTransport()
    monkeypatch.setattr(execution.MotionNode, '__init__', lambda *a, **k:None)
    monkeypatch.setattr(execution, 'SingleThreadedExecutor', lambda:Box(add_node=lambda _:None))
    monkeypatch.setattr(execution, 'ActionClient', wire.action)
    clock_type = execution.PauseAwareClock
    monkeypatch.setattr(execution, 'PauseAwareClock', lambda:clock_type(clock=lambda:wire.wall))

    class Client(execution.MinimalHardwareClient):
        def create_subscription(self, kind, topic, callback, qos):
            wire.subscriptions.append(topic)
            return Box()

        def create_client(self, kind, name):
            return wire.rpc(kind, name)

        def spin_once(self, timeout_sec=0.):
            wire.step()

        def get_clock(self):
            return Box(now=lambda:Box(nanoseconds=1_000_000_000))

    problem = Box(cfg={}, names={arm:joint_names(arm) for arm in ROBOT_IDS}, signature='model',
                  profiles={arm:dict(namespace='/'+arm) for arm in ROBOT_IDS})
    value = Client(problem, 'mock', ARMS)
    wire.owner = value
    value.state(String(data=json.dumps(dict(positions={joint:0. for names in problem.names.values() for joint in names},
                                           records={}, model_signature='model'))))
    return value, wire


def test_two_consecutive_groups_keep_goals_through_long_pause_without_legacy_calls(client):
    value, wire = client
    value.connect()
    first = {}
    value.follow_group(paths(), duration_s=1., segment=first)
    second = {}
    value.follow_group(paths(.1), duration_s=1., segment=second)
    assert first['executed'] and second['executed']
    assert wire.wall >= 7200.  # Paused wall time did not consume the execution budget.
    assert len(wire.goals) == 4 and not value.owned
    assert {topic for topic in wire.subscriptions} == {
        '/uwa_cell/protection/state', '/uwa_cell/protection/status'}
    assert [name for name, _ in wire.calls].count('/right_front/controller_manager/list_controllers') == 2
    assert not any(name.endswith('/pause_all') for name, _ in wire.calls)
    for pair in (wire.goals[:2], wire.goals[2:]):
        stamps = [goal.trajectory.header.stamp for _, goal in pair]
        assert stamps[0] == stamps[1]
    assert [list(goal.trajectory.points[-1].positions) for _, goal in wire.goals] == [[.1]*6, [.1]*6, [.2]*6, [.2]*6]


def test_state_gap_and_warning_do_not_add_a_live_stop(client):
    value, wire = client
    positions = dict(value.positions)
    value.status(String(data=json.dumps(dict(paused=False, warnings=['all collision data unavailable']))))
    value.state(String(data='invalid json'))
    value.health()
    assert value.positions == positions
    assert not wire.calls
    reply = value.stop(('right_front',))
    assert reply['accepted'] and reply['standstill_confirmed'] is False
    assert reply['native_stop_requested_for'] == []
    assert [name for name, _ in wire.calls] == ['/uwa_cell/protection/pause_all']


def test_activation_is_a_one_shot_controller_transition(client):
    value, wire = client
    wire.controller_active = False
    value.activate(['right_front'])
    switch = [(name, request) for name, request in wire.calls if name.endswith('switch_controller')]
    assert len(switch) == 1
    assert switch[0][1].activate_controllers == ['joint_trajectory_controller']
    value.health()
    assert len(wire.calls) == 2


def test_regular_controller_error_remains_an_error_without_implicit_global_pause(client):
    value, wire = client
    wire.result_error = 'Controller could not complete the trajectory'
    with pytest.raises(RuntimeError, match='could not complete'):
        value.follow_group(paths(), duration_s=1.)
    assert not any(name.endswith('/pause_all') for name, _ in wire.calls)


def test_stock_jtc_with_same_endpoint_is_rejected_before_sending_goal(client):
    value, wire = client
    wire.controller_type = 'joint_trajectory_controller/JointTrajectoryController'
    with pytest.raises(RuntimeError, match='[Pp]aus|[Cc]ontroller'):
        value.follow_group(paths(), duration_s=1.)
    assert wire.goals == []


def test_pause_aware_clock_excludes_long_pause_and_backward_wall_jump():
    now = [10.]
    clock = execution.PauseAwareClock(clock=lambda:now[0])
    now[0] = 11.
    assert clock.tick(False) == 1.
    now[0] = 9000.
    assert clock.tick(True) == 1.
    now[0] = 9000.5
    assert clock.tick(False) == 1.5
    now[0] = 8.
    assert clock.tick(False) == 1.5


def test_split_reordered_joint_samples_preserves_timing_and_derivatives():
    names = list(reversed(joint_names(ARMS[0]))) + joint_names(ARMS[1])
    trajectory = dict(joint_names=names, duration_s=2., points=[dict(time=t,
        positions=[t+i for i in range(12)], velocities=[i*.1 for i in range(12)],
        accelerations=[-i*.2 for i in range(12)]) for t in (0., .17, 2.)])
    parts = execution.split_trajectory(trajectory, ARMS)
    for arm, part in parts.items():
        goal = execution.build_goal(part)
        assert part['duration_s'] == 2.
        assert list(goal.trajectory.joint_names) == joint_names(arm)
        for source, target in zip(trajectory['points'], goal.trajectory.points):
            assert target.time_from_start.sec + target.time_from_start.nanosec/1e9 == source['time']
            indexes = [names.index(joint) for joint in joint_names(arm)]
            for key in ('positions', 'velocities', 'accelerations'):
                assert list(getattr(target, key)) == [source[key][i] for i in indexes]

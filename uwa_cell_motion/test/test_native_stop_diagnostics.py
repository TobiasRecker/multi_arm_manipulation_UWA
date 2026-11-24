"""Record the actual fallback request without changing dispatch/throttling."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
from rclpy.time import Time
from uwa_cell_motion import hardware_ports as ports
from uwa_cell_motion.guard_core import GuardState
from uwa_cell_motion.hardware_nodes import GuardJournal, HardwareGuard


class InlineThread:
    def __init__(self, target, daemon):self.target=target
    def start(self):self.target()
    def is_alive(self):return False


def port(monkeypatch, logger_failure=False):
    p=ports.StopPort.__new__(ports.StopPort)
    p.mode='hardware';p.profile={'id':'right_front'};p.native_thread=None
    p.native_sent=-float('inf');p.native_stop_events=[];p.native_ack=False;p.native_error=None
    logs=[];calls=[];clock=[1.]
    def log(message):
        if logger_failure:raise RuntimeError('logger unavailable')
        logs.append(message)
    p.node=SimpleNamespace(get_logger=lambda:SimpleNamespace(error=log))
    monkeypatch.setattr(ports.threading,'Thread',InlineThread)
    monkeypatch.setattr(ports.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(ports,'dashboard_stop',lambda profile:calls.append(profile))
    return p,calls,logs,clock


def test_reason_timestamps_ack_and_existing_throttle_are_retained(monkeypatch):
    p,calls,logs,clock=port(monkeypatch)
    p.native_stop('Manager verification stale')
    assert len(calls)==1 and p.native_ack
    assert p.native_stop_events==[dict(requested_monotonic_s=1.,reason='Manager verification stale',acknowledged=True,error=None)]
    clock[0]=1.1;p.native_stop('throttled second reason')
    assert len(calls)==1 and len(logs)==1 and len(p.native_stop_events)==1
    clock[0]=1.3;p.native_stop('Independent watchdog')
    assert len(calls)==2 and p.native_stop_events[-1]['reason']=='Independent watchdog'


def test_logging_failure_never_prevents_native_stop(monkeypatch):
    p,calls,logs,clock=port(monkeypatch,logger_failure=True)
    p.native_stop('Test fallback')
    assert len(calls)==1 and p.native_ack and p.native_stop_events[-1]['acknowledged']


def test_uncertain_stop_retains_error_without_fabricating_ack(monkeypatch):
    p,calls,logs,clock=port(monkeypatch)
    def fail(profile):raise OSError('connection ended')
    monkeypatch.setattr(ports,'dashboard_stop',fail)
    p.native_stop('Manager timeout')
    assert not p.native_ack and p.native_error=='connection ended'
    assert p.native_stop_events[-1]['error']=='connection ended'
    assert not p.native_stop_events[-1]['acknowledged']


def test_mock_stop_never_calls_real_dashboard(monkeypatch):
    p,calls,logs,clock=port(monkeypatch);p.mode='mock'
    p.native_stop('Mock only')
    assert p.native_ack and not calls and not logs and not p.native_stop_events


def test_idle_stop_port_does_not_poll_controller_management():
    p=ports.StopPort.__new__(ports.StopPort)
    p.cfg={'hold_config_max_age_s':1.0,'braking_acceleration_rad_s2':.2,'stop_latency_s':1.0}
    p.joints=['joint'];p.mode='mock'
    p.pending_hardware=p.pending=p.checking=p.switching=None
    p.hardware_received=p.parameter_received=p.received=-float('inf')
    p.hardware_sent=p.parameter_sent=p.sent=p.switch_started=p.switch_finished=-float('inf')
    p.hardware_observed_from=p.parameters_observed_from=p.list_observed_from=-float('inf')
    p.hold_invalidated=-float('inf')
    p.controllers=[];p.verified=p.hardware_verified=False
    p.error=p.native_error=None;p.native_ack=False
    p.native_thread=None;p.native_sent=-float('inf');p.native_stop_events=[]
    p.unheld_since=None;p.cancelled_owners=set();p.was_blocked=False
    p.stationary_hold=p.cell_held_quiet=p.quiet_partial_hold=p.reusing_hold=False
    p.refresh_for_release=False;p.quiet_transition_until=-float('inf')
    p.duplicate_activity_until=-float('inf');p.activity_holding=False;p.activity_publishers=0
    p.list_refresh_requested=p.hardware_refresh_requested=p.parameter_refresh_requested=False
    p.profile={'id':'right_front'}
    p.node=SimpleNamespace(get_logger=lambda:SimpleNamespace(error=lambda *_:None))
    calls=[]
    class IdleClient:
        def service_is_ready(self):return True
        def call_async(self,*args):calls.append(args);return SimpleNamespace(done=lambda:False)
    p.hardware=p.list=p.parameters=p.switch=IdleClient()
    p.cancels={}
    p.can_reuse_hold=lambda *args:False
    p.native_stop=lambda *_:None;p.cancel=lambda:None
    p.tick(False,False)
    assert calls==[]


def test_guard_journal_separates_new_latch_and_cause_during_hold():
    journal = GuardJournal()
    left = dict(arms=['left_front'], reason='SPEED LIMIT', measured_velocity_rad_s=.2)
    distance = dict(arms=['left_front'], reason='DISTANCE', clearance_m=.02, threshold_m=.04)
    right = dict(arms=['right_rear'], reason='SPEED LIMIT', measured_velocity_rad_s=.11)
    def tick(blocked, faults, latched, t):
        return journal.events(dict(blocked_arms=blocked, faults=faults, latched_causes=latched), t, True)
    assert tick(left['arms'], [left], [left], 1.) == [('STOP LATCHED', [dict(left, source_time_s=1.)])]
    labels = tick(['left_front','right_rear'], [distance,right], [left,distance,right], 2.)
    assert labels == [('STOP LATCHED', [dict(right, source_time_s=2.)]),
                      ('HELD CONDITION', [dict(distance, source_time_s=2.)])]
    assert tick(['left_front','right_rear'], [dict(distance, clearance_m=.01)], [left,distance,right], 3.) == []
    assert tick([], [], [], 4.) == []
    assert tick(left['arms'], [left], [left], 5.)[0][0] == 'STOP LATCHED'


def test_guard_journal_uses_current_error_even_with_empty_latched_causes():
    journal = GuardJournal()
    arm = ['right_front']
    error = dict(arms=arm, reason='Model evaluation failed')
    status = dict(blocked_arms=arm, faults=[error], latched_causes=[])
    assert journal.events(status, 2., False) == [('MONITOR WOULD STOP', [dict(error, source_time_s=2.)])]
    assert journal.events(status, 2.1, False) == []
    clock = dict(arms=arm, reason='CLOCK RESET', source_time_s=1.5)
    status.update(faults=[], latched_causes=[clock])
    assert journal.events(status, 2.2, False) == [('MONITOR HELD CONDITION', [clock])]


def test_guard_journal_partial_reset_uses_current_evidence_only_for_relatch():
    journal = GuardJournal()
    pair = ['left_front','right_front']
    old = dict(arms=pair, reason='DISTANCE', clearance_m=.03)
    status = dict(blocked_arms=pair, faults=[old], latched_causes=[old])
    journal.events(status, 1., True)
    status.update(blocked_arms=['right_front'], faults=[])
    assert journal.events(status, 2., True) == []
    now = dict(old, clearance_m=.02)
    status.update(blocked_arms=pair, faults=[now])
    assert journal.events(status, 3., True) == [('STOP LATCHED', [dict(now, source_time_s=3.)])]


def test_guard_publishes_even_when_diagnostics_fail():
    cfg = dict(rate_hz=20, standstill_window_s=.5, state_timeout_s=.2)
    guard = Mock(core=GuardState(cfg), cfg=cfg, mode='mock', armed=True,
                 sequence=0, tick_overruns=0, last_tick_duration_s=None, last_tick_start=None,
                 pairs=[], positions={}, records={}, model_match={}, pilot_channel=None, pilot_error=None,
                 signature='mock', hardware_signature='mock', instance='mock', journal=GuardJournal())
    guard.problem.binding = {}
    guard.get_clock.return_value.now.return_value = Time()
    guard.update.side_effect = ValueError('Incomplete geometry')
    after_publication = []
    guard.get_logger.return_value.error.side_effect = lambda msg: after_publication.append(guard.publisher.publish.called)
    HardwareGuard.tick(guard)
    assert after_publication == [True]
    message, = guard.get_logger.return_value.error.call_args.args
    assert json.loads(message.removeprefix('STOP LATCHED: '))[0]['reason'] == 'Incomplete geometry'
    guard.journal.events = Mock(side_effect=KeyError('unexpected diagnostic field'))
    HardwareGuard.tick(guard)
    assert guard.publisher.publish.call_count == guard.state_pub.publish.call_count == 2
    status = json.loads(guard.publisher.publish.call_args.args[0].data)
    assert set(status['blocked_arms']) == {'left_front','right_front','left_rear','right_rear'}

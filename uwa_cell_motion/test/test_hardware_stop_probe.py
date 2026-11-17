"""Independent standstill evidence must reject slow motion and short windows."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

spec=importlib.util.spec_from_file_location('stop_probe',Path(__file__).parents[2]/'tools/hardware_stop_probe.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def rows():
    return [dict(received=i*.05,q=[0.]*6,v=[0.]*6) for i in range(11)]


def test_measured_quiet_window_is_required():
    assert module.quiet_window(rows())
    assert not module.quiet_window(rows()[:8])
    assert not module.quiet_window([])


def test_slow_motion_cannot_pass_independent_standstill_check():
    values=rows()
    for r in values:r['v'][5]=.0003
    assert not module.quiet_window(values)


def test_position_drift_cannot_pass_even_if_reported_velocity_is_zero():
    values=rows()
    # Peak-to-peak is below0.2mrad, but the sustained0.3mrad/s trend fails.
    for i,r in enumerate(values):r['q'][5]=i*.000015
    assert not module.quiet_window(values)


def test_all_six_joints_must_be_quiet():
    values=rows();values[-1]['v'][0]=.003
    assert not module.quiet_window(values)


def test_stationary_encoder_jitter_is_separate_from_sustained_drift():
    values=rows()
    for i,r in enumerate(values):r['q'][5]=(-1 if i%2 else 1)*.00005
    assert module.quiet_window(values)



def test_motion_trigger_uses_elapsed_window_at_20_and_500_hz():
    for hz in (20,500):
        samples=[dict(received=i/hz,q=[0.]*5+[i/hz*.003],v=[0.]*5+[.003])
            for i in range(int(.3*hz)+1)]
        assert module.moving_window(samples,[0.]*6)
        assert not module.moving_window(samples[:3] if hz==500 else samples[:2],[0.]*6)
        samples[-1]['v'][5]=0.
        assert not module.moving_window(samples,[0.]*6)


def test_received_stop_metrics_keep_confirmation_and_low_speed_separate():
    import pytest
    import numpy as np
    path=Path(__file__).parents[2]/'tools/analyze_right_front_stop_test.py'
    spec=importlib.util.spec_from_file_location('stop_analysis',path)
    analyzer=importlib.util.module_from_spec(spec);spec.loader.exec_module(analyzer)
    rows=[];q=0.
    for i in range(250):
        t=i*.002;speed=.003 if t<.22 else 0.;q+=speed*.002
        rows.append(dict(received=t,device_stamp=t+10,q=[0.]*5+[q],v=[0.]*5+[speed]))
    record=dict(native_records=rows,stop_sent_monotonic=.2,confirmation_delay_s=.65,success=True)
    m=analyzer.analyze(record)['metrics']
    assert m['request_to_observed_low_speed_s']==pytest.approx(.02)
    assert m['confirmed_hold_window_delay_s']==.65
    record['native_records'][8]['device_stamp']=0.
    with pytest.raises(ValueError):analyzer.analyze(record)


class FakeFuture:
    def __init__(self,value,ready=lambda:True):
        self.value,self.ready=value,ready

    def done(self):return self.ready()
    def result(self):return self.value


def stopped_client(monkeypatch,status=None,error_code=0,error_string=''):
    """Cancel result arrives before the supervisor latch; no ROS participants."""
    clock=SimpleNamespace(now=1.037)
    monkeypatch.setattr(module,'time',SimpleNamespace(monotonic=lambda:clock.now))
    samples=[]
    observer=SimpleNamespace(error=None,snapshot=lambda:list(samples))
    response=SimpleNamespace(status=module.GoalStatus.STATUS_CANCELED if status is None else status,
        result=SimpleNamespace(error_code=error_code,error_string=error_string))
    goal_result=FakeFuture(response)
    client=SimpleNamespace(stop_sent=1.,stop_future=FakeFuture(SimpleNamespace(success=True)),
        observer=observer,guard=dict(faults=[],latched_causes=[],blocked_arms=[]),
        supervisor=dict(state='CLEAR',blocked_arms=[],ports={'right_front':dict(held=False)}),
        handles={'right_front':SimpleNamespace(accepted=True,get_result_async=lambda:goal_result)},
        probe_enabled=True,health_error=None,mutation=None,keep_moving=False)

    def health():
        if client.health_error:raise RuntimeError(client.health_error)

    def spin_once(_):
        start=clock.now
        clock.now+=.01
        for i in range(1,6):
            received=start+i*.002
            speed=.0015 if received<1.06 else .0003 if client.keep_moving else 0.
            samples.append(dict(received=received,q=[0.]*6,v=[0.]*5+[speed]))
        if clock.now>=1.08:
            client.supervisor.update(state='STOP REQUESTED',blocked_arms=['right_front'])
            client.supervisor['ports']['right_front']['held']=True
        if client.mutation:client.mutation(client,clock.now)

    client.health=health;client.spin_once=spin_once
    monkeypatch.setattr(module,'_follow',lambda *_:(_ for _ in ()).throw(
        RuntimeError('right_front: trajectory cancelled, preempted or failed: '+error_string)))
    return client,clock


@pytest.mark.parametrize('status',[module.GoalStatus.STATUS_CANCELED,module.GoalStatus.STATUS_ABORTED])
def test_own_acknowledged_cancel_retains_recording_through_quiet_window(monkeypatch,status):
    client,clock=stopped_client(monkeypatch,status)
    result=dict(success=False)
    module.follow_and_observe_stop(None,client,{},result)
    assert result['success'] and result['hold_confirmed'] and result['latch_confirmed']
    assert result['stage']=='STOP_CONFIRMED'
    assert result['expected_action_stop']['status']==status
    assert result['confirmation_delay_s']>=.51
    assert result['observation_window'][-1]['received']-result['observation_window'][0]['received']>=.45
    assert clock.now>1.5 and not client.probe_enabled


@pytest.mark.parametrize('case',['no_request','no_future','rejected_ack','real_action_error','wrong_status','action_error_text'])
def test_unrelated_cancellation_or_failed_stop_cannot_pass(monkeypatch,case):
    client,_=stopped_client(monkeypatch,
        status=module.GoalStatus.STATUS_UNKNOWN if case=='wrong_status' else None,
        error_code=-4 if case=='real_action_error' else 0,
        error_string='path tolerance violated' if case=='action_error_text' else '')
    if case=='no_request':client.stop_sent=None
    if case=='no_future':client.stop_future=None
    if case=='rejected_ack':client.stop_future=FakeFuture(SimpleNamespace(success=False))
    result=dict(success=False)
    with pytest.raises(RuntimeError):module.follow_and_observe_stop(None,client,{},result)
    assert not result['success'] and not client.probe_enabled


@pytest.mark.parametrize('error',['HARDWARE STATE STALE','HARDWARE SUPERVISION LOST',
    'Independent RTDE observer unavailable: timeout','Stationary obstacle/tool joint moved'])
def test_non_action_execution_fault_is_not_swallowed_after_own_stop(monkeypatch,error):
    client,_=stopped_client(monkeypatch)
    monkeypatch.setattr(module,'_follow',lambda *_:(_ for _ in ()).throw(RuntimeError(error)))
    with pytest.raises(RuntimeError,match=error):module.follow_and_observe_stop(None,client,{},dict(success=False))
    assert not client.probe_enabled


@pytest.mark.parametrize('fault',['freshness','observer','observer_stale','guard_fault','guard_cause','other_arm','watchdog'])
def test_post_cancel_observation_still_rejects_new_faults(monkeypatch,fault):
    client,_=stopped_client(monkeypatch)
    def inject(client,now):
        if now<1.15:return
        if fault=='freshness':client.health_error='HARDWARE STATE STALE'
        elif fault=='observer':client.observer.error='device clock stopped'
        elif fault=='observer_stale':client.observer.snapshot=lambda:[dict(received=0.,q=[0.]*6,v=[0.]*6)]
        elif fault=='guard_fault':client.guard['faults']=[dict(reason='SPEED LIMIT')]
        elif fault=='guard_cause':client.guard['latched_causes']=[dict(reason='DISTANCE')]
        elif fault=='other_arm':client.supervisor['blocked_arms'].append('left_front')
        elif fault=='watchdog':client.supervisor['state']='WATCHDOG LOST OR TRIPPED'
    client.mutation=inject
    result=dict(success=False)
    with pytest.raises(RuntimeError):module.follow_and_observe_stop(None,client,{},result)
    assert not result['success']


def test_ack_and_hold_without_measured_standstill_still_fail(monkeypatch):
    client,_=stopped_client(monkeypatch);client.keep_moving=True
    result=dict(success=False)
    with pytest.raises(RuntimeError,match='standstill/hold/latch'):
        module.follow_and_observe_stop(None,client,{},result)
    assert not result['success']


def test_normal_latch_return_also_records_full_stop_window(monkeypatch):
    client,_=stopped_client(monkeypatch)
    monkeypatch.setattr(module,'_follow',lambda *_:None)
    result=dict(success=False)
    module.follow_and_observe_stop(None,client,{},result)
    assert result['success'] and result['confirmation_delay_s']>=.51
    assert 'expected_action_stop' not in result


def test_probe_and_preparation_reject_hidden_faster_command_limit():
    path=Path(__file__).parents[2]/'tools/prepare_right_front_stop_test.py'
    spec=importlib.util.spec_from_file_location('stop_preparation',path)
    preparation=importlib.util.module_from_spec(spec);spec.loader.exec_module(preparation)
    for validate in (module.validate_slow_config,preparation.validate_slow_config):
        cfg=dict(velocity_limit_rad_s=.003,acceleration_limit_rad_s2=.006)
        validate(cfg)
        validate(dict(cfg,command_velocity_limit_rad_s=.003,
            joint_velocity_limits_rad_s={'right_front':[.003]*5+[.1]}))
        for command in (.1,0.,float('nan'),float('inf')):
            with pytest.raises(ValueError):validate(dict(cfg,command_velocity_limit_rad_s=command))

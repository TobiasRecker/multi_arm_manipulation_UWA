"""Independent standstill evidence must reject slow motion and short windows."""
import importlib.util
from pathlib import Path

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

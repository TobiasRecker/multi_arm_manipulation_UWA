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

"""Exercise episode cleanup and interpretation without starting ROS or Gazebo."""
import importlib.util
import json
from pathlib import Path
import signal
from types import SimpleNamespace
import pytest

spec=importlib.util.spec_from_file_location('exploration_driver',Path(__file__).parents[2]/'tools/explore_manipulation.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


def test_only_confirmed_stopped_episode_can_end(tmp_path):
    signals=[]
    launch=SimpleNamespace(poll=lambda:None,send_signal=signals.append,wait=lambda timeout:None)
    for state in [dict(state='RUNNING'),dict(state='FAILED',stop=dict(confirmed=False)),
                  dict(state='DONE',stop=dict(confirmed=True),group=dict(released=False))]:
        (tmp_path/'state.json').write_text(json.dumps(state))
        with pytest.raises(RuntimeError):driver.end_world(launch,tmp_path)
        assert not signals
    (tmp_path/'state.json').write_text(json.dumps(dict(state='FAILED',stop=dict(confirmed=True))))
    driver.end_world(launch,tmp_path)
    assert signals==[signal.SIGINT]


def test_numerical_or_configured_limit_is_not_material_failure():
    loads=dict(coverage_complete=True,pad_load_reference_n=50.,pads={'right_front/left':dict(maximum_mean_load_upper_bound_n=51.)})
    assert driver.classify({},dict(passed=True),loads,{})=='user_load_reference_exceeded_not_proven_material_damage'
    assert driver.classify({},dict(passed=False),loads,{'reason':'DISTANCE'})=='configured_stopping_reserve'
    assert driver.classify({},dict(passed=False),loads,{'reason':'STATE STALE'})=='telemetry_or_lease_failure'
    loads['coverage_complete']=False
    assert driver.classify({},dict(passed=True),loads,{})=='incomplete_force_measurement'

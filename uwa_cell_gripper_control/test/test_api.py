from types import SimpleNamespace as NS
import pytest
from uwa_cell_gripper_control.api import ARMS,OPEN,CLOSE,SET_OPENING,ACTIVATE,endpoint,raw_target,normalize,capabilities


@pytest.mark.parametrize('percent,target',[(100,0),(0,255),(50,128),(25,191),(75,64)])
def test_relative_stroke_is_bounded_and_monotonic(percent,target):
    assert raw_target(SET_OPENING,percent)==target


def test_named_operations_and_activation_are_distinct():
    for operation,target,raw_operation in [(OPEN,0,1),(CLOSE,255,1),(ACTIVATE,0,2)]:
        goal=NS(operation=operation,opening_percent=0.,speed_raw=16,force_raw=7,timeout_s=15.)
        assert normalize(goal)==(raw_operation,target,16,7,15.)


@pytest.mark.parametrize('value',[-1,101,float('nan'),float('inf')])
def test_bad_width_cannot_become_a_raw_command(value):
    with pytest.raises(ValueError):raw_target(SET_OPENING,value)


def test_invalid_operation_and_arm_never_reach_transport():
    with pytest.raises(ValueError):raw_target(99,50)
    with pytest.raises(ValueError):endpoint('../other_arm','hardware')
    with pytest.raises(ValueError):endpoint('right_front','simulation')


def test_all_four_arms_have_separate_mock_and_hardware_namespaces():
    assert len(ARMS)==4
    assert len({endpoint(r,'hardware') for r in ARMS})==4
    assert not {endpoint(r,'hardware') for r in ARMS}&{endpoint(r,'mock') for r in ARMS}


def test_capabilities_never_claim_physical_calibration_or_automatic_release():
    info=capabilities('left_front','hardware',False,0,32)
    assert not info['physical_force_calibrated'] and not info['physical_width_calibrated']
    assert not info['actuation_enabled'] and not info['automatic_activation'] and not info['automatic_release']
    assert info['max_force_raw']==0

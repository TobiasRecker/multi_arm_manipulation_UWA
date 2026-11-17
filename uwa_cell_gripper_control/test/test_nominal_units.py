import pytest
from uwa_cell_gripper_control.api import nominal_opening_percent,nominal_force_raw,raw_target,SET_OPENING,CLOSE
from uwa_cell_gripper_control.client import GripperClient


def test_nominal_50mm_and_endpoints():
    assert nominal_opening_percent(50)==pytest.approx(58.8235294118)
    assert raw_target(SET_OPENING,nominal_opening_percent(50))==105
    assert nominal_opening_percent(0)==0 and nominal_opening_percent(85)==100


def test_nominal_force_range_and_50n():
    assert nominal_force_raw(20)==0 and nominal_force_raw(235)==255
    assert nominal_force_raw(50)==36


@pytest.mark.parametrize('value',[-1,86,float('inf'),float('nan')])
def test_invalid_width_is_rejected_without_clamping(value):
    with pytest.raises(ValueError):nominal_opening_percent(value)


@pytest.mark.parametrize('value',[0,19,236,float('nan')])
def test_invalid_nominal_force_is_rejected_without_clamping(value):
    with pytest.raises(ValueError):nominal_force_raw(value)


class Spy(GripperClient):
    def __init__(self):self.calls=[]
    def command(self,operation,**kwargs):
        self.calls.append((operation,kwargs));return dict(success=True)


def test_helpers_keep_existing_ros_command_path_and_label_nominal_units():
    client=Spy();width=client.set_width_mm(50);force=client.close_gripper(force_n=50)
    assert client.calls[0][0]==SET_OPENING and client.calls[0][1]['opening_percent']==pytest.approx(58.8235294118)
    assert client.calls[1][0]==CLOSE and client.calls[1][1]['force_raw']==36
    assert width['nominal_request']['width_mm']==50 and force['nominal_request']['force_n']==50
    assert client.close_gripper(force_raw=7)['success']
    for args in ({},{'force_raw':0,'force_n':20}):
        with pytest.raises(ValueError):client.close_gripper(**args)

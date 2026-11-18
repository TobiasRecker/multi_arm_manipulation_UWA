"""Separate commanded timing from unchanged monitored limits/model identity."""
import copy
import numpy as np
import pytest
from uwa_cell_tasks.hardware_carton_approach import slow_trajectory, canonical_base, unloaded_open_status, unloaded_guard_ready


def test_time_dilation_preserves_geometry_and_does_not_mutate_original():
    original = dict(duration_s=10., waypoints=[[0.]*6,[1.]*6],
                    joint_names=['q'+str(i) for i in range(6)],
                    points=[dict(time=t,positions=[t]*6,velocities=[.003]*6,accelerations=[.004]*6) for t in [0.,10.]])
    before = copy.deepcopy(original); slower = slow_trajectory(original, .003, .0015)
    assert original == before and slower['waypoints'] == original['waypoints']
    assert slower['duration_s'] == 20.
    for p,q in zip(slower['points'], original['points']):
        assert p['positions'] == q['positions'] and p['time'] == 2*q['time']
        np.testing.assert_allclose(p['velocities'], np.array(q['velocities'])/2)
        np.testing.assert_allclose(p['accelerations'], np.array(q['accelerations'])/4)


@pytest.mark.parametrize('command', [0., -.1, .004, float('nan')])
def test_command_profile_cannot_increase_the_guard_bound(command):
    with pytest.raises(ValueError):slow_trajectory({}, .003, command)


def test_equal_command_and_monitor_keeps_the_original_timing():
    trajectory=dict(duration_s=10.,points=[dict(time=10.,positions=[1.],velocities=[.1],accelerations=[.2])])
    assert slow_trajectory(trajectory,.1,.1)==trajectory


def test_inactive_open_gripper_does_not_require_an_activation_stroke():
    status=dict(observed=True,busy=False,registers=dict(ACT=0,STA=0,OBJ=0,FLT=0,PRE=0,POS=3))
    assert unloaded_open_status(status)
    for key,value in [('OBJ',2),('POS',128),('PRE',255),('FLT',1),('STA',1)]:
        changed=copy.deepcopy(status);changed['registers'][key]=value
        assert not unloaded_open_status(changed)
    status['busy']=True
    assert not unloaded_open_status(status)


def test_clear_guard_has_physical_quiet_without_a_guard_latched_stop():
    guard=dict(standstill_confirmed=False,stationary_arms=['left_front','left_rear','right_front','right_rear'],faults=[])
    assert unloaded_guard_ready(guard)
    guard['stationary_arms'].pop()
    assert not unloaded_guard_ready(guard)
    guard['stationary_arms'].append('right_rear');guard['faults']=['stale']
    assert not unloaded_guard_ready(guard)


def test_supplemental_object_does_not_hide_a_changed_robot_link():
    base = '<robot name="a"><link name="world"/><link name="arm"/></robot>'
    extra = '<link name="pregrasp_carton_static"/><joint name="pregrasp_carton_anchor" type="fixed"/>'
    augmented = base.replace('</robot>', extra+'</robot>')
    assert canonical_base(base) == canonical_base(augmented)
    assert canonical_base(base) != canonical_base(augmented.replace('name="arm"','name="changed"'))


def test_generated_visual_paths_are_irrelevant_but_collision_geometry_is_bound():
    xml = '<robot name="a"><link name="arm"><visual><geometry><mesh filename="/output1/board.dae"/></geometry></visual><collision><geometry><sphere radius=".1"/></geometry></collision></link></robot>'
    assert canonical_base(xml) == canonical_base(xml.replace('/output1/', '/output2/'))
    assert canonical_base(xml) != canonical_base(xml.replace('radius=".1"','radius=".2"'))

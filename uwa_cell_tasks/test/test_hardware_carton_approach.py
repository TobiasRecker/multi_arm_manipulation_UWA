"""Separate commanded timing from unchanged monitored limits/model identity."""
import copy
import numpy as np
import pytest
from uwa_cell_tasks.hardware_carton_approach import slow_trajectory, canonical_base


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


@pytest.mark.parametrize('command', [0., -.1, .003, .004, float('nan')])
def test_command_profile_cannot_increase_the_guard_bound(command):
    with pytest.raises(ValueError):slow_trajectory({}, .003, command)


def test_supplemental_object_does_not_hide_a_changed_robot_link():
    base = '<robot name="a"><link name="world"/><link name="arm"/></robot>'
    extra = '<link name="pregrasp_carton_static"/><joint name="pregrasp_carton_anchor" type="fixed"/>'
    augmented = base.replace('</robot>', extra+'</robot>')
    assert canonical_base(base) == canonical_base(augmented)
    assert canonical_base(base) != canonical_base(augmented.replace('name="arm"','name="changed"'))

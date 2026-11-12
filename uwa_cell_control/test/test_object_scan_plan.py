"""Target transforms, local IK and collision-swept serial scheduling."""
from itertools import product
from types import SimpleNamespace
import numpy as np
import pytest
from uwa_cell_control.object_scan_plan import box_points, look_at, solve_ik, checked_schedule
from uwa_cell_description.configuration import joint_names


def test_view_frame_is_right_handed_and_looks_at_target_including_vertical_view():
    for eye in ([.3, -.4, .5], [0., 0., 1.]):
        pose = look_at(eye, [0, 0, 0])
        np.testing.assert_allclose(pose[:3, :3].T @ pose[:3, :3], np.eye(3), atol=1e-12)
        assert np.isclose(np.linalg.det(pose[:3, :3]), 1)
        direction = -np.asarray(eye) / np.linalg.norm(eye)
        np.testing.assert_allclose(pose[:3, 2], direction)
    with pytest.raises(ValueError):
        look_at([0, 0, 0], [0, 0, 0])
    for size in ([0, 1, 1], [1, float('nan'), 1]):
        with pytest.raises(ValueError):
            box_points(size)
    assert box_points([.2, .4, .6]).shape == (8, 3)


def test_local_ik_cannot_use_distant_branch_for_small_camera_offset():
    names = list('abcdef')
    def forward(state):
        pose = np.eye(4)
        pose[:3, 3] = [state[n] for n in names[:3]]
        return pose
    chain = SimpleNamespace(forward=forward)
    desired = np.eye(4)
    desired[:3, 3] = [.02, -.03, 0]
    q = solve_ik(chain, names, desired, np.zeros(6), [(-2, 2)] * 6, max_change=.35)
    np.testing.assert_allclose(q[:3], desired[:3, 3], atol=1e-5)
    desired[0, 3] = 1.
    assert solve_ik(chain, names, desired, np.zeros(6), [(-2, 2)] * 6, max_change=.35) is None


def test_small_move_with_blocked_midpoint_is_rejected_not_endpoint_only():
    rid = 'right_front'; names = joint_names(rid)
    start = dict(zip(names, np.zeros(6)))
    target = [0.02, 0, 0, 0, 0, 0]
    model = SimpleNamespace(check=lambda q: (not .008 < q[names[0]] < .012, []))
    candidates = {rid: [dict(joints=target, camera_world=np.eye(4).tolist())]}
    assert checked_schedule(model, start, candidates, lambda _: True) is None


def test_scheduler_changes_order_when_only_one_serial_order_is_clear():
    a, b = 'right_front', 'left_rear'
    na, nb = joint_names(a), joint_names(b)
    start = {j: 0. for j in na + nb}
    # A may leave home only after B reached its target.
    model = SimpleNamespace(check=lambda q: (q[na[0]] < 1e-8 or q[nb[0]] >= .0199, []))
    entry = dict(joints=[.02, 0, 0, 0, 0, 0], camera_world=np.eye(4).tolist())
    found = checked_schedule(model, start, {a: [entry], b: [entry]}, lambda _: True)
    assert [s['arm'] for s in found[1]] == [b, a]
    assert all(len(s['points']) >= 21 for s in found[1])
    assert found[1][1]['start'][nb[0]] == .02
    assert checked_schedule(model, start, {a: [entry], b: [entry]}, lambda _: False) is None

from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from teacher_episode_core import sphere_table_gap, control_map
from generate_teacher_episodes import goal_proposals, direct_task
from uwa_cell_motion.two_arm_teacher import pose_at


@pytest.mark.parametrize('point', [[.7, .3, .2], [.1, .02, .01]])
def test_table_clearance_gradient_in_world_coordinates(point):
    table = np.eye(4)
    table[:3, :3] = Rotation.from_euler('xyz', [.3, -.2, .7]).as_matrix()
    table[:3, 3] = [.6, -.1, .9]
    points = np.array([point]) @ table[:3, :3].T + table[:3, 3]
    radii = np.array([.04])
    half = np.array([.3, .2, .07])
    gap, index, normal = sphere_table_gap(points, radii, table, half)
    assert index == 0
    assert (gap > 0) == (point[0] > .3)
    eps = 1e-6
    fd = []
    for axis in range(3):
        shift = np.eye(3)[axis] * eps
        fd.append((sphere_table_gap(points + shift, radii, table, half)[0]
                   - sphere_table_gap(points - shift, radii, table, half)[0]) / (2 * eps))
    assert np.allclose(normal, fd, atol=1e-8, rtol=0)


def test_control_map_for_noncommuting_rotations():
    start = np.eye(4)
    goal = np.eye(4)
    goal[:3, :3] = Rotation.from_euler('xyz', [.8, -.5, .4]).as_matrix()
    goal[:3, 3] = [.1, -.2, .05]
    task = direct_task('test', start, goal)
    controls = np.random.default_rng(18).normal(0, .1, (6, 6))
    s, eps = .61, 1e-6
    base = pose_at(start, task, s, controls)
    analytic = control_map(s, controls)
    for k in range(36):
        perturbation = np.eye(36)[k].reshape(6, 6) * eps
        plus = pose_at(start, task, s, controls + perturbation)
        minus = pose_at(start, task, s, controls - perturbation)
        fd = np.r_[(plus[:3, 3] - minus[:3, 3]) / (2 * eps),
                   (Rotation.from_matrix(plus[:3, :3] @ base[:3, :3].T).as_rotvec()
                    - Rotation.from_matrix(minus[:3, :3] @ base[:3, :3].T).as_rotvec()) / (2 * eps)]
        assert np.allclose(analytic[:, k], fd, atol=1e-8, rtol=0)


def test_goals_explore_from_current_pose_without_changing_start():
    anchor = np.eye(4)
    anchor[:3, 3] = [.1, .2, 1.]
    start = anchor.copy()
    start[:3, 3] += [.2, -.1, .08]
    start[:3, :3] = Rotation.from_euler('xyz', [.2, -.4, .6]).as_matrix()
    original = start.copy()
    goals = goal_proposals(start, anchor, [], 19)
    assert len(goals) >= 5
    assert np.array_equal(start, original)
    assert np.allclose(goals, goal_proposals(start, anchor, [], 19))
    for goal in goals:
        assert np.linalg.norm(goal[:3, 3] - start[:3, 3]) >= .09
        assert np.all(goal[:3, 3] >= anchor[:3, 3] + [-.28, -.28, 0])
        assert np.all(goal[:3, 3] <= anchor[:3, 3] + [.30, .28, .24])
        task = direct_task('goal', start, goal)
        assert np.allclose(pose_at(start, task, 0, np.zeros((6, 6))), start)
        assert np.allclose(pose_at(start, task, 1, np.zeros((6, 6))), goal)

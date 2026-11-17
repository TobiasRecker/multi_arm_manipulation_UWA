from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from uwa_cell_motion.candidates import enumerate_candidates
from uwa_cell_motion.common import ROBOT_IDS, config, joint_names, nominal_state
from uwa_cell_motion.planning import Problem
from uwa_cell_motion.selection import pareto_flags, select_goals


@pytest.fixture(scope='module')
def problem(tmp_path_factory):
    return Problem(tmp_path_factory.mktemp('selection-model'),
                   config(Path(__file__).parents[1]/'config/motion.yaml'))


@pytest.fixture(scope='module')
def source(problem):
    start = nominal_state(problem.layout)
    goals = {}
    for r in ROBOT_IDS:
        q = [start[j] for j in joint_names(r)]; q2 = q.copy(); q2[-1] += .05
        goals[r] = {'alternatives': [q, q2]}
    # Stage 2 must search beyond the small stage-1 output cap.
    return enumerate_candidates(problem, dict(start=start, goals=goals), max_combinations=1)


def test_full_retained_product_rechecked_and_metrics_reconstructed(problem, source):
    result = select_goals(problem, source)
    assert result['search']['retained_product_exhausted']
    assert result['search']['combinations_checked'] == 16
    assert result['search']['valid_combinations'] == 16
    assert result['search']['pair_cache_entries'] == 24
    assert not result['executable'] and not result['search']['complete_ik']
    assert result['recommended_id'] == result['policy_winners']['shortest']
    for c in result['evaluated_combinations']:
        state = dict(source['start'])
        for r, q in c['goals'].items(): state.update(zip(joint_names(r), q))
        assert problem.collision.check(state)[0]
        world = problem.spheres.world(state)
        assert len(c['pair_clearances']) == 6
        for pair in c['pair_clearances']:
            actual = problem.spheres.nearest(world, *pair['arms'])['clearance_m']
            assert actual == pytest.approx(pair['clearance_m'], abs=1e-12)
            assert actual >= pair['threshold_m']
    assert all(c['pareto'] for c in result['combinations'])


def test_pareto_tradeoffs_dominance_and_numerical_equivalence():
    def row(cost, gap, reserve):
        return dict(start_distance_sum_rad=cost, min_pair_clearance_m=gap,
                    joint_limit_reserve_fraction=reserve)
    records = [row(1,.1,.2), row(2,.2,.2), row(2,.1,.1), row(1+1e-8,.1,.2), row(3,.1,.3)]
    assert pareto_flags(records) == [True, True, False, True, True]
    assert pareto_flags([]) == []


@pytest.mark.parametrize('field', ['model', 'mesh', 'config', 'nan', 'bounds', 'target', 'provenance', 'ids', 'start'])
def test_stale_or_tampered_sources_fail(problem, source, field):
    s = deepcopy(source); r = s['selected'][0]; c = s['candidates'][r][0]
    if field == 'model': s['model_signature'] = 'other'
    if field == 'mesh': s['mesh_sha256'] = {}
    if field == 'config': s['configuration']['model_margin_m'] += .01
    if field == 'nan': c['positions'][0] = float('nan')
    if field == 'bounds': c['positions'][0] = 100.
    if field == 'target': c['positions'][0] += .1
    if field == 'provenance': c['alternative_indices'] = [99]
    if field == 'ids': s['candidates'][r][1]['id'] = c['id']
    if field == 'start': s['start'].pop(next(iter(s['start'])))
    with pytest.raises(ValueError): select_goals(problem, s)


def test_scores_recomputed_not_trusted(problem, source):
    s = deepcopy(source)
    for cs in s['candidates'].values():
        for c in cs: c['start_distance_rad'] = -1000
    result = select_goals(problem, s)
    assert min(c['start_distance_sum_rad'] for c in result['evaluated_combinations']) == 0


def test_cartesian_provenance_is_rechecked(problem, source):
    from scipy.spatial.transform import Rotation
    from uwa_cell_gazebo.charuco_views import Chain
    s = deepcopy(source); r = s['selected'][0]; alternatives = []
    chain = Chain(problem.description, 'world', r+'_tool0')
    for goal in s['goal_options'][r]['alternatives']:
        pose = chain.forward(dict(s['start'], **dict(zip(joint_names(r), goal))))
        alternatives.append(dict(frame_id='world', target_link=r+'_tool0',
                                 pose=dict(position=pose[:3,3].tolist(),
                                           orientation_xyzw=Rotation.from_matrix(pose[:3,:3]).as_quat().tolist())))
    s['goal_options'][r] = dict(alternatives=alternatives)
    assert select_goals(problem, s)['combinations']
    alternatives[0]['pose']['position'][0] += .01
    with pytest.raises(ValueError, match='no longer matches'):
        select_goals(problem, s)


def test_truncation_and_deadline_do_not_claim_optimality(problem, source):
    result = select_goals(problem, source, max_checks=1)
    assert not result['search']['retained_product_exhausted']
    assert result['search']['combinations_checked'] == 1
    result = select_goals(problem, source, budget_s=1e-12)
    assert result['search']['deadline_reached']
    assert result['status'] == 'NO_VALID_COMBINATION_FOUND'
    assert result['recommended_id'] is None


def test_full_scene_rejection_retained(problem, source, monkeypatch):
    monkeypatch.setattr(problem, 'check', lambda request, q: False)
    result = select_goals(problem, source)
    assert not result['combinations']
    assert result['search']['rejected_full_scene'] == 16


def test_diagonal_pair_reserve_is_not_skipped(problem, source, monkeypatch):
    nearest = problem.spheres.nearest
    # Diagonal is not in the legacy four-neighbour stop-reserve list.
    diagonal = {'left_front', 'right_rear'}
    def distance(world, a, b):
        return {'clearance_m': -.01} if {a,b} == diagonal else nearest(world, a, b)
    monkeypatch.setattr(problem.spheres, 'nearest', distance)
    result = select_goals(problem, source)
    assert not result['combinations']
    assert result['search']['rejected_pair_reserve'] == 16


def test_empty_candidate_set_is_explicitly_finite_not_task_infeasible(problem, source):
    s = deepcopy(source); s['candidates'][s['selected'][0]] = []
    result = select_goals(problem, s)
    assert result['search']['retained_product_size'] == 0
    assert result['search']['retained_product_exhausted']
    assert not result['search']['complete_ik']
    assert not result['combinations']


def test_single_arm_checks_all_pairs_including_fixed_arms(problem, source):
    s = deepcopy(source); r = s['selected'][0]
    s['selected'] = [r]; s['candidates'] = {r: s['candidates'][r]}
    s['goal_options'] = {r: s['goal_options'][r]}
    result = select_goals(problem, s)
    assert result['search']['combinations_checked'] == 2
    assert all(len(c['pair_clearances']) == 6 for c in result['combinations'])

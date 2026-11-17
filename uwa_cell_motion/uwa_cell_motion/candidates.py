"""Offline goal alternatives. Results are endpoints, never executable paths."""
import argparse
import heapq
import itertools
import json
from pathlib import Path
import tempfile
import time
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from .common import ROBOT_IDS, config, dump, joint_names
from uwa_cell_gazebo.charuco_views import Chain


class SearchDeadline(Exception):
    pass


def _pose(problem, rid, goal):
    if goal.get('frame_id') != 'world':
        raise ValueError('Cartesian goal requires frame_id=world')
    link = goal.get('target_link', '')
    links = {x.get('name') for x in ET.fromstring(problem.description).findall('link')}
    if not link.startswith(rid + '_') or link not in links:
        raise ValueError('Target link must exist and belong to the selected arm')
    pose = goal['pose']
    xyz = np.asarray(pose['position'], float)
    quat = np.asarray(pose['orientation_xyzw'], float)
    if (xyz.shape != (3,) or quat.shape != (4,) or not np.isfinite(np.r_[xyz, quat]).all()
            or abs(np.linalg.norm(quat) - 1) > 1e-5):
        raise ValueError('Expected finite position and unit XYZW quaternion')
    return Chain(problem.description, 'world', link), xyz, Rotation.from_quat(quat).as_matrix()


def enumerate_candidates(problem, request, *, seeds=16, seed=64, budget_s=30.,
                         max_per_arm=8, max_checks=256, max_combinations=16):
    """Bounded multistart IK, then cost-ordered joint endpoint validation.

    Arm candidates are kinematic only: filtering against other selected arms at
    their start would incorrectly discard solutions where those arms move away.
    No completeness, path existence or execution claim is made.
    """
    if request.get('schema_version', 1) != 1:
        raise ValueError('Unsupported schema')
    for name, value in [('seeds', seeds), ('max_per_arm', max_per_arm),
                        ('max_checks', max_checks), ('max_combinations', max_combinations)]:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(name + ' must be a positive integer')
    if not np.isfinite(budget_s) or budget_s <= 0:
        raise ValueError('budget_s must be positive and finite')
    start = {str(k): float(v) for k, v in request['start'].items()}
    required = {j for names in problem.names.values() for j in names}
    if not required <= start.keys() or not np.isfinite(list(start.values())).all():
        raise ValueError('Complete finite start including grippers required')
    for j, (lo, hi) in problem.collision.bounds.items():
        if j in start and not lo <= start[j] <= hi:
            raise ValueError('Start outside joint bounds: ' + j)
    goals = request['goals']
    if not goals or set(goals) - set(ROBOT_IDS):
        raise ValueError('Expected known nonempty arm goals')
    selected = [r for r in ROBOT_IDS if r in goals]
    # Validate every alternative before search, even if a deadline later expires.
    prepared = {}
    for rid in selected:
        alternatives = goals[rid].get('alternatives') if isinstance(goals[rid], dict) else None
        alternatives = [goals[rid]] if alternatives is None else alternatives
        if not isinstance(alternatives, list) or not alternatives:
            raise ValueError('alternatives must be a nonempty list')
        prepared[rid] = []
        for goal in alternatives:
            if isinstance(goal, list) or 'positions' in goal:
                q = np.asarray(goal if isinstance(goal, list) else goal['positions'], float)
                if q.shape != (6,) or not np.isfinite(q).all():
                    raise ValueError('Joint goal requires six finite radians')
                prepared[rid].append(('joint', q))
            else:
                prepared[rid].append(('pose', _pose(problem, rid, goal)))
    begun = time.monotonic(); deadline = begun + budget_s
    rng = np.random.default_rng(seed)
    candidates = {}; diagnostics = {}; expired = False
    for rid in selected:
        names = joint_names(rid)
        bounds = np.asarray([problem.collision.bounds[j] for j in names]).T
        initial = np.asarray([start[j] for j in names])
        found = []; attempts = 0; rejected = 0
        for index, (kind, target) in enumerate(prepared[rid]):
            if time.monotonic() >= deadline:
                expired = True; break
            if kind == 'joint':
                solutions = [(target, None, None)]
            else:
                chain, xyz, rotation = target
                def residual(q):
                    if time.monotonic() >= deadline:
                        raise SearchDeadline()
                    actual = chain.forward(dict(start, **dict(zip(names, q))))
                    return np.r_[actual[:3, 3] - xyz,
                                 Rotation.from_matrix(actual[:3, :3] @ rotation.T).as_rotvec()]
                solutions = []
                for guess in [initial] + [rng.uniform(*bounds) for _ in range(seeds - 1)]:
                    attempts += 1
                    try:
                        fit = least_squares(residual, np.clip(guess, bounds[0]+1e-9, bounds[1]-1e-9),
                                            bounds=bounds, max_nfev=150)
                        error = residual(fit.x)
                    except SearchDeadline:
                        expired = True; break
                    pe, re = float(np.linalg.norm(error[:3])), float(np.linalg.norm(error[3:]))
                    if pe <= 1e-4 and re <= 1e-4:
                        solutions.append((fit.x, pe, re))
                    else:
                        rejected += 1
            for q, pe, re in solutions:
                if np.any(q < bounds[0]) or np.any(q > bounds[1]):
                    rejected += 1; continue
                duplicate = next((x for x in found if np.linalg.norm(q - x['positions']) < 1e-4), None)
                if duplicate is not None:
                    if index not in duplicate['alternative_indices']:
                        duplicate['alternative_indices'].append(index)
                    continue
                found.append(dict(positions=q.tolist(), alternative_indices=[index],
                                  position_error_m=pe, orientation_error_rad=re,
                                  start_distance_rad=float(np.linalg.norm(q-initial)),
                                  validation='KINEMATIC_ONLY'))
            if expired:
                break
        found.sort(key=lambda x: x['start_distance_rad'])
        diagnostics[rid] = dict(solver_attempts=attempts, rejected_solutions=rejected,
                                found_before_cap=len(found), truncated=len(found) > max_per_arm)
        candidates[rid] = [dict(c, id=f'{rid}:{i}') for i, c in enumerate(found[:max_per_arm])]
    combinations = []; checked = 0; heap = []; seen = set()
    def push(indices):
        if indices in seen: return
        seen.add(indices)
        cost = sum(candidates[r][i]['start_distance_rad'] for r, i in zip(selected, indices))
        heapq.heappush(heap, (cost, indices))
    if all(candidates[r] for r in selected): push(tuple(0 for _ in selected))
    names = [j for rid in selected for j in joint_names(rid)]
    temporary = dict(start=start, joint_names=names)
    while heap and checked < max_checks and len(combinations) < max_combinations:
        if time.monotonic() >= deadline:
            expired = True; break
        cost, indices = heapq.heappop(heap)
        values = [candidates[r][i] for r, i in zip(selected, indices)]
        q = np.concatenate([c['positions'] for c in values]); checked += 1
        valid = problem.check(temporary, q)
        if valid:
            # Baseline neighbor stop reserves plus static clearance on ALL six pairs.
            world = problem.spheres.world(problem.state(temporary, q))
            clearances = []
            for a, b in itertools.combinations(ROBOT_IDS, 2):
                d = problem.spheres.nearest(world, a, b)['clearance_m']
                clearances.append(dict(arms=[a, b], clearance_m=float(d)))
            if min(x['clearance_m'] for x in clearances) >= problem.cfg['model_margin_m']:
                combinations.append(dict(candidate_ids=[c['id'] for c in values],
                                         goals={r: c['positions'] for r, c in zip(selected, values)},
                                         start_distance_sum_rad=cost, pair_clearances=clearances,
                                         validation='MODEL_ENDPOINT_VALID'))
        for axis, rid in enumerate(selected):
            nxt = list(indices); nxt[axis] += 1
            if nxt[axis] < len(candidates[rid]): push(tuple(nxt))
    return dict(schema_version=1, artifact_type='offline_goal_candidates', executable=False,
                status='CANDIDATES_FOUND' if combinations else 'NO_VALID_COMBINATION_FOUND',
                start=start, goal_options=goals, selected=selected,
                candidates=candidates, combinations=combinations, configuration=dict(problem.cfg),
                diagnostics=diagnostics, model_signature=problem.signature,
                mesh_sha256=problem.spheres.geometry.assets,
                search=dict(seed=seed, seeds_per_pose=seeds, budget_s=budget_s,
                            elapsed_s=time.monotonic()-begun, deadline_reached=expired,
                            combinations_checked=checked, combinations_pending=len(heap),
                            max_checks=max_checks, max_combinations=max_combinations,
                            max_per_arm=max_per_arm, position_tolerance_m=1e-4,
                            orientation_tolerance_rad=1e-4, deduplication_rad=1e-4,
                            retained_product_exhausted=not heap, complete_ik=False),
                assumptions=['Fixed model base poses and frozen gripper states',
                             'Only endpoints checked; no path or trajectory validated',
                             'No solution found is not proof of infeasibility'])


def main():
    parser = argparse.ArgumentParser(description='Offline multi-UR goal candidates; no motion commands')
    parser.add_argument('request'); parser.add_argument('--output', required=True)
    parser.add_argument('--layout'); parser.add_argument('--config')
    parser.add_argument('--seeds', type=int, default=16); parser.add_argument('--seed', type=int, default=64)
    parser.add_argument('--budget', type=float, default=30.)
    parser.add_argument('--max-per-arm', type=int, default=8)
    parser.add_argument('--max-checks', type=int, default=256)
    parser.add_argument('--max-combinations', type=int, default=16)
    args = parser.parse_args()
    if Path(args.output).exists(): parser.error('Output exists; choose a fresh path')
    from .planning import Problem
    with tempfile.TemporaryDirectory(prefix='uwa-goals-') as directory:
        problem = Problem(directory, config(args.config), args.layout)
        result = enumerate_candidates(problem, json.loads(Path(args.request).read_text()),
                                      seeds=args.seeds, seed=args.seed, budget_s=args.budget,
                                      max_per_arm=args.max_per_arm, max_checks=args.max_checks,
                                      max_combinations=args.max_combinations)
        dump(args.output, result)
    print(json.dumps(dict(status=result['status'], candidates={r:len(v) for r,v in result['candidates'].items()},
                          combinations=len(result['combinations']), search=result['search'])))
    if not result['combinations']: raise SystemExit(2)


if __name__ == '__main__': main()

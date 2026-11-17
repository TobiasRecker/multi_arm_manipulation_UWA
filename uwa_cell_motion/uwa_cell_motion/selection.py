"""Model-bound joint endpoint selection; no paths, ROS nodes or execution."""
import argparse
import hashlib
import heapq
import itertools
import json
import math
from pathlib import Path
import tempfile
import time

import numpy as np
from scipy.spatial.transform import Rotation

from .candidates import _pose
from .common import ROBOT_IDS, config, dump, joint_names


def validate_source(problem, source):
    """Recheck saved kinematics and provenance instead of trusting labels/scores."""
    if (source.get('schema_version') != 1 or
            source.get('artifact_type') != 'offline_goal_candidates' or
            source.get('executable') is not False):
        raise ValueError('Expected non-executable offline_goal_candidates schema 1')
    if (source['model_signature'] != problem.signature or
            source['mesh_sha256'] != problem.spheres.geometry.assets or
            source['configuration'] != problem.cfg):
        raise ValueError('Candidate model, meshes or configuration changed; regenerate candidates')
    start = source['start']
    required = {j for names in problem.names.values() for j in names}
    if not required <= start.keys() or not np.isfinite(list(start.values())).all():
        raise ValueError('Complete finite start including grippers required')
    for j, (lo, hi) in problem.collision.bounds.items():
        if j in start and not lo <= start[j] <= hi:
            raise ValueError('Start outside joint bounds: ' + j)
    selected = source['selected']
    if (not selected or selected != [r for r in ROBOT_IDS if r in selected] or
            set(selected) != set(source['candidates']) or
            set(selected) != set(source['goal_options'])):
        raise ValueError('Candidate arms and goal options must match')
    candidates = {}; ids = set()
    for rid in selected:
        names = joint_names(rid)
        bounds = np.asarray([problem.collision.bounds[j] for j in names]).T
        initial = np.asarray([start[j] for j in names])
        goal = source['goal_options'][rid]
        alternatives = goal.get('alternatives', [goal]) if isinstance(goal, dict) else [goal]
        targets = []
        for alternative in alternatives:
            if isinstance(alternative, list) or 'positions' in alternative:
                q = np.asarray(alternative if isinstance(alternative, list) else alternative['positions'], float)
                if q.shape != (6,) or not np.isfinite(q).all():
                    raise ValueError('Invalid source joint target')
                targets.append(('joint', q))
            else:
                targets.append(('pose', _pose(problem, rid, alternative)))
        candidates[rid] = []
        for c in source['candidates'][rid]:
            q = np.asarray(c['positions'], float)
            if (q.shape != (6,) or not np.isfinite(q).all() or
                    np.any(q < bounds[0]) or np.any(q > bounds[1])):
                raise ValueError('Invalid candidate joint bounds: ' + rid)
            if not isinstance(c['id'], str) or c['id'] in ids:
                raise ValueError('Candidate IDs must be unique strings')
            ids.add(c['id'])
            indices = c['alternative_indices']
            if not indices or any(type(i) is not int or not 0 <= i < len(targets) for i in indices):
                raise ValueError('Invalid candidate alternative provenance')
            for i in indices:
                kind, target = targets[i]
                if kind == 'joint':
                    valid = np.linalg.norm(q-target) <= 1e-4
                else:
                    chain, xyz, rotation = target
                    actual = chain.forward(dict(start, **dict(zip(names, q))))
                    valid = (np.linalg.norm(actual[:3, 3]-xyz) <= 1e-4 and
                             np.linalg.norm(Rotation.from_matrix(actual[:3, :3] @ rotation.T).as_rotvec()) <= 1e-4)
                if not valid:
                    raise ValueError('Candidate no longer matches its task alternative: ' + c['id'])
            reserve = np.minimum(q-bounds[0], bounds[1]-q)/(bounds[1]-bounds[0])
            candidates[rid].append(dict(c, start_distance_rad=float(np.linalg.norm(q-initial)),
                                        joint_limit_reserve_fraction=float(reserve.min())))
        candidates[rid].sort(key=lambda c: (c['start_distance_rad'], c['id']))
    return candidates


def pareto_flags(records):
    """Min displacement, max clearance and joint reserve; documented 1e-6 rounding."""
    if not records:
        return []
    metrics = np.round([[c['start_distance_sum_rad'], -c['min_pair_clearance_m'],
                         -c['joint_limit_reserve_fraction']] for c in records], 6)
    unique, inverse = np.unique(metrics, axis=0, return_inverse=True)
    flags = np.asarray([not np.any(np.all(unique <= row, axis=1) &
                                  np.any(unique < row, axis=1)) for row in unique])
    return flags[inverse].tolist()


def select_goals(problem, source, *, budget_s=60., max_checks=4096, shortlist_size=3):
    """Re-evaluate the retained product, keep Pareto alternatives and explain choices.

    A cached six-pair compatibility graph rejects conflicting candidate pairs.
    Every surviving complete endpoint also passes the existing full-scene check.
    The budget covers enumeration, not model loading, input validation or ranking.
    """
    if not np.isfinite(budget_s) or budget_s <= 0:
        raise ValueError('budget_s must be positive and finite')
    for name, value in [('max_checks', max_checks), ('shortlist_size', shortlist_size)]:
        if type(value) is not int or value < 1:
            raise ValueError(name + ' must be a positive integer')
    candidates = validate_source(problem, source)
    selected = source['selected']; start = source['start']
    pairs = list(itertools.combinations(ROBOT_IDS, 2))
    thresholds = {tuple(p['arms']): p['threshold_m'] for p in problem.thresholds()}
    thresholds = {pair: max(problem.cfg['model_margin_m'],
                            thresholds.get(pair, thresholds.get(pair[::-1], 0.))) for pair in pairs}
    names = [j for rid in selected for j in joint_names(rid)]
    request = dict(start=start, joint_names=names)
    begun = time.monotonic(); deadline = begun + budget_s
    geometry = {}; pair_cache = {}; heap = []; seen = set(); evaluated = []
    checked = 0; rejected_pair = 0; rejected_scene = 0; expired = False

    def arm_world(rid, candidate):
        key = (rid, candidate['id'] if candidate else None)
        if key not in geometry:
            state = dict(start)
            if candidate:
                state.update(zip(joint_names(rid), candidate['positions']))
            geometry[key] = problem.spheres.world(state)[rid]
        return geometry[key]

    def push(indices):
        if indices in seen:
            return
        seen.add(indices)
        cost = sum(candidates[r][i]['start_distance_rad'] for r, i in zip(selected, indices))
        heapq.heappush(heap, (cost, indices))

    if all(candidates[r] for r in selected):
        push(tuple(0 for _ in selected))
    while heap and checked < max_checks:
        if time.monotonic() >= deadline:
            expired = True; break
        cost, indices = heapq.heappop(heap); checked += 1
        chosen = {r: candidates[r][i] for r, i in zip(selected, indices)}
        clearances = []
        for a, b in pairs:
            ca, cb = chosen.get(a), chosen.get(b)
            key = (a, ca['id'] if ca else None, b, cb['id'] if cb else None)
            if key not in pair_cache:
                world = {a: arm_world(a, ca), b: arm_world(b, cb)}
                pair_cache[key] = float(problem.spheres.nearest(world, a, b)['clearance_m'])
            clearances.append(dict(arms=[a, b], clearance_m=pair_cache[key], threshold_m=thresholds[a, b]))
        if any(c['clearance_m'] < c['threshold_m'] for c in clearances):
            rejected_pair += 1
        elif not problem.check(request, np.concatenate([chosen[r]['positions'] for r in selected])):
            rejected_scene += 1
        else:
            evaluated.append(dict(id='goal-'+'-'.join(map(str, indices)),
                                  candidate_ids=[chosen[r]['id'] for r in selected],
                                  goals={r: chosen[r]['positions'] for r in selected},
                                  start_distance_sum_rad=cost, pair_clearances=clearances,
                                  min_pair_clearance_m=min(c['clearance_m'] for c in clearances),
                                  min_pair_reserve_m=min(c['clearance_m']-c['threshold_m'] for c in clearances),
                                  joint_limit_reserve_fraction=min(c['joint_limit_reserve_fraction'] for c in chosen.values()),
                                  validation='MODEL_ENDPOINT_VALID'))
        for axis, rid in enumerate(selected):
            nxt = list(indices); nxt[axis] += 1
            if nxt[axis] < len(candidates[rid]):
                push(tuple(nxt))
    enumeration_s = time.monotonic()-begun
    for c, flag in zip(evaluated, pareto_flags(evaluated)):
        c['pareto'] = flag
    frontier = [c for c in evaluated if c['pareto']]
    def cost_key(c):
        return (round(c['start_distance_sum_rad'], 6), -round(c['min_pair_clearance_m'], 6),
                -round(c['joint_limit_reserve_fraction'], 6), c['id'])
    policies = {}
    if frontier:
        policies = dict(shortest=min(frontier, key=cost_key)['id'],
                        clearance=min(frontier, key=lambda c: (-round(c['min_pair_clearance_m'], 6), cost_key(c)))['id'],
                        joint_reserve=min(frontier, key=lambda c: (-round(c['joint_limit_reserve_fraction'], 6), cost_key(c)))['id'])
    by_id = {c['id']: c for c in evaluated}; shortlist = []
    for cid in [*policies.values(), *(c['id'] for c in sorted(frontier, key=cost_key))]:
        if cid not in [c['id'] for c in shortlist] and len(shortlist) < shortlist_size:
            shortlist.append(by_id[cid])
    for c in shortlist:
        c['selection_reasons'] = [k for k, v in policies.items() if v == c['id']] or ['pareto_alternative']
    total = math.prod(len(candidates[r]) for r in selected)
    return dict(schema_version=1, artifact_type='offline_goal_selection', executable=False,
                status='GOALS_SELECTED' if shortlist else 'NO_VALID_COMBINATION_FOUND',
                start=start, selected=selected, goal_options=source['goal_options'], candidates=candidates,
                combinations=shortlist, evaluated_combinations=evaluated,
                recommended_id=policies.get('shortest'), policy_winners=policies,
                configuration=dict(problem.cfg), model_signature=problem.signature,
                mesh_sha256=problem.spheres.geometry.assets,
                source_search=source['search'], source_diagnostics=source['diagnostics'],
                search=dict(budget_s=budget_s, enumeration_s=enumeration_s, elapsed_s=time.monotonic()-begun,
                            max_checks=max_checks, combinations_checked=checked, retained_product_size=total,
                            retained_product_exhausted=checked == total, deadline_reached=expired,
                            rejected_pair_reserve=rejected_pair, rejected_full_scene=rejected_scene,
                            valid_combinations=len(evaluated), pareto_combinations=len(frontier),
                            pair_cache_entries=len(pair_cache), complete_ik=False),
                selection=dict(shortlist_size=shortlist_size, metric_rounding_decimals=6,
                               objectives=['min start_distance_sum_rad', 'max min_pair_clearance_m',
                                           'max joint_limit_reserve_fraction'],
                               default_policy='shortest', optimality_scope='evaluated retained candidates only'),
                assumptions=['Fixed bases and grippers; unselected arms remain at start',
                             'All task alternatives are treated as equally acceptable',
                             'Joint displacement is a heuristic, not path length or duration',
                             'Joint-limit reserve is fractional distance to nearest bound, at most 0.5; not manipulability',
                             'Pair gaps use conservative spheres; full-scene FCL additionally checks each valid endpoint',
                             'Only endpoints checked; no path, timing or moving-base trajectory validated',
                             'No solution found is not proof of task infeasibility'])


def main():
    parser = argparse.ArgumentParser(description='Select joint offline goal candidates; no motion')
    parser.add_argument('candidates'); parser.add_argument('--output', required=True)
    parser.add_argument('--layout'); parser.add_argument('--config')
    parser.add_argument('--budget', type=float, default=60.)
    parser.add_argument('--max-checks', type=int, default=4096)
    parser.add_argument('--shortlist-size', type=int, default=3)
    args = parser.parse_args()
    if Path(args.output).exists():
        parser.error('Output exists; choose a fresh path')
    raw = Path(args.candidates).read_bytes(); source = json.loads(raw)
    from .planning import Problem
    with tempfile.TemporaryDirectory(prefix='uwa-select-') as directory:
        problem = Problem(directory, config(args.config), args.layout)
        result = select_goals(problem, source, budget_s=args.budget,
                              max_checks=args.max_checks, shortlist_size=args.shortlist_size)
        result['source_sha256'] = hashlib.sha256(raw).hexdigest()
        dump(args.output, result)
    print(json.dumps(dict(status=result['status'], recommended_id=result['recommended_id'],
                          policy_winners=result['policy_winners'], search=result['search'])))
    if not result['combinations']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()

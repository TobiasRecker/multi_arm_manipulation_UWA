"""Offline swept-geometry/virtual-wall analysis of checked object-scan paths.

No ROS clients. Projection separation covers arbitrary relative path progress,
including a stopped arm, in the frozen collision model. It is not a certificate
for unmeasured real mounting errors, cables, people or the entire reachable workspace.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial import ConvexHull, QhullError
from scipy.optimize import linprog
import yaml

from uwa_cell_description.configuration import ROBOT_IDS, joint_names, gripper_joint
from .parking import digest
from .view_geometry import VisibilityModel, origin


def mesh_vertices(path):
    data = Path(path).read_bytes()
    if len(data) >= 84 and len(data) == 84 + 50 * struct.unpack_from('<I', data, 80)[0]:
        dtype = np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attr', '<u2')])
        points = np.frombuffer(data, dtype=dtype, offset=84)['vertices'].reshape(-1, 3).astype(float)
    else:
        points = np.asarray([list(map(float, line.split()[1:])) for line in data.decode().splitlines()
                             if line.strip().startswith('vertex ')], float)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.isfinite(points).all():
        raise ValueError('Invalid collision mesh')
    points = np.unique(points, axis=0)
    # Convex hull has identical directional support to the original triangle mesh.
    try:
        if len(points) >= 4:
            points = points[ConvexHull(points).vertices]
    except QhullError:
        pass
    return points


def corners(half):
    return np.asarray([[x, y, z] for x in (-half[0], half[0])
                       for y in (-half[1], half[1]) for z in (-half[2], half[2])])


class Body:
    def __init__(self, arm, link, index, collision, radii):
        self.arm, self.link, self.index = arm, link, index
        self.fixed = origin(collision.find('origin'))
        shape = list(collision.find('geometry'))[0]
        self.kind = shape.tag
        self.asset = None
        if self.kind == 'mesh':
            self.asset = Path(shape.get('filename').removeprefix('file://')).resolve()
            scale = np.fromstring(shape.get('scale', '1 1 1'), sep=' ')
            if scale.shape != (3,) or not np.isfinite(scale).all() or not np.all(scale):
                raise ValueError('Invalid mesh scale')
            self.vertices = mesh_vertices(self.asset) * scale
            self.visual_vertices = self.vertices
        elif self.kind == 'box':
            half = np.fromstring(shape.get('size'), sep=' ') / 2
            if half.shape != (3,) or not np.isfinite(half).all() or min(half) <= 0:
                raise ValueError('Invalid collision box')
            self.vertices = corners(half)
            self.visual_vertices = self.vertices
        elif self.kind in ('sphere', 'cylinder'):
            self.radius = float(shape.get('radius'))
            self.half_length = float(shape.get('length')) / 2 if self.kind == 'cylinder' else self.radius
            if not np.isfinite([self.radius, self.half_length]).all() or min(self.radius, self.half_length) <= 0:
                raise ValueError('Invalid collision primitive')
            self.visual_vertices = corners([self.radius, self.radius, self.half_length])
        else:
            raise ValueError('Unsupported collision geometry: ' + self.kind)
        if not np.isfinite(self.visual_vertices).all():
            raise ValueError('Nonfinite collision geometry')
        local = self.visual_vertices @ self.fixed[:3, :3].T + self.fixed[:3, 3]
        self.link_radius = float(np.linalg.norm(local, axis=1).max())
        self.radii = radii(self.link_radius)

    def support(self, frames, directions):
        T = frames[self.link] @ self.fixed
        local_n = directions @ T[:3, :3]
        offset = directions @ T[:3, 3]
        if self.kind in ('mesh', 'box'):
            dots = self.vertices @ local_n.T
            return dots.min(axis=0) + offset, dots.max(axis=0) + offset
        if self.kind == 'sphere':
            extent = self.radius * np.linalg.norm(local_n, axis=1)
        else:
            extent = self.radius * np.linalg.norm(local_n[:, :2], axis=1) + self.half_length * abs(local_n[:, 2])
        return offset - extent, offset + extent

    def world_visual(self, frames):
        T = frames[self.link] @ self.fixed
        return self.visual_vertices @ T[:3, :3].T + T[:3, 3]


class Geometry:
    def __init__(self, description, arm_joints):
        self.fk = VisibilityModel(description, arm_joints)
        self.names = arm_joints
        root = ET.fromstring(description)
        self.joints = {j.get('name'): j for j in root.findall('joint')}
        parent = {j.find('child').get('link'): j for j in self.joints.values()}
        self.bodies = {rid: [] for rid in arm_joints}
        self.assets = {}
        for link in root.findall('link'):
            name = link.get('name')
            arm = next((rid for rid in arm_joints if name.removeprefix('calibrated/').startswith(rid + '_')), None)
            if arm is None:
                continue
            path, current = [], name
            while current != 'world':
                joint = parent[current]
                path.insert(0, joint)
                current = joint.find('parent').get('link')
            for index, collision in enumerate(link.findall('collision')):
                body = Body(arm, name, index, collision, lambda radius, path=path, arm=arm:
                            self.displacement_radii(path, radius, arm))
                self.bodies[arm].append(body)
                if body.asset:
                    self.assets[str(body.asset)] = hashlib.sha256(body.asset.read_bytes()).hexdigest()
        if any(not bodies for bodies in self.bodies.values()):
            raise ValueError('All analyzed arms need collision geometry')

    def dependency(self, joint):
        mimic = joint.find('mimic')
        if mimic is None:
            return joint.get('name'), 1.
        source, coefficient = self.dependency(self.joints[mimic.get('joint')])
        return source, coefficient * float(mimic.get('multiplier', 1))

    def displacement_radii(self, path, body_radius, arm):
        """Triangle-inequality bound from each joint axis to any body point."""
        radii = np.zeros(len(self.names[arm]))
        for i, joint in enumerate(path):
            source, coefficient = self.dependency(joint)
            if source not in self.names[arm]:
                continue
            kind = joint.get('type')
            if kind in ('revolute', 'continuous'):
                radius = body_radius
                for descendant in path[i + 1:]:
                    radius += np.linalg.norm(origin(descendant.find('origin'))[:3, 3])
                    if descendant.get('type') == 'prismatic':
                        limit = descendant.find('limit')
                        radius += max(abs(float(limit.get('lower'))), abs(float(limit.get('upper'))))
                axis = joint.find('axis')
                norm = np.linalg.norm(np.fromstring(axis.get('xyz', '1 0 0'), sep=' ')) if axis is not None else 1.
                radii[self.names[arm].index(source)] += abs(coefficient) * radius * norm
            elif kind == 'prismatic':
                radii[self.names[arm].index(source)] += abs(coefficient)
            else:
                raise ValueError('Moving joint has unsupported kind')
        return radii


def validated_steps(plan, arms):
    if plan.get('purpose') != 'object_scan_review_only' or not plan.get('paths_checked') or not plan.get('common_view_found'):
        raise ValueError('A successful checked object-scan report is required')
    state = dict(plan['start'])
    initial = []
    for index, step in enumerate(plan['steps']):
        rid = step['arm']
        if rid not in arms:
            raise ValueError('Unknown arm in scan path')
        names = arms[rid]
        if set(step['start']) != set(state) or any(abs(step['start'][j] - state[j]) > 1e-7 for j in state):
            raise ValueError('Path start/continuity differs from the checked sequence')
        points = step['points']
        q0 = np.array([state[j] for j in names]);q1 = np.asarray(step['target'], float)
        if q1.shape != q0.shape or not np.isfinite(q1).all():
            raise ValueError('Invalid joint target')
        times = np.asarray([p['time'] for p in points], float)
        if len(points) < 2 or not np.isfinite(times).all() or times[0] != 0 or np.any(np.diff(times) <= 0):
            raise ValueError('Invalid trajectory times')
        duration = times[-1]
        delta = q1 - q0
        for p in points:
            u = p['time'] / duration
            s, ds, dds = 10*u**3-15*u**4+6*u**5, 30*u**2-60*u**3+30*u**4, 60*u-180*u**2+120*u**3
            expected = [q0 + s*delta, ds*delta/duration, dds*delta/duration**2]
            for key, value in zip(('positions', 'velocities', 'accelerations'), expected):
                actual = np.asarray(p[key], float)
                if actual.shape != q0.shape or not np.isfinite(actual).all() or not np.allclose(actual, value, atol=1e-7, rtol=1e-7):
                    raise ValueError('Only the original monotone quintic connections can be bounded')
        if step['purpose'] == 'common_object_initial_view':
            initial.append(rid)
        elif step['purpose'] != 'additional_object_view':
            raise ValueError('Unknown scan phase')
        state.update(zip(names, q1))
        if index == len(arms)-1:
            common = plan['common_state']
            if set(common) != set(state) or any(abs(common[j]-state[j]) > 1e-7 for j in state):
                raise ValueError('Common view state differs from the checked paths')
    if initial != [s['arm'] for s in plan['steps'][:len(arms)]] or set(initial) != set(arms) or len(initial) != len(arms):
        raise ValueError('One initial view per arm must precede extra views')
    return plan['steps']


def pair_planes(geometry, start):
    frames = geometry.fk.frames(start)
    bases = {rid: frames[rid + '_base_link'][:3, 3] for rid in geometry.names}
    planes = []
    for a, b in combinations(geometry.names, 2):
        normal = bases[b] - bases[a]
        normal[2] = 0.
        if np.linalg.norm(normal) < 1e-6:
            raise ValueError('Base positions need distinct horizontal projections')
        normal /= np.linalg.norm(normal)
        midpoint = (bases[a] + bases[b]) / 2
        planes.append(dict(a=a, b=b, normal=normal, offset=float(normal @ midpoint), midpoint=midpoint))
    return planes


def separation(a_min, a_max, b_min, b_max, offset, clearance):
    """Signed wall penetration and a sufficient arbitrary-phase separator."""
    gap = float(b_min - a_max)
    return dict(a_wall_intrusion_bound_m=max(0., float(a_max - offset)),
                b_wall_intrusion_bound_m=max(0., float(offset - b_min)),
                a_wall_clearance_bound_m=float(offset - a_max),
                b_wall_clearance_bound_m=float(b_min - offset),
                midpoint_wall_with_buffer_pass=bool(a_max <= offset-clearance/2 and b_min >= offset+clearance/2),
                projected_gap_bound_m=gap,
                phase_independent_separation_proven=bool(gap >= clearance and gap > 1e-9),
                separator_shift_from_midpoint_m=float((a_max+b_min)/2 - offset) if gap >= clearance else None)


def hull_xy(points):
    points = np.unique(np.asarray(points).reshape(-1, 2), axis=0)
    try:
        return points[ConvexHull(points).vertices].tolist()
    except QhullError:
        return points.tolist()


def hull_xyz(points):
    points = np.unique(np.asarray(points).reshape(-1, 3), axis=0)
    try:
        return points[ConvexHull(points).vertices].tolist()
    except QhullError:
        return points.tolist()


def alternative_separator(A, B, pad_a, pad_b, clearance):
    """Find a candidate plane; certify it directly with support of BOTH hulls.

    Optimizer convergence is never the evidence for separation: the final
    normal's support gap, minus continuous-motion padding, is the evidence.
    """
    A, B = np.asarray(A), np.asarray(B)
    # Five optimization variables, irrespective of hull size. A dense QP with
    # one weight per hull vertex would need quadratic memory for long paths.
    constraints = np.concatenate([
        np.column_stack([A, -np.ones(len(A)), np.zeros(len(A))]),
        np.column_stack([-B, np.zeros(len(B)), np.ones(len(B))])])
    fit = linprog([0., 0., 0., 1., -1.], A_ub=constraints,
                  b_ub=np.zeros(len(constraints)), bounds=[(-1., 1.)]*3+[(None, None)]*2,
                  method='highs')
    if fit.x is None:
        return dict(proven=False, reason='No candidate hull separator from linear program')
    direction = fit.x[:3]
    if not np.isfinite(direction).all() or np.linalg.norm(direction) < 1e-8:
        return dict(proven=False, reason='No nonzero candidate hull separator')
    normal = direction / np.linalg.norm(direction)
    a_max, b_min = float((A @ normal).max()+pad_a), float((B @ normal).min()-pad_b)
    gap = b_min-a_max
    return dict(proven=bool(gap >= clearance and gap > 1e-9),
                normal_world=normal.tolist(), offset_m=(a_max+b_min)/2,
                gap_bound_m=gap, a_support_bound_m=a_max, b_support_bound_m=b_min,
                optimizer_converged=bool(fit.success),
                method='separating support plane of sampled convex hulls plus continuous-motion radius bounds')


def bodywise_separator(A, B, clearance):
    """Sufficient separation of the union of individual swept collision bodies."""
    checked = 0
    unresolved = []
    minimum = None
    for a in A:
        for b in B:
            checked += 1
            pa, pb = np.asarray(a['hull']), np.asarray(b['hull'])
            pad_a, pad_b = a['padding_m'], b['padding_m']
            # Cheap separating directions before a five-variable LP.
            directions = np.r_[np.eye(3), -np.eye(3)]
            gaps = (pb @ directions.T).min(axis=0)-(pa @ directions.T).max(axis=0)-pad_a-pad_b
            k = int(np.argmax(gaps))
            candidate = dict(proven=bool(gaps[k] >= clearance), normal_world=directions[k].tolist(),
                             gap_bound_m=float(gaps[k]), method='coordinate support plane')
            if not candidate['proven']:
                candidate = alternative_separator(pa, pb, pad_a, pad_b, clearance)
            record = dict(a_link=a['link'], a_collision=a['collision_index'],
                          b_link=b['link'], b_collision=b['collision_index'], **candidate)
            if not candidate['proven']:
                unresolved.append(record)
            elif minimum is None or candidate['gap_bound_m'] < minimum['gap_bound_m']:
                minimum = record
    return dict(proven=not unresolved, body_pairs_checked=checked,
                unresolved_pairs=unresolved, smallest_proven_gap=minimum,
                method='every pair of per-collision-body swept hulls separated for arbitrary path progress')


def sweep(geometry, plan, planes, scope, defaults, tracking_error_rad=0.):
    directions = np.asarray([p['normal'] for p in planes])
    phase_start = plan['start'] if scope != 'extra' else plan['common_state']
    selected = [(i, step) for i, step in enumerate(plan['steps']) if
                scope == 'all' or (scope == 'initial') == (step['purpose'] == 'common_object_initial_view')]
    by_arm = {}
    for rid, names in geometry.names.items():
        bodies = geometry.bodies[rid]
        lows = np.full((len(bodies), len(planes)), np.inf)
        highs = np.full_like(lows, -np.inf)
        sample_lows, sample_highs = lows.copy(), highs.copy()
        witnesses = [[None] * len(planes) for _ in bodies]
        low_witnesses = [[None] * len(planes) for _ in bodies]
        tracking_pad = np.asarray([sum(body.radii)*tracking_error_rad for body in bodies])
        body_pad = tracking_pad.copy()
        motion_pad = np.zeros(len(bodies))
        samples = 0
        xyz = [[] for _ in bodies]
        own = [(i, s) for i, s in selected if s['arm'] == rid]
        # Include held start/end poses even for an arm with no extra views.
        segments = [(-1, dict(start=phase_start, points=[dict(positions=[phase_start[j] for j in names])]))] + own
        for step_index, step in segments:
            previous_q = previous_lo = previous_hi = None
            for point_index, point in enumerate(step['points']):
                q = np.asarray(point['positions'])
                state = dict(defaults)
                state.update(step['start'])
                state.update(zip(names, q))
                frames = geometry.fk.frames(state)
                lo, hi = [], []
                for body_index, body in enumerate(bodies):
                    low, high = body.support(frames, directions)
                    lo.append(low);hi.append(high)
                    xyz[body_index].append(body.world_visual(frames))
                lo, hi = np.asarray(lo), np.asarray(hi)
                for body_index, plane_index in zip(*np.where(hi > sample_highs)):
                    witnesses[body_index][plane_index] = dict(step=step_index, point=point_index,
                        link=bodies[body_index].link, collision_index=bodies[body_index].index)
                for body_index, plane_index in zip(*np.where(lo < sample_lows)):
                    low_witnesses[body_index][plane_index] = dict(step=step_index, point=point_index,
                        link=bodies[body_index].link, collision_index=bodies[body_index].index)
                sample_lows, sample_highs = np.minimum(sample_lows, lo), np.maximum(sample_highs, hi)
                lows, highs = np.minimum(lows, lo-tracking_pad[:, None]), np.maximum(highs, hi+tracking_pad[:, None])
                if previous_q is not None:
                    # On each monotone quintic segment, q=q0+s*dq with one scalar s.
                    # Any intermediate point is at most half a joint-interval from
                    # its nearest endpoint. Bound each body with sum(R_j*|dq_j|)/2.
                    interpolated = np.asarray([body.radii @ abs(q-previous_q)/2 for body in bodies])
                    pad = interpolated + tracking_pad
                    lows = np.minimum(lows, np.minimum(previous_lo, lo)-pad[:, None])
                    highs = np.maximum(highs, np.maximum(previous_hi, hi)+pad[:, None])
                    body_pad = np.maximum(body_pad, pad)
                    motion_pad = np.maximum(motion_pad, interpolated)
                previous_q, previous_lo, previous_hi = q, lo, hi
                samples += 1
        body_hulls = [dict(link=body.link, collision_index=body.index, padding_m=float(body_pad[k]),
                           hull=hull_xyz(np.concatenate(xyz[k]))) for k,body in enumerate(bodies)]
        by_arm[rid] = dict(min=lows.min(axis=0), max=highs.max(axis=0),
                          sampled_min=sample_lows.min(axis=0), sampled_max=sample_highs.max(axis=0),
                          high_witness=[witnesses[int(np.argmax(sample_highs[:, k]))][k] for k in range(len(planes))],
                          low_witness=[low_witnesses[int(np.argmin(sample_lows[:, k]))][k] for k in range(len(planes))],
                          max_interpolation_padding_m=float(motion_pad.max()),
                          max_tracking_padding_m=float(tracking_pad.max()),
                          max_total_padding_m=float(body_pad.max()),
                          body_count=len(bodies), samples=samples,
                          body_hulls=body_hulls,
                          xyz_hull=hull_xyz(np.concatenate([h['hull'] for h in body_hulls])))
        by_arm[rid]['xy_hull'] = hull_xy(np.asarray(by_arm[rid]['xyz_hull'])[:, :2])
    return by_arm


def groups_from_pairs(arms, pairs):
    safe = {frozenset((p['a'], p['b'])) for p in pairs if p['phase_independent_separation_proven']}
    groups = [list(combo) for count in range(2, len(arms)+1) for combo in combinations(arms, count)
              if all(frozenset(pair) in safe for pair in combinations(combo, 2))]
    return [g for g in groups if not any(set(g) < set(other) for other in groups)]


def parallel_review_schedule(plan, phases, arms):
    """Reorder only phase-independent arm chains; retain every unproven order.

    The source has contiguous per-arm blocks. For any unproven pair, its earlier
    entire chain still finishes before the later starts. Thus the stationary
    state assumed by its original path checks is retained. Other pairs have a
    continuous arbitrary-progress separation proof. No trajectory is changed.
    """
    batches = []
    for scope in ('initial', 'extra'):
        indexed = [(i, s) for i, s in enumerate(plan['steps']) if
                   (scope=='initial') == (s['purpose']=='common_object_initial_view')]
        order = list(dict.fromkeys(s['arm'] for _,s in indexed))
        run_order = [s['arm'] for k,(_,s) in enumerate(indexed) if k==0 or s['arm']!=indexed[k-1][1]['arm']]
        if run_order != order:
            raise ValueError('Parallel review requires contiguous original arm blocks')
        chains = {rid: [i for i,s in indexed if s['arm']==rid] for rid in order}
        safe = {frozenset((p['a'], p['b'])) for p in phases[scope]['pairs']
                if p['phase_independent_separation_proven']}
        dependencies = {rid: set() for rid in order}
        for a,b in combinations(order, 2):
            if frozenset((a,b)) not in safe:
                dependencies[b].add(a)
        completed = set()
        while len(completed)<len(order):
            ready = [rid for rid in order if rid not in completed and dependencies[rid]<=completed]
            if not ready:
                raise ValueError('No acyclic parallel review order')
            for round_index in range(max(len(chains[rid]) for rid in ready)):
                indices = [chains[rid][round_index] for rid in ready if round_index<len(chains[rid])]
                batches.append(dict(phase=scope, source_step_indices=indices,
                                    arms=[plan['steps'][i]['arm'] for i in indices],
                                    motion_duration_s=max(plan['steps'][i]['points'][-1]['time'] for i in indices),
                                    all_arms_standstill_barrier_after=True,
                                    capture_after=(scope=='extra' or
                                        ((completed | set(ready))==set(order) and
                                         round_index==max(len(chains[rid]) for rid in ready)-1))))
            completed.update(ready)
    serial = sum(s['points'][-1]['time'] for s in plan['steps'])
    parallel = sum(batch['motion_duration_s'] for batch in batches)
    return dict(purpose='parallel_scan_review_only', executable=False, hardware_execution_authorized=False,
                path_points_changed=False, batches=batches, serial_motion_s=serial,
                proposed_motion_s=parallel, motion_time_reduction_percent=100*(1-parallel/serial),
                camera_and_settle_times_included=False,
                prerequisites=['Exact source trajectories, frozen collision geometry and modeled gripper defaults.',
                               'All four initial paths finish before any extra view begins.',
                               'Retain original order for every pair without a separation proof.',
                               'Fresh real states/model review and existing monitored stop handling before hardware use.'])


def analyze(plan, description, defaults, clearance=.02, tracking_error_rad=0.):
    if not np.isfinite(clearance) or clearance <= 0:
        raise ValueError('Clearance must be finite and positive')
    if not np.isfinite(tracking_error_rad) or tracking_error_rad < 0:
        raise ValueError('Tracking corridor must be finite and nonnegative')
    arms = {rid: joint_names(rid) for rid in ROBOT_IDS}
    validated_steps(plan, arms)
    if plan.get('description_sha256') != digest(description):
        raise ValueError('Description differs from checked scan report')
    if plan.get('config_sha256') != digest(plan['design']):
        raise ValueError('Design differs from checked scan report')
    geometry = Geometry(description, arms)
    required = {name for name,joint in geometry.joints.items() if joint.get('type') != 'fixed' and joint.find('mimic') is None}
    if required - (defaults.keys() | plan['start'].keys()):
        raise ValueError('Missing non-arm joint defaults; refusing implicit zero geometry')
    planes = pair_planes(geometry, dict(defaults, **plan['start']))
    result = dict(schema=1, purpose='offline_swept_model_separation', hardware_commands=False,
        hardware_execution_authorized=False, created_at=datetime.now(timezone.utc).isoformat(),
        required_interarm_clearance_m=clearance,
        joint_tracking_corridor_rad=tracking_error_rad,
        analyzed_geometry='all URDF arm collision bodies: exact directional mesh support and analytic primitives',
        interpolation_bound='sum of downstream-link radius bounds times joint interval / 2; original monotone quintics verified',
        joint_defaults=defaults, mesh_sha256=geometry.assets,
        limitations=['Applies to these trajectories and frozen model, not every reachable arm configuration.',
                     'Table/base/mount poses remain provisional; real uncertainty is not bounded by the chosen clearance.',
                     'Gripper joints remain at listed modeled defaults; no real gripper position measured here.',
                     'Cables, people and the visual-only physical tripod are absent.',
                     'Projection overlap means unproven separation, not a detected physical collision.',
                     'Existing self/environment/path checks remain required; no controller or stop policy changed.'], phases={})
    for scope in ('initial', 'extra', 'all'):
        swept = sweep(geometry, plan, planes, scope, defaults, tracking_error_rad)
        pairs = []
        for index, plane in enumerate(planes):
            a, b = plane['a'], plane['b'];A, B = swept[a], swept[b]
            pair = dict(a=a, b=b, wall_normal_world=plane['normal'].tolist(),
                        wall_midpoint_world=plane['midpoint'].tolist(),
                        **separation(A['min'][index], A['max'][index], B['min'][index], B['max'][index], plane['offset'], clearance),
                        a_sampled_intrusion_m=max(0., float(A['sampled_max'][index]-plane['offset'])),
                        b_sampled_intrusion_m=max(0., float(plane['offset']-B['sampled_min'][index])),
                        a_max_sample_witness=A['high_witness'][index],
                        b_min_sample_witness=B['low_witness'][index])
            pair['base_direction_separation_proven'] = pair['phase_independent_separation_proven']
            if not pair['phase_independent_separation_proven']:
                alternative = alternative_separator(A['xyz_hull'], B['xyz_hull'],
                    A['max_total_padding_m'], B['max_total_padding_m'], clearance)
                pair['alternative_separator'] = alternative
                pair['phase_independent_separation_proven'] = alternative['proven']
                if not alternative['proven']:
                    bodywise = bodywise_separator(A['body_hulls'], B['body_hulls'], clearance)
                    pair['bodywise_separation'] = bodywise
                    pair['phase_independent_separation_proven'] = bodywise['proven']
            pairs.append(pair)
        durations = {rid: sum(s['points'][-1]['time'] for s in plan['steps'] if s['arm']==rid and
                     (scope=='all' or (scope=='initial')==(s['purpose']=='common_object_initial_view'))) for rid in arms}
        result['phases'][scope] = dict(pairs=pairs,
            all_four_phase_independent_separation_proven=all(p['phase_independent_separation_proven'] for p in pairs),
            candidate_parallel_groups=groups_from_pairs(arms, pairs),
            duration_per_arm_s=durations, serial_motion_s=sum(durations.values()),
            all_parallel_motion_lower_bound_s=max(durations.values()),
            arms={rid: {key:value for key,value in entry.items() if key not in
                        ('min','max','sampled_min','sampled_max','high_witness','low_witness','xyz_hull','body_hulls')} for rid,entry in swept.items()})
    result['parallel_review'] = parallel_review_schedule(plan, result['phases'], arms)
    return result


def markdown(result):
    lines = ['# Virtuelle Trennebenen der Scanwege', '',
             'Offline-Modellprüfung; keine reale Bewegung oder allgemeine Arbeitsraumfreigabe.', '',
             f"Geforderter Abstand zwischen den Hüllen: {result['required_interarm_clearance_m']*1000:g} mm.", '']
    for name, phase in result['phases'].items():
        lines += [f'## {name}', '', '| Paar | Mittellinien-Überschreitung A/B (obere Schranke) | Nachgewiesener Abstand (untere Schranke) | Methode |',
                  '|---|---:|---:|---|']
        for p in phase['pairs']:
            gap=p['projected_gap_bound_m'];method='Basisrichtung'
            if not p['base_direction_separation_proven']:
                alt=p.get('alternative_separator',{})
                if alt.get('proven'):gap=alt['gap_bound_m'];method='Gedrehte räumliche Ebene'
                elif p.get('bodywise_separation',{}).get('proven'):
                    gap=p['bodywise_separation']['smallest_proven_gap']['gap_bound_m'];method='Einzelkörper-Hüllen'
                else:gap=None;method='NICHT NACHGEWIESEN'
            distance=f'{np.floor(gap*10000)/10:.1f} mm' if gap is not None else 'offen'
            intrusion_a=np.ceil(p['a_wall_intrusion_bound_m']*10000)/10
            intrusion_b=np.ceil(p['b_wall_intrusion_bound_m']*10000)/10
            lines.append(f"| {p['a']} / {p['b']} | {intrusion_a:.1f} / {intrusion_b:.1f} mm | {distance} | {method} |")
        lines += ['', f"Kandidatengruppen: {phase['candidate_parallel_groups']}", '',
                  'Überlappende Projektionen beweisen keine Kollision. Gruppen sind noch keine ausführbare neue Reihenfolge.', '']
    schedule=result['parallel_review']
    lines += ['## Paralleler Prüfablauf', '',
              f"Reine Fahrzeit: {schedule['serial_motion_s']:.1f} → {schedule['proposed_motion_s']:.1f} s.",
              'Foto-/Stillstandszeiten nicht enthalten. Keine Ausführungsfreigabe.', '']
    for index,batch in enumerate(schedule['batches']):
        lines.append(f"- {index+1}. {batch['phase']}: {', '.join(batch['arms'])}; {batch['motion_duration_s']:.1f} s, danach Stillstandsbarriere.")
    lines += ['', '## Grenzen', ''] + ['- ' + value for value in result['limitations']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path, help='Checked object-scan report.json')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--clearance-mm', type=float, default=20.)
    parser.add_argument('--tracking-error-rad', type=float, default=0., help='Bounded deviation from the original joint-space path')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    description = (args.plan.parent / 'cell.urdf').read_text()
    layout = yaml.safe_load((args.plan.parent / 'model/layout.yaml').read_text())
    defaults = {gripper_joint(rid): layout['robots'][rid]['tools']['gripper_initial_position'] for rid in ROBOT_IDS}
    result = analyze(plan, description, defaults, args.clearance_mm/1000, args.tracking_error_rad)
    result.update(source_plan=str(args.plan.resolve()), source_plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                  source_urdf_sha256=hashlib.sha256(description.encode()).hexdigest())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'separation.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    (args.output / 'separation.md').write_text(markdown(result))
    review=dict(result['parallel_review'], source_plan_sha256=result['source_plan_sha256'],
                source_urdf_sha256=result['source_urdf_sha256'],mesh_sha256=result['mesh_sha256'],
                required_interarm_clearance_m=result['required_interarm_clearance_m'])
    (args.output / 'parallel_review.json').write_text(json.dumps(review, indent=2, allow_nan=False)+'\n')
    print(json.dumps({scope:dict(all_four=phase['all_four_phase_independent_separation_proven'],
                                groups=phase['candidate_parallel_groups']) for scope,phase in result['phases'].items()}), flush=True)


if __name__ == '__main__':
    main()

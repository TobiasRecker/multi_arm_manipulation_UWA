"""File-only three-arm Code-as-Policy pilot. No controllers or ROS nodes.

The model starts in a declared in-air fixture. Fixed grasps and a virtual pen
are assumptions; marker traces are visualization, not measured paint/contact.
"""
import hashlib
import itertools
import importlib
import json
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
import time

import numpy as np
from scipy.spatial.transform import Rotation

from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.carton_paths import solve_near
from uwa_cell_motion.smooth_paths import plan_segment, sample_segment
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher, point_box_distance
from .pilot_episode import Episode, digest, write
from .workpiece_paths import SurfaceFrame, SurfacePolyline, point_segment_distance


WORKER = 'left_front'
HOLDERS = ('right_front', 'right_rear')
PEN_LENGTH = .30
PEN_RADIUS = .003
STANDOFF = .06
SURFACES = {'y_max': (1, 1), 'z_min': (2, -1), 'y_min': (1, -1)}
VELOCITY = .1
AWAY_OFFSET = (.07, -.05, .18)
AWAY_ANGLE = 160.
AWAY_YAW = 55.
VARIANTS = ('baseline', 'overlap', 'closer_coordinated', 'away_face')
NOMINAL_ROLL = {'y_max': 0., 'z_min': 80., 'y_min': 180.}


@dataclass(frozen=True)
class Presentation:
    roll_deg: float
    yaw_deg: float = 0.
    offset_m: tuple = (0., 0., 0.)
    translation_leads_turn: bool = False
    origin: str = 'search'


def presentation_candidates(face):
    nominal = NOMINAL_ROLL[face]
    yield Presentation(nominal)
    if face == 'y_min':
        # Seed from the archived three-face trial. Re-solve and check it here.
        yield Presentation(AWAY_ANGLE, AWAY_YAW, AWAY_OFFSET, True, 'away_face_trial')
    for roll_delta, (yaw, offset) in itertools.product(
        (0., -20., 20., -40., 40.),
        ((0., (0., 0., .12)), (25., (-.06, 0., .10)), (-25., (-.06, 0., .10)),
         (55., (.07, -.05, .18)), (-55., (.07, .05, .18))),
    ):
        yield Presentation(nominal + roll_delta, yaw, offset, True)


def policy(variant='baseline'):
    """Readable program, stored with every run; this is its current scope."""
    if variant not in VARIANTS:
        raise ValueError('Unknown drawing policy variant')
    result = dict(schema_version=1, name='hold_box_draw_two_faces_v1', variant=variant,
                holding_arms=list(HOLDERS), working_arm=WORKER,
                surfaces=['y_max', 'z_min'], velocity_rad_s=VELOCITY, circle_radius_m=.025, turn_deg=80.,
                scope='Two named surfaces only; not all sides of the box',
                steps=[dict(id='draw_y_max', operation='draw_face', face='y_max'),
                       dict(id='present_bottom', operation='rotate_held_object', angle_deg=80.),
                       dict(id='draw_z_min', operation='draw_face', face='z_min'),
                       dict(id='park_worker', operation='clear_working_arm'),
                       dict(id='return_box', operation='rotate_held_object', angle_deg=0.)])
    if variant != 'baseline':
        result['name'] = 'hold_box_draw_two_faces_v2'
        result['steps'] = [dict(id='draw_y_max', operation='draw_face', face='y_max'),
                           dict(id='present_bottom', operation='reorient_together', mode='joint' if variant in ('overlap', 'away_face') else 'cartesian'),
                           dict(id='draw_z_min', operation='draw_face', face='z_min'),
                           dict(id='return_box', operation='return_together')]
        if variant=='closer_coordinated':
            result['steps'].insert(0,dict(id='move_closer',operation='shift_box',world_offset_m=[-.08,0,0]))
            result['steps'].append(dict(id='restore_position',operation='shift_box',world_offset_m=[.08,0,0]))
    if variant == 'away_face':
        result.update(name='hold_box_draw_three_faces_v1', surfaces=list(SURFACES),
                      scope='Three named surfaces, with a common reverse path')
        result['steps'][1].update(mode='joint', angle_deg=80., face='z_min')
        result['steps'][3:3] = [
            dict(id='present_away', operation='reorient_together', mode='joint',
                 angle_deg=AWAY_ANGLE, face='y_min', world_yaw_deg=AWAY_YAW,
                 world_offset_m=list(AWAY_OFFSET), translation_leads_turn=True),
            dict(id='draw_y_min', operation='draw_face', face='y_min'),
        ]
    return result


class DrawingModel:
    def __init__(self, directory, source, episode, *, radius_m=.025,
                 presentation_budget=8, max_transfer_s=None, surface_paths=None,
                 replan_return=False):
        self.holding = TwoArmTeacher(directory, source, elevation=.16)
        self.p = self.holding.problem
        self.pose = self.holding.initial.copy()
        self.state = dict(self.holding.start)
        self.names = [j for a in ROBOT_IDS for j in joint_names(a)]
        self.phases = []
        self.diagnostics = []
        self.drawn = []
        self.min_gap = float('inf')
        self.max_tool_error = 0.
        self.max_closure_error = 0.
        self.episode = episode
        self.radius_m = radius_m
        self.surface_paths = surface_paths or {}
        self.replan_return = replan_return
        self.presentation_budget = presentation_budget
        self.max_transfer_s = max_transfer_s
        self.presentations = []
        self.prepared_drawing = None
        self.search_path = Path(directory).parent / 'presentation-search.json'
        self.elapsed = 0.
        self.current_phase = 'initial_fixture'
        self.park_target = self.tip_target(self.pose, 'y_max', 0., standoff=STANDOFF)
        target = self.tool0_target(self.park_target)
        guesses = [np.array([self.state[j] for j in joint_names(WORKER)])]
        guesses += list(np.random.default_rng(17).uniform(-3., 3., (16, 6)))
        for guess in guesses:
            try:
                q = solve_near(self.p, WORKER, self.state, target, guess)
                state = dict(self.state, **dict(zip(joint_names(WORKER), q)))
                self.check(self.pose, state)
                self.state = state
                break
            except ValueError as error:
                self.diagnostics.append(dict(stage='initial_worker_ik', reason=str(error)))
        else:
            raise ValueError('No checked worker fixture; see initial IK')
        self.initial_state = dict(self.state)
        self.presentation_base = self.pose.copy()
        self.worker_park_state = dict(self.state)
        self.coordinated_outbound = []

    def tip_target(self, pose, face, theta, *, standoff=0.):
        if face not in SURFACES:
            raise ValueError(f'Unknown drawing face: {face}')
        axis, sign = SURFACES[face]
        normal = np.eye(3)[axis] * sign
        u = np.array([1., 0., 0.])
        v = np.cross(normal, u)
        centre = normal * self.holding.dimensions[axis] / 2
        local = centre + self.radius_m * (u * np.cos(theta) + v * np.sin(theta)) + normal * standoff
        z = -pose[:3, :3] @ normal
        x = pose[:3, :3] @ u
        tip = np.eye(4)
        tip[:3, :3] = np.column_stack([x, np.cross(z, x), z])
        tip[:3, 3] = pose[:3, :3] @ local + pose[:3, 3]
        return tip

    @staticmethod
    def tool0_target(tip):
        tool = tip.copy()
        tool[:3, 3] -= tool[:3, 2] * PEN_LENGTH
        return tool

    def actual_tip(self, state):
        tip = self.p.chains[WORKER].forward(state)
        tip = tip.copy()
        tip[:3, 3] += tip[:3, 2] * PEN_LENGTH
        return tip

    def surface_frame(self, face):
        axis, sign = SURFACES[face]
        normal = np.eye(3)[axis] * sign
        return SurfaceFrame(normal * self.holding.dimensions[axis]/2, normal, (1., 0., 0.))

    def entry_tip(self, pose, face):
        path = self.surface_paths.get(face)
        if path is None:
            return self.tip_target(pose, face, 0., standoff=STANDOFF)
        return pose @ self.surface_frame(face).tool_pose(path.points_uv_m[0], STANDOFF)

    def worker_ik(self, tip, seed):
        names = joint_names(WORKER)
        q = solve_near(self.p, WORKER, seed, self.tool0_target(tip), np.array([seed[j] for j in names]))
        if np.max(abs(q - [seed[j] for j in names])) > .35:
            raise ValueError('Worker continuation jump')
        return dict(seed, **dict(zip(names, q)))

    def check(self, pose, state, *, closure_errors=None, axial_allowance=None):
        h = self.holding
        if not h.full_check(pose, state):
            raise ValueError('Robot/self/environment/carton FCL collision')
        gap = min(v['clearance_m'] for v in h.distances(pose, state))
        if gap < .02:
            raise ValueError(f'Arm envelope gap {gap:.6f} < .02 m')
        for a in HOLDERS:
            actual = self.p.chains[a].forward(state) @ h.tcp_offsets[a]
            desired = pose @ h.offsets[a]
            error = np.linalg.norm(actual[:3, 3] - desired[:3, 3])
            angle = np.linalg.norm(Rotation.from_matrix(actual[:3, :3] @ desired[:3, :3].T).as_rotvec())
            if closure_errors is not None:
                closure_errors.append(float(error))
            if error > 1e-6 or angle > 1e-5:
                raise ValueError(f'{a}: fixed holder error {error:.3g} m, {angle:.3g} rad')
        # Separate virtual marker geometry. The last 6 mm is a tapered point.
        tool = self.p.chains[WORKER].forward(state)
        lengths = np.linspace(.18, PEN_LENGTH, 61)
        points = tool[:3, 3] + lengths[:, None] * tool[:3, 2]
        radii = PEN_RADIUS * np.minimum(1., (PEN_LENGTH - lengths) / .006)
        local = (points - pose[:3, 3]) @ pose[:3, :3]
        distances, _ = point_box_distance(local, h.dimensions / 2)
        if axial_allowance is None:
            if np.min(distances - radii) < -2e-4:
                raise ValueError('Virtual marker body enters carton envelope')
        else:
            if axial_allowance.get('operation') not in ('axial_feed', 'axial_retract'):
                raise ValueError('Scoped tip penetration allowance is only valid for axial_feed/axial_retract')
            frame = self.surface_frame(axial_allowance['face'])
            normal = np.asarray(frame.outward)
            tangent = np.asarray(frame.u_axis)
            transverse = np.cross(normal, tangent)
            origin = np.asarray(frame.origin_m)
            rel = local[-1] - origin
            lateral = float(np.hypot(rel @ tangent - axial_allowance['uv_m'][0],
                                     rel @ transverse - axial_allowance['uv_m'][1]))
            if lateral > 2.5e-4:
                raise ValueError(f'Axial tip lateral deviation {lateral:.6f} m > .25 mm')
            axis_local = pose[:3, :3].T @ tool[:3, 2]
            axis_error = float(np.arccos(np.clip(axis_local @ (-normal), -1., 1.)))
            if axis_error > 1e-3:
                raise ValueError(f'Axial tool axis deviation {axis_error:.6f} rad > 1 mrad')
            depth_limit = float(axial_allowance['max_depth_m'])
            height = float(rel @ normal)
            if -height > depth_limit + 2e-4:
                raise ValueError(f'Axial tip depth {-height:.6f} m exceeds {depth_limit:.6f} m')
            # Marker shaft above the 6 mm tapered tip keeps the exact unrelaxed carton check.
            shaft = (PEN_LENGTH - lengths) >= .006 - 1e-9
            if np.min(distances[shaft] - radii[shaft]) < -2e-4:
                raise ValueError('Virtual marker shaft enters carton envelope during axial step')
            if np.min(distances[~shaft]) < -(depth_limit + 2e-4):
                raise ValueError('Virtual marker tip exceeds specified axial depth')
        world = self.p.spheres.world(state)
        for a in ROBOT_IDS:
            keep = np.ones(len(world[a]), dtype=bool)
            if a == WORKER:
                keep = np.array([not ('_robotiq_' in link or '_wrist_camera_' in link or
                                    link.endswith(('_wrist_3_link', '_wrist_2_link')))
                                 for link in self.p.spheres.links[a]])
            d = np.linalg.norm(points[:, None] - world[a][None, keep], axis=2)
            if np.min(d - radii[:, None] - self.p.spheres.radii[a][None, keep]) < 0:
                raise ValueError('Virtual marker intersects arm envelope: ' + a)
        for _, box, half in h.environment_boxes:
            d, _ = point_box_distance((points - box[:3, 3]) @ box[:3, :3], half)
            if np.min(d - radii) < 0:
                raise ValueError('Virtual marker intersects environment box')
        return gap

    def phase(self, name, states, poses, *, face=None, draw=False):
        self.current_phase = name
        self.commit_phase(self.prepare_phase(name, states, poses, face=face, draw=draw))

    def prepare_phase(self, name, states, poses, *, face=None, draw=False, max_duration_s=None,
                      preview=None, stroke=None, segment=None):
        # Object motion is reconstructed from the first holder at every sample.
        # Both holders share the same spline and time law.
        if segment is None:
            positions = [[s[j] for j in self.names] for s in states]
            segment = self.timed_joint_path(positions)
        duration = segment['time_law']['duration_s']
        if max_duration_s is not None and duration > max_duration_s:
            raise ValueError(f'Transfer requires {duration:.3f} s; limit is {max_duration_s:.3f} s')
        if preview is not None:
            self.preview_transfer(name, face, segment, states[0], preview)
        count = max(3, int(np.ceil(duration / .02)) + 1)
        times = np.linspace(0, duration, count)
        samples = []
        min_gap = float('inf')
        closure_errors = []
        max_tool_error = 0.
        previous = None
        holder = HOLDERS[0]
        object_from_tool = self.holding.tcp_offsets[holder] @ np.linalg.inv(self.holding.offsets[holder])
        for t, q in zip(times, sample_segment(segment, times)):
            state = dict(states[0], **dict(zip(self.names, q)))
            pose = self.p.chains[holder].forward(state) @ object_from_tool
            try:
                min_gap = min(min_gap, self.check(pose, state, closure_errors=closure_errors))
            except ValueError as error:
                raise ValueError(f'{name} at {t:.3f} s: {error}') from error
            if previous is not None and np.max(abs(q - previous)) > .01:
                raise ValueError('Model sampling step too large')
            previous = q
            tip = self.actual_tip(state)
            if face is not None:
                local = pose[:3, :3].T @ (tip[:3, 3] - pose[:3, 3])
                axis, sign = SURFACES[face]
                expected = sign * self.holding.dimensions[axis] / 2
                if draw:
                    if stroke is None:
                        error = max(abs(local[axis] - expected),
                                    abs(np.linalg.norm(np.delete(local, axis)) - self.radius_m))
                    else:
                        error = point_segment_distance(local, *stroke)
                    max_tool_error = max(max_tool_error, float(error))
                    if error > .00025:
                        raise ValueError('Marker model reference deviation > .25 mm')
            samples.append(dict(local_time_s=float(t), pose=pose.tolist(), q=q.tolist(), tip=tip[:3, 3].tolist(),
                                marker_base=(tip[:3, 3]-.12*tip[:3, 2]).tolist()))
        phase = dict(id=name, face=face, drawing=draw, duration_s=duration, segment=segment, samples=samples)
        if stroke is not None:
            phase['stroke'] = dict(kind='line', start_local_m=stroke[0].tolist(), end_local_m=stroke[1].tolist())
        return phase, states[-1], poses[-1], (min_gap, max(closure_errors), max_tool_error)

    @staticmethod
    def timed_joint_path(positions):
        kind = 'JOINT' if len(positions) == 2 else 'CARTESIAN_LINE'
        segment = dict(kind=kind, knots=np.linspace(0, 1, len(positions)).tolist(),
                       positions=np.asarray(positions).tolist(), check={})
        return plan_segment(segment, velocity=VELOCITY, acceleration=.4, jerk=2.)

    def commit_phase(self, prepared):
        phase, state, pose, (gap, closure_error, tool_error) = prepared
        name, duration = phase['id'], phase['duration_s']
        start = np.array(phase['segment']['positions'][0])
        if np.max(np.abs(start - [self.state[j] for j in self.names])) > 1e-7:
            raise ValueError('Discontinuous phase start')
        self.current_phase = name
        self.episode.append('phase_start', phase=name, source='model', model_time_s=self.elapsed,
                            details=dict(face=phase['face'], drawing=phase['drawing']))
        self.min_gap = min(self.min_gap, gap)
        self.max_closure_error = max(self.max_closure_error, closure_error)
        self.max_tool_error = max(self.max_tool_error, tool_error)
        self.phases.append(phase)
        self.elapsed += duration
        self.episode.append('phase_end', phase=name, source='model', model_time_s=self.elapsed,
                            details=dict(status='MODEL_PHASE_COMPLETE', duration_s=duration))
        self.state = dict(state)
        self.pose = np.array(pose)
        print('PHASE', name, 'samples', len(phase['samples']), 'model seconds', round(duration, 3), flush=True)

    def line(self, name, start_tip, end_tip, *, face=None):
        states = self.line_states(self.state, start_tip, end_tip)
        self.phase(name, states, [self.pose]*len(states), face=face)

    def line_states(self, start, start_tip, end_tip, count=33):
        states = [dict(start)]
        for u in np.linspace(0, 1, count)[1:]:
            tip = start_tip.copy()
            tip[:3, 3] = (1-u)*start_tip[:3, 3] + u*end_tip[:3, 3]
            states.append(self.worker_ik(tip, states[-1]))
        return states

    def draw_face(self, face):
        if self.prepared_drawing is not None:
            prepared_face, phases = self.prepared_drawing
            if prepared_face != face:
                raise ValueError(f'Expected draw_face({prepared_face!r}) after present_surface')
            for phase in phases:
                self.commit_phase(phase)
            self.prepared_drawing = None
            self.drawn.append(face)
            return
        pre = self.tip_target(self.pose, face, 0., standoff=STANDOFF)
        current = self.actual_tip(self.state)
        if np.max(abs(current - pre)) > 1e-6:
            self.current_phase = 'transfer_to_' + face
            # Free transit: choose a checked joint branch, retaining the holders.
            names = joint_names(WORKER)
            start = np.array([self.state[j] for j in names])
            guesses = [start] + list(np.random.default_rng(19).uniform(-3., 3., (20, 6)))
            candidates = []
            for guess in guesses:
                try:
                    q = solve_near(self.p, WORKER, self.state, self.tool0_target(pre), guess)
                    if not any(np.linalg.norm(q-v)<1e-5 for v in candidates):
                        candidates.append(q)
                except ValueError:
                    continue
            for q in sorted(candidates, key=lambda x: np.linalg.norm(x-start)):
                try:
                    for u in np.linspace(0, 1, 121):
                        state = dict(self.state, **dict(zip(names, (1-u)*start+u*q)))
                        self.check(self.pose, state)
                    target = dict(self.state, **dict(zip(names, q)))
                    # A free prepose alone is insufficient. Retain only a branch
                    # whose approach and complete circle also pass model checks.
                    lookahead = dict(target)
                    for gap in np.linspace(STANDOFF, 0., 25):
                        lookahead = self.worker_ik(self.tip_target(self.pose, face, 0., standoff=float(gap)), lookahead)
                        self.check(self.pose, lookahead)
                    for theta in np.linspace(0, 2*np.pi, 65):
                        lookahead = self.worker_ik(self.tip_target(self.pose, face, float(theta)), lookahead)
                        self.check(self.pose, lookahead)
                    self.phase('transfer_to_' + face, [dict(self.state), target], [self.pose, self.pose])
                    break
                except ValueError as error:
                    self.diagnostics.append(dict(stage='worker_joint_transit', face=face, reason=str(error)))
            else:
                raise ValueError('No checked worker transit to ' + face)
        contact = self.tip_target(self.pose, face, 0.)
        self.line('approach_' + face, pre, contact, face=face)
        states = [dict(self.state)]
        for theta in np.linspace(0, 2*np.pi, 129)[1:]:
            states.append(self.worker_ik(self.tip_target(self.pose, face, theta), states[-1]))
        self.phase('draw_' + face, states, [self.pose]*len(states), face=face, draw=True)
        self.line('retract_' + face, contact, pre, face=face)
        self.drawn.append(face)

    def rotate(self, name, angle_deg):
        initial = self.pose.copy()
        target = self.presentation_base.copy()
        target[:3, :3] = self.presentation_base[:3, :3] @ Rotation.from_euler('x', angle_deg, degrees=True).as_matrix()
        rv = Rotation.from_matrix(target[:3, :3] @ initial[:3, :3].T).as_rotvec()
        states, poses = [dict(self.state)], [initial]
        for u in np.linspace(0, 1, 81)[1:]:
            pose = initial.copy()
            pose[:3, :3] = Rotation.from_rotvec(u*rv).as_matrix() @ initial[:3, :3]
            states.append(self.holding.solve(pose, states[-1]))
            poses.append(pose)
        self.phase(name, states, poses)

    def shift_box(self, name, offset):
        """Move holders and free marker together; include relocation in cycle time."""
        offset = np.asarray(offset, dtype=float)
        if offset.shape!=(3,) or not np.isfinite(offset).all() or np.linalg.norm(offset)>.15:
            raise ValueError('Expected a small finite world translation')
        initial = self.pose.copy()
        tip = self.actual_tip(self.state)
        states, poses = [dict(self.state)], [initial]
        for u in np.linspace(0,1,81)[1:]:
            pose = initial.copy();pose[:3,3] += u*offset
            state = self.holding.solve(pose,states[-1])
            target = tip.copy();target[:3,3] += u*offset
            state = self.worker_ik(target,state)
            self.check(pose,state)
            states.append(state);poses.append(pose)
        self.phase(name,states,poses)
        self.presentation_base = self.pose.copy()
        self.worker_park_state = dict(self.state)

    def _check_face_branch(self, pose, state, face):
        if face in self.surface_paths:
            for _, states, _ in self.polyline_phases(pose, state, face, count=17):
                for sample in states:
                    self.check(pose, sample)
            return
        seed = dict(state)
        for gap in np.linspace(STANDOFF,0.,25):
            seed = self.worker_ik(self.tip_target(pose,face,0.,standoff=float(gap)),seed)
            self.check(pose,seed)
        for theta in np.linspace(0,2*np.pi,65):
            seed = self.worker_ik(self.tip_target(pose,face,float(theta)),seed)
            self.check(pose,seed)

    def prepare_drawing(self, pose, start, face):
        if face in self.surface_paths:
            return [self.prepare_phase(name, states, [pose]*len(states), face=face,
                                       draw=stroke is not None, stroke=stroke)
                    for name, states, stroke in self.polyline_phases(pose, start, face)]
        pre = self.tip_target(pose, face, 0., standoff=STANDOFF)
        contact = self.tip_target(pose, face, 0.)
        approach = self.line_states(start, pre, contact)
        circle = [approach[-1]]
        for theta in np.linspace(0, 2*np.pi, 129)[1:]:
            circle.append(self.worker_ik(self.tip_target(pose, face, theta), circle[-1]))
        retract = self.line_states(circle[-1], contact, pre)
        if max(abs(retract[-1][j] - start[j]) for j in self.names) > 1e-7:
            raise ValueError('Drawing changes the IK branch needed for the return path')
        return [
            self.prepare_phase(f'{name}_{face}', states, [pose]*len(states), face=face, draw=name == 'draw')
            for name, states in [('approach', approach), ('draw', circle), ('retract', retract)]
        ]

    def polyline_phases(self, pose, start, face, count=33):
        frame = self.surface_frame(face)
        points = self.surface_paths[face].points_uv_m
        local = [frame.tool_pose(point) for point in points]
        targets = [pose @ point for point in local]
        safe_entry = self.entry_tip(pose, face)
        safe_exit = pose @ frame.tool_pose(points[-1], STANDOFF)
        seed = start
        segments = [(f'approach_{face}', safe_entry, targets[0], None)]
        for index, (a, b) in enumerate(zip(targets, targets[1:]), 1):
            stroke = (local[index - 1][:3, 3], local[index][:3, 3])
            segments.append((f'draw_{face}_edge_{index}', a, b, stroke))
        segments.append((f'retract_{face}', targets[-1], safe_exit, None))
        if points[-1] != points[0]:
            segments.append((f'return_standoff_{face}', safe_exit, safe_entry, None))
        for name, a, b, stroke in segments:
            states = self.line_states(seed, a, b, count)
            yield name, states, stroke
            seed = states[-1]
        if max(abs(seed[joint] - start[joint]) for joint in self.names) > 1e-7:
            raise ValueError('Stroke does not rejoin the checked transfer at standoff')

    def present_surface(self, face):
        """Find and check one pose and route for the next drawing operation."""
        if face not in SURFACES:
            raise ValueError(f'Unknown drawing face: {face}')
        if self.prepared_drawing is not None:
            raise ValueError('Call draw_face before presenting another surface')
        name = f'present_{face}'
        self.current_phase = name
        for candidate in itertools.islice(presentation_candidates(face), self.presentation_budget):
            begun = time.monotonic()
            record = dict(face=face, candidate=asdict(candidate), status='SEARCHING', rejections=[])
            self.presentations.append(record)
            write(self.search_path, self.presentations)
            try:
                transfer, drawing, route = self.try_presentation(face, candidate, record)
            except ValueError as error:
                record.update(status='REJECTED', reason=str(error), wall_s=time.monotonic()-begun)
                write(self.search_path, self.presentations)
                print('REJECTED', name, record['reason'], flush=True)
                continue
            if transfer is not None:
                self.commit_phase(transfer)
                self.coordinated_outbound.append((*route, face))
            self.prepared_drawing = (face, drawing)
            record.update(status='MODEL_CHECKED', wall_s=time.monotonic()-begun,
                          transfer_s=transfer[0]['duration_s'] if transfer is not None else 0.,
                          phase=transfer[0]['id'] if transfer is not None else None,
                          drawing_phase_ids=[phase[0]['id'] for phase in drawing],
                          hold_pose=(route[1][-1] if route is not None else self.pose).tolist())
            write(self.search_path, self.presentations)
            return record
        raise ValueError(f'No checked presentation of {face} within the candidate budget')

    def try_presentation(self, face, candidate, record):
        name = f'present_{face}'
        pose_at = self.presentation_path(candidate.roll_deg, candidate.yaw_deg,
                                         candidate.offset_m, candidate.translation_leads_turn)
        target = pose_at(1.)
        current_tip = self.actual_tip(self.state)
        target_tip = self.entry_tip(target, face)
        if np.allclose(self.pose, target, atol=1e-9, rtol=0) and np.allclose(
            current_tip, target_tip, atol=1e-8, rtol=0
        ):
            return None, self.prepare_drawing(self.pose, self.state, face), None
        worker_names = joint_names(WORKER)
        start = np.array([self.state[j] for j in worker_names])
        try:
            coarse_poses, coarse_states = self.holder_path(pose_at, 81)
        except ValueError as error:
            record['rejections'].append(dict(stage='holder_screen', reason=str(error)))
            raise
        options = self.worker_branches(target_tip, coarse_states[-1], start)
        dense_path = None
        for index, goal in enumerate(options, 1):
            stage = 'worker_screen'
            try:
                self._check_face_branch(target, dict(coarse_states[-1], **dict(zip(worker_names, goal))), face)
                self.worker_route(coarse_poses, coarse_states, start, goal, candidate)
                stage = 'dense_knots'
                if dense_path is None:
                    dense_path = self.holder_path(pose_at, 641 if candidate.yaw_deg else 161)
                poses, holder_states = dense_path
                states = self.worker_route(poses, holder_states, start, goal, candidate)
                stage = 'timed_transfer'
                transfer = self.prepare_phase(name, states, poses, face=face,
                                              max_duration_s=self.max_transfer_s, preview=record)
                stage = 'drawing'
                drawing = self.prepare_drawing(target, states[-1], face)
                return transfer, drawing, (states, poses)
            except ValueError as error:
                record['rejections'].append(dict(stage=stage, worker_branch=index, reason=str(error)))
                if stage == 'dense_knots' and dense_path is None:
                    raise
        if not options:
            record['rejections'].append(dict(stage='worker_ik', reason='No worker branch for the standoff'))
        raise ValueError('No model-checked worker route or drawing for this pose')

    def preview_transfer(self, name, face, segment, start, record):
        duration = segment['time_law']['duration_s']
        times = np.linspace(0., duration, 101)
        holder = HOLDERS[0]
        object_from_tool = self.holding.tcp_offsets[holder] @ np.linalg.inv(self.holding.offsets[holder])
        frames = []
        for t, q in zip(times, sample_segment(segment, times)):
            state = dict(start, **dict(zip(self.names, q)))
            pose = self.p.chains[holder].forward(state) @ object_from_tool
            tip = self.actual_tip(state)
            frames.append(dict(time_s=float(t), phase=name, drawing=False, face=face,
                               pose=pose.tolist(), tip=tip[:3, 3].tolist(),
                               marker_base=(tip[:3, 3] - .12*tip[:3, 2]).tolist(),
                               world=self.viewer_world(state)))
        path = self.search_path.with_name(f'preview-{face}-{len(self.presentations):02d}-{len(record["rejections"])+1:02d}.html')
        summary = dict(status='CANDIDATE PREVIEW', processing_wall_s=0.,
                       phases=[dict(kind='phase_start', phase=name, model_time_s=0.)],
                       detected_events=dict(agent_intervention=None), feedback=[])
        self.write_viewer(path, frames=frames, duration_s=duration, summary=summary,
                          program=dict(surfaces=[face], scope='Candidate transfer. See presentation-search.json for its outcome.'),
                          policy='', candidate_preview=True)
        record.setdefault('previews', []).append(dict(file=path.name, transfer_s=duration))
        record['status'] = 'CHECKING_INTERPOLANT'
        write(self.search_path, self.presentations)
        print('PREVIEW', path, flush=True)

    def viewer_world(self, state):
        return {arm: points.round(5).tolist() for arm, points in self.p.spheres.world(state).items()}

    def write_viewer(self, path, **payload):
        boxes = []
        for _, transform, half in self.holding.environment_boxes:
            corners = np.array(list(itertools.product(*[[-x, x] for x in half])))
            boxes.append((corners @ transform[:3, :3].T + transform[:3, 3]).tolist())
        payload.update(arms=list(ROBOT_IDS), holders=list(HOLDERS), worker=WORKER,
                       radii={arm: values.tolist() for arm, values in self.p.spheres.radii.items()},
                       triangles=(self.holding.triangles-self.holding.dimensions/2).tolist(), boxes=boxes)
        template = Path(__file__).resolve().parents[2] / 'tools/box_drawing_viewer.html'
        html = template.read_text().replace('__DATA__', json.dumps(payload, separators=(',', ':')).replace('</', '<\\/'))
        tmp = path.with_suffix('.html.tmp')
        tmp.write_text(html)
        tmp.replace(path)

    def holder_path(self, pose_at, count):
        poses, states = [pose_at(0.)], [dict(self.state)]
        for progress in np.linspace(0, 1, count)[1:]:
            pose = pose_at(progress)
            try:
                state = self.holding.solve(pose, states[-1])
            except ValueError as error:
                raise ValueError(f'Holder continuation at progress {progress:.3f}: {error}') from error
            poses.append(pose)
            states.append(state)
        return poses, states

    def worker_route(self, poses, holder_states, start, goal, candidate):
        states = []
        worker_names = joint_names(WORKER)
        for progress, pose, state in zip(np.linspace(0, 1, len(poses)), poses, holder_states):
            turn = progress**2 if candidate.translation_leads_turn else progress
            worker = (1-turn)*start + turn*goal
            combined = dict(state, **dict(zip(worker_names, worker)))
            try:
                self.check(pose, combined)
            except ValueError as error:
                raise ValueError(f'Combined route at progress {progress:.3f}: {error}') from error
            states.append(combined)
        return states

    def worker_branches(self, tip, state, start):
        options = []
        tool0 = self.tool0_target(tip)
        for guess in [start, *np.random.default_rng(19).uniform(-3., 3., (20, 6))]:
            try:
                joints = solve_near(self.p, WORKER, state, tool0, guess)
            except ValueError:
                continue
            if not any(np.linalg.norm(joints - old) < 1e-5 for old in options):
                options.append(joints)
        return sorted(options, key=lambda joints: np.linalg.norm(joints - start))

    def presentation_path(self, angle_deg, world_yaw_deg, world_offset_m, translation_leads_turn):
        initial = self.pose.copy()
        local_target = self.presentation_base[:3, :3] @ Rotation.from_euler(
            'x', angle_deg, degrees=True).as_matrix()
        object_turn = Rotation.from_matrix(initial[:3, :3].T @ local_target).as_rotvec()
        offset = np.asarray(world_offset_m)

        def pose_at(progress):
            turn = progress**2 if translation_leads_turn else progress
            yaw = Rotation.from_euler('z', world_yaw_deg * turn, degrees=True).as_matrix()
            roll = Rotation.from_rotvec(turn * object_turn).as_matrix()
            pose = initial.copy()
            pose[:3, :3] = yaw @ initial[:3, :3] @ roll
            pose[:3, 3] += progress * offset
            return pose

        return pose_at

    def reorient_together(self, mode, name='present_bottom', angle_deg=80., face='z_min',
                          world_yaw_deg=0., world_offset_m=(0., 0., 0.),
                          translation_leads_turn=False):
        """Two holders keep one object law; the free worker shares the phase."""
        if mode not in ('joint','cartesian'):
            raise ValueError('Unknown free-worker motion mode')
        initial = self.pose.copy()
        pose_at = self.presentation_path(angle_deg, world_yaw_deg, world_offset_m, translation_leads_turn)
        target = pose_at(1.)
        self.current_phase = name
        worker_names = joint_names(WORKER)
        first_tip = self.actual_tip(self.state)
        last_tip = self.tip_target(target,face,0.,standoff=STANDOFF)
        rv = Rotation.from_matrix(last_tip[:3,:3]@first_tip[:3,:3].T).as_rotvec()
        candidates = [None]
        if mode=='joint':
            _, states = self.holder_path(pose_at, 81)
            q0 = np.array([self.state[j] for j in worker_names])
            candidates = self.worker_branches(last_tip, states[-1], q0)
        knot_count = 641 if world_yaw_deg else 161
        for q in candidates:
            states, poses = [dict(self.state)], [initial]
            try:
                for u in np.linspace(0, 1, knot_count)[1:]:
                    pose = pose_at(u)
                    seed = self.holding.solve(pose,states[-1])
                    if mode == 'joint':
                        turn = u**2 if translation_leads_turn else u
                        seed.update(zip(worker_names, (1-turn)*q0 + turn*q))
                    else:
                        tip = first_tip.copy();tip[:3,:3] = Rotation.from_rotvec(u*rv).as_matrix()@first_tip[:3,:3]
                        tip[:3,3] = (1-u)*first_tip[:3,3]+u*last_tip[:3,3]
                        seed = self.worker_ik(tip,seed)
                    self.check(pose,seed)
                    states.append(seed);poses.append(pose)
                self._check_face_branch(target,states[-1],face)
            except ValueError as error:
                self.diagnostics.append(dict(stage='coordinated_candidate',mode=mode,reason=str(error)))
                continue
            self.phase(name, states, poses)
            self.coordinated_outbound.append((states, poses, None))
            return
        raise ValueError('No checked simultaneous reorientation')

    def return_together(self):
        routes = []
        for index, (states, poses, face) in enumerate(reversed(self.coordinated_outbound)):
            if index == len(self.coordinated_outbound) - 1:
                name = 'return_box'
            else:
                name = f'return_from_{face}' if face is not None else 'return_from_away'
            routes.append((name, list(reversed(states)), list(reversed(poses))))
        planned = self.plan_worker_return(routes) if self.replan_return and routes else None
        if planned is not None:
            for phase in planned:
                self.commit_phase(phase)
        else:
            for name, states, poses in routes:
                self.phase(name, states, poses)
        self.coordinated_outbound.clear()

    def plan_worker_return(self, routes):
        """Try clearing the worker during the first reverse sweep, then park it."""
        paths = [np.array([[state[j] for j in self.names] for state in states])
                 for _, states, _ in routes]
        if np.max(np.abs(paths[0][0] - [self.state[j] for j in self.names])) > 1e-7:
            raise ValueError('Discontinuous return start before replanning')
        worker = [self.names.index(j) for j in joint_names(WORKER)]
        parked = paths[-1][-1, worker]
        end = paths[-1][-1]
        if np.max(np.abs(end - [self.worker_park_state[j] for j in self.names])) > 1e-7:
            raise ValueError('Expected return goal to match the park state')
        original_s = sum(self.timed_joint_path(path)['time_law']['duration_s'] for path in paths)
        progress = np.linspace(0., 1., len(paths[0]))
        for leave_at, park_by in ((.2, .9), (.3, .95), (.4, 1.), (.55, 1.)):
            transition = np.clip((progress - leave_at) / (park_by - leave_at), 0., 1.)
            weight = (transition**3 * (10. - 15.*transition + 6.*transition**2))[:, None]
            candidate = [path.copy() for path in paths]
            candidate[0][:, worker] += weight * (parked - candidate[0][:, worker])
            for path in candidate[1:]:
                path[:, worker] = parked
            record = dict(stage='worker_return', leave_at=leave_at, park_by=park_by, original_s=original_s)
            try:
                prepared = self.check_worker_return(routes, candidate, original_s)
            except ValueError as error:
                self.diagnostics.append(dict(record, status='REJECTED', reason=str(error)))
                continue
            self.diagnostics.append(dict(record, status='MODEL_CHECKED',
                                         duration_s=sum(phase[0]['duration_s'] for phase in prepared)))
            return prepared
        self.diagnostics.append(dict(stage='worker_return', status='REVERSE_FALLBACK', original_s=original_s))
        return None

    def check_worker_return(self, routes, candidate, original_s):
        segments = [self.timed_joint_path(path) for path in candidate]
        if sum(s['time_law']['duration_s'] for s in segments) >= original_s - 1e-6:
            raise ValueError('Candidate does not shorten the model return')
        holder = HOLDERS[0]
        object_from_tool = self.holding.tcp_offsets[holder] @ np.linalg.inv(self.holding.offsets[holder])
        for (name, _, _), segment in zip(routes, segments):
            times = np.linspace(0, segment['time_law']['duration_s'], 151)
            for t, q in zip(times, sample_segment(segment, times)):
                state = dict(self.state, **dict(zip(self.names, q)))
                pose = self.p.chains[holder].forward(state) @ object_from_tool
                try:
                    self.check(pose, state)
                except ValueError as error:
                    raise ValueError(f'{name} screen at {t:.3f} s: {error}') from error
        return [
            self.prepare_phase(name, [dict(self.state, **dict(zip(self.names, q))) for q in path],
                               poses, segment=segment)
            for (name, _, poses), path, segment in zip(routes, candidate, segments)
        ]

    def park_worker(self):
        target = dict(self.state)
        for name in joint_names(WORKER):
            target[name] = self.worker_park_state[name]
        self.phase('park_worker', [dict(self.state), target], [self.pose, self.pose])

def surface_program(faces, radius_m, presentation_budget, max_transfer_s, surface_paths=None,
                    replan_return=False):
    faces = list(faces)
    if not faces or any(face not in SURFACES for face in faces) or len(set(faces)) != len(faces):
        raise ValueError('Choose distinct faces from ' + ', '.join(SURFACES))
    if not isfinite(radius_m) or radius_m <= 0:
        raise ValueError('Circle radius must be finite and positive')
    if type(presentation_budget) is not int or not 1 <= presentation_budget <= 27:
        raise ValueError('Presentation budget must be an integer from 1 to 27')
    if max_transfer_s is not None and (not isfinite(max_transfer_s) or max_transfer_s <= 0):
        raise ValueError('Transfer limit must be finite and positive')
    if surface_paths is not None and set(surface_paths) - set(faces):
        raise ValueError('Specify tool paths only for requested faces')
    steps = []
    code = ['def task(api):']
    for face in faces:
        for operation, prefix in [('present_surface', 'present'), ('draw_face', 'draw')]:
            steps.append(dict(id=f'{prefix}_{face}', operation=operation, face=face))
            code.append(f'    api.{operation}({face!r})')
    steps.append(dict(id='return_box', operation='return_together'))
    code.append('    api.return_together()')
    program = dict(schema_version=1, name='hold_box_draw_requested_surfaces', variant='surface_search',
                   holding_arms=list(HOLDERS), working_arm=WORKER, surfaces=faces,
                   velocity_rad_s=VELOCITY, circle_radius_m=radius_m,
                   presentation_budget=presentation_budget, max_transfer_s=max_transfer_s,
                   scope='Requested box surfaces with searched holding poses and common return path', steps=steps)
    if surface_paths:
        program['surface_paths'] = {face: path.record() for face, path in surface_paths.items()}
    if replan_return:
        program['return_strategy'] = 'replan_worker_with_reverse_fallback'
    return program, '\n'.join(code) + '\n'


def compile_pilot(source, output, *, variant='baseline', feedback_from=None, faces=None,
                  radius_m=None, presentation_budget=None, max_transfer_s=None,
                  tool_paths=None, replan_return=False):
    surface_paths = {}
    if tool_paths is not None:
        spec = json.loads(Path(tool_paths).read_text())
        if not isinstance(spec, dict) or spec.get('schema_version') != 1 or not isinstance(spec.get('surfaces'), dict):
            raise ValueError('Expected a schema_version 1 tool-path file with a surfaces map')
        for face, path in spec['surfaces'].items():
            if (not isinstance(path, dict) or path.get('kind') != 'surface_polyline' or
                    not isinstance(path.get('points_uv_m'), list)):
                raise ValueError(f'{face}: expected a surface_polyline with points_uv_m')
            surface_paths[face] = SurfacePolyline(path['points_uv_m'])
    if faces is not None:
        program, code = surface_program(faces, .025 if radius_m is None else radius_m,
                                        8 if presentation_budget is None else presentation_budget, max_transfer_s,
                                        surface_paths, replan_return)
    else:
        if replan_return or any(value is not None for value in (radius_m, presentation_budget, max_transfer_s, tool_paths)):
            raise ValueError('Search options require a face sequence')
        program = policy(variant)
        code = legacy_code(variant)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    begun = time.monotonic()
    modules = ['uwa_cell_motion.carton_paths', 'uwa_cell_motion.object_transport',
               'uwa_cell_motion.smooth_paths', 'uwa_cell_motion.two_arm_teacher',
               'uwa_cell_motion.geometry', 'uwa_cell_motion.planning', 'uwa_cell_motion.common',
               'uwa_cell_calibration.model', 'uwa_cell_gazebo.charuco_views',
               'uwa_cell_description.configuration', 'uwa_cell_description.scene_assets',
               'uwa_cell_control.parallel_scan']
    repo = Path(__file__).resolve().parents[2]
    files = [Path(__file__), Path(__file__).with_name('pilot_episode.py'),
             Path(__file__).with_name('workpiece_paths.py'),
             repo/'tools/box_drawing_pilot.py', repo/'tools/box_drawing_viewer.html']
    files += [Path(importlib.import_module(name).__file__) for name in modules]
    code_binding = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    write(output / 'program.json', program)
    (output / 'policy.py').write_text(code)
    code_sha = hashlib.sha256(code.encode()).hexdigest()
    feedback_binding = None
    if feedback_from is not None:
        previous = Episode(Path(feedback_from)/'episode')
        feedback = [r for r in previous.records() if r['kind']=='feedback']
        if not feedback:raise ValueError('Feedback source has no user correction')
        feedback_binding = dict(run=str(Path(feedback_from).resolve()),episode_sha256=previous.manifest['sha256'],
                                feedback_sha256=[r['sha256'] for r in feedback])
    episode = Episode.create(output / 'episode', backend='kinematic_model', program_sha256=code_sha,
                             observable_events=('agent_intervention',),
                             metadata=dict(task_scope=program['scope'], source=str(Path(source).resolve()),
                                           feedback_source=feedback_binding, task_spec_sha256=digest(program)))
    try:
        model = DrawingModel(output / 'model', source, episode,
                             radius_m=program['circle_radius_m'],
                             presentation_budget=program.get('presentation_budget', 8),
                             max_transfer_s=program.get('max_transfer_s'),
                             surface_paths=surface_paths, replan_return=replan_return)
        for face in program['surfaces']:
            half = np.delete(model.holding.dimensions, SURFACES[face][0])/2
            if face in surface_paths:
                if np.any(np.abs(surface_paths[face].points_uv_m) >= half):
                    raise ValueError(f'{face}: tool path must fit within the face')
            elif program['circle_radius_m'] >= min(half):
                raise ValueError('Circle radius must fit within each requested face')
        # Execute exactly the saved program against the file-only model API.
        namespace = {}
        exec(compile(code, str(output / 'policy.py'), 'exec'), {'__builtins__': {}}, namespace)
        namespace['task'](model)
        elapsed = 0.
        frames = []
        for phase in model.phases:
            stride = max(1, int(np.floor(len(phase['samples']) / 100)))
            indices = sorted(set(range(0, len(phase['samples']), stride)) | {len(phase['samples'])-1})
            for index in indices:
                s = phase['samples'][index]
                state = dict(model.initial_state, **dict(zip(model.names, s['q'])))
                frames.append(dict(time_s=elapsed+s['local_time_s'], phase=phase['id'],
                                   drawing=phase['drawing'], face=phase['face'],
                                   pose=s['pose'], tip=s['tip'], marker_base=s['marker_base'],
                                   world=model.viewer_world(state)))
            elapsed += phase['duration_s']
        report = dict(schema_version=1, artifact_type='cooperative_box_drawing_model_pilot', executable=False,
                      backend='kinematic_model', status='MODEL_SEQUENCE_COMPLETE', program=program,
                      feedback_source=feedback_binding,
                      policy_sha256=code_sha, program_sha256=digest(program), source_path=str(model.holding.source),
                      source_sha256=model.holding.source_sha256, model_signature=model.p.signature,
                      implementation_sha256=code_binding,
                      model_urdf_sha256=hashlib.sha256((output/'model/carton-moveit/robot.urdf').read_bytes()).hexdigest(),
                      mesh_sha256=model.p.spheres.geometry.assets,
                      dimensions_m=model.holding.dimensions.tolist(),
                      holder_tcp_offsets={a: model.holding.tcp_offsets[a].tolist() for a in HOLDERS},
                      planning_diagnostics=model.diagnostics, presentation_search=model.presentations,
                      initial_state=model.initial_state, grasp_offsets={a: v.tolist() for a, v in model.holding.offsets.items()},
                      validation=dict(samples=sum(len(p['samples']) for p in model.phases), max_dt_s=.02,
                                      min_arm_gap_m=model.min_gap, max_grasp_closure_position_m=model.max_closure_error,
                                      max_marker_reference_error_m=model.max_tool_error),
                      phases=[{k: v for k, v in p.items() if k != 'samples'} for p in model.phases],
                      assumptions=['Hypothetical in-air fixture; no pickup/contact/load validation',
                                   'Open grippers, fixed holder transforms; virtual tool0 +Z 300 mm pen',
                                   'Named drawing surfaces; no force/drop/grasp sensing',
                                   'File-only kinematic execution, sampled geometry; not a physics or hardware run'])
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=sha for p, sha in code_binding.items()):
            raise ValueError('Pilot dependencies changed during compilation; use a new run')
        write(output / 'result.json', report)
        episode.append('run_end', phase='end', source='model', model_time_s=elapsed,
                       details=dict(status=report['status'], processing_wall_s=time.monotonic()-begun))
        summary = episode.summary()
        model.write_viewer(output / 'viewer.html', frames=frames, duration_s=elapsed, summary=summary,
                           report_sha256=digest(report), program=program, policy=code)
        return report
    except BaseException as error:
        if not any(r['kind'] == 'run_end' for r in episode.records()):
            phase = model.current_phase if 'model' in locals() else 'initial_fixture'
            episode.append('run_end', phase=phase, source='model', model_time_s=None,
                           details=dict(status='FAILED', reason=str(error), processing_wall_s=time.monotonic()-begun))
        episode.summary()
        failure = dict(status='FAILED', reason=str(error))
        if 'model' in locals():
            failure.update(phase=model.current_phase, diagnostics=model.diagnostics,
                           presentation_search=model.presentations,
                           last_state=model.state, last_pose=model.pose.tolist())
        write(output / 'failure.json', failure)
        raise


def legacy_code(variant):
    code = 'def task(api):\n    api.draw_face("y_max")\n    api.rotate("present_bottom", 80.0)\n    api.draw_face("z_min")\n    api.park_worker()\n    api.rotate("return_box", 0.0)\n'
    if variant != 'baseline':
        mode = 'joint' if variant in ('overlap', 'away_face') else 'cartesian'
        prefix = '    api.shift_box("move_closer", [-0.08, 0.0, 0.0])\n' if variant == 'closer_coordinated' else ''
        suffix = '    api.shift_box("restore_position", [0.08, 0.0, 0.0])\n' if variant == 'closer_coordinated' else ''
        code = 'def task(api):\n'+prefix+'    api.draw_face("y_max")\n    api.reorient_together("'+mode+'")\n    api.draw_face("z_min")\n    api.return_together()\n'+suffix
    if variant == 'away_face':
        code = code.replace('    api.return_together()',
                            f'    api.reorient_together("joint", "present_away", {AWAY_ANGLE}, "y_min",\n'
                            f'                          {AWAY_YAW}, {AWAY_OFFSET}, translation_leads_turn=True)\n'
                            '    api.draw_face("y_min")\n'
                            '    api.return_together()')
    return code

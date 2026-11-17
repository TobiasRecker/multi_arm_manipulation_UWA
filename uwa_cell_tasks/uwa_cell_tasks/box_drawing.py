"""File-only three-arm Code-as-Policy pilot. No controllers or ROS nodes.

The model starts in a declared in-air fixture. Fixed grasps and a virtual pen
are assumptions; marker traces are visualization, not measured paint/contact.
"""
import hashlib
import itertools
import importlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.spatial.transform import Rotation

from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.carton_paths import solve_near
from uwa_cell_motion.smooth_paths import plan_segment, sample_segment
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher, point_box_distance
from .pilot_episode import Episode, digest, write


WORKER = 'left_front'
HOLDERS = ('right_front', 'right_rear')
PEN_LENGTH = .30
PEN_RADIUS = .003
STANDOFF = .06
SURFACES = ('y_max', 'z_min')
VARIANTS = ('baseline', 'overlap', 'closer_coordinated')


def policy(variant='baseline'):
    """Readable program, stored with every run; this is its current scope."""
    if variant not in VARIANTS:
        raise ValueError('Unknown drawing policy variant')
    result = dict(schema_version=1, name='hold_box_draw_two_faces_v1', variant=variant,
                holding_arms=list(HOLDERS), working_arm=WORKER,
                surfaces=list(SURFACES), circle_radius_m=.025, turn_deg=80.,
                scope='Two named surfaces only; not all sides of the box',
                steps=[dict(id='draw_y_max', operation='draw_face', face='y_max'),
                       dict(id='present_bottom', operation='rotate_held_object', angle_deg=80.),
                       dict(id='draw_z_min', operation='draw_face', face='z_min'),
                       dict(id='park_worker', operation='clear_working_arm'),
                       dict(id='return_box', operation='rotate_held_object', angle_deg=0.)])
    if variant != 'baseline':
        result['name'] = 'hold_box_draw_two_faces_v2'
        result['steps'] = [dict(id='draw_y_max', operation='draw_face', face='y_max'),
                           dict(id='present_bottom', operation='reorient_together', mode='joint' if variant=='overlap' else 'cartesian'),
                           dict(id='draw_z_min', operation='draw_face', face='z_min'),
                           dict(id='return_box', operation='return_together')]
        if variant=='closer_coordinated':
            result['steps'].insert(0,dict(id='move_closer',operation='shift_box',world_offset_m=[-.08,0,0]))
            result['steps'].append(dict(id='restore_position',operation='shift_box',world_offset_m=[.08,0,0]))
    return result


class DrawingModel:
    def __init__(self, directory, source, episode):
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
        self.coordinated_outbound = None

    def tip_target(self, pose, face, theta, *, standoff=0.):
        if face not in SURFACES:
            raise ValueError('This pilot only defines y_max and z_min')
        axis, sign = (1, 1.) if face == 'y_max' else (2, -1.)
        normal = np.eye(3)[axis] * sign
        u = np.array([1., 0., 0.])
        v = np.cross(normal, u)
        centre = normal * self.holding.dimensions[axis] / 2
        local = centre + .025 * (u * np.cos(theta) + v * np.sin(theta)) + normal * standoff
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

    def worker_ik(self, tip, seed):
        names = joint_names(WORKER)
        q = solve_near(self.p, WORKER, seed, self.tool0_target(tip), np.array([seed[j] for j in names]))
        if np.max(abs(q - [seed[j] for j in names])) > .35:
            raise ValueError('Worker continuation jump')
        return dict(seed, **dict(zip(names, q)))

    def check(self, pose, state):
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
            self.max_closure_error = max(self.max_closure_error, float(error))
            if error > 1e-6 or angle > 1e-5:
                raise ValueError('Fixed holder transforms not satisfied')
        # Separate virtual marker geometry. The last 6 mm is a tapered point.
        tool = self.p.chains[WORKER].forward(state)
        lengths = np.linspace(.18, PEN_LENGTH, 61)
        points = tool[:3, 3] + lengths[:, None] * tool[:3, 2]
        radii = PEN_RADIUS * np.minimum(1., (PEN_LENGTH - lengths) / .006)
        local = (points - pose[:3, 3]) @ pose[:3, :3]
        distances, _ = point_box_distance(local, h.dimensions / 2)
        if np.min(distances - radii) < -2e-4:
            raise ValueError('Virtual marker body enters carton envelope')
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
        self.episode.append('phase_start', phase=name, source='model', model_time_s=self.elapsed,
                            details=dict(face=face, drawing=draw))
        positions = np.array([[s[j] for j in self.names] for s in states])
        if np.max(np.abs(positions[0] - [self.state[j] for j in self.names])) > 1e-7:
            raise ValueError('Discontinuous phase start')
        # Object motion is reconstructed from the first holder at every sample.
        # Both holders share the same spline and time law.
        kind = 'JOINT' if len(positions) == 2 else 'CARTESIAN_LINE'
        segment = dict(kind=kind, knots=np.linspace(0, 1, len(positions)).tolist(),
                       positions=positions.tolist(), check={})
        segment = plan_segment(segment, velocity=.35, acceleration=.4, jerk=2.)
        duration = segment['time_law']['duration_s']
        count = max(3, int(np.ceil(duration / .02)) + 1)
        samples = []
        previous = None
        for t in np.linspace(0, duration, count):
            q = sample_segment(segment, float(t))
            state = dict(self.state, **dict(zip(self.names, q)))
            a = HOLDERS[0]
            pose = self.p.chains[a].forward(state) @ self.holding.tcp_offsets[a] @ np.linalg.inv(self.holding.offsets[a])
            self.min_gap = min(self.min_gap, self.check(pose, state))
            if previous is not None and np.max(abs(q - previous)) > .01:
                raise ValueError('Model sampling step too large')
            previous = q
            tip = self.actual_tip(state)
            if face is not None:
                local = pose[:3, :3].T @ (tip[:3, 3] - pose[:3, 3])
                axis = 1 if face == 'y_max' else 2
                expected = (1 if face == 'y_max' else -1) * self.holding.dimensions[axis] / 2
                if draw:
                    plane_error = abs(local[axis] - expected)
                    circle_error = abs(np.linalg.norm(np.delete(local, axis)) - .025)
                    self.max_tool_error = max(self.max_tool_error, float(max(plane_error, circle_error)))
                    if max(plane_error, circle_error) > .00025:
                        raise ValueError('Marker model reference deviation > .25 mm')
            samples.append(dict(local_time_s=float(t), pose=pose.tolist(), q=q.tolist(), tip=tip[:3, 3].tolist(),
                                marker_base=(tip[:3, 3]-.12*tip[:3, 2]).tolist()))
        self.phases.append(dict(id=name, face=face, drawing=draw, duration_s=duration,
                                segment=segment, samples=samples))
        self.elapsed += duration
        self.episode.append('phase_end', phase=name, source='model', model_time_s=self.elapsed,
                            details=dict(status='MODEL_PHASE_COMPLETE', duration_s=duration))
        self.state = dict(states[-1])
        self.pose = np.array(poses[-1])
        print('PHASE', name, 'samples', count, 'model seconds', round(duration, 3), flush=True)

    def line(self, name, start_tip, end_tip, *, face=None):
        states = [dict(self.state)]
        for u in np.linspace(0, 1, 33)[1:]:
            tip = start_tip.copy()
            tip[:3, 3] = (1-u)*start_tip[:3, 3] + u*end_tip[:3, 3]
            states.append(self.worker_ik(tip, states[-1]))
        self.phase(name, states, [self.pose]*len(states), face=face)

    def draw_face(self, face):
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
        seed = dict(state)
        for gap in np.linspace(STANDOFF,0.,25):
            seed = self.worker_ik(self.tip_target(pose,face,0.,standoff=float(gap)),seed)
            self.check(pose,seed)
        for theta in np.linspace(0,2*np.pi,65):
            seed = self.worker_ik(self.tip_target(pose,face,float(theta)),seed)
            self.check(pose,seed)

    def reorient_together(self, mode):
        """Two holders keep one object law; the free worker shares the phase."""
        if mode not in ('joint','cartesian'):
            raise ValueError('Unknown free-worker motion mode')
        initial = self.pose.copy()
        target = self.presentation_base.copy()
        target[:3,:3] = target[:3,:3]@Rotation.from_euler('x',80.,degrees=True).as_matrix()
        worker_names = joint_names(WORKER)
        first_tip = self.actual_tip(self.state)
        last_tip = self.tip_target(target,'z_min',0.,standoff=STANDOFF)
        rv = Rotation.from_matrix(last_tip[:3,:3]@first_tip[:3,:3].T).as_rotvec()
        candidates = [None]
        if mode=='joint':
            seed = dict(self.state)
            for u in np.linspace(0,1,81)[1:]:
                pose = initial.copy();pose[:3,:3] = initial[:3,:3]@Rotation.from_euler('x',80.*u,degrees=True).as_matrix()
                seed = self.holding.solve(pose,seed)
            q0 = np.array([self.state[j] for j in worker_names])
            candidates = []
            for guess in [q0]+list(np.random.default_rng(19).uniform(-3.,3.,(20,6))):
                try:
                    q = solve_near(self.p,WORKER,seed,self.tool0_target(last_tip),guess)
                    if not any(np.linalg.norm(q-v)<1e-5 for v in candidates):candidates.append(q)
                except ValueError:continue
            candidates.sort(key=lambda q:np.linalg.norm(q-q0))
        for q in candidates:
            states, poses = [dict(self.state)], [initial]
            try:
                for u in np.linspace(0,1,161)[1:]:
                    pose = initial.copy();pose[:3,:3] = initial[:3,:3]@Rotation.from_euler('x',80.*u,degrees=True).as_matrix()
                    seed = self.holding.solve(pose,states[-1])
                    if mode=='joint':seed.update(zip(worker_names,(1-u)*q0+u*q))
                    else:
                        tip = first_tip.copy();tip[:3,:3] = Rotation.from_rotvec(u*rv).as_matrix()@first_tip[:3,:3]
                        tip[:3,3] = (1-u)*first_tip[:3,3]+u*last_tip[:3,3]
                        seed = self.worker_ik(tip,seed)
                    self.check(pose,seed)
                    states.append(seed);poses.append(pose)
                self._check_face_branch(target,states[-1],'z_min')
            except ValueError as error:
                self.diagnostics.append(dict(stage='coordinated_candidate',mode=mode,reason=str(error)))
                continue
            self.phase('present_bottom',states,poses)
            self.coordinated_outbound = (states,poses)
            return
        raise ValueError('No checked simultaneous reorientation')

    def return_together(self):
        if self.coordinated_outbound is None:
            raise ValueError('No checked outbound motion to reverse')
        states, poses = self.coordinated_outbound
        self.phase('return_box',list(reversed(states)),list(reversed(poses)))

    def park_worker(self):
        target = dict(self.state)
        for name in joint_names(WORKER):
            target[name] = self.worker_park_state[name]
        self.phase('park_worker', [dict(self.state), target], [self.pose, self.pose])

def compile_pilot(source, output, *, variant='baseline', feedback_from=None):
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
             repo/'tools/box_drawing_pilot.py', repo/'tools/box_drawing_viewer.html']
    files += [Path(importlib.import_module(name).__file__) for name in modules]
    code_binding = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    program = policy(variant)
    write(output / 'program.json', program)
    code = 'def task(api):\n    api.draw_face("y_max")\n    api.rotate("present_bottom", 80.0)\n    api.draw_face("z_min")\n    api.park_worker()\n    api.rotate("return_box", 0.0)\n'
    if variant!='baseline':
        mode = 'joint' if variant=='overlap' else 'cartesian'
        prefix = '    api.shift_box("move_closer", [-0.08, 0.0, 0.0])\n' if variant=='closer_coordinated' else ''
        suffix = '    api.shift_box("restore_position", [0.08, 0.0, 0.0])\n' if variant=='closer_coordinated' else ''
        code = 'def task(api):\n'+prefix+'    api.draw_face("y_max")\n    api.reorient_together("'+mode+'")\n    api.draw_face("z_min")\n    api.return_together()\n'+suffix
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
                                           feedback_source=feedback_binding))
    try:
        model = DrawingModel(output / 'model', source, episode)
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
                                   world={a: v.round(5).tolist() for a, v in model.p.spheres.world(state).items()}))
            elapsed += phase['duration_s']
        report = dict(schema_version=1, artifact_type='cooperative_box_drawing_model_pilot', executable=False,
                      backend='kinematic_model', status='MODEL_SEQUENCE_COMPLETE', program=program,
                      feedback_source=feedback_binding,
                      policy_sha256=code_sha, source_path=str(model.holding.source),
                      source_sha256=model.holding.source_sha256, model_signature=model.p.signature,
                      implementation_sha256=code_binding,
                      model_urdf_sha256=hashlib.sha256((output/'model/carton-moveit/robot.urdf').read_bytes()).hexdigest(),
                      mesh_sha256=model.p.spheres.geometry.assets,
                      dimensions_m=model.holding.dimensions.tolist(),
                      holder_tcp_offsets={a: model.holding.tcp_offsets[a].tolist() for a in HOLDERS},
                      planning_diagnostics=model.diagnostics,
                      initial_state=model.initial_state, grasp_offsets={a: v.tolist() for a, v in model.holding.offsets.items()},
                      validation=dict(samples=sum(len(p['samples']) for p in model.phases), max_dt_s=.02,
                                      min_arm_gap_m=model.min_gap, max_grasp_closure_position_m=model.max_closure_error,
                                      max_marker_reference_error_m=model.max_tool_error),
                      phases=[{k: v for k, v in p.items() if k != 'samples'} for p in model.phases],
                      assumptions=['Hypothetical in-air fixture; no pickup/contact/load validation',
                                   'Open grippers, fixed holder transforms; virtual tool0 +Z 300 mm pen',
                                   'Two explicit surfaces, not every side; no force/drop/grasp sensing',
                                   'File-only kinematic execution, sampled geometry; not a physics or hardware run'])
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=sha for p, sha in code_binding.items()):
            raise ValueError('Pilot dependencies changed during compilation; use a new run')
        write(output / 'result.json', report)
        episode.append('run_end', phase='end', source='model', model_time_s=elapsed,
                       details=dict(status=report['status'], processing_wall_s=time.monotonic()-begun))
        summary = episode.summary()
        boxes = []
        for _, T, half in model.holding.environment_boxes:
            corners = np.array(list(itertools.product(*[[-x, x] for x in half])))
            boxes.append((corners @ T[:3, :3].T + T[:3, 3]).tolist())
        payload = dict(frames=frames, arms=list(ROBOT_IDS), holders=list(HOLDERS), worker=WORKER,
                       radii={a: v.tolist() for a, v in model.p.spheres.radii.items()},
                       triangles=(model.holding.triangles-model.holding.dimensions/2).tolist(),
                       boxes=boxes, duration_s=elapsed, summary=summary, report_sha256=digest(report),
                       program=program, policy=code)
        template = Path(__file__).resolve().parents[2] / 'tools/box_drawing_viewer.html'
        html = template.read_text().replace('__DATA__', json.dumps(payload, separators=(',', ':')).replace('</', '<\\/'))
        (output / 'viewer.html').write_text(html)
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
                           last_state=model.state, last_pose=model.pose.tolist())
        write(output / 'failure.json', failure)
        raise

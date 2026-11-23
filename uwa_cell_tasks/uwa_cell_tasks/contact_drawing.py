"""Retarget an offline drawing reference to a verified Gazebo contact group."""
from itertools import combinations
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.interpolate import BPoly, PPoly
from scipy.spatial.transform import Rotation

from uwa_cell_description.configuration import joint_names
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import ROBOT_IDS
from uwa_cell_motion.object_transport import ObjectTransport
from uwa_cell_motion.smooth_paths import curve, plan_segment, sample_segment
from .box_drawing import DrawingModel, PEN_LENGTH, SURFACES, WORKER
from .core import ARMS, verify, write_json
from .planning import support_exemptions
from .scene import apply_object
from .workpiece_paths import point_segment_distance


def controller_spline(rows, knots, limits, phase_id):
    """Joint limits and timing of the actual shared-controller interpolant."""
    law = plan_segment(dict(kind='CARTESIAN_LINE' if len(rows)>2 else 'JOINT',
        knots=knots.tolist(),positions=rows,check={}),
        velocity=limits[0],acceleration=limits[1],jerk=limits[2])
    duration = law['time_law']['duration_s']
    # Keep the previous 4 mrad maximum travel between controller
    # points, so speeding up preserves the spatial sweep resolution.
    point_period = min(.04, .004 / law['smooth_bounds']['velocity_rad_s'])
    times = np.linspace(0,duration,max(3,int(np.ceil(duration/point_period))+1))
    values = np.stack([sample_segment(law,times,k) for k in (0,1,2)], axis=1)
    # The controller uses exactly these quintics. Check its coefficients
    # conservatively in Bernstein form and sample its realized geometry.
    spline = BPoly.from_derivatives(times, values)
    controller_scale = 1.
    for k, limit in enumerate(limits,1):
        poly = PPoly.from_bernstein_basis(spline.derivative(k))
        widths = np.diff(times)
        power = np.arange(len(poly.c)-1,-1,-1)
        scaled = poly.c * widths[None,:,None]**power[:,None,None]
        unit = PPoly(scaled,np.arange(len(times),dtype=float))
        peak = np.max(abs(BPoly.from_power_basis(unit).c))
        if k == 3 and peak > limit:
            quadratic, linear, constant = scaled
            vertex = np.divide(-linear,2*quadratic,
                               out=np.zeros_like(linear),where=quadratic!=0)
            vertex = np.clip(vertex,0.,1.)
            peak = np.max(np.abs([constant, quadratic+linear+constant,
                (quadratic*vertex+linear)*vertex+constant]))
        controller_scale = max(controller_scale, (peak/limit)**(1/k))
    # Correct only the controller polynomial's measured excess, using
    # one time factor for all 18 axes. No lower velocity cap is used.
    if controller_scale > 1.:
        if controller_scale > 1.01:
            raise ValueError(f'{phase_id}: controller interpolation cannot preserve reviewed timing')
        times *= controller_scale
        duration *= controller_scale
        values[:,1] /= controller_scale
        values[:,2] /= controller_scale**2
        spline = BPoly.from_derivatives(times, values)
    return times, values, spline, controller_scale


class ContactDrawing:
    def __init__(self, path):
        recipe = verify(json.loads(Path(path).read_text()))
        self.reference = recipe['drawing']
        self.connectors = recipe['connectors']
        self.branch = self.reference['initial_state']
        self.trajectories = []
        self.validate_phases()

    def validate_phases(self):
        phases = self.reference['phases']
        if not phases:
            raise ValueError('At least one workpiece operation is required')
        for phase in phases:
            process = phase.get('operation')
            if phase.get('drawing') or process:
                if phase.get('face') not in SURFACES:
                    raise ValueError('Unknown tool face')
            if process:
                if process not in ('axial_approach','axial_feed','axial_retract'):
                    raise ValueError(f'Unexpected virtual-tool operation {process}')
                axial = phase['axial']
                uv = np.asarray(axial['uv_m'], dtype=float)
                if uv.shape != (2,) or not np.isfinite(uv).all():
                    raise ValueError('Invalid axial site')
                if not 0. < float(axial['reference_depth_m']) <= .003:
                    raise ValueError('Virtual axial depth must be at most 3 mm')
                if not .003 <= float(axial['clearance_m']) <= .06:
                    raise ValueError('Virtual axial approach outside checked range')

    def compile(self, problem, group, start, observed_asset, output, *, check_cancel=None):
        """Bind both holders to fresh offsets, keep the reviewed worker path."""
        dims = np.asarray(self.reference['dimensions_m'])
        center = np.eye(4)
        center[:3, 3] = dims / 2
        center_to_asset = np.linalg.inv(center)
        previous = np.linalg.inv(self.reference['grasp_offsets'][ARMS[0]])
        new_offsets = {arm: center_to_asset @ offset for arm,offset in group.offsets.items()}
        reference_state = dict(self.branch)
        problem.chains.update({arm: Chain(problem.base_description,'world',arm+'_tool0')
                               for arm in ROBOT_IDS if arm not in problem.chains})
        solver = ObjectTransport.__new__(ObjectTransport)
        solver.problem, solver.collision = problem, problem.collision
        solver.arms, solver.offsets = ARMS, new_offsets
        solver.tcp_offsets = {arm: np.eye(4) for arm in ARMS}

        def collision(pose, state):
            apply_object(problem.collision, problem.scene_record, pose @ center_to_asset, touching=True)
            support_exemptions(problem, pose @ center_to_asset)
            if not problem.collision.check(state)[0]:
                problem.collision.check(state, contacts=True)
                return False
            return True

        def distances(_, state):
            world = problem.spheres.world(state)
            return [problem.spheres.nearest(world,a,b) for a,b in combinations(ROBOT_IDS,2)]

        env = []
        frames = problem.spheres.geometry.fk.frames(start)
        for body in problem.spheres.environment:
            lo, hi = body.visual_vertices.min(axis=0), body.visual_vertices.max(axis=0)
            transform = (frames[body.link] @ body.fixed).copy()
            transform[:3,3] += transform[:3,:3] @ ((lo+hi)/2)
            env.append((body.link, transform, (hi-lo)/2))
        checker = DrawingModel.__new__(DrawingModel)
        checker.p = problem
        checker.holding = SimpleNamespace(dimensions=dims, offsets=new_offsets,
            tcp_offsets=solver.tcp_offsets, environment_boxes=env, full_check=collision, distances=distances)
        chain = problem.chains[ARMS[0]]
        names = [j for arm in (*ARMS, WORKER) for j in joint_names(arm)]
        worker = joint_names(WORKER)
        origin = observed_asset @ center
        first = self.connectors[0]
        ref_origin = chain.forward(dict(reference_state,**dict(zip(
            first['joint_names'], first['segment']['positions'][0])))) @ previous
        correction = Rotation.from_matrix(origin[:3,:3] @ ref_origin[:3,:3].T).as_rotvec()
        shift = origin[:3,3] - ref_origin[:3,3]
        if np.linalg.norm(shift)>.01 or np.linalg.norm(correction)>.04:
            raise ValueError('Fresh grasp starts outside the reviewed pickup corridor')
        park = np.array([start[j] for j in worker])
        cfg = problem.scene_record['cfg']
        limits = (cfg['joint_velocity_rad_s'], cfg['joint_acceleration_rad_s2'], cfg['joint_jerk_rad_s3'])
        spec = None
        if cfg.get('seek_contact'):
            from .seek_contact import SeekContact, ProbePath
            spec = SeekContact.from_record(cfg['seek_contact'])
            checker.probe_tool = spec.tool
        phases = self.connectors[:2] + ([] if spec else self.reference['phases']) + self.connectors[2:]
        state = dict(start)
        inv = np.linalg.inv(new_offsets[ARMS[0]])
        for phase in phases:
            if check_cancel is not None:
                check_cancel()
            phase_id = phase['id']
            print('Retarget drawing phase',phase_id,flush=True)
            ref_names = phase.get('joint_names', self.reference['names'])
            path = curve(phase['segment'])
            knots = np.linspace(0.,1.,len(phase['segment']['positions']))
            rows = []
            for u, values in zip(knots,path(knots)):
                ref = dict(reference_state,**dict(zip(ref_names, values)))
                pose = chain.forward(ref) @ previous
                if phase_id in ('lift','set_down'):
                    fraction = 1-u if phase_id=='lift' else u
                    pose[:3,:3] = Rotation.from_rotvec(fraction*correction).as_matrix() @ pose[:3,:3]
                    pose[:3,3] += fraction*shift
                    ref.update(zip(worker,park))
                elif phase_id == 'worker_to_drawing_start':
                    target = np.array([self.branch[j] for j in worker])
                    ref.update(zip(worker,(1-u)*park+u*target))
                elif phase_id == 'reverse_worker_to_drawing_start':
                    target = np.array([self.branch[j] for j in worker])
                    ref.update(zip(worker,(1-u)*target+u*park))
                seeded = dict(state)
                for arm in ARMS:
                    seeded.update({j:ref[j] for j in joint_names(arm)})
                updated = solver.solve(pose,seeded)
                if max(abs(updated[j]-state[j]) for j in names if j not in worker)>.5:
                    raise ValueError(f'{phase_id}: live holder branch is discontinuous')
                updated.update({j:ref[j] for j in worker})
                if not rows and max(abs(updated[j]-state[j]) for j in names)>1e-7:
                    raise ValueError(f'{phase_id}: pose does not join previous phase')
                state = updated
                rows.append([state[j] for j in names])
            duration_ref = phase['duration_s']
            times, values, spline, controller_scale = controller_spline(rows, knots, limits, phase_id)
            duration = float(times[-1])
            checks = np.linspace(0,duration,2*len(times)-1)
            error = 0.
            operation = phase.get('operation')
            face = phase.get('face')
            axial = phase.get('axial', {})
            stroke = phase.get('stroke')
            endpoints_local = ([np.asarray(stroke[key],dtype=float) for key in
                               ('start_local_m','end_local_m')] if stroke else None)
            allowance = None
            if operation in ('axial_feed','axial_retract'):
                allowance = dict(operation=operation,face=face,uv_m=axial['uv_m'],
                                 max_depth_m=axial['reference_depth_m'])
            if operation:
                frame = checker.surface_frame(face)
                normal = np.asarray(frame.outward)
                tangent = np.asarray(frame.u_axis)
                transverse = np.cross(normal,tangent)
                heights = []
            for index,q in enumerate(spline(checks)):
                if check_cancel is not None and index % 64 == 0:
                    check_cancel()
                checked = dict(start,**dict(zip(names,q)))
                pose = chain.forward(checked) @ inv
                try:
                    checker.check(pose,checked,axial_allowance=allowance)
                except ValueError as error:
                    write_json(Path(output)/'drawing-rejection.json', dict(
                        phase=phase_id, sample=index, time_s=float(checks[index]), reason=str(error),
                        state=checked, pose=pose.tolist()))
                    raise ValueError(f'{phase_id}, sample {index}: {error}') from error
                if phase.get('drawing') or operation:
                    tool = problem.chains[WORKER].forward(checked)
                    tip = tool[:3,3]+PEN_LENGTH*tool[:3,2]
                    local = pose[:3,:3].T@(tip-pose[:3,3])
                    if operation:
                        rel = local - frame.origin_m
                        lateral = np.linalg.norm(np.array([rel @ tangent,rel @ transverse])-axial['uv_m'])
                        height = float(rel @ normal)
                        lo = -axial['reference_depth_m'] if allowance else 0.
                        axis_error = np.arccos(np.clip((pose[:3,:3].T @ tool[:3,2]) @ (-normal), -1., 1.))
                        if height < lo-.0002 or height > axial['clearance_m']+.00025 or axis_error > .001:
                            raise ValueError(f'{phase_id}: virtual tip leaves the defined axial corridor')
                        heights.append(height)
                        error = max(error,float(lateral))
                    elif endpoints_local is not None:
                        error = max(error,point_segment_distance(local,*endpoints_local))
                    else:
                        axis,sign = SURFACES[face]
                        radius = phase.get('circle_radius_m',.025)
                        error = max(error,abs(local[axis]-sign*dims[axis]/2),
                                    abs(np.linalg.norm(np.delete(local,axis))-radius))
                    if error>.00025:
                        raise ValueError(f'{phase_id}: marker deviation exceeds 0.25 mm')
                if phase_id=='lift' and index==len(checks)-1:
                    self.lifted = pose @ center_to_asset
            if operation:
                depth = axial['reference_depth_m']
                clearance = axial['clearance_m']
                endpoints = {'axial_approach':(clearance,0.), 'axial_feed':(0.,-depth),
                             'axial_retract':(-depth,clearance)}[operation]
                if max(abs(heights[0]-endpoints[0]),abs(heights[-1]-endpoints[1]))>.00025:
                    raise ValueError(f'{phase_id}: axial endpoints differ from reference')
            commands = [dict(time=float(t),positions=q.tolist(),velocities=v.tolist(),accelerations=a.tolist())
                        for t,(q,v,a) in zip(times,values)]
            motion = dict(phase=phase_id,joint_names=names,points=commands,duration_s=duration,
                          checked_samples=len(checks),marker_error_m=error,reference_duration_s=duration_ref,
                          controller_time_factor=controller_scale)
            self.trajectories.append(motion)
            write_json(Path(output)/'drawing-trajectories'/f'{phase_id}.json',motion)
            if spec and phase_id == 'worker_to_drawing_start':
                self.probe = ProbePath(spec, checker, names, inv, state, limits)
                for step in self.probe.compile():
                    self.trajectories.append(step)
                    write_json(Path(output)/'drawing-trajectories'/f"{step['phase']}.json", step)

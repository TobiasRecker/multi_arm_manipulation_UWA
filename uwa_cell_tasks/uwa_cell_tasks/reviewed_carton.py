"""Compile the exact controller trajectories for reviewed, unloaded carton moves."""

import hashlib
from importlib.metadata import version
from importlib.util import find_spec
import itertools
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

import numpy as np

from uwa_cell_motion.common import SPEED_TOLERANCE, joint_names, joint_velocity_limits
from uwa_cell_motion.stopping_reserve import body_budgets


START_TOLERANCE = .0005
TRACKING_TOLERANCE = .001
ARMS = ('right_front', 'right_rear')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def speed_envelope(problem, arms, speed, tcp_speed):
    from uwa_cell_motion.motion_envelope import MotionEnvelope
    if not (0 < speed <= .3 and 0 < tcp_speed <= .25):
        raise ValueError('Requested speed outside the pilot limits')
    if any(speed > min(joint_velocity_limits(problem.cfg,arm).min(),
                       problem.cfg.get('command_velocity_limit_rad_s',problem.cfg['velocity_limit_rad_s']))+1e-12
           for arm in arms):
        raise ValueError('Requested joint speed exceeds the bound of the selected hardware profile')
    frames = {arm: [
        dict(frame=arm+'_tool0', offset_m=[0., 0., 0.]),
        dict(frame=arm+'_robotiq_85_base_link', offset_m=[0., 0., .145]),
    ] for arm in arms}
    return MotionEnvelope(problem.original_description, frames, speed, tcp_speed)


def preview_model(problem, directory):
    root = ET.fromstring(problem.original_description)
    for link in root.findall('link'):
        for visual in list(link.findall('visual')):
            mesh = visual.find('geometry/mesh')
            if mesh is not None and '/charuco/' in mesh.get('filename', ''):
                link.remove(visual)
    for mesh in root.findall('.//mesh'):
        uri = mesh.get('filename', '')
        if not uri.startswith('file://'):
            continue
        path = unquote(urlparse(uri).path)
        if '/share/' in path:
            mesh.set('filename', 'package://'+path.rsplit('/share/', 1)[1])
    path = Path(directory)/'preview.urdf'
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
    return path


def retime(trajectory, arm, envelope):
    scale = 1.
    for _ in range(8):
        points = [dict(time=round(p['time']*scale*1e9)/1e9, positions=p['positions'],
                       velocities=(np.asarray(p['velocities'])/scale).tolist(),
                       accelerations=(np.asarray(p['accelerations'])/scale**2).tolist())
                  for p in trajectory['points']]
        # Evaluate the actual integer-nanosecond controller knots. Rounding
        # or a changed subdivision of the TCP bound may require another pass.
        factor = envelope.time_scale(arm, points)
        if not np.isfinite(factor) or factor < 1:
            raise ValueError('Invalid speed scaling for '+arm)
        if factor<=1+1e-10:
            return dict(joint_names=joint_names(arm), duration_s=points[-1]['time'],
                        points=points, waypoints=trajectory['waypoints'])
        scale *= factor
    raise ValueError('Unable to represent the bounded trajectory at controller time resolution')


def concatenate(parts):
    first = parts[0]
    points = list(first['points'])
    waypoints = list(first['waypoints'])
    for part in parts[1:]:
        if any(not np.allclose(points[-1][key],part['points'][0][key],atol=1e-10,rtol=0)
               for key in ('positions','velocities','accelerations')):
            raise ValueError('Carton trajectory junction mismatch')
        offset = points[-1]['time']
        origin_ns=round(offset*1e9)
        points.extend(dict(p, time=(origin_ns+round(p['time']*1e9))/1e9) for p in part['points'][1:])
        waypoints.extend(part['waypoints'][1:])
    return dict(joint_names=first['joint_names'], duration_s=points[-1]['time'],
                points=points, waypoints=waypoints)


def bernstein_controls(points):
    """Control hulls enclose every interpolated quintic, including overshoot."""
    q, v, a = (np.array([p[key] for p in points], float)
               for key in ('positions', 'velocities', 'accelerations'))
    t = np.array([p['time'] for p in points])
    h = np.diff(t)[:, None]
    if len(q) < 2 or q.shape[1:] != (6,) or v.shape != q.shape or a.shape != q.shape:
        raise ValueError('Expected six complete joint commands per sample')
    if not all(np.isfinite(x).all() for x in (q,v,a,t)) or t[0] != 0 or np.any(h <= 0):
        raise ValueError('Nonfinite or unordered joint trajectory')
    return np.stack((q[:-1], q[:-1]+h*v[:-1]/5,
                     q[:-1]+2*h*v[:-1]/5+h*h*a[:-1]/20,
                     q[1:]-2*h*v[1:]/5+h*h*a[1:]/20,
                     q[1:]-h*v[1:]/5, q[1:]), axis=1)


def _split_curve(control):
    layers = [control]
    for _ in range(5):
        layers.append((layers[-1][1:]+layers[-1][:-1])/2)
    return np.array([x[0] for x in layers]), np.array([x[-1] for x in reversed(layers)])


def _joint_boxes(trajectory, step):
    """Retain controller knots and split any interval wider than the FCL step."""
    anchor = lower = upper = None
    for interval in bernstein_controls(trajectory['points']):
        stack = [interval]
        while stack:
            c = stack.pop()
            if np.ptp(c, axis=0).max() > step:
                left, right = _split_curve(c)
                stack.extend((right, left))
                continue
            lo, hi = c.min(axis=0), c.max(axis=0)
            if anchor is not None:
                new_lo, new_hi = np.minimum(lower, lo), np.maximum(upper, hi)
                if (new_hi-new_lo).max() <= step:
                    lower, upper = new_lo, new_hi
                    continue
                yield anchor, lower, upper
            anchor, lower, upper = c[0], lo, hi
    if anchor is not None:
        yield anchor, lower, upper
    last = np.array(trajectory['points'][-1]['positions'])
    yield last, last, last


def center_radii(model, arm):
    """Global lever-arm bounds for the actual enclosing sphere centres."""
    if arm in getattr(model,'_carton_center_radii',{}):
        return model._carton_center_radii[arm]
    geometry=model.geometry
    parents={j.find('child').get('link'):j for j in geometry.joints.values()}
    names=joint_names(arm)
    for name in names:
        joint=geometry.joints[name]
        axis=joint.find('axis')
        xyz=np.fromstring(axis.get('xyz'),sep=' ') if axis is not None else np.array([1.,0.,0.])
        if (joint.get('type') not in ('revolute','continuous') or xyz.shape!=(3,) or
                not np.isclose(np.linalg.norm(xyz),1.,atol=1e-12,rtol=0) or joint.find('mimic') is not None):
            raise ValueError('Reviewed stopping model requires six independent unit-axis revolute joints')
    result=np.zeros((len(model.local[arm]),6))
    for link in set(model.links[arm]):
        path=[]
        parent=link
        while parent!='world':
            joint=parents[parent]
            path.insert(0,joint)
            parent=joint.find('parent').get('link')
        ordered=[j.get('name') for j in path if j.get('name') in names]
        tied=any(j.find('mimic') is not None and geometry.dependency(j)[0] in names for j in path)
        if tied or ordered!=names[:len(ordered)]:
            raise ValueError('Stopping bound requires the six UR axes in physical chain order')
        zero=geometry.displacement_radii(path,0.,arm)[:6]
        slope=geometry.displacement_radii(path,1.,arm)[:6]-zero
        mask=np.array([name==link for name in model.links[arm]])
        result[mask]=zero+np.linalg.norm(model.local[arm][mask],axis=1)[:,None]*slope
    if not hasattr(model,'_carton_center_radii'):
        model._carton_center_radii={}
    model._carton_center_radii[arm]=result
    return result


def cartesian_stop_box(jacobian, radii, displacement):
    """Componentwise Taylor enclosure for six serial revolute UR axes.

    For i<=j, differentiating J_j about upstream axis i rotates that
    vector. Its mixed derivative norm is bounded by the global lever arm
    of distal joint j. The diagonal obeys the same bound. This encloses
    the full joint interval, including any combination of braking directions.
    """
    indices=np.maximum.outer(np.arange(6),np.arange(6))
    remainder=.5*np.einsum('nij,i,j->n',radii[:,indices],displacement,displacement)
    directed=np.abs(jacobian) @ displacement + remainder[:,None]
    return np.minimum(directed,(radii @ displacement)[:,None])+1e-12


def swept_arm(problem, start, arm, trajectory, extra_collision, stop_dq):
    """Check static/self geometry and enclose all arm positions by body boxes."""
    geometry = problem.spheres
    names = joint_names(arm)
    radii = center_radii(geometry,arm)
    state = dict(start)
    if trajectory:
        samples = _joint_boxes(trajectory, problem.cfg['joint_check_step_rad'])
    else:
        q = np.asarray([start[j] for j in names])
        samples = [(q, q, q)]
    boxes,stopped = [],[]
    for q, qmin, qmax in samples:
        state.update(zip(names, q))
        if any(lo<problem.collision.bounds[name][0] or hi>problem.collision.bounds[name][1]
               for name,lo,hi in zip(names,qmin,qmax)):
            return None
        if not problem.collision.check(state)[0] or (extra_collision and not extra_collision.check(state)[0]):
            return None
        if np.any(stop_dq):
            world,jacobians=geometry.jacobians(state,[arm])
            jacobian=jacobians[arm]
        else:
            world,_=geometry.planning_world(state)
        centers = world[arm]
        # Every quintic position lies in the joint-space Bernstein hull.
        # The live joint corridor also covers the admitted measured start.
        displacement=np.maximum(q-qmin, qmax-q)+TRACKING_TOLERANCE
        spread = radii @ displacement
        lo = centers-spread[:, None]
        hi = centers+spread[:, None]
        boxes.append((lo,hi))
        if np.any(stop_dq):
            stop_box=cartesian_stop_box(jacobian,radii,displacement+stop_dq)
            stopped.append((centers-stop_box,centers+stop_box))
    return np.asarray(boxes),np.asarray(stopped) if stopped else np.asarray(boxes)


def independent_clearance(left, right, required, margin):
    """Prove separation for the Cartesian product of independently reached intervals.

    A broad, curved sweep can cover empty space. Subdivide only the ambiguous
    time ranges; already separated body pairs need no further norm evaluation.
    """
    @lru_cache(maxsize=None)
    def bounds(side, begin, end):
        boxes=(left if side==0 else right)[begin:end]
        return boxes[:,0].min(axis=0), boxes[:,1].max(axis=0)

    def visit(a0,a1,b0,b1,indices):
        alo,ahi=bounds(0,a0,a1)
        blo,bhi=bounds(1,b0,b1)
        i,j=indices
        gaps=np.maximum(np.maximum(alo[i]-bhi[j],blo[j]-ahi[i]),0.)
        residual=np.linalg.norm(gaps,axis=1)-required[i,j]
        ambiguous=residual<=margin+1e-12
        if not np.any(ambiguous) or (a1-a0==1 and b1-b0==1):
            return float(residual.min())
        lower=float(residual[~ambiguous].min(initial=np.inf))
        subset=(i[ambiguous],j[ambiguous])
        if a1-a0>=b1-b0:
            mid=(a0+a1)//2
            halves=((a0,mid,b0,b1),(mid,a1,b0,b1))
        else:
            mid=(b0+b1)//2
            halves=((a0,a1,b0,mid),(a0,a1,mid,b1))
        for half in halves:
            value=visit(*half,subset)
            if value<=margin+1e-12:
                return float(residual.min())
            lower=min(lower,value)
        return lower

    return visit(0,len(left),0,len(right),np.indices(required.shape).reshape(2,-1))


def prove_group(problem, start, trajectories, joint_limit, extra_collision=None):
    """Independent swept volumes include unequal progress and independent stops."""
    geometry = problem.spheres
    arms = list(trajectories)
    for arm, trajectory in trajectories.items():
        nominal = [start[j] for j in joint_names(arm)]
        if not np.allclose(nominal, trajectory['points'][0]['positions'], atol=1e-9, rtol=0):
            raise ValueError('Frozen trajectory does not start at the scheduled state')
    boxes,stopped = {},{}
    pads, stopping_pads = {}, {}
    for arm in problem.names:
        cap = np.zeros(geometry.motion_radii[arm].shape[1])
        if arm in arms:
            cap[:6] = np.minimum(joint_velocity_limits(problem.cfg,arm),joint_limit)
        bound=SPEED_TOLERANCE*cap[:6]
        cfg=problem.cfg
        dq=bound*(cfg['state_timeout_s']+1/cfg['rate_hz']+cfg['stop_latency_s'])+bound**2/(2*cfg['braking_acceleration_rad_s2'])
        result=swept_arm(problem,start,arm,trajectories.get(arm),extra_collision,
                         dq if len(arms)>1 else np.zeros(6))
        if result is None:
            return None, arm+' self, static, object, or frozen-neighbor collision'
        boxes[arm],stopped[arm]=result
        def padded_radii(profile):
            budget = body_budgets(geometry.motion_radii[arm], np.zeros_like(cap), cap,
                                  profile['state_timeout_s'], profile)['total_m']
            return geometry.radii[arm]+budget
        pads[arm]=padded_radii(problem.cfg)
        # The extra independent stop proof is for two *moving* neighbors.
        # The active profile retains its usual clearance to a held obstacle.
        stopping_pads[arm]=padded_radii(dict(problem.cfg,stopping_reserve_policy='enforce'))
    smallest = np.inf
    pairs=[]
    for a, b in itertools.combinations(problem.names, 2):
        if a not in arms and b not in arms:
            continue
        radii=stopping_pads if a in arms and b in arms else pads
        margin=problem.cfg['model_margin_m']
        geometric_radii=geometry.radii[a][:,None]+geometry.radii[b]
        geom=independent_clearance(boxes[a],boxes[b],geometric_radii,margin)
        scalar=independent_clearance(boxes[a],boxes[b],radii[a][:,None]+radii[b],margin)
        free=scalar
        if a in arms and b in arms:
            directed=independent_clearance(stopped[a],stopped[b],geometric_radii,margin)
            free=max(directed,scalar)
        pairs.append(dict(arms=[a,b],geometric_clearance_lower_bound_m=geom,
                          clearance_with_stop_lower_bound_m=free,model_margin_m=margin,
                          scalar_stop_lower_bound_m=scalar,
                          reserve_policy='independently_braking_pair' if a in arms and b in arms else
                              problem.cfg.get('stopping_reserve_policy','enforce'),
                          stop_allowance_in_clearance_bound_m=max(0.,geom-free)))
        smallest = min(smallest, free)
        if free <= margin+1e-12:
            return dict(pairs=pairs), f'{a}/{b}: independent swept clearance {free:.4f} m'
    return dict(min_clearance_m=smallest, model_margin_m=problem.cfg['model_margin_m'],
                tracking_corridor_rad=TRACKING_TOLERANCE,pairs=pairs,
                stop_policy='independent_stop_envelopes' if len(arms)>1 else problem.cfg.get('stopping_reserve_policy','enforce')), None


def compile_groups(problem, start, parts_by_arm, joint_limit, extra_collision=None):
    """Prefer one common run, then common task subphases, then single-arm runs."""
    arms = tuple(parts_by_arm)
    merged = {a:concatenate(parts_by_arm[a]) for a in arms}
    attempts = []

    def try_group(state, traj):
        proof, error = prove_group(problem, state, traj, joint_limit, extra_collision)
        if error:
            attempts.append(dict(arms=list(traj), reason=error,details=proof))
            return None
        return dict(arms=list(traj), trajectories=traj, start=dict(state),
                    duration_s=max(t['duration_s'] for t in traj.values()), proof=proof)

    def advance(state, traj):
        for arm, path in traj.items():
            state.update(zip(joint_names(arm), path['points'][-1]['positions']))

    group = try_group(start, merged)
    if group:
        return [group], attempts
    if len(arms)==2 and len(parts_by_arm[arms[0]])==len(parts_by_arm[arms[1]])>1:
        stages = [dict(zip(arms, paths)) for paths in zip(*(parts_by_arm[a] for a in arms))]
    else:
        stages = []
    fallback = None
    for candidates in ([stages] if stages else [])+[[merged]]:
        state, groups = dict(start), []
        for stage in candidates:
            joined = try_group(state, stage) if stages and candidates is stages else None
            if joined:
                groups.append(joined)
                advance(state, stage)
                continue
            for order in itertools.permutations(stage):
                next_state, singles = dict(state), []
                for arm in order:
                    single = {arm:stage[arm]}
                    segment = try_group(next_state, single)
                    if segment is None:
                        break
                    advance(next_state, single)
                    singles.append(segment)
                else:
                    groups.extend(singles)
                    state = next_state
                    break
            else:
                break
        else:
            if candidates is stages:
                if any(len(g['arms'])>1 for g in groups):
                    return groups, attempts
                # All stages were serial. Try a complete run per arm first
                # to avoid an unnecessary stop between ALIGN and ENTRY.
                fallback=groups
            else:
                return groups, attempts
    if fallback:
        return fallback, attempts
    raise ValueError('No checked carton schedule: '+str(attempts))


def checker_identity(tools_directory=None):
    """Content identity of the task compiler, geometry and controller interpolation."""
    from ament_index_python.packages import get_package_prefix
    modules=('uwa_cell_tasks.reviewed_carton','uwa_cell_tasks.reviewed_carton_execution',
             'uwa_cell_tasks.hardware_carton_approach','uwa_cell_motion.carton_paths',
             'uwa_cell_motion.planning','uwa_cell_motion.common','uwa_cell_motion.geometry',
             'uwa_cell_motion.hardware_model','uwa_cell_motion.stopping_reserve',
             'uwa_cell_motion.motion_envelope','uwa_cell_motion.pilot_interlock',
             'uwa_cell_motion.single_execution','uwa_cell_calibration.model',
             'uwa_cell_control.scan_separation','uwa_cell_control.view_geometry')
    parts={name:file_hash(find_spec(name).origin) for name in modules}
    if tools_directory is not None:
        for name in ('prepare_carton_pregrasp.py','prepare_carton_open_entry.py',
                     'run_carton_pregrasp.py','run_carton_open_entry.py'):
            parts['tools/'+name]=file_hash(Path(tools_directory)/name)
    for package,library in (('joint_trajectory_controller','libjoint_trajectory_controller.so'),
                            ('ur_controllers','libur_controllers.so'),
                            ('moveit_core','libmoveit_collision_detection_fcl.so')):
        parts[package+'/'+library]=file_hash(Path(get_package_prefix(package))/'lib'/library)
    for name in ('numpy','scipy'):
        parts[name+'_version']=version(name)
    return dict(components=parts,sha256=hashlib.sha256(json.dumps(parts,sort_keys=True).encode()).hexdigest())


def write_bundle(path, phase, problem, start, groups, attempts, source, preview, carton, speed, tcp_speed,
                 tools_directory=None):
    data = dict(schema_version=2, checker=checker_identity(tools_directory), phase=phase, start=start, groups=groups,
                coordination_attempts=attempts, model_signature=problem.signature,
                hardware_binding=problem.binding, source_sha256=file_hash(source),
                preview_urdf=str(preview), preview_urdf_sha256=file_hash(preview), carton=carton,
                joint_limit_rad_s=speed, tcp_limit_m_s=tcp_speed)
    with Path(path).open('x') as output:
        json.dump(data, output, allow_nan=False, separators=(',', ':'))
    return data


def read_bundle(path, expected_hash, phase, problem, source, tools_directory=None):
    data = Path(path).read_bytes()
    if not expected_hash or hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError('Reviewed carton trajectory digest mismatch')
    plan = json.loads(data)
    if plan.get('schema_version')!=2 or plan.get('checker')!=checker_identity(tools_directory):
        raise ValueError('Carton trajectory checker or controller interpolation changed; prepare a new review')
    if (plan.get('phase') != phase or
            plan['model_signature'] != problem.signature or plan['hardware_binding'] != problem.binding or
            plan['source_sha256'] != file_hash(source)):
        raise ValueError('Reviewed carton phase, source or hardware binding changed')
    return plan


def check_boundaries(bundle, expected_start, expected_end, selected):
    state=dict(expected_start)
    seen=set()
    def matches(actual,expected):
        return (set(actual)==set(expected) and
                all(np.isfinite(actual[j]) and abs(actual[j]-q)<=1e-9 for j,q in expected.items()))
    if not matches(bundle['start'],state) or not bundle['groups']:
        raise ValueError('Reviewed start differs from task evidence')
    for group in bundle['groups']:
        arms=set(group['arms'])
        if (not arms or len(arms)!=len(group['arms']) or not arms<=set(selected)
                or set(group['trajectories'])!=arms or not matches(group['start'],state)):
            raise ValueError('Discontinuous reviewed group or changed participants')
        for arm,t in group['trajectories'].items():
            names=joint_names(arm)
            if t['joint_names']!=names or t['duration_s']!=t['points'][-1]['time']:
                raise ValueError('Reviewed joint names or duration changed')
            if not matches(dict(zip(names,t['points'][0]['positions'],strict=True)),{j:state[j] for j in names}):
                raise ValueError('Reviewed controller trajectory first point differs from phase start')
            state.update(zip(names,t['points'][-1]['positions'],strict=True))
        seen.update(arms)
        if group['duration_s']!=max(t['duration_s'] for t in group['trajectories'].values()):
            raise ValueError('Reviewed group duration changed')
    if seen!=set(selected) or not matches(state,expected_end):
        raise ValueError('Reviewed endpoint differs from task evidence')


def add_review_arguments(parser):
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-reviewed', type=Path, metavar='BUNDLE',
                      help='Prepare exact timed unloaded motions for review, offline only')
    mode.add_argument('--reviewed', type=Path, metavar='BUNDLE',
                      help='Run the exact prepared bundle through the review lease')
    parser.add_argument('--reviewed-sha256')
    parser.add_argument('--review-id')
    parser.add_argument('--tcp-speed-m-s', type=float)


def check_review_arguments(parser, args):
    if args.tcp_speed_m_s is None and args.prepare_reviewed:
        args.tcp_speed_m_s=.25*args.command_velocity/.3
    if args.prepare_reviewed and args.execute:
        parser.error('--prepare-reviewed is offline only')
    if args.reviewed and not (args.execute and args.review_id and args.reviewed_sha256):
        parser.error('--reviewed requires --execute, --reviewed-sha256 and --review-id')
    if not args.reviewed and (args.review_id or args.reviewed_sha256):
        parser.error('Review credentials require --reviewed')


def carton_representation(binding, scene, shell_boxes):
    reference=binding['T_world_object_candidate']
    if any(not np.allclose(reference,pose,atol=1e-8,rtol=0)
           for pose in binding.get('world_object_by_arm',{}).values()):
        raise ValueError('Reviewed gripper paths require one physical carton pose for the common preview')
    return dict(world_pose=binding['T_world_object_candidate'], shell_boxes=shell_boxes(scene),
                shapes=[{k:v for k,v in s.items() if k in ('vertices','axis','side','triangles')}
                        for s in scene['shapes']])

"""Offline fixed-corner task and independent arm paths. No robot execution."""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation

from uwa_cell_calibration.model import CollisionModel
from uwa_cell_control.parallel_scan import collision_signature
from uwa_cell_description.scene_assets import instances
from uwa_cell_gazebo.charuco_views import Chain
from .common import ROBOT_IDS, joint_names, nominal_state
from .geometry import SphereModel
from .planning import Problem


UPRIGHT = [0., -np.pi/2, 0., -np.pi/2, 0., 0.]


def upright_start(layout):
    start = nominal_state(layout)
    for arm in ROBOT_IDS:
        start.update(zip(joint_names(arm), UPRIGHT))
    return start


class CartonProblem(Problem):
    """Explicitly add the existing visual carton as a static planning obstacle."""
    def __init__(self, directory, cfg, layout_path=None):
        super().__init__(directory, cfg, layout_path)
        self.carton = next(i for i in instances(self.layout) if i['id'] == 'avocado_carton')
        root = ET.fromstring(self.description)
        link = ET.SubElement(root, 'link', name='offline_carton')
        geometry = ET.SubElement(ET.SubElement(link, 'collision'), 'geometry')
        path = self.carton['mesh_file'].parent/self.carton['manifest']['solid_mesh']
        ET.SubElement(geometry, 'mesh', filename=path.as_uri())
        joint = ET.SubElement(root, 'joint', name='offline_carton_anchor', type='fixed')
        ET.SubElement(joint, 'parent', link='world'); ET.SubElement(joint, 'child', link='offline_carton')
        T = self.carton['T_world_object']
        ET.SubElement(joint, 'origin', xyz=' '.join(map(str, T[:3,3])),
                      rpy=' '.join(map(str, Rotation.from_matrix(T[:3,:3]).as_euler('xyz'))))
        self.description = ET.tostring(root, encoding='unicode')
        self.base_collision = self.collision  # Keep native model/state ownership alive.
        self.collision = CollisionModel(self.description, self.directory/'carton-moveit')
        self.spheres = SphereModel(self.description, self.names, cfg['sphere_spacing_m'])
        self.signature = collision_signature(self.description)
        self.isolated = {}; self.chains = {r: Chain(self.description,'world',r+'_tool0') for r in ROBOT_IDS}
        # Keep all world-fixed geometry, including the other robots' base bodies.
        anchored = {'world'}
        for _ in root.findall('joint'):
            for j in root.findall('joint'):
                if j.get('type') == 'fixed' and j.find('parent').get('link') in anchored:
                    anchored.add(j.find('child').get('link'))
        for arm in ROBOT_IDS:
            isolated = ET.fromstring(self.description)
            for link in isolated.findall('link'):
                name = link.get('name')
                if name not in anchored and any(name.startswith(other+'_') for other in ROBOT_IDS if other != arm):
                    for collision in link.findall('collision'): link.remove(collision)
            self.isolated[arm] = CollisionModel(ET.tostring(isolated, encoding='unicode'), self.directory/('single-'+arm))


def corner_targets(problem, *, entry_depth_m=.015, pregrasp_m=.12):
    """One immutable top-down pose per nearest corner; nominal TCP at gripper z=.145m."""
    if not 0 <= entry_depth_m <= .04 or not .02 <= pregrasp_m <= .3:
        raise ValueError('Unsupported corner depth or pregrasp distance')
    item = problem.carton; dims = np.asarray(item['manifest']['dimensions_m']); T = item['T_world_object']
    corners = np.asarray([[x,y,dims[2]] for x in [0.,dims[0]] for y in [0.,dims[1]]])
    world = corners@T[:3,:3].T+T[:3,3]
    targets = {}; used = set()
    for arm in ROBOT_IDS:
        base = Chain(problem.description,'world',arm+'_base_link').forward({})[:3,3]
        index = int(np.argmin(np.linalg.norm(world[:,:2]-base[:2],axis=1)))
        if index in used: raise ValueError('Nearest corners are not uniquely assigned in this layout')
        used.add(index)
        local = corners[index].copy(); local[2] -= entry_depth_m
        closing = T[:3,:3]@np.array([1 if local[0]==0 else -1,1 if local[1]==0 else -1,0.])
        closing /= np.linalg.norm(closing)
        down = np.array([0.,0.,-1.]); R = np.column_stack([closing,np.cross(down,closing),down])
        tcp = T[:3,:3]@local+T[:3,3]
        gripper = np.eye(4);gripper[:3,:3]=R;gripper[:3,3]=tcp-R@np.array([0.,0.,.145])
        tool_gripper = Chain(problem.description,arm+'_tool0',arm+'_robotiq_85_base_link').forward({})
        target = gripper@np.linalg.inv(tool_gripper)
        pre = target.copy();pre[:3,3]+=[0,0,pregrasp_m]
        targets[arm] = dict(corner_index=index, corner_world_m=world[index].tolist(),
                            tcp_world_m=tcp.tolist(), tool0_target=target.tolist(),
                            tool0_pregrasp=pre.tolist(), tool0_to_tcp=(tool_gripper@np.array([[1,0,0,0],[0,1,0,0],[0,0,1,.145],[0,0,0,1]])).tolist())
    return targets


def pose_goal(arm, matrix):
    T = np.asarray(matrix)
    return dict(frame_id='world', target_link=arm+'_tool0',
                pose=dict(position=T[:3,3].tolist(), orientation_xyzw=Rotation.from_matrix(T[:3,:3]).as_quat().tolist()))


def solve_near(problem, arm, start, target, guess):
    names = joint_names(arm); bounds = np.asarray([problem.collision.bounds[j] for j in names]).T
    target = np.asarray(target); chain = problem.chains[arm]
    def residual(q):
        actual = chain.forward(dict(start, **dict(zip(names,q))))
        return np.r_[actual[:3,3]-target[:3,3],Rotation.from_matrix(actual[:3,:3]@target[:3,:3].T).as_rotvec()]
    fit = least_squares(residual,np.clip(guess,bounds[0]+1e-9,bounds[1]-1e-9),bounds=bounds,max_nfev=150,
                        ftol=1e-11,xtol=1e-11,gtol=1e-11)
    error = residual(fit.x)
    if np.linalg.norm(error[:3])>2e-5 or np.linalg.norm(error[3:])>2e-4:
        raise ValueError('Continuous Cartesian IK failed')
    return fit.x


def quintic(u):
    u = np.asarray(u)
    return 10*u**3-15*u**4+6*u**5


def joint_segment(a,b):
    return dict(kind='JOINT', knots=[0.,1.], positions=np.asarray([a,b]).tolist())


def cartesian_entry(problem, arm, start, target, goal_q, pregrasp_m=.12):
    """Continue backward from a fixed goal branch, then traverse downwards."""
    target = np.asarray(target); q = np.asarray(goal_q); upward = [q.tolist()]
    count = int(np.ceil(pregrasp_m/.002))
    for dz in np.linspace(0,pregrasp_m,count+1)[1:]:
        T = target.copy();T[2,3]+=dz
        following = solve_near(problem,arm,start,T,q)
        if np.max(np.abs(following-q))>.15:raise ValueError('Cartesian entry branch jump')
        q=following;upward.append(q.tolist())
    return dict(kind='CARTESIAN_LINE',knots=np.linspace(0,1,len(upward)).tolist(),
                positions=upward[::-1],target=target.tolist(),pregrasp_m=pregrasp_m)


def evaluate(segment,u,derivative=0):
    """C2 joint function with zero velocity and acceleration at every primitive end."""
    u=np.asarray(u); h=quintic(u)
    hp=30*u**2-60*u**3+30*u**4;hpp=60*u-180*u**2+120*u**3
    spline=CubicSpline(segment['knots'],segment['positions'],bc_type='natural')
    if derivative==0:return spline(h)
    if derivative==1:return spline(h,1)*np.expand_dims(hp,-1)
    if derivative==2:return spline(h,2)*np.expand_dims(hp**2,-1)+spline(h,1)*np.expand_dims(hpp,-1)
    raise ValueError('Expected derivative 0, 1 or 2')


def validate_segment(problem, arm, start, segment, *, joint_step=.005):
    """Dense sampling of the actual smoothed primitive, not only its knots."""
    u=np.linspace(0,1,257)
    for _ in range(8):
        q=evaluate(segment,u)
        if np.max(np.abs(np.diff(q,axis=0)))<=joint_step:break
        u=np.linspace(0,1,2*len(u)-1)
    else:raise ValueError('Sampling refinement limit')
    max_line_error=0.;max_angle_error=0.
    for phase,positions in zip(u,q):
        state=dict(start,**dict(zip(joint_names(arm),positions)))
        if not problem.isolated[arm].check(state)[0]:
            raise ValueError(f'{arm}: static/self/carton collision at primitive progress {phase:.6f}')
        if segment['kind']=='CARTESIAN_LINE':
            wanted=np.asarray(segment['target']).copy();wanted[2,3]+=segment['pregrasp_m']*(1-quintic(phase))
            actual=problem.chains[arm].forward(state)
            error=np.linalg.norm(actual[:3,3]-wanted[:3,3])
            angle=np.linalg.norm(Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).as_rotvec())
            max_line_error=max(max_line_error,float(error));max_angle_error=max(max_angle_error,float(angle))
            if error>1e-4 or angle>1e-3:raise ValueError('Smoothed Cartesian entry exceeds pose tolerance')
    # Timing is a conservative sampled estimate for the offline animation only.
    v=np.max(abs(evaluate(segment,u,1)));a=np.max(abs(evaluate(segment,u,2)))
    duration=max(1.,1.1*v/problem.cfg['velocity_limit_rad_s'],np.sqrt(1.1*a/problem.cfg['acceleration_limit_rad_s2']))
    return dict(samples=len(u),max_joint_step_rad=float(np.max(abs(np.diff(q,axis=0)))),
                max_line_error_m=max_line_error,max_angle_error_rad=max_angle_error,
                duration_s=float(duration),validation='SAMPLED_STATIC_SELF_CARTON_CLEAR',
                limits_kind='sampled nominal animation timing; not certified controller dynamics')


def independent_paths(problem,start,candidates,targets,compatible_ids,*,max_paths=3,progress=None):
    """Keep target branch alternatives, with direct and via-point joint primitives."""
    paths={};failures={}
    for arm in ROBOT_IDS:
        paths[arm]=[];failures[arm]=[];initial=np.array([start[j] for j in joint_names(arm)])
        for candidate in candidates[arm]:
            cid=candidate['id']
            if cid not in compatible_ids:continue
            try:
                pregrasp=round(float(np.asarray(targets[arm]['tool0_pregrasp'])[2,3]-np.asarray(targets[arm]['tool0_target'])[2,3]),10)
                entry=cartesian_entry(problem,arm,start,targets[arm]['tool0_target'],candidate['positions'],pregrasp)
                entry['check']=validate_segment(problem,arm,start,entry)
            except ValueError as error:
                failures[arm].append(dict(candidate_id=cid,stage='cartesian_entry',reason=str(error)));continue
            pre=np.array(entry['positions'][0]);rotated=initial.copy();rotated[0]=pre[0]
            strategies=[('direct',[initial,pre]),('pan_first',[initial,rotated,pre])]
            # A geometric alternate that first establishes the pregrasp elbow
            # bend with an upright shoulder, then moves to the pregrasp.
            folded=rotated.copy();folded[2]=pre[2];folded[3]=-np.pi/2-pre[2]
            strategies.append(('pan_then_fold',[initial,rotated,folded,pre]))
            for strategy,points in strategies:
                try:
                    segments=[]
                    for a,b in zip(points,points[1:]):
                        if np.linalg.norm(np.asarray(b)-a)<1e-8:continue
                        segment=joint_segment(a,b);segment['check']=validate_segment(problem,arm,start,segment)
                        segments.append(segment)
                    segments.append(entry)
                    cost=sum(float(np.linalg.norm(np.diff(evaluate(s,np.linspace(0,1,257)),axis=0),axis=1).sum()) for s in segments)
                    paths[arm].append(dict(id=cid+'/'+strategy,candidate_id=cid,strategy=strategy,
                                           segments=segments,joint_arc_length_rad=cost,
                                           duration_s=sum(s['check']['duration_s'] for s in segments)))
                    if progress:progress(arm,paths[arm][-1]['id'])
                    break
                except ValueError as error:
                    failures[arm].append(dict(candidate_id=cid,stage=strategy,reason=str(error)))
            if len(paths[arm])>=max_paths:break
        if progress:progress(arm,f'{len(paths[arm])} paths, {len(failures[arm])} rejected attempts')
    return paths,failures


def path_at(path,time_s):
    remaining=max(0.,time_s)
    for segment in path['segments']:
        duration=segment['check']['duration_s']
        if remaining<=duration:return evaluate(segment,remaining/duration)
        remaining-=duration
    return np.asarray(path['segments'][-1]['positions'][-1])


def diagnose_parallel(problem,start,paths,*,dt=.1):
    """Inspect one uncoordinated start-at-zero schedule; do not resolve conflicts."""
    import itertools
    duration=max(p['duration_s'] for p in paths.values())
    times=np.linspace(0,duration,int(np.ceil(duration/dt))+1)
    thresholds={tuple(sorted(p['arms'])):p['threshold_m'] for p in problem.thresholds()}
    records=[];minimum=float('inf');collisions=0
    for t in times:
        state=dict(start)
        for arm,path in paths.items():state.update(zip(joint_names(arm),path_at(path,float(t))))
        world=problem.spheres.world(state);pairs=[]
        for a,b in itertools.combinations(ROBOT_IDS,2):
            gap=float(problem.spheres.nearest(world,a,b)['clearance_m']);minimum=min(minimum,gap)
            threshold=max(problem.cfg['model_margin_m'],thresholds.get(tuple(sorted((a,b))),0.))
            if gap<threshold:pairs.append(dict(arms=[a,b],gap_m=gap,threshold_m=threshold))
        fcl=problem.collision.check(state)[0];collisions+=not fcl
        if pairs or not fcl:records.append(dict(time_s=float(t),fcl_clear=bool(fcl),pairs=pairs))
    return dict(kind='UNCOORDINATED_SIMULTANEOUS_START_DIAGNOSTIC',samples=len(times),
                max_sample_time_step_s=float(times[1]-times[0]),duration_s=duration,
                conflict_samples=len(records),fcl_collision_samples=collisions,
                min_pair_gap_m=minimum,conflicts=records,
                synchronized_trajectory_certified=False)

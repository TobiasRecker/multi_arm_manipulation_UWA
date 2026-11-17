"""Diverse checked initial states for the fixed-grasp offline teacher."""
import itertools
import numpy as np
from scipy.spatial.transform import Rotation

from .common import joint_names
from .carton_paths import solve_near
from .two_arm_teacher import specification
from .teacher_dataset import pose_error


def start_families():
    """Declared spatial/orientation families, including retained failed starts."""
    rows=[
        ('west_low',[-.12,-.08,.04],[0,-25,-15],'train'),
        ('west_high',[-.12,.08,.14],[10,25,15],'test'),
        ('south',[0,-.16,.08],[0,0,-35],'train'),
        ('north',[0,.16,.08],[0,0,35],'validation'),
        ('east_low',[.16,-.10,.04],[0,-55,0],'train'),
        ('east_high',[.16,.10,.14],[0,50,0],'test'),
        ('centre_high',[0,0,.18],[15,20,-15],'validation'),
        ('negative_tilt',[.12,0,.06],[0,-65,0],'train'),
        ('positive_tilt',[.12,0,.10],[0,60,0],'validation'),
        ('west_yaw',[-.08,0,.12],[0,0,50],'train'),
        ('east_yaw',[.20,0,.10],[0,0,-45],'test'),
        ('negative_oblique',[.12,-.04,.13],[0,-50,-10],'train'),
    ]
    return [dict(id=name,family=name,translation_m=p,rotation_vector_deg=r,split=split,
                 tasks=tasks(name,i,p,r)) for i,(name,p,r,split) in enumerate(rows)]


def tasks(name,index,start_m,start_r):
    sign=-1 if index%2 else 1
    pure=(specification(name+'/translation',goal_m=[-.035,sign*.025,.012],excursion_m=[.015,-sign*.01,.008])
          if index%2==0 else specification(name+'/rotation',rotation_deg=[4,sign*12,-5],goal_rotation_deg=[3,-sign*7,4]))
    rotation=[4,sign*18,-5]
    if start_r[1]<-40:rotation=[2,-32,2]
    if start_r[1]>40:rotation=[-3,25,4]
    mixed=specification(name+'/mixed',[.025,sign*.015,-.012],rotation,
                        [-.025,-sign*.025,.008],[3,-sign*6,4])
    return [dict(category='translation3d' if index%2==0 else 'rotation3d',task=pure),
            dict(category='mixed6d',task=mixed)]


def make_pose(anchor,family):
    pose=np.array(anchor,copy=True);pose[:3,3]+=family['translation_m']
    pose[:3,:3]=Rotation.from_rotvec(np.deg2rad(family['rotation_vector_deg'])).as_matrix()@anchor[:3,:3]
    return pose


def wrapped_distance(a,b):
    return float(np.linalg.norm((np.asarray(a)-b+np.pi)%(2*np.pi)-np.pi))


def state_check(p,pose,state):
    _,sigmas=p.differential(pose,state);errors=[]
    for arm in p.arms:
        actual=p.problem.chains[arm].forward(state)@p.tcp_offsets[arm]
        error=pose_error(pose@p.offsets[arm],actual)
        errors.append([float(np.linalg.norm(error[:3])),float(np.linalg.norm(error[3:]))])
    gap=min(x['clearance_m'] for x in p.distances(pose,state))
    result=dict(fcl_clear=p.full_check(pose,state),pair_gap_m=gap,
        object_box_gap_m=float(p.environment_gaps(pose).min()),object_arm_gap_m=float(p.object_arm_gaps(pose,state).min()),
        min_scaled_sigma=min(sigmas.values()),closure_m=max(e[0] for e in errors),closure_rad=max(e[1] for e in errors),
        joint_bounds_ok=all(p.collision.bounds[n][0]<=state[n]<=p.collision.bounds[n][1] for n in p.names))
    result['passed']=bool(result['fcl_clear'] and gap>=.02 and result['object_box_gap_m']>=.003 and
        result['object_arm_gap_m']>=.003 and result['min_scaled_sigma']>=.05 and result['closure_m']<=1e-6 and
        result['closure_rad']<=1e-5 and result['joint_bounds_ok'])
    return result


def discover_start(p,family,seed=20261117):
    """Multi-start single-arm IK, then coupled geometric acceptance.

    No valid approach from the anchor is claimed. Joint solutions differing
    only by full revolutions are deduplicated. Every attempted combined state
    remains in diagnostics. Select the valid pair with smallest arm clearance
    to include tighter configurations without weakening acceptance criteria.
    """
    anchor=p.initial.copy();anchor_state=dict(p.start);pose=make_pose(anchor,family)
    rng=np.random.default_rng(seed);per_arm={};attempts=[]
    for arm in p.arms:
        names=joint_names(arm);base=np.array([anchor_state[n] for n in names]);solutions=[]
        guesses=[base.copy()]
        for axis in (2,4,0):
            q=base.copy();q[axis]*=-1;guesses.append(q)
        guesses.extend(base+rng.uniform(-np.pi,np.pi,6) for _ in range(6))
        for index,guess in enumerate(guesses):
            try:
                target=pose@p.offsets[arm]@np.linalg.inv(p.tcp_offsets[arm])
                q=solve_near(p.problem,arm,anchor_state,target,guess)
                q=base+(q-base+np.pi)%(2*np.pi)-np.pi
                if any(not p.collision.bounds[n][0]<=v<=p.collision.bounds[n][1] for n,v in zip(names,q)):
                    raise ValueError('Normalized IK outside bounds')
                if not any(wrapped_distance(q,old)<.05 for old in solutions):solutions.append(q)
                attempts.append(dict(arm=arm,seed=index,solved=True))
            except (ValueError,np.linalg.LinAlgError) as error:
                attempts.append(dict(arm=arm,seed=index,solved=False,reason=str(error)))
        per_arm[arm]=solutions
    combined=[];valid=[]
    for index,qs in enumerate(itertools.product(*(per_arm[a] for a in p.arms))):
        state=dict(anchor_state)
        for arm,q in zip(p.arms,qs):state.update(zip(joint_names(arm),q))
        try:
            state=p.solve(pose,state)  # refine grasp closure to teacher tolerance
            check=state_check(p,pose,state)
            record=dict(id=index,state=state,check=check)
            if check['passed']:valid.append(record)
        except (ValueError,np.linalg.LinAlgError) as error:record=dict(id=index,check=dict(passed=False,reason=str(error)))
        combined.append(record)
    selected=min(valid,key=lambda c:(c['check']['pair_gap_m'],c['id'])) if valid else None
    return dict(family=family,initial_pose=pose.tolist(),arm_solution_counts={a:len(v) for a,v in per_arm.items()},
                ik_attempts=attempts,combined_candidates=combined,valid_candidates=len(valid),
                selected=selected,status='VALID_START' if selected else 'NO_VALID_START',
                scope='Checked hypothetical initial grasp configuration; no approach or branch-change trajectory')


def coverage(results,anchor):
    valid=[r for r in results if r.get('selected')]
    if not valid:return dict(valid_starts=0)
    poses=np.array([r['initial_pose'] for r in valid]);positions=poses[:,:3,3]
    pd=[];rd=[]
    for a,b in itertools.combinations(poses,2):
        pd.append(float(np.linalg.norm(a[:3,3]-b[:3,3])))
        rd.append(float(np.rad2deg(Rotation.from_matrix(a[:3,:3]@b[:3,:3].T).magnitude())))
    return dict(valid_starts=len(valid),position_span_xyz_m=np.ptp(positions,axis=0).tolist(),
        max_pair_position_distance_m=max(pd,default=0),max_pair_orientation_angle_deg=max(rd,default=0),
        anchor_distances_m=[float(np.linalg.norm(p[:3,3]-anchor[:3,3])) for p in poses],
        start_arm_clearances_m=[r['selected']['check']['pair_gap_m'] for r in valid],
        families_with_alternative_valid_ik=sum(r['valid_candidates']>1 for r in valid))

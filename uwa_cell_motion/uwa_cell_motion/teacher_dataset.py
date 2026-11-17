"""Reproducible task families and geometric BC records; no policy or execution.

All poses/actions use the world frame. Rotation errors are SO(3) logarithms,
not Euler-angle subtraction. Reference lookahead never contains teacher
corrections. A transition advances path progress, not a fixed wall-clock time.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from .two_arm_teacher import pose_at, specification
from .smooth_paths import curve


HORIZONS = (.025, .05, .10, .20)
SCHEMA = dict(
    observation_size=52, action_size=6, progress_step=.01,
    observation_fields=dict(joints_rad=[0,12], object_position_m=[12,15],
        object_rotation_columns=[15,21], goal_error_world_m_rad=[21,27],
        progress=[27,28], reference_lookahead_world_m_rad=[28,52]),
    rotation_columns='first column followed by second column of world rotation matrix',
    action='next world position minus current; Log(R_next R_current^T) in radians',
    reference_horizons=list(HORIZONS), units='raw SI; fit normalization on train only',
    step_semantics='geometric progress +0.01, NOT a velocity or a fixed-time command',
    observation_scope='fixed object, fixed grasps/bases and parked-arm scene; no obstacle generalization',
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n');tmp.replace(path)


def families(seed=20261117):
    """Freeze 16 families x 2 local variants before any feasibility filtering.

    This is a small designed pilot, not a uniform distribution over SE(3).
    Noncollinear goal and excursion rotation vectors change rotation axes
    along the reference. Zero rotation/translation categories refer only to
    the reference; six-dimensional teacher corrections remain permitted.
    """
    rng=np.random.default_rng(seed);cases=[]
    rotations=[[12,20,15],[-15,-35,20],[15,55,-10],[-12,-85,14],
               [25,15,35],[-20,-50,-25],[10,70,20],[-15,-95,-20]]
    for category,n in [('translation3d',4),('rotation3d',4),('mixed6d',8)]:
        splits=(['train','validation','train','test'] if n==4 else
                ['train','validation','train','test','test','train','validation','train'])
        for f in range(n):
            family=f'{category}-{f:02d}'
            start_m=rng.uniform(-.008,.008,3);start_m[2]=abs(start_m[2])
            start_r=rng.uniform(-2,2,3)
            sign=np.array([1 if f%2==0 else -1,1 if f%3==0 else -1,1])
            goal=np.array([.06,.025,.018])*sign
            excursion=np.array([.035,.012,.012])*sign
            rotation=np.array(rotations[f],float)
            goal_rotation=np.array([5,-7,9])*np.array([sign[1],sign[0],1])
            if category=='translation3d':rotation[:]=0;goal_rotation[:]=0
            if category=='rotation3d':
                goal[:]=0;excursion[:]=0
                rotation=np.array([[12,25,15],[-15,-30,20],[18,40,-12],[-12,-55,18]][f],float)
            if category=='mixed6d' and f in (2,3,5,6,7):excursion[0]=.12
            for variant in range(2):
                factor=1+(.06 if variant else -.06)
                task=specification(f'{family}/v{variant}',excursion*factor,rotation*factor,
                                   goal*factor,goal_rotation*factor)
                cases.append(dict(id=f'{family}-v{variant}',family=family,category=category,
                    split=splits[f],variant=variant,task=task,
                    initial_translation_m=(start_m+variant*np.array([.002,-.001,.001])).tolist(),
                    initial_rotation_vector_deg=(start_r+variant*np.array([.3,-.2,.1])).tolist()))
    return cases


def set_initial(p, case, anchor_pose, anchor_state):
    """IK initialization only; explicitly not an approach/pickup trajectory."""
    p.initial=np.array(anchor_pose,copy=True);p.start=dict(anchor_state)
    shift=np.array(case['initial_translation_m']);rot=np.deg2rad(case['initial_rotation_vector_deg'])
    state=dict(anchor_state)
    for a in np.linspace(0,1,11):
        pose=np.array(anchor_pose,copy=True);pose[:3,3]+=a*shift
        pose[:3,:3]=Rotation.from_rotvec(a*rot).as_matrix()@anchor_pose[:3,:3]
        state=p.solve(pose,state)
    p.initial=pose;p.start=state
    _,sigmas=p.differential(pose,state)
    checks=dict(fcl_clear=p.full_check(pose,state),
                pair_gap_m=min(v['clearance_m'] for v in p.distances(pose,state)),
                object_box_gap_m=float(p.environment_gaps(pose).min()),
                object_arm_gap_m=float(p.object_arm_gaps(pose,state).min()),
                min_scaled_sigma=min(sigmas.values()))
    checks['passed']=bool(checks['fcl_clear'] and checks['pair_gap_m']>=.02 and
                         checks['object_box_gap_m']>=.003 and checks['object_arm_gap_m']>=.003
                         and checks['min_scaled_sigma']>=.05)
    return checks


def pose_error(target, current):
    return np.r_[target[:3,3]-current[:3,3],
                 Rotation.from_matrix(target[:3,:3]@current[:3,:3].T).as_rotvec()]


def observation(initial, task, pose, q, s):
    goal=pose_at(initial,task,1,np.zeros((6,6)))
    lookahead=[pose_error(pose_at(initial,task,min(1,s+h),np.zeros((6,6))),pose)
               for h in HORIZONS]
    return np.r_[q,pose[:3,3],pose[:3,0],pose[:3,1],pose_error(goal,pose),s,
                 np.concatenate(lookahead)]


def transitions(initial, trajectory):
    """Read the validated joint spline, never re-solve a different IK path."""
    if trajectory.get('executable') is not False:
        raise ValueError('Expected an explicitly offline trajectory')
    progress=np.linspace(0,1,101);spline=curve(trajectory['segment'])
    q=spline(progress)
    poses=np.array([pose_at(initial,trajectory['task'],float(s),trajectory['controls']) for s in progress])
    obs=np.array([observation(initial,trajectory['task'],pose,joints,float(s))
                  for s,pose,joints in zip(progress[:-1],poses[:-1],q[:-1])])
    actions=np.array([pose_error(b,a) for a,b in zip(poses[:-1],poses[1:])])
    return dict(observations=obs,actions=actions,q=q[:-1],q_next=q[1:],
                object_pose=poses[:-1],object_pose_next=poses[1:],
                progress=progress[:-1],next_progress=progress[1:],
                terminal=np.arange(100)==99)


def validate_export(p, records):
    """The uniform-progress export has a different grid: check it as well."""
    failures=[];maximum_position=maximum_angle=0.
    poses=np.concatenate([records['object_pose'],records['object_pose_next'][-1:]])
    qs=np.concatenate([records['q'],records['q_next'][-1:]])
    for i,(pose,q) in enumerate(zip(poses,qs)):
        state=dict(p.start,**dict(zip(p.names,q)));_,sigma=p.differential(pose,state)
        pe=ae=0.
        for arm in p.arms:
            actual=p.problem.chains[arm].forward(state)@p.tcp_offsets[arm]
            error=pose_error(pose@p.offsets[arm],actual)
            pe=max(pe,float(np.linalg.norm(error[:3])));ae=max(ae,float(np.linalg.norm(error[3:])))
        maximum_position=max(maximum_position,pe);maximum_angle=max(maximum_angle,ae)
        if (not p.full_check(pose,state) or
            min(v['clearance_m'] for v in p.distances(pose,state))<.02-1e-8 or
            p.environment_gaps(pose).min()<.003-1e-8 or p.object_arm_gaps(pose,state).min()<.003-1e-8 or
            min(sigma.values())<.05 or pe>1e-6 or ae>1e-5 or
            any(not p.collision.bounds[n][0]<=state[n]<=p.collision.bounds[n][1] for n in p.names)):
            failures.append(i)
    return dict(passed=not failures,samples=len(poses),failed_indices=failures,
                max_closure_position_m=maximum_position,max_closure_angle_rad=maximum_angle)

"""Offline four-arm rigid-object kinematics and gradient-based yaw correction.

The grasp is hypothetical: open gripper geometry is retained, no contacts or
execution are asserted. All six arm pairs and the moving object are checked.
"""
import hashlib
import itertools
import json
from pathlib import Path
import struct

import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation

from .carton_paths import CartonProblem
from .common import ROBOT_IDS,config,joint_names

PAIRS=tuple(itertools.combinations(ROBOT_IDS,2))


def skew(v):
    x,y,z=v
    return np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])


def yaw_basis(s):
    """Eight quintic B-spline controls, endpoint values fixed to zero.

    Convex-hull property keeps yaw inside the control bounds continuously.
    """
    knots=np.r_[np.zeros(6),1/3,2/3,np.ones(6)]
    return BSpline(knots,np.eye(8),5)(s)[...,1:-1]


def object_pose(initial,offset,lift,s,yaw=0.):
    if not 0<=s<=1 or lift<=0:raise ValueError('Invalid progress or lift')
    p=initial.copy();u=s*3
    if u<=1:delta=np.array([0.,0.,lift*u])
    elif u<=2:delta=np.array(offset)*(u-1)+[0,0,lift]
    else:delta=np.array(offset)+[0,0,lift*(3-u)]
    p[:3,3]+=delta
    p[:3,:3]=Rotation.from_rotvec([0,0,yaw]).as_matrix()@initial[:3,:3]
    return p


class ObjectTransport:
    def __init__(self,directory,source,*,arms=None):
        self.arms=tuple(ROBOT_IDS if arms is None else arms)
        if not self.arms or len(set(self.arms))!=len(self.arms) or set(self.arms)-set(ROBOT_IDS):
            raise ValueError('Expected unique known carrying arms')
        self.source=Path(source).resolve();raw=self.source.read_bytes();self.saved=json.loads(raw)
        self.source_sha256=hashlib.sha256(raw).hexdigest()
        if self.saved['executable'] is not False:raise ValueError('Expected offline source')
        baseline=Path(self.saved['source_path']).parent
        binding=json.loads((baseline/'comparison.json').read_text())
        root=Path(binding['source_path']).parent
        if hashlib.sha256((root/'paths.json').read_bytes()).hexdigest()!=binding['source_sha256']:
            raise ValueError('Primitive source changed')
        self.primitive_root=root
        self.problem=CartonProblem(directory,config(root/'motion.yaml'),root/'layout.yaml')
        p=self.problem
        if p.signature!=self.saved['model_signature'] or p.spheres.geometry.assets!=self.saved['mesh_sha256']:
            raise ValueError('Frozen model/meshes changed')
        self.dimensions=np.array(self.saved['task']['dimensions_m'])
        mesh=p.carton['mesh_file'].parent/p.carton['manifest']['solid_mesh'];mesh_raw=mesh.read_bytes()
        if hashlib.sha256(mesh_raw).hexdigest()!=self.saved['object_mesh_sha256']:raise ValueError('Object mesh changed')
        n=struct.unpack_from('<I',mesh_raw,80)[0]
        self.triangles=np.array([[struct.unpack_from('<3f',mesh_raw,84+k*50+12+i*12) for i in range(3)] for k in range(n)])
        self.initial=np.array(self.saved['task']['object_pose']);self.initial[:3,3]+=self.initial[:3,:3]@(self.dimensions/2)
        self.start=dict(self.saved['task']['start']);self.names=[j for a in self.arms for j in joint_names(a)]
        for arm in self.arms:
            path=self.saved['paths'][arm]
            self.start.update(zip(joint_names(arm),path['segments'][-1]['positions'][-1]))
        self.tcp_offsets={a:np.array(self.saved['task']['targets'][a]['tool0_to_tcp']) for a in ROBOT_IDS}
        self.offsets={a:np.linalg.inv(self.initial)@p.chains[a].forward(self.start)@self.tcp_offsets[a] for a in self.arms}
        for value in self.offsets.values():value.setflags(write=False)
        # Use the original robot-only scene: the carton must NOT remain fixed in
        # its old URDF position or inherit fixed-world collision exemptions.
        self.collision=p.base_collision
        self._prepare_object()
        self.update_object(self.initial)

    def _prepare_object(self):
        from moveit_msgs.msg import CollisionObject
        from shape_msgs.msg import Mesh,MeshTriangle
        from geometry_msgs.msg import Point,Pose
        obj=CollisionObject();obj.header.frame_id='world';obj.id='offline_carried_carton'
        vertices=self.triangles.reshape(-1,3);mesh=Mesh()
        mesh.vertices=[Point(x=float(x),y=float(y),z=float(z)) for x,y,z in vertices]
        mesh.triangles=[MeshTriangle(vertex_indices=[3*i,3*i+1,3*i+2]) for i in range(len(self.triangles))]
        obj.meshes=[mesh];obj.mesh_poses=[Pose()];obj.operation=CollisionObject.ADD
        self.object_message=obj

    def object_origin(self,pose):
        origin=pose.copy();origin[:3,3]-=origin[:3,:3]@(self.dimensions/2)
        return origin

    def update_object(self,pose):
        origin=self.object_origin(pose);q=Rotation.from_matrix(origin[:3,:3]).as_quat()
        msg=self.object_message.mesh_poses[0]
        msg.position.x,msg.position.y,msg.position.z=map(float,origin[:3,3])
        msg.orientation.x,msg.orientation.y,msg.orientation.z,msg.orientation.w=map(float,q)
        self.collision.scene.apply_collision_object(self.object_message)
        # No object/robot/table contact exemptions: the source has open fingers
        # and nominal 3 mm object/table clearance, not a contact-supported grasp.

    def arm_kinematics(self,arm,state):
        T=np.eye(4);axes={}
        for name,kind,fixed,axis in self.problem.chains[arm].joints:
            T=T@fixed
            if kind in ('revolute','continuous'):
                axes[name]=(T[:3,3].copy(),T[:3,:3]@axis)
                rot=np.eye(4);rot[:3,:3]=Rotation.from_rotvec(axis*state.get(name,0.)).as_matrix();T=T@rot
        tcp=T@self.tcp_offsets[arm];J=np.zeros((6,6))
        for k,name in enumerate(joint_names(arm)):
            origin,axis=axes[name];J[:3,k]=np.cross(axis,tcp[:3,3]-origin);J[3:,k]=axis
        return tcp,J

    def solve(self,pose,seed):
        state=dict(seed)
        for arm in self.arms:
            names=joint_names(arm);target=pose@self.offsets[arm];initial=np.array([seed[j] for j in names])
            q=initial.copy()
            for _ in range(30):
                state.update(zip(names,q));tcp,J=self.arm_kinematics(arm,state)
                error=np.r_[target[:3,3]-tcp[:3,3],Rotation.from_matrix(target[:3,:3]@tcp[:3,:3].T).as_rotvec()]
                if np.max(abs(error))<1e-9:break
                try:step=np.linalg.solve(J,error)
                except np.linalg.LinAlgError as exc:raise ValueError(arm+': singular IK') from exc
                step*=min(1.,.15/max(np.max(abs(step)),1e-12));q+=step
                if any(not self.collision.bounds[j][0]<=value<=self.collision.bounds[j][1] for j,value in zip(names,q)):
                    raise ValueError(arm+': joint bound during continuation')
            else:raise ValueError(arm+': continuous IK did not converge')
            if np.max(abs(q-initial))>.5:raise ValueError(arm+': continuation jump')
        return state

    def differential(self,pose,state):
        blocks=[];sigmas={};S=np.diag([2.,2.,2.,1.,1.,1.])
        for arm in self.arms:
            tcp,J=self.arm_kinematics(arm,state);A=np.eye(6);A[:3,3:]=-skew(tcp[:3,3]-pose[:3,3])
            sv=np.linalg.svd(S@J,compute_uv=False)
            sigmas[arm]=float(sv[-1])
            if sv[-1]<1e-6:raise ValueError(arm+': singular differential kinematics')
            blocks.append(np.linalg.solve(J,A))
        return np.vstack(blocks),sigmas

    def distances(self,pose,state,gradients=False):
        p=self.problem
        if gradients:world,jac=p.spheres.jacobians(state,self.arms);K,sigmas=self.differential(pose,state)
        else:world=p.spheres.world(state)
        result=[]
        for a,b in PAIRS:
            record=dict(arms=[a,b],**p.spheres.nearest(world,a,b))
            if gradients:
                i,j=record['sphere_indices'];n=world[a][i]-world[b][j];n/=max(np.linalg.norm(n),1e-12)
                record['gradient']=(n@(jac[a][i]-jac[b][j])@K).tolist()
            result.append(record)
        return result

    def full_check(self,pose,state):
        self.update_object(pose)
        return bool(self.collision.check(state)[0])

    def path(self,offset,lift,controls=None,count=61,gradients=False):
        controls=np.zeros(6) if controls is None else np.asarray(controls)
        times=np.unique(np.r_[np.linspace(0,1,count),[0,1/3,2/3,1]])
        basis=yaw_basis(times);seed=dict(self.start);rows=[]
        for s,B in zip(times,basis):
            yaw=float(B@controls);pose=object_pose(self.initial,offset,lift,float(s),yaw)
            seed=self.solve(pose,seed);pairs=self.distances(pose,seed,gradients)
            K,sigmas=self.differential(pose,seed)
            rows.append(dict(s=float(s),pose=pose.tolist(),yaw_rad=yaw,q=[seed[j] for j in self.names],
                             pairs=pairs,sigma_min=sigmas))
        return rows

    def check_path(self,rows,margin=.02,sigma_floor=.05,extra_margin=0.):
        failures=[];min_gap=float('inf');min_sigma=float('inf')
        for row in rows:
            state=dict(self.start,**dict(zip(self.names,row['q'])))
            clear=self.full_check(np.array(row['pose']),state)
            gap=min(v['clearance_m'] for v in row['pairs']);sigma=min(row['sigma_min'].values())
            min_gap=min(min_gap,gap);min_sigma=min(min_sigma,sigma)
            required=margin+extra_margin*np.sin(np.pi*row['s'])**2
            if not clear or gap<required-1e-8 or sigma<sigma_floor:
                failures.append(dict(s=row['s'],fcl_clear=clear,min_gap_m=gap,sigma_min=sigma))
        return dict(samples=len(rows),min_pair_gap_m=min_gap,min_scaled_sigma=min_sigma,
                    failures=failures,passed=not failures)

    def optimize_yaw(self,offset,lift,margin=.02,limit_deg=15.,count=121,maxiter=60,extra_margin=0.,constraint_buffer=.0005):
        """Whole-path deterministic SQP, analytic arm-pair distance Jacobians.

        Full-scene FCL and scaled singular values are acceptance checks, not
        differentiable optimizer constraints in this initial implementation.
        """
        cache={};history=[]
        def evaluate(x):
            key=np.asarray(x).tobytes()
            if cache.get('key')!=key:
                rows=self.path(offset,lift,x,count,gradients=True)
                B=yaw_basis(np.array([r['s'] for r in rows]))
                c=np.array([v['clearance_m']-margin-constraint_buffer-extra_margin*np.sin(np.pi*r['s'])**2 for r in rows for v in r['pairs']])
                jac=np.array([np.array(v['gradient'])[5]*B[k] for k,r in enumerate(rows) for v in r['pairs']])
                cache.update(key=key,rows=rows,c=c,jac=jac)
            return cache
        B=yaw_basis(np.linspace(0,1,121));D=np.diff(B,n=2,axis=0)
        H=(B.T@B)/len(B)+20*(D.T@D)
        def objective(x):return float(x@H@x)
        def callback(x):
            e=evaluate(x);history.append(dict(cost=objective(x),min_margin_m=float(e['c'].min()),max_control_deg=float(np.rad2deg(abs(x)).max())))
        try:
            result=minimize(objective,np.zeros(6),jac=lambda x:2*H@x,method='SLSQP',
                            bounds=[(-np.deg2rad(limit_deg),np.deg2rad(limit_deg))]*6,
                            constraints=[dict(type='ineq',fun=lambda x:evaluate(x)['c'],jac=lambda x:evaluate(x)['jac'])],
                            callback=callback,options=dict(maxiter=maxiter,ftol=1e-10))
            rows=self.path(offset,lift,result.x,241);check=self.check_path(rows,margin,extra_margin=extra_margin)
            return dict(controls=result.x.tolist(),solver_success=bool(result.success),solver_message=str(result.message),
                        iterations=int(result.nit),constraint_buffer_m=constraint_buffer,optimization_samples=count,
                        history=history,check=check),rows
        except (ValueError,np.linalg.LinAlgError) as error:
            return dict(solver_success=False,solver_message=str(error),history=history,check=dict(passed=False)),[]


def shared_trajectory(problem,offset,lift,controls,knots_per_phase=101):
    """Three C3 stop-to-stop phases, one progress law for all 24 joints."""
    from .smooth_paths import plan_segment
    if knots_per_phase<6:raise ValueError('Quintic interpolation needs at least six knots')
    controls=np.asarray(controls,float)
    if controls.shape!=(6,) or not np.isfinite(controls).all():raise ValueError('Six finite yaw controls required')
    phases=[];seed=dict(problem.start)
    for phase in range(3):
        knots=np.linspace(0,1,knots_per_phase);positions=[]
        for u in knots:
            s=(phase+u)/3;yaw=float(yaw_basis(s)@controls)
            pose=object_pose(problem.initial,offset,lift,s,yaw);seed=problem.solve(pose,seed)
            positions.append([seed[j] for j in problem.names])
        segment=dict(kind='OBJECT_DERIVED',knots=knots.tolist(),positions=positions,check={})
        segment=plan_segment(segment,velocity=.45,acceleration=.4,jerk=2.)
        segment['phase']=['LIFT','TRANSFER','LOWER'][phase];segment['global_progress']=[phase/3,(phase+1)/3]
        phases.append(segment)
    return dict(executable=False,phases=phases,duration_s=sum(p['time_law']['duration_s'] for p in phases),
                controls=list(controls),offset_m=list(offset),lift_m=lift,joint_names=problem.names,
                limits=dict(velocity_rad_s=.45,acceleration_rad_s2=.4,jerk_rad_s3=2.),
                timing='One shared C3 progress law per phase across all carrying joints; full stops between phases')


def trajectory_at(problem,trajectory,t):
    from .smooth_paths import sample_segment,progress
    elapsed=0.
    for index,segment in enumerate(trajectory['phases']):
        duration=segment['time_law']['duration_s']
        if t<=elapsed+duration or index==len(trajectory['phases'])-1:
            local=float(np.clip(t-elapsed,0,duration));u=float(progress(segment['time_law'],local)[0]);s=(index+u)/3
            yaw=float(yaw_basis(s)@trajectory['controls'])
            pose=object_pose(problem.initial,trajectory['offset_m'],trajectory['lift_m'],s,yaw)
            q=sample_segment(segment,local);v=sample_segment(segment,local,1)
            return dict(s=s,pose=pose,q=q,velocity=v,yaw_rad=yaw,phase=segment['phase'])
        elapsed+=duration


def validate_trajectory(problem,trajectory,*,dt=.01,margin=.02,extra_margin=0.,sigma_floor=.05):
    """Validate the actual shared interpolant, not just the IK knots."""
    from .common import PAIRS as NEIGHBOURS
    if not np.isfinite(dt) or dt<=0:raise ValueError('Positive finite validation timestep required')
    times=np.unique(np.r_[np.linspace(0,trajectory['duration_s'],int(np.ceil(trajectory['duration_s']/dt))+1),
                          np.cumsum([p['time_law']['duration_s'] for p in trajectory['phases']])])
    minimum=float('inf');sigma_min=float('inf');position_error=angle_error=0.;max_yaw=0.
    failures=[];reserves=0;minimum_requested_surplus=float('inf');previous=None;max_step=0.
    for t in times:
        row=trajectory_at(problem,trajectory,float(t));state=dict(problem.start,**dict(zip(problem.names,row['q'])))
        if previous is not None:max_step=max(max_step,float(np.max(abs(row['q']-previous))))
        previous=row['q'];pose=row['pose'];clear=problem.full_check(pose,state)
        pairs=problem.distances(pose,state);K,sigmas=problem.differential(pose,state)
        gap=min(v['clearance_m'] for v in pairs);sigma=min(sigmas.values());minimum=min(minimum,gap);sigma_min=min(sigma_min,sigma)
        pe=ae=0.
        for arm in problem.arms:
            actual=problem.problem.chains[arm].forward(state)@problem.tcp_offsets[arm];target=pose@problem.offsets[arm]
            pe=max(pe,float(np.linalg.norm(actual[:3,3]-target[:3,3])))
            ae=max(ae,float(np.linalg.norm(Rotation.from_matrix(actual[:3,:3]@target[:3,:3].T).as_rotvec())))
        position_error=max(position_error,pe);angle_error=max(angle_error,ae);max_yaw=max(max_yaw,abs(row['yaw_rad']))
        required=margin+extra_margin*np.sin(np.pi*row['s'])**2;minimum_requested_surplus=min(minimum_requested_surplus,gap-required)
        bounds_ok=all(problem.collision.bounds[name][0]<=state[name]<=problem.collision.bounds[name][1]
                      for name in problem.names)
        if not clear or not bounds_ok or gap<required-1e-8 or sigma<sigma_floor or pe>1e-6 or ae>1e-5:
            failures.append(dict(time_s=float(t),s=row['s'],fcl_clear=clear,gap_m=gap,required_m=required,
                                 joint_bounds_ok=bounds_ok,sigma_min=sigma,closure_m=pe,closure_rad=ae))
        p=problem.problem;budgets={}
        for arm in ROBOT_IDS:
            vel=np.zeros(len(p.names[arm]))
            if arm in problem.arms:
                i=problem.arms.index(arm);vel[:6]=row['velocity'][i*6:i*6+6]
            budgets[arm]=p.spheres.arm_budget(arm,vel,p.cfg['state_timeout_s'],p.cfg)[0]
        reserves+=any(v['clearance_m']<margin+budgets[v['arms'][0]]+budgets[v['arms'][1]]
                      for v in pairs if tuple(v['arms']) in NEIGHBOURS or tuple(v['arms'][::-1]) in NEIGHBOURS)
    return dict(passed=not failures,samples=len(times),max_time_step_s=float(np.max(np.diff(times))),
                min_pair_gap_m=minimum,min_requested_surplus_m=minimum_requested_surplus,min_scaled_sigma=sigma_min,
                max_closure_position_m=position_error,max_closure_angle_rad=angle_error,max_joint_step_rad=max_step,
                max_yaw_deg=float(np.rad2deg(max_yaw)),stop_reserve_conflict_samples=int(reserves),failures=failures,
                scope='Discrete full-scene/moving-object and all-pair checks; hypothetical open-gripper rigid grasp')

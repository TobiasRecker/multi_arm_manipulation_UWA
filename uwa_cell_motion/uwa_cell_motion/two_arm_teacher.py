"""Offline object-space teacher for a rigid two-arm grasp.

No ROS nodes or execution commands. Fixed short-side grasps, a single 12-joint
clock, all six arm pairs and the moving object remain in the collision scene.
Pair gradients are analytical; conservative object/environment box gradients
use finite differences. FCL, self collisions and conditioning are acceptance
checks, never inferred from optimizer termination.
"""
from copy import deepcopy
import itertools
import time

import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation

from .carton_paths import solve_near
from .common import ROBOT_IDS, joint_names
from .object_transport import ObjectTransport, skew, yaw_basis
from .smooth_paths import plan_segment, progress, sample_segment


def left_jacobian(vector):
    """SO(3) exponential differential expressed as a world-frame rotation."""
    vector=np.asarray(vector,float);theta=np.linalg.norm(vector);A=skew(vector)
    if theta<1e-6:
        return np.eye(3)+(0.5-theta**2/24)*A+(1/6-theta**2/120)*(A@A)
    return np.eye(3)+(1-np.cos(theta))/theta**2*A+(theta-np.sin(theta))/theta**3*(A@A)


def specification(name, excursion_m=(0,0,0), rotation_deg=(0,0,0),
                  goal_m=(0,0,0), goal_rotation_deg=(0,0,0)):
    result=dict(name=name,excursion_m=list(excursion_m),rotation_vector_deg=list(rotation_deg),
                goal_m=list(goal_m),goal_rotation_vector_deg=list(goal_rotation_deg))
    for key,value in result.items():
        if key!='name' and (np.asarray(value).shape!=(3,) or not np.isfinite(value).all()):
            raise ValueError('Expected finite 3D task vectors')
    return result


def pose_at(initial, task, s, controls):
    """World translation and world-axis rotation about the carton centre.

    Reference = linear goal + sin² excursion; corrections vanish at both ends.
    The specified endpoint orientation is therefore never optimized away.
    """
    controls=np.asarray(controls,float)
    if controls.shape!=(6,6) or not np.isfinite(controls).all() or not 0<=s<=1:
        raise ValueError('Expected six finite 6D spline controls and progress in [0,1]')
    h=np.sin(np.pi*s)**2;B=yaw_basis(s);correction=B@controls
    target=initial.copy()
    target[:3,3]+=s*np.array(task['goal_m'])+h*np.array(task['excursion_m'])+correction[:3]
    reference=np.deg2rad(s*np.array(task['goal_rotation_vector_deg'])+h*np.array(task['rotation_vector_deg']))
    target[:3,:3]=Rotation.from_rotvec(correction[3:]).as_matrix()@Rotation.from_rotvec(reference).as_matrix()@initial[:3,:3]
    return target


def box_separation(pose,half,env_pose,env_half):
    """SAT separation lower bound for two oriented solid boxes.

    Positive value proves a separating plane, negative means box overlap.
    This is not Euclidean mesh distance. Degenerate cross axes are excluded.
    """
    a=pose[:3,:3];b=env_pose[:3,:3]
    axes=np.vstack([a.T,b.T,np.cross(a.T[:,None,:],b.T[None,:,:]).reshape(-1,3)])
    lengths=np.linalg.norm(axes,axis=1);axes=axes[lengths>1e-8]/lengths[lengths>1e-8,None]
    gap=np.abs(axes@(pose[:3,3]-env_pose[:3,3]))-np.abs(axes@a)@half-np.abs(axes@b)@env_half
    return float(np.max(gap))


def point_box_distance(points,half):
    """Signed point/axis-aligned-box distance and outward normals in box frame."""
    points=np.asarray(points);q=np.abs(points)-half;outside=np.maximum(q,0)
    length=np.linalg.norm(outside,axis=1);distance=length+np.minimum(q.max(axis=1),0)
    normal=np.sign(points)*outside/np.maximum(length[:,None],1e-15)
    inside=length<1e-12
    for i in np.flatnonzero(inside):
        axis=int(np.argmax(q[i]));normal[i]=0;normal[i,axis]=1 if points[i,axis]>=0 else -1
    return distance,normal


class TwoArmTeacher(ObjectTransport):
    def __init__(self,directory,source,*,elevation=.08):
        if not np.isfinite(elevation) or not .02<=elevation<=.2:
            raise ValueError('Offline initial elevation must be in [0.02,0.2] m')
        super().__init__(directory,source,arms=('right_front','right_rear'))
        short_axis=int(np.argmax(self.dimensions[:2]));axis='xy'[short_axis]
        self.grasp_sides={arm:axis+suffix for arm,suffix in zip(self.arms,('_min','_max'))}
        # Transfer the fixed side-centre task to the two right arms. Tool/TCP
        # transforms are individual; do not copy another arm's joint angles.
        for arm,side in self.grasp_sides.items():
            old=next(v for v in self.saved['task']['targets'].values() if v['side_name']==side)
            tcp=np.array(old['tool0_target'])@np.array(old['tool0_to_tcp'])
            target=tcp@np.linalg.inv(self.tcp_offsets[arm]);names=joint_names(arm)
            q=solve_near(self.problem,arm,self.start,target,np.array([self.start[j] for j in names]))
            self.start.update(zip(names,q))
            self.offsets[arm]=np.linalg.inv(self.initial)@tcp
            self.offsets[arm].setflags(write=False)
        self.start=self.solve(self.initial,self.start)
        self.source_initial=self.initial.copy()
        # Establish a reproducible hypothetical in-air initial configuration.
        # These IK continuation steps are not a validated pickup trajectory.
        seed=dict(self.start)
        for z in np.linspace(0,elevation,int(np.ceil(elevation/.005))+1):
            pose=self.source_initial.copy();pose[2,3]+=z;seed=self.solve(pose,seed)
        self.initial=pose;self.start=seed;self.elevation=elevation
        if not self.full_check(self.initial,self.start):raise ValueError('Initial two-arm state collides')
        if min(v['clearance_m'] for v in self.distances(self.initial,self.start))<.02:
            raise ValueError('Initial two-arm state violates 20 mm arm margin')
        self.environment_boxes=[];frames=self.problem.spheres.geometry.fk.frames(self.start)
        for body in self.problem.spheres.environment:
            if body.link=='offline_carton':continue
            lo=body.visual_vertices.min(axis=0);hi=body.visual_vertices.max(axis=0)
            T=frames[body.link]@body.fixed;T=T.copy();T[:3,3]+=T[:3,:3]@((lo+hi)/2)
            self.environment_boxes.append((body.link,T,(hi-lo)/2))

    def environment_gaps(self,pose,gradients=False):
        values=np.array([box_separation(pose,self.dimensions/2,T,h) for _,T,h in self.environment_boxes])
        if not gradients:return values
        J=np.empty((len(values),6));eps=1e-6
        for axis in range(6):
            both=[]
            for sign in [-1,1]:
                X=pose.copy()
                if axis<3:X[axis,3]+=sign*eps
                else:
                    r=np.zeros(3);r[axis-3]=sign*eps
                    X[:3,:3]=Rotation.from_rotvec(r).as_matrix()@X[:3,:3]
                both.append(self.environment_gaps(X))
            J[:,axis]=(both[1]-both[0])/(2*eps)
        return values,J

    def object_arm_gaps(self,pose,state,gradients=False):
        """Carton solid box versus arm-body spheres, including parked arms.

        Gripper/finger and wrist3 bodies rigidly attached to the carrying TCP
        are omitted from this steering surrogate only. Full FCL has no added
        object/tool exemptions. Forearm/carton collisions remain optimizable.
        """
        model=self.problem.spheres
        if gradients:world,jac=model.jacobians(state,self.arms);K,_=self.differential(pose,state)
        else:world=model.world(state)
        values=[];J=[]
        for arm in ROBOT_IDS:
            mask=np.array([not ('_robotiq_' in link or '_wrist_camera_' in link or link.endswith('_wrist_3_link'))
                           for link in model.links[arm]])
            indices=np.flatnonzero(mask);points=world[arm][mask]
            local=(points-pose[:3,3])@pose[:3,:3]
            distance,normal=point_box_distance(local,self.dimensions/2)
            gaps=distance-model.radii[arm][mask];i=int(np.argmin(gaps));values.append(gaps[i])
            if gradients:
                n=pose[:3,:3]@normal[i];A=np.c_[np.eye(3),-skew(points[i]-pose[:3,3])]
                J.append(n@(jac[arm][indices[i]]@K-A))
        return (np.array(values),np.array(J)) if gradients else np.array(values)

    def path_rows(self,task,controls=None,*,count=81,gradients=False):
        controls=np.zeros((6,6)) if controls is None else np.asarray(controls)
        seed=dict(self.start);rows=[]
        for s in np.linspace(0,1,count):
            pose=pose_at(self.initial,task,float(s),controls);seed=self.solve(pose,seed)
            pairs=self.distances(pose,seed,gradients);K,sigmas=self.differential(pose,seed)
            row=dict(s=float(s),pose=pose.tolist(),q=[seed[j] for j in self.names],pairs=pairs,
                     sigma_min=sigmas,environment_gaps_m=self.environment_gaps(pose).tolist(),
                     object_arm_gaps_m=self.object_arm_gaps(pose,seed).tolist())
            if gradients:
                row['K']=K;row['environment_gradient']=self.environment_gaps(pose,True)[1]
                row['object_arm_gradient']=self.object_arm_gaps(pose,seed,True)[1]
            rows.append(row)
        return rows

    def constraints(self,rows,controls,*,margin=.02,object_margin=.003,buffer=.001):
        """Normalized inequality residuals and Jacobians wrt flattened SI controls."""
        values=[];derivatives=[]
        bounds=np.array([self.collision.bounds[n] for n in self.names])
        for row in rows:
            B=yaw_basis(row['s']);G=np.zeros((6,36));C=np.eye(6)
            C[3:,3:]=left_jacobian((B@controls)[3:])
            for k,b in enumerate(B):G[:,k*6:k*6+6]=b*C
            gaps=np.array([r['clearance_m'] for r in row['pairs']])
            gapJ=np.array([r['gradient'] for r in row['pairs']])@G
            values.extend((gaps-margin-buffer)/.05);derivatives.extend(gapJ/.05)
            values.extend((np.array(row['environment_gaps_m'])-object_margin-buffer)/.05)
            derivatives.extend(row['environment_gradient']@G/.05)
            values.extend((np.array(row['object_arm_gaps_m'])-object_margin-buffer)/.05)
            derivatives.extend(row['object_arm_gradient']@G/.05)
            q=np.array(row['q']);qJ=row['K']@G
            values.extend(q-bounds[:,0]-.001);derivatives.extend(qJ)
            values.extend(bounds[:,1]-q-.001);derivatives.extend(-qJ)
        return np.asarray(values),np.asarray(derivatives)

    def optimize(self,task,*,count=81,maxiter=50,translation_limit=.12,rotation_limit_deg=35.,initial_controls=None):
        """Trust-region sequential QPs with elastic feasibility and line search.

        Candidate IK failures reject a trial, not the entire search. No global
        completeness or optimality claim; a failed reference IK is recorded.
        """
        if not np.isfinite([translation_limit,rotation_limit_deg]).all() or min(translation_limit,rotation_limit_deg)<=0 or count<7 or maxiter<1:
            raise ValueError('Positive limits, at least seven samples and one iteration required')
        begun=time.monotonic();scale=np.tile([translation_limit]*3+[np.deg2rad(rotation_limit_deg)]*3,6)
        x=np.zeros(36) if initial_controls is None else np.asarray(initial_controls).reshape(36)/scale
        if not np.isfinite(x).all() or np.max(abs(x))>1+1e-9:raise ValueError('Initial controls outside envelope')
        history=[];trust=.2
        B=yaw_basis(np.linspace(0,1,121));D=np.diff(B,n=2,axis=0)
        H=np.kron(B.T@B/len(B)+20*D.T@D,np.eye(6))+.0001*np.eye(36)
        cost=lambda x:float(x@H@x)
        def evaluate(x):
            controls=(x*scale).reshape(6,6);rows=self.path_rows(task,controls,count=count,gradients=True)
            c,J=self.constraints(rows,controls)
            return rows,c,J*scale[None,:]
        try:rows,c,J=evaluate(x)
        except (ValueError,np.linalg.LinAlgError) as error:
            return dict(success=False,status='REFERENCE_IK_FAILED',reason=str(error),history=[],elapsed_s=time.monotonic()-begun)
        # Feasible references are preserved; full FCL can still reject them.
        if c.min()>=-1e-7 and np.max(abs(x))<1e-12:
            return dict(success=True,status='REFERENCE_CONSTRAINTS_CLEAR',controls=(x*scale).reshape(6,6).tolist(),
                        history=[],elapsed_s=time.monotonic()-begun,limits=dict(translation_m=translation_limit,rotation_deg=rotation_limit_deg))
        # Bounded deterministic feasibility seeds: modest lifting and reducing
        # the requested intermediate rotation. Endpoints remain untouched.
        # Preserve all diagnostics; these are not proofs of global feasibility.
        seed_checks=[]
        if initial_controls is None:
            choices=[]
            counter=np.clip(-np.array(task['rotation_vector_deg']),-rotation_limit_deg,rotation_limit_deg)
            for lift,rotation_fraction in [(0,1),(.04,0),(.04,1),(.08,0),(.08,1)]:
                guess=np.zeros((6,6));guess[:,2]=min(lift,translation_limit);guess[:,3:]=np.deg2rad(counter)*rotation_fraction
                candidate=guess.ravel()/scale
                try:
                    rr,cc,jj=evaluate(candidate)
                    seed_checks.append(dict(lift_m=float(guess[0,2]),rotation_fraction=rotation_fraction,
                                            minimum_constraint=float(cc.min()),cost=cost(candidate)))
                    if cc.min()>=-1e-7:choices.append((cost(candidate),candidate,rr,cc,jj))
                except (ValueError,np.linalg.LinAlgError) as error:
                    seed_checks.append(dict(lift_m=lift,rotation_fraction=rotation_fraction,reason=str(error)))
            if choices:
                _,x,rows,c,J=min(choices,key=lambda item:item[0])
        initial_cost=cost(x)
        best=(x.copy(),rows,c.copy(),J.copy()) if c.min()>=-1e-7 else None
        status='ITERATION_LIMIT'
        for iteration in range(maxiter):
            base=x.copy();penalty=200.
            A=np.c_[J,np.ones(len(c))]
            def objective(z):return cost(z[:36])+penalty*z[-1]+1e-5*z[-1]**2
            def derivative(z):return np.r_[2*H@z[:36],penalty+2e-5*z[-1]]
            solution=minimize(objective,np.r_[x,max(0.,-c.min())+1e-6],jac=derivative,method='SLSQP',
                bounds=list(zip(np.maximum(-1,x-trust),np.minimum(1,x+trust)))+[(0,None)],
                constraints=[dict(type='ineq',fun=lambda z:c+J@(z[:36]-base)+z[-1],jac=lambda z:A)],
                options=dict(maxiter=120,ftol=1e-9))
            delta=solution.x[:36]-x;accepted=False
            merit=cost(x)+penalty*max(0.,-c.min())
            for alpha in [1.,.5,.25,.125,.0625]:
                trial=x+alpha*delta
                try:newrows,newc,newJ=evaluate(trial)
                except (ValueError,np.linalg.LinAlgError):continue
                newmerit=cost(trial)+penalty*max(0.,-newc.min())
                if newmerit<merit-1e-8:
                    x,rows,c,J=trial,newrows,newc,newJ;accepted=True;break
            history.append(dict(iteration=iteration,cost=cost(x),minimum_constraint=float(c.min()),
                                accepted=accepted,trust=trust,qp_success=bool(solution.success)))
            if c.min()>=-1e-7 and (best is None or cost(x)<cost(best[0])):
                best=(x.copy(),rows,c.copy(),J.copy())
            if not accepted:
                trust*=.5
                if trust<.003:
                    status='CONVERGED_FEASIBLE' if c.min()>=-1e-6 else 'STALLED_INFEASIBLE';break
            elif np.max(abs(alpha*delta))<1e-4 and c.min()>=-1e-6:
                status='CONVERGED_FEASIBLE';break
            elif alpha==1.:
                trust=min(.2,trust*1.3)
        if best is not None and c.min()<-1e-7:
            x,rows,c,J=best;status='BEST_FEASIBLE_ITERATE'
        return dict(success=bool(c.min()>=-1e-6),status=status,controls=(x*scale).reshape(6,6).tolist(),
                    history=history,elapsed_s=time.monotonic()-begun,
                    limits=dict(translation_m=translation_limit,rotation_deg=rotation_limit_deg),
                    minimum_constraint=float(c.min()),optimization_samples=count,seed_checks=seed_checks,
                    initial_cost=initial_cost,final_cost=cost(x))

    def trajectory(self,task,controls,*,knots=201):
        rows=self.path_rows(task,controls,count=knots)
        segment=plan_segment(dict(kind='OBJECT_DERIVED',knots=[r['s'] for r in rows],
                                  positions=[r['q'] for r in rows],check={}))
        return dict(task=deepcopy(task),controls=np.asarray(controls).tolist(),segment=segment,
                    duration_s=segment['time_law']['duration_s'],joint_names=self.names,executable=False)

    def sample(self,trajectory,t):
        segment=trajectory['segment'];s=float(progress(segment['time_law'],t)[0])
        pose=pose_at(self.initial,trajectory['task'],s,trajectory['controls'])
        q=sample_segment(segment,t);state=dict(self.start,**dict(zip(self.names,q)))
        return pose,state,s

    def validate(self,trajectory,*,dt=.005,margin=.02,object_margin=.003,sigma_floor=.05):
        if not np.isfinite(dt) or not 0<dt<=.01:raise ValueError('Validation dt must be in (0,.01]')
        failures=[];closure=angle=0.;gap=objectgap=objectarmgap=sigma=float('inf');max_step=0.;previous=None
        times=np.linspace(0,trajectory['duration_s'],int(np.ceil(trajectory['duration_s']/dt))+1)
        peak=np.zeros(3);deviation=np.zeros(2);inactive=[r for r in ROBOT_IDS if r not in self.arms]
        for t in times:
            pose,state,s=self.sample(trajectory,float(t));pairs=self.distances(pose,state);_,singular=self.differential(pose,state)
            localgap=min(p['clearance_m'] for p in pairs);localobj=float(self.environment_gaps(pose).min());localsigma=min(singular.values())
            localarm=float(self.object_arm_gaps(pose,state).min())
            pe=ae=0.
            for arm in self.arms:
                actual=self.problem.chains[arm].forward(state)@self.tcp_offsets[arm];target=pose@self.offsets[arm]
                pe=max(pe,float(np.linalg.norm(actual[:3,3]-target[:3,3])))
                ae=max(ae,float(Rotation.from_matrix(actual[:3,:3]@target[:3,:3].T).magnitude()))
            q=np.array([state[n] for n in self.names])
            if previous is not None:max_step=max(max_step,float(np.max(abs(q-previous))))
            previous=q
            clear=self.full_check(pose,state)
            bounds_ok=all(self.collision.bounds[n][0]<=state[n]<=self.collision.bounds[n][1] for n in self.names)
            for arm in inactive:
                if any(state[n]!=self.start[n] for n in joint_names(arm)):raise AssertionError('Stationary arm moved')
            if not clear or not bounds_ok or localgap<margin-1e-8 or localobj<object_margin-1e-8 or localarm<object_margin-1e-8 or localsigma<sigma_floor or pe>1e-6 or ae>1e-5:
                failures.append(dict(time_s=float(t),s=s,fcl_clear=clear,pair_gap_m=localgap,object_box_gap_m=localobj,
                                     object_arm_gap_m=localarm,sigma=localsigma,closure_m=pe,closure_rad=ae,bounds_ok=bounds_ok))
            gap=min(gap,localgap);objectgap=min(objectgap,localobj);sigma=min(sigma,localsigma);closure=max(closure,pe);angle=max(angle,ae)
            objectarmgap=min(objectarmgap,localarm)
            d=yaw_basis(s)@np.array(trajectory['controls']);deviation=np.maximum(deviation,[np.linalg.norm(d[:3]),np.linalg.norm(d[3:])])
        for derivative in range(1,4):
            peak[derivative-1]=float(np.max(abs(sample_segment(trajectory['segment'],times,derivative))))
        bounds=trajectory['segment']['smooth_bounds'];caps=np.array([.45,.4,2.])
        if np.any(peak>caps+1e-7) or np.any(np.array(list(bounds.values()))>caps+1e-7):
            failures.append(dict(reason='joint derivative limit exceeded'))
        return dict(passed=not failures,samples=len(times),max_time_step_s=float(np.max(np.diff(times))),
                    min_pair_gap_m=gap,min_object_box_gap_m=objectgap,min_object_arm_gap_m=objectarmgap,min_scaled_sigma=sigma,
                    max_closure_position_m=closure,max_closure_angle_rad=angle,max_joint_step_rad=max_step,
                    max_position_deviation_m=float(deviation[0]),max_orientation_deviation_deg=float(np.rad2deg(deviation[1])),
                    sampled_derivative_peaks=peak.tolist(),bounds=bounds,failures=failures,
                    scope='Discrete FCL/moving carton, all six arm pairs, conservative carton/environment boxes; no contact physics or stopping-reserve qualification')

    def inspect(self,task,controls=None,count=121):
        try:
            rows=self.path_rows(task,controls,count=count)
        except (ValueError,np.linalg.LinAlgError) as error:
            return dict(complete=False,reason=str(error),passed=False)
        failures=[]
        for row in rows:
            state=dict(self.start,**dict(zip(self.names,row['q'])))
            fcl=self.full_check(np.array(row['pose']),state);gap=min(p['clearance_m'] for p in row['pairs'])
            if not fcl or gap<.02 or min(row['environment_gaps_m'])<.003 or min(row['object_arm_gaps_m'])<.003 or min(row['sigma_min'].values())<.05:
                failures.append(dict(s=row['s'],fcl_clear=fcl,pair_gap_m=gap,
                                     object_box_gap_m=min(row['environment_gaps_m']),object_arm_gap_m=min(row['object_arm_gaps_m']),sigma=min(row['sigma_min'].values())))
        return dict(complete=True,passed=not failures,samples=len(rows),failures=failures,
                    fcl_collision_samples=sum(not x['fcl_clear'] for x in failures),
                    pair_margin_failure_samples=sum(x['pair_gap_m']<.02 for x in failures),
                    min_pair_gap_m=min(p['clearance_m'] for r in rows for p in r['pairs']),
                    min_object_box_gap_m=min(min(r['environment_gaps_m']) for r in rows),
                    min_object_arm_gap_m=min(min(r['object_arm_gaps_m']) for r in rows))

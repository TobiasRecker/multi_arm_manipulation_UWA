"""Nonparametric single-UR CDF and reactive QP rollout.

Reimplements Li et al., RSS2024, algorithms1/eqs5,6,8,14. Reference:
https://github.com/yimingli1998/cdf (08a725718e748366c5b4da5cbc4c67e991961f0f).
Differences: UR6, conservative sphere/box SDF, bounded SciPy L-BFGS-B,
scene-conditioned contact templates rather than Franka neural weights, an exact
box-constrained diagonal QP dual solve, and full-cell validation of every edge.
No RRT guidance, fallback, neural network or hardware command path.
"""
import json
from pathlib import Path
import time
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from .common import dump,sha
from .cdf_geometry import FrozenScene


class ContactBank:
    def __init__(self,contacts,depth,metadata):
        self.contacts=np.asarray(contacts,float);self.depth=np.asarray(depth,int);self.metadata=metadata
        if self.contacts.ndim!=2 or self.contacts.shape[1]!=6 or not len(self.contacts) or self.depth.shape!=(len(self.contacts),):raise ValueError('Empty or malformed CDF contact bank')
        if not np.isfinite(self.contacts).all() or not np.all((self.depth>=1)&(self.depth<=6)):raise ValueError('Invalid contact samples/prefixes')
        self.groups={k:(np.flatnonzero(self.depth==k),cKDTree(self.contacts[self.depth==k,:k])) for k in np.unique(self.depth)}
        self.digest=sha(json.dumps(dict(contacts=self.contacts.tolist(),depth=self.depth.tolist(),metadata=metadata),sort_keys=True))

    def query(self,q):
        """Unsigned sampled CDF [rad], gradient, nearest template (eqs5/6).

        Finite exact contacts overestimate the true minimum; contact residuals
        and geometry approximation can err either way. Never a clearance proof.
        """
        q=np.asarray(q,float)
        if q.shape!=(6,) or not np.isfinite(q).all():raise ValueError('CDF query requires finite six-joint state')
        best=(float('inf'),None,None)
        for k,(indices,tree) in self.groups.items():
            d,i=tree.query(q[:k])
            if d<best[0]:best=(float(d),int(indices[i]),k)
        distance,index,k=best;gradient=np.zeros(6)
        if distance>1e-12:gradient[:k]=(q[:k]-self.contacts[index,:k])/distance
        return distance,gradient,index

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('wb') as stream:np.savez_compressed(stream,contacts=self.contacts,depth=self.depth,metadata=json.dumps(self.metadata),digest=self.digest)

    @classmethod
    def load(cls,path,scene):
        with np.load(path,allow_pickle=False) as data:
            bank=cls(data['contacts'],data['depth'],json.loads(str(data['metadata'])))
            if bank.digest!=str(data['digest']):raise ValueError('CDF bank checksum differs')
        if bank.metadata.get('scene_binding')!=scene.binding:raise ValueError('CDF model/frozen obstacle state changed; rebuild contact bank')
        if np.any(bank.contacts<scene.bounds[:,0]-1e-8) or np.any(bank.contacts>scene.bounds[:,1]+1e-8):raise ValueError('CDF contacts outside joint limits')
        return bank


def build_bank(scene,request,*,samples=2048,seed=0,budget_s=120.,batch_size=64,iterations=80,epsilon_m=.001,progress=None):
    """Scene-level variant of paper algorithm1/2D online_computation.

    L-BFGS minimizes sum SDF(q)^2 from multiple bounded initial states. Store
    only converged zero-level states with their contact link prefix. Half the
    seeds cover joint limits; half cover the requested corridor. No paths or
    RRT solutions are used to generate samples. Preparation time is separate
    from online planning time and always reported.
    """
    if samples<8 or batch_size<1 or budget_s<=0 or iterations<1 or epsilon_m<=0:raise ValueError('Invalid CDF data-generation bounds')
    started=time.monotonic();deadline=started+budget_s;rng=np.random.default_rng(seed)
    bounds=scene.bounds;q0=np.array([request['start'][j] for j in request['joint_names']]);target=np.array(request['target'])
    seeds=rng.uniform(bounds[:,0],bounds[:,1],(samples,6));half=samples//2
    seeds[:half]=q0+rng.uniform(0,1,(half,1))*(target-q0)+rng.normal(0,1,(half,6))*rng.choice([.15,.4,.9,1.5],(half,1))
    seeds=np.clip(seeds,bounds[:,0],bounds[:,1]);contacts=[];depths=[];residuals=[];attempted=0;timed_out=False
    class Deadline(Exception):pass
    for offset in range(0,samples,batch_size):
        initial=seeds[offset:offset+batch_size];B=len(initial)
        def cost(x):
            if time.monotonic()>=deadline:raise Deadline()
            d,g,_=scene.sdf(x.reshape(B,6));return float(np.sum(d*d)),(2*d[:,None]*g).ravel()
        try:
            fit=minimize(cost,initial.ravel(),method='L-BFGS-B',jac=True,bounds=np.tile(bounds,(B,1)),
                options=dict(maxiter=iterations,ftol=1e-14,gtol=1e-7,maxls=20))
        except Deadline:timed_out=True;break
        q=fit.x.reshape(B,6);d,_,k=scene.sdf(q);mask=abs(d)<=epsilon_m
        contacts.extend(q[mask]);depths.extend(k[mask]);residuals.extend(abs(d[mask]));attempted+=B
        if progress:progress(attempted,len(contacts),time.monotonic()-started)
    if not contacts:raise ValueError('No zero-level contact templates found within preparation budget')
    metadata=dict(schema_version=1,scene_binding=scene.binding,arm=scene.arm,seed=seed,requested_samples=samples,attempted_samples=attempted,
        contacts=len(contacts),preparation_time_s=time.monotonic()-started,preparation_budget_s=budget_s,timed_out=timed_out,
        max_contact_residual_m=float(max(residuals)),contact_tolerance_m=epsilon_m,algorithm='bounded_multistart_L-BFGS-B_scene_zero_level_prefix_CDF',
        reference_commit='08a725718e748366c5b4da5cbc4c67e991961f0f',
        approximation='finite scene-conditioned templates, conservative sphere/box SDF; no neural model, no global completeness/clearance guarantee')
    return ContactBank(contacts,depths,metadata)


def qp_step(q,target,gradient,distance,bounds,*,max_step=.04,gamma=.9):
    """Eliminate X/u from paper eq14: optimize bounded joint increment.

    -grad(CDF) delta <= log(CDF+gamma). gamma<1 gives a radian-distance
    buffer. This is the paper's logarithmic condition, not a meter potential.
    """
    q,target,gradient=np.asarray(q,float),np.asarray(target,float),np.asarray(gradient,float)
    bounds=np.asarray(bounds,float)
    if any(a.shape!=(6,) for a in (q,target,gradient)) or bounds.shape!=(6,2):raise ValueError('Invalid CDF QP dimensions')
    if not 0<gamma<1 or max_step<=0 or distance<0 or not np.isfinite(np.r_[q,target,gradient,distance,gamma,max_step,bounds.ravel()]).all():raise ValueError('Invalid CDF QP inputs')
    lower=np.maximum(bounds[:,0]-q,-max_step);upper=np.minimum(bounds[:,1]-q,max_step)
    if np.any(lower>upper):return None,'QP_INFEASIBLE: initial state outside limits'
    limit=float(np.log(distance+gamma));weights=np.array([150.,190.,80.,70.,70.,90.]);hessian=weights+.01
    desired=weights/hessian*(target-q);initial=np.clip(desired,lower,upper);required=-limit
    if gradient@initial>=required-1e-12:return initial,None
    maximum=gradient@np.where(gradient>=0,upper,lower)
    if maximum<required-1e-10:return None,'QP_INFEASIBLE: logarithmic constraint exceeds bounded joint increment'
    # One linear inequality + diagonal positive quadratic + box bounds:
    # KKT gives delta(lambda)=clip(desired+lambda*g/H). Its constraint value
    # is monotonic, so a scalar dual bisection solves this convex QP without
    # line-search false failures from a generic nonlinear optimizer.
    def candidate(multiplier):return np.clip(desired+multiplier*gradient/hessian,lower,upper)
    lo,hi=0.,1.
    for _ in range(80):
        if gradient@candidate(hi)>=required-1e-12:break
        hi*=2
    else:return None,'QP_NUMERICAL_FAILURE: dual bracket'
    for _ in range(70):
        middle=(lo+hi)/2
        if gradient@candidate(middle)>=required:hi=middle
        else:lo=middle
    result=candidate(hi)
    if gradient@result<required-1e-9:return None,'QP_NUMERICAL_FAILURE: constraint residual'
    return result,None


def rollout(problem,request,scene,bank,budget_s,*,gamma=.9,max_step=.04,max_steps=800):
    """Single paper-style reactive QP rollout; every edge is fully checked."""
    deadline=time.monotonic()+budget_s;q=np.array([request['start'][j] for j in request['joint_names']]);target=np.array(request['target'])
    path=[q.tolist()];trace=[]
    for step in range(max_steps):
        if time.monotonic()>=deadline:return None,'TIMEOUT',trace
        if np.max(abs(target-q))<=problem.cfg['goal_tolerance_rad']:
            if problem.edge(request,q,target,deadline=deadline):return path+[target.tolist()],None,trace
        sdf,_,_=scene.sdf(q)
        if sdf[0]<=0:return None,'STEERING_GEOMETRY_IN_COLLISION',trace
        distance,gradient,index=bank.query(q)
        delta,error=qp_step(q,target,gradient,distance,scene.bounds,max_step=max_step,gamma=gamma)
        trace.append(dict(step=step,cdf_rad=distance,sdf_m=float(sdf[0]),gradient=gradient.tolist(),template=index))
        if error:return None,error,trace
        weights=np.array([150.,190.,80.,70.,70.,90.])
        unconstrained=np.clip(weights/(weights+.01)*(target-q),np.maximum(scene.bounds[:,0]-q,-max_step),np.minimum(scene.bounds[:,1]-q,max_step))
        trace[-1].update(avoidance_constraint_changed_step=bool(np.linalg.norm(delta-unconstrained)>1e-6),
            constraint_slack=float(np.log(distance+gamma)+np.dot(gradient,delta)))
        if np.max(abs(delta))<1e-6:return None,'STUCK: CDF QP stationary',trace
        accepted=False
        for scale in (1.,.5,.25,.125):
            candidate=q+scale*delta
            if scene.sdf(candidate)[0][0]>0 and problem.edge(request,q,candidate,deadline=deadline):accepted=True;break
        if not accepted:return None,'TIMEOUT' if time.monotonic()>=deadline else 'STUCK: full-cell validation blocked CDF step',trace
        q=candidate;path.append(q.tolist())
        if len(path)>30 and np.linalg.norm(np.asarray(path[-1])-path[-20])<1e-4:return None,'STUCK: CDF QP cycle',trace
    return None,'STEP_LIMIT',trace


def plan(problem,request,bank,*,seed=None,gamma=.9,max_step=.04):
    if getattr(problem,'inventory',None) is not None:raise ValueError('CDF prototype is offline/simulation only; hardware not supported')
    if not np.isfinite([gamma,max_step]).all() or not 0<gamma<1 or max_step<=0:raise ValueError('Invalid CDF QP settings')
    seed=bank.metadata.get('seed',0) if seed is None else seed
    request=problem.normalize(request);scene=FrozenScene(problem,request)
    if bank.metadata.get('scene_binding')!=scene.binding:raise ValueError('CDF bank differs from frozen scene/model')
    began=time.monotonic();deadline=began+problem.cfg['planning_budget_s']
    q0=np.array([request['start'][j] for j in request['joint_names']]);target=np.array(request['target'])
    result=dict(schema_version=1,method='cdf',seed=seed,request=request,config=problem.cfg,model_signature=problem.signature,
        mesh_sha256=problem.spheres.geometry.assets,layout_path=str(problem.layout_path) if problem.layout_path else None,
        success=False,simulation_only=True,cdf_bank_sha256=bank.digest,cdf=bank.metadata,
        cdf_settings=dict(gamma=gamma,max_joint_increment_rad=max_step),frozen_arms=[r for r in problem.names if r!=scene.arm])
    if not problem.check(request,q0):result['error']='INVALID_START'
    elif not problem.check(request,target):result['error']='INVALID_GOAL'
    elif scene.sdf(q0)[0][0]<=0 or scene.sdf(target)[0][0]<=0:result['error']='CONSERVATIVE_STEERING_START_OR_GOAL_BLOCKED'
    else:
        direct=problem.edge(request,q0,target,deadline=deadline);result['direct_connection']=direct
        if direct:path,error,trace=[q0.tolist(),target.tolist()],None,[]
        else:path,error,trace=rollout(problem,request,scene,bank,max(0,deadline-time.monotonic()),gamma=gamma,max_step=max_step)
        result.update(coordination='single_arm_direct' if direct else 'cdf_qp_rollout',cdf_trace=trace,planning_time_s=time.monotonic()-began)
        if error:result['error']=error
        else:
            try:
                trajectory=problem.time_parameterize(request,path)
                result.update(success=True,trajectory=trajectory,metrics=problem.metrics(request,trajectory))
                result['metrics']['cdf_constrained_steps']=sum(t.get('avoidance_constraint_changed_step',False) for t in trace)
            except ValueError as error:result['error']='VALIDATION: '+str(error)
    result.setdefault('planning_time_s',time.monotonic()-began);result['total_offline_time_s']=time.monotonic()-began
    return result

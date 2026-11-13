"""Common offline PTP request, independent planners and identical final checks."""
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from uwa_cell_control.parallel_scan import collision_signature
from uwa_cell_gazebo.charuco_views import Chain
from .common import ROBOT_IDS, PAIRS, all_names, joint_names, dump, model_context
from .geometry import SphereModel


class Problem:
    def __init__(self,directory,cfg,layout_path=None):
        self.directory=Path(directory);self.cfg=cfg;self.layout_path=layout_path
        self.layout,self.description,self.collision=model_context(self.directory,layout_path)
        self.names=all_names(self.layout)
        self.spheres=SphereModel(self.description,self.names,cfg['sphere_spacing_m'])
        self.signature=collision_signature(self.description)

    def normalize(self,request):
        if request.get('schema_version',1)!=1:raise ValueError('Unsupported motion request schema')
        start={str(k):float(v) for k,v in request['start'].items()}
        required={j for n in self.names.values() for j in n}
        if not required<=start.keys() or not np.isfinite(list(start.values())).all():
            raise ValueError('Complete finite start state, including gripper driving joints, required')
        goals=request['goals']
        if not goals or set(goals)-set(ROBOT_IDS):raise ValueError('Expected goals for one or more known arms')
        selected=[r for r in ROBOT_IDS if r in goals]
        names=[j for rid in selected for j in joint_names(rid)]
        target=dict(start)
        for rid in selected:
            goal=goals[rid]
            if isinstance(goal,list):q=np.asarray(goal,float)
            elif 'positions' in goal:q=np.asarray(goal['positions'],float)
            else:q=self.ik(rid,start,goal)
            if q.shape!=(6,) or not np.isfinite(q).all():raise ValueError('Goal must contain six finite radians')
            target.update(zip(joint_names(rid),q))
        return dict(schema_version=1,start=start,goals={rid:[target[j] for j in joint_names(rid)] for rid in selected},
                    selected=selected,joint_names=names,target=[target[j] for j in names])

    def ik(self,rid,start,goal):
        if goal.get('frame_id')!='world' or not goal.get('target_link'):
            raise ValueError('Cartesian goal requires frame_id=world and explicit target_link')
        if not goal['target_link'].startswith(rid+'_'):raise ValueError('Cartesian target link belongs to a different arm')
        pose=goal['pose']; xyz=np.asarray(pose['position'],float);quat=np.asarray(pose['orientation_xyzw'],float)
        if xyz.shape!=(3,) or quat.shape!=(4,) or not np.isfinite(np.r_[xyz,quat]).all() or abs(np.linalg.norm(quat)-1)>1e-5:
            raise ValueError('Finite Cartesian position and unit XYZW quaternion required')
        desired=Rotation.from_quat(quat).as_matrix()
        chain=Chain(self.description,'world',goal['target_link']);names=joint_names(rid)
        bounds=np.asarray([self.collision.bounds[j] for j in names]).T
        def residual(q):
            actual=chain.forward(dict(start,**dict(zip(names,q))))
            return np.r_[actual[:3,3]-xyz,Rotation.from_matrix(actual[:3,:3]@desired.T).as_rotvec()]
        rng=np.random.default_rng(64);initial=np.asarray([start[j] for j in names]);solutions=[]
        for seed in [initial]+[rng.uniform(bounds[0],bounds[1]) for _ in range(7)]:
            fit=least_squares(residual,np.clip(seed,bounds[0]+1e-8,bounds[1]-1e-8),bounds=bounds,max_nfev=150)
            if np.linalg.norm(residual(fit.x))<1e-4:solutions.append(fit.x)
        if not solutions:raise ValueError('Cartesian goal IK failed')
        return min(solutions,key=lambda q:np.linalg.norm(q-initial))

    def state(self,request,q):return dict(request['start'],**dict(zip(request['joint_names'],q)))

    def thresholds(self):
        velocities={r:np.zeros(len(n)) for r,n in self.names.items()}
        budgets={r:self.spheres.arm_budget(r,velocities[r],self.cfg['state_timeout_s'],self.cfg)[0] for r in self.names}
        return [dict(arms=[a,b],threshold_m=self.cfg['model_margin_m']+budgets[a]+budgets[b]) for a,b in PAIRS]

    def check(self,request,q,*,margin=True):
        state=self.state(request,q)
        if not self.collision.check(state)[0]:return False
        if margin:
            world=self.spheres.world(state)
            for pair in self.thresholds():
                a,b=pair['arms']
                if self.spheres.nearest(world,a,b)['clearance_m']<=pair['threshold_m']:return False
        return True

    def rrt(self,request,seed,budget):
        from ament_index_python.packages import get_package_prefix
        shapes={r:[dict(link=link,centre=centre.tolist(),radius=float(radius))
                   for link,centre,radius in zip(self.spheres.links[r],self.spheres.local[r],self.spheres.radii[r])]
                for r in self.names}
        payload=dict(urdf=str(self.directory/'moveit/robot.urdf'),srdf=str(self.directory/'moveit/robot.srdf'),
                     start=request['start'],joint_names=request['joint_names'],target=request['target'],seed=seed,
                     budget_s=budget,check_step=self.cfg['joint_check_step_rad'],spheres=shapes,pair_thresholds=self.thresholds())
        source,result=self.directory/'rrt-request.json',self.directory/'rrt-result.json'
        dump(source,payload);result.unlink(missing_ok=True)
        executable=Path(get_package_prefix('uwa_cell_motion'))/'lib/uwa_cell_motion/rrt_worker'
        try:
            proc=subprocess.run([str(executable),str(source),str(result)],capture_output=True,text=True,timeout=budget)
        except subprocess.TimeoutExpired:return None,'TIMEOUT'
        import json
        if not result.exists():return None,'RRT worker failed: '+proc.stderr[-500:]
        data=json.loads(result.read_text())
        return (data['path'],None) if data['success'] else (None,data['error'])

    def circular(self,request,seed,budget):
        """Whole-body circular steering, six independent rotation hypotheses.

        Sphere-relative control-point velocities are steered tangentially; a
        damped Jacobian inverse maps each avoidance command to joint space.
        This is a CF-inspired research baseline, not an ICF reproduction.
        """
        deadline=time.monotonic()+budget;cfg=self.cfg
        q0=np.asarray([request['start'][j] for j in request['joint_names']]);target=np.asarray(request['target'])
        bounds=np.asarray([self.collision.bounds[j] for j in request['joint_names']]).T
        thresholds=self.thresholds();rng=np.random.default_rng(seed)
        candidates=[]
        for axis in np.eye(3):
            for sign in (-1.,1.):candidates.append((axis,sign))
        rng.shuffle(candidates)
        agents=[dict(q=q0.copy(),path=[q0.tolist()],axis=a,sign=s,visits={},alive=True) for a,s in candidates]
        # Round robin gives all hypotheses the same wall-clock opportunity.
        for _ in range(int(cfg['field_max_steps'])):
            for agent in agents:
                if time.monotonic()>=deadline:return None,'TIMEOUT'
                if not agent['alive']:continue
                q=agent['q'];error=target-q
                if np.max(abs(error))<=cfg['goal_tolerance_rad']:
                    if self.edge(request,q,target):return agent['path']+[target.tolist()],None
                state=self.state(request,q);world,jac=self.spheres.jacobians(state,request['selected'])
                velocity=np.clip(.8*error,-cfg['velocity_limit_rad_s'],cfg['velocity_limit_rad_s'])
                terms=self.spheres.environment_nearest(state,world,jac)
                for pair in thresholds:
                    a,b=pair['arms'];nearest=self.spheres.nearest(world,a,b)
                    gap=nearest['clearance_m']-pair['threshold_m']
                    if gap>cfg['field_influence_m']:continue
                    i,j=nearest['sphere_indices'];normal=world[a][i]-world[b][j]
                    normal/=max(np.linalg.norm(normal),1e-9)
                    tangent=np.cross(agent['axis'],normal)*agent['sign']
                    tangent/=max(np.linalg.norm(tangent),1e-9)
                    relative=jac[a][i]-jac[b][j]
                    terms.append((gap,normal,relative))
                for gap,normal,relative in terms:
                    if gap>cfg['field_influence_m']:continue
                    tangent=np.cross(agent['axis'],normal)*agent['sign']
                    tangent/=max(np.linalg.norm(tangent),1e-9)
                    strength=np.clip(1-gap/cfg['field_influence_m'],0,1)
                    cartesian=relative@velocity
                    # Remove closing velocity near contact; tangential circulation
                    # supplies an independently chosen passing direction.
                    avoidance=(-min(0.,np.dot(cartesian,normal))*normal+
                               .06*tangent+.02*normal*max(0.,1-gap/.04))*strength
                    velocity+=relative.T@np.linalg.solve(relative@relative.T+.01*np.eye(3),avoidance)
                peak=np.max(abs(velocity))
                if peak>cfg['velocity_limit_rad_s']:velocity*=cfg['velocity_limit_rad_s']/peak
                accepted=False
                for scale in (1.,.5,.25,.125):
                    next_q=np.clip(q+cfg['field_step_s']*scale*velocity,bounds[0],bounds[1])
                    if np.max(abs(next_q-q))>1e-7 and self.edge(request,q,next_q):accepted=True;break
                if not accepted:agent['alive']=False;continue
                key=tuple(np.round(next_q/.015).astype(int));agent['visits'][key]=agent['visits'].get(key,0)+1
                if agent['visits'][key]>100:agent['alive']=False;continue
                agent['q']=next_q;agent['path'].append(next_q.tolist())
            if not any(a['alive'] for a in agents):return None,'STUCK: all circular hypotheses blocked/cycling'
        return None,'STEP_LIMIT'

    def edge(self,request,a,b):
        a,b=np.asarray(a),np.asarray(b)
        count=max(1,int(np.ceil(np.max(abs(b-a))/self.cfg['joint_check_step_rad'])))
        return all(self.check(request,a+u*(b-a)) for u in np.linspace(0,1,count+1))

    def plan(self,request,method,seed=0,normalized=False):
        if method not in ('rrtconnect','circular'):raise ValueError('Unknown planning method')
        request=request if normalized else self.normalize(request)
        started=time.monotonic();q0=[request['start'][j] for j in request['joint_names']]
        result=dict(schema_version=1,method=method,seed=seed,request=request,config=self.cfg,
                    model_signature=self.signature,mesh_sha256=self.spheres.geometry.assets,layout_path=str(self.layout_path) if self.layout_path else None,
                    success=False,simulation_only=True)
        if not self.check(request,q0):result['error']='INVALID_START'
        elif not self.check(request,request['target']):result['error']='INVALID_GOAL'
        else:
            remaining=self.cfg['planning_budget_s']-(time.monotonic()-started)
            path,error=(self.rrt(request,seed,remaining) if method=='rrtconnect' else self.circular(request,seed,remaining))
            result['planning_time_s']=time.monotonic()-started
            if error:result['error']=error
            else:
                try:
                    trajectory=self.time_parameterize(request,path)
                    result.update(success=True,trajectory=trajectory,metrics=self.metrics(request,trajectory))
                except ValueError as error:result['error']='VALIDATION: '+str(error)
        result.setdefault('planning_time_s',time.monotonic()-started)
        result['total_offline_time_s']=time.monotonic()-started
        return result

    def time_parameterize(self,request,path):
        # Stop at each waypoint: quintics have zero velocity/acceleration at
        # joins and never blend outside the checked geometric joint segments.
        path=np.asarray(path,float);dimension=len(request['joint_names'])
        if path.ndim!=2 or path.shape[1]!=dimension or len(path)<2 or not np.isfinite(path).all():raise ValueError('Malformed path')
        q0=np.asarray([request['start'][j] for j in request['joint_names']])
        if np.max(abs(path[0]-q0))>1e-8 or np.max(abs(path[-1]-request['target']))>1e-8:raise ValueError('Path endpoints changed')
        # Collapse collinear runs before applying stop-at-waypoint timing.
        reduced=[path[0]]
        for i in range(1,len(path)-1):
            a=path[i]-reduced[-1];b=path[i+1]-path[i]
            if np.linalg.norm(a)>1e-10 and np.linalg.norm(b)>1e-10 and np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))>0.99999:continue
            reduced.append(path[i])
        reduced.append(path[-1]);points=[];elapsed=0.
        for a,b in zip(reduced,reduced[1:]):
            delta=b-a;peak=float(np.max(abs(delta)))
            if peak<1e-10:continue
            duration=max(.1,1.875*peak/self.cfg['velocity_limit_rad_s'],np.sqrt(5.774*peak/self.cfg['acceleration_limit_rad_s2']))
            count=max(2,int(np.ceil(duration/.1)),int(np.ceil(1.875*peak/self.cfg['joint_check_step_rad'])))
            for u in np.linspace(0,1,count+1):
                if points and u==0:continue
                s=10*u**3-15*u**4+6*u**5;ds=30*u**2-60*u**3+30*u**4;dds=60*u-180*u**2+120*u**3
                q=a+s*delta
                if not self.check(request,q):raise ValueError('Full-cell/guard check rejected timed path')
                if points and not self.edge(request,points[-1]['positions'],q):raise ValueError('Timed interval rejected')
                points.append(dict(time=elapsed+float(u*duration),positions=q.tolist(),
                                   velocities=(ds*delta/duration).tolist(),accelerations=(dds*delta/duration**2).tolist()))
            elapsed+=duration
        if not points:
            points=[dict(time=t,positions=path[0].tolist(),velocities=[0.]*dimension,accelerations=[0.]*dimension) for t in (0.,.1)]
        return dict(joint_names=request['joint_names'],points=points,duration_s=elapsed or .1,
                    waypoints=[q.tolist() for q in reduced])

    def metrics(self,request,trajectory):
        points=trajectory['points'];minimum=float('inf')
        for p in points:
            world=self.spheres.world(self.state(request,p['positions']))
            minimum=min(minimum,*(self.spheres.nearest(world,a,b)['clearance_m'] for a,b in PAIRS))
        q=np.asarray([p['positions'] for p in points])
        return dict(planned_duration_s=trajectory['duration_s'],joint_path_length_rad=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()),
                    minimum_sphere_clearance_m=minimum,full_cell_collision_checked=True,guard_stops=0)

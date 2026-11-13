"""Before grasp: RRT. After grasp: one object path, one shared time law."""
from pathlib import Path
import xml.etree.ElementTree as ET
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from uwa_cell_description.configuration import joint_names
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_calibration.model import CollisionModel
from uwa_cell_motion.common import config as motion_config, all_names
from uwa_cell_motion.planning import Problem
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_control.parallel_scan import collision_signature
from match_cooperative_handling.rigid_object import rigid, interpolate, pose_error
from .core import ARMS, seal
from .scene import apply_object


def support_exemptions(problem,object_pose):
    """Only shallow object/table support, never finger/table or deep penetration."""
    from uwa_cell_description.scene_assets import transform
    local=np.asarray([v for s in problem.scene_record['shapes'] for v in s['vertices']])
    t=np.asarray(object_pose);world=local@t[:3,:3].T+t[:3,3]
    for table_id,table in problem.layout['tables'].items():
        inv=np.linalg.inv(transform(table['xyz'],table['rpy']))
        points=world@inv[:3,:3].T+inv[:3,3]
        shallow=-.001<=points[:,2].min()-table['height']<=.001
        problem.collision.scene.allowed_collision_matrix.set_entry(table_id+'_table_plate',problem.scene_record['object_id'],bool(shallow))


def actual_names(description, layout):
    result=all_names(layout)
    for arm in ARMS:
        result[arm]=joint_names(arm)+[j.get('name') for j in ET.fromstring(description).findall('joint')
            if j.get('type')=='revolute' and j.get('name').startswith(arm+'_robotiq_85_')]
    return result


def static_object_description(description, scene, object_pose):
    root=ET.fromstring(description); link=ET.SubElement(root,'link',name='grasp_object_static')
    for shape in scene['shapes']:
        collision=ET.SubElement(link,'collision'); mesh=ET.SubElement(ET.SubElement(collision,'geometry'),'mesh')
        mesh.set('filename',shape['uri'])
    joint=ET.SubElement(root,'joint',name='grasp_object_anchor',type='fixed')
    ET.SubElement(joint,'parent',link='world');ET.SubElement(joint,'child',link='grasp_object_static')
    t=rigid(object_pose);ET.SubElement(joint,'origin',xyz=' '.join(map(str,t[:3,3])),
        rpy=' '.join(map(str,Rotation.from_matrix(t[:3,:3]).as_euler('xyz'))))
    return ET.tostring(root,encoding='unicode')


class TaskProblem(Problem):
    def __init__(self, directory, description, layout, scene, object_pose, *, static=True):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.cfg=motion_config();self.layout=layout;self.layout_path=None
        self.base_description=description;self.scene_record=scene;self.object_pose=rigid(object_pose)
        self.description=static_object_description(description,scene,object_pose) if static else description
        self.collision=CollisionModel(self.description,self.directory/'moveit')
        self.names=actual_names(self.description,layout)
        self.spheres=SphereModel(self.description,self.names,self.cfg['sphere_spacing_m'])
        self.signature=collision_signature(self.description)
        self.chains={a:Chain(description,'world',a+'_tool0') for a in ARMS}
        if not static:
            apply_object(self.collision,scene,object_pose,touching=True)
            support_exemptions(self,object_pose)

    def solve_tcp(self, arm, start, target, *, attempts=1):
        target=rigid(target);names=joint_names(arm);chain=self.chains[arm]
        initial=np.array([start[n] for n in names]);bounds=np.array([self.collision.bounds[n] for n in names]).T
        def residual(q):
            actual=chain.forward(dict(start,**dict(zip(names,q))))
            return np.r_[actual[:3,3]-target[:3,3],
                .2*Rotation.from_matrix(actual[:3,:3]@target[:3,:3].T).as_rotvec()]
        rng=np.random.default_rng(17)
        for guess in [initial]+[rng.uniform(bounds[0],bounds[1]) for _ in range(attempts-1)]:
            fit=least_squares(residual,np.clip(guess,bounds[0]+1e-8,bounds[1]-1e-8),bounds=bounds,max_nfev=100)
            measured=chain.forward(dict(start,**dict(zip(names,fit.x))))
            distance,angle=pose_error(measured,target)
            if distance<2e-5 and angle<2e-4:return fit.x
        raise ValueError(arm+': continuous object-derived IK failed')


def grasp_candidates(description, scene, cfg, object_pose):
    """Each 85mm gripper pinches one wall, never the carton-wide span."""
    t=rigid(object_pose);dims=np.max([v for shape in scene['shapes'] for v in shape['vertices']],axis=0)
    candidates=[]
    for axis in (0,1):
        tangent=1-axis
        for fraction in (.5,.2,.3,.7,.8):
            targets={};pre={};contacts={}
            for arm, side in zip(ARMS,(0,1)):
                point=np.zeros(3);point[axis]=dims[axis]*side+cfg['wall_thickness_m']*(.5 if not side else -.5)
                point[tangent]=dims[tangent]*(fraction if side==0 else 1-fraction)
                heights=[]
                for shape in scene['shapes']:
                    if shape['axis']!=axis or shape['side']!=side:continue
                    triangle=np.array(shape['vertices'])[:shape.get('outline_vertices',3)]
                    for v,w in zip(triangle,np.roll(triangle,-1,axis=0)):
                        if min(v[tangent],w[tangent])-1e-9 <= point[tangent] <= max(v[tangent],w[tangent])+1e-9:
                            if abs(v[tangent]-w[tangent])<1e-9:heights.extend([v[2],w[2]])
                            else:heights.append(float(v[2]+(w[2]-v[2])*(point[tangent]-v[tangent])/(w[tangent]-v[tangent])))
                if not heights:break
                point[2]=max(heights)-.018
                # Closing axis across wall; fingers enter vertically from above.
                x=np.eye(3)[axis];z=np.array([0.,0.,-1.]);y=np.cross(z,x)
                rotation=t[:3,:3]@np.column_stack([x,y,z])
                base=np.eye(4);base[:3,:3]=rotation
                world_point=t[:3,:3]@point+t[:3,3]
                base[:3,3]=world_point-rotation@np.array([0.,0.,.145])
                tool_base=Chain(description,arm+'_tool0',arm+'_robotiq_85_base_link').forward({})
                targets[arm]=base@np.linalg.inv(tool_base)
                pre[arm]=targets[arm].copy();pre[arm][:3,3]+=[0,0,cfg['pregrasp_distance_m']]
                contacts[arm]=dict(point_object=point,normal_object=x,side=side,wall_axis=axis)
            if len(targets)==2:
                candidates.append(dict(id=f'wall_{axis}_{fraction}',tcp_targets=targets,pregrasp=pre,
                    contacts=contacts,score=float(abs(fraction-.5)),strategy='two local upper-wall pinches'))
    return sorted(candidates,key=lambda c:(c['score'],c['id']))


def plan_approach(problem, start, candidate, *, seed=0):
    goals={}
    for arm in ARMS:
        target=candidate['pregrasp'][arm]
        # Existing deterministic IK supplies alternative branches for RRT.
        goal=dict(frame_id='world',target_link=arm+'_tool0',pose=dict(
            position=np.asarray(target)[:3,3].tolist(),
            orientation_xyzw=Rotation.from_matrix(np.asarray(target)[:3,:3]).as_quat().tolist()))
        goals[arm]=goal
    request=problem.normalize(dict(start=start,goals=goals))
    initial=[start[n] for n in request['joint_names']]
    if not problem.check(request,initial):raise ValueError('Approach start collides or lacks guard clearance')
    if not problem.check(request,request['target']):raise ValueError('Pregrasp collides or lacks guard clearance')
    if problem.edge(request,initial,request['target']):path=[initial,request['target']]
    else:
        path,error=problem.rrt(request,seed,problem.cfg['planning_budget_s'])
        if path is None:raise ValueError(error)
    trajectory=problem.time_parameterize(request,path)
    return seal(dict(schema_version=1,kind='pregrasp',request=request,trajectory=trajectory,
        mesh_sha256=problem.spheres.geometry.assets,
        model_signature=problem.signature,scene_sha256=problem.scene_record['sha256'],candidate=candidate))


def grasp_entry(problem, start, candidate, cfg):
    """Checked common Cartesian entry before contacts; no individual retiming."""
    names=[j for a in ARMS for j in joint_names(a)];q=dict(start);samples=[]
    origins={a:problem.chains[a].forward(q) for a in ARMS}
    for u in np.linspace(0,1,121):
        for arm in ARMS:
            target=interpolate(origins[arm],candidate['tcp_targets'][arm],float(u))
            q.update(zip(joint_names(arm),problem.solve_tcp(arm,q,target)))
        if not problem.collision.check(q)[0]:raise ValueError('Final grasp entry collides')
        request=dict(start=start,joint_names=names)
        if not problem.check(request,np.array([q[n] for n in names])):
            raise ValueError('Final grasp entry violates stopping reserve')
        samples.append([q[j] for j in names])
    samples=np.asarray(samples);fractions=np.linspace(0,1,len(samples))
    gradient=np.gradient(samples,fractions,axis=0)
    duration=max(30.,1.875*np.max(abs(gradient))/cfg['joint_velocity_rad_s'])
    points=[]
    for u in np.linspace(0,1,max(121,int(np.ceil(duration/.025))+1)):
        s=10*u**3-15*u**4+6*u**5
        positions=[float(np.interp(s,fractions,samples[:,i])) for i in range(len(names))]
        points.append(dict(time=float(u*duration),positions=positions))
    return dict(joint_names=names,points=points,duration_s=float(duration)),q


class PlannedObjectConstraint:
    """Predicted rigid geometry for preflight; never evidence of a real grasp."""
    members=ARMS
    def __init__(self,obj,tcps):
        from match_cooperative_handling.rigid_object import relative
        self.offsets={a:relative(obj,tcps[a]) for a in ARMS}
    def targets(self,obj):
        from match_cooperative_handling.rigid_object import tcp_target
        return {a:tcp_target(obj,t) for a,t in self.offsets.items()}
    def record(self):return dict(kind='predicted_geometry_only',members=ARMS,object_to_tcp=self.offsets,contact_confirmed=False)


def object_trajectory(problem, group, start, object_start, object_end, cfg):
    """One common object parameter. IK resolves actuator states, not arm paths.

    Dense interpolation validation bounds deviation of the resulting shared
    joint controller interpolation from the rigid-object constraint.
    """
    distance,angle=pose_error(object_start,object_end)
    steps=max(2,int(np.ceil(distance/.0005)),int(np.ceil(angle/.002)))
    names=[j for a in group.members for j in joint_names(a)]
    qprev=dict(start);samples=[];poses=[]
    for u in np.linspace(0,1,steps+1):
        obj=interpolate(object_start,object_end,float(u));targets=group.targets(obj)
        q=dict(qprev)
        for arm,(target,_) in targets.items():q.update(zip(joint_names(arm),problem.solve_tcp(arm,qprev,target)))
        apply_object(problem.collision,problem.scene_record,obj,touching=True)
        support_exemptions(problem,obj)
        if not problem.collision.check(q)[0]:raise ValueError('Object motion full-scene collision')
        world=problem.spheres.world(q)
        for pair in problem.thresholds():
            if problem.spheres.nearest(world,*pair['arms'])['clearance_m']<=pair['threshold_m']:
                raise ValueError('Object motion violates interarm stopping reserve')
        samples.append([q[n] for n in names]);poses.append(obj);qprev=q
    samples=np.array(samples)
    duration=max(2.,1.875*distance/cfg['max_object_speed_m_s'])
    # Rescale the WHOLE object law to satisfy the most restrictive joint.
    fractions=np.linspace(0,1,len(samples));gradient=np.gradient(samples,fractions,axis=0)
    curvature=np.gradient(gradient,fractions,axis=0)
    duration=max(duration,1.875*float(np.max(abs(gradient)))/cfg['joint_velocity_rad_s'],
        np.sqrt(float(np.max(abs(curvature)))*3.52/cfg['joint_acceleration_rad_s2']),
        np.sqrt(float(np.max(abs(gradient)))*5.774/cfg['joint_acceleration_rad_s2']))
    points=[]
    # Uniform time, quintic object progress, shared linear joint interpolation.
    for time_u in np.linspace(0,1,max(steps+1,int(np.ceil(duration/.025))+1)):
        progress=10*time_u**3-15*time_u**4+6*time_u**5
        q=np.array([np.interp(progress,fractions,samples[:,i]) for i in range(len(names))])
        obj=interpolate(object_start,object_end,float(progress))
        state=dict(start,**dict(zip(names,q)))
        for arm,(expected,_) in group.targets(obj).items():
            d,a=pose_error(problem.chains[arm].forward(state),expected)
            if d>.0005 or a>.004:raise ValueError('Shared controller interpolation violates rigid-object corridor')
        apply_object(problem.collision,problem.scene_record,obj,touching=True)
        support_exemptions(problem,obj)
        if not problem.collision.check(state)[0]:raise ValueError('Interpolated object motion collides')
        points.append(dict(time=float(time_u*duration),positions=q.tolist(),object_pose=obj.tolist()))
    return seal(dict(kind='rigid_object',joint_names=names,points=points,duration_s=duration,
        group=group.record(),scene_sha256=problem.scene_record['sha256'],
        statement='One object path and one shared time law; no independent arm trajectory planning'))

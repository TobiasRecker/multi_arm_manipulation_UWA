"""Before grasp: RRT. After grasp: one object path, one shared time law."""
from pathlib import Path
import xml.etree.ElementTree as ET
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.interpolate import CubicSpline
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
from .scene import apply_object,mass_properties,inherit_pad_adjacency
from .operating import motion_configuration,TaskSphereModel
from .timing import limit_shared_jerk,object_law_duration


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
        self.cfg=motion_configuration(scene['cfg']);self.layout=layout;self.layout_path=None
        self.base_description=description;self.scene_record=scene;self.object_pose=rigid(object_pose)
        self.description=static_object_description(description,scene,object_pose) if static else description
        self.collision=CollisionModel(self.description,self.directory/'moveit')
        inherit_pad_adjacency(self.collision,self.directory/'moveit/robot.srdf')
        self.names=actual_names(self.description,layout)
        self.spheres=TaskSphereModel(self.description,self.names,scene['cfg'],self.cfg['sphere_spacing_m'])
        self.signature=collision_signature(self.description)
        self.chains={a:Chain(description,'world',a+'_tool0') for a in ARMS}
        if not static:
            apply_object(self.collision,scene,object_pose,touching=True)
            support_exemptions(self,object_pose)

    def time_parameterize(self,request,path):
        trajectory=super().time_parameterize(request,path)
        limit=self.scene_record['cfg'].get('joint_jerk_rad_s3')
        return limit_shared_jerk(trajectory,limit) if limit is not None else trajectory

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
    if t[2,2]<np.cos(np.deg2rad(2.)):
        raise ValueError('This wall-pinch strategy requires an upright carton on horizontal support')
    com,_=mass_properties(scene['shapes'],cfg['mass_kg'])
    world_com=t[:3,:3]@com+t[:3,3]
    bases={a:Chain(description,'world',a+'_base_link').forward({})[:3,3] for a in ARMS}
    root=ET.fromstring(description);pad_top_offsets={}
    fingers=root.find("ros2_control[@name='ContactGrippers']")
    for arm in ARMS:
        lowest=float('inf')
        for angle in (.76,.8):
            q={joint.get('name'):angle*float(joint.find("param[@name='multiplier']").text
                if joint.find("param[@name='multiplier']") is not None else 1.)
                for joint in fingers.findall('joint') if joint.get('name').startswith(arm+'_')}
            for side in ('left','right'):
                name=arm+'_robotiq_85_'+side+'_finger_tip_pad_link'
                collision=root.find(f"link[@name='{name}']/collision");origin=collision.find('origin')
                size=np.fromstring(collision.find('geometry/box').get('size'),sep=' ')
                local=np.array([[x,y,z] for x in (-size[0]/2,size[0]/2)
                    for y in (-size[1]/2,size[1]/2) for z in (-size[2]/2,size[2]/2)])
                local=local@Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).as_matrix().T+np.fromstring(origin.get('xyz'),sep=' ')
                tf=Chain(description,arm+'_robotiq_85_base_link',name).forward(q)
                lowest=min(lowest,float((local@tf[:3,:3].T+tf[:3,3])[:,2].min()))
        pad_top_offsets[arm]=.145-lowest
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
                    triangle=np.array(shape['vertices'])[:len(shape['vertices'])//2]
                    for v,w in zip(triangle,np.roll(triangle,-1,axis=0)):
                        if min(v[tangent],w[tangent])-1e-9 <= point[tangent] <= max(v[tangent],w[tangent])+1e-9:
                            if abs(v[tangent]-w[tangent])<1e-9:heights.extend([v[2],w[2]])
                            else:heights.append(float(v[2]+(w[2]-v[2])*(point[tangent]-v[tangent])/(w[tangent]-v[tangent])))
                if not heights or max(heights)<.06:break
                # Keep the complete pad below the exact lower-wall envelope.
                # A pinch across artificial convex-mesh seams can produce
                # opposing edge contacts in the rigid-body solver.
                base_top=min(shape['wall_base_top_m'] for shape in scene['shapes']
                    if shape['axis']==axis and shape['side']==side)
                point[2]=min(max(heights)-.025,base_top-pad_top_offsets[arm]-.003)
                # Closing axis across wall; fingers enter vertically from above.
                x=np.eye(3)[axis]
                # Supported upright-carton strategy: project the image-derived
                # wall yaw onto the gravity plane. Do not command small planar
                # PnP roll/pitch errors as a tilted pinch into vertical walls.
                # This is a declared grasp assumption, not a truth pose prior.
                closing=t[:3,:3]@x;closing[2]=0.;closing/=np.linalg.norm(closing)
                z=np.array([0.,0.,-1.]);y=np.cross(z,closing)
                rotation=np.column_stack([closing,y,z])
                base=np.eye(4);base[:3,:3]=rotation
                world_point=t[:3,:3]@point+t[:3,3]
                base[:3,3]=world_point-rotation@np.array([0.,0.,.145])
                tool_base=Chain(description,arm+'_tool0',arm+'_robotiq_85_base_link').forward({})
                targets[arm]=base@np.linalg.inv(tool_base)
                pre[arm]=targets[arm].copy();pre[arm][:3,3]+=[0,0,cfg['pregrasp_distance_m']]
                contacts[arm]=dict(point_object=point,normal_object=x,side=side,wall_axis=axis,
                    nominal_pad_top_object_m=float(point[2]+pad_top_offsets[arm]),
                    continuous_wall_top_object_m=float(base_top),pad_top_margin_m=.003)
            if len(targets)==2:
                points=[(t[:3,:3]@contacts[a]['point_object']+t[:3,3])[:2] for a in ARMS]
                span=points[1]-points[0]
                beta=float((world_com[:2]-points[0])@span/(span@span))
                if not .05<beta<.95:continue
                offset=float(np.linalg.norm(world_com[:2]-(points[0]+beta*span)))
                reach=float(np.mean([np.linalg.norm(pre[a][:3,3]-bases[a]) for a in ARMS]))
                candidates.append(dict(id=f'wall_{axis}_{fraction}',tcp_targets=targets,pregrasp=pre,
                    contacts=contacts,score=reach+5*offset+.05*abs(fraction-.5),strategy='gravity-aligned upright-carton wall pinches',
                    assumptions=['upright_carton_on_horizontal_support','image_derived_yaw'],
                    centre_of_mass_object_m=com,gravity_projection_fraction=beta,support_line_offset_m=offset,
                    estimated_vertical_load_n={ARMS[0]:(1-beta)*cfg['mass_kg']*9.81,ARMS[1]:beta*cfg['mass_kg']*9.81},
                    load_estimate_kind='static point-support approximation; not contact holding proof'))
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
    spline=CubicSpline(fractions,samples,axis=0)
    dense=np.linspace(0,1,len(samples)*4+1)
    gradient=spline(dense,1);curvature=spline(dense,2)
    duration=max(cfg.get('grasp_entry_min_duration_s',30.),1.875*np.max(abs(gradient))/cfg['joint_velocity_rad_s'],
        np.sqrt((np.max(abs(curvature))*1.875**2+np.max(abs(gradient))*5.774)/cfg['joint_acceleration_rad_s2']))
    points=[]
    for u in np.linspace(0,1,max(121,int(np.ceil(duration/.025))+1)):
        s=10*u**3-15*u**4+6*u**5
        positions=spline(s);ds=(30*u**2-60*u**3+30*u**4)/duration;dds=(60*u-180*u**2+120*u**3)/duration**2
        velocity=spline(s,1)*ds;acceleration=spline(s,2)*ds**2+spline(s,1)*dds
        if np.max(abs(velocity))>cfg['joint_velocity_rad_s']+1e-9 or np.max(abs(acceleration))>cfg['joint_acceleration_rad_s2']+1e-9:
            raise ValueError('Shared grasp entry timing exceeds operating envelope')
        state=dict(start,**dict(zip(names,positions)))
        if not problem.collision.check(state)[0] or not problem.check(dict(start=start,joint_names=names),positions):
            raise ValueError('Interpolated shared grasp entry collides or violates stopping reserve')
        points.append(dict(time=float(u*duration),positions=positions.tolist(),velocities=velocity.tolist(),accelerations=acceleration.tolist()))
    trajectory=dict(joint_names=names,points=points,duration_s=float(duration))
    if cfg.get('joint_jerk_rad_s3') is not None:trajectory=limit_shared_jerk(trajectory,cfg['joint_jerk_rad_s3'])
    return trajectory,q


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


def object_pose_at(start, end, fraction, pivot=None):
    """Interpolate an asset pose, optionally about a declared material point."""
    pose=interpolate(start,end,float(fraction))
    if pivot is not None:
        pivot=np.asarray(pivot)
        a=np.asarray(start);b=np.asarray(end)
        world=(1-fraction)*(a[:3,:3]@pivot+a[:3,3])+fraction*(b[:3,:3]@pivot+b[:3,3])
        pose[:3,3]=world-pose[:3,:3]@pivot
    return pose


def carton_motion_poses(scene, layout, object_start, cfg):
    """Lift/roll/place geometry; camera selects the sign, never truth pose."""
    obj=rigid(object_start)
    if not cfg.get('roll_long_axis',False):
        lifted=obj.copy();lifted[2,3]+=cfg['lift_m']
        return dict(lifted=lifted,placed=obj,lift_m=cfg['lift_m'],pivot=None)
    vertices=np.asarray([v for shape in scene['shapes'] for v in shape['vertices']])
    extent=np.ptp(vertices,axis=0);axis=int(np.argmax(extent[:2]))
    pivot=np.asarray(scene['lift_reference_point_object_m'])
    centre=obj[:3,:3]@pivot+obj[:3,3]
    camera=np.asarray(scene['T_world_overview_optical'])[:3,3]
    choices=[]
    for sign in (-1,1):
        rotation=obj[:3,:3]@Rotation.from_rotvec(np.eye(3)[axis]*sign*np.pi/2).as_matrix()
        choices.append((float(rotation[:,2]@(camera-centre)),sign,rotation))
    score,sign,rotation=max(choices,key=lambda item:item[0])
    if score<=0:raise ValueError('No longitudinal quarter turn faces the overview camera')
    placed=obj.copy();placed[:3,:3]=rotation;placed[:3,3]=centre-rotation@pivot
    # The existing carton spans the gap between two coplanar tables. Allow
    # that initial support, but place the whole final footprint on one table.
    support=[]
    from uwa_cell_description.scene_assets import transform
    for name,table in layout['tables'].items():
        if cfg.get('placement_table') and name!=cfg['placement_table']:continue
        frame=transform(table['xyz'],table['rpy'])
        if not np.allclose(frame[:3,2],[0,0,1],atol=1e-8):continue
        points=(vertices@obj[:3,:3].T+obj[:3,3]-frame[:3,3])@frame[:3,:3]
        half=np.array([table['width'],table['length']])/2
        if abs(points[:,2].min()-table['height'])>.005:continue
        if np.any(points[:,:2].max(0)<-half) or np.any(points[:,:2].min(0)>half):continue
        footprint=(vertices@rotation.T+placed[:3,3]-frame[:3,3])@frame[:3,:3]
        low=-half+.005-footprint[:,:2].min(0)
        high=half-.005-footprint[:,:2].max(0)
        if np.any(low>high):continue
        shift=np.clip(np.zeros(2),low,high)
        target=placed.copy();target[:3,3]+=frame[:3,:2]@shift
        height=frame[2,3]+table['height']
        target[2,3]+=height-(vertices@rotation.T+target[:3,3])[:,2].min()
        support.append((float(np.linalg.norm(shift)),name,target,height))
    if not support:raise ValueError('Roll requires horizontal support and a table fitting the sideways footprint')
    _,name,placed,height=min(support,key=lambda item:(item[0],item[1]))
    turned=obj.copy();turned[:3,:3]=rotation;turned[:3,3]=centre-rotation@pivot
    lowest=min((vertices@object_pose_at(obj,turned,u,pivot)[:3,:3].T+
                object_pose_at(obj,turned,u,pivot)[:3,3])[:,2].min() for u in np.linspace(0,1,721))
    # Sampling error is bounded by radius*dtheta/2; keep it in the reserve.
    radius=float(np.linalg.norm(vertices-pivot,axis=1).max())
    clearance=cfg.get('rotation_clearance_m',.02)+radius*np.pi/2880
    lift=max(cfg['lift_m'],height+clearance-lowest)
    if lift>cfg.get('maximum_roll_lift_m',.25):raise ValueError('Roll clearance exceeds configured lift envelope')
    lifted=obj.copy();lifted[2,3]+=lift
    turned[2,3]+=lift
    return dict(lifted=lifted,turned=turned,placed=placed,lift_m=float(lift),pivot=pivot,
                axis_object=axis,angle_rad=sign*np.pi/2,support_table=name,
                opening_camera_cosine=float(rotation[:,2]@(camera-centre)/np.linalg.norm(camera-centre)),
                statement='Geometric target only; contact holding and release require simulation evidence')


def compile_object_recipe(problem, group, start, obj, cfg):
    """Preflight the entire carrying path before entry, with fixed grasp offsets."""
    poses=carton_motion_poses(problem.scene_record,problem.layout,obj,cfg)
    stages=[('lift',poses['lifted'])]+([('turn',poses['turned'])] if 'turned' in poses else [])+[('set_down',poses['placed'])]
    # Reject a blocked late phase before spending time on dense timed splines
    # of earlier phases. This is an additional screen, never a final approval.
    state=dict(start);origin=obj
    for name,target in stages:
        try:samples,_,_,names,_,_=_object_samples(problem,group,state,origin,target,cfg,poses['pivot'])
        except ValueError as error:raise ValueError(name+': '+str(error)) from error
        state.update(zip(names,samples[-1]));origin=target
    state=dict(start);origin=obj;motions={}
    for name,target in stages:
        try:trajectory=object_trajectory(problem,group,state,origin,target,cfg,pivot=poses['pivot'])
        except ValueError as error:raise ValueError(name+': '+str(error)) from error
        motions[name]=trajectory
        state.update(zip(trajectory['joint_names'],trajectory['points'][-1]['positions']))
        origin=target
    return dict(poses=poses,motions=motions)


def _object_samples(problem,group,start,object_start,object_end,cfg,pivot=None):
    distance,angle=pose_error(object_start,object_end)
    if pivot is not None:
        # Bound translation of the asset origin along the pivoted arc.
        a=np.asarray(object_start);b=np.asarray(object_end);p=np.asarray(pivot)
        travel=np.linalg.norm((b[:3,:3]@p+b[:3,3])-(a[:3,:3]@p+a[:3,3]))
        distance=max(distance,float(travel+np.linalg.norm(p)*angle))
    steps=max(2,int(np.ceil(distance/.0005)),int(np.ceil(angle/.002)))
    names=[j for a in group.members for j in joint_names(a)]
    qprev=dict(start);samples=[];poses=[]
    for u in np.linspace(0,1,steps+1):
        obj=object_pose_at(object_start,object_end,float(u),pivot);targets=group.targets(obj)
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
    return samples,poses,steps,names,distance,angle


def object_trajectory(problem, group, start, object_start, object_end, cfg, *, pivot=None):
    """One common object parameter. IK resolves actuator states, not arm paths.

    Dense interpolation validation bounds deviation of the resulting shared
    joint controller interpolation from the rigid-object constraint.
    """
    samples,poses,steps,names,distance,angle=_object_samples(problem,group,start,object_start,object_end,cfg,pivot)
    samples=np.array(samples)
    duration=max(2.,1.875*distance/cfg['max_object_speed_m_s'])
    if angle>1e-9:
        duration=max(duration,1.875*angle/cfg.get('max_object_angular_speed_rad_s',.05))
    # Rescale the WHOLE object law to satisfy the most restrictive joint.
    fractions=np.linspace(0,1,len(samples));spline=CubicSpline(fractions,samples,axis=0)
    gradient=spline(np.linspace(0,1,steps*4+1),1);curvature=spline(np.linspace(0,1,steps*4+1),2)
    if cfg.get('roll_long_axis'):
        duration=max(duration,object_law_duration(spline,cfg['joint_velocity_rad_s'],cfg['joint_acceleration_rad_s2']))*1.02
    else:
        duration=max(duration,1.875*float(np.max(abs(gradient)))/cfg['joint_velocity_rad_s'],
            np.sqrt((float(np.max(abs(curvature)))*1.875**2+float(np.max(abs(gradient)))*5.774)/cfg['joint_acceleration_rad_s2']))*1.02
    points=[]
    # Uniform time, quintic object progress, common C2 joint spline; supply
    # derivatives so the action controller preserves smooth interpolation.
    for time_u in np.linspace(0,1,max(steps+1,int(np.ceil(duration/.025))+1)):
        progress=10*time_u**3-15*time_u**4+6*time_u**5
        q=spline(progress)
        ds=(30*time_u**2-60*time_u**3+30*time_u**4)/duration
        dds=(60*time_u-180*time_u**2+120*time_u**3)/duration**2
        velocity=spline(progress,1)*ds
        acceleration=spline(progress,2)*ds**2+spline(progress,1)*dds
        if np.max(abs(velocity))>cfg['joint_velocity_rad_s'] or np.max(abs(acceleration))>cfg['joint_acceleration_rad_s2']:
            raise ValueError('Common object timing exceeds joint operating limits')
        obj=object_pose_at(object_start,object_end,float(progress),pivot)
        state=dict(start,**dict(zip(names,q)))
        for arm,(expected,_) in group.targets(obj).items():
            d,a=pose_error(problem.chains[arm].forward(state),expected)
            if d>.0005 or a>.004:raise ValueError('Shared controller interpolation violates rigid-object corridor')
        apply_object(problem.collision,problem.scene_record,obj,touching=True)
        support_exemptions(problem,obj)
        if not problem.collision.check(state)[0]:raise ValueError('Interpolated object motion collides')
        points.append(dict(time=float(time_u*duration),positions=q.tolist(),velocities=velocity.tolist(),
            accelerations=acceleration.tolist(),object_pose=obj.tolist()))
    trajectory=dict(kind='rigid_object',joint_names=names,points=points,duration_s=duration,
        group=group.record(),scene_sha256=problem.scene_record['sha256'],
        statement='One object path and one shared time law; no independent arm trajectory planning')
    if cfg.get('joint_jerk_rad_s3') is not None:trajectory=limit_shared_jerk(trajectory,cfg['joint_jerk_rad_s3'])
    return seal(trajectory)

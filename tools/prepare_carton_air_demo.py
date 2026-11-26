#!/usr/bin/env python3
"""File-only transfer of the completed Gazebo demonstration to a current grip.

No ROS nodes, robot commands or gripper commands. The 300 mm tool is a
mathematical reference only. An accepted model draft still requires the
controller-interpolation check and explicit Motion Review before execution.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

from uwa_cell_calibration.model import CollisionModel
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import config, joint_names, PAIRS
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.object_transport import ObjectTransport
from uwa_cell_motion.carton_paths import solve_near
from uwa_cell_tasks.reviewed_carton import START_TOLERANCE
from prepare_carton_open_entry import shell_boxes
from return_home_model import model_identity

REPO = Path(__file__).resolve().parents[1]
HOLDERS = ('right_front', 'right_rear')
WORKER = 'left_front'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bind_grip(proof, observations, binding, chains):
    """A task continuation requires the exact successful lift end, not an old pose."""
    if not proof.get('success') or proof.get('height_m') != .020:
        raise ValueError('The successful checked20mm lift is required')
    if set(observations.get('arms', {})) != set(chains):
        raise ValueError('Complete current four-arm scene required')
    state = {}
    for arm, row in observations['arms'].items():
        q = np.asarray(row['samples'][-1]['actual_q'])
        if row.get('observed') is not True or q.shape != (6,) or not np.isfinite(q).all():
            raise ValueError(arm+': complete measured start required')
        state.update(zip(joint_names(arm), q.tolist(), strict=True))
    for arm in HOLDERS:
        if max(abs(state[j]-proof['end'][j]) for j in joint_names(arm)) > START_TOLERANCE:
            raise ValueError(arm+': current joints differ from the successful lift end')
    support = np.asarray(binding['world_object_by_arm'][HOLDERS[0]], float)
    if not all(np.allclose(support, t, atol=1e-8, rtol=0)
               for t in binding['world_object_by_arm'].values()):
        raise ValueError('One common registered carton pose required')
    lifted = support.copy()
    lifted[2,3] += proof['height_m']
    estimates = [chains[a].forward(state) @ np.linalg.inv(chains[a].forward(proof['end'])) @ lifted
                 for a in HOLDERS]
    if (np.linalg.norm(estimates[0][:3,3]-estimates[1][:3,3]) > .001 or
            Rotation.from_matrix(estimates[0][:3,:3] @ estimates[1][:3,:3].T).magnitude() > .002):
        raise ValueError('The two holders disagree on the current carton pose')
    pose = estimates[0]
    offsets = {a: np.linalg.inv(pose) @ chains[a].forward(state) for a in HOLDERS}
    return state, pose, offsets


def pack(args):
    from return_home_request import recorded_carton
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    profile = REPO/'uwa_cell_motion/config/hardware_carton_supported_trend.yaml'
    problem = HardwareProblem(out/'model', config(profile), REPO/'config/hardware_inventory.yaml')
    problem.chains = {a: Chain(problem.original_description, 'world', a+'_tool0') for a in problem.names}
    run = args.grasp_run.resolve()
    recorded_carton(run)
    proof = read(run/'plan/weigh-plan/proof.json')
    binding = read(run/'multiview/object-pose.json')
    evidence = read(run/'plan/high-plan/evidence.json')
    scene_path = Path(evidence['inputs']['contact_scene']['path'])
    if digest(scene_path) != evidence['inputs']['contact_scene']['sha256']:
        raise ValueError('The bound carton geometry changed')
    if digest(run/'multiview/object-pose.json') != evidence['inputs']['object_pose']['sha256']:
        raise ValueError('The carton registration differs from the executed grasp input')
    observation = read(args.observations)
    identity = observation.get('model_identity')
    matching = identity == model_identity(problem) if identity else observation.get('model_signature') == problem.signature
    if not matching:
        raise ValueError('Snapshot and hardware model differ')
    state, pose, offsets = bind_grip(proof, observation, binding, problem.chains)
    state.update({j:0. for names in problem.names.values() for j in names[6:]})
    trial = args.reference.resolve()
    if read(trial/'run05/state.json')['state'] != 'DONE':
        raise ValueError('Use the completed Gazebo reference')
    recipe = read(trial/'fixed-drawing-recipe.json')
    phases = recipe['connectors'][:2]+recipe['drawing']['phases']+recipe['connectors'][2:]
    reference_description = (trial/'scene05/robot.urdf').read_text()
    group = read(trial/'run05/group.json')
    trajectories = [];reference_files=[]
    for phase in phases:
        path = trial/'run05/drawing-trajectories'/ (phase['id']+'.json')
        data = read(path)
        reference_files.append(path)
        trajectories.append(dict(id=phase['id'], face=phase.get('face'),
            drawing=bool(phase.get('drawing')), operation=phase.get('operation'),
            joint_names=data['joint_names'], points=data['points']))
    record = dict(start=state, pose=pose.tolist(), offsets={a:v.tolist() for a,v in offsets.items()},
        nominal_jaws=proof['nominal_contact_joints'], names=problem.names, config=problem.cfg,
        model_signature=problem.signature, model_identity=model_identity(problem), source_grasp=str(run), tool_length_m=.300,
        object_boxes=shell_boxes(read(scene_path)), reference_group=group,
        dimensions_m=recipe['drawing']['dimensions_m'],
        reference_initial=recipe['drawing']['initial_state'], phases=trajectories,
        inputs={str(p):digest(p) for p in [args.observations, run/'plan/weigh-plan/proof.json',
            run/'multiview/object-pose.json',scene_path,trial/'fixed-drawing-recipe.json',
            trial/'scene05/robot.urdf',trial/'run05/group.json',Path(__file__)]})
    record['inputs'].update({str(path):digest(path)for path in [trial/'run05/state.json',*reference_files]})
    # The container receives the finite model and its own local mesh copies.
    assets = out/'assets';assets.mkdir()
    def portable(description):
        root = ET.fromstring(description)
        for mesh in root.findall('.//mesh'):
            source = mesh.get('filename')
            if source is None:continue
            path = Path(source.removeprefix('file://'))
            if not path.is_absolute() or not path.is_file():
                raise ValueError('Frozen model needs resolved mesh files: '+source)
            target = assets/(digest(path)+path.suffix)
            if not target.exists():shutil.copyfile(path,target)
            mesh.set('filename','file:///input/assets/'+target.name)
        return ET.tostring(root, encoding='unicode')
    for name, description in [('hardware.urdf',problem.description),
                               ('original.urdf',problem.original_description),
                               ('reference.urdf',reference_description)]:
        (out/name).write_text(portable(description))
    shutil.copyfile(problem.directory/'moveit/robot.srdf',out/'hardware.srdf')
    write(out/'input.json',record)
    sources=out/'python';sources.mkdir()
    for package in ('uwa_cell_calibration','uwa_cell_control','uwa_cell_description',
                    'uwa_cell_gazebo','uwa_cell_motion','uwa_cell_tasks'):
        shutil.copytree(REPO/package/package,sources/package,ignore=shutil.ignore_patterns('__pycache__'))
    match=REPO.parents[0]/'match_mobile_robotics_jazzy/ur_robot/match_ur_hardware/match_ur_hardware'
    shutil.copytree(match,sources/'match_ur_hardware',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(Path(__file__),out/'prepare.py')
    shutil.copyfile(REPO/'tools/prepare_carton_open_entry.py',out/'prepare_carton_open_entry.py')
    shutil.copyfile(REPO/'tools/return_home_model.py',out/'return_home_model.py')
    print(json.dumps(dict(packed=str(out),phases=len(phases),robot_commands_sent=False)))


def moving_model(problem, data, output):
    """Auxiliary held-object scene; the cell proof retains every opening."""
    root = ET.fromstring(problem.description)
    original = ET.fromstring(problem.original_description)
    for link in root.findall('link'):
        if any(link.get('name').startswith(a+'_robotiq_85_') for a in HOLDERS):
            for collision in list(link.findall('collision')):link.remove(collision)
            for collision in original.find("link[@name='%s']"%link.get('name')).findall('collision'):
                link.append(copy.deepcopy(collision))
    # Keep the carried geometry inside this auxiliary URDF. World-object
    # insertion in the installed Python binding also contaminated the base
    # scene on the next query; no world collision object is inserted here.
    parent='world'
    for axis in ('x','y','z','yaw','pitch','roll'):
        child='air_demo_'+axis
        ET.SubElement(root,'link',name=child)
        joint=ET.SubElement(root,'joint',name=child+'_joint',
            type='prismatic' if axis in ('x','y','z') else 'revolute')
        ET.SubElement(joint,'parent',link=parent);ET.SubElement(joint,'child',link=child)
        vector={'x':'1 0 0','y':'0 1 0','z':'0 0 1',
                'yaw':'0 0 1','pitch':'0 1 0','roll':'1 0 0'}[axis]
        ET.SubElement(joint,'axis',xyz=vector)
        ET.SubElement(joint,'limit',lower='-10',upper='10',effort='1',velocity='1')
        parent=child
    body=ET.SubElement(root,'link',name='air_demo_carton')
    anchor=ET.SubElement(root,'joint',name='air_demo_anchor',type='fixed')
    ET.SubElement(anchor,'parent',link=parent);ET.SubElement(anchor,'child',link='air_demo_carton')
    for box in data['object_boxes']:
        lo,hi=np.asarray(box['lo']),np.asarray(box['hi'])
        collision=ET.SubElement(body,'collision')
        ET.SubElement(collision,'origin',xyz=' '.join(map(str,(lo+hi)/2)))
        ET.SubElement(ET.SubElement(collision,'geometry'),'box',size=' '.join(map(str,hi-lo)))
    model = CollisionModel(ET.tostring(root, encoding='unicode'), output/'held-model')
    model.bounds.update({'air_demo_'+axis+'_joint':(-10.,10.)for axis in ('x','y','z')})
    for pair in ET.parse(problem.directory/'moveit/robot.srdf').findall('disable_collisions'):
        model.scene.allowed_collision_matrix.set_entry(pair.get('link1'),pair.get('link2'),True)
    for arm in HOLDERS:
        for side in ('left','right'):
            model.scene.allowed_collision_matrix.set_entry('air_demo_carton',
                arm+f'_robotiq_85_{side}_finger_tip_link',True)
    return model


def carton_coordinates(pose):
    roll,pitch,yaw=Rotation.from_matrix(pose[:3,:3]).as_euler('xyz')
    values=[*pose[:3,3],yaw,pitch,roll]
    return {'air_demo_'+axis+'_joint':float(value)
            for axis,value in zip(('x','y','z','yaw','pitch','roll'),values,strict=True)}


def interpolate_pose(a, b, u):
    result=a.copy()
    result[:3,3]=(1-u)*a[:3,3]+u*b[:3,3]
    turn=Rotation.from_matrix(b[:3,:3]@a[:3,:3].T).as_rotvec()
    result[:3,:3]=Rotation.from_rotvec(u*turn).as_matrix()@a[:3,:3]
    return result


def roll_face_pose(pose, dimensions, degrees):
    """Clocking about object Y preserves the opposite wall normal and centre."""
    center=np.eye(4);center[:3,3]=np.asarray(dimensions)/2
    rotation=np.eye(4);rotation[:3,:3]=Rotation.from_euler('y',degrees,degrees=True).as_matrix()
    return pose@center@rotation@np.linalg.inv(center)


def check_state(problem, held, data, state, pose, *, contacts=False):
    if not problem.collision.check(state)[0]:
        if contacts:problem.collision.check(state,contacts=True)
        raise ValueError('real full-opening cell collision')
    world=problem.spheres.world(state)
    distances=[dict(problem.spheres.nearest(world,a,b),arms=[a,b])for a,b in PAIRS]
    nearest=min(distances,key=lambda row:row['clearance_m'])
    gaps=[row['clearance_m']for row in distances]
    if min(gaps)<=problem.cfg['model_margin_m']:
        raise ValueError(f"neighbor envelope gap {min(gaps):.6f}m <=40mm: {nearest['arms']} {nearest['links']}")
    combined=dict(state,**data['nominal_jaws'],**carton_coordinates(pose))
    if not held.check(combined)[0]:
        if contacts:held.check(combined,contacts=True)
        raise ValueError('held carton/body/environment collision')
    return min(gaps)


def polyline_at(points, u):
    points=np.asarray(points)
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1)
    if lengths.sum()<1e-12:return points[0]
    knots=np.r_[0.,np.cumsum(lengths)]/lengths.sum()
    return np.array([np.interp(u,knots,points[:,j])for j in range(points.shape[1])])


def free_route(problem, held, data, start, pose, arm, goals, preferred=None):
    names=joint_names(arm);initial=np.asarray([start[j]for j in names])
    upright=initial.copy();upright[1:]=[-np.pi/2,0.,-np.pi/2,0.,0.]
    reasons=[]
    def preference(q):
        if preferred is None:return np.linalg.norm(q-initial)
        # Preserve the task-demonstrated wrist/elbow branch before shortening
        # the free approach from an unrelated current inspection posture.
        difference=np.arctan2(np.sin(q-preferred),np.cos(q-preferred))
        return np.linalg.norm(difference)
    for goal in sorted(goals,key=preference):
        for route in ([initial,goal],[initial,upright,goal]):
            try:
                for left,right in zip(route,route[1:]):
                    n=max(3,int(np.ceil(np.max(abs(right-left))/.015))+1)
                    for u in np.linspace(0.,1.,n):
                        trial=dict(start,**dict(zip(names,(1-u)*left+u*right)))
                        check_state(problem,held,data,trial,pose)
            except ValueError as error:
                reasons.append(str(error));continue
            return route
    raise ValueError(arm+': no checked direct/upright free route: '+str(sorted(set(reasons))))


def nearest_home(problem, state, arm):
    result=[]
    for joint,wanted in zip(joint_names(arm),(0.,-np.pi/2,0.,-np.pi/2,0.,0.),strict=True):
        lo,hi=problem.collision.bounds[joint]
        values=[wanted+2*np.pi*k for k in range(-2,3)if lo<=wanted+2*np.pi*k<=hi]
        result.append(float(np.clip(min(values,key=lambda q:abs(q-state[joint])),lo+.001,hi-.001)))
    return np.asarray(result)


def compile_draft(args):
    """Retarget all reference phases before requesting any motion review."""
    folder=args.bundle.resolve();data=read(folder/'input.json')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    p=HardwareProblem.__new__(HardwareProblem);p.directory=out/'cell'
    p.cfg=data['config'];p.names=data['names']
    p.description=(folder/'hardware.urdf').read_text()
    p.original_description=(folder/'original.urdf').read_text()
    p.collision=CollisionModel(p.description,p.directory/'moveit')
    shutil.copyfile(folder/'hardware.srdf',p.directory/'moveit/robot.srdf')
    for pair in ET.parse(folder/'hardware.srdf').findall('disable_collisions'):
        p.collision.scene.allowed_collision_matrix.set_entry(pair.get('link1'),pair.get('link2'),True)
    p.spheres=SphereModel(p.description,p.names,p.cfg['sphere_spacing_m'])
    p.chains={a:Chain(p.original_description,'world',a+'_tool0')for a in p.names}
    solver=ObjectTransport.__new__(ObjectTransport);solver.problem=p;solver.collision=p.collision
    solver.arms=(*HOLDERS,WORKER);solver.tcp_offsets={a:np.eye(4)for a in solver.arms}
    offsets={a:np.asarray(v)for a,v in data['offsets'].items()}
    reference=(folder/'reference.urdf').read_text()
    chains={a:Chain(reference,'world',a+'_tool0')for a in solver.arms}
    group=data['reference_group']['object_to_tcp']
    initial=dict(data['reference_initial'])
    first=data['phases'][0];initial.update(zip(first['joint_names'],first['points'][0]['positions']))
    reference_origin=chains[HOLDERS[0]].forward(initial)@np.linalg.inv(group[HOLDERS[0]])
    hypothetical=bool(args.regrasp_reference_branch)
    if hypothetical:
        # Only a proposed future regrasp. These joint values are never an
        # executable continuation from the measured suspended-carton start.
        proposed=dict(data['start'])
        for arm in HOLDERS:
            target=np.asarray(data['pose'])@offsets[arm]
            names=joint_names(arm)
            seed=np.asarray([initial[j]for j in names])
            sign=None if args.regrasp_wrist_signs is None else args.regrasp_wrist_signs[HOLDERS.index(arm)]
            if sign is not None and np.sign(seed[4])!=sign:
                seed[3]+=np.pi;seed[4]*=-1;seed[5]+=np.pi
            q=solve_near(p,arm,proposed,target,seed)
            if sign is not None and np.sign(q[4])!=sign:
                raise ValueError(arm+': proposed wrist branch did not converge')
            proposed.update(zip(names,q))
        data=dict(data,start=proposed)
    transform=np.asarray(data['pose'])@np.linalg.inv(reference_origin)
    canonical=np.eye(4);canonical[:3,3]=args.work_offset
    high_ref=dict(initial,**dict(zip(first['joint_names'],first['points'][-1]['positions'])))
    high=chains[HOLDERS[0]].forward(high_ref)@np.linalg.inv(group[HOLDERS[0]])
    align=dict(id='align_reference',joint_names=[],points=[dict(positions=[])for _ in range(17)])
    restore=dict(align,id='restore_current_pose')
    park=dict(align,id='park_left_rear')
    phases=[park,first,align]
    for item in data['phases'][1:-1]:
        if item['id']in ('present_z_min','present_y_min','return_from_y_min'):
            phases.append(dict(align,id='clear_worker_before_'+item['id']))
        phases.append(item)
        if item['id']in ('present_z_min','present_y_min'):
            phases.append(dict(align,id='enter_worker_after_'+item['id']))
    phases.extend([restore,data['phases'][-1]])
    state=dict(data['start']);held=moving_model(p,data,out)
    report=dict(success=False,executable=False,phase='COARSE_HARDWARE_DRAFT',
        robot_commands_sent=False,physical_tool=False,virtual_tool_length_m=.300,
        required_followup='Exact controller interpolation, speed, fixed-grip, task-shape and review binding',
        model_signature=data['model_signature'],phases=[])
    report['work_offset_m']=args.work_offset
    report['opposite_roll_deg']=args.opposite_roll_deg
    report['start_kind']='HYPOTHETICAL_REGRASP_NOT_CURRENT' if hypothetical else 'MEASURED_CURRENT_GRASP'
    report['start']=data['start']
    report['opposite_direct']=args.opposite_direct
    report['opposite_excursion_m']=args.opposite_excursion
    report['opposite_offset_m']=args.opposite_offset
    report['opposite_pose_center_xyz_rpy_deg']=args.opposite_pose
    report['regrasp_wrist_signs']=args.regrasp_wrist_signs
    write(out/'result.json',report)
    refstate=dict(initial);minimum=float('inf');opposite=False;opposite_adjust=np.eye(4)
    try:
        for phase in phases:
            print('Checking',phase['id'],flush=True)
            positions=np.asarray([point['positions']for point in phase['points']])
            # A short coarse rejection pass; never an execution qualification.
            count=max(3,min(len(positions),args.samples))
            indices=np.unique(np.linspace(0,len(positions)-1,count).astype(int))
            clearing=phase['id'].startswith('clear_worker_before_')
            entering=phase['id'].startswith('enter_worker_after_')
            connector=clearing or entering or phase['id'] in ('worker_to_drawing_start','reverse_worker_to_drawing_start')
            box_transition=phase['id'].startswith(('present_','return_from_'))
            worker_start=np.asarray([state[j]for j in joint_names(WORKER)])
            worker_goal=None
            worker_route=None
            parking=phase['id']=='park_left_rear'
            rear_route=None
            if parking:
                rear_route=free_route(p,held,data,state,np.asarray(data['pose']),'left_rear',
                                      [nearest_home(p,state,'left_rear')])
            if connector:
                preferred=None
                if clearing:
                    worker_goal=nearest_home(p,state,WORKER)
                    solutions=[worker_goal]
                elif phase['id'].startswith('reverse'):
                    worker_goal=np.asarray([data['start'][j]for j in joint_names(WORKER)])
                    solutions=[worker_goal]
                else:
                    endpoint=dict(refstate,**dict(zip(phase['joint_names'],positions[-1])))
                    preferred=np.asarray([endpoint[j]for j in joint_names(WORKER)])
                    target=canonical@chains[WORKER].forward(endpoint)
                    if opposite:target=opposite_adjust@target
                    bounds=np.asarray([p.collision.bounds[j]for j in joint_names(WORKER)])
                    guesses=[worker_start,np.asarray([endpoint[j]for j in joint_names(WORKER)])]
                    guesses.extend(np.random.default_rng(17).uniform(bounds[:,0],bounds[:,1],(12,6)))
                    solutions=[]
                    for guess in guesses:
                        try:q=solve_near(p,WORKER,state,target,guess)
                        except ValueError:continue
                        for k in range(6):
                            turns=[q[k]+2*np.pi*n for n in range(-2,3)
                                   if bounds[k,0]<=q[k]+2*np.pi*n<=bounds[k,1]]
                            q[k]=min(turns,key=lambda v:abs(v-worker_start[k]))
                        if not any(np.max(abs(q-other))<1e-4 for other in solutions):solutions.append(q)
                    if not solutions:raise ValueError('Worker drawing prepose is unreachable in all14 bounded IK attempts')
                # Test whole free transitions, including alternatives above the
                # table. A closest endpoint alone is not a valid task branch.
                fixed_pose=p.chains[HOLDERS[0]].forward(state)@np.linalg.inv(offsets[HOLDERS[0]])
                worker_route=free_route(p,held,data,state,fixed_pose,WORKER,solutions,preferred)
            rows=[]
            transition_start=p.chains[HOLDERS[0]].forward(state)@np.linalg.inv(offsets[HOLDERS[0]])
            transition_goal=None
            if phase['id']=='present_y_min':
                endpoint=dict(refstate,**dict(zip(phase['joint_names'],positions[-1])))
                goal=canonical@chains[HOLDERS[0]].forward(endpoint)@np.linalg.inv(group[HOLDERS[0]])
                adjusted=roll_face_pose(goal,data['dimensions_m'],args.opposite_roll_deg)
                adjusted[:3,3]+=np.asarray(args.opposite_offset)
                if args.opposite_pose is not None:
                    adjusted=np.eye(4)
                    adjusted[:3,:3]=Rotation.from_euler('xyz',args.opposite_pose[3:],degrees=True).as_matrix()
                    adjusted[:3,3]=np.asarray(args.opposite_pose[:3])-adjusted[:3,:3]@(np.asarray(data['dimensions_m'])/2)
                opposite_adjust=adjusted@np.linalg.inv(goal)
                transition_goal=opposite_adjust@goal
            if phase['id']=='return_from_y_min':
                endpoint=dict(refstate,**dict(zip(phase['joint_names'],positions[-1])))
                transition_goal=canonical@chains[HOLDERS[0]].forward(endpoint)@np.linalg.inv(group[HOLDERS[0]])
            for index in indices:
                refstate.update(zip(phase['joint_names'],positions[index]))
                mapping=transform if phase['id']in ('lift','set_down') else canonical
                wanted=mapping@chains[HOLDERS[0]].forward(refstate)@np.linalg.inv(group[HOLDERS[0]])
                worker_target=mapping@chains[WORKER].forward(refstate)
                if opposite and phase['id']!='return_from_y_min':
                    wanted=opposite_adjust@wanted;worker_target=opposite_adjust@worker_target
                if phase['id']in ('present_y_min','return_from_y_min'):
                    fraction=float(index)/(len(positions)-1)
                    if phase['id']=='return_from_y_min':fraction=1-fraction
                    wanted=roll_face_pose(wanted,data['dimensions_m'],fraction*args.opposite_roll_deg)
                    wanted[:3,3]+=fraction*np.asarray(args.opposite_offset)
                    if args.opposite_direct:
                        u=float(index)/(len(positions)-1)
                        wanted=interpolate_pose(transition_start,transition_goal,u)
                        wanted[:3,3]+=np.sin(np.pi*u)**2*np.asarray(args.opposite_excursion)
                if parking:wanted=np.asarray(data['pose'])
                alignment=phase['id']in ('align_reference','restore_current_pose')
                if alignment:
                    endpoints=(transform@high,canonical@high)
                    if phase['id']=='restore_current_pose':endpoints=endpoints[::-1]
                    wanted=interpolate_pose(*endpoints,float(index)/(len(positions)-1))
                    worker_target=p.chains[WORKER].forward(data['start'])
                if phase['id'] in ('lift','set_down'):
                    worker_target=p.chains[WORKER].forward(data['start'])
                # The shared Newton solver accepts a separate absolute worker target.
                solver.offsets=dict(offsets,**{WORKER:np.linalg.inv(wanted)@worker_target})
                solver.arms=HOLDERS if connector or alignment or parking or box_transition else (*HOLDERS,WORKER)
                report['checking']=dict(phase=phase['id'],source_index=int(index),object_pose=wanted.tolist(),
                                        worker_target=worker_target.tolist())
                try:
                    state=solver.solve(wanted,state)
                except ValueError:
                    # Near a wrist singularity use the existing bounded
                    # least-squares IK; do not jump to a different branch.
                    replacement=dict(state)
                    for arm in solver.arms:
                        names=joint_names(arm);seed=np.asarray([state[j]for j in names])
                        target=wanted@solver.offsets[arm]
                        q=solve_near(p,arm,state,target,seed)
                        for k,joint in enumerate(names):
                            lo,hi=p.collision.bounds[joint]
                            choices=[q[k]+2*np.pi*n for n in range(-2,3)if lo<=q[k]+2*np.pi*n<=hi]
                            q[k]=min(choices,key=lambda value:abs(value-seed[k]))
                        if max(abs(q-seed))>.5:raise ValueError(arm+': continuation jump')
                        replacement.update(zip(names,q))
                    state=replacement
                if connector:
                    fraction=float(index)/(len(positions)-1)
                    state.update(zip(joint_names(WORKER),polyline_at(worker_route,fraction)))
                if parking:
                    state.update(zip(joint_names('left_rear'),polyline_at(rear_route,float(index)/(len(positions)-1))))
                minimum=min(minimum,check_state(p,held,data,state,wanted,contacts=True))
                rows.append(dict(source_index=int(index),positions=dict(state),object_pose=wanted.tolist()))
            report['phases'].append(dict(id=phase['id'],samples=rows,
                worker_route=None if worker_route is None else np.asarray(worker_route).tolist(),
                rear_route=None if rear_route is None else np.asarray(rear_route).tolist()))
            if phase['id']=='present_y_min':opposite=True
            if phase['id']=='return_from_y_min':opposite=False
            write(out/'result.json',report)
        report.update(success=True,phase='COARSE_HARDWARE_DRAFT_PASSED',minimum_arm_gap_m=minimum)
    except Exception as error:
        report.update(error=str(error),last_state=state,phase='COARSE_HARDWARE_DRAFT_REJECTED')
        print('REJECTED',error,flush=True)
    write(out/'result.json',report)
    return 0 if report['success'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='operation',required=True)
    p=commands.add_parser('pack')
    for key in ('grasp-run','observations','reference','output'):p.add_argument('--'+key,type=Path,required=True)
    p=commands.add_parser('draft')
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--samples',type=int,default=17)
    p.add_argument('--work-offset',type=float,nargs=3,default=[0.,0.,0.])
    p.add_argument('--opposite-roll-deg',type=float,default=0.)
    p.add_argument('--regrasp-reference-branch',action='store_true')
    p.add_argument('--opposite-direct',action='store_true')
    p.add_argument('--opposite-excursion',type=float,nargs=3,default=[0.,0.,0.])
    p.add_argument('--opposite-offset',type=float,nargs=3,default=[0.,0.,0.])
    p.add_argument('--opposite-pose',type=float,nargs=6)
    p.add_argument('--regrasp-wrist-signs',type=int,nargs=2,choices=(-1,1))
    a=parser.parse_args()
    if a.operation=='pack':pack(a)
    else:raise SystemExit(compile_draft(a))

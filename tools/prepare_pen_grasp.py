#!/usr/bin/env python3
"""ROSmini-only pen perception and complete single-arm approach/entry/lift compilation."""
import argparse
import hashlib
import importlib
import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation

from pen_grasp_vision import perceive,transform
from carton_camera_session import validate_session
from uwa_cell_calibration.model import CollisionModel,set_origin
from uwa_cell_control.parallel_scan import collision_signature
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import dump,joint_names
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.carton_paths import solve_near,pose_goal
from uwa_cell_tasks.reviewed_carton import speed_envelope,retime,prove_group
from uwa_cell_tasks.timing import interpolation_peaks

REPO=Path(__file__).resolve().parents[1]
ARM='left_rear'


def task_scene(problem, adapter, definition, directory, *, tool_adapter=None):
    """Exact CAD dock/adapter plus a conservative shaft; only intended pad/dock contacts excluded."""
    root=ET.fromstring(problem.description)
    def link(name,parent,T,shapes):
        body=ET.SubElement(root,'link',name=name)
        joint=ET.SubElement(root,'joint',name=name+'_mount',type='fixed')
        ET.SubElement(joint,'parent',link=parent);ET.SubElement(joint,'child',link=name);set_origin(joint,T)
        for kind,value,offset in shapes:
            for tag in ('collision','visual'):
                member=ET.SubElement(body,tag);ET.SubElement(member,'origin',xyz=' '.join(map(str,offset)))
                geometry=ET.SubElement(member,'geometry')
                if kind=='mesh':ET.SubElement(geometry,'mesh',filename=Path(value).resolve().as_uri())
                else:ET.SubElement(geometry,'cylinder',radius=str(value[0]),length=str(value[1]))
    meshes=REPO/'uwa_cell_description/assets/pen_grasp_v1'
    dock=adapter.copy();dock[:3,3]+=adapter[:3,2]*definition['mount']['dock_base_z_m']
    link('pen_task_dock','world',dock,[('mesh',meshes/'dock.stl',[0,0,0])])
    parent=ARM+'_tool0' if tool_adapter is not None else 'world'
    pose=tool_adapter if tool_adapter is not None else adapter
    link('pen_task_adapter',parent,pose,[('mesh',meshes/f'adapter-{i}.stl',[0,0,0]) for i in (1,2)])
    link('pen_task_shaft','pen_task_adapter',np.eye(4),[('cylinder',(.0105,.125),[0,0,-.0165])])
    description=ET.tostring(root,encoding='unicode')
    model=CollisionModel(description,directory/'moveit')
    robot_links=[x.get('name') for x in ET.fromstring(problem.description).findall('link')]
    # Preserve precisely the existing full-opening-envelope internal exclusions.
    for arm in problem.names:
        members=[n for n in robot_links if n.startswith(arm+'_robotiq_85_')]
        for a,b in itertools.combinations(members,2):model.scene.allowed_collision_matrix.set_entry(a,b,True)
    for body in ('pen_task_adapter','pen_task_shaft','pen_task_dock'):
        for name in robot_links:
            model.scene.allowed_collision_matrix.set_entry(body,name,False)
    for side in ('left','right'):
        model.scene.allowed_collision_matrix.set_entry('pen_task_adapter',ARM+f'_robotiq_85_{side}_finger_tip_link',True)
    model.scene.allowed_collision_matrix.set_entry('pen_task_dock','left_table_plate',True)
    # Dock/pen overlap belongs to the intended insertion/withdrawal contact.
    model.scene.allowed_collision_matrix.set_entry('pen_task_dock','pen_task_adapter',True)
    model.scene.allowed_collision_matrix.set_entry('pen_task_dock','pen_task_shaft',True)
    model.scene.allowed_collision_matrix.set_entry('pen_task_adapter','pen_task_shaft',True)
    # The RRT worker reads SRDF rather than the in-memory matrix.
    srdf_path=directory/'moveit/robot.srdf';srdf=ET.fromstring(srdf_path.read_text())
    pairs={tuple(sorted((x.get('link1'),x.get('link2')))) for x in srdf.findall('disable_collisions')}
    allowed=[]
    for arm in problem.names:
        allowed.extend(itertools.combinations([n for n in robot_links if n.startswith(arm+'_robotiq_85_')],2))
    allowed.extend([('pen_task_dock','left_table_plate'),('pen_task_dock','pen_task_adapter'),
                    ('pen_task_dock','pen_task_shaft'),('pen_task_adapter','pen_task_shaft')])
    allowed.extend(('pen_task_adapter',ARM+f'_robotiq_85_{side}_finger_tip_link') for side in ('left','right'))
    for a,b in allowed:
        if tuple(sorted((a,b))) not in pairs:
            ET.SubElement(srdf,'disable_collisions',link1=a,link2=b,reason='ExistingOpeningEnvelopeOrTaskContact')
    srdf_path.write_text(ET.tostring(srdf,encoding='unicode'))
    return model,description


def preview_description(xml):
    tree=ET.fromstring(xml)
    for link in tree.findall('link'):
        name=link.get('name')
        if name in ('pen_task_adapter','pen_task_shaft') or 'marker_station' in name or 'cos_marker_docked' in name:
            for visual in list(link.findall('visual')):link.remove(visual)
    for mesh in tree.iter('mesh'):
        file=Path(mesh.get('filename').removeprefix('file://'))
        if file.is_relative_to(REPO/'uwa_cell_description'):
            uri='package://uwa_cell_description/'+str(file.relative_to(REPO/'uwa_cell_description'))
        elif '/share/' in str(file):uri='package://'+str(file).rsplit('/share/',1)[1]
        else:raise ValueError('Preview mesh has no installed package binding: '+str(file))
        mesh.set('filename',uri)
    return ET.tostring(tree,encoding='unicode')


def linear_path(problem,start,target,goal,height):
    q=np.asarray(goal);paths=[q.copy()]
    state=dict(start);names=joint_names(ARM)
    for z in np.linspace(0,height,max(2,int(np.ceil(height/.003)))+1)[1:]:
        pose=target.copy();pose[2,3]+=z
        next_q=solve_near(problem,ARM,state,pose,q)
        if np.max(abs(next_q-q))>.15:raise ValueError('Pen Cartesian path changes IK branch')
        paths.append(next_q.copy());q=next_q
    return np.asarray(paths)


def smooth_trajectory(path,envelope,cfg):
    """One continuous C2 law, no stop at each Cartesian IK knot or observation slowdown."""
    spline=CubicSpline(np.linspace(0,1,len(path)),path,bc_type='natural')
    # Composition with the quintic progress law has zero end speed/acceleration.
    u=np.linspace(0,1,201);s=10*u**3-15*u**4+6*u**5
    ds=30*u**2-60*u**3+30*u**4;dds=60*u-180*u**2+120*u**3
    q=spline(s);v=spline(s,1)*ds[:,None];a=spline(s,2)*ds[:,None]**2+spline(s,1)*dds[:,None]
    duration=max(.1,float(np.max(abs(v)))/cfg['command_velocity_limit_rad_s'],
                 np.sqrt(float(np.max(abs(a)))/cfg['acceleration_limit_rad_s2']))
    for _ in range(6):
        points=[dict(time=round(float(t*duration)*1e9)/1e9,positions=x.tolist(),velocities=(y/duration).tolist(),
                     accelerations=(z/duration**2).tolist()) for t,x,y,z in zip(u,q,v,a)]
        trajectory=retime(dict(points=points,waypoints=path.tolist()),ARM,envelope)
        acceleration=float(np.max(interpolation_peaks(trajectory,2)))
        if acceleration<=cfg['acceleration_limit_rad_s2']*(1+1e-10):return trajectory
        duration=trajectory['duration_s']*np.sqrt(acceleration/cfg['acceleration_limit_rad_s2'])
    raise ValueError('Pen trajectory timing failed')


def portable(plan,remote):
    plan.update(inventory=remote['inventory'],hardware_binding=remote['hardware_binding'],
        model_signature=remote['model_signature'],mesh_sha256=remote['mesh_sha256'],execution_mode='hardware',layout_path=None,
        compiled_command_limit_rad_s=remote['config']['command_velocity_limit_rad_s'],
        portable_binding=dict(exact_planner_modules=remote['modules'],geometry_changed=False,
            user_authorization='Pen grasp: left_rear only; existing command limits; explicit motion and contact reviews'))
    return plan


def compile_plan(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    definition=json.loads(args.definition.read_text());remote=json.loads(args.context.read_text());snapshot=json.loads(args.snapshot.read_text())
    if definition['arm']!=ARM or definition['program_id']!='pen-left-rear-v1':raise ValueError('Unexpected pen arm or program')
    for name,digest in remote['modules'].items():
        if hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()!=digest:
            raise ValueError('Planner differs from N100: '+name)
    problem=HardwareProblem(out/'base',remote['config'],REPO/'config/hardware_inventory.yaml')
    tree=ET.fromstring(problem.description)
    for mesh in tree.iter('mesh'):
        file=Path(mesh.get('filename').removeprefix('file://'));mesh.set('filename','sha256:'+hashlib.sha256(file.read_bytes()).hexdigest())
    if (collision_signature(ET.tostring(tree,encoding='unicode'))!=remote['canonical_collision_signature']
            or sorted(problem.spheres.geometry.assets.values())!=sorted(remote['mesh_sha256'].values())):
        raise ValueError('ROSmini and N100 collision models differ')
    camera=json.loads(args.camera.read_text());session=validate_session(json.loads(args.session.read_text()),args.camera)
    T_world_camera=Chain(problem.original_description,'world','right_charuco').forward({})@np.linalg.inv(transform(session['T_camera_board']))
    pose=perceive(args.image,camera,T_world_camera,definition,out/'perception')
    adapter=transform(pose['T_world_adapter']);state=dict(snapshot['start'])
    tip=adapter[:3,3]+adapter[:3,2]*definition['mount']['pen_tip_z_m']
    table=Chain(problem.original_description,'world','left_table_top').forward({})
    # Seated CAD tip should be10.5mm above its supporting tabletop.
    tip_table=np.linalg.inv(table)@np.r_[tip,1]
    if abs(tip_table[2]-.0105)>.01:raise ValueError(f'Pen seating/CAD/table inconsistency: nominal tip height {tip_table[2]*1000:.1f} mm, expected10.5mm')
    scene,scene_xml=task_scene(problem,adapter,definition,out/'static')
    base_collision=problem.collision;problem.collision=scene
    problem.directory=out/'static'
    problem.chains={ARM:Chain(problem.original_description,'world',ARM+'_tool0')}
    gripper=Chain(problem.original_description,ARM+'_tool0',ARM+'_robotiq_85_base_link').forward({})
    down=-np.array([0.,0.,1.]);x=adapter[:3,0].copy();x[2]=0;x/=np.linalg.norm(x)
    envelope=speed_envelope(problem,[ARM],remote['config']['command_velocity_limit_rad_s'],args.tcp_cap)
    trials=[];chosen=None
    for sign in (1,-1):
        R=np.column_stack([sign*x,np.cross(down,sign*x),down]);base=np.eye(4);base[:3,:3]=R
        base[:3,3]=(adapter[:3,:3]@definition['mount']['grasp_center_m']+adapter[:3,3]
                        -R@np.array([0,0,definition['gripper_tcp_from_base_m']]))
        contact=base@np.linalg.inv(gripper)
        try:
            goals=problem.ik(ARM,state,pose_goal(ARM,contact))
            for goal in goals:
                try:
                    entry_up=linear_path(problem,state,contact,goal,definition['pregrasp_m'])
                    entry=smooth_trajectory(entry_up[::-1],envelope,remote['config'])
                    request=dict(schema_version=1,start=state,goals={ARM:entry_up[-1].tolist()})
                    approach=problem.plan(request,'rrtconnect',seed=2411)
                    if not approach['success']:raise ValueError(approach.get('error','Approach failed'))
                    approach['trajectory']=retime(approach['trajectory'],ARM,envelope)
                    endpoint=dict(state,**dict(zip(joint_names(ARM),goal)))
                    prestate=dict(state,**dict(zip(joint_names(ARM),entry_up[-1])))
                    # Moving pen is attached at exactly the reviewed contact pose.
                    carried,carried_xml=task_scene(problem,adapter,definition,out/'carried',tool_adapter=np.linalg.inv(contact)@adapter)
                    old=problem.collision;problem.collision=carried
                    lift_path=linear_path(problem,endpoint,contact,goal,definition['lift_m'])
                    lift=smooth_trajectory(lift_path,envelope,remote['config'])
                    problem.collision=old
                    phases=[('approach',state,approach['trajectory'],scene),('entry',prestate,entry,scene),('lift',endpoint,lift,carried)]
                    proofs={}
                    for name,start,traj,collision in phases:
                        problem.collision=base_collision
                        proof,error=prove_group(problem,start,{ARM:traj},remote['config']['command_velocity_limit_rad_s'],collision)
                        if error:raise ValueError(name+': '+error)
                        proofs[name]=proof
                    chosen=(phases,approach,contact,carried_xml,proofs)
                    break
                except ValueError as error:trials.append(str(error))
                finally:problem.collision=scene
            if chosen:break
        except ValueError as error:trials.append(str(error))
    dump(out/'search.json',dict(attempts=trials))
    if not chosen:raise ValueError('No complete collision-checked pen approach/entry/lift: '+'; '.join(trials[-4:]))
    phases,approach,contact,carried_xml,proofs=chosen
    segments=[]
    for name,start,traj,collision in phases:
        problem.collision=base_collision
        proof=proofs[name]
        request=dict(schema_version=1,start=start,goals={ARM:traj['points'][-1]['positions']},selected=[ARM],joint_names=joint_names(ARM))
        plan=portable(dict(schema_version=1,success=True,hardware_plan=True,config=remote['config'],request=request,
            trajectory=traj,metrics=dict(full_cell_collision_checked=True,task_objects_checked=True),
            coordination='single_arm',proof=proof),remote)
        file=out/(name+'.json');dump(file,plan)
        segments.append(dict(phase=name,arm=ARM,plan=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),duration_s=traj['duration_s']))
    # Scene contains the actual measured dock and pen, for operator RViz playback.
    preview_xml=preview_description(scene_xml)
    (out/'preview.urdf').write_text(preview_xml)
    sequence=dict(kind='pen_holder_grasp',schema_version=1,arm=ARM,segments=segments,start=state,
        command_velocity_limit_rad_s=remote['config']['command_velocity_limit_rad_s'],tcp_limit_m_s=args.tcp_cap,
        scene_session=snapshot['area_session'],T_world_adapter=adapter.tolist(),T_world_contact_tool0=contact.tolist(),
        definition=definition,definition_sha256=hashlib.sha256(args.definition.read_bytes()).hexdigest(),
        perception=pose,robot_description=preview_xml,total_duration_s=sum(s['duration_s'] for s in segments),
        pen=dict(arm=ARM,T_world_adapter=adapter.tolist(),T_tool0_adapter=(np.linalg.inv(contact)@adapter).tolist(),
                 meshes=['package://uwa_cell_description/assets/pen_grasp_v1/adapter-1.stl',
                         'package://uwa_cell_description/assets/pen_grasp_v1/adapter-2.stl']),
        qualification=definition['mount']['qualification'],robot_commands_sent=False)
    dump(out/'sequence.json',sequence)
    print(json.dumps(dict(success=True,output=str(out),duration_s=sequence['total_duration_s'])))


def inspect_image(args):
    from uwa_cell_gazebo.configuration import render_description
    from uwa_cell_motion.common import load_layout,default_layout_path
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    xml,_=render_description(load_layout(default_layout_path()),out/'display-model')
    session=validate_session(json.loads(args.session.read_text()),args.camera)
    frame=Chain(xml,'world','right_charuco').forward({})@np.linalg.inv(transform(session['T_camera_board']))
    pose=perceive(args.image,json.loads(args.camera.read_text()),frame,json.loads(args.definition.read_text()),out/'perception')
    print(json.dumps(dict(success=True,inspection_only=True,reprojection_rms_px=pose['reprojection_rms_px'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('definition','camera','session','image','output'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('snapshot','context'):p.add_argument('--'+name,type=Path)
    p.add_argument('--tcp-cap',type=float)
    p.add_argument('--inspect-only',action='store_true')
    args=p.parse_args()
    if args.inspect_only:inspect_image(args)
    else:
        if args.snapshot is None or args.context is None or args.tcp_cap is None:p.error('Planning needs snapshot, context and TCP cap')
        compile_plan(args)

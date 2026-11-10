"""Reviewed single-arm real acquisition; simulation backend remains untouched."""
from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np

from uwa_cell_gazebo.configuration import joint_names
from uwa_cell_calibration.planner import generate_plan,timed_path
from uwa_cell_calibration.storage import atomic_json
from .parking import digest,save_plan


def acquisition_plan(model,layout,profiles,rid,start,sources,missing,count,directory,layout_file,progress=lambda p:None):
    if not 30<=count<=40:raise ValueError('Hardware acquisition supports30–40 new poses')
    if missing:raise ValueError('Observe or explicitly declare all stationary arm poses before planning')
    camera=layout['robots'][rid]['tools'];width,height=camera['camera_width'],camera['camera_height']
    focal=width/(2*np.tan(camera['camera_horizontal_fov']/2))
    nominal={'k':[[focal,0,width/2],[0,focal,height/2],[0,0,1]],'width':width,'height':height}
    # This K bounds proposed views only. Real calibration fitting never receives it.
    proposed=generate_plan(model,layout,start,{rid:nominal},[rid],count,progress)[rid]
    state=dict(start);segments=[];combined=[];tool_path=[];offset=0.
    from uwa_cell_gazebo.charuco_views import Chain
    tool=Chain(model.description,'world',rid+'_tool0')
    for index,pose in enumerate(proposed['poses']):
        path=timed_path(model,rid,state,pose['joints'],velocity=.05,acceleration=.10)
        segments.append({'sample_id':f'sample_{index+1:03d}','role':pose['role'],
                         'target':pose['joints'],'points':path})
        for point in path:
            absolute=dict(point,time=offset+point['time'])
            if combined and absolute['time']<=combined[-1]['time']:continue
            combined.append(absolute)
            q=dict(state,**dict(zip(joint_names(rid),point['positions'])))
            tool_path.append(tool.forward(q)[:3,3].tolist())
        offset+=path[-1]['time']+2.
        combined.append(dict(path[-1],time=offset));tool_path.append(tool_path[-1])
        state.update(zip(joint_names(rid),pose['joints']))
    plan={'schema_version':1,'mode':'hardware','arm':rid,'start':start,'state_sources':sources,
          'segments':segments,'layout':layout,'layout_file':str(Path(layout_file).resolve()),
          'inventory_fingerprint':digest(profiles),'description':model.description,
          'planning_only_camera_model':dict(nominal,source='nominal FOV; never passed to intrinsic/hand-eye fit'),
          'new_observations':count,'automatic_return':False,'duration_motion_s':sum(s['points'][-1]['time'] for s in segments)}
    plan['fingerprint']=digest(plan)
    directory=Path(directory);atomic_json(directory/'batch.json',plan)
    preview={'purpose':'ChArUco acquisition sequence','arm':rid,'joint_names':joint_names(rid),
             'start':start,'target':segments[-1]['target'],'points':combined,'duration':offset,
             'tool_path_world':tool_path,'nominal_camera_target_world':None,
             'method':'full MoveIt collision sweep per segment; captures while stationary',
             'velocity_limit':.05,'acceleration_limit':.10,'collision_samples':len(combined)}
    preview=save_plan(directory,preview,model,layout,profiles,sources,missing,'hardware')
    preview['executable']=False;preview.pop('fingerprint');preview['fingerprint']=digest(preview)
    atomic_json(directory/'plan.json',preview)  # Only batch-aware execution may capture/run it.
    return plan


def validate_batch(plan,profiles,current_layout):
    value=dict(plan);fingerprint=value.pop('fingerprint',None)
    if fingerprint!=digest(value):raise ValueError('Acquisition plan changed')
    if plan.get('mode')!='hardware' or plan.get('schema_version')!=1:raise ValueError('Wrong acquisition mode/schema')
    if plan['inventory_fingerprint']!=digest(profiles) or digest(plan['layout'])!=digest(current_layout):
        raise ValueError('Inventory or cell geometry changed; regenerate acquisition plan')
    if any(s not in ('live_joint_states','manual_pendant','user_nominal_home') for s in plan['state_sources'].values()):
        raise ValueError('Hardware acquisition requires measured/declared real states')


def acquire(args):
    import rclpy
    from match_ur_hardware.operations import switch
    from match_ur_hardware.trajectory import execute_trajectory
    from match_ur_hardware.profiles import load_profiles
    from uwa_cell_gazebo.configuration import load_layout
    from .park_arm import node_for,JointObserver
    from .parking import make_model
    from .handeye_hardware import capture_observation
    from .wrist_camera import WristCamera
    plan=json.loads(Path(args.batch).read_text());profiles=load_profiles(args.inventory);rid=plan['arm']
    directory=Path(args.session).resolve();metadata=json.loads((directory/'session.json').read_text())
    if metadata['robot_id']!=rid or metadata['mode']!='hardware':raise ValueError('Wrong image session')
    node=node_for('hardware');completed=False
    observer=JointObserver(node,profiles,[r for r,s in plan['state_sources'].items() if s=='live_joint_states'],'hardware')
    try:
        model,layout=make_model(load_layout(plan['layout_file']),profiles,directory/'acquisition_model')
        validate_batch(plan,profiles,layout)
        if metadata['layout_fingerprint']!=digest(layout):raise ValueError('Session model changed')
        current=observer.sample()
        for r,s in plan['state_sources'].items():
            if s=='live_joint_states':
                if r not in current:raise ValueError(r+': no live joint data')
                if max(abs(q-plan['start'][j]) for q,j in zip(current[r]['positions'],joint_names(r)))>.01:
                    raise ValueError(r+': start changed; regenerate acquisition plan')
        def guard():observer.guard(plan,require_program_link=True)
        guard();camera=WristCamera(profiles[rid]['ip'])
        first=json.loads((directory/'records/sample_000.json').read_text())
        settings=camera.settings()
        if settings['focusAuto'] or settings['focus']!=first['camera_settings']['focus']:
            raise ValueError('Camera focus differs from first observation')
        for segment in plan['segments']:
            if (directory/'records'/(segment['sample_id']+'.json')).exists():
                raise ValueError('Existing observation; create a new reviewed acquisition instead of overwriting')
        for segment in plan['segments']:
            observer.sample(.2);guard()
            live=dict(plan['start'])
            for r,record in observer.received.items():live.update(zip(joint_names(r),record['positions']))
            q0=[live[j] for j in joint_names(rid)]
            if max(abs(np.array(q0)-segment['points'][0]['positions']))>.01:
                raise ValueError('Segment start changed; stop without an unchecked connection')
            for point in segment['points']:
                q=dict(live,**dict(zip(joint_names(rid),point['positions'])))
                if not model.check(q)[0]:raise ValueError('Current full-cell segment collision check failed')
            observer.sample(.2);guard()
            print(json.dumps({'phase':'MOVING','sample_id':segment['sample_id'],'role':segment['role']}),flush=True)
            execute_trajectory(node,profiles[rid],segment['points'],mock=False,guard=guard)
            observer.sample(.4);guard()
            if max(abs(np.array(observer.received[rid]['positions'])-segment['target']))>.03:
                raise ValueError('Goal error exceeds0.03rad')
            record=capture_observation(camera,node,observer,model,layout,rid,directory/'records',
                                       segment['sample_id'],segment['role'])
            guard()
            print(json.dumps({'phase':'CAPTURED','sample_id':segment['sample_id'],
                              'corners':record['corners'],'role':record['role']}),flush=True)
        completed=True
        print(json.dumps({'phase':'ACQUISITION_COMPLETE','new_observations':len(plan['segments'])}),flush=True)
    finally:
        if not completed:
            try:switch(node,profiles[rid])
            except Exception as error:print('Could not confirm controller deactivation: '+str(error),flush=True)
        observer.close();node.destroy_node();rclpy.shutdown()

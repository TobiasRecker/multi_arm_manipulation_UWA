"""Reviewed single-arm real acquisition; simulation backend remains untouched."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from uwa_cell_gazebo.configuration import joint_names
from uwa_cell_calibration.planner import generate_plan,timed_path
from uwa_cell_calibration.storage import atomic_json
from .parking import digest,save_plan
from .hardware_parallel import DIAGONAL,independent_arm,configure_model


def planning_camera(layout,rid,*,capture_source=None,focus=None):
    camera=layout['robots'][rid]['tools'];width,height=camera['camera_width'],camera['camera_height']
    if capture_source=='wrist_hd_service':
        from .wrist_hd import HD_SIZE
        width,height=HD_SIZE
        focal=width/(2*np.tan(camera['camera_horizontal_fov']/2))
        return {'k':[[focal,0,width/2],[0,focal,height/2],[0,0,1]],'d':[0.]*5,'width':width,'height':height,
                'required_focus':focus,'focusAuto':False,'planned_capture_source':capture_source,
                'source':'nominal native-HD FOV proxy for planning only; no VGA intrinsics copied and never a fit input'}
    measured=layout.get('calibration',{}).get('robots',{}).get(rid,{}).get('camera')
    if measured:
        status=layout['calibration']['robots'][rid].get('quality_status',{}).get('intrinsics','passed')
        return {'k':measured['camera_matrix'],'d':measured['distortion'],'width':width,'height':height,
                'required_focus':measured['focus'],'focusAuto':False,
                'source':('validated' if status=='passed' else status)+
                         ' hardware intrinsics; planning only, not an input to the new fit',
                'quality_status':status,
                'profile_id':layout['calibration']['profile_id']}
    focal=width/(2*np.tan(camera['camera_horizontal_fov']/2))
    return {'k':[[focal,0,width/2],[0,focal,height/2],[0,0,1]],'d':[0.]*5,'width':width,'height':height,
            'source':'nominal FOV; never passed to intrinsic/hand-eye fit'}


def acquisition_plan(model,layout,profiles,rid,start,sources,missing,count,directory,layout_file,progress=lambda p:None,*,view_design='standard',capture_source=None,focus=None,joint_window_deg=None):
    if not 30<=count<=79:raise ValueError('Hardware acquisition supports30–79 new poses (31–80 including initial view)')
    if missing:raise ValueError('Observe or explicitly declare all stationary arm poses before planning')
    configure_model(model,rid,DIAGONAL[rid])
    nominal=planning_camera(layout,rid,capture_source=capture_source,focus=focus)
    # This K bounds proposed views only. Real calibration fitting never receives it.
    proposed=generate_plan(model,layout,start,{rid:nominal},[rid],count,progress,view_design=view_design,
        joint_window_rad=np.radians(joint_window_deg) if joint_window_deg is not None else None,
        check_direct_return=False)[rid]
    nominal['view_design']=view_design
    if joint_window_deg is not None:nominal['joint_window_about_start_deg']=joint_window_deg
    nominal['route_ordering']=proposed.get('route_ordering','not reported')
    nominal['direct_return_checked']=False  # Hardware batch never commands an automatic return.
    poses=[dict(pose,sample_id=f'sample_{index+1:03d}') for index,pose in enumerate(proposed['poses'])]
    return assemble_plan(model,layout,profiles,rid,start,sources,missing,poses,directory,layout_file,nominal)


def assemble_plan(model,layout,profiles,rid,start,sources,missing,poses,directory,layout_file,nominal,*,resume=None):
    if not poses:raise ValueError('No outstanding acquisition views')
    configure_model(model,rid,DIAGONAL[rid])
    state=dict(start);segments=[];combined=[];tool_path=[];offset=0.
    from uwa_cell_gazebo.charuco_views import Chain
    tool=Chain(model.description,'world',rid+'_tool0')
    for pose in poses:
        path=timed_path(model,rid,state,pose['joints'],velocity=.05,acceleration=.10)
        segments.append({'sample_id':pose['sample_id'],'role':pose['role'],
                         'target':pose['joints'],'points':path})
        if 'projected_board_corner_bounds_px' in pose:
            segments[-1]['projected_board_corner_bounds_px']=pose['projected_board_corner_bounds_px']
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
          'planning_only_camera_model':dict({'source':'nominal FOV; never passed to intrinsic/hand-eye fit'},**nominal),
          'independent_diagonal_arm':DIAGONAL[rid],
          'diagonal_policy_source':'User physical reach statement and authorization2026-11-12; not measured geometry',
          'new_observations':len(segments),'automatic_return':False,'duration_motion_s':sum(s['points'][-1]['time'] for s in segments)}
    if resume is not None:plan['resume']=resume
    plan['fingerprint']=digest(plan)
    directory=Path(directory);atomic_json(directory/'batch.json',plan)
    preview={'purpose':'ChArUco acquisition sequence','arm':rid,'joint_names':joint_names(rid),
             'independent_diagonal_arm':DIAGONAL[rid],
             'start':start,'target':segments[-1]['target'],'points':combined,'duration':offset,
             'tool_path_world':tool_path,'nominal_camera_target_world':None,
             'method':'full MoveIt collision sweep per segment; captures while stationary',
             'velocity_limit':.05,'acceleration_limit':.10,'collision_samples':len(combined)}
    preview=save_plan(directory,preview,model,layout,profiles,sources,missing,'hardware')
    preview['executable']=False;preview.pop('fingerprint');preview['fingerprint']=digest(preview)
    atomic_json(directory/'plan.json',preview)  # Only batch-aware execution may capture/run it.
    return plan


def remaining_observations(plan,session):
    """Reuse only a verified completed prefix; never skip a failed/holey record."""
    session=Path(session).resolve();completed=[];remaining=[];hashes={};gap=False
    for segment in plan['segments']:
        path=session/'records'/(segment['sample_id']+'.json')
        if not path.exists():
            gap=True;remaining.append({'sample_id':segment['sample_id'],
                'role':segment['role'],'joints':segment['target']});continue
        if gap:raise ValueError('Non-contiguous observations; inspect the session before resuming')
        record=json.loads(path.read_text())
        if (record.get('accepted') is not True or record.get('robot_id')!=plan['arm'] or
                record.get('sample_id')!=segment['sample_id'] or record.get('role')!=segment['role']):
            raise ValueError('Existing observation is rejected or does not match the planned identity/role')
        q=np.asarray(record.get('positions',[]),float)
        if q.shape!=(6,) or not np.isfinite(q).all() or max(abs(q-segment['target']))>.03:
            raise ValueError('Existing observation joint pose differs from the completed target')
        image=Path(record['image'])
        if image.name!=str(image):raise ValueError('Observation image must be local to records')
        for item in (path,session/'records'/image):
            hashes[str(item.relative_to(session))]=hashlib.sha256(item.read_bytes()).hexdigest()
        completed.append(segment['sample_id'])
    return remaining,{'session':str(session),'parent_fingerprint':plan['fingerprint'],
                      'completed_samples':completed,'record_sha256':hashes,
                      'replanned_from_live_state':True}


def validate_session_model(metadata,rid,profile,layout):
    kinematics=profile.get('kinematics_file')
    actual=hashlib.sha256(Path(kinematics).read_bytes()).hexdigest() if kinematics else None
    if (metadata.get('mode')!='hardware' or metadata.get('robot_id')!=rid or
            metadata.get('camera_ip')!=profile['ip'] or metadata.get('layout_fingerprint')!=digest(layout) or
            metadata.get('kinematics_sha256')!=actual):
        raise ValueError('Session robot/camera/model or factory kinematics changed')


def validate_resume_records(plan,session):
    if 'resume' not in plan:return
    session=Path(session).resolve();resume=plan['resume']
    if str(session)!=resume['session']:raise ValueError('Resume session changed')
    for relative,expected in resume['record_sha256'].items():
        path=(session/relative).resolve()
        if session not in path.parents or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Completed observation changed since resume planning')


def validate_batch(plan,profiles,current_layout):
    independent_arm(plan)
    value=dict(plan);fingerprint=value.pop('fingerprint',None)
    if fingerprint!=digest(value):raise ValueError('Acquisition plan changed')
    if plan.get('mode')!='hardware' or plan.get('schema_version')!=1:raise ValueError('Wrong acquisition mode/schema')
    if plan['inventory_fingerprint']!=digest(profiles) or digest(plan['layout'])!=digest(current_layout):
        raise ValueError('Inventory or cell geometry changed; regenerate acquisition plan')
    if any(s not in ('live_joint_states','manual_pendant','user_nominal_home') for s in plan['state_sources'].values()):
        raise ValueError('Hardware acquisition requires measured/declared real states')


def initial_joint_state(observer,plan,timeout=16.):
    """Allow discovery to settle before motion; never merge expired snapshots."""
    required={r for r,s in plan['state_sources'].items()
              if s=='live_joint_states' and r!=independent_arm(plan)}
    deadline=time.monotonic()+timeout
    while True:
        current=observer.sample(2.)
        missing=required-set(current)
        if not missing:return current
        if time.monotonic()>=deadline:
            raise ValueError('No fresh initial joint data: '+', '.join(sorted(missing)))
        print(json.dumps({'phase':'WAITING_FOR_FRESH_JOINTS','stage':'series_start',
                          'missing_arms':sorted(missing)}),flush=True)


def acquire(args):
    import rclpy
    from match_ur_hardware.operations import switch
    from match_ur_hardware.trajectory import execute_trajectory
    from match_ur_hardware.profiles import load_profiles
    from uwa_cell_gazebo.configuration import load_layout
    from .park_arm import node_for,JointObserver
    from .parking import make_model
    from .handeye_hardware import capture_observation
    from .wrist_hd import make_camera
    plan=json.loads(Path(args.batch).read_text());profiles=load_profiles(args.inventory);rid=plan['arm']
    directory=Path(args.session).resolve();metadata=json.loads((directory/'session.json').read_text())
    if metadata['robot_id']!=rid or metadata['mode']!='hardware':raise ValueError('Wrong image session')
    node=node_for('hardware');completed=False;motion_started=False;trajectory_client=None
    if not getattr(args,'check_only',False):
        # Register the endpoint before MoveIt creates its C++ scene/logger and
        # before the first spin; late-created actions can fail discovery on this
        # Lyrical installation. Own one client for the whole batch.
        from rclpy.action import ActionClient
        from control_msgs.action import FollowJointTrajectory
        trajectory_client=ActionClient(node,FollowJointTrajectory,
            profiles[rid]['namespace']+'/scaled_joint_trajectory_controller/follow_joint_trajectory')
    observer=JointObserver(node,profiles,[r for r,s in plan['state_sources'].items() if s=='live_joint_states'],'hardware')
    try:
        model,layout=make_model(load_layout(plan['layout_file']),profiles,directory/'acquisition_model')
        validate_batch(plan,profiles,layout)
        diagonal=independent_arm(plan)
        if diagonal:configure_model(model,rid,diagonal)
        validate_resume_records(plan,directory)
        validate_session_model(metadata,rid,profiles[rid],layout)
        current=initial_joint_state(observer,plan)
        for r,s in plan['state_sources'].items():
            if r==diagonal:continue
            if s=='live_joint_states':
                if r not in current:raise ValueError(r+': no live joint data')
                if max(abs(q-plan['start'][j]) for q,j in zip(current[r]['positions'],joint_names(r)))>.01:
                    raise ValueError(r+': start changed; regenerate acquisition plan')
        def guard():observer.guard(plan,require_program_link=not getattr(args,'check_only',False))
        guard();camera=make_camera(profiles[rid]['ip'],node,metadata=metadata,rid=rid)
        planned_source=plan['planning_only_camera_model'].get('planned_capture_source')
        if planned_source and metadata.get('capture_source',{}).get('kind')!=planned_source:
            raise ValueError('Planned acquisition image source differs from the session')
        first=json.loads((directory/'records/sample_000.json').read_text())
        settings=camera.settings()
        if settings['focusAuto'] or settings['focus']!=first['camera_settings']['focus']:
            raise ValueError('Camera focus differs from first observation')
        for segment in plan['segments']:
            if (directory/'records'/(segment['sample_id']+'.json')).exists():
                raise ValueError('Existing observation; create a new reviewed acquisition instead of overwriting')
        if getattr(args,'check_only',False):
            state=dict(plan['start'])
            for r,record in observer.received.items():
                if r!=diagonal:state.update(zip(joint_names(r),record['positions']))
            for segment in plan['segments']:
                for point in segment['points']:
                    state.update(zip(joint_names(rid),point['positions']))
                    if not model.check(state)[0]:raise ValueError('Current acquisition path collision check failed')
            print(json.dumps({'success':True,'check_only':True,'segments':len(plan['segments']),
                              'fingerprint':plan['fingerprint']}),flush=True)
            completed=True;return
        deadline=time.monotonic()+30
        while not trajectory_client.server_is_ready():
            rclpy.spin_once(node,timeout_sec=.03);guard()
            if time.monotonic()>deadline:
                raise RuntimeError('Native trajectory endpoint unavailable before controller activation')
        for segment in plan['segments']:
            observer.sample(.2);guard()
            live=dict(plan['start'])
            for r,record in observer.received.items():
                if r!=diagonal:live.update(zip(joint_names(r),record['positions']))
            q0=[live[j] for j in joint_names(rid)]
            if max(abs(np.array(q0)-segment['points'][0]['positions']))>.01:
                raise ValueError('Segment start changed; stop without an unchecked connection')
            for point in segment['points']:
                q=dict(live,**dict(zip(joint_names(rid),point['positions'])))
                if not model.check(q)[0]:raise ValueError('Current full-cell segment collision check failed')
            observer.sample(.2);guard()
            print(json.dumps({'phase':'MOVING','sample_id':segment['sample_id'],'role':segment['role']}),flush=True)
            motion_started=True
            execute_trajectory(node,profiles[rid],segment['points'],mock=False,guard=guard,
                               action_client=trajectory_client)
            observer.sample(.4);guard()
            if max(abs(np.array(observer.received[rid]['positions'])-segment['target']))>.03:
                raise ValueError('Goal error exceeds0.03rad')
            record=capture_observation(camera,node,observer,model,layout,rid,directory/'records',
                                       segment['sample_id'],segment['role'],capture_guard=guard)
            guard()
            print(json.dumps({'phase':'CAPTURED','sample_id':segment['sample_id'],
                              'corners':record['corners'],'role':record['role']}),flush=True)
        completed=True
        print(json.dumps({'phase':'ACQUISITION_COMPLETE','new_observations':len(plan['segments'])}),flush=True)
    finally:
        if not completed and motion_started:
            try:switch(node,profiles[rid])
            except Exception as error:print('Could not confirm controller deactivation: '+str(error),flush=True)
        if trajectory_client is not None:trajectory_client.destroy()
        observer.close();node.destroy_node();rclpy.shutdown()

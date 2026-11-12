"""Explicit real first-view planning, stationary image capture and offline fitting.

No automatic power/brake/program operations and no simulation backend remapping.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import time

import cv2
import numpy as np

from match_ur_hardware.profiles import load_profiles
from uwa_cell_gazebo.configuration import ROBOT_IDS,default_layout_path,load_layout,joint_names
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_calibration.storage import atomic_json
from .park_arm import JointObserver,node_for
from .parking import complete_state,digest,manual_states,make_model,save_plan
from .hardware_charuco import first_view,observe,calibrate_intrinsics
from .wrist_camera import WristCamera,save_snapshot
from .wrist_hd import make_camera
from .wrist_activity import photo_activity


def read_state(node,profiles,args):
    manual=manual_states(args.manual_states)
    observer=JointObserver(node,profiles,[r for r,p in profiles.items() if p['ip']],args.mode)
    configured={r for r,p in profiles.items() if p['ip']}
    deadline=time.monotonic()+10
    while True:
        readings=dict(manual,**observer.sample(2.))
        missing=configured-set(readings)
        if not missing or time.monotonic()>=deadline:break
        print(json.dumps({'phase':'WAITING_FOR_FRESH_JOINTS','missing_arms':sorted(missing)}),flush=True)
    return observer,readings


def plan_view(args):
    import rclpy
    profiles=load_profiles(args.inventory);layout=load_layout(args.layout)
    directory=Path(args.output).expanduser().resolve();directory.mkdir(parents=True,exist_ok=True)
    node=node_for(args.mode);observer=None
    try:
        observer,readings=read_state(node,profiles,args)
        start,sources,missing=complete_state(layout,readings)
        model,layout=make_model(layout,profiles,directory)
        path=first_view(model,layout,args.arm,start)
        path['layout_file']=str(Path(args.layout).resolve())
        artifact=save_plan(directory,path,model,layout,profiles,sources,missing,args.mode)
        atomic_json(directory/'states.json',{'mode':args.mode,'arms':readings})
        print(json.dumps({'plan':str(directory/'plan.json'),'duration_s':artifact['duration'],
            'target_deg':np.degrees(artifact['target']).tolist(),
            'nominal_camera_world':np.array(artifact['nominal_camera_target_world'])[:3,3].tolist(),
            'executable':artifact['executable'],'unobserved_arms':missing},indent=2))
    finally:
        if observer:observer.close()
        node.destroy_node();rclpy.shutdown()


def plan_series(args):
    import rclpy
    from .hardware_sequence import acquisition_plan,assemble_plan,remaining_observations,validate_batch,validate_session_model
    profiles=load_profiles(args.inventory);node=node_for(args.mode);observer=None
    if args.mode!='hardware':raise ValueError('Reviewed image acquisition uses real hardware mode')
    directory=Path(args.output).resolve();directory.mkdir(parents=True,exist_ok=True)
    try:
        observer,readings=read_state(node,profiles,args)
        start,sources,missing=complete_state(load_layout(args.layout),readings)
        model,layout=make_model(load_layout(args.layout),profiles,directory)
        if args.command=='resume-series':
            old=json.loads(Path(args.batch).read_text());validate_batch(old,profiles,layout)
            metadata=json.loads((Path(args.session)/'session.json').read_text())
            if args.arm!=old['arm']:raise ValueError('Resume arm changed')
            validate_session_model(metadata,args.arm,profiles[args.arm],layout)
            if missing:raise ValueError('Missing stationary arm states')
            poses,resume=remaining_observations(old,args.session)
            plan=assemble_plan(model,layout,profiles,args.arm,start,sources,missing,poses,directory,args.layout,
                               old['planning_only_camera_model'],resume=resume)
        else:
            plan=acquisition_plan(model,layout,profiles,args.arm,start,sources,missing,args.count,directory,args.layout,
                lambda p:print(json.dumps({'phase':'PLANNING',**p}),flush=True),view_design=args.view_design,
                capture_source=getattr(args,'camera_source',None),focus=getattr(args,'planning_focus',None),
                joint_window_deg=getattr(args,'joint_window_deg',None))
        print(json.dumps({'batch':str(directory/'batch.json'),'preview':str(directory/'plan.json'),
                          'new_observations':len(plan['segments']),'motion_seconds':plan['duration_motion_s'],
                          'no_return_after_run':True},indent=2))
    finally:
        if observer:observer.close()
        node.destroy_node();rclpy.shutdown()


@photo_activity
def capture_observation(camera,node,observer,model,layout,rid,directory,sample_id,role,*,freshness_timeout=6.,capture_guard=None):
    """Conservative stationary interval plus changed decoded image payloads.

    Exposure timestamp is unavailable. Record that limitation explicitly rather
    than claiming hardware synchronization from HTTP receipt times.
    """
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if not sample_id.replace('_','').isalnum():raise ValueError('Invalid sample id')
    output=directory/(sample_id+'.json')
    if output.exists():raise ValueError('Observation exists; refusing to overwrite')
    expected=observer.sample(1.)
    if rid not in expected:raise ValueError('Live robot state missing')
    baseline=np.array(expected[rid]['positions']);names=joint_names(rid)
    def stationary():
        if capture_guard is not None:capture_guard()
        record=observer.received.get(rid)
        if not record or time.monotonic()-record['received_monotonic']>.5:
            raise ValueError('Joint telemetry stale while taking image')
        if max(abs(np.array(record['positions'])-baseline))>.002:
            raise ValueError('Robot moved during image capture; discard observation')
    settings=camera.settings()
    if settings['focusAuto']:raise ValueError('Set a fixed manual focus before intrinsic/hand-eye acquisition')
    hashes=[];receipt=[];frame=None;jpeg=None;detection=None;selected=0;native_validation=None
    if hasattr(camera,'capture_burst'):
        # The service client spins joint/safety subscriptions throughout its
        # camera-only transaction and waits for restoration even after motion.
        burst=camera.capture_burst(stationary)
        if getattr(camera,'require_native_controls',False):
            native_validation=validate_native_controls(camera.last_burst,settings)
        candidates=[]
        for index,data in enumerate(burst):
            image=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
            if image is None:raise ValueError('JPEG decode failed')
            hashes.append(hashlib.sha256(image.tobytes()).hexdigest())
            receipt.append(datetime.now(timezone.utc).isoformat())
            found=observe(image,layout['charuco'],layout['robots'][rid]['table'])
            sharp=float(cv2.Laplacian(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var())
            candidates.append((found['corners'],sharp,index,data,image,found))
        if not candidates:raise ValueError('HD service returned no frames')
        _,_,selected,jpeg,frame,detection=max(candidates,key=lambda item:item[:2])
        observer.sample(.15);stationary()
    else:
        end=time.monotonic()+freshness_timeout
        while time.monotonic()<end:
            observer.sample(.15);stationary()
            jpeg=camera.image();receipt.append(datetime.now(timezone.utc).isoformat())
            frame=cv2.imdecode(np.frombuffer(jpeg,np.uint8),cv2.IMREAD_COLOR)
            if frame is None:raise ValueError('JPEG decode failed')
            hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
            observer.sample(.15);stationary()
            if len(hashes)>=3 and len(set(hashes))>=2:break
        selected=len(hashes)-1
    if len(set(hashes))<2:raise ValueError('Image payload did not update; freshness is unverified, observation rejected')
    after=camera.settings()
    protected=['focus','focusAuto','pan','tilt','zoom','exposureAuto','lightingMode','lightingValue']
    if not settings.get('exposureAuto'):protected+=['exposure','gain']
    if any(after.get(k)!=settings.get(k) for k in protected):
        raise ValueError('Focus, image geometry or manual capture settings changed during capture')
    table=layout['robots'][rid]['table']
    if detection is None:detection=observe(frame,layout['charuco'],table)
    save_snapshot(directory,sample_id,jpeg,settings,dimensions=detection['image_size'])
    # save_snapshot writes diagnostics; replace metadata with complete observation.
    annotated=detection.pop('annotated');cv2.imwrite(str(directory/(sample_id+'_annotated.jpg')),annotated)
    if detection['corners']<layout['charuco']['min_corners']:
        atomic_json(output,{'accepted':False,'reason':'insufficient board corners',**detection,'camera_settings':settings})
        raise ValueError(f"Board has only {detection['corners']} detected corners; image saved for inspection")
    q=observer.received[rid]['positions'];positions=dict(zip(names,q))
    tool=Chain(model.description,rid+'_base_link',rid+'_tool0').forward(positions)
    record={'sample_id':sample_id,'robot_id':rid,'role':role,'accepted':True,
        **detection,'joint_names':names,'positions':q,'T_base_tool0':tool.tolist(),
        'camera_settings':settings,'camera_settings_after':after,'pixel_sha256':hashes[selected],
        'capture_source':getattr(camera,'capture_source',{'kind':'http_vga'}),
        'native_burst':getattr(camera,'last_burst',None),
        'native_control_validation':native_validation,
        'image':sample_id+'.jpg','receipt_utc':receipt[selected],
        'freshness':{'decoded_payload_changes':len(set(hashes)),'http_samples':len(hashes),
            'stationary_joint_tolerance_rad':.002,'sensor_exposure_timestamp_available':False,
            'association':'Frames acquired/received inside monitored stationary interval; no exposure timestamp guarantee'}}
    atomic_json(output,record)
    return record


def validate_native_controls(burst,settings):
    """Require actual V4L2 readbacks during the first and last retained frame."""
    samples={s['frame']:s for s in burst.get('sensor_controls',[]) if s.get('frame') in (3,5)}
    if set(samples)!={3,5}:
        raise ValueError('Native sensor controls were not read during both burst endpoints')
    expected={'focus_absolute':settings['focus'],'focus_auto':0}
    if not settings.get('exposureAuto'):
        # V4L2_EXPOSURE_MANUAL=1; this camera reports the same exposure units as UCC.
        expected.update(exposure_absolute=settings['exposure'],exposure_auto=1,gain=settings['gain'])
    for sample in samples.values():
        if any(sample.get(key)!=value for key,value in expected.items()):
            raise ValueError('Native sensor focus/exposure readback differs from the acquisition profile: '+str(sample))
    return dict(passed=True,expected=expected,samples=list(samples.values()),
                source='VIDIOC_G_CTRL during retained V4L2 frame3/frame5; not a physical focal-length measurement')


def capture(args):
    import rclpy
    profiles=load_profiles(args.inventory);rid=args.arm
    if args.mode!='hardware':raise ValueError('HTTP camera capture is explicitly hardware-only')
    if not profiles[rid]['ip']:raise ValueError('No configured camera/robot IP')
    node=node_for(args.mode);observer=None
    directory=Path(args.session).resolve();directory.mkdir(parents=True,exist_ok=True)
    try:
        observer,readings=read_state(node,profiles,args)
        model,layout=make_model(load_layout(args.layout),profiles,directory/'model')
        info={'schema_version':1,'mode':'hardware','robot_id':rid,
                'layout':layout,'description':model.description,'created_at':datetime.now(timezone.utc).isoformat(),
                'camera_ip':profiles[rid]['ip'],'layout_fingerprint':digest(layout),
                'kinematics_sha256':hashlib.sha256(Path(profiles[rid]['kinematics_file']).read_bytes()).hexdigest()
                    if profiles[rid]['kinematics_file'] else None,
                'kinematics_file':profiles[rid]['kinematics_file']}
        camera=make_camera(profiles[rid]['ip'],node,args,rid=rid)
        info['capture_source']=getattr(camera,'capture_source',{'kind':'http_vga'})
        info['native_control_readback_required']=getattr(camera,'require_native_controls',False)
        if (directory/'session.json').exists():
            old=json.loads((directory/'session.json').read_text())
            if any(old.get(k)!=info[k] for k in ('robot_id','camera_ip','layout_fingerprint','kinematics_sha256')):
                raise ValueError('Robot/camera/model changed; start a new acquisition session')
            if old.get('capture_source',{'kind':'http_vga'})!=info['capture_source']:
                raise ValueError('Image source changed; start a separate HD/VGA session')
            if old.get('native_control_readback_required',False)!=info['native_control_readback_required']:
                raise ValueError('Sensor readback policy changed; start a separate session')
        else:atomic_json(directory/'session.json',info)
        record=capture_observation(camera,node,observer,model,layout,rid,
            directory/'records',args.sample_id,args.role)
        print(json.dumps({k:record[k] for k in ('sample_id','corners','image_size','freshness')},indent=2))
    finally:
        if observer:observer.close()
        node.destroy_node();rclpy.shutdown()


def fit(args):
    from uwa_cell_gazebo.charuco import detect_pose
    from uwa_cell_calibration.solver import solve_session
    from uwa_cell_calibration.storage import validate_result
    directory=Path(args.session);metadata=json.loads((directory/'session.json').read_text())
    records=[json.loads(p.read_text()) for p in sorted((directory/'records').glob('sample_*.json'))]
    records=[r for r in records if r.get('accepted')]
    if not records:raise ValueError('No accepted hardware observations')
    rid=metadata['robot_id'];layout=metadata['layout']
    intrinsics=calibrate_intrinsics(records,focus=records[0]['camera_settings']['focus'],image_size=records[0]['image_size'])
    atomic_json(directory/'intrinsics.json',intrinsics)
    if args.intrinsics_only:
        print(json.dumps(intrinsics,indent=2));return
    handeye=[]
    for record in records:
        image=cv2.imread(str(directory/'records'/record['image']))
        pose=detect_pose(image,np.array(intrinsics['camera_matrix']),np.array(intrinsics['distortion']),
                         layout['charuco'],layout['robots'][rid]['table'])
        if pose is None:raise ValueError(record['sample_id']+': board pose failed with fitted intrinsics')
        handeye.append(dict(record,T_camera_board=pose['T_camera_board'].tolist(),
            object_points=pose['object_points'],image_points=pose['image_points'],
            camera_matrix=intrinsics['camera_matrix'],distortion=intrinsics['distortion']))
    result=solve_session({rid:handeye})
    result.update(mode='hardware',session_dir=str(directory.resolve()),intrinsics_file='intrinsics.json',
        timing_limitations='Monitored stationary image capture; sensor exposure timestamps unavailable',
        activated=False)
    try:validate_result(result)
    except ValueError as error:
        result.update(passed=False,profile_validation_error=str(error))
    atomic_json(directory/'handeye_result.json',result)
    print(json.dumps({'passed':result['passed'],'result':str(directory/'handeye_result.json'),
                      'activated':False},indent=2))
    if not result['passed']:raise ValueError('Independent hand-eye validation failed; result not activated')


def main():
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for command in ('plan-view','plan-series','resume-series','capture'):
        p=sub.add_parser(command)
        p.add_argument('--inventory',default=str(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'))
        p.add_argument('--layout',default=str(default_layout_path()))
        p.add_argument('--arm',choices=ROBOT_IDS,default='right_rear')
        p.add_argument('--mode',choices=['hardware','mock'],default='hardware')
        p.add_argument('--manual-states',default=str(ws/'setup/calibration/parking/left_home.json'))
        if command in ('plan-view','plan-series','resume-series'):
            p.add_argument('--output',required=True)
            if command=='plan-series':
                p.add_argument('--camera-source',choices=['http_vga','wrist_hd_service'],default=None,
                               help='Image source to design for; native HD uses a nominal FOV proxy, not scaled VGA calibration')
                p.add_argument('--planning-focus',type=int,default=None,help='Record intended fixed focus; does not write camera settings')
                p.add_argument('--joint-window-deg',type=float,default=None,
                               help='Optional local design envelope about measured start, <=180deg; native robot limits unchanged')
                p.add_argument('--count',type=int,default=40,help='Additional views after sample_000;61 yields62 total')
                p.add_argument('--view-design',choices=['standard','wide'],default='standard',
                               help='Wide varies board image position, distance, inclination and roll')
            if command=='resume-series':
                p.add_argument('batch');p.add_argument('--session',required=True)
        else:
            p.add_argument('--require-native-controls',action='store_true',
                           help='Require matching V4L2 focus/exposure readback during retained HD frames')
            p.add_argument('--camera-source',choices=['http_vga','wrist_hd_service'],default=None)
            p.add_argument('--hd-service',default=None,help='Override the selected arm HD service name')
            p.add_argument('--session',required=True);p.add_argument('--sample-id',required=True)
            p.add_argument('--role',choices=['fit','validation'],required=True)
    p=sub.add_parser('fit');p.add_argument('session');p.add_argument('--intrinsics-only',action='store_true')
    p=sub.add_parser('run-series');p.add_argument('batch');p.add_argument('--session',required=True)
    p.add_argument('--inventory',default=str(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'))
    p.add_argument('--check-only',action='store_true',help='Recheck the full sequence without motion or controller changes')
    p.add_argument('--intrinsics-only',action='store_true',help='Fit intrinsics after acquisition; do not run hand-eye fitting')
    args=parser.parse_args()
    try:
        if args.command=='run-series':
            from .hardware_sequence import acquire
            acquire(args)
            if not args.check_only:
                fit(args)
        else:{'plan-view':plan_view,'plan-series':plan_series,'resume-series':plan_series,'capture':capture,'fit':fit}[args.command](args)
        return 0
    except KeyboardInterrupt:return 130
    except Exception as error:
        print(json.dumps({'success':False,'error':str(error)}));return 1


if __name__=='__main__':raise SystemExit(main())

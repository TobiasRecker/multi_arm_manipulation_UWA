"""Independent ROS session owner, capture engine and wall-time motion watchdog."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import signal
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.clock import Clock,ClockType
from rclpy.duration import Duration
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.time import Time
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import Image, CameraInfo, JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from geometry_msgs.msg import TransformStamped
from trajectory_msgs.msg import JointTrajectoryPoint, JointTrajectory
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers
from rcl_interfaces.srv import GetParameters
from tf2_ros import Buffer, TransformListener, TransformBroadcaster, TransformException
from uwa_cell_calibration_msgs.action import RunCalibration
from uwa_cell_calibration_msgs.srv import PrepareCalibration, ApplyCalibration

from uwa_cell_gazebo.configuration import load_layout, joint_names, gripper_joint, ROBOT_IDS, default_layout_path, render_description
from uwa_cell_gazebo.charuco import detect_pose, pose_error, table_board_transform
from uwa_cell_gazebo.charuco_check import tf_matrix
from .model import calibrated_description
from .planner import PlanningProcess
from .storage import atomic_json, fingerprint, validate_result

PREFIX='/uwa_cell/calibration'
ACTIVE={'PREPARING','RUNNING','PARKING','POSITIONING','MOVING','SETTLING','CAPTURING','RETURNING','PAUSED','SOLVING','APPLYING'}


class CaptureFailure(ValueError):
    """Only image acquisition failures may consume reserve poses."""


def rgb_image(msg):
    if msg.encoding not in ('rgb8','bgr8'):
        raise ValueError('Only RGB8/BGR8 images are supported')
    result=np.frombuffer(msg.data,dtype=np.uint8).reshape(msg.height,msg.step)[:,:msg.width*3].reshape(msg.height,msg.width,3)
    return cv2.cvtColor(result,cv2.COLOR_RGB2BGR) if msg.encoding=='rgb8' else result.copy()


class Backend(Node):
    def __init__(self):
        super().__init__('calibration_backend',namespace='uwa_cell')
        self.declare_parameter('layout',str(default_layout_path()))
        self.declare_parameter('session_root',str(Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))/'setup/calibration'))
        self.layout_path=Path(self.get_parameter('layout').value)
        self.layout=load_layout(self.layout_path)
        self.stop_joints=[j for rid in ROBOT_IDS for j in joint_names(rid)]+[
            gripper_joint(rid) for rid in ROBOT_IDS if self.layout['robots'][rid]['tools']['gripper']!='none']
        self.root=Path(self.get_parameter('session_root').value).expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.lockfile=(Path(tempfile.gettempdir())/f'uwa-cell-calibration-{os.getuid()}-64.lock').open('a')
        try:fcntl.flock(self.lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another calibration backend owns this cell')
        self.mutex=threading.RLock();self.motion_lock=threading.RLock()
        self.abort=threading.Event();self.pause=threading.Event();self.shutdown_event=threading.Event()
        self.state={'phase':'IDLE','robot_id':'','accepted':0,'target':40,'rejected':0,'message':'Simulation bereitstellen; Posen vorbereiten.',
                    'plan_id':'','result_path':'','counts':{},'active_profile':''}
        self.description='';self.active_description='';self.model_xml=None;self.planner=None
        self.positions={};self.velocities={};self.last_joints=0.;self.history=deque(maxlen=3000)
        self.images={};self.infos={};self.last_images={};self.detections={r:deque(maxlen=80) for r in ROBOT_IDS}
        self.processed={};self.heartbeat=0.;self.owner='';self.clock_value=None;self.last_clock_change=time.monotonic()
        self.frozen={};self.hold_positions={};self.camera_quality={}
        self.motion_handles={};self.pending_goals={};self.registration_pending=set();self.motion_results={}
        self.controlled_robots=set();self.goal_reserved=False;self.run_handle=None
        self.plan=None;self.session=None;self.halt_thread=None;self.running=False;self.threads=[]
        self.profile_restored=False;self.command_sent=0.;self.preparation_start=0.
        self.operation_thread=None
        self.buffer=Buffer();self.listener=TransformListener(self.buffer,self)
        self.broadcaster=TransformBroadcaster(self)
        self.group=ReentrantCallbackGroup()
        transient=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(String,'/uwa_cell/robot_description',self.on_description,transient,callback_group=self.group)
        self.create_subscription(JointState,'/uwa_cell/joint_states',self.on_joints,qos_profile_sensor_data,callback_group=self.group)
        self.create_subscription(String,PREFIX+'/heartbeat',self.on_heartbeat,10,callback_group=self.group)
        self.status_pub=self.create_publisher(String,PREFIX+'/status',transient)
        self.description_pub=self.create_publisher(String,'/uwa_cell/calibrated/robot_description',transient)
        self.preview={}
        self.trajectory_clients={}
        for rid in ROBOT_IDS:
            self.create_subscription(Image,f'/uwa_cell/{rid}/wrist_camera/image_raw',lambda m,r=rid:self.on_image(r,m),qos_profile_sensor_data,callback_group=self.group)
            self.create_subscription(CameraInfo,f'/uwa_cell/{rid}/wrist_camera/camera_info',lambda m,r=rid:self.infos.update({r:m}),qos_profile_sensor_data,callback_group=self.group)
            self.create_subscription(JointTrajectory,f'/uwa_cell/{rid}_trajectory_controller/joint_trajectory',lambda m,r=rid:self.external_command(r,m),10,callback_group=self.group)
            self.preview[rid]=self.create_publisher(Image,f'{PREFIX}/{rid}/image_annotated',qos_profile_sensor_data)
            self.trajectory_clients[rid]=ActionClient(self,FollowJointTrajectory,f'/uwa_cell/{rid}_trajectory_controller/follow_joint_trajectory',callback_group=self.group)
        self.create_service(PrepareCalibration,PREFIX+'/prepare',self.prepare,callback_group=self.group)
        self.create_service(ApplyCalibration,PREFIX+'/apply',self.apply,callback_group=self.group)
        for command in ('pause','resume','stop','pause_world'):
            self.create_service(Trigger,PREFIX+'/'+command,lambda req,res,c=command:self.control(c,res),callback_group=self.group)
        self.action=ActionServer(self,RunCalibration,PREFIX+'/run',execute_callback=self.execute,
                                 goal_callback=self.accept_goal,cancel_callback=self.cancel_goal,callback_group=self.group)
        self.status_clock=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.1,self.publish_status,clock=self.status_clock,callback_group=self.group)
        self.create_timer(.05,self.publish_model,callback_group=self.group)
        self.spawn(self.image_loop);self.spawn(self.watchdog)
        if (self.root/'profiles/active.json').is_file():
            self.status('RESTORING',message='Lade gespeichertes kalibriertes Modell')
            self.operation_thread=self.spawn(self.restore_existing)

    def spawn(self,function):
        thread=threading.Thread(target=function,daemon=True);self.threads.append(thread);thread.start();return thread

    def restore_existing(self):
        try:
            deadline=time.monotonic()+30
            while not self.description or time.monotonic()-self.last_joints>1:
                if self.halted():raise InterruptedError('Profile restore stopped')
                if time.monotonic()>deadline:raise TimeoutError('Start the simulated cell before restoring its calibration profile')
                time.sleep(.05)
            profile=json.loads((self.root/'profiles/active.json').read_text())
            if profile.get('description_fingerprint')!=fingerprint(self.description):raise ValueError('Active profile does not match the current cell')
            self.install_model(profile);self.profile_restored=True
            self.status('IDLE',active_profile=str(self.root/'profiles/active.json'),message='Gespeichertes kalibriertes Modell aktiv',
                        **self.result_fields(profile,self.root/'profiles/active.json'))
        except Exception as error:
            self.status('STOPPED' if self.abort.is_set() else 'ERROR',message=str(error))
            self.get_logger().error(str(error))

    def status(self,phase=None,**fields):
        with self.mutex:
            if phase:self.state['phase']=phase
            self.state.update(fields)

    def result_fields(self,profile,path):
        truth_path=Path(profile.get('session_dir',''))/'ground_truth_validation.json'
        try:truth=json.loads(truth_path.read_text()) if truth_path.is_file() else {}
        except (OSError,ValueError):truth={}
        counts={r:fit['fit_count']+fit['validation_count']+len(fit.get('excluded_samples',[])) for r,fit in profile['robots'].items()}
        return {'result_path':str(path),'summary':{r:{k:v for k,v in fit.items() if k not in ('bootstrap_base_board','validation_samples')}
                                                 for r,fit in profile['robots'].items()},
                'counts':counts,'progress_total':sum(counts.values()),
                'relative_bases':profile.get('relative_bases',{}),'table_bases':profile.get('table_bases',{}),'ground_truth':truth}

    def publish_status(self):
        with self.mutex:state=dict(self.state)
        state['client_id']=self.owner
        state['stopped']=self.stationary() and time.monotonic()-self.last_joints<.5
        state['camera_quality']=dict(self.camera_quality)
        self.status_pub.publish(String(data=json.dumps(state)))
        if self.run_handle and self.run_handle.is_active:
            feedback=RunCalibration.Feedback()
            for key in ('phase','robot_id','accepted','target','rejected','message'):setattr(feedback,key,state[key])
            feedback.robot_ids=state.get('active_robots',[])
            self.run_handle.publish_feedback(feedback)

    def on_description(self,msg):
        if self.description and fingerprint(msg.data)!=fingerprint(self.description) and self.state['phase'] in ACTIVE:
            self.request_halt('Robot description changed during session')
        self.description=msg.data

    def on_heartbeat(self,msg):
        if msg.data==self.owner:self.heartbeat=time.monotonic()

    def on_joints(self,msg):
        now=time.monotonic()
        self.positions.update(zip(msg.name,msg.position));self.velocities.update(zip(msg.name,msg.velocity))
        self.last_joints=now
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        self.history.append((stamp,dict(self.positions),dict(self.velocities)))
        if self.clock_value is None or stamp>self.clock_value:
            self.last_clock_change=now
        elif stamp<self.clock_value-.05 and self.state['phase'] in ACTIVE:
            self.request_halt('Simulation clock jumped backwards')
        self.clock_value=stamp

    def on_image(self,rid,msg):
        self.images[rid]=msg;self.last_images[rid]=time.monotonic()

    def external_command(self,rid,msg):
        if msg.points and self.state['phase'] in ACTIVE:
            self.request_halt(f'External trajectory topic command on {rid}; disable rqt output')

    def image_loop(self):
        while not self.shutdown_event.wait(.08):
            for rid in ROBOT_IDS:
                msg,info=self.images.get(rid),self.infos.get(rid)
                if msg is None or info is None:continue
                stamp=(msg.header.stamp.sec,msg.header.stamp.nanosec)
                if self.processed.get(rid)==stamp:continue
                self.processed[rid]=stamp
                try:
                    if msg.header.frame_id!=info.header.frame_id or (msg.width,msg.height)!=(info.width,info.height):continue
                    pixels=rgb_image(msg)
                    detected=detect_pose(pixels,np.array(info.k).reshape(3,3),np.array(info.d),self.layout['charuco'],self.layout['robots'][rid]['table'])
                    self.detections[rid].append((msg,info,detected,pixels))
                    self.camera_quality[rid]=({'corners':detected['corners'],'reprojection_rms_px':detected['reprojection_rms_px']}
                                              if detected else {'corners':0})
                    annotated=detected['annotated'] if detected else pixels
                    out=Image();out.header=msg.header;out.encoding='bgr8';out.height,out.width=annotated.shape[:2]
                    out.step=out.width*3;out.data=annotated.tobytes();self.preview[rid].publish(out)
                except Exception as error:
                    self.get_logger().warn(f'{rid}: image processing failed: {error}',throttle_duration_sec=5)

    def wait_future(self,future,timeout=15,interruptible=True):
        deadline=time.monotonic()+timeout
        while not future.done():
            if interruptible and self.halted():raise InterruptedError('Motion/session interrupted')
            if self.shutdown_event.is_set() or time.monotonic()>deadline:raise TimeoutError('ROS service/action response timed out')
            time.sleep(.01)
        return future.result()

    def require_telemetry(self,interruptible=True):
        if not self.description:raise ValueError('No live robot_description; start the simulated cell first')
        if time.monotonic()-self.last_joints>1:raise ValueError('Fresh simulated joint states are required')
        if any(j not in self.positions for r in ROBOT_IDS for j in joint_names(r)):raise ValueError('Missing arm joint states')
        if self.state['phase'] not in ('MOVING','RETURNING','PARKING','POSITIONING'):
            # An isolated velocity spike is possible even on actuated joints in
            # Gazebo. Require a stable window before dispatch, rather than
            # aborting a valid dataset on one noisy telemetry sample.
            deadline=time.monotonic()+2.;stable=None
            while time.monotonic()<deadline:
                if interruptible and self.halted():raise InterruptedError('Stationary check interrupted')
                if time.monotonic()-self.last_joints>1:raise ValueError('Joint telemetry stale')
                if self.stationary():
                    stable=stable or time.monotonic()
                    if time.monotonic()-stable>=.2:break
                else:stable=None
                time.sleep(.02)
            else:
                moving={j:self.velocities.get(j) for j in self.stop_joints if abs(self.velocities.get(j,1))>=.01}
                raise ValueError(f'All arms/grippers must be stationary: {moving}')

    def stationary(self):
        # Passive mimic velocity telemetry jitters in this Gazebo backend.
        # Check every actuated arm/gripper joint; independently monitor all link
        # joint positions for unexpected changes during acquisition.
        return all(abs(self.velocities.get(j,1.))<.01 for j in self.stop_joints)

    def require_controllers(self,ids):
        client=self.create_client(ListControllers,'/uwa_cell/controller_manager/list_controllers',callback_group=self.group)
        try:
            if not client.wait_for_service(timeout_sec=3):raise ValueError('Controller manager missing')
            result=self.wait_future(client.call_async(ListControllers.Request()))
            active={c.name:c.state for c in result.controller}
            if any(active.get(r+'_trajectory_controller')!='active' for r in ROBOT_IDS):raise ValueError('All four arm controllers must be active')
        finally:self.destroy_client(client)
        for rid in ids:
            client=self.create_client(GetParameters,f'/uwa_cell/{rid}_trajectory_controller/get_parameters',callback_group=self.group)
            try:
                if not client.wait_for_service(timeout_sec=3):raise ValueError('Controller parameters unavailable')
                params=['constraints.decelerate_on_cancel']+[f'constraints.{j}.max_deceleration_on_cancel' for j in joint_names(rid)]
                response=self.wait_future(client.call_async(GetParameters.Request(names=params)))
                if not response.values[0].bool_value or any(v.double_value<=0 for v in response.values[1:]):
                    raise ValueError('Restart the cell with the updated decelerate-on-cancel controller settings')
            finally:self.destroy_client(client)

    def ensure_planner(self):
        if self.planner is None:
            self.planner=PlanningProcess(self.active_description or self.description,self.root/'planning')
        return self.planner

    def prepare(self,request,response):
        with self.mutex:
            if self.state['phase'] not in ('IDLE','READY','COMPLETE','STOPPED','ERROR') or self.goal_reserved or (self.operation_thread and self.operation_thread.is_alive()):
                response.accepted=False;response.message='A calibration operation is already active';return response
            ids=[r for r in ROBOT_IDS if r in request.robot_ids]
            if len(ids)!=len(request.robot_ids) or not ids or not 30<=request.samples_per_robot<=50 or not request.client_id:
                response.accepted=False;response.message='Select unique cell robot IDs, 30-50 samples and a client ID';return response
            self.abort.clear();self.pause.clear();self.owner=request.client_id;self.heartbeat=time.monotonic()
            self.preparation_start=time.monotonic()
            self.frozen=dict(self.positions)
            self.state.update(phase='PREPARING',message='Prüfe Telemetrie und plane Messstellungen',plan_id='',result_path='',robot_id='',accepted=0,rejected=0,target=request.samples_per_robot,counts={r:0 for r in ids},
                              summary={},ground_truth={},relative_bases={},table_bases={},progress_total=0,
                              active_robots=[],cohort=[],parked_robots=[],stage_index=0,stage_total=0,
                              mode='diagonal_pairs' if request.diagonal_pairs else 'sequential')
        self.operation_thread=self.spawn(lambda:self.prepare_work(ids,request.samples_per_robot,request.diagonal_pairs))
        response.accepted=True;response.message='Preparation started';return response

    def prepare_work(self,ids,count,diagonal_pairs=True):
        try:
            self.require_telemetry();self.require_controllers(ROBOT_IDS if diagonal_pairs else ids)
            self.layout=load_layout(self.layout_path)
            with tempfile.TemporaryDirectory(prefix='uwa_calibration_reference_') as directory:
                expected=render_description(self.layout,directory)[0]
            if fingerprint(expected)!=fingerprint(self.description):
                raise ValueError('Layout does not match the running cell; restart the cell with this layout')
            active=self.root/'profiles/active.json'
            if not self.profile_restored:
                if active.is_file():
                    profile=json.loads(active.read_text())
                    if profile.get('description_fingerprint')!=fingerprint(self.description):raise ValueError('Active profile does not match the current cell; remove/replace it explicitly')
                    self.install_model(profile)
                    self.state['active_profile']=str(active)
                self.profile_restored=True
            for rid in ids:
                if not self.layout['robots'][rid]['tools']['camera_enabled'] or rid not in self.infos:raise ValueError(f'{rid}: camera not available')
                if time.monotonic()-self.last_images.get(rid,0)>2:raise ValueError(f'{rid}: camera stream stale')
                if not self.detections[rid] or not self.detections[rid][-1][2]:raise ValueError(f'{rid}: assigned ChArUco board not visible at the start')
            stamp=datetime.now(ZoneInfo('Australia/Perth')).strftime('%Y%m%d_%H%M%S')
            self.session=self.root/(stamp+'_'+uuid.uuid4().hex[:6]);self.session.mkdir()
            start=dict(self.positions)
            matrices={r:{'k':np.asarray(self.infos[r].k).reshape(3,3).tolist(),'width':self.infos[r].width,'height':self.infos[r].height,
                         'd':list(self.infos[r].d),'frame':self.infos[r].header.frame_id} for r in ids}
            def progress(p):self.status(**p,message=f"{p['robot_id']}: prüfe Ziel {p['accepted']}/{p['target']}")
            prepared=self.ensure_planner().call({'op':'prepare','layout':self.layout,'start':start,'matrices':matrices,'robots':ids,'count':count,
                                                'diagonal_pairs':diagonal_pairs},self.halted,progress)
            if self.halted():raise InterruptedError('Preparation interrupted')
            self.plan={'schema_version':1,'plan_id':uuid.uuid4().hex,'description_fingerprint':fingerprint(self.description),
                       'robots':ids,'samples_per_robot':count,'start':start,'matrices':matrices,**prepared,
                       'layout':self.layout,'session_dir':str(self.session)}
            atomic_json(self.session/'plan.json',self.plan)
            with self.motion_lock:
                if self.halted():raise InterruptedError('Preparation interrupted before ready')
                self.status('READY',plan_id=self.plan['plan_id'],robot_id='',accepted=0,target=count,message='Posen und Wege geprüft. Start ist möglich.')
        except InterruptedError:
            self.status('STOPPED',message='Vorbereitung gestoppt')
        except Exception as error:
            self.status('STOPPED' if self.abort.is_set() else 'ERROR',message=str(error));self.get_logger().error(str(error))

    def accept_goal(self,request):
        with self.mutex:
            if self.state['phase']!='READY' or self.goal_reserved or not self.plan or request.plan_id!=self.plan['plan_id'] or self.abort.is_set() or time.monotonic()-self.heartbeat>1.5:return GoalResponse.REJECT
            self.goal_reserved=True
            return GoalResponse.ACCEPT

    def cancel_goal(self,handle):
        self.request_halt('Session action cancelled');return CancelResponse.ACCEPT

    def halted(self):return self.abort.is_set() or self.pause.is_set() or self.shutdown_event.is_set()

    def control(self,command,response):
        if command=='pause_world':
            response.success=self.pause_world();response.message='Gazebo pause requested';self.request_halt('Simulation manually paused');return response
        if command=='stop':
            self.request_halt('Stopp angefordert');response.success=True;response.message='Stop latched';return response
        if command=='pause':
            if not self.running or self.state['phase']=='SOLVING':response.success=False;response.message='No pausable acquisition';return response
            self.request_halt('Pause angefordert',pause=True);response.success=True;response.message='Pausing';return response
        if command=='resume':
            if self.state['phase']!='PAUSED' or self.abort.is_set():response.success=False;response.message='Resume only from confirmed PAUSED';return response
            if time.monotonic()-self.heartbeat>1:response.success=False;response.message='Session owner heartbeat missing';return response
            self.pause.clear();self.status('RUNNING',message='Fortgesetzt; Wege werden erneut geprüft')
            response.success=True;response.message='Resuming';return response

    def request_halt(self,reason,pause=False):
        self.status(stop_reason=reason)
        with self.motion_lock:
            (self.pause if pause and not self.abort.is_set() else self.abort).set()
            for handle in list(self.motion_handles.values()):
                try:handle.cancel_goal_async()
                except Exception:pass
        if self.state['phase'] in ACTIVE or self.running:
            self.status('HALTING',message=reason,stop_reason=reason)
            if self.halt_thread is None or not self.halt_thread.is_alive():
                self.halt_thread=self.spawn(self.confirm_halt)
        else:
            self.status('STOPPED',message=reason)

    def confirm_halt(self):
        deadline=time.monotonic()+1.5;stable=None
        while time.monotonic()<deadline and not self.shutdown_event.is_set():
            pending=bool(self.registration_pending) or any(not f.done() for f in list(self.pending_goals.values()))
            stopped=(self.stationary() and time.monotonic()-self.last_joints<.5)
            if stopped and not pending and not self.motion_handles:
                stable=stable or time.monotonic()
                if time.monotonic()-stable>=.2:
                    self.hold_positions=dict(self.positions)
                    self.status('PAUSED' if self.pause.is_set() and not self.abort.is_set() else 'STOPPED',message='Stillstand bestätigt: '+self.state.get('stop_reason',''))
                    return
            else:stable=None
            time.sleep(.02)
        paused=self.pause_world()
        self.abort.set();self.status('STOPPED',world_pause_confirmed=paused,
                                    message=('Stopp nicht rechtzeitig bestätigt; Gazebo-Pause bestätigt. Sitzung abgebrochen.' if paused
                                             else 'ACHTUNG: Weder Stillstand noch Gazebo-Pause bestätigt. Keine weiteren Fahrbefehle.'))

    def pause_world(self):
        try:
            from gz.transport import Node as GzNode
            from gz.msgs.world_control_pb2 import WorldControl
            from gz.msgs.boolean_pb2 import Boolean
            transport=GzNode()
            result,response=transport.request('/world/uwa_lab/control',WorldControl(pause=True),WorldControl,Boolean,1000)
            return bool(result and response.data)
        except Exception as error:
            self.get_logger().error(f'Gazebo pause fallback failed: {error}');return False

    def watchdog(self):
        while not self.shutdown_event.wait(.05):
            phase=self.state['phase'];now=time.monotonic()
            if phase not in ACTIVE:continue
            if now-self.heartbeat>1.5:
                self.request_halt('GUI/client heartbeat lost');continue
            if now-self.last_joints>1 or now-self.last_clock_change>1:
                self.request_halt('Joint telemetry or simulation clock stale');continue
            if self.running or phase in ('PREPARING','APPLYING'):
                for rid in self.state.get('cohort',[]):
                    if now-self.last_images.get(rid,0)>2:self.request_halt(f'{rid}: camera stream lost')
                holding=phase in ('PAUSED','CAPTURING')
                controlled={j for rid in self.controlled_robots for j in joint_names(rid)} if self.running and not holding else set()
                baseline=self.hold_positions if holding else self.frozen
                for joint,position in baseline.items():
                    if joint not in controlled and abs(self.positions.get(joint,position)-position)>.015:
                        self.request_halt(f'Unexpected movement of {joint}');break

    def wait_unpaused(self):
        while self.pause.is_set() and not self.abort.is_set():
            time.sleep(.05)
        if self.abort.is_set() or self.shutdown_event.is_set():raise InterruptedError('Session stopped')

    def move(self,rid,target,returning=False):
        return self.move_many({rid:target},'RETURNING' if returning else 'MOVING')

    def accept_motion(self,rid,future):
        """Register every acknowledgement, including those arriving after Stop."""
        try:
            handle=future.result()
            with self.motion_lock:
                if handle.accepted:
                    self.motion_handles[rid]=handle
                    self.motion_results[rid]=handle.get_result_async()
                    def finished(result,robot=rid,h=handle):
                        with self.motion_lock:
                            if self.motion_handles.get(robot) is h:self.motion_handles.pop(robot,None)
                    self.motion_results[rid].add_done_callback(finished)
                    if self.halted():handle.cancel_goal_async()
                else:self.request_halt(f'{rid}: trajectory rejected; cancelling whole cohort')
        except Exception as error:self.request_halt(f'{rid}: goal acknowledgement failed: {error}')
        finally:self.registration_pending.discard(rid)

    def move_many(self,targets,phase='MOVING'):
        self.wait_unpaused()
        self.require_telemetry()
        ids=list(targets)
        self.controlled_robots=set(ids)
        self.status(phase,robot_id=ids[0],active_robots=ids,
                    message={'PARKING':'Wartearm zur Seite parken','POSITIONING':'Aktives Paar zum Board ausrichten',
                             'RETURNING':'Rückfahrt zur Sitzungsstartstellung'}.get(phase,'Geprüfte Messstellung des Diagonalpaars' if len(ids)==2 else 'Fahre geprüfte Messstellung'))
        checked=self.ensure_planner().call({'op':'paths','start':dict(self.positions),'targets':targets},self.halted)
        goals={}
        for rid,path in checked['paths'].items():
            if not self.trajectory_clients[rid].wait_for_server(timeout_sec=3):raise ValueError(f'{rid}: trajectory action missing')
            goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=joint_names(rid)
            for p in path[1:]:
                point=JointTrajectoryPoint(positions=p['positions'],velocities=p['velocities'],accelerations=p['accelerations'])
                point.time_from_start.sec=int(p['time']);point.time_from_start.nanosec=round((p['time']-int(p['time']))*1e9)
                if point.time_from_start.nanosec>=1000000000:point.time_from_start.sec+=1;point.time_from_start.nanosec-=1000000000
                goal.trajectory.points.append(point)
            goals[rid]=goal
        start_time=self.get_clock().now()+Duration(seconds=.75)
        acceptance_deadline=start_time.nanoseconds-150000000
        self.status(motion_start_ns=start_time.nanoseconds,envelope_separation_m=checked['envelope_separation_m'])
        with self.motion_lock:
            if self.halted():raise InterruptedError('Stopped before goal dispatch')
            self.motion_results={}
            for rid,goal in goals.items():
                goal.trajectory.header.stamp=start_time.to_msg()
                self.registration_pending.add(rid)
                try:self.pending_goals[rid]=self.trajectory_clients[rid].send_goal_async(goal)
                except Exception:
                    self.registration_pending.discard(rid)
                    self.request_halt('Controller goal dispatch failed');raise
                self.pending_goals[rid].add_done_callback(lambda future,r=rid:self.accept_motion(r,future))
        try:
            while self.registration_pending:
                if self.halted():raise InterruptedError('Stopped during cohort goal acceptance')
                if self.get_clock().now().nanoseconds>=acceptance_deadline:raise TimeoutError('Not all goals acknowledged before shared start; cohort cancelled')
                time.sleep(.01)
            if self.get_clock().now().nanoseconds>=acceptance_deadline:raise TimeoutError('Cohort acknowledgements arrived too late for shared start')
            if self.halted():raise InterruptedError('Cohort start stopped')
            if set(self.motion_results)!=set(ids):raise ValueError('Missing trajectory acceptance/result future')
            deadline=time.monotonic()+checked['duration']*5+10
            remaining=set(ids)
            while remaining:
                if self.halted():raise InterruptedError('Cohort motion interrupted')
                if time.monotonic()>deadline:raise TimeoutError('Cohort trajectory timed out')
                for rid in list(remaining):
                    future=self.motion_results[rid]
                    if not future.done():continue
                    result=future.result()
                    if result.status!=4 or result.result.error_code!=0:raise ValueError(f'{rid}: trajectory aborted: {result.result.error_string}')
                    remaining.remove(rid)
                time.sleep(.01)
            for rid,target in targets.items():
                if max(abs(self.positions[j]-q) for j,q in zip(joint_names(rid),target))>.02:raise ValueError(f'{rid}: goal tracking error exceeds 0.02 rad')
        except InterruptedError:raise
        except Exception as error:self.request_halt(str(error));raise
        with self.motion_lock:
            self.pending_goals={r:f for r,f in self.pending_goals.items() if r not in ids}
        self.status('SETTLING',message='Warte auf Stillstand und frische Bilder')
        start=None;deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if self.halted():raise InterruptedError('Settling interrupted')
            if all(abs(self.velocities.get(j,1))<.01 for rid in ids for j in joint_names(rid)):
                start=self.clock_value if start is None else start
                if self.clock_value-start>=.5:
                    self.frozen=dict(self.positions);self.controlled_robots=set();return
            else:start=None
            time.sleep(.02)
        raise TimeoutError('Robot did not settle')

    def capture(self,rid,pose,index,announce=True,after=None):
        if announce:
            self.hold_positions=dict(self.positions)
            self.status('CAPTURING',message='Wähle scharfes Bild aus fünf frischen Boardansichten')
        after=self.clock_value if after is None else after
        deadline=time.monotonic()+6;seen=set();choices=[]
        expected=self.plan['matrices'][rid]
        while time.monotonic()<deadline and len(choices)<5:
            if self.halted():raise InterruptedError('Capture interrupted')
            for msg,info,detected,pixels in list(self.detections[rid]):
                stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
                if stamp<=after or stamp in seen:continue
                if not np.allclose(info.k,np.array(expected['k']).ravel()) or list(info.d)!=expected['d']:
                    raise ValueError('CameraInfo changed during the session')
                if detected is None or detected['reprojection_rms_px']>1:seen.add(stamp);continue
                try:
                    tf=self.buffer.lookup_transform(f'{rid}_base_link',f'{rid}_tool0',Time.from_msg(msg.header.stamp))
                except TransformException:continue
                if not self.history:continue
                joint_sample=min(list(self.history),key=lambda item:abs(item[0]-stamp))
                if abs(joint_sample[0]-stamp)>.04 or any(abs(joint_sample[2].get(j,1))>=.01 for j in joint_names(rid)):continue
                seen.add(stamp)
                score=cv2.Laplacian(cv2.cvtColor(pixels,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()
                choices.append((score,msg,info,detected,pixels,tf,joint_sample))
                if len(choices)>=5:break
            time.sleep(.02)
        if len(choices)<5:raise CaptureFailure(f'{rid}: only {len(choices)} of five valid fresh board views within capture timeout')
        _,msg,info,detected,pixels,tf,joint_sample=max(choices,key=lambda item:item[0])
        folder=self.session/rid;folder.mkdir(exist_ok=True)
        name=f'sample_{index:03d}'
        if not cv2.imwrite(str(folder/(name+'_raw.png')),pixels):raise IOError('Cannot save raw image')
        if not cv2.imwrite(str(folder/(name+'_annotated.png')),detected['annotated']):raise IOError('Cannot save annotation')
        record={'schema_version':1,'sample_id':name,'robot_id':rid,'role':pose['role'],'candidate':pose['candidate'],
                'stamp':[msg.header.stamp.sec,msg.header.stamp.nanosec],
                'T_base_tool0':tf_matrix(tf).tolist(),'T_camera_board':detected['T_camera_board'].tolist(),
                'camera_matrix':np.asarray(info.k).reshape(3,3).tolist(),'distortion':list(info.d),
                'camera_info':{'frame':info.header.frame_id,'width':info.width,'height':info.height,'k':list(info.k),'d':list(info.d),'r':list(info.r),'p':list(info.p),'distortion_model':info.distortion_model},
                'joint_stamp':joint_sample[0],
                'object_points':detected['object_points'],'image_points':detected['image_points'],
                'corners':detected['corners'],'reprojection_rms_px':detected['reprojection_rms_px'],
                'joint_names':joint_names(rid),'joints':[joint_sample[1][j] for j in joint_names(rid)]}
        atomic_json(folder/(name+'.json'),record)
        return record

    def measure_cohort(self,ids,records):
        self.status(cohort=list(ids),active_robots=list(ids),robot_id=ids[0],accepted=0,
                    target=self.plan['samples_per_robot'])
        spare={r:iter(self.plan['plans'][r]['reserve']) for r in ids}
        for index in range(self.plan['samples_per_robot']):
            pending={r:dict(self.plan['plans'][r]['poses'][index]) for r in ids}
            attempts={r:0 for r in ids}
            while pending:
                self.wait_unpaused()
                try:
                    self.move_many({r:p['joints'] for r,p in pending.items()})
                    self.hold_positions=dict(self.positions)
                    self.status('CAPTURING',active_robots=list(pending),robot_id=next(iter(pending)),
                                message='Je Kamera das schärfste von fünf frischen Bildern auswählen')
                    after=self.clock_value;outcomes={}
                    with ThreadPoolExecutor(max_workers=len(pending),thread_name_prefix='calibration_capture') as pool:
                        captures={r:pool.submit(self.capture,r,pose,index,False,after) for r,pose in pending.items()}
                        for rid,future in captures.items():
                            try:outcomes[rid]=future.result()
                            except Exception as error:
                                outcomes[rid]=error
                                if not isinstance(error,(CaptureFailure,InterruptedError)):self.request_halt(str(error))
                    interrupted=False
                    for rid,outcome in outcomes.items():
                        if isinstance(outcome,InterruptedError):interrupted=True;continue
                        if isinstance(outcome,CaptureFailure):
                            self.get_logger().warn(str(outcome));attempts[rid]+=1
                            self.status(rejected=self.state['rejected']+1,message=str(outcome))
                            if attempts[rid]>=3:
                                try:replacement=dict(next(spare[rid]))
                                except StopIteration:raise ValueError(f'{rid}: reserve poses exhausted') from outcome
                                replacement['role']=pending[rid]['role'];pending[rid]=replacement;attempts[rid]=0
                        elif isinstance(outcome,Exception):raise outcome
                        else:
                            records[rid].append(outcome);pending.pop(rid)
                    counts={r:len(samples) for r,samples in records.items()}
                    self.status(counts=counts,accepted=min(counts[r] for r in ids))
                    if self.abort.is_set():raise InterruptedError('Cohort stopped; accepted observations preserved')
                    if interrupted:self.wait_unpaused()
                except InterruptedError:
                    if self.abort.is_set():raise
                    self.wait_unpaused()

    def run_stages(self,records,run_start):
        for index,stage in enumerate(self.plan['stages']):
            self.wait_unpaused()
            self.status(stage_index=index+1,stage_total=len(self.plan['stages']))
            if stage['kind']=='measure':
                self.measure_cohort(stage['robots'],records)
                continue
            rid=stage['robot'];target=stage['target']
            if stage['kind']=='returning':target=[run_start[j] for j in joint_names(rid)]
            self.status(cohort=[])
            while True:
                try:
                    self.move_many({rid:target},stage['kind'].upper())
                    parked=set(self.state.get('parked_robots',[]))
                    if stage['kind']=='parking':parked.add(rid)
                    else:parked.discard(rid)
                    self.status(parked_robots=sorted(parked))
                    break
                except InterruptedError:
                    if self.abort.is_set():raise
                    self.wait_unpaused()

    def execute(self,goal):
        self.run_handle=goal;self.running=True;records={r:[] for r in self.plan['robots']}
        result=RunCalibration.Result()
        try:
            self.require_telemetry();self.require_controllers(ROBOT_IDS if self.plan['mode']=='diagonal_pairs' else self.plan['robots'])
            if fingerprint(self.description)!=self.plan['description_fingerprint']:raise ValueError('Cell model changed since preparation')
            if any(abs(self.positions.get(j,q)-q)>.015 for j,q in self.plan['start'].items()):raise ValueError('Joint state changed since preparation; prepare again')
            for rid,expected in self.plan['matrices'].items():
                info=self.infos.get(rid)
                if (info is None or info.header.frame_id!=expected['frame'] or
                    (info.width,info.height)!=(expected['width'],expected['height']) or
                    not np.allclose(info.k,np.asarray(expected['k']).ravel()) or list(info.d)!=expected['d']):
                    raise ValueError('CameraInfo changed since preparation; prepare again')
            self.frozen=dict(self.positions)
            self.status('RUNNING',message='Messfahrt gestartet')
            run_start=dict(self.positions)
            self.plan['run_start']=run_start;self.plan['run_start_stamp']=self.clock_value
            atomic_json(self.session/'plan.json',self.plan)
            self.run_stages(records,run_start)
            self.status('SOLVING',robot_id='',active_robots=[],cohort=[],message='Hand-Auge-Schätzung und unabhängige Validierung')
            solved=self.ensure_planner().call({'op':'solve','records':records},self.halted)
            if self.halted():raise InterruptedError('Solving stopped')
            solved['description_fingerprint']=fingerprint(self.description)
            solved['session_dir']=str(self.session)
            solved['robot_sessions']={r:str(self.session) for r in solved['robots']}
            solved['table_bases']={r:(table_board_transform(self.layout['charuco'],self.layout['robots'][r]['table'])@
                                       np.linalg.inv(fit['T_base_board'])).tolist() for r,fit in solved['robots'].items()}
            # Truth is obtained only after fitting, and is stored separately.
            truth={}
            for rid in records:
                table=self.layout['robots'][rid]['table']
                x=tf_matrix(self.buffer.lookup_transform(f'{rid}_tool0',f'{rid}_wrist_camera_optical_frame',Time()))
                y=tf_matrix(self.buffer.lookup_transform(f'{rid}_base_link',f'{table}_charuco',Time()))
                truth[rid]={'T_tool0_camera':x.tolist(),'T_base_board':y.tolist(),
                            'handeye_error':pose_error(np.asarray(solved['robots'][rid]['T_tool0_camera']),x)}
            validation={'robots':truth,'relative_bases':{}}
            for table,pair in solved['relative_bases'].items():
                gt=np.asarray(truth[table+'_front']['T_base_board'])@np.linalg.inv(truth[table+'_rear']['T_base_board'])
                validation['relative_bases'][table]=pose_error(np.asarray(pair['T_front_rear']),gt)
            atomic_json(self.session/'ground_truth_validation.json',validation)
            atomic_json(self.session/'result.json',solved)
            result.success=solved['passed'];result.result_path=str(self.session/'result.json')
            result.message='Calibration passed' if result.success else 'Independent validation failed'
            with self.motion_lock:
                if self.halted():raise InterruptedError('Session stopped before publishing result')
                self.status('COMPLETE',result_path=result.result_path,message=result.message,ground_truth=validation,
                            summary={r:{k:v for k,v in fit.items() if k not in ('bootstrap_base_board','validation_samples')} for r,fit in solved['robots'].items()},
                            relative_bases=solved['relative_bases'],table_bases=solved['table_bases'])
                if result.success:goal.succeed()
                else:goal.abort()
        except InterruptedError:
            result.success=False;result.message='Session stopped; accepted observations preserved'
            if goal.is_cancel_requested:goal.canceled()
            else:goal.abort()
        except Exception as error:
            self.request_halt(str(error));result.success=False;result.message=str(error);goal.abort()
            self.get_logger().error(str(error))
        finally:
            self.running=False;self.goal_reserved=False;self.run_handle=None
        return result

    def apply(self,request,response):
        with self.mutex:
            if self.state['phase'] not in ('COMPLETE','READY','IDLE','STOPPED','ERROR') or self.goal_reserved or (self.operation_thread and self.operation_thread.is_alive()):
                response.accepted=False;response.message='Apply is allowed only while idle and stationary';return response
            if not request.client_id:
                response.accepted=False;response.message='A responsive client ID is required';return response
            self.abort.clear();self.pause.clear();self.frozen=dict(self.positions)
            self.owner=request.client_id;self.heartbeat=time.monotonic()
            self.status('APPLYING',message='Prüfe und aktiviere getrenntes kalibriertes Modell')
        try:
            self.require_telemetry()
            path=Path(request.result_path).resolve()
            profile=json.loads(path.read_text());validate_result(profile)
            if profile.get('description_fingerprint')!=fingerprint(self.description):raise ValueError('Result does not match current cell geometry')
            active=self.root/'profiles/active.json'
            if active.is_file():
                previous=json.loads(active.read_text())
                if previous.get('description_fingerprint')==profile['description_fingerprint']:
                    validate_result(previous)
                    profile['robots']={**previous['robots'],**profile['robots']}
                    profile['robot_sessions']={**previous.get('robot_sessions',{}),**profile.get('robot_sessions',{})}
                    from .solver import relative_bases
                    profile['relative_bases']=relative_bases(profile['robots'])
            profile['table_bases']={r:(table_board_transform(self.layout['charuco'],self.layout['robots'][r]['table'])@
                                     np.linalg.inv(fit['T_base_board'])).tolist() for r,fit in profile['robots'].items()}
        except Exception as error:
            if not self.abort.is_set():self.status('ERROR',message=f'Profil nicht übernommen: {error}')
            response.accepted=False;response.message=str(error);return response
        self.operation_thread=self.spawn(lambda:self.apply_work(profile,path))
        response.accepted=True;response.message='Profile activation started';return response

    def install_model(self,profile,commit=None,rollback=None):
        validate_result(profile)
        description=calibrated_description(self.description,self.layout,profile)
        parsed=ET.fromstring(description)
        candidate=PlanningProcess(description,self.root/'calibrated_planning')
        try:
            if not candidate.call({'op':'check','positions':dict(self.positions)},self.halted):raise ValueError('Calibrated planning scene is in collision')
        except Exception:candidate.cancel();raise
        committed=False
        try:
            self.require_telemetry()
            with self.motion_lock:
                if self.halted():raise InterruptedError('Model activation stopped')
                if commit:commit();committed=True
                self.description_pub.publish(String(data=description))
                old=self.planner;self.planner=candidate;self.active_description=description;self.model_xml=parsed
        except Exception:
            candidate.cancel()
            if committed and rollback:rollback()
            raise
        if old:old.cancel()

    def apply_work(self,profile,path):
        previous=self.active_description;old_profile=self.state['active_profile']
        try:
            profiles=self.root/'profiles';profiles.mkdir(exist_ok=True)
            active=profiles/'active.json'
            saved=json.loads(active.read_text()) if active.is_file() else None
            destination=profiles/((self.session.name+'_' if self.session else '')+uuid.uuid4().hex[:8]+'.json')
            def commit():
                atomic_json(destination,profile);atomic_json(active,profile)
            def rollback():
                if saved is None:active.unlink(missing_ok=True)
                else:atomic_json(active,saved)
            self.install_model(profile,commit,rollback)
            self.status('STOPPED' if self.abort.is_set() else 'COMPLETE',active_profile=str(destination),message='Kalibriertes TF- und Planungsmodell aktiv; Gazebo unverändert',
                        **self.result_fields(profile,path))
            self.plan=None;self.state['plan_id']=''
        except Exception as error:
            # No active profile file is replaced until the new model has loaded successfully.
            self.active_description=previous;self.state['active_profile']=old_profile
            self.status('ERROR',message=f'Profil nicht übernommen: {error}')

    def publish_model(self):
        if self.model_xml is None or not self.positions:return
        stamp=self.get_clock().now().to_msg()
        transforms=[]
        for joint in self.model_xml.findall('joint'):
            msg=TransformStamped();msg.header.stamp=stamp;msg.header.frame_id=joint.find('parent').get('link');msg.child_frame_id=joint.find('child').get('link')
            origin=joint.find('origin')
            xyz=np.fromstring(origin.get('xyz','0 0 0'),sep=' ') if origin is not None else np.zeros(3)
            rpy=np.fromstring(origin.get('rpy','0 0 0'),sep=' ') if origin is not None else np.zeros(3)
            rotation=Rotation.from_euler('xyz',rpy)
            if joint.get('type') in ('revolute','continuous'):
                axis=np.fromstring(joint.find('axis').get('xyz'),sep=' ')
                rotation=rotation*Rotation.from_rotvec(axis*self.positions.get(joint.get('name'),0))
            msg.transform.translation.x,msg.transform.translation.y,msg.transform.translation.z=map(float,xyz)
            q=rotation.as_quat();msg.transform.rotation.x,msg.transform.rotation.y,msg.transform.rotation.z,msg.transform.rotation.w=map(float,q)
            transforms.append(msg)
        self.broadcaster.sendTransform(transforms)

    def close(self):
        self.request_halt('Calibration backend shutting down')
        if self.halt_thread:self.halt_thread.join(timeout=2)
        self.shutdown_event.set()
        if self.planner:self.planner.cancel()
        fcntl.flock(self.lockfile,fcntl.LOCK_UN);self.lockfile.close()


def main():
    if os.environ.get('ROS_DOMAIN_ID')!='64' or os.environ.get('GZ_PARTITION')!='uwa_cell_sim':
        raise SystemExit('Source UWA scripts/env.bash: only simulation domain 64 / uwa_cell_sim is permitted')
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=Backend();executor=MultiThreadedExecutor(num_threads=8);executor.add_node(node)
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
    spin=threading.Thread(target=executor.spin,daemon=True);spin.start()
    try:
        while not stop.wait(.1):pass
    finally:
        node.close();executor.shutdown(timeout_sec=3);spin.join(timeout=2);node.destroy_node();rclpy.shutdown()

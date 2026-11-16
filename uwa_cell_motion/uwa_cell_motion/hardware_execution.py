"""Explicit PTP execution against four independent UR controller managers."""
import json
from pathlib import Path
import tempfile
import time
import numpy as np
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers,SwitchController,ListHardwareComponents
from .node import MotionNode
from .common import ROBOT_IDS,joint_names,dump
from .execution import MotionClient,motion_context,_follow
from .hardware_model import HardwareProblem
from .hardware_state import require_domain,signature,Peer
from .hardware_ports import StopPort,HOLD,unsafe_controllers,matching_hardware


class HardwareClient(MotionClient):
    def __init__(self,problem,mode,selected=()):
        require_domain(mode);MotionNode.__init__(self,'hardware_ptp_execution',namespace='/uwa_cell')
        self.problem,self.cfg,self.mode=problem,problem.cfg,mode;self.selected=list(selected);self.names=problem.names
        self.expected=signature(problem,mode);self.state_peer=Peer();self.guard_peer=Peer();self.supervisor_peer=Peer()
        self.guard=None;self.supervisor=None;self.records={};self.epochs={};self.driver={};self.state_received=-float('inf')
        self.guard_received=self.supervisor_received=self.received=self.source_advanced=-float('inf');self.stamp=-float('inf')
        self.positions={};self.velocities={};self.live_signature=None;self.minimum_clearance=float('inf')
        self.handles={};self.pending={};self.owned=set();self.clock_reversed=False
        self.standstill_velocity={j:(self.cfg['standstill_velocity_rad_s'] if j in joint_names(r) else 0.) for r,n in self.names.items() for j in n}
        self.actions={r:ActionClient(self,FollowJointTrajectory,p['namespace']+'/'+('joint_trajectory_controller' if mode=='mock' else 'scaled_joint_trajectory_controller')+'/follow_joint_trajectory') for r,p in problem.profiles.items()}
        self.stop_clients={r:self.create_client(Trigger,'/uwa_cell/collision_supervisor/'+r+'/stop') for r in ROBOT_IDS}
        self.create_subscription(String,'/uwa_cell/hardware_state',self.state,1)
        self.create_subscription(String,'/uwa_cell/collision_guard/decision',self.guard_message,1)
        self.create_subscription(String,'/uwa_cell/collision_supervisor/status',self.supervisor_message,1)
        for rid in self.selected:
            self.create_subscription(JointState,problem.profiles[rid]['namespace']+'/joint_states',lambda msg,r=rid:self.driver_state(r,msg),qos_profile_sensor_data)
        self.event_executor=SingleThreadedExecutor();self.event_executor.add_node(self)
    def accept(self,peer,msg):
        try:
            value=json.loads(msg.data)
            if not isinstance(value,dict):return None
            if type(value.get('armed')) is not bool:return None
            return value if peer.receive(value,time.monotonic(),self.expected,value['armed']) else None
        except (ValueError,TypeError):return None
    def state(self,msg):
        value=self.accept(self.state_peer,msg)
        if value is None:return
        self.records=value['records'];self.positions=dict(value['model_state']);self.velocities={}
        for rid,names in self.names.items():
            if rid not in self.records:continue
            record=self.records[rid];self.velocities.update(zip(names[:6],record['v']))
            if len(names)>6:self.velocities[names[6]]=0.
            if rid in self.epochs and self.epochs[rid]!=record['epoch']:self.clock_reversed=True
            self.epochs[rid]=record['epoch']
        self.received=self.state_received=time.monotonic();self.stamp=value['assembled_wall_time_s'];self.live_signature=value['model_signature']
    def guard_message(self,msg):
        value=self.accept(self.guard_peer,msg)
        if value is not None:
            self.guard=value;self.guard_received=time.monotonic()
            if value.get('pairs'):self.minimum_clearance=min(self.minimum_clearance,*(p['clearance_m'] for p in value['pairs']))
    def supervisor_message(self,msg):
        value=self.accept(self.supervisor_peer,msg)
        if value is not None:self.supervisor=value;self.supervisor_received=time.monotonic()
    def driver_state(self,rid,msg):
        q=dict(zip(msg.name,msg.position));v=dict(zip(msg.name,msg.velocity));names=joint_names(rid)
        if all(j in q and j in v for j in names) and np.isfinite([q[j] for j in names]+[v[j] for j in names]).all():
            stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9;old=self.driver.get(rid)
            advanced=time.monotonic() if old is None or stamp>old['stamp'] else old['advanced']
            self.driver[rid]=dict(q=[q[j] for j in names],stamp=stamp,received=time.monotonic(),advanced=advanced)
    def health(self):
        for _ in range(20):self.spin_once(timeout_sec=0.)
        now=time.monotonic();timeout=self.cfg['state_timeout_s']
        if self.clock_reversed:raise RuntimeError('Device epoch changed; regenerate the hardware plan')
        if not self.state_peer.fresh(now,timeout) or set(self.records)!=set(ROBOT_IDS):raise RuntimeError('HARDWARE STATE STALE')
        for rid,record in self.records.items():
            if max(now-record['received'],now-record['source_stamp'])>timeout:raise RuntimeError(rid+': DEVICE STATE STALE')
        if not self.guard_peer.fresh(now,self.cfg['heartbeat_timeout_s']) or not self.supervisor_peer.fresh(now,self.cfg['heartbeat_timeout_s']):raise RuntimeError('HARDWARE SUPERVISION LOST')
        if not self.guard.get('model_match') or self.live_signature!=self.problem.signature:raise RuntimeError('Hardware driver/cell model unconfirmed')
        if self.selected and (not self.guard['armed'] or not self.supervisor['armed'] or not self.supervisor['witness_available']):raise RuntimeError('Hardware backend is monitor-only or witness unavailable')
        for rid in self.selected:
            port=self.supervisor.get('ports',{}).get(rid,{})
            if not port.get('hardware_mode_verified') or not port.get('manager_fresh') or not port.get('hold_config_verified'):raise RuntimeError(rid+': hardware manager/hold configuration unavailable')
            if self.mode=='hardware':
                status=self.records[rid]['status']
                if status['robot_mode']!=7 or status['runtime_state']!=2 or status['safety_mode'] not in (1,2):raise RuntimeError(rid+': native robot/program is not ready; no automatic power/brake/play')
            driver=self.driver.get(rid)
            if driver is None or max(now-driver['received'],now-driver['advanced'])>timeout:raise RuntimeError(rid+': driver JointStates unavailable/stale')
            if np.max(abs(np.asarray(driver['q'])-self.records[rid]['q']))>.005:raise RuntimeError(rid+': driver cache differs from independent actual joints')
    def connect(self,guard=True):
        self.wait(lambda:len(self.positions)==sum(map(len,self.names.values())) and self.guard is not None and self.supervisor is not None,timeout=15.)
        if guard:
            self.wait(lambda:all(r in self.driver for r in self.selected),timeout=5.);self.health()
    def manager(self,rid,kind,endpoint,request):
        return self.service(kind,self.problem.profiles[rid]['namespace']+'/controller_manager/'+endpoint,request)
    def activate(self,arms):
        if not set(arms)<=set(self.selected):raise RuntimeError('Arm was not selected for verified hardware execution')
        self.health();blocked=set(self.guard['blocked_arms'])|set(self.supervisor['blocked_arms'])
        if blocked&set(arms):raise RuntimeError('Hardware stop latch requires explicit reset')
        for rid in arms:
            components=self.manager(rid,ListHardwareComponents,'list_hardware_components',ListHardwareComponents.Request())
            if not matching_hardware(components.component,joint_names(rid),self.mode):raise RuntimeError(rid+': hardware/mock plugin mismatch')
            controllers=self.manager(rid,ListControllers,'list_controllers',ListControllers.Request()).controller
            name='joint_trajectory_controller' if self.mode=='mock' else 'scaled_joint_trajectory_controller'
            if not any(c.name==name and c.state in ('active','inactive') for c in controllers):raise RuntimeError(rid+': trajectory controller not configured')
            request=SwitchController.Request();request.strictness=SwitchController.Request.STRICT;request.activate_asap=True;request.timeout.sec=1
            request.deactivate_controllers=[n for n in unsafe_controllers(controllers,joint_names(rid)) if n!=name]
            if any(c.name==HOLD and c.state=='active' for c in controllers):raise RuntimeError(rid+': resource hold has not been released')
            request.activate_controllers=[] if any(c.name==name and c.state=='active' for c in controllers) else [name]
            self.owned.add(rid)
            if request.activate_controllers or request.deactivate_controllers:
                if not self.manager(rid,SwitchController,'switch_controller',request).ok:raise RuntimeError(rid+': controller activation rejected')
            self.health()
    def hold_idle_tools(self):return []  # tools are unobserved; no gripper command is sent
    def stop(self,arms):
        arms=set(arms);requests=[];errors=[]
        for rid in arms:
            if rid in self.handles and self.handles[rid].accepted:self.handles[rid].cancel_goal_async()
            client=self.stop_clients[rid]
            if client.service_is_ready():requests.append(client.call_async(Trigger.Request()))
        ports={r:StopPort(self,self.problem.profiles[r],self.cfg,self.mode) for r in arms};end=time.monotonic()+2.;held=set()
        while time.monotonic()<end:
            self.spin_once(timeout_sec=.01);held={r for r,p in ports.items() if p.tick(True,True)['held']}
            if held==arms and all(f.done() for f in requests):break
        ack=len(requests)==len(arms) and all(f.done() and f.result() is not None and f.result().success for f in requests)
        for rid,p in ports.items():
            if rid not in held:p.native_stop();errors.append(rid+': resource hold unconfirmed; native STOP requested')
        return dict(resource_holds_confirmed=held==arms,latches_confirmed=ack,errors=errors)


def execute(plan,output,mode):
    require_domain(mode)
    if not plan.get('success') or not plan.get('hardware_plan') or plan.get('execution_mode')!=mode:raise ValueError('Successful explicitly bound hardware/mock plan required')
    cfg=plan['config'];result=dict(success=False,guard_stops=0,phase_count=0,record_path=str(output),stage='CONNECT');began=time.monotonic()
    with motion_context(),tempfile.TemporaryDirectory(prefix='uwa-hardware-execute-') as directory:
        problem=HardwareProblem(directory,cfg,plan['inventory'],plan.get('layout_path'))
        if problem.binding!=plan['hardware_binding'] or problem.spheres.geometry.assets!=plan['mesh_sha256']:raise ValueError('Hardware model/inventory/config changed; replan')
        client=HardwareClient(problem,mode,plan['request']['selected'])
        try:
            client.connect();request=plan['request']
            if max(abs(client.positions[j]-request['start'][j]) for n in problem.names.values() for j in n)>.002:raise ValueError('Actual start changed; regenerate the hardware plan (no automatic reposition)')
            # Revalidate all timing/limits/full-cell collision states before any controller activation.
            verified=problem.time_parameterize(request,plan['trajectory']['waypoints'])
            if verified!=plan['trajectory']:raise ValueError('Trajectory differs from deterministic validated timing')
            result['stage']='EXECUTION';_follow(problem,client,plan,result)
            result.update(success=not result['stopped_arms'],final_positions=dict(client.positions),actual_wall_s=time.monotonic()-began)
            if result['success']:result['stage']='COMPLETE'
        except BaseException as error:
            result['error']=str(error)
            if client.owned:result['stop_result']=client.stop(client.owned)
        finally:
            result.update(guard_status=client.guard,supervisor_status=client.supervisor,total_wall_s=time.monotonic()-began,
                stop_budget_qualification='NOT MEASURED ON HARDWARE',execution_mode=mode)
            if not result['success'] and not result.get('error'):result['error']='Hardware interlock stopped selected arms'
            dump(output,result);client.destroy_node()
    return result

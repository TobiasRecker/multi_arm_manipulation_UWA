"""Hardware-only geometric guard, resource supervisor and independent witness.

All start in monitor mode unless explicitly armed. No robot startup, power,
brakes, program load/play or protective-stop recovery is implemented here.
"""
import json
import tempfile
import threading
import time
import uuid
import numpy as np
import rclpy
from rclpy.clock import Clock,ClockType
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker,MarkerArray
from .node import MotionNode
from .common import ROBOT_IDS,PAIRS,all_names
from .guard_core import GuardState
from .guard_node import CollisionGuard
from .interlock import Interlock,expired_pair_leases
from .hardware_model import HardwareProblem,matching_arm
from .hardware_state import require_domain,signature,packet,Peer,DeviceStates,RtdeStates
from .hardware_ports import StopPort
from .status_markers import interlock_markers


def decode(message):
    try:
        value=json.loads(message.data)
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):return {}


class HardwareGuard(MotionNode):
    show=CollisionGuard.show
    def __init__(self,cfg,inventory,layout=None,mode='mock',armed=False,source=None):
        require_domain(mode);super().__init__('hardware_collision_guard',namespace='/uwa_cell')
        self.directory=tempfile.TemporaryDirectory(prefix='uwa-hardware-guard-')
        self.problem=HardwareProblem(self.directory.name,cfg,inventory,layout);self.layout=self.problem.layout
        self.names=self.problem.names;self.model=self.problem.spheres;self.cfg=cfg;self.core=GuardState(cfg)
        self.signature=self.problem.signature;self.hardware_signature=signature(self.problem,mode)
        self.mode,self.armed=mode,armed;self.instance=str(uuid.uuid4());self.sequence=0
        self.positions={};self.pairs=[];self.records={};self.playing={};self.supervisor_status={};self.supervisor=Peer();self.model_match={r:False for r in ROBOT_IDS}
        self.source=source or (RtdeStates(self.problem.profiles,cfg['state_timeout_s']) if mode=='hardware' else DeviceStates())
        self.last_source={};self.epochs={};self.source_faults=[];self.previous_blocked=set()
        self.publisher=self.create_publisher(String,'/uwa_cell/collision_guard/decision',1)
        self.state_pub=self.create_publisher(String,'/uwa_cell/hardware_state',1)
        self.joints_pub=self.create_publisher(JointState,'/uwa_cell/joint_states',qos_profile_sensor_data)
        self.model_joints_pub=self.create_publisher(JointState,'/uwa_cell/model_joint_states',qos_profile_sensor_data)
        self.markers=self.create_publisher(MarkerArray,'/uwa_cell/collision_guard/markers',1)
        self.description_pub=self.create_publisher(String,'/uwa_cell/robot_description',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.description_pub.publish(String(data=self.problem.description))
        for rid,p in self.problem.profiles.items():
            self.create_subscription(String,p['namespace']+'/robot_description',lambda msg,r=rid:self.description(r,msg),
                QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
            if mode=='mock':self.create_subscription(JointState,p['namespace']+'/joint_states',lambda msg,r=rid:self.mock_receive(r,msg),qos_profile_sensor_data)
        self.create_subscription(String,'/uwa_cell/collision_supervisor/status',self.backend,1)
        self.create_service(Trigger,'/uwa_cell/collision_guard/reset',self.reset)
        self.wall_clock=Clock(clock_type=ClockType.STEADY_TIME);self.create_timer(1/cfg['rate_hz'],self.tick,clock=self.wall_clock)
    def description(self,rid,msg):self.model_match[rid]=matching_arm(msg.data,self.problem.original_description,rid)
    def mock_receive(self,rid,msg):
        q=dict(zip(msg.name,msg.position));v=dict(zip(msg.name,msg.velocity));names=self.problem.profiles[rid]['joint_names']
        if all(j in q and j in v for j in names):self.source.accept(rid,msg.header.stamp.sec+msg.header.stamp.nanosec/1e9,[q[j] for j in names],[v[j] for j in names],time.monotonic())
    def backend(self,msg):
        value=decode(msg)
        if self.supervisor.receive(value,time.monotonic(),self.hardware_signature,self.armed):self.supervisor_status=value
    def update(self,now):
        records,errors=self.source.snapshot();faults=[]
        for rid,record in records.items():
            status=record['status'];affected=sorted({r for pair in PAIRS if rid in pair for r in pair})
            if status['safety_mode'] not in (1,2):faults.append(dict(arms=affected,reason='NATIVE SAFETY STOP: '+rid))
            if self.playing.get(rid,False) and status['runtime_state']!=2:faults.append(dict(arms=affected,reason='NATIVE PROGRAM INTERRUPTED: '+rid))
            self.playing[rid]=status['runtime_state']==2
            if self.epochs.get(rid,record['epoch'])!=record['epoch']:
                affected=[r for pair in PAIRS if rid in pair for r in pair]
                faults.append(dict(arms=sorted(set(affected)),reason='DEVICE CLOCK RESET'))
            self.epochs[rid]=record['epoch']
            if record['device_stamp']!=self.last_source.get(rid) or rid not in self.core.records:
                self.core.receive(rid,record['q'],record['v'],record['source_stamp'],record['received'])
                self.last_source[rid]=record['device_stamp']
            self.positions.update(zip(self.names[rid][:6],record['q']))
            if len(self.names[rid])>6:self.positions[self.names[rid][6]]=0.
        for rid,error in errors.items():
            affected=sorted({r for pair in PAIRS if rid in pair for r in pair})
            faults.append(dict(arms=affected,reason='DEVICE STATE INVALID',detail=error))
        for rid,valid in self.model_match.items():
            if not valid:faults.append(dict(arms=sorted({r for pair in PAIRS if rid in pair for r in pair}),reason='DRIVER MODEL UNCONFIRMED: '+rid))
        available=self.supervisor.fresh(now,self.cfg['heartbeat_timeout_s'])
        if not available:faults.append(dict(arms=list(ROBOT_IDS),reason='STOP ADAPTER LOST'))
        elif self.armed:
            for rid,port in self.supervisor_status.get('ports',{}).items():
                if not port.get('manager_fresh') or not port.get('hardware_mode_verified') or not port.get('hold_config_verified'):
                    faults.append(dict(arms=sorted({r for pair in PAIRS if rid in pair for r in pair}),reason='ARM STOP ADAPTER UNAVAILABLE: '+rid))
        self.core.external_faults=faults;self.records=records
        velocities={r:np.r_[v['v'],0.] if len(self.names[r])>6 else np.asarray(v['v']) for r,v in records.items()}
        ages={r:max(now-v['received'],now-v['source_stamp']) for r,v in records.items()}
        world,self.pairs=self.model.pairs(self.positions,velocities,ages,self.cfg,partial=True)
        return world,available
    def tick(self):
        now=time.monotonic()
        try:world,available=self.update(now);status=self.core.evaluate(self.pairs,now,now)
        except Exception as error:
            self.core.latched.update(ROBOT_IDS);world={};available=False
            status=dict(state='STATE STALE',blocked_arms=list(ROBOT_IDS),faults=[dict(arms=list(ROBOT_IDS),reason=str(error))],latched_causes=[],reset_sequence=self.core.reset_sequence,reset_arms=[])
        if not available:status['state']='STOP ADAPTER LOST'
        blocked=set(status['blocked_arms'])
        if blocked-self.previous_blocked:self.get_logger().error(('STOP LATCHED: ' if self.armed else 'MONITOR WOULD STOP: ')+json.dumps(status.get('latched_causes',status['faults'])))
        self.previous_blocked=blocked
        self.sequence+=1
        status.update(packet(self.hardware_signature,self.armed,self.instance,self.sequence),evaluated_monotonic_s=now,pairs=self.pairs,
            model_signature=self.signature,model_match=all(self.model_match.values()),guard_config_signature=self.hardware_signature,
            source_time_s=now,stop_adapter_available=available,state_ages_s={r:now-v['received'] for r,v in self.records.items()},
            stationary_arms=[r for r in ROBOT_IDS if self.core.fresh(r,now,now) and self.core.stationary(r,now)],
            runtime_label=self.mode.upper()+('\nSTOP-GUARD-ARMED' if self.armed else '\nMONITOR-ONLY')+'\nStop-reserve:UNMEASURED\nTool:opening-envelope',
            model_uncertainty='World/table anchors provisional; hardware stop reserve unmeasured; gripper opening unobserved')
        self.publisher.publish(String(data=json.dumps(status,allow_nan=False)))
        state=packet(self.hardware_signature,self.armed,self.instance,self.sequence,records=self.records,model_state=self.positions,
            model_signature=self.signature,hardware_binding=self.problem.binding,tool_policy='all_openings_envelope_no_gripper_command',
            assembled_wall_time_s=self.get_clock().now().nanoseconds/1e9)
        self.state_pub.publish(String(data=json.dumps(state,allow_nan=False)))
        message=JointState();message.header.stamp=self.get_clock().now().to_msg()
        for rid,v in self.records.items():
            message.name.extend(self.names[rid][:6]);message.position.extend(v['q']);message.velocity.extend(v['v'])
        self.joints_pub.publish(message)
        # A separate, explicitly model-only stream supplies the fixed zero
        # coordinate of swept envelopes. It is not gripper telemetry.
        model_message=JointState();model_message.header=message.header
        model_message.name=list(message.name);model_message.position=list(message.position);model_message.velocity=list(message.velocity)
        for rid in self.records:
            if len(self.names[rid])>6:model_message.name.append(self.names[rid][6]);model_message.position.append(0.);model_message.velocity.append(0.)
        self.model_joints_pub.publish(model_message);self.show(world,status)
    def reset(self,request,response):
        now=time.monotonic()
        try:self.update(now);response.success,response.message=self.core.reset(self.pairs,now,now)
        except Exception as error:response.success=False;response.message=str(error)
        return response
    def destroy_node(self):
        if hasattr(self.source,'close'):self.source.close()
        self.directory.cleanup();return super().destroy_node()


class HardwareSupervisor(MotionNode):
    def __init__(self,cfg,inventory,layout=None,mode='mock',armed=False):
        require_domain(mode);super().__init__('hardware_collision_supervisor',namespace='/uwa_cell')
        self.directory=tempfile.TemporaryDirectory(prefix='uwa-hardware-supervisor-');self.problem=HardwareProblem(self.directory.name,cfg,inventory,layout)
        self.cfg,self.mode,self.armed=cfg,mode,armed;self.signature=signature(self.problem,mode)
        self.instance=str(uuid.uuid4());self.sequence=0;self.guard=Peer();self.witness=Peer();self.lock=threading.RLock();self.group=ReentrantCallbackGroup()
        self.core=Interlock(cfg['heartbeat_timeout_s']);self.stopping_since={};self.ports={r:StopPort(self,p,cfg,mode,self.group) for r,p in self.problem.profiles.items()}
        self.publisher=self.create_publisher(String,'/uwa_cell/collision_supervisor/status',1)
        self.markers=self.create_publisher(MarkerArray,'/uwa_cell/collision_supervisor/markers',1)
        self.geometry_markers=self.create_publisher(MarkerArray,'/uwa_cell/collision_guard/markers',1)
        self.reset_guard=self.create_client(Trigger,'/uwa_cell/collision_guard/reset',callback_group=self.group)
        self.reset_witness=self.create_client(Trigger,'/uwa_cell/hardware_watchdog/reset',callback_group=self.group)
        self.create_subscription(String,'/uwa_cell/collision_guard/decision',self.receive,1,callback_group=self.group)
        self.create_subscription(String,'/uwa_cell/hardware_watchdog/status',lambda msg:self.witness.receive(decode(msg),time.monotonic(),self.signature,self.armed),1,callback_group=self.group)
        self.create_service(Trigger,'/uwa_cell/collision_supervisor/reset',self.reset,callback_group=self.group)
        for rid in ROBOT_IDS:self.create_service(Trigger,'/uwa_cell/collision_supervisor/'+rid+'/stop',lambda request,response,r=rid:self.stop(r,response),callback_group=self.group)
        self.wall_clock=Clock(clock_type=ClockType.STEADY_TIME);self.create_timer(.02,self.tick,clock=self.wall_clock)
    def receive(self,msg):
        value=decode(msg);now=time.monotonic()
        with self.lock:
            if self.guard.receive(value,now,self.signature,self.armed):self.core.receive(value,now)
    def stop(self,rid,response):
        with self.lock:self.core.pending_reset=None;self.core.blocked.add(rid);self.core.reason='STOP REQUESTED'
        response.success=True;response.message='STOP LATCHED; measured standstill not yet confirmed';return response
    def request(self,client):
        if not client.service_is_ready():raise RuntimeError('Reset peer unavailable')
        future=client.call_async(Trigger.Request());event=threading.Event();future.add_done_callback(lambda _:event.set())
        if not event.wait(3.):raise RuntimeError('Reset peer timed out')
        if not future.result().success:raise RuntimeError(future.result().message)
        return future.result()
    def reset(self,request,response):
        try:
            now=time.monotonic()
            if not self.guard.fresh(now,self.cfg['heartbeat_timeout_s']) or not self.witness.fresh(now,self.cfg['heartbeat_timeout_s']):raise RuntimeError('Supervision unavailable')
            if self.armed and not any(p.verified and p.hardware_verified and time.monotonic()-p.received<=.25 and time.monotonic()-p.hardware_received<=.25 for p in self.ports.values()):raise RuntimeError('No provisioned fresh matching manager available')
            self.request(self.reset_witness)
            end=time.monotonic()+1.
            while self.witness.value.get('tripped',True):
                if time.monotonic()>end:raise RuntimeError('Watchdog reset status unavailable')
                time.sleep(.005)
            with self.lock:
                if not self.core.request_reset(time.monotonic()):raise RuntimeError('Guard reset not eligible')
            answer=self.request(self.reset_guard);response.success=True;response.message=answer.message+'; no trajectory/program activated'
        except Exception as error:
            with self.lock:self.core.pending_reset=None
            response.success=False;response.message=str(error)
        return response
    def tick(self):
        now=time.monotonic()
        with self.lock:
            blocked=self.core.tick(now)
            if not self.guard.fresh(now,self.cfg['heartbeat_timeout_s']):self.core.blocked.update(ROBOT_IDS);self.core.reason='GUARD LOST'
            if self.core.last:
                expired=expired_pair_leases(self.core.last,now,self.cfg)
                if expired:self.core.blocked.update(expired);self.core.reason='PAIR SUPERVISION EXPIRED'
            if not self.witness.fresh(now,self.cfg['heartbeat_timeout_s']) or self.witness.value.get('tripped',True):self.core.blocked.update(ROBOT_IDS);self.core.reason='WATCHDOG LOST OR TRIPPED'
            blocked=set(self.core.blocked);ports={r:p.tick(r in blocked,self.armed) for r,p in self.ports.items()};held=[r for r,p in ports.items() if p['held']]
            if self.armed:
                failed=[r for r,p in ports.items() if not p['manager_fresh'] or not p['hardware_mode_verified'] or not p['hold_config_verified']]
                if failed:
                    affected={r for pair in PAIRS if set(pair)&set(failed) for r in pair};self.core.blocked.update(affected);self.core.reason='ARM STOP ADAPTER UNAVAILABLE'
                    for rid in affected-blocked:ports[rid]=self.ports[rid].tick(True,True)
                    blocked=set(self.core.blocked);held=[r for r,p in ports.items() if p['held']]
                for rid in ROBOT_IDS:
                    if rid not in blocked:self.stopping_since.pop(rid,None);continue
                    self.stopping_since.setdefault(rid,now)
                    if now-self.stopping_since[rid]>self.cfg['stop_latency_s'] and rid not in (self.guard.value or {}).get('stationary_arms',[]):
                        self.ports[rid].native_stop()
            self.sequence+=1;status=packet(self.signature,self.armed,self.instance,self.sequence,state=self.core.reason,blocked_arms=sorted(blocked),held_arms=held,
                guard_config_signature=self.signature,interlock_confirmed=self.armed and blocked<=set(held),ports=ports,
                guard_age_s=None if not self.guard.value else now-self.guard.value['evaluated_monotonic_s'],
                witness_available=self.witness.fresh(now,self.cfg['heartbeat_timeout_s']),monitor_only=not self.armed,
                controller_error='; '.join(r+':'+str(p['controller_error']) for r,p in ports.items() if p['controller_error']) or None)
            self.publisher.publish(String(data=json.dumps(status)))
            if self.sequence%5==0:
                markers,lost=interlock_markers(status,self.cfg['heartbeat_timeout_s']);self.markers.publish(markers)
                if lost:self.geometry_markers.publish(MarkerArray(markers=[Marker(action=Marker.DELETEALL)]))


class HardwareWatchdog(MotionNode):
    def __init__(self,cfg,inventory,layout=None,mode='mock',armed=False):
        require_domain(mode);super().__init__('hardware_watchdog',namespace='/uwa_cell')
        self.directory=tempfile.TemporaryDirectory(prefix='uwa-hardware-witness-');self.problem=HardwareProblem(self.directory.name,cfg,inventory,layout)
        self.cfg,self.mode,self.armed=cfg,mode,armed;self.signature=signature(self.problem,mode);self.peer=Peer()
        self.instance=str(uuid.uuid4());self.sequence=0;self.tripped=False;self.began=time.monotonic()
        self.ports={r:StopPort(self,p,cfg,mode) for r,p in self.problem.profiles.items()}
        self.publisher=self.create_publisher(String,'/uwa_cell/hardware_watchdog/status',1)
        self.create_subscription(String,'/uwa_cell/collision_supervisor/status',lambda msg:self.peer.receive(decode(msg),time.monotonic(),self.signature,self.armed),1)
        self.create_service(Trigger,'/uwa_cell/hardware_watchdog/reset',self.reset)
        self.wall_clock=Clock(clock_type=ClockType.STEADY_TIME);self.create_timer(.02,self.tick,clock=self.wall_clock)
    def reset(self,request,response):
        response.success=self.peer.fresh(time.monotonic(),self.cfg['heartbeat_timeout_s'])
        if response.success:self.tripped=False;self.publish()
        response.message='Watchdog reset; program/motion remains inactive' if response.success else 'Supervisor unavailable';return response
    def publish(self):
        self.sequence+=1;self.publisher.publish(String(data=json.dumps(packet(self.signature,self.armed,self.instance,self.sequence,tripped=self.tripped))))
    def tick(self):
        if time.monotonic()-self.began>self.cfg['heartbeat_timeout_s'] and not self.peer.fresh(time.monotonic(),self.cfg['heartbeat_timeout_s']):self.tripped=True
        if self.tripped and self.armed:
            for port in self.ports.values():port.tick(True,True);port.native_stop()
        self.publish()


def run(role,cfg,inventory,layout=None,mode='mock',armed=False):
    require_domain(mode);rclpy.init();node={'guard':HardwareGuard,'supervisor':HardwareSupervisor,'watchdog':HardwareWatchdog}[role](cfg,inventory,layout,mode,armed)
    executor=MultiThreadedExecutor(num_threads=4) if role=='supervisor' else rclpy.executors.SingleThreadedExecutor();executor.add_node(node)
    try:executor.spin()
    finally:executor.shutdown();node.destroy_node();rclpy.shutdown()

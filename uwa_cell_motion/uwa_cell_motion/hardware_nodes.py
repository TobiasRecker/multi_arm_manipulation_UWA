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
from .hardware_ports import StopPort,standstill_deadline_expired
from .status_markers import interlock_markers
from .pilot_interlock import PilotGuardChannel


def decode(message):
    try:
        value=json.loads(message.data)
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):return {}


def fresh_native_stops(peer, now, cfg):
    """Measured STOPPED program and stationary arm, bounded by original RTDE age."""
    if not peer.fresh(now, cfg['heartbeat_timeout_s']):
        return {}
    stamps = peer.value.get('native_stopped_at', {})
    if not isinstance(stamps, dict):
        return {}
    return {arm: stamp for arm, stamp in stamps.items()
            if arm in ROBOT_IDS and type(stamp) in (int, float)
            and 0 <= now - stamp <= cfg['state_timeout_s']}


class GuardJournal:
    """Report a newly latched arm separately from another fault during its hold."""
    def __init__(self):
        self.blocked = set()
        self.seen = set()

    @staticmethod
    def key(cause):
        return frozenset(cause['arms']), cause.get('check', cause['reason'])

    def events(self, status, now, armed):
        blocked = set(status['blocked_arms'])
        newly_blocked = blocked - self.blocked
        self.blocked = blocked
        self.seen = {key for key in self.seen if key[0] & blocked}
        # CLOCK RESET can latch in the receive callback between evaluations.
        # Other current faults supply the values measured on this tick, even
        # if a partial reset retained an older latched cause with the same key.
        causes = {self.key(cause): cause for cause in status['latched_causes']}
        active = {}
        for fault in status['faults']:
            key = self.key(fault)
            active[key] = dict(fault, source_time_s=now)
        causes.update(active)
        stops, held = [], []
        for key, cause in causes.items():
            arms, _ = key
            if not (arms & blocked):
                continue
            new_latch = bool(arms & newly_blocked)
            if key in self.seen and not (key in active and new_latch):
                continue
            (stops if new_latch else held).append(cause)
            self.seen.add(key)
        events = []
        if stops:
            events.append(('STOP LATCHED' if armed else 'MONITOR WOULD STOP', stops))
        if held:
            events.append(('HELD CONDITION' if armed else 'MONITOR HELD CONDITION', held))
        return events


class HardwareGuard(MotionNode):
    show=CollisionGuard.show
    def __init__(self,cfg,inventory,layout=None,mode='mock',armed=False,source=None):
        require_domain(mode);super().__init__('hardware_collision_guard',namespace='/uwa_cell')
        self.directory=tempfile.TemporaryDirectory(prefix='uwa-hardware-guard-')
        self.problem=HardwareProblem(self.directory.name,cfg,inventory,layout);self.layout=self.problem.layout
        self.names=self.problem.names;self.model=self.problem.spheres;self.cfg=cfg;self.core=GuardState(cfg)
        self.signature=self.problem.signature;self.hardware_signature=signature(self.problem,mode)
        self.mode,self.armed=mode,armed;self.instance=str(uuid.uuid4());self.sequence=0
        self.pilot_channel = None
        self.pilot_error = None
        if armed:
            try:self.pilot_channel = PilotGuardChannel(self.problem,mode,self.hardware_signature,self.instance)
            except (OSError,ValueError,TypeError,KeyError) as error:
                self.pilot_error = str(error)
                self.get_logger().error('Reviewed execution unavailable: '+str(error))
        self.last_tick_start=None;self.last_tick_duration_s=None;self.tick_overruns=0
        self.positions={};self.pairs=[];self.records={};self.playing={};self.supervisor_status={};self.supervisor=Peer();self.model_match={r:False for r in ROBOT_IDS}
        self.source=source or (RtdeStates(self.problem.profiles,cfg['state_timeout_s']) if mode=='hardware' else DeviceStates())
        self.last_source={};self.epochs={};self.source_faults=[];self.journal=GuardJournal()
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
        self.native_program_states = {
            arm: [record['epoch'], record['status']['runtime_state'], min(record['received'], record['source_stamp'])]
            for arm, record in records.items() if arm not in errors
        }
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
        interval=None if self.last_tick_start is None else now-self.last_tick_start
        self.last_tick_start=now
        pilot_status = dict(state='PILOT_UNAVAILABLE' if self.armed else 'MONITOR_ONLY',
                            exclusive_commands_proved=False, error=self.pilot_error)
        program_states = {}
        evidence, stationary = {}, []
        try:
            world,available=self.update(now)
            evidence = {r:self.core.stationarity_evidence(r, now) for r in ROBOT_IDS}
            stationary = [r for r in ROBOT_IDS if evidence[r]['confirmed'] and self.core.fresh(r, now, now)]
            status=self.core.evaluate(self.pairs,now,now,fresh_stationary_arms=stationary)
            if self.pilot_channel is not None:
                status['stationary_arms'] = stationary
                extra,pilot_status = self.pilot_channel.tick(now,self.records,status,self.supervisor_status,available)
                if extra:
                    self.core.external_faults.extend(extra)
                    status = self.core.evaluate(self.pairs,now,now,fresh_stationary_arms=stationary)
            program_states = self.native_program_states
        except Exception as error:
            self.core.latched.update(ROBOT_IDS);world={};available=False
            status=dict(state='STATE STALE',blocked_arms=list(ROBOT_IDS),faults=[dict(arms=list(ROBOT_IDS),
                reason=str(error) or type(error).__name__,check='GUARD EVALUATION ERROR: '+type(error).__name__)],
                latched_causes=[],reset_sequence=self.core.reset_sequence,reset_arms=[])
        if not available:status['state']='STOP ADAPTER LOST'
        self.sequence+=1
        status.update(packet(self.hardware_signature,self.armed,self.instance,self.sequence),evaluated_monotonic_s=now,pairs=self.pairs,
            pilot=pilot_status,
            timing=dict(evaluation_ms=1000*(time.monotonic()-now),interval_ms=None if interval is None else interval*1000,
                previous_callback_ms=None if self.last_tick_duration_s is None else self.last_tick_duration_s*1000,
                budget_ms=1000/self.cfg['rate_hz'],callback_overruns=self.tick_overruns),
            model_signature=self.signature,model_match=all(self.model_match.values()),guard_config_signature=self.hardware_signature,
            source_time_s=now,stop_adapter_available=available,state_ages_s={r:now-v['received'] for r,v in self.records.items()},
            stationary_arms=stationary, stationarity_evidence=evidence,
            runtime_label=self.mode.upper()+('\nSTOP-GUARD-ARMED' if self.armed else '\nMONITOR-ONLY')+
                ('\nStop-reserve:OFF (GEOMETRIC ONLY)' if self.cfg.get('stopping_reserve_policy')=='geometric_only' else '\nStop-reserve:UNMEASURED')+'\nTool:opening-envelope',
            model_uncertainty='World/table anchors provisional; hardware stop reserve unmeasured; gripper opening unobserved')
        status['native_program_states'] = {
            arm: state for arm, state in program_states.items() if self.core.fresh(arm, now, now)
        }
        # A quiet position trend may coexist with a raw speed fault. Never
        # suppress a stop on the strength of contradictory motion evidence.
        speed_faults = {arm for fault in status['faults'] for arm in fault['arms']
                        if fault['reason'] in ('SPEED LIMIT', 'REVIEWED JOINT/TCP SPEED OR STATE INVALID')}
        status['native_stopped_at'] = {arm: state[2] for arm, state in status['native_program_states'].items()
                                       if state[1] == 1 and arm in status['stationary_arms'] and arm not in speed_faults}
        self.publisher.publish(String(data=json.dumps(status,allow_nan=False)))
        try:
            for event, causes in self.journal.events(status, now, self.armed):
                self.get_logger().error(event + ': ' + json.dumps(causes))
        except Exception:
            pass  # Unexpected diagnostic fields or logger errors must not interrupt supervision.
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
        self.last_tick_duration_s=time.monotonic()-now
        if self.last_tick_duration_s>1/self.cfg['rate_hz']:self.tick_overruns+=1
    def reset(self,request,response):
        now=time.monotonic()
        try:self.update(now);response.success,response.message=self.core.reset(self.pairs,now,now)
        except Exception as error:response.success=False;response.message=str(error)
        return response
    def destroy_node(self):
        if self.pilot_channel is not None:self.pilot_channel.close()
        if hasattr(self.source,'close'):self.source.close()
        self.directory.cleanup();return super().destroy_node()


class HardwareSupervisor(MotionNode):
    def __init__(self,cfg,inventory,layout=None,mode='mock',armed=False):
        require_domain(mode);super().__init__('hardware_collision_supervisor',namespace='/uwa_cell')
        self.directory=tempfile.TemporaryDirectory(prefix='uwa-hardware-supervisor-');self.problem=HardwareProblem(self.directory.name,cfg,inventory,layout)
        self.cfg,self.mode,self.armed=cfg,mode,armed;self.signature=signature(self.problem,mode)
        self.instance=str(uuid.uuid4());self.sequence=0;self.guard=Peer();self.witness=Peer();self.lock=threading.RLock();self.group=ReentrantCallbackGroup()
        self.core=Interlock(cfg['heartbeat_timeout_s']);self.reset_lock=threading.Lock();self.stopping_since={}
        self.ports={r:StopPort(self,p,cfg,mode,self.group,observe_manager=True) for r,p in self.problem.profiles.items()}
        self.program_states = {}
        self.publisher=self.create_publisher(String,'/uwa_cell/collision_supervisor/status',1)
        self.markers=self.create_publisher(MarkerArray,'/uwa_cell/collision_supervisor/markers',1)
        self.geometry_markers=self.create_publisher(MarkerArray,'/uwa_cell/collision_guard/markers',1)
        self.reset_guard=self.create_client(Trigger,'/uwa_cell/collision_guard/reset',callback_group=self.group)
        self.reset_witness=self.create_client(Trigger,'/uwa_cell/hardware_watchdog/reset',callback_group=self.group)
        self.create_subscription(String,'/uwa_cell/collision_guard/decision',self.receive,1,callback_group=self.group)
        self.create_subscription(String,'/uwa_cell/hardware_watchdog/status',self.receive_witness,1,callback_group=self.group)
        self.create_service(Trigger,'/uwa_cell/collision_supervisor/reset',self.reset,callback_group=self.group)
        for rid in ROBOT_IDS:self.create_service(Trigger,'/uwa_cell/collision_supervisor/'+rid+'/stop',lambda request,response,r=rid:self.stop(r,response),callback_group=self.group)
        for rid in ROBOT_IDS:self.create_service(Trigger,'/uwa_cell/collision_supervisor/'+rid+'/reset',lambda request,response,r=rid:self.reset(request,response,arms={r}),callback_group=self.group)
        self.wall_clock=Clock(clock_type=ClockType.STEADY_TIME);self.create_timer(.02,self.tick,clock=self.wall_clock)
    def receive(self,msg):
        value=decode(msg)
        with self.lock:
            now=time.monotonic()
            if self.guard.receive(value,now,self.signature,self.armed):self.core.receive(value,now)
    def receive_witness(self,msg):
        value=decode(msg)
        with self.lock:self.witness.receive(value,time.monotonic(),self.signature,self.armed)
    def stop(self,rid,response):
        with self.lock:self.core.pending_reset=None;self.core.blocked.add(rid);self.core.reason='STOP REQUESTED'
        response.success=True;response.message='STOP LATCHED; measured standstill not yet confirmed';return response
    def request(self,client):
        if not client.service_is_ready():raise RuntimeError('Reset peer unavailable')
        future=client.call_async(Trigger.Request());event=threading.Event();future.add_done_callback(lambda _:event.set())
        if not event.wait(3.):raise RuntimeError('Reset peer timed out')
        if not future.result().success:raise RuntimeError(future.result().message)
        return future.result()
    def reset(self,request,response,arms=None):
        if not self.reset_lock.acquire(blocking=False):
            response.success=False;response.message='Another explicit reset is already in progress';return response
        candidates = {}
        def eligible(now):
            return {r for r,p in candidates.items() if p.verified and p.hardware_verified
                    and min(p.list_observed_from,p.hardware_observed_from,p.parameters_observed_from) >= p.hold_invalidated
                    and now-p.received <= .25 and now-p.hardware_received <= .25
                    and now-p.parameter_received <= self.cfg.get('hold_config_max_age_s', .3)}
        try:
            with self.lock:
                now=time.monotonic()
                if not self.guard.fresh(now,self.cfg['heartbeat_timeout_s']) or not self.witness.fresh(now,self.cfg['heartbeat_timeout_s']):raise RuntimeError('Supervision unavailable')
            if self.armed:
                candidates = self.ports if arms is None else {r:self.ports[r] for r in arms}
                # A latched stationary Hold may have spent hours without a list RPC.
                # Request live readback without clearing that Hold or releasing the lockout.
                deadline = time.monotonic() + 1.3
                with self.lock:
                    for port in candidates.values():
                        port.refresh_for_release = True
                while True:
                    with self.lock:
                        now = time.monotonic()
                        ready = eligible(now)
                        if ready and (arms is None or ready == arms):
                            break
                    if now >= deadline:
                        raise RuntimeError('No provisioned fresh matching manager available for requested release')
                    time.sleep(.02)
            self.request(self.reset_witness)
            end=time.monotonic()+1.
            while self.witness.value.get('tripped',True):
                if time.monotonic()>end:raise RuntimeError('Watchdog reset status unavailable')
                time.sleep(.005)
            with self.lock:
                now = time.monotonic()
                if not self.guard.fresh(now,self.cfg['heartbeat_timeout_s']) or not self.witness.fresh(now,self.cfg['heartbeat_timeout_s']):
                    raise RuntimeError('Supervision unavailable')
                ready = eligible(now) if self.armed else arms
                if self.armed and (not ready or arms is not None and ready != arms):
                    raise RuntimeError('Matching manager readback expired before release')
                if not self.core.request_reset(now,arms=ready):raise RuntimeError('Guard reset not eligible')
            answer=self.request(self.reset_guard);response.success=True;response.message=answer.message+'; supervisor release limited to '+(', '.join(sorted(ready)) if ready is not None else 'all eligible arms')+'; no trajectory/program activated'
        except Exception as error:
            with self.lock:self.core.pending_reset=None
            response.success=False;response.message=str(error)
        finally:
            with self.lock:
                for port in candidates.values():
                    port.refresh_for_release = False
            self.reset_lock.release()
        return response
    def tick(self):
        with self.lock:
            # Witness reception uses this same lock. Capture time after
            # acquiring it: a concurrent fresh packet must not appear to be
            # from the future relative to an earlier tick timestamp.
            now=time.monotonic()
            blocked=self.core.tick(now)
            if not self.guard.fresh(now,self.cfg['heartbeat_timeout_s']):self.core.blocked.update(ROBOT_IDS);self.core.reason='GUARD LOST'
            decision = self.core.last
            expired = expired_pair_leases(decision, now, self.cfg) if decision else set()
            if expired:self.core.blocked.update(expired);self.core.reason='PAIR SUPERVISION EXPIRED'
            witness_fresh = self.witness.fresh(now, self.cfg['heartbeat_timeout_s'])
            if not witness_fresh or self.witness.value.get('tripped',True):self.core.blocked.update(ROBOT_IDS);self.core.reason='WATCHDOG LOST OR TRIPPED'
            # A progressing tripped witness owns the Dashboard fallback. It can
            # take over ROS holds as well if this supervisor stops progressing.
            delegated = witness_fresh and self.witness.value.get('tripped') is True
            stopped_at = fresh_native_stops(self.guard, now, self.cfg)
            guard_fresh = self.guard.fresh(now, self.cfg['heartbeat_timeout_s'])
            stationary = (self.guard.value or {}).get('stationary_arms', [])
            native_states = self.guard.value.get('native_program_states', {}) if guard_fresh else {}
            program_states = {arm: state[:2] for arm, state in native_states.items()
                              if isinstance(state, list) and len(state) == 3 and type(state[2]) in (int, float)
                              and 0 <= now - state[2] <= self.cfg['state_timeout_s']}
            blocked = set(self.core.blocked)
            ports = {}
            all_quiet = set(stationary) == set(ROBOT_IDS) and set(program_states) == set(ROBOT_IDS)
            cell_held_quiet = all_quiet and blocked == set(ROBOT_IDS)
            quiet_partial_hold = (all_quiet and 0 < len(blocked) < len(ROBOT_IDS) and guard_fresh and witness_fresh
                and self.witness.value.get('tripped') is False and decision is self.guard.value
                and not expired and decision.get('faults') == [] and decision.get('stop_adapter_available') is True
                and decision.get('model_match') is True and program_states == self.program_states
                and [p.get('arms') for p in decision['pairs']] == [list(pair) for pair in PAIRS])
            for rid, port in self.ports.items():
                port.cell_held_quiet = cell_held_quiet
                port.quiet_partial_hold = quiet_partial_hold and rid in blocked
                previous, current = self.program_states.get(rid), program_states.get(rid)
                if previous != current:
                    program_started = (cell_held_quiet and previous and current and previous[0] == current[0]
                                       and previous[1] == 1 and current[1] == 2)
                    port.invalidate_hold_evidence(quiet_readback=bool(program_started))
                if not cell_held_quiet:
                    port.quiet_transition_until = -float('inf')
                port.stationary_hold = rid in program_states and rid in stationary
                ports[rid] = port.tick(rid in blocked, self.armed, allow_native=not delegated and rid not in stopped_at)
            self.program_states = program_states
            held = [r for r, port in ports.items() if port['held']]
            if self.armed:
                failed=[r for r,p in ports.items() if not p['manager_fresh'] or not p['hardware_mode_verified'] or not p['hold_config_verified']]
                if failed:
                    affected={r for pair in PAIRS if set(pair)&set(failed) for r in pair};self.core.blocked.update(affected);self.core.reason='ARM STOP ADAPTER UNAVAILABLE'
                    for rid in affected-blocked:
                        ports[rid] = self.ports[rid].tick(True, True, allow_native=not delegated and rid not in stopped_at)
                    blocked=set(self.core.blocked);held=[r for r,p in ports.items() if p['held']]
                for rid in ROBOT_IDS:
                    if standstill_deadline_expired(self.stopping_since,rid,now,blocked=rid in blocked,
                            guard_fresh=guard_fresh,reported_stationary=rid in stationary,
                            quiet_stamp=(self.guard.value or {}).get('evaluated_monotonic_s',-float('inf')),
                            latency=self.cfg['stop_latency_s']) and not delegated:
                        detail=(self.guard.value or {}).get('stationarity_evidence',{}).get(rid)
                        self.ports[rid].native_stop(f'Blocked arm: no fresh standstill evidence within stop latency; guard_fresh={guard_fresh}; evidence={detail}')
            self.sequence+=1;status=packet(self.signature,self.armed,self.instance,self.sequence,state=self.core.reason,blocked_arms=sorted(blocked),held_arms=held,
                native_stopped_at=stopped_at,
                native_stop_pending=[r for r,p in self.ports.items() if p.native_thread and p.native_thread.is_alive()],
                guard_config_signature=self.signature,interlock_confirmed=self.armed and blocked<=set(held),ports=ports,
                guard_age_s=None if not self.guard.value else now-self.guard.value['evaluated_monotonic_s'],
                witness_available=self.witness.fresh(now,self.cfg['heartbeat_timeout_s']),monitor_only=not self.armed,
                witness_age_s=None if self.witness.value is None else now-self.witness.received,
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
        self.guard = Peer()
        self.hold_errors = {}
        self.publisher=self.create_publisher(String,'/uwa_cell/hardware_watchdog/status',1)
        self.create_subscription(String,'/uwa_cell/collision_supervisor/status',lambda msg:self.peer.receive(decode(msg),time.monotonic(),self.signature,self.armed),1)
        self.create_subscription(String, '/uwa_cell/collision_guard/decision', self.receive_guard, 1)
        self.create_service(Trigger,'/uwa_cell/hardware_watchdog/reset',self.reset)
        self.wall_clock=Clock(clock_type=ClockType.STEADY_TIME);self.create_timer(.02,self.tick,clock=self.wall_clock)
    def receive_guard(self, msg):
        # The supervisor normally forwards original RTDE timestamps. During
        # takeover use the existing guard decision independently of that process.
        now = time.monotonic()
        if self.tripped and not self.peer.fresh(now, self.cfg['heartbeat_timeout_s']):
            self.guard.receive(decode(msg), now, self.signature, self.armed)
    def reset(self,request,response):
        response.success=self.peer.fresh(time.monotonic(),self.cfg['heartbeat_timeout_s'])
        if response.success:
            self.tripped=False
            self.publish(self.peer.value.get('native_stop_pending', ()))
        response.message='Watchdog reset; program/motion remains inactive' if response.success else 'Supervisor unavailable';return response
    def publish(self, supervisor_pending=()):
        pending=[r for r,p in self.ports.items() if p.native_thread is not None and p.native_thread.is_alive()]
        pending=sorted(set(pending).union(supervisor_pending))
        self.sequence+=1;self.publisher.publish(String(data=json.dumps(packet(self.signature,self.armed,self.instance,self.sequence,tripped=self.tripped,native_stop_pending=pending))))
    def tick(self):
        now = time.monotonic()
        fresh = self.peer.fresh(now, self.cfg['heartbeat_timeout_s'])
        if now - self.began > self.cfg['heartbeat_timeout_s'] and not fresh:
            self.tripped = True
        if self.tripped and self.armed:
            supervisor_holding = fresh and set(self.peer.value.get('blocked_arms', ())) == set(ROBOT_IDS)
            stopped_at = fresh_native_stops(self.peer if fresh else self.guard, now, self.cfg)
            for arm, port in self.ports.items():
                if arm not in stopped_at:
                    port.native_stop('Independent watchdog: supervisor heartbeat unavailable/tripped')
            if not supervisor_holding:
                for arm, port in self.ports.items():
                    # A failed controller RPC must not interrupt the ongoing
                    # Dashboard fallback for this or any other arm.
                    try:
                        port.tick(True, True, allow_native=False)
                        self.hold_errors.pop(arm, None)
                    except RuntimeError as error:
                        detail = str(error)
                        if self.hold_errors.get(arm) != detail:
                            self.get_logger().error(f'{arm}: watchdog resource hold unavailable: {detail}')
                        self.hold_errors[arm] = detail
        self.publish(self.peer.value.get('native_stop_pending', ()) if fresh else ())


def run(role,cfg,inventory,layout=None,mode='mock',armed=False):
    require_domain(mode);rclpy.init();node={'guard':HardwareGuard,'supervisor':HardwareSupervisor,'watchdog':HardwareWatchdog}[role](cfg,inventory,layout,mode,armed)
    executor=MultiThreadedExecutor(num_threads=4) if role=='supervisor' else rclpy.executors.SingleThreadedExecutor();executor.add_node(node)
    try:executor.spin()
    finally:executor.shutdown();node.destroy_node();rclpy.shutdown()

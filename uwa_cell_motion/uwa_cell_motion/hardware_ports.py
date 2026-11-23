"""Per-manager resource interlocks and independent native-stop fallback."""
import threading
import time
import math
from pathlib import Path
import tempfile
import subprocess
import yaml
import rclpy
from controller_manager_msgs.msg import ControllerManagerActivity
from controller_manager_msgs.srv import ListControllers,SwitchController,ListHardwareComponents
from rcl_interfaces.msg import ParameterEvent, ParameterType
from rcl_interfaces.srv import GetParameters
from rclpy.event_handler import SubscriptionEventCallbacks
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_parameter_events
from action_msgs.srv import CancelGoal
from match_ur_hardware.profiles import MOTION
from .hardware_state import dashboard_stop

HOLD='collision_hold_controller'


def standstill_deadline_expired(since,rid,now,*,blocked,guard_fresh,reported_stationary,quiet_stamp,latency):
    """Bound each absence of fresh quiet evidence, including after long holds.

    A stale packet never renews this deadline. An active hold/manager fault
    still uses its independent immediate native-stop fallback below.
    """
    if not blocked:
        since.pop(rid,None);return False
    if guard_fresh and reported_stationary and math.isfinite(quiet_stamp) and quiet_stamp<=now:
        # Reusing one still-fresh packet must not keep extending the deadline.
        since[rid]=max(since.get(rid,-float('inf')),quiet_stamp)
        return now-since[rid]>latency
    since.setdefault(rid,now)
    return now-since[rid]>latency


def matching_hardware(components,joints,mode):
    plugin='mock_components/GenericSystem' if mode=='mock' else 'ur_robot_driver/URPositionHardwareInterface'
    required={j+'/position' for j in joints}
    return any(c.plugin_name==plugin and required<={i.name for i in c.command_interfaces} for c in components)


def unsafe_controllers(controllers,joints):
    return [c.name for c in controllers if c.state=='active' and c.name!=HOLD and
            (c.name in MOTION or any(i.split('/')[0] in joints for i in c.claimed_interfaces))]


def hold_owned(controllers,joints):
    return any(c.name==HOLD and c.state=='active' and c.type=='uwa_cell_motion/CollisionHold' and
               {j+'/position' for j in joints}<=set(c.claimed_interfaces) for c in controllers)


def provision(node,profiles,cfg,mode):
    """Explicitly load inactive six-joint plugins, without arm activation."""
    with tempfile.TemporaryDirectory(prefix='uwa-hardware-holds-') as directory:
        for rid,p in profiles.items():
            client=node.create_client(ListHardwareComponents,p['namespace']+'/controller_manager/list_hardware_components')
            try:
                if not client.wait_for_service(timeout_sec=5.):raise RuntimeError(rid+': hardware manager missing')
                future=client.call_async(ListHardwareComponents.Request());rclpy.spin_until_future_complete(node,future,timeout_sec=5.)
                if not future.done() or not matching_hardware(future.result().component,p['joint_names'],mode):raise RuntimeError(rid+': hardware/mock plugin mismatch')
            finally:node.destroy_client(client)
            file=Path(directory)/(rid+'.yaml');file.write_text(yaml.safe_dump({p['namespace']+'/'+HOLD:{'ros__parameters':dict(
                type='uwa_cell_motion/CollisionHold',joints=p['joint_names'],deceleration=cfg['braking_acceleration_rad_s2'],use_sim_time=False)}}))
            result=subprocess.run(['ros2','run','controller_manager','spawner',HOLD,'--inactive','-c',p['namespace']+'/controller_manager',
                '--param-file',str(file),'--controller-manager-timeout','10','--service-call-timeout','5',
                '--ros-args','-r','__ns:='+p['namespace']],capture_output=True,text=True,timeout=30.)
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)


class StopPort:
    def __init__(self,node,profile,cfg,mode,group=None,*,observe_manager=False):
        self.node,self.profile,self.cfg,self.mode=node,profile,cfg,mode;self.joints=profile['joint_names'];ns=profile['namespace']
        self.list=node.create_client(ListControllers,ns+'/controller_manager/list_controllers',callback_group=group)
        self.switch=node.create_client(SwitchController,ns+'/controller_manager/switch_controller',callback_group=group)
        self.parameters=node.create_client(GetParameters,ns+'/'+HOLD+'/get_parameters',callback_group=group)
        self.hardware=node.create_client(ListHardwareComponents,ns+'/controller_manager/list_hardware_components',callback_group=group)
        self.pending_hardware=None;self.hardware_verified=False;self.hardware_received=-float('inf');self.hardware_sent=-float('inf')
        self.parameter_sent=-float('inf');self.parameter_received=-float('inf')
        self.pending=None;self.switching=None;self.checking=None;self.verified=False
        self.controllers=[];self.received=-float('inf');self.sent=-float('inf');self.switch_started=-float('inf')
        self.error=None;self.native_error=None;self.native_ack=False;self.native_thread=None;self.native_sent=-float('inf')
        self.unheld_since=None;self.cancelled_owners=set();self.switch_finished=-float('inf')
        self.native_stop_events=[]
        self.cancels={};self.was_blocked=False
        self.stationary_hold = False
        self.cell_held_quiet = False
        self.reusing_hold = False
        self.refresh_for_release = False
        self.list_observed_from = self.hardware_observed_from = self.parameters_observed_from = -math.inf
        self.hold_invalidated = time.monotonic()
        self.quiet_transition_until = -math.inf
        self.activity_holding = False
        self.activity_state = None
        self.activity_publishers = 0
        self.activity = None
        if observe_manager:
            # These callbacks and the supervisor timer use the same mutually exclusive
            # group. An activity message triggers readback of type and claimed joints.
            qos = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
            events = SubscriptionEventCallbacks(matched=self.manager_matched, message_lost=self.manager_sample_lost,
                                                use_default_callbacks=False)
            self.activity = node.create_subscription(ControllerManagerActivity, ns+'/controller_manager/activity',
                                                     self.manager_activity, qos, event_callbacks=events)
            node.create_subscription(ParameterEvent, '/parameter_events', self.hold_parameters_changed,
                                     qos_profile_parameter_events)
        # RMW entity allocation may block. Provision the known cancellation
        # endpoints before the armed timer starts, never inside its stop path.
        for name in (*MOTION,HOLD):
            path=ns+'/'+name+'/follow_joint_trajectory/_action/cancel_goal'
            self.cancels[path]=node.create_client(CancelGoal,path,callback_group=group)
        path=ns+'/ur_robot_state_helper/set_mode/_action/cancel_goal'
        self.cancels[path]=node.create_client(CancelGoal,path,callback_group=group)
    def invalidate_hold_evidence(self, *, quiet_readback=False):
        self.hold_invalidated = time.monotonic()
        if quiet_readback and self.reusing_hold and self.cell_held_quiet:
            # Bound readback after a matching notification or expected Play. Repeated
            # events cannot extend the window without new replies from all three services.
            self.quiet_transition_until = self.hold_invalidated + .25
        elif not quiet_readback:
            self.quiet_transition_until = -math.inf
        self.reusing_hold = False

    def manager_activity(self, msg):
        state = tuple(tuple(sorted((item.name, item.state.label) for item in group))
                      for group in (msg.controllers, msg.hardware_components))
        self.invalidate_hold_evidence(quiet_readback=state == self.activity_state)
        self.activity_state = state
        self.activity_holding = any(c.name == HOLD and c.state.label == 'active' for c in msg.controllers)

    def manager_matched(self, event):
        self.invalidate_hold_evidence()
        self.activity_state = None
        self.activity_publishers = event.current_count
        if event.current_count != 1 or event.current_count_change < 0:
            self.activity_holding = False

    def manager_sample_lost(self, _event):
        self.invalidate_hold_evidence()
        self.activity_state = None
        self.activity_holding = False

    def hold_parameters_changed(self, msg):
        if msg.node != self.profile['namespace']+'/'+HOLD:
            return
        names = ('joints', 'deceleration')
        if any(p.name in names for p in (*msg.new_parameters, *msg.deleted_parameters)):
            self.invalidate_hold_evidence()
            return
        changed = [p for p in msg.changed_parameters if p.name in names]
        if changed:
            matching = all((p.value.type == ParameterType.PARAMETER_STRING_ARRAY
                            and list(p.value.string_array_value) == self.joints) if p.name == 'joints'
                           else (p.value.type == ParameterType.PARAMETER_DOUBLE
                                 and abs(p.value.double_value-self.cfg['braking_acceleration_rad_s2']) < 1e-10)
                           for p in changed)
            self.invalidate_hold_evidence(quiet_readback=matching)

    def can_reuse_hold(self, blocked, now):
        return (blocked and self.was_blocked and self.stationary_hold and self.activity_holding
                and self.verified and self.hardware_verified and self.switching is None and not self.error
                and self.list_observed_from > self.switch_finished
                and min(self.list_observed_from, self.hardware_observed_from,
                        self.parameters_observed_from) >= self.hold_invalidated
                and (self.reusing_hold or (now-self.received < 1.0 and now-self.hardware_received < 1.3
                     and now-self.parameter_received <= self.cfg.get('hold_config_max_age_s', .3)))
                and self.activity_publishers == 1 and hold_owned(self.controllers, self.joints)
                and not unsafe_controllers(self.controllers, self.joints))

    def native_stop(self,reason='Explicit native-stop fallback'):
        if self.mode=='mock':self.native_ack=True;return
        if self.native_thread and self.native_thread.is_alive():return
        if time.monotonic()-self.native_sent<.25:return
        self.native_sent=time.monotonic()
        self.native_ack=False
        event=dict(requested_monotonic_s=self.native_sent,reason=str(reason),acknowledged=False,error=None)
        self.native_stop_events.append(event);self.native_stop_events=self.native_stop_events[-20:]
        try:self.node.get_logger().error('NATIVE STOP REQUESTED '+self.profile.get('id','unknown')+': '+str(reason))
        except Exception:pass  # Diagnostic logging must never prevent stopping.
        def stop():
            try:
                dashboard_stop(self.profile);self.native_ack=True;self.native_error=None
                event['acknowledged']=True
            except Exception as error:
                self.native_error=str(error);event['error']=str(error)
        self.native_thread=threading.Thread(target=stop,daemon=True);self.native_thread.start()
    def cancel(self):
        names=[c.name for c in self.controllers if c.name in MOTION or any(i.split('/')[0] in self.joints for i in c.claimed_interfaces)]
        paths=[self.profile['namespace']+'/'+n+'/follow_joint_trajectory/_action/cancel_goal' for n in names]
        paths.append(self.profile['namespace']+'/ur_robot_state_helper/set_mode/_action/cancel_goal')
        for path in paths:
            client=self.cancels.setdefault(path,self.node.create_client(CancelGoal,path)) if path not in self.cancels else self.cancels[path]
            if client.service_is_ready():client.call_async(CancelGoal.Request())
    def tick(self,blocked,enabled,*,allow_native=True):
        now=time.monotonic()
        if self.pending_hardware and now-self.hardware_sent>.3:
            self.hardware.remove_pending_request(self.pending_hardware)
            self.pending_hardware=None
        if self.pending_hardware and self.pending_hardware.done():
            try:
                self.hardware_verified=matching_hardware(self.pending_hardware.result().component,self.joints,self.mode)
                self.hardware_received=now
                self.hardware_observed_from=self.hardware_sent
            except Exception:self.hardware_verified=False
            self.pending_hardware=None
        if self.pending and now-self.sent>1.3:
            self.list.remove_pending_request(self.pending)
            self.pending=None;self.error='Controller list response stale'
        if self.pending and self.pending.done():
            try:
                self.controllers=self.pending.result().controller
                self.received=now
                self.list_observed_from=self.sent
            except Exception as error:self.error=str(error)
            self.pending=None
        if self.checking and now-self.parameter_sent>.3:
            self.parameters.remove_pending_request(self.checking)
            self.checking=None
        if self.checking and self.checking.done():
            try:
                values=self.checking.result().values
                self.parameter_received=now
                self.parameters_observed_from=self.parameter_sent
                self.verified=(list(values[0].string_array_value)==self.joints and abs(values[1].double_value-self.cfg['braking_acceleration_rad_s2'])<1e-10)
                if not self.verified:self.error='Hold configuration differs'
            except Exception as error:self.verified=False;self.error=str(error)
            self.checking=None
        self.reusing_hold=self.can_reuse_hold(blocked, now)
        if not self.reusing_hold or self.refresh_for_release:
            if self.pending_hardware is None and now-self.hardware_sent>.1 and self.hardware.service_is_ready():
                self.hardware_sent=now;self.pending_hardware=self.hardware.call_async(ListHardwareComponents.Request())
            if self.pending is None and now-self.sent>=.05 and self.list.service_is_ready():
                self.pending=self.list.call_async(ListControllers.Request());self.sent=now
            if self.checking is None and now-self.parameter_sent>.1 and self.parameters.service_is_ready():
                self.parameter_sent=now
                request=GetParameters.Request();request.names=['joints','deceleration'];self.checking=self.parameters.call_async(request)
        # An unchanged event in an already latched, quiet cell wakes the readers.
        # Retain the previous binding briefly while they answer. A mismatch, lost
        # publisher, motion or explicit release immediately ends this allowance.
        reading_back = (now <= self.quiet_transition_until and blocked and self.cell_held_quiet
                        and self.stationary_hold and self.activity_holding and self.activity_publishers == 1
                        and self.hardware_verified and self.verified and not self.error and self.switching is None
                        and hold_owned(self.controllers,self.joints) and not unsafe_controllers(self.controllers,self.joints))
        if not (self.reusing_hold or reading_back) and now-self.parameter_received>self.cfg.get('hold_config_max_age_s', .3):
            self.verified=False
        hardware_ok=self.hardware_verified and (self.reusing_hold or reading_back or now-self.hardware_received<1.3)
        if self.switching and self.switching.done():
            try:
                if not self.switching.result().ok:self.error='Hold switch rejected'
            except Exception as error:self.error=str(error)
            self.switching=None;self.switch_finished=now
        if self.switching and now-self.switch_started>.3:
            self.switch.remove_pending_request(self.switching)
            self.switching=None;self.switch_finished=now;self.error='Hold switch response stale'
        fresh=self.reusing_hold or reading_back or now-self.received<1.0
        switch_observed = self.switching is None and self.list_observed_from > self.switch_finished
        held=fresh and hardware_ok and self.verified and switch_observed and hold_owned(self.controllers,self.joints)
        bad=unsafe_controllers(self.controllers,self.joints)
        if blocked and (not held or bad):
            if self.unheld_since is None:self.unheld_since=now
        else:
            self.unheld_since=None
        if enabled and hardware_ok:
            if blocked and (not self.was_blocked or set(bad)-self.cancelled_owners):
                self.cancel()
            self.cancelled_owners=set(bad) if blocked else set()
            # A completed RPC can precede the controller state transition.
            # Observe the manager again before sending another switch.
            if fresh and switch_observed and self.switch.service_is_ready():
                activate=[HOLD] if blocked and not held and self.verified else []
                deactivate=bad if blocked else ([HOLD] if hold_owned(self.controllers,self.joints) else [])
                if activate or deactivate:
                    request=SwitchController.Request();request.activate_controllers=activate;request.deactivate_controllers=deactivate
                    request.strictness=SwitchController.Request.BEST_EFFORT;request.activate_asap=True;request.timeout.nanosec=200_000_000
                    self.switch_started=now;self.switching=self.switch.call_async(request)
            if allow_native and blocked and (not fresh or not self.verified or self.error or
                            (self.unheld_since is not None and (not self.switch.service_is_ready()
                             or now-self.unheld_since>=self.cfg['stop_latency_s']))):
                self.native_stop(f'Blocked interlock: manager_fresh={fresh}, hold_config_verified={self.verified}, '
                                 f'held={held}, controller_error={self.error}, list_age_s={now-self.received:.6f}, '
                                 f'parameter_age_s={now-self.parameter_received:.6f}')
        if allow_native and enabled and blocked and not hardware_ok:
            self.native_stop(f'Blocked interlock: native hardware verification unavailable, age_s={now-self.hardware_received:.6f}')
        self.was_blocked=blocked
        if held and not bad:self.error=None
        return dict(held=bool(held and not bad),manager_fresh=fresh,hardware_mode_verified=hardware_ok,hold_config_verified=self.verified,
                    inventory_reused_during_stationary_hold=self.reusing_hold,
                    controller_error=self.error,native_stop_ack=self.native_ack,native_stop_error=self.native_error,
                    native_stop_events=[dict(event) for event in self.native_stop_events[-5:]])

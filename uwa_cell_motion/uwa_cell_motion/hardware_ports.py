"""Per-manager resource interlocks and independent native-stop fallback."""
import threading
import time
from pathlib import Path
import tempfile
import subprocess
import yaml
import rclpy
from controller_manager_msgs.srv import ListControllers,SwitchController
from rcl_interfaces.srv import GetParameters
from action_msgs.srv import CancelGoal
from match_ur_hardware.profiles import MOTION
from .hardware_state import dashboard_stop

HOLD='collision_hold_controller'


def unsafe_controllers(controllers,joints):
    return [c.name for c in controllers if c.state=='active' and c.name!=HOLD and
            (c.name in MOTION or any(i.split('/')[0] in joints for i in c.claimed_interfaces))]


def hold_owned(controllers,joints):
    return any(c.name==HOLD and c.state=='active' and c.type=='uwa_cell_motion/CollisionHold' and
               {j+'/position' for j in joints}<=set(c.claimed_interfaces) for c in controllers)


def provision(node,profiles,cfg):
    """Explicitly load inactive six-joint plugins, without arm activation."""
    with tempfile.TemporaryDirectory(prefix='uwa-hardware-holds-') as directory:
        for rid,p in profiles.items():
            file=Path(directory)/(rid+'.yaml');file.write_text(yaml.safe_dump({p['namespace']+'/'+HOLD:{'ros__parameters':dict(
                type='uwa_cell_motion/CollisionHold',joints=p['joint_names'],deceleration=cfg['braking_acceleration_rad_s2'],use_sim_time=False)}}))
            result=subprocess.run(['ros2','run','controller_manager','spawner',HOLD,'--inactive','-c',p['namespace']+'/controller_manager',
                '--param-file',str(file),'--controller-manager-timeout','10','--service-call-timeout','5'],capture_output=True,text=True,timeout=30.)
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)


class StopPort:
    def __init__(self,node,profile,cfg,mode,group=None):
        self.node,self.profile,self.cfg,self.mode=node,profile,cfg,mode;self.joints=profile['joint_names'];ns=profile['namespace']
        self.list=node.create_client(ListControllers,ns+'/controller_manager/list_controllers',callback_group=group)
        self.switch=node.create_client(SwitchController,ns+'/controller_manager/switch_controller',callback_group=group)
        self.parameters=node.create_client(GetParameters,ns+'/'+HOLD+'/get_parameters',callback_group=group)
        self.pending=None;self.switching=None;self.checking=None;self.verified=False
        self.controllers=[];self.received=-float('inf');self.sent=-float('inf');self.switch_started=-float('inf')
        self.error=None;self.native_error=None;self.native_ack=False;self.native_thread=None;self.native_sent=-float('inf')
        self.cancels={};self.was_blocked=False
    def native_stop(self):
        if self.mode=='mock':self.native_ack=True;return
        if self.native_thread and self.native_thread.is_alive():return
        if time.monotonic()-self.native_sent<.25:return
        self.native_sent=time.monotonic()
        def stop():
            try:dashboard_stop(self.profile);self.native_ack=True;self.native_error=None
            except Exception as error:self.native_error=str(error)
        self.native_thread=threading.Thread(target=stop,daemon=True);self.native_thread.start()
    def cancel(self):
        names=[c.name for c in self.controllers if c.name in MOTION or any(i.split('/')[0] in self.joints for i in c.claimed_interfaces)]
        paths=[self.profile['namespace']+'/'+n+'/follow_joint_trajectory/_action/cancel_goal' for n in names]
        paths.append(self.profile['namespace']+'/ur_robot_state_helper/set_mode/_action/cancel_goal')
        for path in paths:
            client=self.cancels.setdefault(path,self.node.create_client(CancelGoal,path)) if path not in self.cancels else self.cancels[path]
            if client.service_is_ready():client.call_async(CancelGoal.Request())
    def tick(self,blocked,enabled):
        now=time.monotonic()
        if self.pending and self.pending.done():
            try:self.controllers=self.pending.result().controller;self.received=now
            except Exception as error:self.error=str(error)
            self.pending=None
        if self.pending and now-self.sent>.3:self.pending=None;self.error='Controller list response stale'
        if self.pending is None and now-self.sent>=.05 and self.list.service_is_ready():
            self.pending=self.list.call_async(ListControllers.Request());self.sent=now
        if self.checking and self.checking.done():
            try:
                values=self.checking.result().values
                self.verified=(list(values[0].string_array_value)==self.joints and abs(values[1].double_value-self.cfg['braking_acceleration_rad_s2'])<1e-10)
                if not self.verified:self.error='Hold configuration differs'
            except Exception as error:self.error=str(error)
            self.checking=None
        if not self.verified and self.checking is None and self.parameters.service_is_ready():
            request=GetParameters.Request();request.names=['joints','deceleration'];self.checking=self.parameters.call_async(request)
        if self.switching and self.switching.done():
            try:
                if not self.switching.result().ok:self.error='Hold switch rejected'
            except Exception as error:self.error=str(error)
            self.switching=None
        if self.switching and now-self.switch_started>.3:self.switching=None;self.error='Hold switch response stale'
        fresh=now-self.received<.25;held=fresh and self.verified and hold_owned(self.controllers,self.joints)
        bad=unsafe_controllers(self.controllers,self.joints)
        if enabled:
            if blocked and (not self.was_blocked or bad):self.cancel()
            if fresh and self.switching is None and self.switch.service_is_ready():
                activate=[HOLD] if blocked and not held and self.verified else []
                deactivate=bad if blocked else ([HOLD] if hold_owned(self.controllers,self.joints) else [])
                if activate or deactivate:
                    request=SwitchController.Request();request.activate_controllers=activate;request.deactivate_controllers=deactivate
                    request.strictness=SwitchController.Request.BEST_EFFORT;request.activate_asap=True;request.timeout.nanosec=200_000_000
                    self.switch_started=now;self.switching=self.switch.call_async(request)
            if blocked and (not fresh or not self.verified or self.error or
                            (not held and now-self.switch_started>self.cfg['stop_latency_s'])):self.native_stop()
        self.was_blocked=blocked
        if held and not bad:self.error=None
        return dict(held=bool(held and not bad),manager_fresh=fresh,hold_config_verified=self.verified,
                    controller_error=self.error,native_stop_ack=self.native_ack,native_stop_error=self.native_error)

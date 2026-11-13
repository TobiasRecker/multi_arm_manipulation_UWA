"""Independent wall-clock watchdog and per-arm controller resource interlocks."""
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from controller_manager_msgs.srv import ListControllers, SwitchController
from action_msgs.srv import CancelGoal
from std_msgs.msg import String
from std_srvs.srv import Trigger
import yaml

from .common import ROBOT_IDS, all_names, load_layout, default_layout_path, simulation_only
from .interlock import Interlock


def hold_name(rid):return rid+'_collision_hold_controller'


class Supervisor(Node):
    def __init__(self,cfg,layout_path=None,prepare=True):
        super().__init__('collision_supervisor',namespace='/uwa_cell')
        self.cfg=cfg; self.layout=load_layout(layout_path or default_layout_path()); self.names=all_names(self.layout)
        self.lock=threading.RLock(); self.core=Interlock(cfg['heartbeat_timeout_s'])
        self.group=ReentrantCallbackGroup(); self.pending_list=None; self.pending_switch=None
        self.controllers=[]; self.last_error=None; self.last_release=set(); self.last_cancel=set()
        self.list_client=self.create_client(ListControllers,'/uwa_cell/controller_manager/list_controllers',callback_group=self.group)
        self.switch_client=self.create_client(SwitchController,'/uwa_cell/controller_manager/switch_controller',callback_group=self.group)
        self.reset_client=self.create_client(Trigger,'/uwa_cell/collision_guard/reset',callback_group=self.group)
        self.cancel_clients={name:self.create_client(CancelGoal,'/uwa_cell/'+name+'/follow_joint_trajectory/_action/cancel_goal')
            for rid in ROBOT_IDS for name in (rid+'_trajectory_controller',rid+'_gripper_controller')}
        self.publisher=self.create_publisher(String,'~/status',10)
        self.create_subscription(String,'/uwa_cell/collision_guard/decision',self.receive,10,callback_group=self.group)
        self.create_service(Trigger,'~/reset',self.reset,callback_group=self.group)
        if prepare:self.prepare()
        self.create_timer(.05,self.tick)  # independent system clock; simulation pauses cannot hide a lost guard
        self.get_logger().info('RUNNING: resource interlocks armed; explicit reset required; simulation only')

    def prepare(self):
        with tempfile.TemporaryDirectory(prefix='uwa-holds-') as directory:
            parameters={}
            for rid,names in self.names.items():
                parameters['/uwa_cell/'+hold_name(rid)]={'ros__parameters':
                    {'joints':names,'deceleration':self.cfg['braking_acceleration_rad_s2'],'use_sim_time':True}}
            path=Path(directory)/'holds.yaml';path.write_text(yaml.safe_dump(parameters))
            for rid in ROBOT_IDS:
                result=subprocess.run(['ros2','run','controller_manager','spawner',hold_name(rid),
                    '-c','/uwa_cell/controller_manager','-t','uwa_cell_motion/CollisionHold',
                    '--inactive','--param-file',str(path)],capture_output=True,text=True,timeout=45)
                if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)

    def receive(self,msg):
        try:
            value=json.loads(msg.data)
            with self.lock:self.core.receive(value,time.monotonic())
        except (ValueError,KeyError,TypeError):pass

    def reset(self,request,response):
        with self.lock:
            if not self.core.request_reset(time.monotonic()):
                response.success=False;response.message='GUARD LOST: reset refused';return response
        if not self.reset_client.service_is_ready():
            response.success=False;response.message='Guard reset service unavailable';return response
        future=self.reset_client.call_async(Trigger.Request());done=threading.Event()
        future.add_done_callback(lambda _:done.set())
        if not done.wait(3.):
            with self.lock:self.core.pending_reset=None
            response.success=False;response.message='Guard reset timed out';return response
        answer=future.result();response.success=answer.success;response.message=answer.message
        if not answer.success:
            with self.lock:self.core.pending_reset=None
        return response

    def tick(self):
        with self.lock:
            blocked=self.core.tick(time.monotonic())
            if self.pending_switch is not None and self.pending_switch.done():
                try:
                    if not self.pending_switch.result().ok:self.last_error='Controller interlock switch rejected'
                except Exception as error:self.last_error=str(error)
                self.pending_switch=None
            if self.pending_list is not None and self.pending_list.done():
                try:self.controllers=self.pending_list.result().controller
                except Exception as error:self.last_error=str(error)
                self.pending_list=None
            if self.pending_list is None and self.list_client.service_is_ready():
                self.pending_list=self.list_client.call_async(ListControllers.Request())
            active={c.name for c in self.controllers if c.state=='active'}
            activate=[hold_name(r) for r in blocked if hold_name(r) not in active]
            deactivate=[]
            for c in self.controllers:
                if c.state!='active':continue
                if c.name in [hold_name(r) for r in ROBOT_IDS]:
                    if c.name not in [hold_name(r) for r in blocked]:deactivate.append(c.name)
                elif any(interface.split('/')[0] in self.names[r] for r in blocked for interface in c.claimed_interfaces):
                    deactivate.append(c.name)
            for rid in blocked-self.last_cancel:
                for suffix in ('_trajectory_controller','_gripper_controller'):
                    client=self.cancel_clients[rid+suffix]
                    if client.service_is_ready():client.call_async(CancelGoal.Request())
            self.last_cancel=blocked
            if (activate or deactivate) and self.pending_switch is None and self.switch_client.service_is_ready():
                request=SwitchController.Request();request.activate_controllers=activate;request.deactivate_controllers=deactivate
                request.strictness=SwitchController.Request.BEST_EFFORT;request.activate_asap=True
                request.timeout.sec=1
                self.pending_switch=self.switch_client.call_async(request)
            held={r for r in ROBOT_IDS if hold_name(r) in active}
            status=dict(state=self.core.reason,blocked_arms=sorted(blocked),held_arms=sorted(held),
                        interlock_confirmed=blocked<=held,controller_error=self.last_error,
                        guard_age_s=None if self.core.last is None else time.monotonic()-self.core.received)
            self.publisher.publish(String(data=json.dumps(status)))


def run(cfg,layout=None):
    simulation_only();rclpy.init();node=Supervisor(cfg,layout);executor=MultiThreadedExecutor(num_threads=4);executor.add_node(node)
    try:executor.spin()
    finally:executor.shutdown();node.destroy_node();rclpy.shutdown()

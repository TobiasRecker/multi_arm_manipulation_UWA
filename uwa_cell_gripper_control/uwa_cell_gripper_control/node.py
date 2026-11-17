"""Persistent four-arm action/service adapter; startup never moves fingers."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import threading

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
import yaml

from uwa_cell_gripper_interfaces.action import GripperCommand, RobotiqCommand
from uwa_cell_tasks.robotiq_gripper import Robotiq
from .api import ARMS, capabilities, endpoint, normalize


class GripperNode(Node):
    def __init__(self, arm, mode, device):
        super().__init__('gripper',namespace=endpoint(arm,mode).rsplit('/',1)[0])
        self.device=device;self.arm=arm;self.mode=mode;self.busy=False
        self.gate=threading.Lock();self.group=ReentrantCallbackGroup()
        self.publisher=self.create_publisher(String,'~/status',1)
        self.actions=[self.make_action(GripperCommand,'~/operate',True),
                      self.make_action(RobotiqCommand,'~/command',False)]
        self.create_service(Trigger,'~/read',self.read,callback_group=self.group)
        self.create_service(Trigger,'~/capabilities',self.describe,callback_group=self.group)
        self.create_timer(1.,self.poll,callback_group=self.group)
        self.get_logger().warning(('COMMANDS ENABLED' if device.enabled else 'MONITOR ONLY')+
            '; no automatic activation or opening; force raw values are not N')

    def info(self):
        return capabilities(self.arm,self.mode,self.device.enabled,self.device.max_force_raw,self.device.max_speed_raw)

    def publish(self, state):
        with self.gate:busy=self.busy
        value=dict(state,**self.info(),busy=busy)
        self.publisher.publish(String(data=json.dumps(value,allow_nan=False)))
        return value

    def describe(self, request, response):
        response.success=True;response.message=json.dumps(self.info());return response

    def read(self, request, response):
        try:
            response.message=json.dumps(self.publish(dict(observed=True,**self.device.status())))
            response.success=True
        except (OSError,RuntimeError,ValueError) as error:
            response.success=False;response.message=str(error)
        return response

    def poll(self):
        with self.gate:
            if self.busy:return
        try:self.publish(dict(observed=True,**self.device.status()))
        except (OSError,RuntimeError,ValueError) as error:self.publish(dict(observed=False,error=str(error)))

    def make_action(self, kind, name, convenience):
        def values(request):
            if convenience:return normalize(request)
            return (request.operation,request.position_raw,request.speed_raw,request.force_raw,request.timeout_s)

        def goal(request):
            try:self.device.validate(*values(request))
            except (ValueError,TypeError) as error:
                self.get_logger().warning(str(error));return GoalResponse.REJECT
            with self.gate:
                if self.busy:return GoalResponse.REJECT
                self.busy=True
            return GoalResponse.ACCEPT

        def execute(handle):
            result=kind.Result()
            try:
                def feedback(state):
                    item=kind.Feedback();item.status_json=json.dumps(self.publish(dict(observed=True,**state)))
                    handle.publish_feedback(item)
                state=self.device.command(*values(handle.request),feedback=feedback)
                result.success=True
                result.message='Register outcome confirmed; raw setting is not measured jaw force'
                result.status_json=json.dumps(self.publish(dict(observed=True,**state)))
                if convenience:
                    result.contact_detected=state['registers']['OBJ'] in (1,2)
                    result.position_raw=state['registers']['POS']
                handle.succeed()
            except (OSError,RuntimeError,ValueError) as error:
                result.success=False;result.message=str(error);handle.abort()
            finally:
                with self.gate:self.busy=False
            return result

        return ActionServer(self,kind,name,execute_callback=execute,goal_callback=goal,
            # Cancellation must never imply opening, resetting or dropping a
            # held object. No qualified finger-stop protocol is available yet.
            cancel_callback=lambda _:CancelResponse.REJECT,callback_group=self.group)


def inventory_path():
    for parent in Path(__file__).resolve().parents:
        candidate=parent/'config/hardware_inventory.yaml'
        if candidate.is_file():return candidate
    raise ValueError('Pass --inventory: central inventory not found')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',choices=ARMS,required=True)
    p.add_argument('--mode',choices=['hardware','mock'],default='mock')
    p.add_argument('--inventory',type=Path)
    p.add_argument('--actuate',action='store_true')
    p.add_argument('--max-force-raw',type=int,default=0)
    p.add_argument('--max-speed-raw',type=int,default=32)
    p.add_argument('--mock-port',type=int,default=63352)
    args,ros=p.parse_known_args(argv)
    if ros and ros[0]!='--ros-args':p.error('Unrecognized arguments: '+' '.join(ros))
    domain='66' if args.mode=='hardware' else '67'
    if os.environ.get('ROS_DOMAIN_ID')!=domain or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST':
        p.error('Expected domain'+domain+' and LOCALHOST')
    if not 0<=args.max_force_raw<=255 or not 0<=args.max_speed_raw<=255 or not 1<=args.mock_port<=65535:
        p.error('Invalid raw caps or mock port')
    if args.mode=='hardware':
        inventory=args.inventory or inventory_path()
        host=yaml.safe_load(inventory.read_text())['robots'][args.arm]['ip'];port=63352
    else:host,port='127.0.0.1',args.mock_port
    # Same lease as the legacy adapter: both interfaces share one writer, and
    # two separate processes cannot own the same arm/domain simultaneously.
    lease=Path('/tmp')/f'uwa-gripper-{os.getuid()}-{domain}-{args.arm}.lock'
    lock=lease.open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:p.error('Another gripper adapter owns this arm')
    device=Robotiq(host,port=port,enabled=args.actuate,
                   max_force_raw=args.max_force_raw,max_speed_raw=args.max_speed_raw)
    from rclpy.signals import SignalHandlerOptions
    rclpy.init(args=ros,signal_handler_options=SignalHandlerOptions.NO)
    def interrupted(signum, frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    node=GripperNode(args.arm,args.mode,device)
    executor=MultiThreadedExecutor(num_threads=4);executor.add_node(node)
    try:executor.spin()
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        # Keep the final gripping target on timeout, process exit or arm STOP.
        # Allow any bounded command to complete without automatic release.
        executor.shutdown(timeout_sec=35.)
        for action in node.actions:action.destroy()
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        lock.close()

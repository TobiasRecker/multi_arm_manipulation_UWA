"""ROS action adapter. Monitor-only default; no automatic release on node exit."""
import argparse
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import signal
import threading

import rclpy
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import String
from std_srvs.srv import Trigger
import yaml
from uwa_cell_gripper_interfaces.action import RobotiqCommand
from .core import ARMS
from .robotiq_gripper import Robotiq


def main(argv=None):
    repo = Path(__file__).resolve().parents[2]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=ARMS, required=True)
    p.add_argument('--mode', choices=['hardware','mock'], default='mock')
    p.add_argument('--inventory', type=Path, default=repo/'config/hardware_inventory.yaml')
    p.add_argument('--actuate', action='store_true', help='Enable individually requested goals; activation may move fingers')
    p.add_argument('--max-force-raw', type=int, default=0)
    p.add_argument('--max-speed-raw', type=int, default=32)
    p.add_argument('--mock-port', type=int, default=63352)
    args=p.parse_args(argv)
    domain='66' if args.mode=='hardware' else '67'
    if os.environ.get('ROS_DOMAIN_ID')!=domain or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST':
        p.error('Expected domain'+domain+' and LOCALHOST')
    if not 0 <= args.max_force_raw <= 255 or not 0 <= args.max_speed_raw <= 255:
        p.error('Raw limits must be0..255')
    if args.mode=='hardware':
        host=yaml.safe_load(args.inventory.read_text())['robots'][args.arm]['ip'];port=63352
        namespace='/uwa_hardware/'+args.arm
    else:
        host='127.0.0.1';port=args.mock_port;namespace='/uwa_gripper_mock/'+args.arm
    if args.mode=='mock' and not ipaddress.ip_address(host).is_loopback:
        p.error('Mock transport requires loopback')
    lease=Path('/tmp')/f'uwa-gripper-{os.getuid()}-{domain}-{args.arm}.lock'
    lock=lease.open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:p.error('Another gripper adapter owns this arm')
    client=Robotiq(host,port=port,enabled=args.actuate,max_force_raw=args.max_force_raw,max_speed_raw=args.max_speed_raw)
    from rclpy.signals import SignalHandlerOptions
    rclpy.init(args=[],signal_handler_options=SignalHandlerOptions.NO)
    def interrupted(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    node=rclpy.create_node('gripper',namespace=namespace)
    group=ReentrantCallbackGroup();state_lock=threading.Lock();busy=False
    publisher=node.create_publisher(String,'~/status',1)
    def publish(value):
        value=dict(value,mode=args.mode,arm=args.arm,actuation_enabled=args.actuate,
                   max_force_raw=args.max_force_raw,max_speed_raw=args.max_speed_raw,
                   force_is_measured_newtons=False)
        publisher.publish(String(data=json.dumps(value)));return value
    def poll():
        with state_lock:
            if busy:return
        try:publish(dict(observed=True,**client.status()))
        except (OSError,RuntimeError,ValueError) as error:publish(dict(observed=False,error=str(error)))
    def read(request,response):
        try:response.message=json.dumps(publish(dict(observed=True,**client.status())));response.success=True
        except (OSError,RuntimeError,ValueError) as error:response.message=str(error);response.success=False
        return response
    def goal(request):
        nonlocal busy
        try:client.validate(request.operation,request.position_raw,request.speed_raw,request.force_raw,request.timeout_s)
        except ValueError as error:node.get_logger().warning(str(error));return GoalResponse.REJECT
        with state_lock:
            if busy:return GoalResponse.REJECT
            busy=True
        return GoalResponse.ACCEPT
    def execute(handle):
        nonlocal busy
        result=RobotiqCommand.Result();request=handle.request
        try:
            def feedback(state):
                value=publish(dict(observed=True,**state));item=RobotiqCommand.Feedback()
                item.status_json=json.dumps(value);handle.publish_feedback(item)
            state=client.command(request.operation,request.position_raw,request.speed_raw,request.force_raw,
                                 request.timeout_s,feedback)
            result.success=True;result.message='Register outcome confirmed; not a measured holding-force/contact proof'
            result.status_json=json.dumps(state);handle.succeed()
        except (OSError,RuntimeError,ValueError) as error:
            result.success=False;result.message=str(error);handle.abort()
        finally:
            with state_lock:busy=False
        return result
    action=ActionServer(node,RobotiqCommand,'~/command',execute_callback=execute,goal_callback=goal,
        # No generic cancel-to-open/reset/force-zero semantics. Arm STOP never
        # cancels or changes the gripper target. Use native emergency controls
        # for a hazardous finger movement; this adapter is not a safety device.
        cancel_callback=lambda handle:CancelResponse.REJECT,callback_group=group)
    node.create_service(Trigger,'~/read',read,callback_group=group)
    node.create_timer(1.,poll,callback_group=group)
    node.get_logger().warning(('ACTUATION ENABLED: explicit goals only' if args.actuate else
        'MONITOR ONLY: all command goals rejected')+'; raw force is not newtons; no automatic activation/opening')
    executor=MultiThreadedExecutor(num_threads=2);executor.add_node(node)
    try:executor.spin()
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        # No reset/GTO0/open/force0 is sent on shutdown. The last target remains
        # at the device. Wait for any bounded outstanding goal before destruction.
        executor.shutdown(timeout_sec=35.);action.destroy();node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        lock.close()

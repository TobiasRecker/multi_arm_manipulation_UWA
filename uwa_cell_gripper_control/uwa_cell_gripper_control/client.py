"""Synchronous agent client over ROS actions/services; never uses device sockets."""
import argparse
import json
import os
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from std_srvs.srv import Trigger
from uwa_cell_gripper_interfaces.action import GripperCommand
from .api import ARMS, OPEN, CLOSE, SET_OPENING, ACTIVATE, endpoint, raw_target, nominal_opening_percent, nominal_force_raw


class GripperClient:
    """Owns one ROS client node. Construction/close never actuate or release."""
    def __init__(self, arm, mode='hardware'):
        self.path=endpoint(arm,mode)
        domain='66' if mode=='hardware' else '67'
        if os.environ.get('ROS_DOMAIN_ID')!=domain or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST':
            raise ValueError('Source the correct local domain: '+domain)
        self.owns_context=not rclpy.ok()
        if self.owns_context:rclpy.init(args=[])
        self.node=rclpy.create_node('gripper_client_'+arm)
        self.executor=SingleThreadedExecutor();self.executor.add_node(self.node)
        self.action=ActionClient(self.node,GripperCommand,self.path+'/operate')
        self.services={name:self.node.create_client(Trigger,self.path+'/'+name) for name in ('read','capabilities')}

    def __enter__(self):return self

    def __exit__(self,*args):self.close()

    def close(self):
        self.action.destroy();self.executor.remove_node(self.node);self.executor.shutdown()
        self.node.destroy_node()
        if self.owns_context and rclpy.ok():rclpy.shutdown()

    def wait(self, future, timeout):
        deadline=time.monotonic()+timeout
        while not future.done():
            if time.monotonic()>=deadline:
                raise TimeoutError('Result unconfirmed; an accepted command may continue. No retry/cancel/open sent.')
            self.executor.spin_once(timeout_sec=.01)
        return future.result()

    def service(self, name):
        if name not in self.services:self.services[name]=self.node.create_client(Trigger,self.path+'/'+name)
        client=self.services[name]
        # Persist endpoints across reads; each request still fetches fresh
        # device status. Graph churn must not interrupt the arm managers.
        if not client.wait_for_service(timeout_sec=10.):raise RuntimeError('Gripper service unavailable: '+self.path+'/'+name)
        response=self.wait(client.call_async(Trigger.Request()),3.)
        if not response.success:raise RuntimeError(response.message)
        return json.loads(response.message)

    def status(self):return self.service('read')

    def capabilities(self):return self.service('capabilities')

    def command(self, operation, *, opening_percent=0., force_raw=0, speed_raw=16, timeout_s=15., feedback=None):
        raw_target(operation,opening_percent)
        for name,value in [('force_raw',force_raw),('speed_raw',speed_raw)]:
            if type(value) is not int or not 0<=value<=255:raise ValueError(name+' must be an integer0..255')
        if not 1<=timeout_s<=30:raise ValueError('timeout_s must be1..30')
        goal=GripperCommand.Goal(operation=operation,opening_percent=float(opening_percent),
            force_raw=force_raw,speed_raw=speed_raw,timeout_s=float(timeout_s))
        if not self.action.wait_for_server(timeout_sec=10.):raise RuntimeError('Gripper action unavailable: '+self.path+'/operate')
        callback=None if feedback is None else lambda msg:feedback(json.loads(msg.feedback.status_json))
        handle=self.wait(self.action.send_goal_async(goal,feedback_callback=callback),3.)
        if not handle.accepted:raise RuntimeError('Command rejected: inspect capabilities, busy status, monitor mode and configured raw limits')
        result=self.wait(handle.get_result_async(),timeout_s+3.).result
        if not result.success:raise RuntimeError(result.message)
        return dict(success=True,message=result.message,contact_detected=result.contact_detected,
                    position_raw=result.position_raw,status=json.loads(result.status_json))

    def open(self, *, speed_raw=16, force_raw=0, timeout_s=15., feedback=None):
        return self.command(OPEN,speed_raw=speed_raw,force_raw=force_raw,timeout_s=timeout_s,feedback=feedback)

    def close_gripper(self, *, force_raw=None, force_n=None, speed_raw=16, timeout_s=15., feedback=None):
        if (force_raw is None)==(force_n is None):raise ValueError('Specify exactly one of force_raw or nominal force_n')
        raw=force_raw if force_n is None else nominal_force_raw(force_n)
        result=self.command(CLOSE,force_raw=raw,speed_raw=speed_raw,timeout_s=timeout_s,feedback=feedback)
        if force_n is not None:result['nominal_request']=dict(force_n=force_n,force_raw=raw,mapping='linear nominal20..235N; not measured force')
        return result

    def set_opening(self, opening_percent, *, force_raw=0, speed_raw=16, timeout_s=15., feedback=None):
        return self.command(SET_OPENING,opening_percent=opening_percent,force_raw=force_raw,
                            speed_raw=speed_raw,timeout_s=timeout_s,feedback=feedback)

    def set_width_mm(self, width_mm, *, force_raw=0, speed_raw=16, timeout_s=15., feedback=None):
        percent=nominal_opening_percent(width_mm)
        result=self.set_opening(percent,force_raw=force_raw,speed_raw=speed_raw,timeout_s=timeout_s,feedback=feedback)
        result['nominal_request']=dict(width_mm=width_mm,opening_percent=percent,mapping='nominal85mm stroke; not measured aperture')
        return result

    def activate(self, *, timeout_s=15., feedback=None):
        return self.command(ACTIVATE,timeout_s=timeout_s,feedback=feedback)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',choices=ARMS,required=True)
    p.add_argument('--mode',choices=['hardware','mock'],default='hardware')
    commands=p.add_subparsers(dest='op',required=True)
    for name in ('status','capabilities'):commands.add_parser(name)
    for name in ('open','close','set-opening','set-width','activate'):
        child=commands.add_parser(name)
        if name=='set-opening':child.add_argument('opening_percent',type=float)
        if name=='set-width':child.add_argument('width_mm',type=float)
        force=child.add_mutually_exclusive_group(required=name=='close')
        force.add_argument('--force-raw',type=int)
        force.add_argument('--force-n',type=float,help='Nominal linear20..235N scale; not measured force')
        child.add_argument('--speed-raw',type=int,default=16)
        child.add_argument('--timeout',type=float,default=15.)
    args=p.parse_args(argv)
    try:
        with GripperClient(args.arm,args.mode) as client:
            if args.op=='status':result=client.status()
            elif args.op=='capabilities':result=client.capabilities()
            else:
                operation={'open':OPEN,'close':CLOSE,'set-opening':SET_OPENING,'set-width':SET_OPENING,'activate':ACTIVATE}[args.op]
                raw=nominal_force_raw(args.force_n) if args.force_n is not None else (args.force_raw or 0)
                percent=nominal_opening_percent(args.width_mm) if args.op=='set-width' else getattr(args,'opening_percent',0.)
                result=client.command(operation,opening_percent=percent,
                    force_raw=raw,speed_raw=args.speed_raw,timeout_s=args.timeout)
                if args.force_n is not None or args.op=='set-width':
                    result['nominal_request']=dict(width_mm=getattr(args,'width_mm',None),force_n=args.force_n,
                        opening_percent=percent,force_raw=raw,mapping='nominal85mm / linear20..235N; not calibrated')
        print(json.dumps(result,indent=2,allow_nan=False))
    except (ValueError,RuntimeError,OSError) as error:
        print(json.dumps(dict(success=False,error=str(error))));raise SystemExit(1)

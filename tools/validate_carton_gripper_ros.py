#!/usr/bin/env python3
"""ROS action integration on domain67 and a loopback register emulator only."""
import argparse
import json
import os
from pathlib import Path
import signal
import socketserver
import subprocess
import sys
import threading
import time

import rclpy
from rclpy.action import ActionClient
from std_msgs.msg import String
from std_srvs.srv import Trigger
from uwa_cell_gripper_interfaces.action import RobotiqCommand


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if os.environ.get('ROS_DOMAIN_ID')!='67' or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST':
        p.error('Isolated mock67/LOCALHOST required')
    args.output.mkdir(parents=True,exist_ok=False)
    registers=dict(ACT=0,STA=0,FLT=0,OBJ=0,POS=3,PRE=0,SPE=0,FOR=0,COU=0,GTO=0)
    writes=[];lock=threading.Lock()
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            while True:
                line=self.rfile.readline(256)
                if not line:return
                words=line.decode('ascii').split()
                with lock:
                    if len(words)==2 and words[0]=='GET' and words[1] in registers:
                        self.wfile.write(f'{words[1]} {registers[words[1]]}\n'.encode());self.wfile.flush()
                    elif words[0]=='SET' and len(words)%2==1:
                        values={words[i]:int(words[i+1]) for i in range(1,len(words),2)}
                        writes.append(values);registers.update(values)
                        if 'ACT' in values:registers['STA']=3 if values['ACT'] else 0
                        if 'GTO' in values:registers.update(PRE=registers['POS'],OBJ=3)
                        self.wfile.write(b'ack');self.wfile.flush()
                    else:self.wfile.write(b'bad');self.wfile.flush()
    server=socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    rclpy.init();node=rclpy.create_node('uwa_gripper_mock_validation');status=[];process=None;logs=[]
    ns='/uwa_gripper_mock/right_front/gripper'
    node.create_subscription(String,ns+'/status',lambda msg:status.append(json.loads(msg.data)),1)
    client=ActionClient(node,RobotiqCommand,ns+'/command');read=node.create_client(Trigger,ns+'/read')
    def wait(predicate,timeout=15.):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.03)
            if predicate():return
            if process is not None and process.poll() is not None:raise RuntimeError('Own mock adapter exited')
        raise TimeoutError('Own mock ROS operation timed out')
    def send(operation,position=0,speed=0,force=0):
        goal=RobotiqCommand.Goal(operation=operation,position_raw=position,speed_raw=speed,force_raw=force,timeout_s=5.)
        future=client.send_goal_async(goal);wait(future.done);handle=future.result()
        if not handle.accepted:return dict(accepted=False)
        future=handle.get_result_async();wait(future.done,8.);result=future.result().result
        return dict(accepted=True,success=result.success,status=json.loads(result.status_json) if result.status_json else {},message=result.message)
    results={}
    try:
        for enabled in (False,True):
            phase='enabled' if enabled else 'monitor';start=len(status)
            log=(args.output/(phase+'.log')).open('w');logs.append(log)
            command=[sys.executable,str(Path(__file__).with_name('carton_gripper_ros.py')),
                '--mode','mock','--arm','right_front','--mock-port',str(server.server_address[1])]
            if enabled:command.append('--actuate')
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            wait(lambda:len(status)>start and status[-1].get('actuation_enabled') is enabled and client.server_is_ready())
            wait(lambda:read.service_is_ready());future=read.call_async(Trigger.Request());wait(future.done)
            assert future.result().success
            if not enabled:
                assert send(2)['accepted'] is False and send(1,128,10,0)['accepted'] is False
                assert writes==[];results['monitor_no_writes']=True
            else:
                assert send(1,128,10,1)['accepted'] is False
                assert writes==[];results['above_raw_force_cap_rejected']=True
                activated=send(2);assert activated['success']
                moved=send(1,128,10,0);assert moved['success'] and moved['status']['registers']['PRE']==128
                results['explicit_activate_and_move']=True
            process.send_signal(signal.SIGINT);process.wait(timeout=8.);assert process.returncode==0;process=None
        assert writes==[{'ACT':0},{'ACT':1},{'FOR':0},{'SPE':10},{'POS':128},{'GTO':1}]
        results['shutdown_no_open_reset_or_force_zero']=True
        report=dict(passed=True,domain=67,transport='loopback TCP emulator',hardware_commands_sent=False,
            checks=results,writes_to_emulator=writes,interpretation='ROS/interface evidence only; no physical activation, force calibration or grasp proof')
        (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:
        if process is not None and process.poll() is None:process.send_signal(signal.SIGINT);process.wait(timeout=8.)
        for log in logs:log.close()
        client.destroy();node.destroy_node();rclpy.shutdown();server.shutdown();server.server_close();worker.join(timeout=2.)


if __name__=='__main__':main()

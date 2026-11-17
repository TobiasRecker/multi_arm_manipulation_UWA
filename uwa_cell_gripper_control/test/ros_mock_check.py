"""Explicit integration run: loopback register emulator, mock domain67 only."""
import json
import os
from pathlib import Path
import signal
import socketserver
import subprocess
import threading
import time

from rclpy.action import ActionClient
from uwa_cell_gripper_interfaces.action import GripperCommand, RobotiqCommand
from uwa_cell_gripper_control.client import GripperClient


def main():
    if os.environ.get('ROS_DOMAIN_ID')!='67':raise RuntimeError('Mock67 only')
    root=Path('/home/rosmatch/UWA_ws/setup/research/gripper-ros-api-20261117/mock')
    root.mkdir(parents=True,exist_ok=False)
    regs=dict(ACT=0,STA=0,FLT=0,OBJ=0,POS=3,PRE=0,SPE=0,FOR=0,COU=0)
    writes=[];pending=[0];release=threading.Event();gate=threading.Lock()
    def finish():
        if pending[0]==128 and not release.is_set():regs['OBJ']=0;return
        regs.update(PRE=pending[0],POS=140 if pending[0]==255 else pending[0],OBJ=2 if pending[0]==255 else 3)
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            for data in self.rfile:
                fields=data.decode().strip().split()
                with gate:
                    if fields[0]=='GET':
                        if regs.get('GTO'):finish()
                        self.wfile.write(f'{fields[1]} {regs[fields[1]]}\n'.encode())
                    else:
                        assert len(fields)==3,'Only separately acknowledged writes expected'
                        key,value=fields[1],int(fields[2]);writes.append(dict(key=key,value=value))
                        if key=='POS':pending[0]=value
                        else:regs[key]=value
                        if key=='ACT':regs['STA']=3 if value else 0
                        if regs.get('GTO') and key in ('POS','GTO'):finish()
                        self.wfile.write(b'ack')
                    self.wfile.flush()
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address=True;daemon_threads=True
    server=Server(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    command=['ros2','run','uwa_cell_gripper_control','cell_gripper_node','--arm','left_front',
             '--mode','mock','--mock-port',str(server.server_address[1]),'--max-force-raw','64']
    processes=[];logs=[];result=dict(success=False)
    def start(enabled):
        log=(root/('enabled.log' if enabled else 'monitor.log')).open('w');logs.append(log)
        p=subprocess.Popen(command+(['--actuate'] if enabled else []),stdout=log,stderr=subprocess.STDOUT)
        processes.append(p);return p
    def stop(p):
        p.send_signal(signal.SIGINT);p.wait(timeout=8.)
        assert p.returncode==0
    try:
        process=start(True)
        with GripperClient('left_front','mock') as client:
            assert client.capabilities()['actuation_enabled']
            assert not writes,'Startup sent SET'
            try:client.close_gripper(force_raw=20)
            except RuntimeError as e:assert 'inactive' in str(e)
            else:raise AssertionError('Inactive close implicitly activated')
            assert not writes
            client.activate();assert regs['ACT']==1
            assert client.open()['position_raw']==0
            # The two APIs must share a single reservation.
            goal=GripperCommand.Goal(operation=3,opening_percent=50.,force_raw=20,speed_raw=16,timeout_s=5.)
            h=client.wait(client.action.send_goal_async(goal),3.);assert h.accepted
            completed=h.get_result_async()
            until=time.monotonic()+3.
            while not client.status()['busy'] and time.monotonic()<until:time.sleep(.02)
            legacy=ActionClient(client.node,RobotiqCommand,client.path+'/command')
            assert legacy.wait_for_server(timeout_sec=3.)
            raw=RobotiqCommand.Goal(operation=1,position_raw=0,force_raw=0,speed_raw=16,timeout_s=5.)
            assert not client.wait(legacy.send_goal_async(raw),3.).accepted
            legacy.destroy()
            release.set();answer=client.wait(completed,6.).result
            assert answer.success and answer.position_raw==128
            assert client.close_gripper(force_raw=20)['contact_detected']
            assert client.status()['registers']['FOR']==20
            before=len(writes)
            try:client.command(3,opening_percent=101)
            except ValueError:pass
            else:raise AssertionError('Invalid percent accepted')
            try:client.close_gripper(force_raw=65)
            except RuntimeError:pass
            else:raise AssertionError('Raw-force cap not enforced')
            assert len(writes)==before
            duplicate=subprocess.run(command,capture_output=True,text=True,timeout=8.)
            assert duplicate.returncode and 'Another gripper adapter' in duplicate.stderr
        stop(process);before=len(writes)
        assert regs['FOR']==20 and regs['POS']==140,'Shutdown changed held target'
        process=start(False)
        with GripperClient('left_front','mock') as client:
            assert not client.capabilities()['actuation_enabled']
            assert client.status()['registers']['FOR']==20
            try:client.open()
            except RuntimeError:pass
            else:raise AssertionError('Monitor accepted movement')
        stop(process);assert len(writes)==before,'Monitor/startup/exit sent a write'
        result.update(success=True,checks=['no-startup-write','inactive-close-rejected','explicit-activation',
            'open','relative-opening','contact-close-with-raw-force','parameter-readback','legacy-and-convenience-single-writer',
            'force-cap','duplicate-process-lease','monitor-no-write','shutdown-retains-target'],writes=writes)
    except BaseException as error:
        import traceback
        result.update(error=str(error),traceback=traceback.format_exc())
    finally:
        release.set()
        for p in processes:
            if p.poll() is None:
                p.send_signal(signal.SIGINT)
                try:p.wait(timeout=8.)
                except subprocess.TimeoutExpired:p.kill();p.wait()
        for log in logs:log.close()
        server.shutdown();server.server_close()
        (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['success']:raise SystemExit(1)


if __name__=='__main__':main()

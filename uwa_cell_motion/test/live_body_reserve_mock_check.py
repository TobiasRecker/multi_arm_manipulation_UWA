"""Explicit multiprocess v2 integration in domain67; never collected by pytest.

Fake managers use a loopback-only inventory. Guard/supervisor/watchdog run in
separate processes as in deployment. No real arm, program or device is used.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import numpy as np
import rclpy
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger
import yaml

from live_hardware_mock_check import FakeManager
from uwa_cell_motion.common import config,dump,ROBOT_IDS,joint_names,BODY_RESERVE_MODEL
from uwa_cell_motion.hardware_model import HardwareProblem,inventory_path
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_motion.hardware_execution import HardwareClient
from uwa_cell_motion.hardware_ports import HOLD
from match_ur_hardware.profiles import load_profiles


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    args=p.parse_args();require_domain('mock')
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    cfg=config(args.config)
    if cfg.get('stopping_reserve_model')!=BODY_RESERVE_MODEL:raise ValueError('v2 profile required')
    inventory=yaml.safe_load(inventory_path().read_text());original=load_profiles(inventory_path())
    inventory['ros_namespace']='/uwa_body_reserve_validation'
    for index,(rid,profile) in enumerate(inventory['robots'].items()):
        profile.update(ip='127.0.0.'+str(index+2),kinematics_file=original[rid]['kinematics_file'])
    inv=root/'inventory.yaml';inv.write_text(yaml.safe_dump(inventory))
    cfgpath=root/'config.yaml';cfgpath.write_text(yaml.safe_dump(cfg))
    model=HardwareProblem(root/'model',cfg,inv)
    result=dict(success=False,backend='mock',real_tcp_allowed=False,processes_separate=True)
    old=socket.create_connection
    def forbidden(*a,**k):raise AssertionError('Fake integration attempted a device TCP connection')
    socket.create_connection=forbidden
    rclpy.init();managers=[];processes={};logs=[];client=None;worker=None;executor=None
    def start(role):
        log=(root/(role+'-'+str(time.monotonic_ns())+'.log')).open('w');logs.append(log)
        command=['ros2','run','uwa_cell_motion','cell_hardware_motion','--mode','mock',
            '--config',str(cfgpath),'--inventory',str(inv),role,'--armed']
        processes[role]=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    def stop(role):
        child=processes.pop(role,None)
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGINT)
            try:child.wait(timeout=8.)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3.)
    try:
        managers=[FakeManager(profile,model,cfg) for profile in model.profiles.values()]
        byid={m.p['id']:m for m in managers}
        executor=MultiThreadedExecutor(num_threads=8)
        for manager in managers:executor.add_node(manager)
        worker=threading.Thread(target=executor.spin,daemon=True);worker.start()
        for role in ('guard','supervisor','watchdog'):start(role)
        client=HardwareClient(model,'mock',['right_front'])
        client.connect(guard=False)
        def wait(seconds):
            until=time.monotonic()+seconds;client.wait(lambda:time.monotonic()>=until,seconds+2.)
        def held():return {m.p['id'] for m in managers if m.states[HOLD]=='active'}
        def reset():
            for attempt in range(3):
                stable=[None]
                def ready():
                    now=time.monotonic();supervisor=client.supervisor or {}
                    good=(client.guard_peer.fresh(now,cfg['heartbeat_timeout_s'])
                        and client.supervisor_peer.fresh(now,cfg['heartbeat_timeout_s'])
                        and client.guard is not None and not client.guard.get('faults')
                        and set(client.guard.get('stationary_arms',[]))==set(ROBOT_IDS)
                        and supervisor.get('witness_available')
                        and supervisor.get('guard_age_s',float('inf'))<cfg['heartbeat_timeout_s']
                        and supervisor.get('witness_age_s',float('inf'))<cfg['heartbeat_timeout_s']
                        and len(supervisor.get('ports',{}))==4
                        and all(all(port.get(k) for k in ('manager_fresh','hardware_mode_verified','hold_config_verified'))
                            for port in supervisor['ports'].values()))
                    if not good:stable[0]=None;return False
                    if stable[0] is None:stable[0]=now
                    return now-stable[0]>=.7
                client.wait(ready,15.)
                answer=client.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request())
                if not answer.success:raise RuntimeError(answer.message)
                try:
                    client.wait(lambda:not client.supervisor['blocked_arms'] and not held(),1.)
                    return
                except TimeoutError:
                    if attempt==2:raise
        client.wait(lambda:held()==set(ROBOT_IDS),10.);reset();client.health()
        result['explicit_initial_reset']=True
        q0=np.array([client.positions[j] for j in joint_names('right_front')])
        target=q0+np.array([0,0,0,0,0,.003])
        if not model.edge(dict(start=dict(client.positions),joint_names=joint_names('right_front')),q0,target):
            raise RuntimeError('Tiny fake path is not model-clear')
        client.activate(['right_front'])
        assert not client.phase({'right_front':target},cfg,set())
        assert max(abs(np.array([client.positions[j] for j in joint_names('right_front')])-target))<.001
        result['joint_capped_fake_motion_completed']=True
        answer=client.service(Trigger,'/uwa_cell/collision_supervisor/right_front/stop',Trigger.Request());assert answer.success
        client.wait(lambda:'right_front' in held(),3.);wait(.7);reset()
        byid['left_front'].freeze=True
        client.wait(lambda:held()=={'left_front','right_front','left_rear'},4.)
        result['frozen_source_stops_only_neighbors']=True
        byid['left_front'].freeze=False;wait(.7)
        assert held()=={'left_front','right_front','left_rear'}
        result['no_automatic_restart_after_source_recovery']=True
        reset();stop('guard');client.wait(lambda:held()==set(ROBOT_IDS),4.)
        result['guard_loss_stops_all']=True
        start('guard');wait(2.);assert held()==set(ROBOT_IDS);reset()
        stop('watchdog');client.wait(lambda:held()==set(ROBOT_IDS),4.)
        result['watchdog_loss_stops_all']=True
        start('watchdog');wait(2.);reset()
        stop('supervisor');client.wait(lambda:held()==set(ROBOT_IDS),4.)
        result['supervisor_loss_independent_watchdog_holds_all']=True
        result.update(success=True,final_held=sorted(held()),guard=client.guard,
            qualification='Fake controllers and ROS processes only; no UR stopping proof')
    except BaseException as error:
        import traceback
        result.update(error=str(error),traceback=traceback.format_exc())
        if client:result.update(guard=client.guard,supervisor=client.supervisor)
    finally:
        for manager in managers:
            with manager.lock:
                manager.states={name:('active' if name==HOLD else 'inactive') for name in manager.states}
                manager.v=np.zeros(6)
        for role in list(processes):stop(role)
        if client:client.destroy_node()
        if executor:executor.shutdown(timeout_sec=3.)
        if worker:worker.join(timeout=3.)
        for manager in managers:manager.destroy_node()
        rclpy.shutdown();socket.create_connection=old
        for log in logs:log.close()
        dump(root/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('guard','supervisor','traceback')}))
    if not result['success']:raise SystemExit(1)


if __name__=='__main__':main()

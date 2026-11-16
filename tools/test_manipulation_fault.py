#!/usr/bin/env python3
"""Inject one scoped simulation fault after verified unsupported load pickup.

This deliberately fails a running recipe. It never opens a gripper, commands a
trajectory or resumes a stopped group. A paused process is always continued for
cleanup; the recipe must then terminate FAILED with independently held arms.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger

from match_cooperative_handling.rigid_object import pose_error
from uwa_cell_description.configuration import joint_names
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import simulation_only
from uwa_cell_tasks.core import ARMS,write_json,seal
from uwa_cell_tasks.scene import verify_scene


def stop_window(history):
    """Reject continued slow rigid motion, even below velocity standstill tolerance."""
    if len(history)<3:return dict(ready=False)
    elapsed=history[-1][0]-history[0][0]
    arm_span=float(np.max(np.ptp([r[1] for r in history],axis=0)))
    poses=np.array([r[2] for r in history])
    translation_span=float(np.max(np.ptp(poses[:,:3,3],axis=0)))
    rotation_span=float(np.max(np.ptp(poses[:,:3,:3],axis=0)))
    return dict(ready=elapsed>=.3 and arm_span<=1e-5 and translation_span<=1e-4 and rotation_span<=1e-4,
        window_wall_s=elapsed,maximum_arm_span_rad=arm_span,
        maximum_object_axis_span_m=translation_span,maximum_object_rotation_element_span=rotation_span)


def process_for(role,run,scene):
    matches=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:raw=(path/'cmdline').read_bytes();args=raw.decode().rstrip('\0').split('\0')
        except (OSError,UnicodeError):continue
        if len(args)<3 or Path(args[1]).name!='cell_task' or args[2]!=role:continue
        option='--output' if role=='run' else '--scene';target=run if role=='run' else scene
        value=Path(args[args.index(option)+1]) if option in args else None
        if value is not None and not value.is_absolute():value=(path/'cwd').resolve()/value
        if value is not None and value.resolve()==target.resolve():
            matches.append((int(path.name),raw))
    if len(matches)!=1:raise RuntimeError(f'Expected exactly one scoped {role} process; found {len(matches)}')
    return matches[0]


def execute(args):
    scene=verify_scene(args.scene);data={};received={};paused=None;node=None
    report=dict(kind='loaded_group_fault_injection',fault=args.fault,passed=False,injected=False,
        run=str(args.run.resolve()),scene=str(args.scene.resolve()),namespace=args.namespace,
        scene_sha256=scene['sha256'],trajectory_commanded=False,gripper_open_commanded=False,
        injector_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),started_at_unix_s=time.time())
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    def interrupted(signum,frame):raise KeyboardInterrupt('Signal '+str(signum))
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
    def put(key,value):data[key]=value;received[key]=time.monotonic()
    def spin():rclpy.spin_once(node,timeout_sec=.02)
    def fresh():return all(time.monotonic()-received.get(k,0.)<.15 for k in ('object','contacts','joints'))
    try:
        node=Node('task_fault_probe',namespace=args.namespace)
        for key,topic in [('object','tasks/object_truth'),('contacts','tasks/contacts'),
                          ('guard','collision_guard/decision'),('supervisor','collision_supervisor/status')]:
            node.create_subscription(String,args.namespace+'/'+topic,lambda m,k=key:put(k,json.loads(m.data)),
                qos_profile_sensor_data if key in ('object','contacts') else 10)
        node.create_subscription(String,args.namespace+'/tasks/group',lambda m:put('group',json.loads(m.data)),
            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        node.create_subscription(JointState,args.namespace+'/joint_states',lambda m:put('joints',
            dict(positions=dict(zip(m.name,m.position)),velocities=dict(zip(m.name,m.velocity)))),qos_profile_sensor_data)
        stops={a:node.create_client(Trigger,args.namespace+'/collision_supervisor/'+a+'/stop') for a in ARMS}
        description=(args.scene/'robot.urdf').read_text()
        chains={a:Chain(description,'world',a+'_tool0') for a in ARMS}
        # Includes three agent reviews, Home approach and the slow load-transfer
        # profile. This waiting budget does not change the5s physical-stop limit.
        origin=None;grasp_offsets=None;ready_since=None;deadline=time.monotonic()+900.
        print('WAITING FOR UNSUPPORTED LOADED GROUP',flush=True)
        while True:
            spin();now=time.monotonic();state=json.loads((args.run/'state.json').read_text())
            if state['state'] in ('DONE','FAILED'):raise RuntimeError('Recipe ended before fault injection: '+state['state'])
            if now>deadline:raise TimeoutError('Loaded-group wait expired')
            if origin is None and fresh():origin=np.array(data['object']['T_world_object'])
            group=data.get('group',{});guard=data.get('guard',{});contact=data.get('contacts',{})
            supervisor=data.get('supervisor',{})
            if (grasp_offsets is None and fresh() and group.get('members')==list(ARMS)
                    and not group.get('released') and contact.get('supported')
                    and all(all(contact['pads'][a].values()) for a in ARMS)):
                # Freeze once at supported group formation, not after lifting:
                # do not hide pre-existing load-transfer deflection/slip.
                grasp_pose=np.array(data['object']['T_world_object'])
                grasp_offsets={a:np.linalg.inv(grasp_pose)@chains[a].forward(data['joints']['positions']) for a in ARMS}
                report['grasp_baseline_object_pose']=grasp_pose.tolist()
                report['grasp_baseline_contacts']=contact
                report['grasp_baseline_offsets']={a:t.tolist() for a,t in grasp_offsets.items()}
            ready=(fresh() and origin is not None and state['phase']=='move_object'
                and guard.get('scene_sha256')==scene['sha256'] and guard.get('active_grasp_members')==list(ARMS)
                and now-received.get('guard',0.)<.15 and now-received.get('supervisor',0.)<.15
                and guard.get('state')=='CLEAR' and not guard.get('faults') and not guard.get('latched_causes')
                and not set(ARMS).intersection(supervisor.get('blocked_arms',[]))
                and not set(ARMS).intersection(supervisor.get('held_arms',[]))
                and group.get('members')==list(ARMS) and not group.get('released')
                and not contact.get('supported',True) and all(all(contact['pads'][a].values()) for a in ARMS)
                and data['object']['T_world_object'][2][3]-origin[2,3]>=.005)
            if not ready:ready_since=None;continue
            if grasp_offsets is None:raise RuntimeError('No supported group-formation baseline recorded before pickup')
            if ready_since is None:ready_since=now
            if now-ready_since>=.2:break
        initial=np.array(data['object']['T_world_object'])
        offsets=grasp_offsets
        report['initial_object_pose']=initial.tolist();report['initial_contacts']=data['contacts']
        report['pre_injection_guard']=data['guard'];report['pre_injection_supervisor']=data['supervisor']
        injected_at=time.monotonic();stop_reply=None;report['injected_at_unix_s']=time.time()
        if args.fault=='member_stop':
            client=stops[ARMS[0]]
            if not client.wait_for_service(timeout_sec=2.):raise RuntimeError('Scoped member stop service absent')
            stop_reply=client.call_async(Trigger.Request())
        else:
            role='run' if args.fault=='runner_pause' else 'guard'
            paused=process_for(role,args.run,args.scene);os.kill(paused[0],signal.SIGSTOP)
            report['paused_role']=role;report['paused_pid']=paused[0]
        report['injected']=True;print('FAULT INJECTED: '+args.fault,flush=True)
        both_held=None;held_since=None;errors=[];all_contacts_retained=True;telemetry_fresh=True;peak_speed=0.
        stationary_history=[];stationary=dict(ready=False)
        while time.monotonic()-injected_at<5.:
            spin();now=time.monotonic()
            if not fresh():telemetry_fresh=False;continue
            contact=data['contacts'];all_contacts_retained &= all(all(contact['pads'][a].values()) for a in ARMS)
            peak_speed=max(peak_speed,max(abs(v) for j,v in data['joints']['velocities'].items() if j.startswith(ARMS)))
            obj=np.array(data['object']['T_world_object'])
            errors.extend(pose_error(chains[a].forward(data['joints']['positions']),obj@offsets[a]) for a in ARMS)
            stationary_history.append((now,np.array([data['joints']['positions'][j] for a in ARMS for j in joint_names(a)]),obj))
            stationary_history=[r for r in stationary_history if r[0]>=now-.35]
            stationary=stop_window(stationary_history)
            supervisor=data.get('supervisor',{})
            held=(set(ARMS)<=set(supervisor.get('held_arms',[]))
                and set(ARMS)<=set(supervisor.get('blocked_arms',[]))
                and stationary['ready']
                and all(abs(data['joints']['velocities'].get(j,1.))<.003 for a in ARMS for j in joint_names(a)))
            if held and both_held is None:both_held=now
            if not held:held_since=None
            elif held_since is None:held_since=now
            if held_since is not None and now-held_since>=.6:break
        else:raise TimeoutError('Both independent holds were not confirmed and retained')
        report.update(both_held_latency_wall_s=both_held-injected_at,pads_retained=all_contacts_retained,
            stationary_window=stationary,
            stationary_window_limits=dict(minimum_wall_s=.3,arm_span_rad=1e-5,object_axis_span_m=1e-4,object_rotation_element_span=1e-4),
            telemetry_fresh_during_stop=telemetry_fresh,
            maximum_observed_right_joint_speed_rad_s=peak_speed,
            maximum_rigidity_error_m=max(e[0] for e in errors),maximum_rigidity_error_rad=max(e[1] for e in errors),
            final_contacts=data['contacts'],supervisor=data['supervisor'],guard=data.get('guard'))
        if stop_reply is not None:
            report['member_stop_acknowledged']=bool(stop_reply.done() and stop_reply.result().success)
        report['passed']=(telemetry_fresh and all_contacts_retained and not data['contacts']['supported']
            and peak_speed<=scene['cfg']['joint_velocity_rad_s']+1e-8
            and (stop_reply is None or report['member_stop_acknowledged'])
            and report['maximum_rigidity_error_m']<=scene['cfg']['relative_position_tolerance_m']
            and report['maximum_rigidity_error_rad']<=scene['cfg']['relative_angle_tolerance_rad'])
    except BaseException as error:report['error']=str(error)
    finally:
        if report['injected'] and not report['passed']:
            (args.run/'STOP').write_text('STOP REQUESTED: fault-test cleanup\n')
            report['cleanup_stop_requested']=True
            if node is not None:
                for client in stops.values():client.call_async(Trigger.Request())
        if paused is not None:
            try:
                if Path(f'/proc/{paused[0]}/cmdline').read_bytes()==paused[1]:
                    os.kill(paused[0],signal.SIGCONT);report['resume_sent']=True
            except OSError:report['resume_sent']=False
        if node is not None and report['injected']:
            # Physical-stop deadline above remains5s. Allow bounded read-only
            # RPC retry/diagnostic cleanup after resuming a paused process.
            end=time.monotonic()+25.
            while time.monotonic()<end:
                spin();state=json.loads((args.run/'state.json').read_text())
                if state['state']=='FAILED':break
            report['recipe_final_state']=state['state'];report['recipe_stop']=state.get('stop')
            report['passed'] &= state['state']=='FAILED' and bool(state.get('stop',{}).get('confirmed'))
        report=seal(report);write_json(args.run/'fault-test-report.json',report);print(json.dumps(report),flush=True)
        if node is not None:node.destroy_node()
        rclpy.shutdown()
    return 0 if report['passed'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
    parser.add_argument('--scene',type=Path,required=True)
    parser.add_argument('--fault',choices=['member_stop','runner_pause','guard_pause'],required=True)
    parser.add_argument('--namespace',default='/uwa_grasp_validation');args=parser.parse_args();simulation_only()
    if not args.namespace.startswith('/uwa_grasp_'):parser.error('Isolated simulation namespace required')
    if not (args.run/'state.json').is_file():parser.error('Existing running task required')
    with (args.run/'fault-test.lock').open('x') as lock:
        lock.write(args.fault+'\n');lock.flush();return execute(args)


if __name__=='__main__':raise SystemExit(main())

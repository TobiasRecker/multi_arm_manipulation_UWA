#!/usr/bin/env python3
"""Dispatch exact offline-checked serial observation trajectories on N100.

Geometry is compiled on ROSmini and SHA-bound to the active model and checker
sources. Minimal mode uses the shared protection service and retained action
goals; legacy mode keeps its previous checks. No N100 planning or retiming.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import time
import sys
import threading

import numpy as np
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory

from uwa_cell_motion.common import dump, joint_names
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_execution import HardwareClient
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_tasks.reviewed_carton_execution import _build_goal, _start_matches, _monitor
from uwa_cell_motion.common import ROBOT_IDS
from std_srvs.srv import Trigger


def checked_plans(folder, digest, cap):
    raw=(folder/'sequence.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:
        raise ValueError('Authorized sequence SHA changed')
    sequence=json.loads(raw)
    if sequence['command_velocity_limit_rad_s']!=cap:
        raise ValueError('Task-specific approved command cap changed')
    plans=[]
    for entry in sequence['segments']:
        file=folder/entry['plan']
        if file.parent.resolve()!=folder.resolve() or hashlib.sha256(file.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Offline-checked plan file changed')
        plan=json.loads(file.read_text())
        if not (plan['success'] and plan['hardware_plan'] and plan['execution_mode']=='hardware'
                and plan['compiled_command_limit_rad_s']==cap and plan['request']['selected']==[entry['arm']]
                and plan['metrics']['full_cell_collision_checked']):
            raise ValueError('Invalid offline checked hardware trajectory')
        points=plan['trajectory']['points']
        times=np.array([p['time'] for p in points]);q=np.array([p['positions'] for p in points])
        v=np.array([p['velocities'] for p in points]);a=np.array([p['accelerations'] for p in points])
        if not (len(times)>1 and times[0]==0 and np.all(np.diff(times)>0)
                and q.shape==v.shape==a.shape==(len(times),6) and np.isfinite(np.r_[times,q.ravel(),v.ravel(),a.ravel()]).all()
                and np.max(abs(v))<=cap+1e-12 and np.max(abs(a))<=plan['config']['acceleration_limit_rad_s2']+1e-12
                and plan['trajectory']['joint_names']==joint_names(entry['arm'])
                and np.allclose(q[0],[plan['request']['start'][j] for j in joint_names(entry['arm'])],rtol=0,atol=1e-10)
                and np.allclose(q[-1],plan['request']['goals'][entry['arm']],rtol=0,atol=1e-10)):
            raise ValueError('Malformed timing, bounds or endpoints in frozen trajectory')
        for name,wanted in plan['portable_binding']['exact_planner_modules'].items():
            if hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()!=wanted:
                raise ValueError('Offline checker source changed: '+name)
        plans.append(plan)
    return sequence,plans


def follow_frozen(client, plan, record):
    rid=plan['request']['selected'][0];trajectory=plan['trajectory']
    group=dict(arms=[rid],start=plan['request']['start'],trajectories={rid:trajectory},duration_s=trajectory['duration_s'])
    if getattr(client,'protection_backend',None)=='minimal':
        client.wait_unpaused();client.health()
        if not set(group['start']) <= client.positions.keys():
            raise ValueError('Current joint inputs unavailable for the checked observation start')
        _start_matches(client.problem,client,group['start'])
        record.update(phase='MOVING',protection_backend='minimal')
        client.follow_group(group['trajectories'],duration_s=group['duration_s'],segment=record)
        record.update(success=True,phase='COMPLETE')
        return
    obstacles=[j for r,names in client.problem.names.items() for j in names if r!=rid or j not in joint_names(r)]
    vertices=np.array([p['positions'] for p in trajectory['points']]);delta=np.diff(vertices,axis=0)
    corridors={rid:(vertices[:-1],delta,np.maximum(np.sum(delta*delta,axis=1),1e-20))}
    client.health();_start_matches(client.problem,client,group['start'])
    _monitor(client,group,corridors,{rid},obstacles,{},None)
    client.activate([rid])
    action=client.actions[rid]
    if not action.wait_for_server(timeout_sec=3.):raise RuntimeError('Trajectory action unavailable')
    client.health();_start_matches(client.problem,client,group['start'])
    goal=_build_goal(trajectory);start=client.get_clock().now().nanoseconds+200_000_000
    goal.trajectory.header.stamp.sec,goal.trajectory.header.stamp.nanosec=divmod(start,10**9)
    sent=time.monotonic();client.pending={rid:action.send_goal_async(goal)}
    client.wait(client.pending[rid].done,3.,health=True)
    handle=client.pending[rid].result();client.handles={rid:handle}
    if not handle.accepted:raise RuntimeError('Frozen observation trajectory rejected')
    result=handle.get_result_async();last_stamp=None
    record.update(phase='MOVING',sent_monotonic_s=sent)
    print(json.dumps(dict(event='TRAJECTORY_ACCEPTED',arm=rid,duration_s=trajectory['duration_s'])),flush=True)
    deadline=sent+trajectory['duration_s']*5+8
    while time.monotonic()<deadline:
        client.spin_once(timeout_sec=.005);client.health()
        if client.stamp!=last_stamp:
            _monitor(client,group,corridors,{rid},obstacles,{},None);last_stamp=client.stamp
            record['maximum_measured_joint_speed_rad_s']=max(record.get('maximum_measured_joint_speed_rad_s',0.),
                max(abs(client.velocities[j]) for j in joint_names(rid)))
        if result.done():
            response=result.result()
            if response.status!=GoalStatus.STATUS_SUCCEEDED or response.result.error_code!=FollowJointTrajectory.Result.SUCCESSFUL:
                raise RuntimeError('Native trajectory result: '+response.result.error_string)
            if max(abs(client.positions[j]-q) for j,q in zip(joint_names(rid),trajectory['points'][-1]['positions']))<=client.cfg['goal_tolerance_rad']:
                record.update(success=True,phase='COMPLETE',dispatch_to_target_s=time.monotonic()-sent,
                    final_positions=dict(client.positions))
                return
    raise TimeoutError('Frozen observation motion timed out')


def run_minimal_sequence(problem,plans,args,check_area):
    """Keep exact serial paths while using only the shared protection service."""
    from uwa_cell_motion.minimal_execution import MinimalHardwareClient
    selected=list(dict.fromkeys(plan['request']['selected'][0] for plan in plans))
    client=MinimalHardwareClient(problem,'hardware',selected)
    records=[]
    try:
        client.connect()
        if args.prepare_stopped_programs:
            from observe_calibration_start import released_area
            from uwa_cell_tasks.minimal_reviewed_execution import start_programs
            scene=released_area(getattr(args,'area_session',None))['session_id']
            start_programs(client,args.output,selected,scene=scene)
        for plan in plans:
            check_area()
            rid=plan['request']['selected'][0]
            record=dict(arm=rid,success=False,phase='CONNECT',frozen_trajectory=True,
                        protection_backend='minimal',command_limit_rad_s=args.command_cap)
            began=time.monotonic()
            try:
                client.connect();follow_frozen(client,plan,record)
            except KeyboardInterrupt as error:
                record.update(error=str(error) or 'Operator cancelled the observation sequence')
                try:record['stop_result']=client.stop()
                except Exception as stop_error:record['stop_error']=str(stop_error)
            except Exception as error:
                record['error']=str(error)
            finally:
                record.update(total_wall_s=time.monotonic()-began,protection_status=client.protection_status)
                records.append(record)
                dump(args.output/('result-'+rid+'.json'),record)
                dump(args.output/'sequence-result.json',dict(protection_backend='minimal',
                    complete=len(records)==len(plans) and all(r['success'] for r in records),
                    results=[{k:r.get(k) for k in ('arm','success','phase','error','total_wall_s')} for r in records]))
            print(json.dumps({k:record.get(k) for k in ('arm','success','phase','error','total_wall_s')}),flush=True)
            if not record['success']:
                raise RuntimeError('Sequence stopped at '+rid+': '+record.get('error','unknown failure'))
    finally:
        client.destroy_node()


def main(args):
    require_domain('hardware')
    def check_area():
        if getattr(args, 'area_session', None):
            from observe_calibration_start import released_area
            released_area(args.area_session)
    check_area()
    sequence,plans=checked_plans(args.plans.resolve(),args.sequence_sha256,args.command_cap)
    args.output.mkdir(parents=True,exist_ok=False)
    records=[]
    with motion_context():
        first=plans[0]
        problem=HardwareProblem(args.output/'model',first['config'],first['inventory'],first.get('layout_path'))
        for plan in plans:
            if problem.binding!=plan['hardware_binding'] or problem.spheres.geometry.assets!=plan['mesh_sha256'] or problem.cfg!=plan['config']:
                raise ValueError('Active hardware model/assets/configuration changed; recompile')
        selected=[p['request']['selected'][0] for p in plans]
        from uwa_cell_motion.protection_backend import minimal_enabled
        if minimal_enabled():
            run_minimal_sequence(problem,plans,args,check_area)
            print('ALL_FOUR_OBSERVATION_POSES_REACHED',flush=True)
            return
        # Serial jobs keep all actions/readers/managers alive across arm changes.
        # Construct/discover while native programs are STOPPED, before releasing
        # the existing holds, so graph allocation cannot interrupt a live start.
        client=HardwareClient(problem,'hardware',selected)
        reset_clients={r:client.create_client(Trigger,'/uwa_cell/collision_supervisor/'+r+'/reset') for r in ROBOT_IDS} if args.prepare_stopped_programs else {}
        try:
            if args.prepare_stopped_programs:
                client.connect(guard=False)
                until=time.monotonic()+2
                while time.monotonic()<until:client.spin_once(timeout_sec=.01)
                if (set(client.records)!=set(ROBOT_IDS) or any(r['status']['runtime_state']!=1 or r['status']['robot_mode']!=7 for r in client.records.values())
                        or set(client.guard.get('stationary_arms',[]))!=set(ROBOT_IDS)):
                    raise RuntimeError('Fresh, stopped, stationary native programs required before connection-preserving preparation')
                for arm,c in reset_clients.items():
                    if not c.wait_for_service(timeout_sec=3.):raise RuntimeError('Reset service unavailable')
                    f=c.call_async(Trigger.Request());client.wait(f.done,6.)
                    if not f.result().success:raise RuntimeError(f.result().message)
                    client.wait(lambda:arm not in client.supervisor['blocked_arms'] and arm not in client.guard['blocked_arms']
                        and not client.supervisor['ports'][arm]['held'],4.)
                if client.supervisor['blocked_arms'] or client.guard['blocked_arms']:
                    raise RuntimeError('Full-cell applied release required')
                sys.path.insert(0,str(Path(first['inventory']).parents[1]/'scripts'))
                from ur_bringup import run_arm,load_arms,Blocked
                startup=[];done=threading.Event()
                def only_play(step):
                    if step!='play':raise Blocked('separate_preparation_required','Only prepared stopped ROS programs may be started')
                def start_programs():
                    try:
                        for arm in load_arms(Path(first['inventory'])).values():
                            row=run_arm(arm,True,before_write=only_play);startup.append(row)
                            if row['code']!='ready':break
                    finally:done.set()
                worker=threading.Thread(target=start_programs,daemon=True);worker.start()
                while not done.is_set():client.spin_once(timeout_sec=.01)
                dump(args.output/'startup.json',startup)
                if len(startup)!=4 or any(r['code']!='ready' for r in startup):raise RuntimeError('Native ROS program startup not confirmed')
                print('PERSISTENT_CONNECTION_AND_FOUR_PROGRAMS_READY',flush=True)
            for plan in plans:
                check_area()
                rid=plan['request']['selected'][0]
                print(json.dumps(dict(event='ARM_START',arm=rid,planned_s=plan['trajectory']['duration_s'])),flush=True)
                record=dict(arm=rid,success=False,phase='CONNECT',frozen_trajectory=True,
                    command_limit_rad_s=args.command_cap,guard_limit_rad_s=problem.cfg['velocity_limit_rad_s'])
                began=time.monotonic()
                try:
                    client.connect();follow_frozen(client,plan,record)
                except BaseException as error:
                    record.update(error=str(error))
                    if client.owned:record['stop_result']=client.stop(client.owned)
                finally:
                    record.update(total_wall_s=time.monotonic()-began,guard_status=client.guard,
                        supervisor_status=client.supervisor)
                    dump(args.output/('result-'+rid+'.json'),record);records.append(record)
                    dump(args.output/'sequence-result.json',dict(complete=all(r['success'] for r in records) and len(records)==len(plans),
                        results=[{k:r.get(k) for k in ('arm','success','phase','error','total_wall_s','dispatch_to_target_s')} for r in records]))
                print(json.dumps({k:record.get(k) for k in ('arm','success','phase','error','total_wall_s','dispatch_to_target_s')}),flush=True)
                if not record['success']:raise RuntimeError('Sequence stopped at '+rid+': '+record.get('error','unknown failure'))
        finally:
            for c in reset_clients.values():client.destroy_client(c)
            client.destroy_node()
    print('ALL_FOUR_OBSERVATION_POSES_REACHED',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plans',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sequence-sha256',required=True);p.add_argument('--command-cap',type=float,required=True)
    p.add_argument('--prepare-stopped-programs',action='store_true',help='Build persistent connection before explicit reset/Play of prepared stopped programs')
    p.add_argument('--area-session',help='Existing operator work-area release, rechecked before each arm')
    main(p.parse_args())

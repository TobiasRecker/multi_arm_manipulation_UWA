#!/usr/bin/env python3
"""Dispatch exact offline-checked serial observation trajectories on N100.

Uses the existing hardware client, start/corridor/obstacle/full-cell checks and
native action results. Geometry is compiled on ROSmini, SHA-bound to the active
hardware model and checker sources. No N100 planning/retiming or guard changes.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import time

import numpy as np
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory

from uwa_cell_motion.common import dump, joint_names
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_execution import HardwareClient
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_tasks.reviewed_carton_execution import _build_goal, _start_matches, _monitor


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


def main(args):
    require_domain('hardware')
    sequence,plans=checked_plans(args.plans.resolve(),args.sequence_sha256,args.command_cap)
    args.output.mkdir(parents=True,exist_ok=False)
    records=[]
    with motion_context():
        first=plans[0]
        problem=HardwareProblem(args.output/'model',first['config'],first['inventory'],first.get('layout_path'))
        for plan in plans:
            if problem.binding!=plan['hardware_binding'] or problem.spheres.geometry.assets!=plan['mesh_sha256'] or problem.cfg!=plan['config']:
                raise ValueError('Active hardware model/assets/configuration changed; recompile')
        for plan in plans:
            rid=plan['request']['selected'][0]
            print(json.dumps(dict(event='ARM_START',arm=rid,planned_s=plan['trajectory']['duration_s'])),flush=True)
            record=dict(arm=rid,success=False,phase='CONNECT',frozen_trajectory=True,
                command_limit_rad_s=args.command_cap,guard_limit_rad_s=problem.cfg['velocity_limit_rad_s'])
            began=time.monotonic();client=HardwareClient(problem,'hardware',[rid])
            try:
                client.connect();follow_frozen(client,plan,record)
            except BaseException as error:
                record.update(error=str(error))
                if client.owned:record['stop_result']=client.stop(client.owned)
            finally:
                record.update(total_wall_s=time.monotonic()-began,guard_status=client.guard,
                    supervisor_status=client.supervisor)
                dump(args.output/('result-'+rid+'.json'),record)
                client.destroy_node();records.append(record)
                dump(args.output/'sequence-result.json',dict(complete=all(r['success'] for r in records) and len(records)==len(plans),
                    results=[{k:r.get(k) for k in ('arm','success','phase','error','total_wall_s','dispatch_to_target_s')} for r in records]))
            print(json.dumps({k:record.get(k) for k in ('arm','success','phase','error','total_wall_s','dispatch_to_target_s')}),flush=True)
            if not record['success']:raise RuntimeError('Sequence stopped at '+rid+': '+record.get('error','unknown failure'))
    print('ALL_FOUR_OBSERVATION_POSES_REACHED',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plans',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sequence-sha256',required=True);p.add_argument('--command-cap',type=float,required=True)
    main(p.parse_args())

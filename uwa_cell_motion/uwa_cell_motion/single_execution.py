"""Smooth single-arm execution in a measured stationary environment."""
import time
from pathlib import Path
import numpy as np
import rclpy
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from action_msgs.msg import GoalStatus

from .common import joint_names,dump


def corridor_error(measured,segment_start,delta,lengths_squared):
    u=np.clip(np.sum((measured-segment_start)*delta,axis=1)/lengths_squared,0.,1.)
    return float(np.min(np.max(abs(measured-(segment_start+u[:,None]*delta)),axis=1)))


def follow(problem,client,plan,result):
    rid=plan['request']['selected'][0];cfg=problem.cfg
    names=joint_names(rid)
    stationary=[j for n in problem.names.values() for j in n if j not in names]
    client.health()
    if any(abs(client.velocities[j])>.003 for j in stationary):return False
    baseline=dict(client.positions)
    request=problem.normalize(dict(start=baseline,goals={rid:plan['request']['goals'][rid]}))
    # Preserve all original geometric waypoints, with a checked tiny initial
    # correction from the measured state rather than a discontinuous t=0 jump.
    waypoints=[[baseline[j] for j in names]]+plan['trajectory']['waypoints']
    trajectory=problem.time_parameterize(request,waypoints)
    client.health()
    if any(abs(client.positions[j]-baseline[j])>.0005 for n in problem.names.values() for j in n):return False
    client.activate([rid])
    action=client.actions[rid]
    if not action.wait_for_server(timeout_sec=3.):raise RuntimeError(rid+': trajectory action unavailable')
    goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=names
    for value in trajectory['points']:
        point=JointTrajectoryPoint();point.positions=value['positions'];point.velocities=value['velocities'];point.accelerations=value['accelerations']
        ns=int(round(value['time']*1e9));point.time_from_start.sec=ns//10**9;point.time_from_start.nanosec=ns%10**9
        goal.trajectory.points.append(point)
    client.health()
    if any(abs(client.positions[j]-baseline[j])>.0005 for n in problem.names.values() for j in n):return False
    stage=result.get('stage','EXECUTION');record=Path(result['record_path'])
    applied=record.parent/'applied-trajectories'/(record.stem+'-'+stage+'-'+rid+'.json')
    dump(applied,dict(model_signature=problem.signature,request=request,trajectory=trajectory))
    result.setdefault('applied_trajectory_files',[]).append(str(applied))
    client.health()
    start=client.get_clock().now().nanoseconds+200_000_000
    goal.trajectory.header.stamp.sec=start//10**9;goal.trajectory.header.stamp.nanosec=start%10**9
    client.pending={rid:action.send_goal_async(goal)};client.wait(client.pending[rid].done,3.,health=True)
    handle=client.pending[rid].result();client.handles={rid:handle}
    if not handle.accepted:raise RuntimeError(rid+': trajectory rejected')
    completed=handle.get_result_async();points=trajectory['points']
    times=np.asarray([p['time'] for p in points]);positions=np.asarray([p['positions'] for p in points])
    vertices=np.asarray(trajectory['waypoints']);segment_start=vertices[:-1];delta=vertices[1:]-vertices[:-1]
    lengths_squared=np.maximum(np.sum(delta*delta,axis=1),1e-20)
    tolerance=max(cfg['goal_tolerance_rad'],.001)
    result.setdefault('execution_modes',[]).append(dict(stage=result.get('stage'),mode='smooth_single_arm',arm=rid))
    result['phase_count']+=1;result['stopped_arms']=[]
    deadline=time.monotonic()+trajectory['duration_s']*5+8.;last_mesh_check=-float('inf');maximum=0.;nominal_time_error=0.
    while True:
        client.spin_once(timeout_sec=.005);client.health()
        blocked=set(client.guard['blocked_arms'])|set(client.supervisor['blocked_arms'])
        if rid in blocked:
            handle.cancel_goal_async();result['guard_stops']+=1;result['stopped_arms']=[rid]
            result['error']=rid+': collision interlock latched';return True
        if client.live_signature!=problem.signature:raise RuntimeError('Running collision model changed')
        if any(abs(client.positions[j]-baseline[j])>.001 or abs(client.velocities[j])>.003 for j in stationary):
            raise RuntimeError('Stationary obstacle/tool joint moved; remaining single-arm path invalidated')
        elapsed=client.stamp-start/1e9
        expected=np.asarray([np.interp(elapsed,times,positions[:,i]) for i in range(6)])
        measured=np.asarray([client.positions[j] for j in names])
        nominal_time_error=max(nominal_time_error,float(np.max(abs(measured-expected))))
        # A single arm among stationary obstacles may lag in time safely. Its
        # measured geometric path, rather than a presumed common start time,
        # must remain inside the checked joint-space corridor.
        error=corridor_error(measured,segment_start,delta,lengths_squared)
        maximum=max(maximum,error)
        if error>tolerance:raise RuntimeError(f'{rid}: measured path tracking error {error:.6f}rad exceeds {tolerance:.6f}rad')
        now=time.monotonic()
        if client.stamp-last_mesh_check>=.05:
            if not problem.collision.check(client.positions)[0]:raise RuntimeError('Measured full-cell collision/limit check failed')
            last_mesh_check=client.stamp
        if completed.done():
            response=completed.result()
            if response.status!=GoalStatus.STATUS_SUCCEEDED or response.result.error_code!=FollowJointTrajectory.Result.SUCCESSFUL:
                raise RuntimeError(rid+': trajectory cancelled, preempted or failed: '+response.result.error_string)
            if max(abs(client.positions[j]-request['goals'][rid][i]) for i,j in enumerate(names))<=cfg['goal_tolerance_rad']:
                result.setdefault('tracking_max_rad_by_stage',{})[result.get('stage','EXECUTION')]=maximum
                result.setdefault('nominal_time_error_max_rad_by_stage',{})[result.get('stage','EXECUTION')]=nominal_time_error
                return True
        if now>deadline:raise TimeoutError('Measured single-arm progress timed out')

"""Guarded execution used by the UR hardware and mock adapters."""
import json
from pathlib import Path
import time
import signal
import threading
from contextlib import contextmanager
from itertools import combinations

import numpy as np
import rclpy
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from action_msgs.msg import GoalStatus

from .common import ROBOT_IDS,joint_names,arm_velocity_limit,joint_timing_duration,BODY_RESERVE_MODEL
from .node import MotionNode


@contextmanager
def motion_context():
    """Keep ROS alive for cancellation/holds when the operator interrupts."""
    owns=not rclpy.ok();previous={}
    if owns:
        from rclpy.signals import SignalHandlerOptions
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        if threading.current_thread() is threading.main_thread():
            def interrupted(signum,frame):raise KeyboardInterrupt(f'Signal {signum}')
            for signum in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):
                previous[signum]=signal.getsignal(signum);signal.signal(signum,interrupted)
    try:yield
    finally:
        if owns:
            for signum,handler in previous.items():signal.signal(signum,handler)
            if rclpy.ok():rclpy.shutdown()


class MotionClient(MotionNode):
    def spin_once(self,timeout_sec=.01):
        if self.executor is not self.event_executor:self.event_executor.add_node(self)
        self.event_executor.spin_once(timeout_sec=timeout_sec)

    def destroy_node(self):
        self.event_executor.remove_node(self);self.event_executor.shutdown(timeout_sec=1.)
        return super().destroy_node()

    def wait(self,predicate,timeout=5.,health=False):
        deadline=time.monotonic()+timeout
        while not predicate():
            if time.monotonic()>deadline:raise TimeoutError('ROS response timed out')
            self.spin_once(timeout_sec=.01)
            if health:self.health()

    def service(self,kind,name,request):
        client=self.create_client(kind,name)
        try:
            if not client.wait_for_service(timeout_sec=3.):raise RuntimeError('Service unavailable: '+name)
            future=client.call_async(request);self.wait(future.done,5.)
            return future.result()
        finally:self.destroy_client(client)

    def phase(self,targets,cfg,blocked,stationary=None):
        arms=list(targets);q0={r:np.array([self.positions[j] for j in joint_names(r)]) for r in arms}
        peak=max(np.max(abs(targets[r]-q0[r])) for r in arms)
        if cfg.get('stopping_reserve_model')==BODY_RESERVE_MODEL:
            duration=joint_timing_duration(cfg,arms,np.concatenate([targets[r]-q0[r] for r in arms]),minimum=.2)
        else:
            velocity=min(cfg.get('command_velocity_limit_rad_s',cfg['velocity_limit_rad_s']),*(arm_velocity_limit(cfg,r) for r in arms))
            duration=max(.2,1.875*peak/velocity,np.sqrt(5.774*peak/cfg['acceleration_limit_rad_s2']))
        count=max(2,int(np.ceil(duration/.1)));self.handles={};self.pending={}
        for rid in arms:
            if not self.actions[rid].server_is_ready():raise RuntimeError(rid+': action server unavailable')
            goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=joint_names(rid)
            for u in np.linspace(0,1,count+1):
                point=JointTrajectoryPoint();delta=targets[rid]-q0[rid]
                s=10*u**3-15*u**4+6*u**5;ds=30*u**2-60*u**3+30*u**4;dds=60*u-180*u**2+120*u**3
                point.positions=(q0[rid]+s*delta).tolist();point.velocities=(ds*delta/duration).tolist();point.accelerations=(dds*delta/duration**2).tolist()
                ns=int(u*duration*1e9);point.time_from_start.sec=ns//10**9;point.time_from_start.nanosec=ns%10**9
                goal.trajectory.points.append(point)
            self.pending[rid]=self.actions[rid].send_goal_async(goal)
        deadline=time.monotonic()+duration*5+5.;results={};new_stops=set()
        while True:
            self.spin_once(timeout_sec=.005);self.health()
            check_stationary(self,stationary or {})
            current_blocked=set(self.guard['blocked_arms'])|set(self.supervisor['blocked_arms'])
            new_stops.update(current_blocked-blocked)
            for rid,future in self.pending.items():
                if rid not in self.handles and future.done():
                    handle=future.result();self.handles[rid]=handle
                    if not handle.accepted:
                        if rid in current_blocked:results[rid]=None
                        else:raise RuntimeError(rid+': goal rejected')
                    else:
                        if rid in current_blocked:handle.cancel_goal_async()
                        results[rid]=handle.get_result_async()
            finished=True
            for rid in arms:
                future=results.get(rid)
                if rid in current_blocked:
                    if rid in self.handles and self.handles[rid].accepted:self.handles[rid].cancel_goal_async()
                    continue
                if future is None or not future.done():finished=False;continue
                response=future.result()
                if response.status!=GoalStatus.STATUS_SUCCEEDED or response.result.error_code!=FollowJointTrajectory.Result.SUCCESSFUL:
                    raise RuntimeError(rid+': trajectory cancelled, preempted or failed: '+response.result.error_string)
                error=max(abs(self.positions[j]-targets[rid][i]) for i,j in enumerate(joint_names(rid)))
                if error>cfg['goal_tolerance_rad']:finished=False
            if finished and len(results)==len(arms):break
            if time.monotonic()>deadline:raise TimeoutError('Measured phase progress timed out')
        return new_stops


def check_stationary(client,baseline):
    """All joints outside the trajectory, including tool drives, stay fixed."""
    moved=[dict(joint=j,delta_rad=client.positions[j]-q,velocity_rad_s=client.velocities[j])
           for j,q in baseline.items() if abs(client.positions[j]-q)>.001 or abs(client.velocities[j])>getattr(client,'standstill_velocity',{}).get(j,.003)]
    if moved:raise RuntimeError('Stationary obstacle/tool joint moved; remaining PTP path invalidated: '+json.dumps(moved))


def settle_obstacles(client,joints):
    """Wait for a preceding controller's final settling, before owning motion."""
    client.health()
    quiet_since=None
    def quiet():
        nonlocal quiet_since
        if any(abs(client.velocities[j])>getattr(client,'standstill_velocity',{}).get(j,.003) for j in joints):quiet_since=None;return False
        if quiet_since is None:quiet_since=time.monotonic()
        return time.monotonic()-quiet_since>=.1
    try:client.wait(quiet,timeout=5.,health=True)
    except TimeoutError as error:raise RuntimeError('Stationary obstacle/tool joints did not settle before PTP start') from error


def safe_targets(problem,client,desired,active):
    """Prove all relative phase progress and stopping positions inside a phase."""
    start=dict(client.positions);world=problem.spheres.world(start);cfg=problem.cfg
    names=[j for r in active for j in joint_names(r)]
    current=np.array([start[j] for j in names]);goal=np.array([desired[j] for j in names])
    peak=np.max(abs(goal-current))
    factor=min(1.,.15/max(peak,1e-12))
    body_pairs=None
    if cfg.get('stopping_reserve_model')==BODY_RESERVE_MODEL:
        _,values=problem.spheres.pairs(start,
            {r:np.asarray([client.velocities[j] for j in n]) for r,n in problem.names.items()},
            {r:cfg['state_timeout_s'] for r in problem.names},cfg)
        body_pairs={frozenset(p['arms']):p for p in values}
    for scale in (1.,.5,.25,.125,.0625,.03125):
        q=current+(goal-current)*factor*scale;candidate=dict(start,**dict(zip(names,q)))
        displacement={}
        for rid in problem.names:
            delta=np.asarray([abs(candidate[j]-start[j])+.0005 for j in problem.names[rid]])
            v=np.asarray([abs(client.velocities[j]) for j in problem.names[rid]])
            # A stopped arm can still traverse its remaining braking envelope.
            if rid not in active:delta+=v*cfg['stop_latency_s']+v*v/(2*cfg['braking_acceleration_rad_s2'])
            displacement[rid]=float(np.max(problem.spheres.motion_radii[rid]@delta))
        safe=True;unsafe=set()
        for a,b in combinations(ROBOT_IDS,2):
            if body_pairs is not None and frozenset((a,b)) in body_pairs:
                # The selected risk pair need not be the geometrically nearest
                # pair. Its least residual clearance bounds *all* sphere pairs.
                remaining=body_pairs[frozenset((a,b))]['remaining_clearance_m']-displacement[a]-displacement[b]
                if remaining<=0 and (a in active or b in active):
                    safe=False;unsafe.update({a,b}&set(active))
                continue
            clearance=problem.spheres.nearest(world,a,b)['clearance_m']-displacement[a]-displacement[b]
            threshold=cfg['model_margin_m']
            for pair in client.guard['pairs']:
                if set(pair['arms'])=={a,b}:threshold=max(threshold,pair['threshold_m'])
            if clearance<=threshold and (a in active or b in active):
                safe=False;unsafe.update({a,b}&set(active))
        if not safe:continue
        # Self/static obstacles for each moving arm throughout the phase. Other
        # moving arms are covered by the independent interarm envelope above.
        for rid in active:
            normalized=dict(start=start,joint_names=joint_names(rid))
            a=[start[j] for j in joint_names(rid)];b=[candidate[j] for j in joint_names(rid)]
            if not problem.edge(normalized,a,b,margin=False):safe=False;unsafe.add(rid)
        if safe:return {r:np.asarray([candidate[j] for j in joint_names(r)]) for r in active},set()
    return None,unsafe


def _follow(problem,client,plan,result):
    selected=plan['request']['selected'];blocked=set(client.guard['blocked_arms'])|set(client.supervisor['blocked_arms'])
    if blocked&set(selected):raise RuntimeError('Selected arm is latched; explicit reset required')
    tools=client.hold_idle_tools()
    if tools:result.setdefault('tool_holds_started',[]).extend(tools)
    commanded=set(plan['trajectory']['joint_names'])
    fixed=[j for names in problem.names.values() for j in names if j not in commanded]
    settle_obstacles(client,fixed)
    if max(abs(client.positions[j]-plan['request']['start'][j]) for names in problem.names.values() for j in names)>.002:
        raise RuntimeError('Live start changed while obstacle joints settled; generate a fresh plan')
    stationary={j:client.positions[j] for names in problem.names.values() for j in names if j not in commanded}
    check_stationary(client,stationary)
    if len(selected)==1:
        from .single_execution import follow
        if follow(problem,client,plan,result):return
    result.setdefault('execution_modes',[]).append(dict(stage=result.get('stage'),mode='independent_progress_phases',arms=selected))
    client.activate(selected);stopped=set();names=plan['trajectory']['joint_names']
    for waypoint in plan['trajectory']['waypoints'][1:]:
        desired=dict(zip(names,waypoint));phase_limit=0
        while True:
            client.health();current_blocked=set(client.guard['blocked_arms'])|set(client.supervisor['blocked_arms'])
            check_stationary(client,stationary)
            stopped.update(current_blocked&set(selected));active=[r for r in selected if r not in stopped]
            result['stopped_arms']=sorted(stopped)
            if not active:break
            error=max(abs(client.positions[j]-desired[j]) for r in active for j in joint_names(r))
            if error<=problem.cfg['goal_tolerance_rad']:break
            targets,unsafe=safe_targets(problem,client,desired,active)
            if targets is None:
                # Preserve independent remaining arms when only some paths
                # conflict with a newly stopped/braking neighbor.
                client.stop(unsafe);stopped.update(unsafe)
                result.setdefault('rest_path_stops',[]).extend(sorted(unsafe))
                if not unsafe:raise RuntimeError('Remaining phase cannot be proved clear')
                continue
            new_stops=client.phase(targets,problem.cfg,current_blocked,stationary)
            result['guard_stops']+=len(new_stops&set(selected));result['phase_count']+=1
            phase_limit+=1
            if phase_limit>5000:raise RuntimeError('Phase progress limit reached')
    result['stopped_arms']=sorted(stopped)


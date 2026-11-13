"""Simulation execution with measured progress barriers and conservative phases.

Each short phase is independent of relative arm progress. This also covers a
partial stop. Remaining phases are checked against the measured frozen arms,
including a bound for their remaining braking displacement.
"""
import json
from pathlib import Path
import tempfile
import time
import signal
import threading
from contextlib import contextmanager
from itertools import combinations

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from controller_manager_msgs.srv import SwitchController,ListControllers
from action_msgs.msg import GoalStatus

from .common import ROBOT_IDS,PAIRS,config,all_names,joint_names,load_layout,default_layout_path,dump,simulation_only,guard_signature
from .supervisor import hold_name


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


class MotionClient(Node):
    def __init__(self,layout_path=None):
        simulation_only()
        super().__init__('ptp_execution',namespace='/uwa_cell')
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
        self.names=all_names(load_layout(layout_path or default_layout_path()))
        self.positions={};self.velocities={};self.received=-float('inf');self.stamp=-float('inf')
        self.source_advanced=-float('inf');self.clock_reversed=False
        self.guard=None;self.supervisor=None;self.guard_received=-float('inf');self.supervisor_received=-float('inf')
        self.handles={};self.pending={};self.owned=set()
        self.live_signature=None;self.minimum_clearance=float('inf')
        self.create_subscription(JointState,'/uwa_cell/joint_states',self.joints,qos_profile_sensor_data)
        self.create_subscription(String,'/uwa_cell/collision_guard/decision',self.guard_message,10)
        self.create_subscription(String,'/uwa_cell/collision_supervisor/status',self.supervisor_message,10)
        self.create_subscription(String,'/uwa_cell/robot_description',self.description_message,
            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE))
        self.actions={r:ActionClient(self,FollowJointTrajectory,'/uwa_cell/'+r+'_trajectory_controller/follow_joint_trajectory') for r in ROBOT_IDS}
        self.switch_client=self.create_client(SwitchController,'/uwa_cell/controller_manager/switch_controller')
        self.list_client=self.create_client(ListControllers,'/uwa_cell/controller_manager/list_controllers')
        self.stop_clients={r:self.create_client(Trigger,'/uwa_cell/collision_supervisor/'+r+'/stop') for r in ROBOT_IDS}

    def joints(self,msg):
        q=dict(zip(msg.name,msg.position));v=dict(zip(msg.name,msg.velocity));required={j for n in self.names.values() for j in n}
        if required<=q.keys() and required<=v.keys() and np.isfinite([q[j] for j in required]+[v[j] for j in required]).all():
            now=time.monotonic();stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
            if stamp>self.stamp:self.source_advanced=now
            elif stamp<self.stamp:self.clock_reversed=True
            self.positions=q;self.velocities=v;self.received=now;self.stamp=stamp

    def guard_message(self,msg):
        self.guard=json.loads(msg.data);self.guard_received=time.monotonic()
        if self.guard.get('pairs'):self.minimum_clearance=min(self.minimum_clearance,*(p['clearance_m'] for p in self.guard['pairs']))

    def description_message(self,msg):
        from uwa_cell_control.parallel_scan import collision_signature
        self.live_signature=collision_signature(msg.data)

    def supervisor_message(self,msg):
        self.supervisor=json.loads(msg.data);self.supervisor_received=time.monotonic()

    def wait(self,predicate,timeout=5.,health=False):
        deadline=time.monotonic()+timeout
        while not predicate():
            if time.monotonic()>deadline:raise TimeoutError('Simulation response timed out')
            rclpy.spin_once(self,timeout_sec=.01)
            if health:self.health()

    def health(self):
        # Offline model/check work can occupy this client between phases. Drain
        # queued telemetry before judging freshness; the guard itself runs in
        # a separate continuously spinning process.
        deadline=time.monotonic()+.15
        while True:
            for _ in range(20):rclpy.spin_once(self,timeout_sec=0.)
            now=time.monotonic();source=self.get_clock().now().nanoseconds/1e9
            if self.clock_reversed:raise RuntimeError('Simulation clock/state epoch changed; regenerate the plan')
            state_fresh=now-self.received<=.15 and now-self.source_advanced<=.15 and -.02<=source-self.stamp<=.15
            guard_fresh=now-self.guard_received<=.4 and now-self.supervisor_received<=.4
            if state_fresh and guard_fresh:return
            if now>=deadline:
                if not state_fresh:raise RuntimeError(f'STATE STALE: receive age={now-self.received:.3f}s, source age={source-self.stamp:.3f}s')
                raise RuntimeError('GUARD/SUPERVISOR LOST')
            # No new command is sent while the client catches up. The separate
            # geometric guard and resource watchdog continue uninterrupted.
            rclpy.spin_once(self,timeout_sec=.002)

    def connect(self,guard=True):
        self.wait(lambda:bool(self.positions) and (not guard or self.guard is not None and self.supervisor is not None
                  and self.live_signature is not None and self.get_clock().now().nanoseconds>0),timeout=12.)
        if guard:self.health()
        if guard:
            for client in (self.switch_client,self.list_client):
                if not client.wait_for_service(timeout_sec=3.):raise RuntimeError('Controller manager unavailable')

    def service(self,kind,name,request):
        client=self.create_client(kind,name)
        try:
            if not client.wait_for_service(timeout_sec=3.):raise RuntimeError('Service unavailable: '+name)
            future=client.call_async(request);self.wait(future.done,5.)
            return future.result()
        finally:self.destroy_client(client)

    def switch(self,activate,deactivate):
        if not activate and not deactivate:return
        request=SwitchController.Request();request.activate_controllers=list(activate);request.deactivate_controllers=list(deactivate)
        request.strictness=SwitchController.Request.BEST_EFFORT;request.activate_asap=True;request.timeout.sec=1
        future=self.switch_client.call_async(request);self.wait(future.done,3.)
        if not future.result().ok:raise RuntimeError('Motion controller switch rejected')

    def activate(self,arms):
        self.health()
        blocked=set(self.guard['blocked_arms'])|set(self.supervisor['blocked_arms'])
        if blocked&set(arms):raise RuntimeError('Arm interlock is latched; explicit reset required')
        future=self.list_client.call_async(ListControllers.Request());self.wait(future.done,3.)
        active={c.name for c in future.result().controller if c.state=='active'}
        self.switch([r+'_trajectory_controller' for r in arms if r+'_trajectory_controller' not in active],[])
        self.owned.update(arms)

    def stop(self,arms):
        arms=set(arms);errors=[];requests=[]
        for rid,handle in self.handles.items():
            if rid in arms and handle.accepted:
                try:handle.cancel_goal_async()
                except Exception as error:errors.append(str(error))
        for rid in arms:
            try:
                client=self.stop_clients[rid]
                if client.wait_for_service(timeout_sec=.2):requests.append((rid,client.call_async(Trigger.Request())))
                else:errors.append(rid+': stop-latch service unavailable')
            except Exception as error:errors.append(str(error))
        # Direct resource hold is also available if the supervisor process died.
        def states():
            future=self.list_client.call_async(ListControllers.Request());self.wait(future.done,1.)
            return future.result().controller
        try:
            controllers=states();active={c.name for c in controllers if c.state=='active'}
            deactivate=[c.name for c in controllers if c.state=='active' and c.name not in [hold_name(r) for r in ROBOT_IDS]
                and any(interface.split('/')[0] in self.names[r] for r in arms for interface in c.claimed_interfaces)]
            try:self.switch([hold_name(r) for r in arms if hold_name(r) not in active],deactivate)
            except Exception:pass  # the supervisor may have completed the same switch first
            held={r for r in arms if any(c.name==hold_name(r) and c.state=='active' for c in states())}
        except Exception as error:held=set();errors.append(str(error))
        acknowledged=set()
        for rid,future in requests:
            try:
                self.wait(future.done,1.)
                if future.result().success:acknowledged.add(rid)
                else:errors.append(rid+': stop latch rejected')
            except Exception as error:errors.append(str(error))
        confirmed=held==arms and acknowledged==arms
        if not confirmed:self.get_logger().error('STOP_UNCONFIRMED: '+str(errors))
        return dict(resource_holds_confirmed=held==arms,latches_confirmed=acknowledged==arms,errors=errors)

    def phase(self,targets,cfg,blocked,stationary=None):
        arms=list(targets);q0={r:np.array([self.positions[j] for j in joint_names(r)]) for r in arms}
        peak=max(np.max(abs(targets[r]-q0[r])) for r in arms)
        duration=max(.2,1.875*peak/cfg['velocity_limit_rad_s'],np.sqrt(5.774*peak/cfg['acceleration_limit_rad_s2']))
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
            rclpy.spin_once(self,timeout_sec=.005);self.health()
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
    if any(abs(client.positions[j]-q)>.001 or abs(client.velocities[j])>.003
           for j,q in baseline.items()):
        raise RuntimeError('Stationary obstacle/tool joint moved; remaining PTP path invalidated')


def settle_obstacles(client,joints):
    """Wait for a preceding controller's final settling, before owning motion."""
    client.health()
    quiet_since=None
    def quiet():
        nonlocal quiet_since
        if any(abs(client.velocities[j])>.003 for j in joints):quiet_since=None;return False
        if quiet_since is None:quiet_since=time.monotonic()
        return time.monotonic()-quiet_since>=.1
    try:client.wait(quiet,timeout=5.,health=True)
    except TimeoutError as error:raise RuntimeError('Stationary obstacle/tool joints did not settle before PTP start') from error


def drives_stationary(client):
    """Use the same independent drives as guard/hold, not passive mimic noise."""
    required=[j for names in client.names.values() for j in names]
    return bool(required and all(j in client.velocities and np.isfinite(client.velocities[j])
                                 and abs(client.velocities[j])<.003 for j in required))


def safe_targets(problem,client,desired,active):
    """Prove all relative phase progress and stopping positions inside a phase."""
    start=dict(client.positions);world=problem.spheres.world(start);cfg=problem.cfg
    names=[j for r in active for j in joint_names(r)]
    current=np.array([start[j] for j in names]);goal=np.array([desired[j] for j in names])
    peak=np.max(abs(goal-current))
    factor=min(1.,.15/max(peak,1e-12))
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


def execute(plan,output,restore_start=False):
    simulation_only()
    if not plan.get('success') or not plan.get('simulation_only'):raise ValueError('Successful simulation plan required')
    with motion_context():return _execute(plan,output,restore_start)


def _execute(plan,output,restore_start=False):
    from .planning import Problem
    client=MotionClient(plan.get('layout_path'));result=dict(success=False,guard_stops=0,phase_count=0)
    result['record_path']=str(output)
    result['stage']='CONNECT';started=time.monotonic()
    try:
        client.connect();cfg=plan['config']
        result['guard_config_signature']=client.guard.get('guard_config_signature')
        result['guard_instance']=client.guard.get('instance')
        with tempfile.TemporaryDirectory(prefix='uwa-execute-') as directory:
            problem=Problem(directory,cfg,plan.get('layout_path'))
            if problem.signature!=plan['model_signature'] or problem.spheres.geometry.assets!=plan['mesh_sha256']:
                raise ValueError('Model/meshes changed since planning')
            if client.live_signature!=problem.signature or client.guard.get('model_signature',problem.signature)!=problem.signature:
                raise ValueError('Running Gazebo/guard model differs from the checked plan')
            if any(status.get('guard_config_signature')!=guard_signature(cfg) for status in (client.guard,client.supervisor)):
                raise ValueError('Plan/guard/hold operating bounds differ')
            request=plan['request'];selected=request['selected']
            result['stage']='PREPARATION'
            if restore_start:
                # Reposition in simulation through the same planner and guard,
                # never teleport/reset the Gazebo entity to a benchmark start.
                reposition_goals={r:[request['start'][j] for j in joint_names(r)] for r in ROBOT_IDS
                    if max(abs(client.positions[j]-request['start'][j]) for j in joint_names(r))>.001}
                if reposition_goals:
                    reposition=problem.normalize(dict(start=dict(client.positions),goals=reposition_goals))
                    problem.cfg=dict(cfg,planning_budget_s=60.)  # setup is outside the10s comparison budget
                    try:preparation=problem.plan(reposition,'rrtconnect',0,normalized=True)
                    finally:problem.cfg=cfg
                    preparation_file=Path(output).parent/'preparation'/Path(output).name
                    dump(preparation_file,preparation);result['preparation_plan_file']=str(preparation_file)
                    if not preparation['success']:raise RuntimeError('Benchmark start reposition failed: '+preparation.get('error',''))
                    _follow(problem,client,preparation,result)
                    if result.get('stopped_arms'):raise RuntimeError('Start preparation stopped; target execution remains unstarted')
            if max(abs(client.positions[j]-request['start'][j]) for n in problem.names.values() for j in n)>.002:
                raise ValueError('Live start differs from checked plan; generate a fresh plan')
            result['setup_wall_s']=time.monotonic()-started;motion_started=time.monotonic();sim_started=client.get_clock().now().nanoseconds/1e9
            result['stage']='EXECUTION'
            client.owned.clear()
            result['preparation_phase_count']=result['phase_count'];result['phase_count']=0;client.minimum_clearance=float('inf')
            _follow(problem,client,plan,result)
            result.update(success=not result['stopped_arms'],actual_wall_s=time.monotonic()-motion_started,
                          actual_simulation_s=client.get_clock().now().nanoseconds/1e9-sim_started,
                          minimum_observed_sphere_clearance_m=client.minimum_clearance if np.isfinite(client.minimum_clearance) else None,
                          final_positions=dict(client.positions))
            if result['success']:result['stage']='COMPLETE'
    except BaseException as error:
        result['error']=str(error)
        import traceback
        result['error_traceback']=traceback.format_exc()
        result['guard_status']=client.guard;result['supervisor_status']=client.supervisor
        if client.owned:result['stop_result']=client.stop(client.owned)
        if isinstance(error,KeyboardInterrupt):result['error']='INTERRUPTED'
    finally:
        result['total_wall_s']=time.monotonic()-started;dump(output,result)
        client.destroy_node()
    return result


def _follow(problem,client,plan,result):
    selected=plan['request']['selected'];blocked=set(client.guard['blocked_arms'])|set(client.supervisor['blocked_arms'])
    if blocked&set(selected):raise RuntimeError('Selected arm is latched; explicit reset required')
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


def snapshot():
    rclpy.init();client=MotionClient()
    try:
        client.connect(guard=False)
        return dict(schema_version=1,start=dict(client.positions),source='simulation_joint_states',source_time_s=client.stamp,goals={})
    finally:client.destroy_node();rclpy.shutdown()


def reset():
    rclpy.init();client=MotionClient()
    try:
        # A transient service can be starting while its controllers are still
        # being prepared. Require published supervision, without requiring all
        # arm states: partial resets must remain possible with one missing arm.
        client.wait(lambda:client.guard is not None and client.supervisor is not None
            and time.monotonic()-client.guard_received<.4 and time.monotonic()-client.supervisor_received<.4
            and client.supervisor.get('guard_age_s') is not None,timeout=15.)
        response=client.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request())
        if not response.success:raise RuntimeError(response.message)
        return response.message
    finally:client.destroy_node();rclpy.shutdown()


def stop_all():
    simulation_only();rclpy.init();client=MotionClient()
    try:
        client.connect(guard=False)
        for rid in ROBOT_IDS:
            answer=client.service(Trigger,'/uwa_cell/collision_supervisor/'+rid+'/stop',Trigger.Request())
            if not answer.success:raise RuntimeError(answer.message)
        client.wait(lambda:client.supervisor is not None and set(client.supervisor['held_arms'])==set(ROBOT_IDS),5.)
        since=None;end=time.monotonic()+5.
        while time.monotonic()<end:
            rclpy.spin_once(client,timeout_sec=.02)
            quiet=(time.monotonic()-client.received<.15 and time.monotonic()-client.source_advanced<.15
                   and client.get_clock().now().nanoseconds>0 and
                   -.02<=client.get_clock().now().nanoseconds/1e9-client.stamp<=.15 and
                   drives_stationary(client))
            if quiet:
                if since is None:since=time.monotonic()
                if time.monotonic()-since>=.3:return 'STOPPED: four resource holds active; measured drive standstill confirmed'
            else:since=None
        raise RuntimeError('STOP_UNCONFIRMED: hold resources requested, fresh standstill not confirmed')
    finally:client.destroy_node();rclpy.shutdown()

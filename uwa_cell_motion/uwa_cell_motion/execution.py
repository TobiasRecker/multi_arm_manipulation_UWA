"""Simulation execution with measured progress barriers and conservative phases.

Each short phase is independent of relative arm progress. This also covers a
partial stop. Remaining phases are checked against the measured frozen arms,
including a bound for their remaining braking displacement.
"""
import json
from pathlib import Path
import tempfile
import time
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

from .common import ROBOT_IDS,PAIRS,config,all_names,joint_names,load_layout,default_layout_path,dump,simulation_only
from .supervisor import hold_name


class MotionClient(Node):
    def __init__(self,layout_path=None):
        super().__init__('ptp_execution',namespace='/uwa_cell')
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
        self.names=all_names(load_layout(layout_path or default_layout_path()))
        self.positions={};self.velocities={};self.received=-float('inf');self.stamp=-float('inf')
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

    def joints(self,msg):
        q=dict(zip(msg.name,msg.position));v=dict(zip(msg.name,msg.velocity));required={j for n in self.names.values() for j in n}
        if required<=q.keys() and required<=v.keys() and np.isfinite([q[j] for j in required]+[v[j] for j in required]).all():
            self.positions=q;self.velocities=v;self.received=time.monotonic();self.stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9

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
        for _ in range(20):rclpy.spin_once(self,timeout_sec=0.)
        now=time.monotonic();source=self.get_clock().now().nanoseconds/1e9
        if now-self.received>.15 or not -.02<=source-self.stamp<=.15:raise RuntimeError('STATE STALE')
        if now-self.guard_received>.4 or now-self.supervisor_received>.4:raise RuntimeError('GUARD/SUPERVISOR LOST')

    def connect(self,guard=True):
        self.wait(lambda:bool(self.positions) and (not guard or self.guard is not None and self.supervisor is not None and self.live_signature is not None),timeout=12.)
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
        arms=set(arms)
        for rid,handle in self.handles.items():
            if rid in arms and handle.accepted:handle.cancel_goal_async()
        for rid in arms:
            client=self.create_client(Trigger,'/uwa_cell/collision_supervisor/'+rid+'/stop')
            if client.service_is_ready():client.call_async(Trigger.Request())
        # Direct resource hold is also available if the supervisor process died.
        try:self.switch([hold_name(r) for r in arms],[r+'_trajectory_controller' for r in arms])
        except Exception as error:self.get_logger().error('STOP_UNCONFIRMED: '+str(error))

    def phase(self,targets,cfg,blocked):
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
                if response.result.error_code!=FollowJointTrajectory.Result.SUCCESSFUL:raise RuntimeError(rid+': '+response.result.error_string)
                error=max(abs(self.positions[j]-targets[rid][i]) for i,j in enumerate(joint_names(rid)))
                if error>.001:finished=False
            if finished and len(results)==len(arms):break
            if time.monotonic()>deadline:raise TimeoutError('Measured phase progress timed out')
        return new_stops


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
    from .planning import Problem
    own_context=not rclpy.ok()
    if own_context:rclpy.init()
    client=MotionClient(plan.get('layout_path'));result=dict(success=False,guard_stops=0,phase_count=0)
    started=time.monotonic()
    try:
        client.connect();cfg=plan['config']
        with tempfile.TemporaryDirectory(prefix='uwa-execute-') as directory:
            problem=Problem(directory,cfg,plan.get('layout_path'))
            if problem.signature!=plan['model_signature'] or problem.spheres.geometry.assets!=plan['mesh_sha256']:
                raise ValueError('Model/meshes changed since planning')
            if client.live_signature!=problem.signature or client.guard.get('model_signature',problem.signature)!=problem.signature:
                raise ValueError('Running Gazebo/guard model differs from the checked plan')
            request=plan['request'];selected=request['selected']
            if restore_start:
                # Reposition in simulation through the same planner and guard,
                # never teleport/reset the Gazebo entity to a benchmark start.
                reposition=problem.normalize(dict(start=dict(client.positions),goals={r:[request['start'][j] for j in joint_names(r)] for r in ROBOT_IDS}))
                preparation=problem.plan(reposition,'rrtconnect',0,normalized=True)
                if not preparation['success']:raise RuntimeError('Benchmark start reposition failed: '+preparation.get('error',''))
                _follow(problem,client,preparation,result)
            if max(abs(client.positions[j]-request['start'][j]) for n in problem.names.values() for j in n)>.002:
                raise ValueError('Live start differs from checked plan; generate a fresh plan')
            result['setup_wall_s']=time.monotonic()-started;motion_started=time.monotonic();sim_started=client.get_clock().now().nanoseconds/1e9
            result['preparation_phase_count']=result['phase_count'];result['phase_count']=0;client.minimum_clearance=float('inf')
            _follow(problem,client,plan,result)
            result.update(success=not result['stopped_arms'],actual_wall_s=time.monotonic()-motion_started,
                          actual_simulation_s=client.get_clock().now().nanoseconds/1e9-sim_started,
                          minimum_observed_sphere_clearance_m=client.minimum_clearance if np.isfinite(client.minimum_clearance) else None,
                          final_positions=dict(client.positions))
    except BaseException as error:
        result['error']=str(error)
        import traceback
        result['error_traceback']=traceback.format_exc()
        result['guard_status']=client.guard;result['supervisor_status']=client.supervisor
        if client.owned:client.stop(client.owned)
        if isinstance(error,KeyboardInterrupt):result['error']='INTERRUPTED'
    finally:
        result['total_wall_s']=time.monotonic()-started;dump(output,result)
        client.destroy_node()
        if own_context:rclpy.shutdown()
    return result


def _follow(problem,client,plan,result):
    selected=plan['request']['selected'];blocked=set(client.guard['blocked_arms'])|set(client.supervisor['blocked_arms'])
    if blocked&set(selected):raise RuntimeError('Selected arm is latched; explicit reset required')
    client.activate(selected);stopped=set();names=plan['trajectory']['joint_names']
    for waypoint in plan['trajectory']['waypoints'][1:]:
        desired=dict(zip(names,waypoint));phase_limit=0
        while True:
            client.health();current_blocked=set(client.guard['blocked_arms'])|set(client.supervisor['blocked_arms'])
            stopped.update(current_blocked&set(selected));active=[r for r in selected if r not in stopped]
            result['stopped_arms']=sorted(stopped)
            if not active:break
            error=max(abs(client.positions[j]-desired[j]) for r in active for j in joint_names(r))
            if error<=.001:break
            targets,unsafe=safe_targets(problem,client,desired,active)
            if targets is None:
                # Preserve independent remaining arms when only some paths
                # conflict with a newly stopped/braking neighbor.
                client.stop(unsafe);stopped.update(unsafe)
                result.setdefault('rest_path_stops',[]).extend(sorted(unsafe))
                if not unsafe:raise RuntimeError('Remaining phase cannot be proved clear')
                continue
            new_stops=client.phase(targets,problem.cfg,current_blocked)
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
        response=client.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request())
        if not response.success:raise RuntimeError(response.message)
        return response.message
    finally:client.destroy_node();rclpy.shutdown()

"""Execution adapter for the collision-only C++ backend.

No synthetic guard/supervisor evidence and no secondary live geometry checks.
Controller results remain ordinary execution results; data gaps only warn in
the shared protection status.  Planning still uses the checked start/model.
"""
import json
import time

import numpy as np
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers, SwitchController
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint

from .common import ROBOT_IDS, joint_names
from .execution import MotionClient
from .hardware_state import require_domain
from .node import MotionNode


ROOT = '/uwa_cell/protection'


def protection_call(operation, mode='hardware'):
    """One explicit CLI command, independent of model/manager discovery."""
    from .execution import motion_context
    require_domain(mode)
    if operation not in ('pause_all', 'resume_all', 'status', 'begin_recovery'):
        raise ValueError('Unknown protection command')
    with motion_context():
        node = MotionNode('protection_cli')
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        try:
            service = node.create_client(Trigger,ROOT+'/'+operation)
            if not service.wait_for_service(timeout_sec=3.):
                raise RuntimeError('Protection service unavailable: '+operation)
            future = service.call_async(Trigger.Request())
            deadline = time.monotonic()+5.
            while not future.done():
                if time.monotonic() >= deadline:
                    raise TimeoutError('Protection command unconfirmed; no automatic retry')
                executor.spin_once(timeout_sec=.02)
            response = future.result()
            try:
                detail = json.loads(response.message)
            except ValueError:
                detail = dict(message=response.message)
            return dict(success=response.success,detail=detail,standstill_confirmed=False)
        finally:
            executor.remove_node(node)
            executor.shutdown()
            node.destroy_node()


def build_goal(trajectory):
    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = trajectory['joint_names']
    for value in trajectory['points']:
        point = JointTrajectoryPoint()
        point.positions = value['positions']
        point.velocities = value.get('velocities', [])
        point.accelerations = value.get('accelerations', [])
        ns = round(value['time']*1e9)
        point.time_from_start.sec, point.time_from_start.nanosec = divmod(ns, 10**9)
        goal.trajectory.points.append(point)
    return goal


class PauseAwareClock:
    """Wall execution budget excluding explicit operator/collision pauses."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.last = clock()
        self.elapsed = 0.

    def tick(self, paused):
        now = self.clock()
        if not paused:
            self.elapsed += max(0., now-self.last)
        self.last = now
        return self.elapsed


class MinimalHardwareClient(MotionClient):
    protection_backend = 'minimal'

    def __init__(self, problem, mode, selected=()):
        require_domain(mode)
        MotionNode.__init__(self, 'minimal_hardware_execution', namespace='/uwa_cell')
        self.problem, self.cfg, self.mode = problem, problem.cfg, mode
        self.names, self.selected = problem.names, list(selected)
        self.positions, self.velocities, self.records = {}, {}, {}
        self.protection_status = None
        self.live_signature = None
        self.stamp = 0.
        self.pending, self.handles, self.owned = {}, {}, set()
        self.rpc_clients, self.service_timings = {}, []
        self.event_executor = SingleThreadedExecutor()
        self.event_executor.add_node(self)
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, ROOT+'/state', self.state, qos)
        self.create_subscription(String, ROOT+'/status', self.status, qos)
        name = 'joint_trajectory_controller' if mode == 'mock' else 'scaled_joint_trajectory_controller'
        self.actions = {arm: ActionClient(self, FollowJointTrajectory,
                        problem.profiles[arm]['namespace']+'/'+name+'/follow_joint_trajectory')
                        for arm in selected}

    @property
    def paused(self):
        return bool((self.protection_status or {}).get('paused', False))

    def state(self, msg):
        try:
            value = json.loads(msg.data)
            positions = value.get('positions', value.get('model_state', {}))
            if not isinstance(positions, dict) or not np.isfinite(list(positions.values())).all():
                return
            self.positions = dict(positions)
            self.velocities = dict(value.get('velocities', {}))
            self.records = value.get('records', {})
            for names in self.names.values():
                for joint in names[6:]:
                    self.positions[joint] = self.velocities[joint] = 0.
            self.live_signature = value.get('model_signature')
            self.stamp = value.get('assembled_wall_time_s', time.time())
        except (ValueError, TypeError):
            return

    def status(self, msg):
        try:
            value = json.loads(msg.data)
            if isinstance(value, dict):
                self.protection_status = value
        except (ValueError, TypeError):
            pass

    def health(self):
        # Process the shared status. No guards, state deadlines, speed checks,
        # stationary-joint tests or manager polling belong in this adapter.
        for _ in range(4):
            self.spin_once(timeout_sec=0.)

    def service(self, kind, name, request):
        started = time.monotonic()
        key = (kind, name)
        client = self.rpc_clients.get(key)
        if client is None:
            client = self.rpc_clients[key] = self.create_client(kind, name)
        self.wait(client.service_is_ready, timeout=3.)
        future = client.call_async(request)
        self.wait(future.done, timeout=5.)
        self.service_timings.append(dict(service=name, duration_s=time.monotonic()-started))
        return future.result()

    def connect(self, guard=True):
        required = {joint for names in self.names.values() for joint in names[:6]}
        self.wait(lambda:required <= self.positions.keys(), timeout=15.)
        answer = self.service(Trigger, ROOT+'/status', Trigger.Request())
        if not answer.success:
            raise RuntimeError(answer.message)
        self.status(String(data=answer.message))
        if self.live_signature != self.problem.signature:
            raise ValueError('Planning and C++ collision models differ; prepare a matching model')

    def refresh_after_validation(self):
        self.health()

    def wait_unpaused(self):
        while self.paused:
            self.spin_once(timeout_sec=.05)

    def activate(self, arms, *, recovery=False):
        if not recovery:
            self.wait_unpaused()
        if not set(arms) <= set(self.selected):
            raise ValueError('Trajectory arm was not selected')
        name = 'joint_trajectory_controller' if self.mode == 'mock' else 'scaled_joint_trajectory_controller'
        for arm in arms:
            namespace = self.problem.profiles[arm]['namespace']+'/controller_manager/'
            # A one-shot command transition, not a periodic manager/hold gate.
            controllers = self.service(ListControllers, namespace+'list_controllers',
                                       ListControllers.Request()).controller
            configured = next((c for c in controllers if c.name == name),None)
            if configured is None or configured.type != 'uwa_cell_protection/PausableJointTrajectoryController':
                raise RuntimeError(arm+': minimal pausable controller is not loaded; complete the runtime cutover')
            if not any(c.name == name and c.state == 'active' for c in controllers):
                request = SwitchController.Request()
                request.strictness = SwitchController.Request.FORCE_AUTO
                request.activate_asap = True
                request.timeout.sec = 1
                request.activate_controllers = [name]
                request.deactivate_controllers = [c.name for c in controllers
                    if c.state == 'active' and c.name != name and c.claimed_interfaces]
                if not self.service(SwitchController, namespace+'switch_controller', request).ok:
                    raise RuntimeError(arm+': controller activation rejected')
            self.owned.add(arm)

    def stop(self, arms=ROBOT_IDS):
        answer = self.service(Trigger, ROOT+'/pause_all', Trigger.Request())
        return dict(pause_requested=True, accepted=answer.success, message=answer.message,
                    standstill_confirmed=False, native_stop_requested_for=[])

    def follow_group(self, trajectories, *, duration_s, segment=None, recovery=False,
                     recovery_sha256=None):
        """Send exactly the checked paths; explicit pause never cancels them."""
        if recovery and (not isinstance(recovery_sha256,str) or len(recovery_sha256)!=64):
            raise ValueError('Checked withdrawal needs its exact reviewed digest')
        if not recovery:
            self.wait_unpaused()
        self.activate(trajectories,recovery=recovery)
        if not recovery:
            self.wait_unpaused()
        goals = {arm:build_goal(value) for arm, value in trajectories.items()}
        for arm in goals:
            self.wait(self.actions[arm].server_is_ready, timeout=3.)
        start = self.get_clock().now().nanoseconds+200_000_000
        self.pending, self.handles = {}, {}
        for arm, goal in goals.items():
            goal.trajectory.header.stamp.sec, goal.trajectory.header.stamp.nanosec = divmod(start, 10**9)
            self.pending[arm] = self.actions[arm].send_goal_async(goal)
        self.wait(lambda:all(f.done() for f in self.pending.values()), timeout=3.)
        results = {}
        for arm, future in self.pending.items():
            handle = self.handles[arm] = future.result()
            if not handle.accepted:
                raise RuntimeError(arm+': trajectory rejected')
            results[arm] = handle.get_result_async()
        if recovery:
            self.wait(lambda:all((self.protection_status or {}).get('arms',{}).get(arm,{}).get(
                'active_recovery_sha256') == recovery_sha256 and
                (self.protection_status or {}).get('arms',{}).get(arm,{}).get('action_active')
                for arm in trajectories),timeout=3.)
            response = self.service(Trigger,ROOT+'/resume_all',Trigger.Request())
            if not response.success:
                raise RuntimeError('Checked withdrawal remains paused: '+response.message)
        timer = PauseAwareClock()
        while not all(future.done() for future in results.values()):
            self.spin_once(timeout_sec=.01)
            if timer.tick(self.paused) > duration_s*5+8:
                raise TimeoutError('Trajectory execution exceeded its unpaused duration budget')
        for arm, future in results.items():
            response = future.result()
            if (response.status != GoalStatus.STATUS_SUCCEEDED or
                    response.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL):
                raise RuntimeError(arm+': '+response.result.error_string)
        if segment is not None:
            segment.update(executed=True, final_positions=dict(self.positions),
                           target_confirmed_monotonic_s=time.monotonic(),
                           completion_source='FollowJointTrajectory result; no standstill test')
        self.owned.difference_update(trajectories)

    def driver_evidence(self):
        return dict(source='single C++ RTDE source', records=self.records)


def execute(plan, output, mode):
    """Existing offline plan format, with no legacy runtime interlock path."""
    from pathlib import Path
    import tempfile
    from .common import dump
    from .execution import motion_context
    from .hardware_model import HardwareProblem

    require_domain(mode)
    if not plan.get('success') or not plan.get('hardware_plan') or plan.get('execution_mode') != mode:
        raise ValueError('Successful explicitly bound hardware/mock plan required')
    began = time.monotonic()
    result = dict(success=False, protection_backend='minimal', execution_mode=mode,
                  phase_count=0, guard_stops=0, stopped_arms=[], stage='CONNECT')
    with motion_context(), tempfile.TemporaryDirectory(prefix='uwa-minimal-execute-') as directory:
        problem = HardwareProblem(directory, plan['config'], plan['inventory'], plan.get('layout_path'))
        if problem.binding != plan['hardware_binding'] or problem.spheres.geometry.assets != plan['mesh_sha256']:
            raise ValueError('Hardware model/inventory/config changed; replan')
        request = plan['request']
        client = MinimalHardwareClient(problem, mode, request['selected'])
        try:
            client.connect()
            client.wait_unpaused()
            if any(abs(client.positions[j]-q) > .002 for j, q in request['start'].items()):
                raise ValueError('Actual start differs from the checked plan; replan')
            trajectory = problem.time_parameterize(request, plan['trajectory']['waypoints'])
            if trajectory != plan['trajectory']:
                raise ValueError('Trajectory differs from its validated timing')
            trajectories = split_trajectory(trajectory, request['selected'])
            if len(trajectories) > 1:
                from uwa_cell_tasks.reviewed_carton import prove_group
                proof, error = prove_group(problem,request['start'],trajectories,
                    plan['config'].get('command_velocity_limit_rad_s',plan['config']['velocity_limit_rad_s']))
                if error:
                    raise ValueError('Parallel path cannot be retained under independent progress: '+error)
                result['independent_progress_proof'] = proof
            result['stage'] = 'EXECUTION'
            client.follow_group(trajectories, duration_s=trajectory['duration_s'])
            result.update(success=True, stage='COMPLETE', phase_count=1,
                          final_positions=dict(client.positions))
        except KeyboardInterrupt as error:
            result['error'] = str(error)
            try:
                result['stop_result'] = client.stop()
            except Exception as stop_error:
                result['stop_error'] = str(stop_error)
        except Exception as error:
            result['error'] = str(error)
        finally:
            result.update(total_wall_s=time.monotonic()-began,
                          protection_status=client.protection_status)
            dump(Path(output), result)
            client.destroy_node()
    return result


def split_trajectory(trajectory, arms):
    """Keep the checked common timing and every original joint sample."""
    result = {}
    for arm in arms:
        names = joint_names(arm)
        indexes = [trajectory['joint_names'].index(joint) for joint in names]
        points = []
        for value in trajectory['points']:
            point = dict(time=value['time'])
            for key in ('positions', 'velocities', 'accelerations'):
                point[key] = [value[key][i] for i in indexes] if value.get(key) else []
            points.append(point)
        result[arm] = dict(joint_names=names, points=points,
                           duration_s=trajectory['duration_s'])
    return result

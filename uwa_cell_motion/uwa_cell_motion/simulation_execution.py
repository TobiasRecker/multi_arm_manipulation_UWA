"""Play checked trajectories through the regular Gazebo position controllers."""
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from uwa_cell_control.parallel_scan import collision_signature
from .common import ROBOT_IDS, all_names, dump, joint_names, load_layout, simulation_only
from .execution import motion_context
from .node import MotionNode
from uwa_cell_gazebo.trajectory import trajectory_goal


class GazeboPlayback(MotionNode):
    def __init__(self, layout_path=None):
        simulation_only()
        super().__init__('ptp_playback', namespace='/uwa_cell')
        self.names = all_names(load_layout(layout_path))
        self.positions = {}
        self.stamp = None
        self.signature = None
        self.pending = []
        self.handles = []
        self.set_parameters([Parameter('use_sim_time', value=True)])
        self.create_subscription(JointState, 'joint_states', self.joints, qos_profile_sensor_data)
        self.create_subscription(String, 'robot_description', self.description,
                                 QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.events = SingleThreadedExecutor()
        self.events.add_node(self)

    def joints(self, msg):
        positions = dict(zip(msg.name, msg.position))
        if all(j in positions for names in self.names.values() for j in names):
            self.positions = positions
            self.stamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9

    def description(self, msg):
        self.signature = collision_signature(msg.data)

    def wait(self, predicate, timeout):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() >= deadline:
                raise TimeoutError('Timed out waiting for Gazebo controller or snapshot')
            self.events.spin_once(timeout_sec=.05)

    def play(self, trajectory, arms):
        actions = [ActionClient(self, FollowJointTrajectory,
                                arm + '_trajectory_controller/follow_joint_trajectory') for arm in arms]
        try:
            for action in actions:
                if not action.wait_for_server(timeout_sec=5.):
                    raise RuntimeError('Gazebo trajectory controller unavailable')
            self.wait(lambda: self.get_clock().now().nanoseconds > 0, 5.)
            stamp = (self.get_clock().now() + Duration(seconds=1.)).to_msg()
            names = trajectory['joint_names']
            for arm, action in zip(arms, actions):
                arm_names = joint_names(arm)
                indices = [names.index(j) for j in arm_names]
                points = [dict(time=entry['time'],
                               **{key: [entry[key][i] for i in indices]
                                  for key in ('positions', 'velocities', 'accelerations')})
                          for entry in trajectory['points']]
                goal = trajectory_goal(dict(joint_names=arm_names, points=points), stamp)
                self.pending.append(action.send_goal_async(goal))
            self.wait(lambda: all(future.done() for future in self.pending), 5.)
            self.handles = [future.result() for future in self.pending if future.result().accepted]
            if len(self.handles) != len(actions):
                raise RuntimeError('Gazebo controller rejected a trajectory')
            results = [handle.get_result_async() for handle in self.handles]
            self.wait(lambda: all(future.done() for future in results), trajectory['duration_s'] * 5 + 15)
            for future in results:
                response = future.result()
                if (response.status != GoalStatus.STATUS_SUCCEEDED
                        or response.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL):
                    raise RuntimeError('Gazebo trajectory action ended: ' + response.result.error_string)
        except BaseException:
            try:
                self.wait(lambda: all(future.done() for future in self.pending), 2.)
            except TimeoutError:
                pass
            cancellations = [future.result().cancel_goal_async() for future in self.pending
                             if future.done() and future.result().accepted]
            try:
                self.wait(lambda: all(future.done() for future in cancellations), 3.)
            except TimeoutError:
                pass
            raise
        finally:
            self.pending.clear()
            self.handles.clear()
            for action in actions:
                action.destroy()

    def close(self):
        self.events.remove_node(self)
        self.events.shutdown()
        self.destroy_node()


def snapshot():
    simulation_only()
    with motion_context():
        client = GazeboPlayback()
        try:
            client.wait(lambda: bool(client.positions), 15.)
            return dict(schema_version=1, start=client.positions, source='simulation_joint_states',
                        source_time_s=client.stamp, goals={})
        finally:
            client.close()


def execute(plan, output, restore_start=False):
    simulation_only()
    if not plan.get('success') or not plan.get('simulation_only'):
        raise ValueError('Successful simulation plan required')
    with motion_context():
        return _execute(plan, output, restore_start)


def _execute(plan, output, restore_start):
    from .planning import Problem

    client = GazeboPlayback(plan.get('layout_path'))
    result = dict(success=False, stage='CONNECT', phase_count=0, record_path=str(output))
    started = time.monotonic()
    try:
        client.wait(lambda: bool(client.positions) and client.signature is not None, 15.)
        with TemporaryDirectory(prefix='uwa-playback-') as directory:
            cfg = plan['config']
            problem = Problem(directory, cfg, plan.get('layout_path'))
            if (problem.signature != plan['model_signature'] or client.signature != problem.signature
                    or problem.spheres.geometry.assets != plan['mesh_sha256']):
                raise ValueError('Gazebo model or collision meshes differ from the plan')
            request = problem.normalize(plan['request'])
            trajectory = problem.time_parameterize(request, plan['trajectory']['waypoints'])
            result['stage'] = 'PREPARATION'
            if restore_start:
                targets = {arm: [request['start'][j] for j in joint_names(arm)] for arm in ROBOT_IDS
                           if any(abs(client.positions[j] - request['start'][j]) > .001 for j in joint_names(arm))}
                if targets:
                    problem.cfg = dict(cfg, planning_budget_s=60.)
                    preparation = problem.plan(dict(start=dict(client.positions), goals=targets), 'rrtconnect')
                    preparation_file = Path(output).parent / 'preparation' / Path(output).name
                    dump(preparation_file, preparation)
                    result['preparation_plan_file'] = str(preparation_file)
                    if not preparation['success']:
                        raise RuntimeError('Start reposition failed: ' + preparation.get('error', ''))
                    client.play(preparation['trajectory'], preparation['request']['selected'])
            if any(abs(client.positions[j] - request['start'][j]) > .002 for names in problem.names.values() for j in names):
                raise ValueError('Start snapshot differs from the plan')
            result.update(stage='EXECUTION', setup_wall_s=time.monotonic() - started)
            wall_start = time.monotonic()
            sim_start = client.get_clock().now()
            applied = Path(output).parent / 'applied-trajectories' / Path(output).name
            dump(applied, dict(request=request, trajectory=trajectory, model_signature=problem.signature))
            result['applied_trajectory_files'] = [str(applied)]
            client.play(trajectory, request['selected'])
            result.update(success=True, stage='COMPLETE', phase_count=1,
                          actual_wall_s=time.monotonic() - wall_start,
                          actual_simulation_s=(client.get_clock().now() - sim_start).nanoseconds / 1e9,
                          final_positions=dict(client.positions))
    except (Exception, KeyboardInterrupt) as error:
        result['error'] = 'INTERRUPTED' if isinstance(error, KeyboardInterrupt) else str(error)
    finally:
        result['total_wall_s'] = time.monotonic() - started
        client.close()
        dump(output, result)
    return result

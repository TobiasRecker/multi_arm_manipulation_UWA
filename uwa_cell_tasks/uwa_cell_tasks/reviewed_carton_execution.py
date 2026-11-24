"""Dispatch frozen unloaded trajectories with cell-wide supervision and group holds."""

from contextlib import ExitStack
import json
import time

import numpy as np
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from std_msgs.msg import String
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint

from uwa_cell_gripper_control.api import endpoint
from uwa_cell_motion.common import ROBOT_IDS, dump, joint_names
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_motion.single_execution import corridor_error
from .hardware_carton_approach import retained_holds, unloaded_guard_ready, unloaded_open_status
from .motion_review import ReviewStore
from .reviewed_carton import START_TOLERANCE, TRACKING_TOLERANCE, speed_envelope


def _start_matches(problem, client, expected):
    for names in problem.names.values():
        if any(not np.isfinite(client.positions[j]) or abs(client.positions[j]-expected[j])>START_TOLERANCE
               for j in names):
            raise RuntimeError('Measured state outside reviewed start window; replan')


def _build_goal(trajectory):
    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = trajectory['joint_names']
    for p in trajectory['points']:
        item = JointTrajectoryPoint()
        item.positions = p['positions']
        item.velocities = p['velocities']
        item.accelerations = p['accelerations']
        ns = round(p['time']*1e9)
        item.time_from_start.sec, item.time_from_start.nanosec = divmod(ns, 10**9)
        goal.trajectory.points.append(item)
    return goal


def _entry_status(status):
    registers = status.get('registers')
    return (isinstance(registers, dict) and type(registers.get('POS')) is int
            and registers.get('ACT') == 1 and unloaded_open_status(status))


def _jaw_sample(status, received):
    # The adapter and executor run on the same host. Older adapter versions
    # timestamped only reception in this process.
    stamp = status.get('read_started_monotonic_s', received)
    if type(stamp) not in (int, float) or not 0 <= stamp <= received:
        return received, {}
    return stamp, status


def _check_jaws(client, now):
    for arm,(received,status) in client.jaws.items():
        # Native status is normally published every second by each gripper.
        # A read-only preflight reply also provides a fresh initial sample.
        if not 0 <= now-received <= 2.0 or not _entry_status(status):
            raise RuntimeError(f'{arm}: active open-jaw registers lost or stale '
                               f'(age={now-received:.3f}s, observed={status.get("observed")}, '
                               f'busy={status.get("busy")}, registers={status.get("registers")})')


class IncompleteForceWindow(RuntimeError):
    """A new set of consecutive samples may still arrive under the initial hold."""


def _fresh_force_reference(arm, observer, timeout):
    rows=observer.snapshot()[-12:]
    stamps=np.array([r['received'] for r in rows])
    if (len(rows)<10 or not np.isfinite(stamps).all() or
            not 0<=time.monotonic()-stamps[-1]<=timeout or
            np.any(np.diff(stamps)<=0) or np.any(np.diff(stamps)>timeout)):
        raise IncompleteForceWindow(arm+': insufficient fresh force baseline')
    baseline=np.array([r['force'] for r in rows])
    if baseline.shape!=(len(rows),6) or not np.isfinite(baseline).all():
        raise RuntimeError(arm+': invalid force baseline')
    return np.median(baseline,axis=0)


def _force_windows_ready(observers, timeout):
    try:
        for arm,ob in observers.items():
            _fresh_force_reference(arm,ob,timeout)
    except IncompleteForceWindow:
        return False
    return True


def _cancel_late(client):
    def cancel(future):
        try:
            goal=future.result()
            if goal is not None and goal.accepted:
                goal.cancel_goal_async()
        except Exception:
            pass  # The independent hardware resource hold also covers late acceptance.
    for arm,future in client.pending.items():
        if arm not in client.handles:
            future.add_done_callback(cancel)


def _monitor(client, group, trajectories, active, obstacles, force_refs, extra, *, geometry=True):
    blocked = set(client.guard['blocked_arms']) | set(client.supervisor['blocked_arms'])
    if active & blocked:
        raise RuntimeError('Reviewed arm group interlocked: '+', '.join(sorted(active & blocked)))
    if any(abs(client.positions[j]-group['start'][j])>TRACKING_TOLERANCE or
           abs(client.velocities[j])>.003 for j in obstacles):
        raise RuntimeError('Stationary arm moved during the reviewed group')
    for arm, (start, delta, lengths) in trajectories.items():
        q = np.array([client.positions[j] for j in joint_names(arm)])
        if corridor_error(q, start, delta, lengths)>TRACKING_TOLERANCE:
            raise RuntimeError(arm+': left the reviewed trajectory corridor')
    for arm, ref in force_refs.items():
        observer = client.observers[arm]
        with observer.lock:
            current = np.asarray(observer.rows[-1]['force'])
        if not np.isfinite(current).all() or np.linalg.norm(current[:3]-ref[:3])>10 or np.linalg.norm(current[3:]-ref[3:])>1.5:
            raise RuntimeError(arm+': unexpected wrench during open entry')
    if extra:
        _check_jaws(client,time.monotonic())
    if geometry and (not client.problem.collision.check(client.positions)[0] or (extra and not extra.check(client.positions)[0])):
        raise RuntimeError('Measured carton or full-cell collision')


def _accept_responses(client, results, segment, acceptance_deadline, common_start):
    """Record acceptance before blocking work, within the unchanged deadline."""
    for arm,future in client.pending.items():
        if arm in client.handles or not future.done():continue
        observed=time.monotonic()
        segment['goal_response_observed_monotonic_s_by_arm'][arm]=observed
        if observed>=acceptance_deadline or client.get_clock().now().nanoseconds>=common_start:
            raise TimeoutError('Missing timely group acceptance before the common trajectory start')
        handle=future.result();client.handles[arm]=handle
        if not handle.accepted:raise RuntimeError(arm+': reviewed trajectory rejected')
        segment['goal_accept_observed_monotonic_s_by_arm'][arm]=observed
        results[arm]=handle.get_result_async()


def _dispatch(client, lock, group, goals, extra, force_refs, segment):
    active = set(group['arms'])
    obstacles = [j for r,names in client.problem.names.items() for j in names
                 if r not in active or j not in joint_names(r)]
    corridors = {}
    for arm, trajectory in group['trajectories'].items():
        vertices = np.array([p['positions'] for p in trajectory['points']])
        delta = np.diff(vertices, axis=0)
        corridors[arm] = (vertices[:-1], delta, np.maximum((delta*delta).sum(axis=1), 1e-20))
    lock.check()
    client.health()
    _start_matches(client.problem, client, group['start'])
    if any(not client.actions[a].server_is_ready() for a in active):
        raise RuntimeError('A reviewed arm trajectory server is unavailable')
    # Keep half of the existing 200-ms controller lead for cancellation if
    # any peer fails to accept. Both clocks are checked before admission.
    common_start = client.get_clock().now().nanoseconds+200_000_000
    acceptance_deadline = time.monotonic()+.1
    client.pending, client.handles = {}, {}
    results = {}
    segment['common_start_ros_ns']=common_start
    segment['acceptance_deadline_monotonic_s']=acceptance_deadline
    segment['goal_response_observed_monotonic_s_by_arm']={}
    segment['goal_send_monotonic_s_by_arm']={}
    segment['goal_accept_observed_monotonic_s_by_arm']={}
    for arm in group['arms']:
        lock.check()
        stamp = goals[arm].trajectory.header.stamp
        stamp.sec, stamp.nanosec = divmod(common_start, 10**9)
        sent=time.monotonic()
        segment['goal_send_monotonic_s_by_arm'][arm]=sent
        if not client.pending:
            segment['send_monotonic_s']=sent
            segment['pre_dispatch_s']=sent-segment['group_started_monotonic_s']
        client.pending[arm] = client.actions[arm].send_goal_async(goals[arm])
    deadline = time.monotonic()+group['duration_s']*5+8
    last_stamp = None
    while time.monotonic()<deadline:
        client.spin_once(timeout_sec=.001)
        _accept_responses(client,results,segment,acceptance_deadline,common_start)
        client.health()
        lock.check()
        # health() also services ready responses. Consume them before any FCL
        # work, while the controller is still waiting for its common start.
        _accept_responses(client,results,segment,acceptance_deadline,common_start)
        if len(client.handles)<len(active):
            if time.monotonic()>=acceptance_deadline or client.get_clock().now().nanoseconds>=common_start:
                raise TimeoutError('Missing timely group acceptance before the common trajectory start')
            _start_matches(client.problem,client,group['start'])
            _monitor(client,group,corridors,active,obstacles,force_refs,extra,geometry=False)
            continue
        if client.stamp != last_stamp:
            _monitor(client, group, corridors, active, obstacles, force_refs, extra)
            last_stamp = client.stamp
        if len(results)!=len(active) or not all(r.done() for r in results.values()):
            continue
        for arm, result in results.items():
            value = result.result()
            if value.status!=GoalStatus.STATUS_SUCCEEDED or value.result.error_code!=FollowJointTrajectory.Result.SUCCESSFUL:
                raise RuntimeError(arm+': reviewed trajectory failed: '+value.result.error_string)
        if all(max(abs(client.positions[j]-q) for j,q in zip(joint_names(a),t['points'][-1]['positions']))
               <=client.cfg['goal_tolerance_rad'] for a,t in group['trajectories'].items()):
            reached=time.monotonic()
            segment['target_confirmed_monotonic_s']=reached
            segment['dispatch_to_target_s']=reached-segment['send_monotonic_s']
            return
    raise TimeoutError('Reviewed trajectory group timed out')


def run_bundle(problem, bundle, args, output, report, *, client_type, observer_type,
               read_gripper, start_programs, end_phase, extra_collision=None):
    from uwa_cell_motion.protection_backend import minimal_enabled
    if minimal_enabled():
        from .minimal_reviewed_execution import run_bundle as minimal_run
        return minimal_run(problem, bundle, args, output, report, end_phase=end_phase)
    from uwa_cell_motion.pilot_interlock import PilotInterlock
    require_domain('hardware')
    started = time.monotonic()
    store = ReviewStore()
    def check_review():
        store.check_active(args.review_id, args.reviewed_sha256, stage='motion')
    def save():
        dump(output/'result.json', report)
    check_review()
    groups = bundle['groups']
    all_arms = sorted({arm for g in groups for arm in g['arms']})
    joint_cap, tcp_cap = bundle['joint_limit_rad_s'], bundle['tcp_limit_m_s']
    envelope = speed_envelope(problem, all_arms, joint_cap, tcp_cap)
    prepared = []
    for group in groups:
        if set(group['arms']) != set(group['trajectories']) or not group['arms']:
            raise ValueError('Malformed reviewed arm group')
        goals = {}
        for arm, trajectory in group['trajectories'].items():
            if trajectory['joint_names']!=joint_names(arm):
                raise ValueError('Reviewed joint order changed')
            envelope.check_trajectory(arm, trajectory['points'])
            goals[arm] = _build_goal(trajectory)
        prepared.append(goals)
    report.update(review_id=args.review_id, reviewed_sha256=args.reviewed_sha256,
                  command_velocity_rad_s=joint_cap, tcp_limit_m_s=tcp_cap,
                  phase='REVIEWED_PREFLIGHT', segments=[], arm_commands=[], finger_commands=[])
    save()
    class ReviewedClient(client_type):
        check_review = None

        def health(self):
            super().health()
            if self.check_review:
                self.check_review()
    with motion_context(), ExitStack() as cleanup:
        observers = {}
        for arm in all_arms:
            ob = observer_type(problem.profiles[arm]['ip'])
            cleanup.callback(ob.close)
            observers[arm] = ob
        client = ReviewedClient(problem, all_arms, observers)
        client.check_review = check_review
        client.startup_review=(args.review_id,args.reviewed_sha256,'motion')
        cleanup.callback(client.destroy_node)
        client.jaws={}
        if extra_collision:
            def receive(arm,msg):
                try:
                    status=json.loads(msg.data)
                except (TypeError,ValueError):
                    status={}
                if not isinstance(status, dict):
                    status = {}
                now = time.monotonic()
                sample = _jaw_sample(status, now)
                previous = client.jaws.get(arm)
                if previous is not None:
                    if not _entry_status(previous[1]):
                        # A subsequent queued status must not hide an observed
                        # fault before the motion loop processes this batch.
                        return
                    if status.get('observed') is False and status.get('busy') is False and 'registers' not in status:
                        # A missed poll cannot renew the last device sample.
                        report.setdefault('missed_jaw_reads', {})[arm] = dict(
                            received_monotonic_s=now, last_observation_monotonic_s=previous[0],
                            error=status.get('error'))
                        return
                    if sample[0] < previous[0] and _entry_status(sample[1]):
                        return
                client.jaws[arm]=sample
            for arm in all_arms:
                client.create_subscription(String,endpoint(arm,'hardware')+'/status',
                                           lambda msg,a=arm:receive(a,msg),1)
        for arm in ROBOT_IDS:
            name = endpoint(arm,'hardware')+'/read'
            client.rpc_clients[(Trigger,name)] = client.create_client(Trigger,name)
        needs_hold = False
        try:
            store.begin_component(args.review_id, args.reviewed_sha256, stage='motion')
            if args.start_ros_programs:
                store.check_startup(args.review_id, 'motion')
            end=time.monotonic()+3.
            while any(not obs.snapshot() for obs in observers.values()):
                check_review()
                if any(obs.error for obs in observers.values()) or time.monotonic()>=end:
                    raise RuntimeError('Independent native arm observers unavailable')
                time.sleep(.01)
            for i, (group, goals) in enumerate(zip(groups, prepared)):
                group_start=time.monotonic()
                if i==0:
                    report['runner_setup_before_groups_s']=group_start-started
                segment = dict(arms=group['arms'], executed=False,group_started_monotonic_s=group_start)
                report['segments'].append(segment)
                arm_set = set(group['arms'])
                segment['grippers_before'] = {}
                for arm in ROBOT_IDS:
                    status=read_gripper(client,arm)
                    segment['grippers_before'][arm]=status
                    if extra_collision and arm in all_arms:
                        client.jaws[arm]=_jaw_sample(status, time.monotonic())
                for arm, status in segment['grippers_before'].items():
                    if not unloaded_open_status(status) or (extra_collision and arm in all_arms and status['registers']['ACT']!=1):
                        raise ValueError(arm+': reviewed unloaded/open state unavailable')
                if args.start_ros_programs and i==0:
                    check_review()
                    start_programs(client, output, problem, segment, save)
                client.connect()
                client.wait(lambda:unloaded_guard_ready(client.guard),3.,health=True)
                _start_matches(problem, client, group['start'])
                holds = retained_holds(client.supervisor, ROBOT_IDS)
                if holds['issues']:
                    segment['supervisor_at_hold_failure'] = client.supervisor
                    raise RuntimeError(f"Before {bundle['phase']} group {i+1}, no goal sent for this group. "
                                       + '. '.join(holds['issues']) + '. Check UWA Robot Power → Safety log.')
                if extra_collision:
                    client.wait(lambda:_force_windows_ready(observers,client.cfg['state_timeout_s']),
                                3.,health=True)
                lock = PilotInterlock(client, envelope, check_review=check_review, arms=list(group['arms']))
                # PilotInterlock advances its ownership heartbeat through each
                # executor spin, including reset RPC and stationarity waits.
                with lock.execution():
                    segment['reset_responses'] = {}
                    for arm in group['arms']:
                        lock.check()
                        needs_hold = True
                        answer = client.service(Trigger,'/uwa_cell/collision_supervisor/'+arm+'/reset',Trigger.Request())
                        segment['reset_responses'][arm] = dict(success=answer.success,message=answer.message)
                        if not answer.success:
                            raise RuntimeError(answer.message)
                        client.wait(lambda:arm not in client.guard['blocked_arms'] and arm not in client.supervisor['blocked_arms'],3.,health=True)
                    holds = retained_holds(client.supervisor,set(ROBOT_IDS)-arm_set)
                    if holds['issues']:
                        segment['supervisor_at_hold_failure'] = client.supervisor
                        raise RuntimeError('Nonparticipating arm hold lost before goal dispatch. '
                                           + '. '.join(holds['issues']))
                    _start_matches(problem, client, group['start'])
                    force_refs = {}
                    if extra_collision:
                        force_refs={arm:_fresh_force_reference(arm,ob,client.cfg['state_timeout_s'])
                                    for arm,ob in observers.items()}
                    client.activate(group['arms'])
                    report['phase']='REVIEWED_'+bundle['phase'].upper()
                    report['arm_commands'].append(dict(arms=group['arms'],bundle_sha256=args.reviewed_sha256,group=i))
                    save()
                    if extra_collision:
                        _check_jaws(client,time.monotonic())
                    _dispatch(client, lock, group, goals, extra_collision, force_refs, segment)
                    hold = client.stop(arm_set)
                    segment['hold_after'] = hold
                    if not hold['resource_holds_confirmed'] or not hold['latches_confirmed']:
                        raise RuntimeError('Reviewed arm group final holds unconfirmed')
                    client.wait(lambda:arm_set<=set(client.guard['stationary_arms']),5.,health=True)
                    lock.check()
                    held=time.monotonic()
                    segment.update(executed=True, final_positions=dict(client.positions), end_monotonic_s=held,
                                   hold_confirm_s=held-segment['target_confirmed_monotonic_s'],
                                   group_elapsed_s=held-group_start)
                    needs_hold = False
                    client.owned.difference_update(arm_set)
                    save()
            report.update(success=True,phase=end_phase)
            return 0
        except BaseException as error:
            client.check_review = None
            report.update(success=False,phase='HELD_REVIEWED_ABORTED',error=str(error))
            if needs_hold or client.owned:
                _cancel_late(client)
                report['stop_result'] = client.stop(ROBOT_IDS)
            # Persist the evidence behind a comparison stop after requesting
            # holds; recording must never delay the protective action.
            report['state_alignment']=dict(getattr(client,'alignment_diagnostics',{}))
            report['alignment_evidence']=dict(
                native_epoch_baseline=dict(getattr(client,'epochs',{})),
                native_records=dict(getattr(client,'records',{})),
                **client.driver_evidence())
            return 1
        finally:
            for arm, observer in observers.items():
                dump(output/(arm+'-native.json'),dict(error=observer.error,records=observer.snapshot()))
            report['service_timings']=client.service_timings
            report['reviewed_runner_s']=time.monotonic()-started
            save()

#!/usr/bin/env python3
"""Execute a prepared two-task physical test; GUI alone requests pause/resume.

This tool does not issue Pause, Resume, native STOP, Play, power, or gripper
commands. READY_FOR_GUI_* events are observations for the separate operator/UI
harness, not controller watchdogs. Interrupted recording does not cancel goals.
"""
import argparse
from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import threading
import time


def quiet_measurement(rows, *, after, seconds=1., span_limit=.0005):
    """Test evidence only: distinct advancing device samples over a full second."""
    usable=[row for row in rows if row['received'] >= after]
    if len(usable)<10 or usable[-1]['received']-usable[0]['received']<seconds:
        return None
    cutoff=usable[-1]['received']-seconds
    first=max((i for i,row in enumerate(usable) if row['received']<=cutoff),default=0)
    window=usable[first:]
    stamps=[row['device_stamp'] for row in window]
    gaps=[b-a for a,b in zip(stamps,stamps[1:])]
    if len(window)<10 or any(gap<=0 or gap>.2 for gap in gaps):return None
    q=[row['q'] for row in window]
    spans=[max(row[j] for row in q)-min(row[j] for row in q) for j in range(6)]
    times=[row['received'] for row in window]
    centre=sum(times)/len(times);dt=[value-centre for value in times]
    denominator=sum(value*value for value in dt)
    trends=[sum(t*row[j] for t,row in zip(dt,q))/denominator for j in range(6)]
    return dict(ready=max(spans)<=span_limit, samples=len(window),
        interval_s=times[-1]-times[0], position_span_rad=spans,
        max_position_span_rad=max(spans), position_trend_rad_s=trends,
        device_interval_max_s=max(gaps), span_limit_rad=span_limit)


class Log:
    def __init__(self, directory):
        self.path=Path(directory);self.path.mkdir(parents=True,exist_ok=False)
        self.stream=(self.path/'telemetry.jsonl').open('w')
        self.lock=threading.Lock()

    def record(self, kind, **value):
        row=dict(event=kind,received_monotonic_s=time.monotonic(),**value)
        with self.lock:self.stream.write(json.dumps(row,allow_nan=False)+'\n')
        return row

    def notify(self, kind, **value):
        row=self.record(kind,**value)
        with self.lock:self.stream.flush()
        print(json.dumps(row),flush=True)

    def close(self):
        with self.lock:self.stream.close()


def validate_plan(plan):
    arms=('left_front','left_rear','right_front','right_rear')
    if (plan.get('kind')!='minimal_four_arm_functional_test' or not plan.get('ready') or
            plan.get('command_joint_limit_rad_s')!=.1 or len(plan.get('groups',[]))!=2):
        raise ValueError('Prepared two-task four-arm functional test at 0.1 rad/s required')
    for group in plan['groups']:
        if set(group['arms'])!=set(arms) or set(group['trajectories'])!=set(arms):
            raise ValueError('Both tasks must contain all four prepared arm trajectories')
        for trajectory in group['trajectories'].values():
            last=-1.
            for point in trajectory['points']:
                if point['time']<=last:raise ValueError('Frozen trajectory times must increase')
                last=point['time']
                for field in ('positions','velocities','accelerations'):
                    values=point.get(field,[])
                    if len(values)!=6 or not all(math.isfinite(q) for q in values):
                        raise ValueError('Six finite frozen point fields required')
                if max(map(abs,point['velocities']))>.100000001:
                    raise ValueError('Frozen command speed exceeds approved 0.1 rad/s')
    return arms


def execute(args, plan, plan_sha):
    import rclpy
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    from std_msgs.msg import String, Bool
    from action_msgs.msg import GoalStatusArray
    from control_msgs.msg import JointTrajectoryControllerState
    from uwa_cell_motion.common import joint_names, dump
    from uwa_cell_motion.execution import motion_context
    from uwa_cell_motion.hardware_model import HardwareProblem
    from uwa_cell_motion.minimal_execution import MinimalHardwareClient
    from uwa_cell_motion.hardware_state import require_domain

    require_domain('hardware')
    arms=validate_plan(plan)
    log=Log(args.output)
    report=dict(success=False,kind='minimal_four_arm_physical_functional_test',
        plan_path=str(args.plan.resolve()),plan_sha256=plan_sha,
        started_utc=datetime.now(timezone.utc).isoformat(),groups=[],
        telemetry=str(log.path/'telemetry.jsonl'),
        pause_resume_source='separate operator/GUI; this helper never calls either service',
        qualification='Physical functional observation; not a certified braking bound',
        forbidden_commands_sent=[])

    class Client(MinimalHardwareClient):
        def __init__(self, problem):
            self.private={};self.programs={};self.grippers={};self.rows=defaultdict(lambda:deque(maxlen=2000))
            self.group=None;self.zero_since=None;self.phase_at_zero={};self.native_scale={}
            self.program_false=[];self.controller_recorded={}
            super().__init__(problem,'hardware',arms)
            qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,
                           reliability=ReliabilityPolicy.RELIABLE)
            for arm in arms:
                prefix=problem.profiles[arm]['namespace']
                controller=prefix+'/scaled_joint_trajectory_controller'
                self.create_subscription(String,controller+'/pause_status',
                    lambda msg,arm=arm:self.private_status(arm,msg),qos)
                self.create_subscription(GoalStatusArray,controller+'/follow_joint_trajectory/_action/status',
                    lambda msg,arm=arm:log.record('action_status',arm=arm,statuses=[dict(
                        uuid=bytes(entry.goal_info.goal_id.uuid).hex(),status=entry.status)
                        for entry in msg.status_list]),qos)
                self.create_subscription(Bool,prefix+'/io_and_status_controller/robot_program_running',
                    lambda msg,arm=arm:self.program_status(arm,msg.data),qos)
                self.create_subscription(String,prefix+'/gripper/status',
                    lambda msg,arm=arm:self.gripper_status(arm,msg),1)
                self.create_subscription(JointTrajectoryControllerState,controller+'/controller_state',
                    lambda msg,arm=arm:self.controller_status(arm,msg),1)
                report.setdefault('endpoints',{})[arm]=dict(controller=controller,
                    action=controller+'/follow_joint_trajectory',pause_status=controller+'/pause_status',
                    program_status=prefix+'/io_and_status_controller/robot_program_running',
                    gripper_status=prefix+'/gripper/status')

        def state(self,msg):
            super().state(msg)
            value=json.loads(msg.data);now=time.monotonic()
            log.record('core_state',value=value)
            for arm,record in value.get('records',{}).items():
                history=self.rows[arm];stamp=record['device_timestamp']
                if not history or stamp!=history[-1]['device_stamp']:
                    history.append(dict(received=now,device_stamp=stamp,q=record['q'],v=record['v']))

        def status(self,msg):
            super().status(msg)
            log.record('core_status',value=self.protection_status)

        def private_status(self,arm,msg):
            value=json.loads(msg.data);self.private[arm]=value
            log.record('controller_pause_status',arm=arm,value=value)

        def program_status(self,arm,value):
            self.programs[arm]=value
            if self.group is not None and not value:self.program_false.append(arm)
            log.record('robot_program_running',arm=arm,value=value)

        def gripper_status(self,arm,msg):
            try:value=json.loads(msg.data)
            except ValueError:value=dict(raw=msg.data)
            self.grippers[arm]=value;log.record('gripper_status',arm=arm,value=value)

        def controller_status(self,arm,msg):
            now=time.monotonic();self.native_scale[arm]=msg.speed_scaling_factor
            if now-self.controller_recorded.get(arm,0.)>=.05:
                self.controller_recorded[arm]=now
                log.record('controller_reference_sample',arm=arm,native_speed_scaling=msg.speed_scaling_factor,
                    reference_positions=list(msg.reference.positions),
                    actual_positions=list(msg.feedback.positions))

        def spin_once(self,timeout_sec=.01):
            super().spin_once(timeout_sec=timeout_sec)
            self.observe()

        def observe(self):
            group=self.group
            if group is None or len(self.handles)!=4:return
            if 'action_uuids' not in group:
                group['action_uuids']={arm:bytes(self.handles[arm].goal_id.uuid).hex() for arm in arms}
                log.notify('ALL_FOUR_GOALS_ACCEPTED',group=group['name'],uuids=group['action_uuids'])
            if group['index']!=0:return
            ids=group['action_uuids']
            retained=all(self.private.get(arm,{}).get('action_active') and
                self.private[arm].get('active_goal','').replace('-','')==ids[arm] for arm in arms)
            movement={arm:self.positions.get(joint_names(arm)[5],group['start'][joint_names(arm)[5]])-
                      group['start'][joint_names(arm)[5]] for arm in arms}
            if not group.get('ready_for_pause') and retained and not self.paused and all(
                    abs(value)>=.0005 for value in movement.values()):
                group['ready_for_pause']=True
                log.notify('READY_FOR_GUI_PAUSE',group=group['name'],uuids=ids,q6_delta_rad=movement)
                save()
            if self.paused:
                if not group.get('pause_observed'):
                    group['pause_observed']=True
                    group['pause_generation']=(self.protection_status or {}).get('generation')
                    group['pause_reason']=(self.protection_status or {}).get('reason')
                    log.notify('GUI_PAUSE_OBSERVED',status=self.protection_status)
                generation=group['pause_generation']
                all_zero=retained and all(self.private[arm].get('generation')==generation and
                    self.private[arm].get('paused') and self.private[arm].get('factor')==0. for arm in arms)
                if all_zero:
                    if self.zero_since is None:
                        self.zero_since=time.monotonic()
                        self.phase_at_zero={arm:self.private[arm]['phase_time_s'] for arm in arms}
                        log.notify('ALL_FOUR_CONTROLLERS_PAUSED',uuids=ids,phase=self.phase_at_zero)
                    phase_frozen=all(abs(self.private[arm]['phase_time_s']-self.phase_at_zero[arm])<1e-9
                                     for arm in arms)
                    measurements={arm:quiet_measurement(self.rows[arm],after=self.zero_since) for arm in arms}
                    if (not group.get('ready_for_resume') and phase_frozen and all(
                            value and value['ready'] for value in measurements.values())):
                        group['ready_for_resume']=True;group['retained_uuids']=True
                        group['stationary_measurement']=measurements
                        log.notify('READY_FOR_GUI_RESUME',group=group['name'],uuids=ids,
                                   measurement=measurements,phase=self.phase_at_zero)
                        save()
            elif group.get('pause_observed') and not group.get('resume_observed'):
                group['resume_observed']=True
                group['uuid_retained_on_resume']=retained
                log.notify('GUI_RESUME_OBSERVED',uuids=ids,retained=retained,status=self.protection_status)
                save()

    def save():dump(log.path/'result.json',report)

    try:
        with motion_context():
            problem=HardwareProblem(log.path/'runtime-model',plan['config'],
                args.inventory or plan['inventory'],args.layout or plan.get('layout_path'))
            if problem.signature!=plan['model_signature']:
                raise ValueError('Prepared test and active hardware model differ')
            client=Client(problem)
            try:
                client.connect()
                log.notify('TEST_CONNECTED',initial_paused=client.paused,model_signature=problem.signature)
                if client.paused:log.notify('INITIAL_GUI_RESUME_REQUIRED')
                client.wait_unpaused()
                initial={joint:client.positions[joint] for arm in arms for joint in joint_names(arm)}
                if any(abs(initial[j]-plan['start'][j])>.002 for j in initial):
                    raise ValueError('Current start differs from the prepared test; prepare again')
                until=time.monotonic()+1.2
                while time.monotonic()<until:client.spin_once(timeout_sec=.02)
                report['programs_before']=dict(client.programs)
                report['grippers_before']=dict(client.grippers)
                report['initial_positions']=initial;save()
                for index,prepared in enumerate(plan['groups']):
                    group=dict(index=index,name=prepared['name'],start=prepared['start'],completed=False)
                    report['groups'].append(group);client.group=group
                    client.handles={};client.pending={}
                    log.notify('TASK_STARTING',index=index,name=prepared['name'],duration_s=prepared['duration_s'])
                    client.follow_group(prepared['trajectories'],duration_s=prepared['duration_s'])
                    group['completed']=True
                    group['final_positions']=dict(client.positions)
                    log.notify('TASK_COMPLETE',index=index,name=prepared['name'],uuids=group.get('action_uuids'))
                    save()
                client.group=None
                until=time.monotonic()+1.
                while time.monotonic()<until:client.spin_once(timeout_sec=.02)
                report['programs_after']=dict(client.programs)
                report['program_false_events']=client.program_false
                report['grippers_after']=dict(client.grippers)
                report['native_speed_scaling_observed']=dict(client.native_scale)
                report['final_positions']=dict(client.positions)
                first=report['groups'][0]
                report['two_tasks_completed']=all(group['completed'] for group in report['groups'])
                report['new_uuids_second_task']=all(report['groups'][0].get('action_uuids',{}).get(arm)!=
                    report['groups'][1].get('action_uuids',{}).get(arm) for arm in arms)
                report['success']=bool(report['two_tasks_completed'] and first.get('ready_for_pause') and
                    first.get('ready_for_resume') and first.get('resume_observed') and
                    first.get('uuid_retained_on_resume') and first.get('pause_reason')=='OPERATOR PAUSE' and
                    report['new_uuids_second_task'])
                before,after=report['programs_before'],report['programs_after']
                report['native_program_links_unchanged']=((before==after and all(before.values()) and
                    not client.program_false) if len(before)==4 and len(after)==4 else None)
                def registers(values):
                    return {arm:value.get('registers') for arm,value in values.items()}
                b,a=registers(report['grippers_before']),registers(report['grippers_after'])
                report['gripper_registers_unchanged']=(b==a) if len(b)==4 and all(b.values()) else None
            finally:client.destroy_node()
    except BaseException as error:
        report['error']=str(error) or type(error).__name__
        report['goals_may_continue']=True
        log.notify('TEST_RECORDING_FAILED',error=report['error'],automatic_stop_sent=False)
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        log.notify('FUNCTIONAL_TEST_RESULT',success=report['success'],result=str(log.path/'result.json'))
        log.close()
    return 0 if report['success'] else 1


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--inventory',type=Path)
    parser.add_argument('--layout',type=Path)
    parser.add_argument('--expected-sha256',required=True,help='Exact root-reviewed prepared file digest')
    parser.add_argument('--execute',action='store_true',help='Explicitly authorize the two prepared motion tasks')
    args=parser.parse_args(argv)
    for name in ('plan','output','inventory','layout'):
        value=getattr(args,name)
        if value is not None:setattr(args,name,value.expanduser().resolve())
    body=args.plan.read_bytes();sha=hashlib.sha256(body).hexdigest()
    if sha!=args.expected_sha256:raise ValueError('Prepared file differs from the root-reviewed digest')
    plan=json.loads(body);validate_plan(plan)
    if not args.execute:raise ValueError('No robot commands sent: --execute is required')
    return execute(args,plan,sha)


if __name__=='__main__':raise SystemExit(main())

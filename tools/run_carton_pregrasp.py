#!/usr/bin/env python3
"""Explicit unloaded RF-then-RR approach; no entry, fingers or loaded motion.

Default: verify/model-check saved geometric evidence only. --execute plus
--reset-unloaded permits one stationary reset per arm, with all four grippers
confirmed open and all other resource holds retained across each scoped arm release.
"""
import argparse
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.spatial.transform import Rotation
from std_srvs.srv import Trigger
from std_msgs.msg import String
from controller_manager_msgs.srv import ListControllers,SwitchController,ListHardwareComponents

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'uwa_cell_tasks'))
from uwa_cell_tasks.hardware_carton_approach import checked_problem, unloaded_open_status, unloaded_guard_ready, wait_service_spinning, unloaded_program_start_ready, retained_holds
from uwa_cell_tasks.reviewed_carton import (add_review_arguments, check_review_arguments, carton_representation,check_boundaries,
    compile_groups, file_hash, preview_model, read_bundle, retime, speed_envelope, write_bundle)
from uwa_cell_motion.common import ROBOT_IDS, joint_names, dump,arm_velocity_limit
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_execution import HardwareClient
from uwa_cell_motion.single_execution import follow
from uwa_cell_motion.hardware_state import require_domain,signature,Peer
from uwa_cell_gripper_control.api import endpoint
from uwa_cell_gazebo.charuco_views import Chain
from hardware_stop_probe import Observer


class ApproachClient(HardwareClient):
    def __init__(self,problem,arm,observer):
        self.observer=observer
        arms=[arm] if isinstance(arm,str) else list(arm)
        self.observers={arms[0]:observer} if isinstance(arm,str) else observer
        super().__init__(problem,'hardware',arms)
        self.witness_peer=Peer();self.witness=None
        self.create_subscription(String,'/uwa_cell/hardware_watchdog/status',self.witness_message,1)
        # RMW entity creation/destruction can block independently of service
        # discovery. Provision persistent RPCs before collecting driver history,
        # and destroy them only with the node after its final resource hold.
        self.rpc_clients={};self.service_timings=[]
        services=[(Trigger,'/uwa_cell/hardware_watchdog/reset')]
        for selected in arms:
            services.append((Trigger,'/uwa_cell/collision_supervisor/'+selected+'/reset'))
            services.extend((kind,problem.profiles[selected]['namespace']+'/controller_manager/'+name)
                            for kind,name in [(ListHardwareComponents,'list_hardware_components'),
                                              (ListControllers,'list_controllers'),(SwitchController,'switch_controller')])
        for kind,name in services:
            self.rpc_clients[(kind,name)]=self.create_client(kind,name)
    def witness_message(self,msg):
        value=self.accept(self.witness_peer,msg)
        if value is not None:self.witness=value
    def spin_once(self,timeout_sec=.01):
        super().spin_once(timeout_sec=timeout_sec)
        for arm,observer in self.observers.items():
            with observer.lock:
                last=observer.rows[-1]['received'] if observer.rows else -float('inf')
            if observer.error or time.monotonic()-last>.2:
                raise RuntimeError(arm+': independent native trace stale/failed: '+str(observer.error))
    def service(self,kind,name,request):
        started=time.monotonic();key=(kind,name)
        if key not in self.rpc_clients:self.rpc_clients[key]=self.create_client(kind,name)
        client=self.rpc_clients[key]
        wait_service_spinning(client,self.spin_once)
        future=client.call_async(request);self.wait(future.done,5.)
        self.service_timings.append(dict(service=name,duration_s=time.monotonic()-started))
        return future.result()


@contextmanager
def approach_resources(problem, arms, client_type=ApproachClient, observer_type=Observer):
    """Build the entire arm graph before starting any programs or trajectories.

    Keep both arm clients alive across the serial transition. Reading gripper
    status uses provisioned read-only RPCs on these same nodes, without creating
    and destroying extra action clients between the two arm goals.
    """
    with ExitStack() as cleanup:
        resources={}
        for arm in arms:
            observer=observer_type(problem.profiles[arm]['ip']);cleanup.callback(observer.close)
            client=client_type(problem,arm,observer);cleanup.callback(client.destroy_node)
            for rid in ROBOT_IDS:
                name=endpoint(rid,'hardware')+'/read'
                client.rpc_clients[(Trigger,name)]=client.create_client(Trigger,name)
            resources[arm]=(observer,client)
        yield resources


def read_gripper_status(client, arm):
    response=client.service(Trigger,endpoint(arm,'hardware')+'/read',Trigger.Request())
    if not response.success:raise RuntimeError(response.message)
    return json.loads(response.message)


def reviewed_command(args, phase, problem, source, start, end, selected, make_parts, output, report,
                     binding, scene, end_phase, observer_type, extra_collision=None):
    from prepare_carton_open_entry import shell_boxes
    if args.prepare_reviewed:
        started=time.monotonic()
        envelope=speed_envelope(problem,selected,args.command_velocity,args.tcp_speed_m_s)
        from uwa_cell_motion.pilot_interlock import validate_operating_point
        validate_operating_point(problem,'hardware',envelope)
        parts={arm:[retime(part,arm,envelope) for part in trajectories]
               for arm,trajectories in make_parts().items()}
        groups,attempts=compile_groups(problem,start,parts,args.command_velocity,extra_collision)
        for group in groups:
            for arm,trajectory in group['trajectories'].items():
                envelope.check_trajectory(arm,trajectory['points'])
        check_boundaries(dict(start=start,groups=groups),start,end,selected)
        preview=preview_model(problem,output)
        carton=carton_representation(binding,scene,shell_boxes)
        write_bundle(args.prepare_reviewed,phase,problem,start,groups,attempts,source,preview,
                     carton,args.command_velocity,args.tcp_speed_m_s,REPO/'tools')
        report.update(success=True,phase='PREPARED_FOR_REVIEW',reviewed_bundle=str(args.prepare_reviewed),
                      reviewed_sha256=file_hash(args.prepare_reviewed),preparation_s=time.monotonic()-started,
                      duration_s=sum(g['duration_s'] for g in groups),coordination=[g['arms'] for g in groups],
                      coordination_attempts=attempts)
        dump(output/'result.json',report)
        return 0
    from uwa_cell_tasks.reviewed_carton_execution import run_bundle
    bundle=read_bundle(args.reviewed,args.reviewed_sha256,phase,problem,source,REPO/'tools')
    check_boundaries(bundle,start,end,selected)
    return run_bundle(problem,bundle,args,output,report,client_type=ApproachClient,observer_type=observer_type,
                      read_gripper=read_gripper_status,start_programs=start_ros_programs_held,
                      end_phase=end_phase,extra_collision=extra_collision)


def start_ros_programs_held(client, root, problem, segment, save, *, browser_play=None):
    # Startup is explicit, with all four open/unloaded and resource-held.
    # Spin telemetry while the existing dashboard CLI runs.
    client.connect(guard=False)
    client.wait(lambda:client.witness is not None,timeout=5.)
    for _ in range(20):client.spin_once(timeout_sec=.005)
    now=time.monotonic()
    if (not client.state_peer.fresh(now,problem.cfg['state_timeout_s']) or
        any(max(now-r['received'],now-r['source_stamp'])>problem.cfg['state_timeout_s'] for r in client.records.values()) or
        not client.guard_peer.fresh(now,problem.cfg['heartbeat_timeout_s']) or
        not client.supervisor_peer.fresh(now,problem.cfg['heartbeat_timeout_s']) or
        not client.witness_peer.fresh(now,problem.cfg['heartbeat_timeout_s']) or
        not unloaded_program_start_ready(client.guard,client.supervisor,client.records,client.owned)):
        raise RuntimeError('Explicit program start requires fresh all-four unloaded holds and native quiet/normal state')
    segment['program_start_eligible_under_all_holds']=True;save()
    startup=getattr(client,'startup_review',None)
    if startup:
        from uwa_cell_tasks.motion_review import ReviewStore
        store=ReviewStore()
        def authorize():
            store.check_active(*startup)
            store.check_startup(startup[0],startup[2])
        authorize()
    # The existing independent witness can latch during service startup.
    # Reset only that software witness under the proven unloaded holds; wait
    # for its already-issued native STOP calls to finish BEFORE pressing Play.
    answer=client.service(Trigger,'/uwa_cell/hardware_watchdog/reset',Trigger.Request())
    segment['startup_witness_reset']=dict(success=answer.success,message=answer.message);save()
    if not answer.success:raise RuntimeError('Startup witness reset refused; no program start')
    client.wait(lambda:client.witness_peer.fresh(time.monotonic(),problem.cfg['heartbeat_timeout_s']) and
                not client.witness.get('tripped',True) and client.witness.get('native_stop_pending')==[],timeout=3.)
    import subprocess
    from concurrent.futures import ThreadPoolExecutor
    command=[sys.executable,str(REPO/'scripts/ur_bringup.py'),'--apply','--json']
    if browser_play is not None:
        scene, arms = browser_play
        command.extend(['--play-only-for-scene', scene])
        for arm in arms:
            command.extend(['--arm', arm])
    elif startup:
        authorize()
        command.extend(['--review-id',startup[0],'--review-component',startup[1],'--review-stage',startup[2]])
    with (root/'program-start.json').open('w') as program_log, ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(subprocess.run,command,stdout=program_log,stderr=subprocess.PIPE,text=True,timeout=30.)
        client.wait(future.done,35.)
        answer=future.result()
    segment['program_start']=dict(returncode=answer.returncode,stderr=answer.stderr,report=str(root/'program-start.json'));save()
    if answer.returncode:
        try:
            result = json.loads((root/'program-start.json').read_text())
        except ValueError:
            result = {}
        details = [
            f"{arm}: {row['message']}" for arm, row in result.get('arms', {}).items() if row['code'] != 'ready'
        ]
        reason = result.get('error') or '; '.join(details) or 'see program-start.json'
        raise RuntimeError('Explicit ROS program startup failed: ' + reason)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--inventory', type=Path, default=REPO/'config/hardware_inventory.yaml')
    p.add_argument('--command-velocity', type=float, default=.1)
    p.add_argument('--arm', choices=['right_front','right_rear'], help='One unloaded phase only; default both serially')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--reset-unloaded', action='store_true')
    p.add_argument('--start-ros-programs', action='store_true', help='Explicit one-time unloaded ROS startup after geometry compilation, under all four holds; no native safety acknowledgement')
    add_review_arguments(p)
    args = p.parse_args()
    check_review_arguments(p,args)
    if not (args.prepare_reviewed or args.reviewed) and args.tcp_speed_m_s is not None:
        p.error('Configurable TCP speed requires the reviewed approach')
    if args.execute and not args.reset_unloaded: p.error('Explicit --reset-unloaded required for this unloaded commissioning sequence')
    if args.start_ros_programs and not args.execute:p.error('--start-ros-programs requires --execute')
    root = args.output.resolve(); root.mkdir(parents=True, exist_ok=False)
    model_started = time.monotonic()
    problem = checked_problem(root/'model', args.evidence, args.inventory, command_velocity=args.command_velocity)
    model_scene_build_s = time.monotonic()-model_started
    evidence = problem.pregrasp_evidence; path = evidence['path']; expected = dict(evidence['saved_start'])
    binding=json.loads(Path(evidence['inputs']['object_pose']['path']).read_text())
    anchor=Chain(problem.original_description,'world','right_front_base_link').forward({})
    if binding.get('binding_kind')=='per_arm_camera':
        from uwa_cell_tasks.hardware_registration import validate_per_arm_binding
        validate_per_arm_binding(problem.original_description,binding)
        if not np.allclose(binding['T_world_object_candidate'],evidence['world_object_candidate'],atol=1e-9,rtol=0):
            raise ValueError('Carton obstacle and per-arm camera binding differ')
    elif ('T_world_anchor_current' not in binding or
        not np.allclose(binding['T_world_anchor_current'],anchor,atol=1e-9,rtol=0) or
        not np.allclose(binding['T_world_object_candidate'],evidence['world_object_candidate'],atol=1e-9,rtol=0)):
        raise ValueError('Object pose must explicitly use the current right-front model anchor; old frozen world pose is not an execution target')
    selected=[args.arm] if args.arm else ['right_front','right_rear']
    reviewed=bool(args.prepare_reviewed or args.reviewed)
    if path['kind'] not in ('serial_direct','simultaneous_direct') and not (path['kind']in ('single_arm_via_upright','rrt_detour')and (len(selected)==1 or reviewed)):
        raise ValueError('Expected direct or explicitly checked single-arm upright pregrasp path')
    if not args.reviewed and any(not 0<args.command_velocity<=arm_velocity_limit(problem.cfg,r) for r in selected):
        raise ValueError('Command speed must not exceed a selected monitored arm cap')
    required_names=[j for r in selected for j in joint_names(r)]
    if path['joint_names']!=required_names or len(path['waypoints'][-1])!=len(required_names) or not np.isfinite(path['waypoints'][-1]).all():
        raise ValueError('Exactly the selected unloaded six-joint endpoints required')
    end=dict(zip(path['joint_names'],path['waypoints'][-1]))
    # Only a high pregrasp, not contact insertion, is permitted by this runner.
    for goal in evidence['goals'].values():
        pre = np.asarray(goal['tool0_pregrasp']); entry = np.asarray(goal['theoretical_tool0_entry'])
        if not np.allclose(pre[:3, :3], entry[:3, :3]) or not np.allclose((pre-entry)[:2, 3], 0) or pre[2, 3]-entry[2, 3] < .149:
            raise ValueError('First unloaded physical approach requires >=150mm vertical pregrasp')
    for arm in selected:
        actual=Chain(problem.original_description,'world',arm+'_tool0').forward(dict(expected,**end))
        wanted=np.asarray(evidence['goals'][arm]['tool0_pregrasp'])
        if (np.linalg.norm(actual[:3,3]-wanted[:3,3])>1e-4 or
            Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).magnitude()>1e-4):
            raise ValueError('Saved joint endpoint does not match the high pregrasp frame')
    report = dict(hardware_signature=signature(problem,'hardware'),supervision_limits={k:problem.cfg[k] for k in ('state_timeout_s','heartbeat_timeout_s','standstill_velocity_rad_s')},success=False, phase='OFFLINE_CHECK', arm_commands=[], finger_commands=[],
                  loaded_motion=False, command_velocity_rad_s=args.command_velocity,
                  model_scene_build_s=model_scene_build_s,
                  monitored_velocity_rad_s={r:arm_velocity_limit(problem.cfg,r) for r in selected}, segments=[],
                  base_guard_signature=problem.signature, supplemental_object_signature=problem.supplemental_signature)
    record = root/'result.json'
    def save():dump(record, report)
    save()
    if reviewed:
        from run_carton_open_entry import timed_primitive
        from uwa_cell_motion.carton_paths import joint_segment
        def parts():
            result={}
            for arm in selected:
                indexes=[path['joint_names'].index(j) for j in joint_names(arm)]
                vertices=np.asarray(path['waypoints'])[:,indexes]
                moves=[(a,b) for a,b in zip(vertices,vertices[1:]) if np.max(abs(a-b))>1e-12]
                if moves:
                    result[arm]=[timed_primitive(joint_segment(a,b),a,args.command_velocity,
                                                 problem.cfg['acceleration_limit_rad_s2']) for a,b in moves]
                else:
                    # A timed constant command retains the participating arm in the group.
                    point=dict(positions=vertices[0].tolist(),velocities=[0.]*6,accelerations=[0.]*6)
                    result[arm]=[dict(duration_s=.1,waypoints=vertices[[0,-1]].tolist(),
                                      points=[dict(point,time=0.),dict(point,time=.1)])]
            return result
        scene=json.loads(Path(evidence['inputs']['contact_scene']['path']).read_text())
        return reviewed_command(args,'high',problem,args.evidence/'evidence.json',expected,dict(expected,**end),selected,parts,root,
                                report,binding,scene,'AT_HIGH_PREGRASP_HELD_NO_CONTACT',Observer)
    for index, arm in enumerate(selected):
        # Derive and fully recheck serial motion even when the offline source
        # offered a simultaneous direct path. Both arms are still unloaded.
        request = problem.normalize(dict(start=expected, goals={arm:[end[j] for j in joint_names(arm)]}))
        initial = [expected[j] for j in joint_names(arm)]
        geometric_path=path['waypoints'] if path['kind']in ('single_arm_via_upright','rrt_detour')else [initial,request['target']]
        if not all(problem.edge(request,a,b)for a,b in zip(geometric_path,geometric_path[1:])):raise ValueError('Fresh full-cell path verification failed')
        trajectory=problem.time_parameterize(request,geometric_path)
        planned=root/(arm+'-planned-trajectory.json')
        dump(planned,dict(executable=False,hardware_plan=False,request=request,trajectory=trajectory,
                          supplemental_object_signature=problem.supplemental_signature))
        report['segments'].append(dict(arm=arm, request=request, geometric_path=geometric_path,
            planned_trajectory=str(planned),nominal_duration_s=trajectory['duration_s'],executed=False))
        expected.update(zip(joint_names(arm), request['target']))
    if not args.execute:
        report.update(success=True, phase='OFFLINE_CHECKED_NOT_EXECUTED'); save(); return 0
    require_domain('hardware')
    with motion_context(), approach_resources(problem,selected) as resources:
        for index, segment in enumerate(report['segments']):
            arm = segment['arm'];observer,client=resources[arm]
            try:
                end=time.monotonic()+2.
                while not observer.snapshot():
                    if observer.error or time.monotonic()>end:raise RuntimeError('Independent native observer unavailable')
                    time.sleep(.01)
                report['phase'] = 'UNLOADED_CHECK_'+arm; save()
                for r in ROBOT_IDS:
                    status=read_gripper_status(client,r)
                    segment.setdefault('grippers_before', {})[r] = status
                    if not unloaded_open_status(status):
                        raise ValueError(r+': not confirmed open/unloaded; no reset or goal sent')
                # Gripper discovery/services have their own executor. Build the
                # arm history afterwards, so those blocking checks cannot punch
                # a gap in the driver/native alignment window.
                if args.start_ros_programs and index==0:
                    start_ros_programs_held(client,root,problem,segment,save)
                client.connect()
                client.health()
                if any(abs(client.positions[j]-segment['request']['start'][j])>.0005 for n in problem.names.values() for j in n):
                    raise ValueError('Actual start changed; replan, no automatic reposition')
                # standstill_confirmed describes a *guard-latched* stop; it is
                # deliberately false in CLEAR even when all arms are quiet.
                # Reset eligibility needs fresh per-arm physical evidence.
                segment['stationary_arms_before_reset']=client.guard.get('stationary_arms',[])
                # Program reconnect may precede the guard's existing0.5s
                # physical quiet window. Wait for that unchanged criterion;
                # health remains fail-fast and no controller is activated.
                client.wait(lambda:unloaded_guard_ready(client.guard),timeout=3.,health=True)
                # Preserve all old causes in the report; reset is a separate
                # explicit operation, never failure recovery or loaded resume.
                segment['guard_before_reset'] = client.guard; segment['supervisor_before_reset'] = client.supervisor; save()
                answer = client.service(Trigger, '/uwa_cell/collision_supervisor/'+arm+'/reset', Trigger.Request())
                segment['reset_response'] = dict(success=answer.success, message=answer.message); save()
                if not answer.success: raise RuntimeError(answer.message)
                client.wait(lambda:arm not in client.guard['blocked_arms'] and arm not in client.supervisor['blocked_arms'], timeout=3., health=True)
                others = set(ROBOT_IDS)-{arm}
                client.health();segment['other_arm_holds'] = retained_holds(client.supervisor,others); save()
                if not all(segment['other_arm_holds'][key] for key in ('resource_holds_confirmed','latches_confirmed')):
                    raise RuntimeError('Other arm holds unconfirmed')
                client.health(); baseline = dict(client.positions)
                request = problem.normalize(dict(start=baseline, goals=segment['request']['goals']))
                # Revalidate the measured tiny start correction at unchanged
                # monitored reserves; timing uses the smaller command bound.
                # follow() rechecks and times the measured-start path, then
                # refreshes telemetry before activation. Do that work once.
                plan = dict(request=request, trajectory=dict(waypoints=
                    [[baseline[j] for j in joint_names(arm)]]+segment['geometric_path'][1:]))
                execution = dict(stage='UNLOADED_PREGRASP_'+arm, record_path=str(root/(arm+'-execution.json')),
                                 phase_count=0, guard_stops=0)
                report['phase'] = 'APPROACH_'+arm; save()
                report['arm_commands'].append(dict(arm=arm, goal=request['goals'][arm], requested_monotonic_s=time.monotonic())); save()
                if not follow(problem, client, plan, execution):
                    raise RuntimeError(arm+': approach was not dispatched or did not complete')
                segment['execution'] = execution
                if execution.get('stopped_arms'): raise RuntimeError(arm+': interlock stopped approach')
                segment['hold_after'] = client.stop([arm])
                if not all(segment['hold_after'][key] for key in ('resource_holds_confirmed','latches_confirmed')):
                    raise RuntimeError(arm+': final hold unconfirmed')
                client.wait(lambda:arm in client.guard.get('stationary_arms',[]), timeout=3., health=True)
                segment['standstill_confirmed_by_guard'] = True
                segment['final_positions'] = dict(client.positions)
                segment['executed'] = True; dump(root/(arm+'-execution.json'), execution); save()
            except BaseException as error:
                report['error'] = str(error); report['phase'] = 'STOPPED_'+arm
                import traceback
                report['error_traceback']=traceback.format_exc()
                if client is not None:
                    # A successful global unloaded reset can release all holds
                    # before this client owns a controller. Restore the group
                    # holds on any subsequent preflight/activation failure.
                    stops=set(ROBOT_IDS) if segment.get('reset_response',{}).get('success') else client.owned
                    if stops:report['stop_result']=client.stop(stops)
                save(); return 1
            finally:
                if observer is not None:
                    native=root/(arm+'-native.json')
                    dump(native,dict(records=observer.snapshot(),error=observer.error))
                    segment['native_trace']=str(native);save()
                if client is not None:
                    segment["service_timings"]=client.service_timings;save()
        report.update(success=True, phase='AT_HIGH_PREGRASP_HELD_NO_CONTACT'); save()
    return 0


if __name__ == '__main__':raise SystemExit(main())

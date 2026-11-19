#!/usr/bin/env python3
"""Supported static carton gripper phases over the shared ROS API.

Default read-only. prepare: activate/open only at confirmed high pregrasp.
close: both arms already inserted, held and visually checked; rawFOR0/SPE16.
No arm goals, automatic restart/opening, lift or loaded motion.
Explicit --start-ros-programs starts only before closing under all-four open holds.
"""
import argparse,hashlib,json,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import rclpy
from std_msgs.msg import String
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'uwa_cell_tasks'))
from uwa_cell_gripper_control.client import GripperClient
from uwa_cell_tasks.hardware_carton_approach import unloaded_open_status
from uwa_cell_motion.common import ROBOT_IDS,joint_names,dump
from uwa_cell_motion.hardware_state import Peer,require_domain


def held_error(values,now,expected,limits,positions,*,require_running=True):
    """Reuse current arm freshness, mode, geometry and held-state requirements."""
    if set(values)!={'guard','supervisor','state','witness'}:return 'Waiting for existing hardware state/holds'
    for name,(value,received) in values.items():
        timeout=limits['state_timeout_s'] if name=='state' else limits['heartbeat_timeout_s']
        if value.get('hardware_signature')!=expected or value.get('armed') is not True:return 'Hardware signature/mode differs'
        if not 0<=now-received<=timeout or not 0<=now-value['evaluated_monotonic_s']<=timeout:return name+': stale packet'
    g,s,state,w=[values[k][0]for k in ('guard','supervisor','state','witness')]
    if w.get('tripped') or not s.get('witness_available'):return 'Existing hardware witness unavailable/tripped'
    if g.get('faults') or not g.get('model_match') or set(g.get('stationary_arms',[]))!=set(ROBOT_IDS):return 'Arms not confirmed quiet/model-valid'
    if set(s.get('held_arms',[]))!=set(ROBOT_IDS):return 'Arms not all resource-held'
    if any(s.get('ports',{}).get(r,{}).get(k) is not True for r in ROBOT_IDS for k in ('held','manager_fresh','hardware_mode_verified','hold_config_verified')):return 'Existing controller/hold verification unavailable'
    if set(state.get('records',{}))!=set(ROBOT_IDS):return 'Native arm state incomplete'
    for arm,record in state['records'].items():
        if max(now-record['source_stamp'],now-record['received'])>limits['state_timeout_s']:return arm+': native state stale'
        if not np.isfinite(record['q']+record['v']).all():return arm+': moving/nonfinite'
        # An explicitly selected trend profile already proves stationarity
        # above from fresh guard evidence with the unchanged position span.
        trend=g.get('stationarity_evidence',{}).get(arm,{}).get('velocity_measure')=='position_trend'
        if not trend and max(abs(v)for v in record['v'])>limits['standstill_velocity_rad_s']:return arm+': moving/nonfinite'
        status=record['status']
        if arm in ('right_front','right_rear') and (status['robot_mode']!=7 or (require_running and status['runtime_state']!=2) or status['safety_mode'] not in (1,2)):return arm+': native program/safety state not ready'
        if max(abs(q-positions[j])for j,q in zip(joint_names(arm),record['q']))>.0005:return arm+': pose changed since entry/pregrasp'
    return None


def closing_contact(status):
    r=status.get('registers',{})
    return (status.get('observed') is True and status.get('busy') is False and
            all(r.get(k)==v for k,v in dict(ACT=1,STA=3,OBJ=2,FLT=0,PRE=255,FOR=0,SPE=16).items()) and
            8<r.get('POS',255)<248)


def ready_for_open_preparation(status):
    """Allow an activated, near-open boot state ONLY to command opening high.

    OBJ0 after activation is not a completed opening and must not authorize
    arm entry or closing. Those phases continue to require OBJ3/open readback.
    """
    if unloaded_open_status(status):return True
    r=status.get('registers',{})
    return (status.get('observed') is True and status.get('busy') is False and
            all(r.get(k)==v for k,v in dict(ACT=1,STA=3,OBJ=0,FLT=0,PRE=0,COU=0).items()) and
            0<=r.get('POS',256)<=8)


class HeldMonitor:
    def __init__(self,expected,limits,positions,*,require_running=True):
        self.require_running=require_running
        self.expected,self.limits,self.positions=expected,limits,positions;self.node=rclpy.create_node('supported_carton_gripper_phase');self.values={};self.peers={k:Peer()for k in ['guard','supervisor','state','witness']}
        for key,topic in [('guard','/uwa_cell/collision_guard/decision'),('supervisor','/uwa_cell/collision_supervisor/status'),('state','/uwa_cell/hardware_state'),('witness','/uwa_cell/hardware_watchdog/status')]:self.node.create_subscription(String,topic,lambda m,k=key:self.receive(m,k),1)
    def receive(self,msg,key):
        try:
            value=json.loads(msg.data);now=time.monotonic()
            if self.peers[key].receive(value,now,self.expected,True):self.values[key]=(value,now)
        except (ValueError,TypeError,KeyError):pass
    def spin(self):rclpy.spin_once(self.node,timeout_sec=.005)
    def error(self):
        # Process already queued status callbacks before evaluating their source
        # ages, as HardwareClient.health does. Never widen the age limits.
        for _ in range(20):rclpy.spin_once(self.node,timeout_sec=0.)
        return held_error(self.values,time.monotonic(),self.expected,self.limits,self.positions,require_running=self.require_running)
    def connect(self):
        end=time.monotonic()+10.
        while True:
            self.spin();error=self.error()
            if error is None:return
            if time.monotonic()>end:raise RuntimeError(error)


def freeze_group(state_path,state,monitor,contacts):
    from uwa_cell_gazebo.charuco_views import Chain
    plan=json.loads(Path(state['plan']).read_text());evidence=next(Path(p)for p in plan['inputs']if p.endswith('/evidence.json'));e=json.loads(evidence.read_text());binding=json.loads(Path(e['inputs']['object_pose']['path']).read_text());obj=np.array(binding['T_world_object_candidate']);description=(state_path.parent/'model/moveit/robot.urdf').read_text();q=monitor.values['state'][0]['model_state'];offsets={}
    for arm in contacts:
        tcp=Chain(description,'world',arm+'_robotiq_85_base_link').forward(q);tcp=tcp@np.array([[1,0,0,0],[0,1,0,0],[0,0,1,.145],[0,0,0,1]])
        offsets[arm]=(np.linalg.inv(obj)@tcp).tolist()
    return dict(members=contacts,T_world_virtual_object=obj.tolist(),T_object_tcp=offsets,reference_kind='Frozen virtual frame at held arm poses; not a post-clamp object measurement',allowed_next_action='HOLD',independent_arm_motion_allowed=False,loaded_motion_enabled=False,object_supported=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('phase',choices=['prepare','close','release']);ap.add_argument('--state',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--visual-confirmed',action='store_true',help='Agent inspected entry, or table support for explicit release; no operator approval prompt')
    ap.add_argument('--start-ros-programs',action='store_true',help='Explicit unloaded regular program startup after graph creation, before close; no native safety acknowledgement')
    args=ap.parse_args()
    if args.start_ros_programs and not (args.execute and args.phase=='close' and args.visual_confirmed):ap.error('Program startup only with explicit visually reviewed unloaded close')
    state=json.loads(args.state.read_text());wanted='AT_HIGH_PREGRASP_HELD_NO_CONTACT' if args.phase=='prepare' else 'BOTH_OPEN_AT_WALL_HELD_NO_CLOSE'
    if not state.get('success') or state.get('phase')!=wanted:raise ValueError('Confirmed '+wanted+' result required')
    if args.phase in ('close','release') and args.execute and not args.visual_confirmed:ap.error('Inspect actual entry/support before using --visual-confirmed')
    expected=state['hardware_signature'];limits=state['supervision_limits'];positions=state['segments'][-1]['final_positions'];out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);report=dict(success=False,phase=args.phase.upper(),arm_commands=[],finger_commands=[],loaded_motion=False,force_raw=0,speed_raw=16,nominal_force_note='Minimum raw setting, not measured jaw force',state=str(args.state.resolve()),state_sha256=hashlib.sha256(args.state.read_bytes()).hexdigest(),visual_confirmed=args.visual_confirmed,results={});require_domain('hardware');rclpy.init();clients={};monitor=None;startup_client=None;startup_observer=None;startup_directory=None
    def save():dump(out/'result.json',report)
    save()
    try:
        for arm in (ROBOT_IDS if args.start_ros_programs else ('right_front','right_rear')):
            g=clients[arm]=GripperClient(arm);status=g.status();report.setdefault('before',{})[arm]=status
            ready=(ready_for_open_preparation(status) if args.phase=='prepare' else closing_contact(status) if args.phase=='release' else unloaded_open_status(status))
            if not ready:raise ValueError(arm+': not open/unloaded')
            r=status['registers']
            if args.phase=='close' and arm in ('right_front','right_rear') and (r['ACT']!=1 or r['STA']!=3 or r['FOR']!=0 or r['SPE']!=16):raise ValueError(arm+': prepare active open minimal-force gripper first')
        monitor=HeldMonitor(expected,limits,positions,**({'require_running':False}if args.phase=='release'else {}))
        if args.start_ros_programs:
            import tempfile
            from uwa_cell_motion.hardware_model import HardwareProblem
            from run_carton_pregrasp import ApproachClient,start_ros_programs_held
            from hardware_stop_probe import Observer
            plan=json.loads(Path(state['plan']).read_text())
            evidence=json.loads(next(Path(p)for p in plan['inputs']if p.endswith('/evidence.json')).read_text())
            startup_directory=tempfile.TemporaryDirectory(prefix='uwa-static-close-start-')
            problem=HardwareProblem(startup_directory.name,evidence['configuration'],REPO/'config/hardware_inventory.yaml')
            from uwa_cell_motion.hardware_state import signature
            if signature(problem,'hardware')!=expected:raise ValueError('Static startup model/config differs from held entry')
            startup_observer=Observer(problem.profiles['right_front']['ip'])
            deadline=time.monotonic()+2.
            while not startup_observer.snapshot():
                if startup_observer.error or time.monotonic()>deadline:raise RuntimeError('Static startup native observer unavailable')
                time.sleep(.01)
            startup_client=ApproachClient(problem,'right_front',startup_observer)
            report['explicit_unloaded_startup']={};save()
            start_ros_programs_held(startup_client,out,problem,report['explicit_unloaded_startup'],save)
            # These extra clients are retained until final hold/contact capture.
            # No ROS entity teardown between startup and the finger goals.
        monitor.connect();report['holds_before']={k:v[0]for k,v in monitor.values.items()};save()
        if args.start_ros_programs:clients_to_close={a:clients[a]for a in ('right_front','right_rear')}
        else:clients_to_close=clients
        if not args.execute:report.update(success=True,phase='READ_ONLY_READY_NO_COMMANDS');save();return 0
        def action(arm):
            g=clients[arm];records=[]
            if args.phase=='prepare':
                if report['before'][arm]['registers']['ACT']==0:records.append(dict(operation='activate',result=g.activate()))
                records.append(dict(operation='open',result=g.open(force_raw=0,speed_raw=16)))
            elif args.phase=='release':records.append(dict(operation='open',result=g.open(force_raw=0,speed_raw=16)))
            else:records.append(dict(operation='close',result=g.close_gripper(force_raw=0,speed_raw=16)))
            return records
        # Do not retry/cancel/open after accepted goals. If health is lost, the
        # existing arm holds/watchdogs remain authoritative; retain grip targets.
        monitor.connect()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures={arm:pool.submit(action,arm)for arm in clients_to_close};report['finger_commands']=[dict(arm=a,operation=args.phase,force_raw=0,speed_raw=16)for a in clients_to_close];save()
            while not all(f.done()for f in futures.values()):
                monitor.spin();error=monitor.error()
                if error:report.setdefault('hardware_fault',error);save()
            for arm,future in futures.items():
                try:report['results'][arm]=future.result()
                except BaseException as error:report.setdefault('errors',{})[arm]=str(error)
        monitor.spin();error=monitor.error()
        if error:report.setdefault('hardware_fault',error)
        for arm,g in clients_to_close.items():
            try:report.setdefault('after',{})[arm]=g.status()
            except BaseException as error:report.setdefault('errors',{})[arm]=str(error)
        # Contact is physical state even when the subsequent arm validation
        # fails. Preserve group membership/no-independent-motion immediately;
        # never leave a clamped object looking like an unloaded failure.
        if args.phase=='close':
            contacts=[a for a,r in report.get('after',{}).items()if closing_contact(r)]
            report['confirmed_contact_members']=contacts
            report['group']=dict(members=contacts,allowed_next_action='HOLD',
                independent_arm_motion_allowed=False,loaded_motion_enabled=False,
                object_supported=True,reference_pending=True)
            if len(contacts)==2:
                monitor.error()  # Drain queued state; keep every age/hold limit.
                static_error=held_error(monitor.values,time.monotonic(),expected,limits,positions,require_running=False)
                report['static_hold_error']=static_error
                if static_error is None:
                    report['group']=freeze_group(args.state.resolve(),state,monitor,contacts)
                    report['static_contact_hold_verified']=True
            save()
        if args.phase=='release':
            report['remaining_contact_members']=[a for a,r in report.get('after',{}).items()if closing_contact(r)]
            report['both_open_observed']=len(report.get('after',{}))==2 and all(unloaded_open_status(r)for r in report['after'].values())
            save()
        monitor.connect();save()
        if args.phase in ('prepare','release'):
            report['success']=not report.get('errors') and not report.get('hardware_fault') and all(unloaded_open_status(r) and r['registers']['ACT']==1 and r['registers']['SPE']==16 and r['registers']['FOR']==0 for r in report.get('after',{}).values()) and len(report.get('after',{}))==2
            report['phase']=('SUPPORTED_RELEASED_OPEN_HELD'if args.phase=='release'else 'ACTIVE_OPEN_HELD')if report['success']else 'HELD_OPEN_UNCONFIRMED'
        else:
            contacts=[a for a,r in report.get('after',{}).items()if closing_contact(r)]
            report['confirmed_contact_members']=contacts;save();report['group']=freeze_group(args.state.resolve(),state,monitor,contacts);report['success']=len(contacts)==2 and not report.get('errors') and not report.get('hardware_fault');report['phase']='SUPPORTED_TWO_ARM_CONTACT_HELD' if report['success'] else 'HELD_CONTACT_UNCONFIRMED';report['contact_scope']='OBJ2 supports object contact, not four-pad contact/holding strength/50N jaw-limit proof; no lift'
        save();return 0 if report['success']else 1
    except BaseException as error:report.update(error=str(error),phase='HELD_NO_AUTOMATIC_RECOVERY');save();return 1
    finally:
        for g in clients.values():g.close()
        if startup_client is not None:startup_client.destroy_node()
        if startup_observer is not None:startup_observer.close()
        if startup_directory is not None:startup_directory.cleanup()
        if monitor is not None:monitor.node.destroy_node()
        rclpy.shutdown()


if __name__=='__main__':raise SystemExit(main())

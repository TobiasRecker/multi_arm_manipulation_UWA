#!/usr/bin/env python3
"""Explicit unloaded open-jaw entry, ending held; NEVER closes fingers or lifts."""
import argparse,hashlib,json,socket,struct,sys,threading,time
from pathlib import Path
import numpy as np
from std_srvs.srv import Trigger
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'uwa_cell_tasks'))
from uwa_cell_tasks.hardware_carton_approach import unloaded_open_status,unloaded_guard_ready,retained_holds
from uwa_cell_tasks.hardware_preparation import OUTPUT_FIELDS,OUTPUT_TYPES,decode_arm_output
from uwa_cell_control.capture_rtde import OutputReader
from uwa_cell_motion.common import joint_names,dump,ROBOT_IDS
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import signature
from uwa_cell_motion.carton_paths import evaluate
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.single_execution import follow
from uwa_cell_gripper_control.client import GripperClient
from hardware_stop_probe import Observer,quiet_window
from run_carton_pregrasp import ApproachClient,start_ros_programs_held
from prepare_carton_open_entry import open_model


def timed_primitive(segment,actual_start,velocity=.1,acceleration=.2):
    q0=np.array(segment['positions'][0]);correction=np.array(actual_start)-q0
    if np.max(abs(correction))>.0005:raise ValueError('Entry start changed; replan rather than reposition')
    def values(u):
        u=np.asarray(u);h=10*u**3-15*u**4+6*u**5;hp=30*u**2-60*u**3+30*u**4;hpp=60*u-180*u**2+120*u**3
        return (evaluate(segment,u)+(1-h)[...,None]*correction,
                evaluate(segment,u,1)-hp[...,None]*correction,
                evaluate(segment,u,2)-hpp[...,None]*correction)
    _,v,a=values(np.linspace(0,1,8193));duration=max(float(abs(v).max())/velocity,np.sqrt(float(abs(a).max())/acceleration))
    if duration<1e-6:raise ValueError('Zero entry primitive; omit instead of adding a wait')
    times=np.linspace(0,duration,max(2,int(np.ceil(duration/.02))+1));q,v,a=values(times/duration)
    return dict(duration_s=duration,waypoints=values(np.linspace(0,1,257))[0].tolist(),points=[dict(time=float(t),positions=x.tolist(),velocities=y.tolist(),accelerations=z.tolist())for t,x,y,z in zip(times,q,v/duration,a/duration**2)])


def timed_sequence(segments,actual_start):
    """Deliver the checked ALIGN/ENTRY primitives as one action per arm.

    Preserve each time law and its zero velocity/acceleration junction. This
    avoids recompiling/reconnecting a second follow() while already owning
    the active controller. No extra hold, reset or time dilation is inserted.
    """
    points=[];waypoints=[];duration=0.;start=actual_start
    for index,segment in enumerate(segments):
        if index and not np.allclose(start,segment['positions'][0],atol=1e-10,rtol=0):
            raise ValueError('Entry primitive junction changed')
        part=timed_primitive(segment,start)
        for point in part['points'][1 if index else 0:]:
            points.append(dict(point,time=point['time']+duration))
        waypoints.extend(part['waypoints'][1 if index else 0:])
        duration+=part['duration_s'];start=part['points'][-1]['positions']
    return dict(duration_s=duration,waypoints=waypoints,points=points)


class ForceObserver(Observer):
    def __init__(self,host):
        self.reader=OutputReader.__new__(OutputReader);self.reader.socket=socket.create_connection((host,30004),timeout=1.);self.reader.socket.settimeout(2.)
        try:
            if self.reader.request(86,struct.pack('>H',2))!=b'\x01':raise ValueError('Read-only RTDE protocol rejected')
            reply=self.reader.request(79,struct.pack('>d',20.)+OUTPUT_FIELDS.encode())
            if len(reply)<2 or reply[0]==0 or reply[1:]!=OUTPUT_TYPES:raise ValueError('Read-only force recipe rejected')
            self.recipe=reply[0]
            if self.reader.request(83)!=b'\x01':raise ValueError('Read-only RTDE stream rejected')
            self.reader.socket.settimeout(.3)
        except BaseException:self.reader.close();raise
        self.rows=[];self.error=None;self.lock=threading.Lock();self.done=threading.Event();self.worker=threading.Thread(target=self.run,daemon=True);self.worker.start()
    def run(self):
        previous=-1
        try:
            while not self.done.is_set():
                kind,payload=self.reader.receive()
                if kind!=85:continue
                r=decode_arm_output(payload,self.recipe);stamp=r['device_timestamp_s']
                if stamp<=previous:raise ValueError('Force observer clock did not advance')
                previous=stamp
                with self.lock:self.rows.append(dict(received=time.monotonic(),device_stamp=stamp,q=r['actual_q'],v=r['actual_qd'],force=r['actual_tcp_force_raw'],status={k:r[k]for k in ['robot_mode','runtime_state','safety_mode']}))
        except BaseException as e:
            if not self.done.is_set():self.error=str(e)


class EntryProblem(HardwareProblem):
    def check(self,request,q,*,margin=True):
        return super().check(request,q,margin=margin) and self.current_open.check(self.state(request,q))[0]
    def time_parameterize(self,request,path):
        arm=self.current_arm;segment=self.current_primitive;start=[request['start'][j]for j in joint_names(arm)]
        segments=segment if isinstance(segment,list) else [segment]
        if np.max(abs(np.array(request['target'])-segments[-1]['positions'][-1]))>1e-8:raise ValueError('Entry endpoint mismatch')
        trajectory=timed_sequence(segments,start)
        for q in trajectory['waypoints']:
            if not self.check(request,q):raise ValueError('Measured-start entry recheck failed')
        return trajectory


class EntryClient(ApproachClient):
    def __init__(self,problem,arm,observer):
        self.force_reference=None;self.monitor_open=False;self.last_open_check=-float('inf');super().__init__(problem,arm,observer)
    def spin_once(self,timeout_sec=.01):
        super().spin_once(timeout_sec=timeout_sec)
        if self.force_reference is not None:
            force=np.array(self.observer.snapshot()[-1]['force'])
            if np.linalg.norm(force[:3]-self.force_reference[:3])>10. or np.linalg.norm(force[3:]-self.force_reference[3:])>1.5:raise RuntimeError('Unexpected native wrench change; entry held, no closing')
        if self.monitor_open and self.positions and time.monotonic()-self.last_open_check>.05:
            self.last_open_check=time.monotonic()
            if not self.problem.current_open.check(self.positions)[0]:raise RuntimeError('Measured open-jaw/carton collision')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--inventory',type=Path,default=REPO/'config/hardware_inventory.yaml');ap.add_argument('--execute',action='store_true');ap.add_argument('--reset-unloaded',action='store_true');ap.add_argument('--start-ros-programs',action='store_true');args=ap.parse_args()
    if args.execute and not args.reset_unloaded:ap.error('Explicit --reset-unloaded required')
    plan=json.loads(args.plan.read_text());assert plan['success'] and plan['executable'] is False
    for path,digest in plan['inputs'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Entry source changed: '+path)
    evidence_path=next(Path(p)for p in plan['inputs']if p.endswith('/evidence.json'));e=json.loads(evidence_path.read_text());binding=json.loads(Path(e['inputs']['object_pose']['path']).read_text());scene=json.loads(Path(e['inputs']['contact_scene']['path']).read_text());out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);p=EntryProblem(out/'model',e['configuration'],args.inventory);assert p.signature==plan['base_signature'];models={a:open_model(p,binding,scene,a,out/('open-'+a))for a in ['right_front','right_rear']}
    report=dict(hardware_signature=signature(p,'hardware'),model_signature=p.signature,supervision_limits={k:p.cfg[k] for k in ('state_timeout_s','heartbeat_timeout_s','standstill_velocity_rad_s')},success=False,phase='OFFLINE',arm_commands=[],finger_commands=[],loaded_motion=False,command_velocity_rad_s=.1,segments=[],plan=str(args.plan.resolve()),plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),wrench_scope='Native wrench DELTA10N/1.5Nm abort; not jaw-force metrology')
    def save():dump(out/'result.json',report)
    # Recheck every complete segment before explicit program startup/activation.
    for s in plan['segments']:
        p.current_arm=s['arm'];p.current_open=models[s['arm']];p.current_primitive=s['primitive'];p.time_parameterize(s['request'],[])
    if not args.execute:report.update(success=True,phase='OFFLINE_ENTRY_RECHECKED');save();return 0
    save()
    with motion_context():
        for index,arm in enumerate(['right_front','right_rear']):
            ob=ForceObserver(p.profiles[arm]['ip']);client=None;record=dict(arm=arm);report['segments'].append(record)
            try:
                deadline=time.monotonic()+3
                while not quiet_window(ob.snapshot()[-12:]):
                    if ob.error or time.monotonic()>deadline:raise RuntimeError('No independent quiet prewindow')
                    time.sleep(.02)
                for r in ROBOT_IDS:
                    with GripperClient(r) as g:status=g.status()
                    record.setdefault('grippers_before',{})[r]=status
                    if not unloaded_open_status(status):raise ValueError(r+': not open/unloaded')
                    if r in ('right_front','right_rear') and status['registers'].get('ACT')!=1:raise ValueError(r+': activate/open at high pose before entry')
                p.current_arm=arm;p.current_open=models[arm];client=EntryClient(p,arm,ob)
                if args.start_ros_programs and index==0:start_ros_programs_held(client,out,p,record,save)
                client.connect();client.health()
                if not unloaded_guard_ready(client.guard):raise ValueError('Current clear physical stationarity required')
                baseline=dict(client.positions);expected=next(s for s in plan['segments']if s['arm']==arm)['request']['start']
                if any(abs(baseline[j]-expected[j])>.0005 for n in p.names.values()for j in n):raise ValueError('Entry live start changed')
                answer=client.service(Trigger,'/uwa_cell/collision_supervisor/'+arm+'/reset',Trigger.Request());record['reset_response']=dict(success=answer.success,message=answer.message);save()
                if not answer.success:raise RuntimeError(answer.message)
                client.wait(lambda:arm not in client.guard['blocked_arms'] and arm not in client.supervisor['blocked_arms'],3.,health=True);client.health();record['other_holds']=retained_holds(client.supervisor,set(ROBOT_IDS)-{arm});save()
                if not all(record['other_holds'][k]for k in ['resource_holds_confirmed','latches_confirmed']):raise RuntimeError('Other holds unconfirmed')
                client.force_reference=np.median([r['force']for r in ob.snapshot()[-12:]],axis=0);client.monitor_open=True
                parts=[s for s in plan['segments']if s['arm']==arm]
                p.current_primitive=[s['primitive']for s in parts]
                request=p.normalize(dict(start=dict(client.positions),goals={arm:parts[-1]['primitive']['positions'][-1]}))
                execution=dict(stage='OPEN_ALIGN_ENTRY_'+arm,record_path=str(out/(arm+'-ALIGN-ENTRY.json')),phase_count=0,guard_stops=0)
                report['phase']=execution['stage'];report['arm_commands'].append(dict(arm=arm,phases=[s['name']for s in parts],goal=request['goals'][arm]));save()
                completed=follow(p,client,dict(request=request,trajectory=dict(waypoints=[q for s in parts for q in s['primitive']['positions']])),execution)
                dump(execution['record_path'],execution)
                if not completed:raise RuntimeError('Entry phase not executed; no continuation')
                if execution.get('stopped_arms'):raise RuntimeError('Entry interlock stopped arm')
                record['hold_after']=client.stop([arm]);save()
                if not all(record['hold_after'][k]for k in ['resource_holds_confirmed','latches_confirmed']):raise RuntimeError('Entry hold unconfirmed')
                client.wait(lambda:arm in client.guard['stationary_arms'] and quiet_window(ob.snapshot()[-12:]),5.,health=True);record.update(executed=True,final_positions=dict(client.positions));save()
            except BaseException as error:
                report.update(error=str(error),phase='HELD_ENTRY_ABORTED');import traceback;report['traceback']=traceback.format_exc()
                if client is not None:
                    client.force_reference=None;client.monitor_open=False
                    report['stop_result']=client.stop(ROBOT_IDS)
                save();return 1
            finally:
                ob.close();dump(out/(arm+'-native.json'),dict(error=ob.error,records=ob.snapshot()))
                if client is not None:client.destroy_node()
        report.update(success=True,phase='BOTH_OPEN_AT_WALL_HELD_NO_CLOSE');save();return 0


if __name__=='__main__':raise SystemExit(main())

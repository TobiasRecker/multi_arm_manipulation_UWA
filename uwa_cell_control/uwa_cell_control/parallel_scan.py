"""Explicit, monitored multi-arm scan runner. No automatic Power/Brake/Play.

Only a hash-bound plan with arbitrary-progress separation for ALL selected arms
may run. An independent GUI heartbeat/STOP service remains active during photos.
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import tempfile
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np

from uwa_cell_description.configuration import ROBOT_IDS, joint_names, load_layout, default_layout_path
from .parking import digest, make_model
from .park_arm import JointObserver


def path_deviation(q, start, target):
    q, start, target = np.asarray(q), np.asarray(start), np.asarray(target)
    delta=target-start
    u=float(np.dot(q-start,delta)/np.dot(delta,delta)) if np.dot(delta,delta)>1e-15 else 0.
    nominal=start+np.clip(u,0.,1.)*delta
    return float(np.max(abs(q-nominal)))


def collision_signature(description):
    root=ET.fromstring(description)
    def value(element):
        return [element.tag,sorted(element.attrib.items()),[value(c) for c in element]]
    return digest(dict(joints=[value(j) for j in root.findall('joint')],
                       collision=[(link.get('name'),[value(c) for c in link.findall('collision')])
                                  for link in root.findall('link')]))


def load_checked(plan_path, analysis_path, tracking=.005):
    from .scan_separation import validated_steps
    plan_path,analysis_path=Path(plan_path),Path(analysis_path)
    plan=json.loads(plan_path.read_text());analysis=json.loads(analysis_path.read_text())
    if hashlib.sha256(plan_path.read_bytes()).hexdigest()!=analysis['source_plan_sha256']:
        raise ValueError('Separation proof does not belong to this exact plan')
    description=(plan_path.parent/'cell.urdf').read_text()
    snapshot=Path(plan['snapshot'])
    if not snapshot.is_file() or digest(json.loads(snapshot.read_text()))!=plan['snapshot_sha256']:
        raise ValueError('Original measured snapshot changed or is missing; regenerate the plan')
    if hashlib.sha256(description.encode()).hexdigest()!=analysis['source_urdf_sha256']:
        raise ValueError('Collision model differs from separation proof')
    if analysis.get('required_interarm_clearance_m',0)<.05:
        raise ValueError('First hardware parallel scan requires at least 50mm modeled clearance')
    if analysis.get('joint_tracking_corridor_rad',0)<tracking:
        raise ValueError('Separation proof lacks the monitored tracking corridor')
    for phase in ('initial','extra'):
        if analysis['phases'][phase]['all_four_phase_independent_separation_proven'] is not True:
            raise ValueError(phase+': not all four arms have a separation proof')
    for path,expected in analysis['mesh_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Collision mesh changed since proof')
    validated_steps(plan,{rid:joint_names(rid) for rid in ROBOT_IDS})
    for step in plan['steps']:
        for point in step['points']:
            if max(abs(np.asarray(point['velocities'])))>.050001 or max(abs(np.asarray(point['accelerations'])))>.100001:
                raise ValueError('Scan trajectory exceeds 0.05rad/s or 0.10rad/s²')
    # One initial view and the same number of extra views per robot.
    initial=[i for i,s in enumerate(plan['steps']) if s['purpose']=='common_object_initial_view']
    extras={rid:[i for i,s in enumerate(plan['steps']) if s['arm']==rid and s['purpose']=='additional_object_view'] for rid in ROBOT_IDS}
    if len({len(chain) for chain in extras.values()})!=1 or not all(extras.values()):
        raise ValueError('Four-arm execution requires equal nonzero extra-view counts')
    rounds=[initial]+[[extras[rid][k] for rid in ROBOT_IDS] for k in range(len(next(iter(extras.values()))))]
    return plan,analysis,description,rounds


class DashboardWatch:
    """Independent read-only device liveness; ROS broadcasters can cache joints."""
    def __init__(self,profiles):
        self.profiles=profiles;self.records={};self.sockets={};self.lock=threading.Lock();self.done=threading.Event()
        self.threads=[threading.Thread(target=self.run,args=(rid,p),daemon=True) for rid,p in profiles.items()]
        for thread in self.threads:thread.start()

    @staticmethod
    def line(connection):
        result=bytearray()
        while not result.endswith(b'\n'):
            data=connection.recv(1)
            if not data:raise RuntimeError('Dashboard connection closed')
            result.extend(data)
            if len(result)>4096:raise RuntimeError('Invalid Dashboard response')
        return result.decode(errors='replace').strip()

    def run(self,rid,profile):
        connection=None
        while not self.done.is_set():
            try:
                if connection is None:
                    connection=socket.create_connection((profile['ip'],profile.get('dashboard_port',29999)),timeout=1.)
                    connection.settimeout(1.);self.line(connection)
                    with self.lock:self.sockets[rid]=connection
                answers={}
                for command in ('robotmode','safetymode','programState'):
                    connection.sendall((command+'\n').encode());answers[command]=self.line(connection)
                record=dict(received_monotonic=time.monotonic(),answers=answers)
            except Exception as error:
                record=dict(received_monotonic=time.monotonic(),error=str(error))
                if connection:
                    try:connection.close()
                    except Exception:pass
                connection=None
            with self.lock:self.records[rid]=record
            self.done.wait(.2)

    def guard(self):
        with self.lock:records=dict(self.records)
        for rid in self.profiles:
            record=records.get(rid)
            if not record or time.monotonic()-record['received_monotonic']>2.:
                raise RuntimeError(rid+': live hardware confirmation unavailable; cached ROS joints are insufficient')
            if record.get('error'):raise RuntimeError(rid+': Dashboard hardware link failed: '+record['error'])
            answers=record['answers']
            if answers['robotmode'].strip()!='Robotmode: RUNNING':
                raise RuntimeError(rid+': '+answers['robotmode'])
            if answers['safetymode'].strip() not in ('Safetymode: NORMAL','Safetymode: REDUCED'):
                raise RuntimeError(rid+': '+answers['safetymode'])
            if not answers['programState'].startswith('PLAYING'):
                raise RuntimeError(rid+': native program is not PLAYING')

    def close(self):
        self.done.set()
        with self.lock:connections=list(self.sockets.values())
        for connection in connections:
            try:connection.shutdown(socket.SHUT_RDWR);connection.close()
            except Exception:pass
        for thread in self.threads:thread.join(timeout=2.)


class ScanObserver(JointObserver):
    def __init__(self,node,profiles,mock):
        self.history={rid:deque(maxlen=1000) for rid in profiles}
        self.robot_modes={}
        super().__init__(node,profiles,profiles,'mock' if mock else 'hardware')
        if not mock:
            from ur_dashboard_msgs.msg import RobotMode
            from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
            qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
            for rid,p in profiles.items():
                self.subscriptions.append(node.create_subscription(RobotMode,p['namespace']+'/io_and_status_controller/robot_mode',
                    lambda msg,rid=rid:self.robot_modes.update({rid:msg.mode}),qos))

    def receive(self,rid,msg):
        previous=self.received.get(rid)
        super().receive(rid,msg)
        record=self.received.get(rid)
        if record is None or record is previous:return
        velocities=dict(zip(msg.name,msg.velocity)) if len(msg.velocity)==len(msg.name) else {}
        v=[velocities[j] for j in self.profiles[rid]['joint_names']] if velocities else None
        self.history[rid].append((time.monotonic(),np.asarray(record['positions']),v))

    def settled(self,window=.5):
        now=time.monotonic()
        for rid,history in self.history.items():
            record=self.received.get(rid)
            if not record or now-record['received_monotonic']>.3:return False
            rows=[r for r in history if r[0]>=now-window-.1]
            if not rows or now-rows[-1][0]>.3 or rows[-1][0]-rows[0][0]<window:return False
            if np.max(np.ptp([r[1] for r in rows],axis=0))>.001:return False
            if any(v is not None and (not np.isfinite(v).all() or np.max(abs(np.asarray(v)))>.005) for _,_,v in rows):return False
        return True


class ParallelMotion:
    def __init__(self,node,profiles,output,*,mock=False,require_gui=True,tracking=.005):
        import rclpy
        from rclpy.action import ActionClient
        from control_msgs.action import FollowJointTrajectory
        from std_msgs.msg import String,Empty
        from std_srvs.srv import Trigger
        from action_msgs.srv import CancelGoal
        self.node,self.profiles,self.mock=node,profiles,mock
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.require_gui,self.tracking=require_gui,tracking
        self.stop_requested=False;self.last_heartbeat=0.;self.last_clock=None
        self.paused=False;self.resume_requested=False
        self.owned=set();self.claimed=set();self.active={};self.expected={};self.handles={};self.pending={};self.results={}
        controller='joint_trajectory_controller' if mock else 'scaled_joint_trajectory_controller'
        self.controller=controller
        # Register actions before MoveIt creates its C++ model/logger.
        self.clients={rid:ActionClient(node,FollowJointTrajectory,p['namespace']+'/'+controller+'/follow_joint_trajectory')
                      for rid,p in profiles.items()}
        self.cancel_clients={rid:node.create_client(CancelGoal,p['namespace']+'/'+controller+'/follow_joint_trajectory/_action/cancel_goal')
                             for rid,p in profiles.items()}
        self.observer=ScanObserver(node,profiles,mock)
        self.dashboard_watch=None if mock else DashboardWatch(profiles)
        self.status_publisher=node.create_publisher(String,'/uwa_object_scan/status',10)
        self.heartbeat_sub=node.create_subscription(Empty,'/uwa_object_scan/heartbeat',
            lambda msg:setattr(self,'last_heartbeat',time.monotonic()),10)
        def stop(request,response):
            self.stop_requested=True;response.success=True;response.message='STOP RECEIVED: cancel/deactivate in progress, standstill not yet confirmed'
            return response
        self.stop_service=node.create_service(Trigger,'/uwa_object_scan/stop',stop)
        def resume(request,response):
            response.success=self.paused and not self.stop_requested
            if response.success:self.resume_requested=True
            response.message='Resume received' if response.success else 'Not paused or STOP is latched'
            return response
        self.resume_service=node.create_service(Trigger,'/uwa_object_scan/resume',resume)

    def status(self,phase,**details):
        from std_msgs.msg import String
        record=dict(phase=phase,recorded_at=datetime.now(timezone.utc).isoformat(),**details)
        (self.output/'runtime.json').write_text(json.dumps(record,indent=2)+'\n')
        with (self.output/'events.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
        self.status_publisher.publish(String(data=json.dumps(record)))
        print(json.dumps(record),flush=True)

    def spin(self,timeout=.02):
        import rclpy
        rclpy.spin_once(self.node,timeout_sec=timeout)

    def guard(self):
        if self.stop_requested:raise RuntimeError('Operator/GUI requested STOP')
        now=time.monotonic()
        if self.require_gui and now-self.last_heartbeat>.8:raise RuntimeError('Scan GUI heartbeat lost')
        if self.dashboard_watch is not None:self.dashboard_watch.guard()
        clock=self.node.get_clock().now().nanoseconds
        if self.last_clock is not None and clock<self.last_clock-10_000_000:raise RuntimeError('ROS time jumped backwards')
        self.last_clock=clock
        for rid in self.profiles:
            r=self.observer.received.get(rid)
            if not r or now-r['received_monotonic']>.5:raise RuntimeError(rid+': joint telemetry stale')
            if not self.mock:
                if self.observer.safety_modes.get(rid) not in (1,2):raise RuntimeError(rid+': native safety is not NORMAL/REDUCED')
                if self.observer.robot_modes.get(rid)!=7:raise RuntimeError(rid+': native robot mode is not RUNNING')
                if self.observer.program_running.get(rid) is not True:raise RuntimeError(rid+': External Control link not confirmed')
            q=np.asarray(r['positions'])
            if rid in self.active:
                start,target=self.active[rid]
                if path_deviation(q,start,target)>self.tracking:
                    raise RuntimeError(rid+': left the proved joint-path tracking corridor')
            elif rid in self.expected and np.max(abs(q-self.expected[rid]))>self.tracking:
                raise RuntimeError(rid+': unexpected motion of a holding arm')

    def wait_ready(self,expected,timeout=20.):
        self.expected={rid:np.asarray(expected[rid]) for rid in self.profiles}
        end=time.monotonic()+timeout;error='No data'
        while time.monotonic()<end:
            self.spin(.03)
            try:
                self.guard()
                if self.observer.settled():return
            except RuntimeError as e:error=str(e)
            if self.stop_requested:break
        raise RuntimeError('Readiness/settling failed: '+error)

    def wait(self,future,deadline,*,guard=True):
        while not future.done():
            self.spin(.01)
            if guard:self.guard()
            if time.monotonic()>deadline:raise RuntimeError('Native action response timed out')
        return future.result()

    def batch(self,steps):
        from action_msgs.msg import GoalStatus
        from match_ur_hardware.operations import switch
        from match_ur_hardware.trajectory import trajectory_goal
        if self.stop_requested:raise RuntimeError('STOP already latched')
        self.guard()
        for step in steps:
            rid=step['arm'];p=self.profiles[rid]
            if np.max(abs(np.asarray(self.observer.received[rid]['positions'])-step['points'][0]['positions']))>.001:
                raise RuntimeError(rid+': batch start differs from checked path')
            deadline=time.monotonic()+20
            while not self.clients[rid].server_is_ready():
                self.spin(.03);self.guard()
                if time.monotonic()>deadline:raise RuntimeError(rid+': trajectory endpoint unavailable')
            switch(self.node,p,target=self.controller);self.owned.add(rid);self.claimed.add(rid)
        self.guard()
        self.handles,self.pending,self.results={},{},{}
        self.active={s['arm']:(np.asarray(s['points'][0]['positions']),np.asarray(s['target'])) for s in steps}
        try:
            for s in steps:
                rid=s['arm'];goal=trajectory_goal(self.profiles[rid]['joint_names'],s['points'])
                self.pending[rid]=self.clients[rid].send_goal_async(goal)
            deadline=time.monotonic()+8
            for rid,future in self.pending.items():
                handle=self.wait(future,deadline)
                self.handles[rid]=handle
                if handle is None or not handle.accepted:raise RuntimeError(rid+': trajectory rejected')
                self.results[rid]=handle.get_result_async()
            deadline=time.monotonic()+max(s['points'][-1]['time'] for s in steps)*3+30
            finished=set()
            while len(finished)<len(steps):
                self.spin(.01);self.guard()
                for rid,future in self.results.items():
                    if rid not in finished and future.done():
                        result=future.result()
                        if result.status!=GoalStatus.STATUS_SUCCEEDED or result.result.error_code!=0:
                            raise RuntimeError(rid+': trajectory aborted: '+result.result.error_string)
                        finished.add(rid)
                if time.monotonic()>deadline:raise RuntimeError('Parallel trajectories timed out')
            for s in steps:self.expected[s['arm']]=np.asarray(s['target'])
            self.active={}
            self.wait_ready(self.expected,timeout=8.)
        except BaseException:
            self.abort()
            raise

    def deactivate(self):
        from match_ur_hardware.operations import switch
        errors=[]
        for rid in list(self.owned):
            try:switch(self.node,self.profiles[rid]);self.owned.remove(rid)
            except Exception as e:errors.append(rid+': '+str(e))
        return errors

    def abort(self):
        self.stop_requested=True
        from action_msgs.srv import CancelGoal
        # Collect late acknowledgements too, then cancel all goals before blocking
        # controller-service calls. Never leave three accepted goals running when
        # the fourth rejects or its acknowledgement is delayed.
        cancellations=[]
        # Zero goal UUID/time cancels all goals on our exclusively claimed JTC.
        # This also covers accepted goals whose acknowledgement has not reached
        # our ActionClient yet; don't wait several controller-service timeouts.
        for rid,client in getattr(self,'cancel_clients',{}).items():
            if rid in self.claimed:
                try:cancellations.append(client.call_async(CancelGoal.Request()))
                except Exception:pass
        cancelled=set()
        def cancel_known():
            for rid,handle in self.handles.items():
                if rid not in cancelled and handle is not None and handle.accepted:
                    try:cancellations.append(handle.cancel_goal_async());cancelled.add(rid)
                    except Exception:pass
        cancel_known()  # Do not wait for a late fourth acknowledgement first.
        self.owned.update(self.claimed)
        errors=self.deactivate()
        deadline=time.monotonic()+2.
        for rid,future in list(self.pending.items()):
            if rid not in self.handles:
                try:self.handles[rid]=self.wait(future,deadline,guard=False)
                except Exception:pass
        cancel_known()
        deadline=time.monotonic()+3
        for future in cancellations:
            try:self.wait(future,deadline,guard=False)
            except Exception:pass
        self.owned.update(self.claimed)
        errors+=self.deactivate()
        self.active={}
        end=time.monotonic()+4
        while time.monotonic()<end:
            self.spin(.03)
            if self.observer.settled():
                self.status('STOPPED',standstill_confirmed=True,controller_errors=errors)
                return
        if not self.mock:
            from std_srvs.srv import Trigger
            clients=[]
            for p in self.profiles.values():
                client=self.node.create_client(Trigger,p['namespace']+'/dashboard_client/stop');clients.append(client)
                if client.service_is_ready():client.call_async(Trigger.Request())
            end=time.monotonic()+2
            while time.monotonic()<end:self.spin(.03)
            for client in clients:self.node.destroy_client(client)
        confirmed=self.observer.settled()
        self.status('STOPPED' if confirmed else 'STOP_UNCONFIRMED',standstill_confirmed=confirmed,
                    controller_errors=errors,message='USE PHYSICAL EMERGENCY STOP if motion continues')

    def close(self):
        self.deactivate()
        if self.dashboard_watch is not None:self.dashboard_watch.close()
        for client in self.clients.values():client.destroy()
        for client in self.cancel_clients.values():self.node.destroy_client(client)
        self.observer.close();self.node.destroy_subscription(self.heartbeat_sub);self.node.destroy_service(self.stop_service)
        self.node.destroy_service(self.resume_service)


def round_start_positions(plan, rounds, number):
    if not 1 <= number <= len(rounds):
        raise ValueError('Start round outside the checked scan')
    selected = [plan['steps'][index] for index in rounds[number-1]]
    expected = {step['arm']: step['points'][0]['positions'] for step in selected}
    if set(expected) != set(ROBOT_IDS) or len(selected) != len(ROBOT_IDS):
        raise ValueError('A resume round must contain exactly all four original arm paths')
    return expected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--analysis',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,default=Path.home()/'UWA_ws')
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--start-round',type=int,default=1,help='Explicit restart from a checked round; never blend to its start')
    parser.add_argument('--pause-after-initial',action='store_true',help='Hold after first five photographs for image review')
    args=parser.parse_args()
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    from match_ur_hardware.profiles import load_profiles,MOTION
    from match_ur_hardware.operations import controller_list
    from .scan_camera_worker import CameraProcess
    args.output.mkdir(parents=True,exist_ok=False)
    lock=(args.workspace/'setup/digitization/.four_arm_scan.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ['ROS_DOMAIN_ID']='66';os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    rclpy.init(args=[],signal_handler_options=SignalHandlerOptions.NO)
    node=rclpy.create_node('uwa_parallel_object_scan')
    profiles=load_profiles(args.workspace/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml')
    runner=ParallelMotion(node,profiles,args.output,require_gui=not args.check_only)
    def stop(signum,frame):runner.stop_requested=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    rig=None
    try:
        plan,proof,description,rounds=load_checked(args.plan,args.analysis)
        if plan.get('inventory_fingerprint')!=digest(profiles):
            raise RuntimeError('Robot inventory differs from the planned physical identities')
        expected=round_start_positions(plan,rounds,args.start_round)
        runner.status('PREPARING',message='Checking exact source paths, live robot states and separation proof')
        runner.wait_ready(expected)
        for rid,p in profiles.items():
            if any(c.name in MOTION and c.state=='active' for c in controller_list(node,p)):
                raise RuntimeError(rid+': an existing motion controller is active; no takeover')
        with tempfile.TemporaryDirectory(prefix='uwa-parallel-scan-recheck-') as directory:
            model,layout=make_model(load_layout(default_layout_path()),profiles,directory)
            if collision_signature(model.description)!=collision_signature(description):
                raise RuntimeError('Current collision model differs from proved source model')
            from .object_scan_plan import target_geometry,add_object_collision
            target=target_geometry(layout,model.description,plan['design'])
            add_object_collision(model,target,plan['design']['collision_padding_m'])
            # Preserve original full-cell self/environment checks. Inter-arm
            # arbitrary-progress proof separately permits reordering these paths.
            for step in plan['steps']:
                for point in step['points']:
                    state=dict(step['start'],**dict(zip(joint_names(step['arm']),point['positions'])))
                    if not model.check(state)[0]:raise RuntimeError('Fresh full-cell source-path check failed')
            runner.wait_ready(expected)
        # Mesh/FCL planning state is no longer needed during native image work.
        # Release it before the 48-MP decoder/detector allocates its buffers.
        del model
        (args.output/'source_manifest.json').write_text(json.dumps(dict(plan=str(args.plan.resolve()),
            inventory_fingerprint=digest(profiles),
            plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),analysis=str(args.analysis.resolve()),
            analysis_sha256=hashlib.sha256(args.analysis.read_bytes()).hexdigest(),rounds=rounds,start_round=args.start_round),indent=2)+'\n')
        if args.check_only:
            runner.status('CHECKED',motion_sent=False,rounds=len(rounds));return
        rig=CameraProcess(args.workspace,args.output)
        def wait_camera(token):
            while not rig.ready(token):
                runner.spin(.02);runner.guard()
                if rig.child.poll() is not None:
                    raise RuntimeError('Camera worker exited; see camera_ipc/worker.log')
            return rig.result(token)
        wait_camera(rig.submit('focus'))
        for index,indices in enumerate(rounds[args.start_round-1:],start=args.start_round-1):
            runner.wait_ready(runner.expected)
            steps=[plan['steps'][i] for i in indices]
            runner.status('MOVING',round=index+1,total_rounds=len(rounds),arms=[s['arm'] for s in steps])
            runner.batch(steps)
            errors=runner.deactivate()
            if errors:raise RuntimeError('Controller deactivation failed: '+str(errors))
            runner.status('CAPTURING',round=index+1,total_rounds=len(rounds),message='All four arms settled; native five-camera photographs')
            report=wait_camera(rig.submit('capture'))
            if not report['all_captured'] or not report.get('stationary_set_confirmed'):
                raise RuntimeError('Photo set failed; no next movement: '+report.get('error','see manifest'))
            runner.status('CAPTURED',round=index+1,total_rounds=len(rounds),directory=report['directory'])
            if index==0 and args.pause_after_initial:
                runner.paused=True;runner.resume_requested=False
                runner.status('PAUSED',round=1,total_rounds=len(rounds),directory=report['directory'],
                              message='Initial photographs saved. Review images, then Continue. All motion controllers inactive.')
                while not runner.resume_requested:runner.spin(.02);runner.guard()
                runner.paused=False
        runner.status('COMPLETE',rounds=len(rounds),photo_session=str(rig.session),automatic_return=False)
    except BaseException as error:
        if runner.owned or runner.handles:runner.abort()
        runner.status('FAILED',error=str(error),automatic_return=False)
        raise
    finally:
        # A native photo transaction must finish its restoration even after STOP.
        if rig is not None:
            try:rig.close(spin=lambda:runner.spin(.02))
            except Exception as e:runner.status('RESTORE_FAILED',error=str(e))
        runner.close();node.destroy_node();rclpy.shutdown();lock.close()


if __name__=='__main__':main()

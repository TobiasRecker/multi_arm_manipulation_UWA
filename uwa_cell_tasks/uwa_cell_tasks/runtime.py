"""ROS simulation adapter. One action controller owns the whole rigid group."""
import fcntl
import json
from pathlib import Path
import threading
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from sensor_msgs.msg import JointState,Image,CameraInfo
from std_msgs.msg import String
from std_srvs.srv import Trigger,SetBool
from controller_manager_msgs.srv import SwitchController,ListControllers
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from action_msgs.msg import GoalStatus
from uwa_cell_description.configuration import load_layout,joint_names,gripper_joint
from uwa_cell_motion.common import simulation_only
from uwa_cell_gazebo.charuco_views import Chain
from match_cooperative_handling.rigid_object import pose_error,interpolate
from .core import ARMS,CAMERAS,RunStore,GraspGroup,verify,write_json,seal
from .planning import TaskProblem,grasp_candidates,plan_approach,object_trajectory,grasp_entry,PlannedObjectConstraint
from .scene import verify_scene


class Simulation(Node):
    def __init__(self,namespace,scene_directory):
        simulation_only()
        if not namespace.startswith('/uwa_grasp_'):raise ValueError('An isolated /uwa_grasp_* simulation namespace is required')
        super().__init__('task_runner',namespace=namespace,
            cli_args=['--ros-args','-r','/clock:='+namespace+'/clock'])
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
        self.ns=namespace;self.directory=Path(scene_directory);self.q={};self.v={};self.joint_received=0.
        self.guard=None;self.supervisor=None;self.guard_received=0.;self.supervisor_received=0.
        self.contact=None;self.object=None;self.contact_received=0.;self.object_received=0.;self.images={};self.infos={}
        self.phase='observe';self.handles=[];self.owned=False
        self.create_subscription(JointState,namespace+'/joint_states',self.joints,qos_profile_sensor_data)
        for topic,key in [('collision_guard/decision','guard'),('collision_supervisor/status','supervisor'),
                          ('tasks/contacts','contact'),('tasks/object_truth','object')]:
            self.create_subscription(String,namespace+'/'+topic,lambda msg,k=key:self.message(k,msg),10)
        self.heartbeat_pub=self.create_publisher(String,'tasks/heartbeat',10)
        self.group_pub=self.create_publisher(String,'tasks/group',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.heartbeat_clock=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.1,self.heartbeat,clock=self.heartbeat_clock)
        self.service_clients={key:self.create_client(kind,namespace+'/'+topic) for key,kind,topic in [
            ('reset',Trigger,'collision_supervisor/reset'),('switch',SwitchController,'controller_manager/switch_controller'),
            ('list',ListControllers,'controller_manager/list_controllers'),('latch',SetBool,'tasks/grip_latch'),
            ('capture',Trigger,'tasks/camera_capture')]}
        for arm in ARMS:self.service_clients['stop_'+arm]=self.create_client(Trigger,namespace+'/collision_supervisor/'+arm+'/stop')
        self.actions={name:ActionClient(self,FollowJointTrajectory,namespace+'/'+name+'/follow_joint_trajectory')
            for name in ['rigid_object_controller']+[a+'_gripper_controller' for a in ARMS]}
        self.executor=MultiThreadedExecutor(num_threads=2);self.executor.add_node(self)
        self.thread=threading.Thread(target=self.executor.spin,daemon=True);self.thread.start()

    def joints(self,msg):
        self.q=dict(zip(msg.name,msg.position));self.v=dict(zip(msg.name,msg.velocity));self.joint_received=time.monotonic()
    def message(self,key,msg):setattr(self,key,json.loads(msg.data));setattr(self,key+'_received',time.monotonic())
    def image(self,arm,msg):self.images[arm]=msg
    def info(self,arm,msg):self.infos[arm]=msg
    def heartbeat(self):
        if self.owned:
            if (getattr(self,'stop_directory',self.directory)/'STOP').exists() and not getattr(self,'stop_sent',False):
                self.stop_sent=True
                for arm in ARMS:self.service_clients['stop_'+arm].call_async(Trigger.Request())
            self.heartbeat_pub.publish(String(data=json.dumps(dict(phase=self.phase))))
    def now(self):return self.get_clock().now().nanoseconds/1e9

    def wait(self,predicate,timeout=10.,*,health=False):
        end=time.monotonic()+timeout
        while not predicate():
            if health:self.health()
            if time.monotonic()>end:raise TimeoutError('Simulation response timed out')
            time.sleep(.01)

    def call(self,key,request,timeout=8.):
        client=self.service_clients[key]
        if not client.wait_for_service(timeout_sec=timeout):raise RuntimeError('Missing service '+key)
        future=client.call_async(request);self.wait(future.done,timeout,health=key=='capture')
        result=future.result()
        if hasattr(result,'success') and not result.success:raise RuntimeError(result.message)
        return result

    def health(self):
        now=time.monotonic()
        if ((getattr(self,'stop_directory',self.directory)/'STOP').exists() or now-self.joint_received>.2 or now-self.guard_received>.4
                or now-self.supervisor_received>.4):raise RuntimeError('STOP requested or state/guard lost')
        if self.owned and set(ARMS).intersection(self.supervisor.get('blocked_arms',[])):
            raise RuntimeError('Grasp group/owned arm STOP LATCHED')
        if self.owned and any(abs(self.q.get(j,float('inf'))-q)>.001 or abs(self.v.get(j,float('inf')))>.003
            for j,q in getattr(self,'obstacles',{}).items()):
            raise RuntimeError('Unselected obstacle arm moved; remaining task plan invalid')

    def connect(self):
        self.wait(lambda:bool(self.q) and self.guard is not None and self.supervisor is not None
            and self.object is not None and self.contact is not None,30.)

    def reset(self):
        from .planning import actual_names
        description=(self.directory/'robot.urdf').read_text()
        required=[j for names in actual_names(description,getattr(self,'layout',load_layout())).values() for j in names]
        if self.contact and any(any(p.values()) for p in self.contact['pads'].values()):
            raise RuntimeError('Object contact already exists; explicit supported release is required before a new run')
        self.wait(lambda:all(j in self.v and abs(self.v[j])<.003 for j in required),30.)
        time.sleep(.5)
        self.call('reset',Trigger.Request())
        self.wait(lambda:not set(ARMS).intersection(self.supervisor.get('blocked_arms',[])),5.)
        self.owned=True

    def activate_group(self):
        states=self.call('list',ListControllers.Request()).controller
        deactivate=[c.name for c in states if c.state=='active' and c.name in [a+'_trajectory_controller' for a in ARMS]]
        req=SwitchController.Request();req.activate_controllers=['rigid_object_controller'];req.deactivate_controllers=deactivate
        req.strictness=2;req.timeout.sec=5
        response=self.call('switch',req)
        if not response.ok:raise RuntimeError('Common rigid-object controller activation rejected')

    def follow(self,trajectory,controller='rigid_object_controller',timeout=None):
        self.health();action=self.actions[controller]
        if not action.wait_for_server(timeout_sec=5.):raise RuntimeError('Missing action '+controller)
        goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=trajectory['joint_names']
        for entry in trajectory['points']:
            point=JointTrajectoryPoint();point.positions=list(entry['positions'])
            # Linear interpolation for object-derived samples; no independent retiming.
            if 'velocities' in entry:point.velocities=list(entry['velocities'])
            if 'accelerations' in entry:point.accelerations=list(entry['accelerations'])
            ns=round(entry['time']*1e9);point.time_from_start.sec=ns//10**9;point.time_from_start.nanosec=ns%10**9
            goal.trajectory.points.append(point)
        future=action.send_goal_async(goal);self.wait(future.done,5.,health=True);handle=future.result()
        if not handle.accepted:raise RuntimeError('Action rejected '+controller)
        self.handles.append(handle);result=handle.get_result_async()
        self.wait(result.done,timeout or trajectory['points'][-1]['time']*5+10,health=True)
        response=result.result()
        if response.status!=GoalStatus.STATUS_SUCCEEDED or response.result.error_code!=0:
            raise RuntimeError('Action failed: '+response.result.error_string)
        self.wait(lambda:all(abs(self.v.get(j,1))<.003 for j in trajectory['joint_names']),5.,health=True)
        if any(abs(self.q.get(j,float('inf'))-q)>.001 for j,q in zip(trajectory['joint_names'],trajectory['points'][-1]['positions'])):
            raise RuntimeError('Measured endpoint did not reach the checked common target')
        self.handles.remove(handle)

    def grippers(self,target):
        states=self.call('list',ListControllers.Request()).controller
        needed=[a+'_gripper_controller' for a in ARMS]
        activate=[n for n in needed if not any(c.name==n and c.state=='active' for c in states)]
        if activate:
            req=SwitchController.Request();req.activate_controllers=activate;req.strictness=2;req.timeout.sec=5
            if not self.call('switch',req).ok:raise RuntimeError('Gripper activation rejected')
        # Both fingers advance under the same target schedule. Physical contact
        # can stop the force-limited fingers before their requested closure.
        start={a:self.q[gripper_joint(a)] for a in ARMS}
        duration=max(1.,max(abs(target-start[a]) for a in ARMS)/.02)
        pending=[]
        for arm in ARMS:
            goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=[gripper_joint(arm)]
            for u in np.linspace(0,1,int(duration/.1)+2):
                p=JointTrajectoryPoint();p.positions=[float(start[arm]+u*(target-start[arm]))]
                ns=round(u*duration*1e9);p.time_from_start.sec=ns//10**9;p.time_from_start.nanosec=ns%10**9
                goal.trajectory.points.append(p)
            action=self.actions[arm+'_gripper_controller']
            if not action.wait_for_server(timeout_sec=5.):raise RuntimeError('Gripper action unavailable')
            pending.append(action.send_goal_async(goal))
        self.wait(lambda:all(p.done() for p in pending),5.,health=True)
        handles=[p.result() for p in pending]
        if not all(h.accepted for h in handles):raise RuntimeError('Gripper goal rejected')
        self.handles.extend(handles)
        # A force-limited grip intentionally cannot reach its closed-air angle.
        if target>0:
            self.wait(lambda:all(all(self.contact['pads'][a].values()) for a in ARMS),duration+5,health=True)
            self.call('latch',SetBool.Request(data=True))
            for h in handles:h.cancel_goal_async()
            preload_until=self.now()+max(.5,max(.8-self.q[gripper_joint(a)] for a in ARMS)/.02)
            wall_deadline=time.monotonic()+180.
            while self.now()<preload_until:
                self.health()
                if time.monotonic()>wall_deadline:raise TimeoutError('Grip preload did not settle')
                time.sleep(.02)
        else:
            results=[h.get_result_async() for h in handles]
            self.wait(lambda:all(f.done() for f in results),duration*3+10,health=True)
            if any(f.result().result.error_code!=0 for f in results):raise RuntimeError('Open gripper action failed')
        for h in handles:
            if h in self.handles:self.handles.remove(h)

    def stop(self):
        report=dict(arms=list(ARMS),grip_release_commanded=False,confirmed=False)
        for h in list(self.handles):h.cancel_goal_async()
        try:
            for arm in ARMS:self.call('stop_'+arm,Trigger.Request(),3.)
            self.wait(lambda:set(ARMS)<=set(self.supervisor.get('held_arms',[])) and
                all(abs(self.v.get(j,1))<.003 for a in ARMS for j in joint_names(a)),5.)
            states=self.call('list',ListControllers.Request()).controller
            report['confirmed']=all(any(c.name==a+'_collision_hold_controller' and c.state=='active' for c in states) for a in ARMS)
        except Exception as error:report['error']=str(error)
        return report

    def close(self):
        self.executor.shutdown(timeout_sec=2.);self.thread.join(timeout=2.);self.destroy_node()


def await_review(store,sim,stage,evidence):
    packet=store.request_review(stage,evidence);end=time.monotonic()+300.
    while time.monotonic()<end:
        sim.health()
        if (store.directory/'STOP').exists():raise RuntimeError('STOP requested')
        decision=store.decision(packet)
        if decision:
            store.event('REVIEWED',stage,decision=decision)
            return decision['decision']
        time.sleep(.1)
    raise TimeoutError('Agent review timed out; group remains held')


def run_task(directory,scene_directory,layout_file,namespace,reference):
    directory=Path(directory).resolve();store=RunStore(directory)
    lock=(directory/'runner.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if store.state['state']!='CREATED':raise RuntimeError('A run is immutable after start; create a new run directory')
    scene_directory=Path(scene_directory);scene=verify_scene(scene_directory)
    cfg=scene['cfg'];layout=load_layout(layout_file);description=(scene_directory/'robot.urdf').read_text()
    sim=Simulation(namespace,scene_directory);sim.stop_directory=directory;sim.layout=layout;sim.connect();group=None
    try:
        sim.reset();sim.activate_group()
        sim.obstacles={j:q for j,q in sim.q.items() if j.startswith(('left_front_','left_rear_')) and ('_robotiq_' not in j or j.endswith('robotiq_85_left_knuckle_joint'))}
        for attempt in range(int(cfg['maximum_attempts'])):
            store.event('RUNNING','observe',attempt=attempt+1)
            from .observation import observe
            observation=observe(sim,description,reference,directory/f'observe-{attempt}')
            obj=np.array(observation['T_world_object']);start=dict(sim.q)
            candidates=grasp_candidates(description,scene,cfg,obj)
            strategy=seal(dict(observation=observation,candidates=candidates,scene_sha256=scene['sha256']))
            write_json(directory/'strategy.json',strategy)
            decision=await_review(store,sim,'review_strategy',strategy)
            if decision in ('observe','replan'):continue
            if decision=='abort':raise RuntimeError('Agent aborted strategy')
            problem=TaskProblem(directory/f'planning-{attempt}',description,layout,scene,obj)
            failures=[];plan=None
            for candidate in candidates:
                try:
                    plan=plan_approach(problem,start,candidate)
                    witness=TaskProblem(directory/f'witness-{candidate["id"]}',description,layout,scene,obj,static=False)
                    pre_state=dict(start,**dict(zip(plan['request']['joint_names'],plan['request']['target'])))
                    entry,grasp_state=grasp_entry(witness,pre_state,candidate,cfg)
                    predicted=PlannedObjectConstraint(obj,candidate['tcp_targets'])
                    lifted=obj.copy();lifted[2,3]+=cfg['lift_m']
                    # This geometric witness is distinct from the actual
                    # contact-bound plan recomputed after grasp confirmation.
                    lift_witness=object_trajectory(witness,predicted,grasp_state,obj,lifted,cfg)
                    plan=seal(dict(plan,entry=entry,lift_witness=lift_witness))
                    break
                except ValueError as error:
                    failures.append(dict(candidate=candidate['id'],reason=str(error)));plan=None
            write_json(directory/'candidate_failures.json',failures)
            if plan is None:raise RuntimeError('No collision-clear reachable grasp candidate; see candidate_failures.json')
            write_json(directory/'plan.json',plan)
            decision=await_review(store,sim,'review_plan',plan)
            if decision in ('observe','replan'):continue
            if decision=='abort':raise RuntimeError('Agent aborted plan')
            verify(plan)
            verify_scene(scene_directory)
            import hashlib
            if any(hashlib.sha256(Path(path).read_bytes()).hexdigest()!=value for path,value in plan['mesh_sha256'].items()):
                raise RuntimeError('Robot collision mesh changed after review')
            if any(abs(sim.q.get(j,float('inf'))-q)>.002 for j,q in start.items() if j in problem.collision.bounds):
                raise RuntimeError('Measured start changed after review; regenerate plan')
            latest=observe(sim,description,reference,directory/f'pre-execution-{attempt}')
            freshness_delta=pose_error(obj,latest['T_world_object'])
            if freshness_delta[0]>.002 or freshness_delta[1]>.0175:
                store.event('REPLAN_REQUIRED','observe',reason='Object changed after plan review')
                continue
            sim.phase='approach';store.event('RUNNING','approach');sim.follow(plan['trajectory'])
            aligned=observe(sim,description,reference,directory/f'alignment-{attempt}')
            delta=pose_error(obj,aligned['T_world_object'])
            alignment=seal(dict(observation=aligned,expected_object_pose=obj,delta_m_rad=delta,
                plan_sha256=plan['sha256'],candidate=plan['candidate']))
            decision=await_review(store,sim,'review_alignment',alignment)
            if decision in ('observe','replan'):continue
            if decision=='abort':raise RuntimeError('Agent aborted alignment')
            if delta[0]>.003 or delta[1]>.02:raise RuntimeError('Pregrasp alignment exceeds first-run corridor')
            # Final entry is still pre-grasp. Both Cartesian targets share one
            # interpolation parameter and one combined controller.
            sim.phase='grasp';store.event('RUNNING','grasp')
            contact_problem=TaskProblem(directory/'contact-plan',description,layout,scene,obj,static=False)
            entry,_=grasp_entry(contact_problem,dict(sim.q),plan['candidate'],cfg)
            sim.follow(entry);sim.grippers(.8)
            # Use visual pose and actual TCPs, not a synthetic attachment.
            grasp_observation=observe(sim,description,reference,directory/'grasp-observation')
            obj=np.array(grasp_observation['T_world_object'])
            tcps={a:contact_problem.chains[a].forward(sim.q) for a in ARMS}
            group=GraspGroup(cfg['object_id'],obj,tcps,sim.contact['pads'],cfg,plan['candidate']['contacts'])
            record=group.record();write_json(directory/'group.json',record)
            sim.group_pub.publish(String(data=json.dumps(record,default=lambda v:v.tolist())))
            lifted=obj.copy();lifted[2,3]+=cfg['lift_m']
            sim.phase='move_object';store.event('RUNNING','move_object')
            trajectory=object_trajectory(contact_problem,group,dict(sim.q),obj,lifted,cfg)
            truth_before=np.array(sim.object['T_world_object'])
            write_json(directory/'object-lift.json',trajectory);sim.follow(trajectory)
            truth=np.array(sim.object['T_world_object'])
            truth_start=truth_before
            if sim.contact['supported'] or abs((truth[2,3]-truth_start[2,3])-cfg['lift_m'])>.002:
                raise RuntimeError('Actual load pickup was not established')
            end=sim.now()+cfg['dwell_s'];wall_deadline=time.monotonic()+30.
            while sim.now()<end:
                sim.health()
                if time.monotonic()>wall_deadline:raise TimeoutError('Simulation dwell did not complete')
                if sim.contact['supported']:raise RuntimeError('Support contact during free hold')
                time.sleep(.02)
            sim.phase='set_down';store.event('RUNNING','set_down')
            back=object_trajectory(contact_problem,group,dict(sim.q),lifted,obj,cfg)
            write_json(directory/'object-set-down.json',back);sim.follow(back)
            sim.wait(lambda:sim.contact['supported'],5.,health=True)
            release_request=dict(group.record(),release_requested=True)
            sim.group_pub.publish(String(data=json.dumps(release_request,default=lambda v:v.tolist())))
            sim.call('latch',SetBool.Request(data=False));sim.phase='release';sim.grippers(0.)
            sim.wait(lambda:not any(any(sim.contact['pads'][a].values()) for a in ARMS)
                and all(sim.q[gripper_joint(a)]<.02 for a in ARMS),10.,health=True)
            time.sleep(.5)
            group.release(supported=bool(sim.contact['supported']),stationary=True)
            sim.group_pub.publish(String(data=json.dumps(group.record(),default=lambda v:v.tolist())))
            store.event('DONE','done',group=group.record(),actual_hub_m=float(truth[2,3]-truth_start[2,3]),
                physically_attached=False,assumptions=cfg['simulation_assumptions'])
            sim.owned=False
            return store.state
        raise RuntimeError('Review/replanning attempt budget exhausted')
    except BaseException as error:
        report=sim.stop()
        store.event('FAILED',sim.phase,error=str(error),stop=report)
        raise
    finally:
        sim.close();fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

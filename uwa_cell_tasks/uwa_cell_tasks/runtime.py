"""ROS simulation adapter. One action controller owns the whole rigid group."""
import fcntl
import json
from pathlib import Path
import threading
import time
import xml.etree.ElementTree as ET
import numpy as np
import rclpy
from uwa_cell_motion.node import MotionNode
from rclpy.clock import Clock,ClockType
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from sensor_msgs.msg import JointState,Image,CameraInfo
from std_msgs.msg import String
from std_srvs.srv import Trigger,SetBool
from controller_manager_msgs.srv import SwitchController,ListControllers
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTolerance
from trajectory_msgs.msg import JointTrajectoryPoint
from action_msgs.msg import GoalStatus
from uwa_cell_description.configuration import load_layout,joint_names,gripper_joint
from uwa_cell_motion.common import simulation_only
from uwa_cell_gazebo.charuco_views import Chain
from match_cooperative_handling.rigid_object import pose_error,interpolate
from .core import ARMS,CAMERAS,RunStore,GraspGroup,verify,write_json,seal,resource_lease,gripper_profile,measured_open,object_point_height
from .planning import TaskProblem,grasp_candidates,plan_approach,object_trajectory,grasp_entry,PlannedObjectConstraint,carton_motion_poses,compile_object_recipe
from .scene import verify_scene


class Simulation(MotionNode):
    def __init__(self,namespace,scene_directory):
        simulation_only()
        if not namespace.startswith('/uwa_grasp_'):raise ValueError('An isolated /uwa_grasp_* simulation namespace is required')
        super().__init__('task_runner',namespace=namespace,
            cli_args=['--ros-args','-r','/clock:='+namespace+'/clock'])
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
        self.ns=namespace;self.directory=Path(scene_directory);self.q={};self.v={};self.joint_received=0.
        self.cfg=json.loads((self.directory/'scene.json').read_text())['cfg']
        self.finger_names=[j.get('name') for j in ET.fromstring((self.directory/'robot.urdf').read_text()).findall('joint')
            if j.get('type')=='revolute' and j.get('name').startswith(ARMS) and '_robotiq_85_' in j.get('name')]
        if len(self.finger_names)!=12:raise ValueError('Twelve measured right finger joints required')
        self.guard=None;self.supervisor=None;self.guard_received=0.;self.supervisor_received=0.
        self.contact=None;self.object=None;self.contact_received=0.;self.object_received=0.;self.images={};self.infos={}
        self.phase='observe';self.handles=[];self.owned=False;self.measured_peaks={};self.last_artifact_check=0.
        self.create_subscription(JointState,namespace+'/joint_states',self.joints,qos_profile_sensor_data)
        for topic,key in [('collision_guard/decision','guard'),('collision_supervisor/status','supervisor'),
                          ('tasks/contacts','contact'),('tasks/object_truth','object')]:
            self.create_subscription(String,namespace+'/'+topic,lambda msg,k=key:self.message(k,msg),
                qos_profile_sensor_data if key in ('contact','object') else 10)
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
        # A fixed single executor prevents ready /clock callbacks from piling
        # up ahead of controller RPC replies in a multithreaded work queue.
        self.ros_executor=SingleThreadedExecutor();self.ros_executor.add_node(self)
        self.thread=threading.Thread(target=self.ros_executor.spin,daemon=True);self.thread.start()

    def joints(self,msg):
        self.q=dict(zip(msg.name,msg.position));self.v=dict(zip(msg.name,msg.velocity));self.joint_received=time.monotonic()
        peaks=self.measured_peaks.setdefault(self.phase,{})
        for joint,speed in self.v.items():
            if joint.startswith(ARMS):peaks[joint]=max(peaks.get(joint,0.),abs(speed))
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
        # Only this read-only query is replayed after a missing transport reply.
        # Reset, controller switches, latches and captures are never retried here.
        for attempt in range(2 if key=='list' else 1):
            future=client.call_async(request)
            try:self.wait(future.done,timeout,health=key=='capture');break
            except TimeoutError:
                client.remove_pending_request(future)
                if key!='list' or attempt:raise
        result=future.result()
        if hasattr(result,'success') and not result.success:raise RuntimeError(result.message)
        return result

    def health(self):
        now=time.monotonic()
        if now-self.last_artifact_check>=1.:
            verify_scene(self.directory);self.last_artifact_check=now
        if (getattr(self,'stop_directory',self.directory)/'STOP').exists():raise RuntimeError('STOP requested')
        for channel,limit in [('joint',.2),('guard',.4),('supervisor',.4)]:
            age=now-getattr(self,channel+'_received')
            if age>limit:
                import faulthandler
                with (getattr(self,'stop_directory',self.directory)/'stale-thread-stacks.txt').open('a') as output:
                    output.write(f'{channel} stale at monotonic {now}; age {age}\n');output.flush()
                    faulthandler.dump_traceback(file=output,all_threads=True)
                raise RuntimeError(f'{channel} reception stale: {age:.6f}s exceeds {limit:.3f}s')
        if self.owned and set(ARMS).intersection(self.supervisor.get('blocked_arms',[])):
            raise RuntimeError('Grasp group/owned arm STOP LATCHED')
        if self.owned and any(abs(self.q.get(j,float('inf'))-q)>.001 or abs(self.v.get(j,float('inf')))>.003
            for j,q in getattr(self,'obstacles',{}).items()):
            raise RuntimeError('Unselected obstacle arm moved; remaining task plan invalid')

    def connect(self):
        self.wait(lambda:bool(self.q) and self.guard is not None and self.supervisor is not None
            and self.object is not None and self.contact is not None,30.)
        # Discovery of the runner's action/service endpoints can still be in
        # progress after its first telemetry sample. Require sustained fresh
        # reception before reset/ownership; keep all armed deadlines unchanged.
        quiet_since=None
        def ready():
            nonlocal quiet_since
            now=time.monotonic()
            if any(now-getattr(self,k+'_received')>.1 for k in ('joint','object','contact')):
                quiet_since=None;return False
            if quiet_since is None:quiet_since=now
            return now-quiet_since>=5.
        self.wait(ready,30.)

    def reset(self):
        from .planning import actual_names
        description=(self.directory/'robot.urdf').read_text()
        required=[j for names in actual_names(description,getattr(self,'layout',load_layout())).values() for j in names]
        if self.contact and any(any(p.values()) for p in self.contact['pads'].values()):
            raise RuntimeError('Object contact already exists; explicit supported release is required before a new run')
        # A single quiet sample is insufficient while startup controllers are
        # settling. Match the independent guard's measured standstill window.
        history=[]
        def settled():
            now=time.monotonic()
            if not all(j in self.q and j in self.v and abs(self.v[j])<.003 for j in required):
                history.clear();return False
            history.append((now,np.array([self.q[j] for j in required])))
            while len(history)>1 and history[1][0]<now-.5:history.pop(0)
            return (now-history[0][0]>=.5 and
                    np.max(np.ptp([q for _,q in history],axis=0))<=.0009)
        self.wait(settled,30.)
        answer=self.call('reset',Trigger.Request())
        try:self.wait(lambda:not set(ARMS).intersection(self.supervisor.get('blocked_arms',[])),5.)
        except TimeoutError as error:
            raise RuntimeError('Owned arms remain interlocked after reset: '+answer.message) from error
        self.owned=True

    def activate_group(self):
        states=self.call('list',ListControllers.Request()).controller
        if any(c.name=='rigid_object_controller' and c.state=='active' for c in states):return
        deactivate=[c.name for c in states if c.state=='active' and c.name in [a+'_trajectory_controller' for a in ARMS]]
        req=SwitchController.Request();req.activate_controllers=['rigid_object_controller'];req.deactivate_controllers=deactivate
        req.strictness=2;req.timeout.sec=5
        response=self.call('switch',req)
        if not response.ok:raise RuntimeError('Common rigid-object controller activation rejected')

    def follow(self,trajectory,controller='rigid_object_controller',timeout=None):
        self.health();action=self.actions[controller]
        if not action.wait_for_server(timeout_sec=5.):raise RuntimeError('Missing action '+controller)
        goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=trajectory['joint_names']
        # Detect an unresponsive actuator during the path, not only at its
        # final endpoint. Rigid-group telemetry adds the tighter TCP corridor.
        goal.path_tolerance=[JointTolerance(name=j,position=.005) for j in trajectory['joint_names']]
        goal.goal_tolerance=[JointTolerance(name=j,position=.001) for j in trajectory['joint_names']]
        for entry in trajectory['points']:
            point=JointTrajectoryPoint();point.positions=list(entry['positions'])
            # Supplied derivatives preserve the shared object time law.
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
        profile=gripper_profile([start[a] for a in ARMS],target,self.cfg);duration=profile['duration_s']
        pending=[]
        for index,arm in enumerate(ARMS):
            goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=[gripper_joint(arm)]
            if target==0:
                goal.goal_tolerance=[JointTolerance(name=gripper_joint(arm),position=.02,velocity=.003)]
            for entry in profile['points']:
                p=JointTrajectoryPoint();p.positions=[entry['positions'][index]]
                ns=round(entry['time']*1e9);p.time_from_start.sec=ns//10**9;p.time_from_start.nanosec=ns%10**9
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
            self.wait(lambda:all(all(self.contact['pads'][a].values()) for a in ARMS),duration*5+10,health=True)
            self.call('latch',SetBool.Request(data=True))
            for h in handles:h.cancel_goal_async()
            preload_until=self.now()+max(2.,max(.8-self.q[gripper_joint(a)] for a in ARMS)/self.cfg['gripper_fine_velocity_rad_s']+2.)
            wall_deadline=time.monotonic()+180.
            while self.now()<preload_until:
                self.health()
                if time.monotonic()>wall_deadline:raise TimeoutError('Grip preload did not settle')
                time.sleep(.02)
            quiet_since=None
            def stable_contact():
                nonlocal quiet_since
                quiet=(all(all(self.contact['pads'][a].values()) for a in ARMS) and
                    all(abs(v)<.003 for j,v in self.v.items() if '_robotiq_' in j and j.startswith(ARMS)))
                if not quiet:quiet_since=None;return False
                if quiet_since is None:quiet_since=self.now()
                return self.now()-quiet_since>=.3
            self.wait(stable_contact,30.,health=True)
            write_json(self.stop_directory/'grasp-contact-confirmation.json',dict(
                source='simulation_contact_telemetry',stable_source_duration_s=self.now()-quiet_since,
                contacts=self.contact,positions={j:q for j,q in self.q.items() if '_robotiq_' in j and j.startswith(ARMS)},
                holding_reliability_proved=False))
        else:
            results=[h.get_result_async() for h in handles]
            self.wait(lambda:all(f.done() for f in results),duration*5+10,health=True)
            if any(f.result().result.error_code!=0 for f in results):raise RuntimeError('Open gripper action failed')
            quiet_since=None
            def open_measured():
                nonlocal quiet_since
                if not measured_open(self.finger_names,self.q,self.v):quiet_since=None;return False
                if quiet_since is None:quiet_since=self.now()
                return self.now()-quiet_since>=.3
            try:self.wait(open_measured,8.,health=True)
            except TimeoutError as error:raise RuntimeError('Actual finger positions did not confirm open grippers') from error
        for h in handles:
            if h in self.handles:self.handles.remove(h)

    def stop(self):
        report=dict(arms=list(ARMS),grip_release_commanded=False,confirmed=False)
        pending=[];errors=[]
        for h in list(self.handles):
            try:h.cancel_goal_async()
            except Exception as error:errors.append('cancel: '+str(error))
        # Send to every member before waiting; one missing reply must never
        # prevent requesting the other member's independent hold.
        for arm in ARMS:
            try:pending.append(self.service_clients['stop_'+arm].call_async(Trigger.Request()))
            except Exception as error:errors.append(arm+': '+str(error))
        if errors:report['request_errors']=errors
        try:
            self.wait(lambda:set(ARMS)<=set(self.supervisor.get('held_arms',[])) and
                time.monotonic()-self.supervisor_received<.4 and time.monotonic()-self.joint_received<.2 and
                all(abs(self.v.get(j,1))<.003 for a in ARMS for j in joint_names(a)),5.)
            states=self.call('list',ListControllers.Request()).controller
            report['confirmed']=all(any(c.name==a+'_collision_hold_controller' and c.state=='active' for c in states) for a in ARMS)
        except Exception as error:report['error']=str(error)
        return report

    def close(self):
        self.ros_executor.shutdown(timeout_sec=2.);self.thread.join(timeout=2.);self.destroy_node()


def await_review(store,sim,stage,evidence):
    sim.phase=stage
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
    with resource_lease(namespace):
        return _run_task(directory,scene_directory,layout_file,namespace,reference)


def _run_task(directory,scene_directory,layout_file,namespace,reference):
    directory=Path(directory).resolve();store=RunStore(directory)
    lock=(directory/'runner.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if store.state['state']!='CREATED':raise RuntimeError('A run is immutable after start; create a new run directory')
    scene_directory=Path(scene_directory);scene=verify_scene(scene_directory)
    cfg=scene['cfg'];layout=load_layout(layout_file);description=(scene_directory/'robot.urdf').read_text()
    sim=Simulation(namespace,scene_directory);sim.stop_directory=directory;sim.layout=layout;group=None
    try:
        sim.connect()
        sim.reset();sim.activate_group()
        # No pre-existing contact was accepted by reset. Establish the open
        # start explicitly before generating a wall-straddling approach.
        store.event('RUNNING','observe',step='open_unloaded_grippers')
        sim.grippers(0.)
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
            sim.phase='plan_approach';store.event('RUNNING','plan_approach')
            problem=TaskProblem(directory/f'planning-{attempt}',description,layout,scene,obj)
            failures=[];plan=None
            for candidate in candidates:
                try:
                    store.event('RUNNING','plan_approach',candidate_id=candidate['id'])
                    plan=plan_approach(problem,start,candidate)
                    witness=TaskProblem(directory/f'witness-{candidate["id"]}',description,layout,scene,obj,static=False)
                    pre_state=dict(start,**dict(zip(plan['request']['joint_names'],plan['request']['target'])))
                    entry,grasp_state=grasp_entry(witness,pre_state,candidate,cfg)
                    predicted=PlannedObjectConstraint(obj,candidate['tcp_targets'])
                    poses=carton_motion_poses(scene,layout,obj,cfg)
                    lifted=poses['lifted']
                    # This geometric witness is distinct from the actual
                    # contact-bound plan recomputed after grasp confirmation.
                    extra={}
                    if cfg.get('roll_long_axis') or cfg.get('force_comparison_lift'):
                        recipe=compile_object_recipe(witness,predicted,grasp_state,obj,cfg)
                        lift_witness=recipe['motions']['lift']
                        extra=dict(object_recipe_witness=recipe)
                    else:lift_witness=object_trajectory(witness,predicted,grasp_state,obj,lifted,cfg)
                    plan=seal(dict(plan,entry=entry,lift_witness=lift_witness,**extra))
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
            sim.phase='inspect_pregrasp';store.event('RUNNING','inspect_pregrasp')
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
            if not sim.contact['supported']:raise RuntimeError('Grasp entry requires a supported object')
            contact_problem=TaskProblem(directory/'contact-plan',description,layout,scene,obj,static=False)
            entry,_=grasp_entry(contact_problem,dict(sim.q),plan['candidate'],cfg)
            store.event('RUNNING','grasp',step='checked_entry')
            sim.follow(entry)
            if not sim.contact['supported']:raise RuntimeError('Contact closure requires a supported object')
            store.event('RUNNING','grasp',step='contact_closure_and_preload')
            sim.grippers(.8)
            # Use visual pose and actual TCPs, not a synthetic attachment.
            grasp_observation=observe(sim,description,reference,directory/'grasp-observation')
            obj=np.array(grasp_observation['T_world_object'])
            tcps={a:contact_problem.chains[a].forward(sim.q) for a in ARMS}
            sim.phase='form_group';store.event('RUNNING','form_group')
            group=GraspGroup(cfg['object_id'],obj,tcps,sim.contact['pads'],cfg,plan['candidate']['contacts'])
            record=group.record();write_json(directory/'group.json',record)
            sim.group_pub.publish(String(data=json.dumps(record,default=lambda v:v.tolist())))
            poses=carton_motion_poses(scene,layout,obj,cfg)
            write_json(directory/'object-targets.json',seal(poses))
            lifted=poses['lifted']
            sim.phase='move_object';store.event('RUNNING','move_object')
            recipe=compile_object_recipe(contact_problem,group,dict(sim.q),obj,cfg) if (cfg.get('roll_long_axis') or cfg.get('force_comparison_lift')) else None
            if recipe:write_json(directory/'object-recipe.json',seal(recipe))
            trajectory=recipe['motions']['lift'] if recipe else object_trajectory(contact_problem,group,dict(sim.q),obj,lifted,cfg)
            truth_before=np.array(sim.object['T_world_object'])
            write_json(directory/'object-lift.json',trajectory);sim.follow(trajectory)
            truth=np.array(sim.object['T_world_object'])
            truth_start=truth_before
            reference=scene['lift_reference_point_object_m']
            actual_hub=object_point_height(truth,reference)-object_point_height(truth_start,reference)
            if sim.contact['supported'] or abs(actual_hub-poses['lift_m'])>.002:
                raise RuntimeError('Actual load pickup was not established')
            end=sim.now()+cfg['dwell_s'];wall_deadline=time.monotonic()+30.
            while sim.now()<end:
                sim.health()
                if time.monotonic()>wall_deadline:raise TimeoutError('Simulation dwell did not complete')
                if sim.contact['supported']:raise RuntimeError('Support contact during free hold')
                time.sleep(.02)
            carried=lifted
            if 'turned' in poses:
                # Keep the existing move_object guard phase throughout rotation.
                store.event('RUNNING','move_object',step='longitudinal_quarter_turn')
                turn=recipe['motions']['turn']
                write_json(directory/'object-turn.json',turn);sim.follow(turn)
                carried=poses['turned']
                measured=np.asarray(sim.object['T_world_object'])
                if pose_error(measured,carried)[1]>.0174533 or sim.contact['supported']:
                    raise RuntimeError('Unsupported quarter-turn orientation was not established')
            sim.phase='set_down';store.event('RUNNING','set_down')
            back=recipe['motions']['set_down'] if recipe else object_trajectory(contact_problem,group,dict(sim.q),carried,poses['placed'],cfg)
            write_json(directory/'object-set-down.json',back);sim.follow(back)
            sim.wait(lambda:sim.contact['supported'],5.,health=True)
            if cfg.get('roll_long_axis') and pose_error(sim.object['T_world_object'],poses['placed'])[1]>.0174533:
                raise RuntimeError('Supported sideways orientation differs from target')
            release_request=dict(group.record(),release_requested=True)
            sim.group_pub.publish(String(data=json.dumps(release_request,default=lambda v:v.tolist())))
            sim.call('latch',SetBool.Request(data=False));sim.phase='release';store.event('RUNNING','release');sim.grippers(0.)
            sim.wait(lambda:not any(any(sim.contact['pads'][a].values()) for a in ARMS)
                and all(sim.q[gripper_joint(a)]<.02 for a in ARMS),10.,health=True)
            time.sleep(.5)
            sim.wait(lambda:sim.guard.get('group_stationary') is True,10.,health=True)
            stationary=all(abs(sim.v.get(j,float('inf')))<.003 for a in ARMS for j in joint_names(a))
            group.release(supported=bool(sim.contact['supported']),stationary=stationary)
            sim.group_pub.publish(String(data=json.dumps(group.record(),default=lambda v:v.tolist())))
            sim.wait(lambda:sim.guard.get('active_grasp_members')==[],5.,health=True)
            stop_report=sim.stop()
            if not stop_report['confirmed']:raise RuntimeError('Final resource holds not confirmed')
            if cfg.get('roll_long_axis') and (not sim.contact['supported'] or
                    pose_error(sim.object['T_world_object'],poses['placed'])[1]>.0174533):
                raise RuntimeError('Released carton did not retain supported sideways orientation')
            write_json(directory/'object-targets.json',seal(poses))
            store.event('DONE','done',group=group.record(),actual_hub_m=actual_hub,
                asset_origin_hub_m=float(truth[2,3]-truth_start[2,3]),
                lift_reference_point_object_m=reference,lift_reference_kind=scene['lift_reference_kind'],stop=stop_report,
                physically_attached=False,assumptions=cfg['simulation_assumptions'],measured_peak_speeds_rad_s=sim.measured_peaks)
            sim.phase='done';sim.heartbeat();sim.owned=False
            return store.state
        raise RuntimeError('Review/replanning attempt budget exhausted')
    except BaseException as error:
        # Preserve the primary fault before stopping changes the diagnosis
        # to secondary cancellation/runner-loss messages.
        write_json(directory/'stop-diagnostic.json',dict(error=str(error),phase=sim.phase,
            reception_ages_wall_s={k:time.monotonic()-getattr(sim,k+'_received')
                for k in ('joint','guard','supervisor','object','contact')},executor_thread_alive=sim.thread.is_alive(),
            guard=sim.guard,supervisor=sim.supervisor,positions=sim.q,velocities=sim.v,
            contact=sim.contact,object_truth_evaluation_only=sim.object,measured_peak_speeds_rad_s=sim.measured_peaks))
        report=sim.stop()
        store.event('FAILED',sim.phase,error=str(error),stop=report)
        raise
    finally:
        sim.close();fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

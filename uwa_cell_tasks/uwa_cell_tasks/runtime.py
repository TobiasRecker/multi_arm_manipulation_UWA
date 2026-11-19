"""ROS simulation adapter. One action controller owns the whole rigid group."""
import fcntl
import json
from pathlib import Path
import threading
import time
import numpy as np
import rclpy
from uwa_cell_motion.node import MotionNode
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger,SetBool
from controller_manager_msgs.srv import SwitchController,ListControllers
from control_msgs.action import FollowJointTrajectory
from uwa_cell_gazebo.trajectory import trajectory_goal
from action_msgs.msg import GoalStatus
from uwa_cell_description.configuration import load_layout,joint_names,gripper_joint
from uwa_cell_motion.common import simulation_only
from match_cooperative_handling.rigid_object import pose_error
from .core import ARMS,RunStore,GraspGroup,verify,write_json,seal,resource_lease,gripper_profile,object_point_height
from .planning import TaskProblem,grasp_candidates,plan_approach,object_trajectory,grasp_entry,PlannedObjectConstraint,carton_motion_poses,compile_object_recipe
from .scene import verify_scene


class Simulation(MotionNode):
    motion_arms = ARMS
    def __init__(self,namespace,scene_directory):
        simulation_only()
        if not namespace.startswith('/uwa_grasp_'):raise ValueError('An isolated /uwa_grasp_* simulation namespace is required')
        super().__init__('task_runner',namespace=namespace,
            cli_args=['--ros-args','-r','/clock:='+namespace+'/clock'])
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
        self.directory=Path(scene_directory)
        self.stop_directory=self.directory
        self.q={}
        self.cfg=json.loads((self.directory/'scene.json').read_text())['cfg']
        self.motion_arms = (*ARMS, 'left_front') if self.cfg.get('drawing_recipe') else ARMS
        self.contact=None
        self.object=None
        self.phase='observe'
        self.handles=[]
        self.pending_goals=[]
        self.create_subscription(JointState,namespace+'/joint_states',self.joints,qos_profile_sensor_data)
        for topic,key in [('tasks/contacts','contact'),('tasks/object_truth','object')]:
            self.create_subscription(String,namespace+'/'+topic,lambda msg,k=key:setattr(self,k,json.loads(msg.data)),
                qos_profile_sensor_data)
        self.group_pub=self.create_publisher(String,'tasks/group',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.service_clients={key:self.create_client(kind,namespace+'/'+topic) for key,kind,topic in [
            ('switch',SwitchController,'controller_manager/switch_controller'),
            ('list',ListControllers,'controller_manager/list_controllers'),('latch',SetBool,'tasks/grip_latch'),
            ('capture',Trigger,'tasks/camera_capture')]}
        self.actions={name:ActionClient(self,FollowJointTrajectory,namespace+'/'+name+'/follow_joint_trajectory')
            for name in ['rigid_object_controller']+[a+'_gripper_controller' for a in ARMS]}
        # A fixed single executor prevents ready /clock callbacks from piling
        # up ahead of controller RPC replies in a multithreaded work queue.
        self.ros_executor=SingleThreadedExecutor();self.ros_executor.add_node(self)
        self.thread=threading.Thread(target=self.ros_executor.spin,daemon=True);self.thread.start()

    def joints(self,msg):
        self.q=dict(zip(msg.name,msg.position))

    def now(self):
        return self.get_clock().now().nanoseconds/1e9

    def check_cancel(self):
        if (self.stop_directory/'STOP').exists():
            raise RuntimeError('STOP requested')

    def wait(self,predicate,timeout=10.,*,cancellable=True):
        end=time.monotonic()+timeout
        while True:
            if cancellable:self.check_cancel()
            if predicate():return
            if time.monotonic()>end:raise TimeoutError('Simulation response timed out')
            time.sleep(.01)

    def call(self,key,request,timeout=8.):
        client=self.service_clients[key]
        if not client.wait_for_service(timeout_sec=timeout):raise RuntimeError('Missing service '+key)
        # Only this read-only query is replayed after a missing transport reply.
        # Controller switches, latches and captures are never retried here.
        for attempt in range(2 if key=='list' else 1):
            future=client.call_async(request)
            try:self.wait(future.done,timeout);break
            except TimeoutError:
                client.remove_pending_request(future)
                if key!='list' or attempt:raise
        result=future.result()
        if hasattr(result,'success') and not result.success:raise RuntimeError(result.message)
        return result

    def connect(self):
        required=[j for a in self.motion_arms for j in joint_names(a)]
        required.extend(gripper_joint(a) for a in ARMS)
        self.wait(lambda:all(j in self.q for j in required) and self.object is not None and self.contact is not None,30.)

    def activate_group(self):
        states=self.call('list',ListControllers.Request()).controller
        if any(c.name=='rigid_object_controller' and c.state=='active' for c in states):return
        deactivate=[c.name for c in states if c.state=='active' and c.name in [a+'_trajectory_controller' for a in self.motion_arms]]
        req=SwitchController.Request();req.activate_controllers=['rigid_object_controller'];req.deactivate_controllers=deactivate
        req.strictness=2;req.timeout.sec=5
        response=self.call('switch',req)
        if not response.ok:raise RuntimeError('Common rigid-object controller activation rejected')

    def send_goal(self, controller, trajectory):
        self.check_cancel()
        action=self.actions[controller]
        if not action.wait_for_server(timeout_sec=5.):raise RuntimeError('Missing action '+controller)
        future=action.send_goal_async(trajectory_goal(trajectory))
        self.pending_goals.append(future)
        return future

    def accept_goals(self, futures):
        self.wait(lambda:all(f.done() for f in futures),5.)
        handles=[]
        for future in futures:
            handle=future.result()
            self.pending_goals.remove(future)
            if handle.accepted:
                self.handles.append(handle)
                handles.append(handle)
        if len(handles)!=len(futures):raise RuntimeError('Trajectory action was rejected')
        return handles

    def wait_results(self, handles, timeout):
        results=[handle.get_result_async() for handle in handles]
        self.wait(lambda:all(f.done() for f in results),timeout)
        for future in results:
            response=future.result()
            if response.status!=GoalStatus.STATUS_SUCCEEDED or response.result.error_code!=0:
                raise RuntimeError('Action failed: '+response.result.error_string)
        for handle in handles:
            self.handles.remove(handle)

    def follow(self,trajectory,controller='rigid_object_controller',timeout=None,*,fixed_positions=None):
        if self.cfg.get('drawing_recipe') and controller=='rigid_object_controller':
            missing=[j for arm in self.motion_arms for j in joint_names(arm)
                     if j not in trajectory['joint_names']]
            if missing:
                held=[fixed_positions[j] for j in missing]
                trajectory = dict(trajectory,joint_names=trajectory['joint_names']+missing,
                    points=[dict(point,positions=list(point['positions'])+held,
                        **{key:list(point[key])+[0.]*len(missing)
                           for key in ('velocities','accelerations') if key in point})
                        for point in trajectory['points']])
        handles=self.accept_goals([self.send_goal(controller,trajectory)])
        self.wait_results(handles,timeout or trajectory['points'][-1]['time']*5+10)

    def grippers(self,target):
        states=self.call('list',ListControllers.Request()).controller
        needed=[a+'_gripper_controller' for a in ARMS]
        activate=[n for n in needed if not any(c.name==n and c.state=='active' for c in states)]
        if activate:
            req=SwitchController.Request();req.activate_controllers=activate;req.strictness=2;req.timeout.sec=5
            if not self.call('switch',req).ok:raise RuntimeError('Gripper activation rejected')
        profile=gripper_profile([self.q[gripper_joint(a)] for a in ARMS],target,self.cfg)
        pending=[]
        for index,arm in enumerate(ARMS):
            trajectory=dict(joint_names=[gripper_joint(arm)],
                points=[dict(time=p['time'],positions=[p['positions'][index]]) for p in profile['points']])
            pending.append(self.send_goal(arm+'_gripper_controller',trajectory))
        handles=self.accept_goals(pending)
        timeout=profile['duration_s']*5+10
        if target>0:
            # Pad contact is the event that commands the physical grip latch.
            self.wait(lambda:all(all(self.contact['pads'][a].values()) for a in ARMS),timeout)
            self.call('latch',SetBool.Request(data=True))
            cancellations=[h.cancel_goal_async() for h in handles]
            self.wait(lambda:all(f.done() for f in cancellations),5.)
            for handle in handles:
                self.handles.remove(handle)
            self.dwell(max(2.,max(.8-self.q[gripper_joint(a)] for a in ARMS)
                /self.cfg['gripper_fine_velocity_rad_s']+2.),180.)
            write_json(self.stop_directory/'grasp-contact-confirmation.json',dict(
                source='simulation_contact_telemetry',contacts=self.contact))
        else:
            self.wait_results(handles,timeout)

    def dwell(self,duration,timeout):
        end=self.now()+duration
        self.wait(lambda:self.now()>=end,timeout)

    def cancel(self):
        report=dict(requested_goals=0,acknowledged_goals=0,errors=[])
        for future in self.pending_goals:
            try:
                self.wait(future.done,2.,cancellable=False)
                if future.result().accepted:self.handles.append(future.result())
            except Exception as error:
                report['errors'].append(str(error))
        requests=[]
        for handle in self.handles:
            try:requests.append(handle.cancel_goal_async())
            except Exception as error:report['errors'].append(str(error))
        report['requested_goals']=len(self.handles)
        try:self.wait(lambda:all(f.done() for f in requests),5.,cancellable=False)
        except TimeoutError as error:report['errors'].append(str(error))
        for future in requests:
            if future.done():
                try:report['acknowledged_goals']+=bool(future.result().goals_canceling)
                except Exception as error:report['errors'].append(str(error))
        return report

    def close(self):
        self.ros_executor.shutdown(timeout_sec=2.);self.thread.join(timeout=2.);self.destroy_node()


def await_review(store,sim,stage,evidence):
    sim.phase=stage
    packet=store.request_review(stage,evidence);end=time.monotonic()+300.
    while time.monotonic()<end:
        sim.check_cancel()
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
    sim=Simulation(namespace,scene_directory);sim.stop_directory=directory
    drawing = None
    if cfg.get('drawing_recipe'):
        from .contact_drawing import ContactDrawing
        drawing = ContactDrawing(cfg['drawing_recipe'])
    try:
        sim.connect()
        sim.activate_group()
        if any(any(p.values()) for p in sim.contact['pads'].values()):
            raise RuntimeError('A new grasp needs a box outside the grippers')
        store.event('RUNNING','observe',step='open_unloaded_grippers')
        sim.grippers(0.)
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
                    plan=plan_approach(problem,start,candidate, branch_seed=drawing.branch if drawing else None)
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
            sim.phase='approach';store.event('RUNNING','approach');sim.follow(plan['trajectory'],fixed_positions=start)
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
            contact_problem=TaskProblem(directory/'contact-plan',description,layout,scene,obj,static=False)
            entry_start=dict(sim.q)
            entry,_=grasp_entry(contact_problem,entry_start,plan['candidate'],cfg)
            store.event('RUNNING','grasp',step='checked_entry')
            sim.follow(entry,fixed_positions=entry_start)
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
            if drawing:
                drawing.compile(contact_problem, group, dict(sim.q), obj, directory, check_cancel=sim.check_cancel)
                lifted = drawing.lifted
                poses.update(lifted=lifted, placed=obj,
                    lift_m=object_point_height(lifted,scene['lift_reference_point_object_m'])
                           - object_point_height(obj,scene['lift_reference_point_object_m']))
                write_json(directory/'object-targets.json',seal(poses))
            recipe=compile_object_recipe(contact_problem,group,dict(sim.q),obj,cfg) if (cfg.get('roll_long_axis') or cfg.get('force_comparison_lift')) else None
            if recipe:write_json(directory/'object-recipe.json',seal(recipe))
            trajectory=drawing.trajectories[0] if drawing else recipe['motions']['lift'] if recipe else object_trajectory(contact_problem,group,dict(sim.q),obj,lifted,cfg)
            carried=poses.get('turned',lifted)
            if drawing:
                back=drawing.trajectories[-1]
            elif recipe:
                back=recipe['motions']['set_down']
            else:
                lifted_state=dict(sim.q,**dict(zip(trajectory['joint_names'],trajectory['points'][-1]['positions'])))
                back=object_trajectory(contact_problem,group,lifted_state,carried,poses['placed'],cfg)
            write_json(directory/'object-lift.json',trajectory)
            write_json(directory/'object-set-down.json',back)
            truth_start=np.array(sim.object['T_world_object'])
            sim.follow(trajectory,timeout=trajectory['duration_s']*12+20 if drawing else None)
            truth=np.array(sim.object['T_world_object'])
            lift_reference=scene['lift_reference_point_object_m']
            actual_hub=object_point_height(truth,lift_reference)-object_point_height(truth_start,lift_reference)
            sim.dwell(cfg['dwell_s'],30.)
            if drawing:
                for path in drawing.trajectories[1:-1]:
                    store.event('RUNNING','move_object',step=path['phase'])
                    sim.follow(path,timeout=path['duration_s']*12+20)
            if 'turned' in poses:
                store.event('RUNNING','move_object',step='longitudinal_quarter_turn')
                turn=recipe['motions']['turn']
                write_json(directory/'object-turn.json',turn)
                sim.follow(turn)
            sim.phase='set_down';store.event('RUNNING','set_down')
            sim.follow(back,timeout=back['duration_s']*12+20 if drawing else None)
            release_request=dict(group.record(),release_requested=True)
            sim.group_pub.publish(String(data=json.dumps(release_request,default=lambda v:v.tolist())))
            sim.call('latch',SetBool.Request(data=False));sim.phase='release';store.event('RUNNING','release');sim.grippers(0.)
            group.release()
            sim.group_pub.publish(String(data=json.dumps(group.record(),default=lambda v:v.tolist())))
            store.event('DONE','done',group=group.record(),actual_hub_m=actual_hub,
                asset_origin_hub_m=float(truth[2,3]-truth_start[2,3]),
                lift_reference_point_object_m=lift_reference,lift_reference_kind=scene['lift_reference_kind'],
                physically_attached=False,assumptions=cfg['simulation_assumptions'])
            return store.state
        raise RuntimeError('Review/replanning attempt budget exhausted')
    except BaseException as error:
        write_json(directory/'stop-diagnostic.json',dict(error=str(error),phase=sim.phase,
            positions=sim.q,contact=sim.contact,object_truth_evaluation_only=sim.object))
        store.event('FAILED',sim.phase,error=str(error),cancellation=sim.cancel())
        raise
    finally:
        sim.close();fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

"""Opt-in Domain67 integration with four fake managers; no real robot sockets.

Uses real ROS services/actions, hardware guard/supervisor/witness and executor.
Fake managers emulate interface ownership, not UR dynamics or stop latency.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import numpy as np
import yaml
import rclpy
from rclpy.action import ActionServer
from rclpy.action.server import GoalResponse,CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile,DurabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectory
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers,SwitchController,ListHardwareComponents
from controller_manager_msgs.msg import ControllerState,HardwareComponentState,HardwareInterface
from rcl_interfaces.srv import GetParameters
from rcl_interfaces.msg import ParameterValue
from uwa_cell_motion.common import config,nominal_state,ROBOT_IDS,joint_names,dump
from uwa_cell_motion.node import MotionNode
from uwa_cell_motion.hardware_model import HardwareProblem,inventory_path
from uwa_cell_motion.hardware_nodes import HardwareGuard,HardwareSupervisor,HardwareWatchdog
from uwa_cell_motion.hardware_execution import HardwareClient,execute
from uwa_cell_motion.hardware_ports import HOLD
from uwa_cell_motion.hardware_state import require_domain


class FakeManager(MotionNode):
    def __init__(self,p,model,cfg):
        super().__init__('controller_manager',namespace=p['namespace']);self.p=p;self.cfg=cfg;self.names=p['joint_names'];self.lock=threading.RLock()
        state=nominal_state(model.layout);self.q=np.array([state[j] for j in self.names]);self.v=np.zeros(6)
        self.states={HOLD:'inactive','joint_trajectory_controller':'inactive','custom_owner':'inactive'};self.switch_calls=0;self.freeze=False;self.last_stamp=None
        self.plugin='mock_components/GenericSystem';self.deceleration=cfg['braking_acceleration_rad_s2']
        self.pub=self.create_publisher(JointState,p['namespace']+'/joint_states',10)
        self.description=self.create_publisher(String,p['namespace']+'/robot_description',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.description.publish(String(data=model.original_description))
        self.create_service(ListControllers,'~/list_controllers',self.list)
        self.create_service(SwitchController,'~/switch_controller',self.switch)
        self.create_service(ListHardwareComponents,'~/list_hardware_components',self.hardware)
        self.create_service(GetParameters,p['namespace']+'/'+HOLD+'/get_parameters',self.params)
        self.create_subscription(JointTrajectory,p['namespace']+'/joint_trajectory_controller/joint_trajectory',self.topic,10)
        self.create_timer(.02,self.tick)
        self.server=ActionServer(self,FollowJointTrajectory,p['namespace']+'/joint_trajectory_controller/follow_joint_trajectory',
            execute_callback=self.run,goal_callback=lambda request:GoalResponse.ACCEPT if self.states['joint_trajectory_controller']=='active' else GoalResponse.REJECT,
            cancel_callback=lambda handle:CancelResponse.ACCEPT,callback_group=ReentrantCallbackGroup())
    def list(self,request,response):
        with self.lock:
            for name,state in self.states.items():
                response.controller.append(ControllerState(name=name,state=state,type='uwa_cell_motion/CollisionHold' if name==HOLD else 'test/Controller',
                    claimed_interfaces=[j+'/position' for j in self.names] if state=='active' else []))
        return response
    def switch(self,request,response):
        with self.lock:
            wanted=dict(self.states)
            for name in request.deactivate_controllers:
                if name in wanted:wanted[name]='inactive'
            for name in request.activate_controllers:
                if name not in wanted:response.ok=False;return response
                wanted[name]='active'
            if sum(s=='active' for s in wanted.values())>1:response.ok=False;return response
            self.states=wanted;self.switch_calls+=1
            if self.states[HOLD]=='active':self.v=np.zeros(6)
            response.ok=True;return response
    def hardware(self,request,response):
        response.component=[HardwareComponentState(name='test',type='system',plugin_name=self.plugin,
            command_interfaces=[HardwareInterface(name=j+'/position') for j in self.names])];return response
    def params(self,request,response):
        response.values=[ParameterValue(type=9,string_array_value=self.names) if name=='joints' else ParameterValue(type=3,double_value=self.deceleration) for name in request.names]
        return response
    def topic(self,msg):
        if self.states['joint_trajectory_controller']=='active' and msg.points:
            # Only used to verify that a blocked topic cannot change position.
            with self.lock:self.q=np.asarray(msg.points[-1].positions);self.v=np.zeros(6)
    def tick(self):
        msg=JointState()
        with self.lock:
            if not self.freeze or self.last_stamp is None:self.last_stamp=self.get_clock().now().to_msg()
            msg.header.stamp=self.last_stamp;msg.name=self.names;msg.position=self.q.tolist();msg.velocity=self.v.tolist()
        self.pub.publish(msg)
    def run(self,handle):
        trajectory=handle.request.trajectory;points=trajectory.points
        times=np.array([p.time_from_start.sec+p.time_from_start.nanosec/1e9 for p in points]);q=np.asarray([p.positions for p in points]);v=np.asarray([p.velocities for p in points])
        requested=trajectory.header.stamp.sec+trajectory.header.stamp.nanosec/1e9;began=max(time.time(),requested)
        result=FollowJointTrajectory.Result()
        while rclpy.ok():
            with self.lock:
                if self.states['joint_trajectory_controller']!='active':self.v=np.zeros(6);handle.abort();result.error_code=-1;return result
                if handle.is_cancel_requested:self.v=np.zeros(6);handle.canceled();result.error_code=0;return result
                elapsed=max(0,time.time()-began)
                self.q=np.array([np.interp(elapsed,times,q[:,i]) for i in range(6)])
                self.v=np.array([np.interp(elapsed,times,v[:,i]) for i in range(6)])
                if elapsed>=times[-1]:self.q=q[-1];self.v=np.zeros(6);handle.succeed();result.error_code=0;return result
            time.sleep(.01)
        return result


class TestGuard(HardwareGuard):
    def __init__(self,*args,**kwargs):self.fault_pairs=set();super().__init__(*args,**kwargs)
    def update(self,now):
        world,available=super().update(now)
        for i in self.fault_pairs:self.pairs[i]['clearance_m']=self.pairs[i]['threshold_m']-.001
        return world,available


def check(output,config_path=None):
    require_domain('mock');result={};rclpy.init();executor=None;worker=None;roles=[];managers=[];client=None
    # Accidental real network access is an immediate test failure in this process.
    previous=socket.create_connection
    def forbidden(*args,**kwargs):raise AssertionError('Mock backend attempted a robot TCP connection')
    socket.create_connection=forbidden
    with tempfile.TemporaryDirectory(prefix='uwa-hardware-mock-') as directory:
        try:
            inventory=yaml.safe_load(inventory_path().read_text());inventory['ros_namespace']='/uwa_motion_validation'
            from match_ur_hardware.profiles import load_profiles
            originals=load_profiles(inventory_path())
            for index,(rid,p) in enumerate(inventory['robots'].items()):p['ip']='127.0.0.'+str(index+2);p['kinematics_file']=originals[rid]['kinematics_file']
            file=Path(directory)/'inventory.yaml';file.write_text(yaml.safe_dump(inventory));cfg=config(config_path or Path(__file__).parents[1]/'config/hardware_motion.yaml')
            model=HardwareProblem(Path(directory)/'model',cfg,file)
            managers=[FakeManager(p,model,cfg) for p in model.profiles.values()];byid={m.p['id']:m for m in managers}
            def start(armed):
                nonlocal executor,worker,roles
                roles=[TestGuard(cfg,file,mode='mock',armed=armed),HardwareSupervisor(cfg,file,mode='mock',armed=armed),HardwareWatchdog(cfg,file,mode='mock',armed=armed)]
                executor=MultiThreadedExecutor(num_threads=12)
                for node in managers+roles:executor.add_node(node)
                worker=threading.Thread(target=executor.spin,daemon=True);worker.start()
            def close():
                nonlocal executor,worker,roles
                if executor:executor.shutdown(timeout_sec=3.);worker.join(timeout=3.)
                for node in roles:node.destroy_node()
                roles=[]
            start(False);time.sleep(1.)
            assert not any(m.switch_calls for m in managers);result['monitor_has_no_controller_or_native_commands']=True
            close();start(True)
            client=HardwareClient(model,'mock',['left_front','right_front','left_rear'])
            client.connect(guard=False)
            client.wait(lambda:set(client.supervisor['held_arms'])==set(ROBOT_IDS),10.)
            def wait(seconds):
                end=time.monotonic()+seconds;client.wait(lambda:time.monotonic()>=end,seconds+2.)
            def reset():
                stable_since=[None]
                def ready():
                    now=time.monotonic();ports=client.supervisor.get('ports',{})
                    healthy=(not client.guard.get('faults') and set(client.guard.get('stationary_arms',[]))==set(ROBOT_IDS)
                        and client.supervisor.get('witness_available') and len(ports)==4
                        and all(p['manager_fresh'] and p['hardware_mode_verified'] and p['hold_config_verified'] for p in ports.values()))
                    if not healthy:stable_since[0]=None;return False
                    if stable_since[0] is None:stable_since[0]=now
                    return now-stable_since[0]>=.7
                # Recovery deliberately needs a fresh stable observation window;
                # re-adding an executor node can leave queued stale callbacks.
                # Never extend production freshness limits to accommodate that.
                # A valid reset can release a subset when one arm's sampling
                # window is not eligible at the RPC instant. This fake-only
                # fixture explicitly requests the remainder after renewed
                # stable preconditions; production never retries a reset.
                for attempt in range(3):
                    client.wait(ready,8.)
                    answer=client.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request())
                    assert answer.success,answer.message
                    try:
                        client.wait(lambda:not client.supervisor['blocked_arms'] and not client.supervisor['held_arms'],1.)
                        break
                    except TimeoutError:
                        if attempt==2:raise
                        stable_since[0]=None
            reset();client.health();start_q=dict(client.positions);arms=['left_front','right_front','left_rear']
            # ACK records the last fallback, including the startup latch;
            # clear only the fixture's historical flag before this assertion.
            roles[1].ports['right_rear'].native_ack=False
            answer=client.service(Trigger,'/uwa_cell/collision_supervisor/right_rear/stop',Trigger.Request());assert answer.success
            client.wait(lambda:client.supervisor['held_arms']==['right_rear'],5.);wait(1.3)
            assert not client.supervisor['ports']['right_rear']['native_stop_ack']
            result['explicit_arm_hold_uses_its_own_measured_standstill']=True;reset()
            client.activate(arms);timer=threading.Timer(.7,lambda:roles[0].fault_pairs.add(0));timer.start()
            try:stops=client.phase({r:np.array([start_q[j] for j in joint_names(r)])+np.array([0,0,0,0,0,.02]) for r in arms},cfg,set())
            finally:timer.cancel()
            assert stops=={'left_front','right_front'},stops
            assert abs(client.positions[joint_names('left_rear')[-1]]-start_q[joint_names('left_rear')[-1]]-.02)<.001
            assert set(client.supervisor['held_arms'])=={'left_front','right_front'}
            result['pair_stop_independent_arm_finishes']=True
            roles[0].fault_pairs.clear();wait(.4);assert set(client.supervisor['blocked_arms'])=={'left_front','right_front'}
            controller=byid['left_front'];before=controller.q.copy();message=JointTrajectory();message.joint_names=controller.names
            from trajectory_msgs.msg import JointTrajectoryPoint
            message.points=[JointTrajectoryPoint(positions=(before+.02).tolist())]
            publisher=client.create_publisher(JointTrajectory,controller.p['namespace']+'/joint_trajectory_controller/joint_trajectory',10)
            publisher.publish(message);wait(.15);assert np.max(abs(controller.q-before))<1e-8
            request=SwitchController.Request();request.activate_controllers=['joint_trajectory_controller']
            assert not client.manager('left_front',SwitchController,'switch_controller',request).ok
            result['topic_and_resource_activation_blocked']=True;result['no_auto_resume']=True
            reset();roles[0].fault_pairs.update({0,1});client.wait(lambda:set(client.supervisor['held_arms'])=={'left_front','right_front','left_rear'},5.)
            result['simultaneous_pair_union']=True;roles[0].fault_pairs.clear();reset()
            byid['left_front'].freeze=True;client.wait(lambda:set(client.supervisor['held_arms'])=={'left_front','right_front','left_rear'},5.)
            result['frozen_device_source_neighbor_scope']=True
            answer=client.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request());assert answer.success,answer.message
            client.wait(lambda:set(client.supervisor['blocked_arms'])=={'left_front','right_front','left_rear'},3.);result['partial_reset_is_scoped']=True
            byid['left_front'].freeze=False;reset()
            executor.remove_node(roles[0]);client.wait(lambda:set(client.supervisor['held_arms'])==set(ROBOT_IDS),3.);result['guard_loss_stops_all']=True
            executor.add_node(roles[0]);wait(.7);assert client.supervisor['blocked_arms'];reset()
            bad=byid['left_front'];count=bad.switch_calls;bad.plugin='ur_robot_driver/URPositionHardwareInterface'
            client.wait(lambda:set(client.supervisor['blocked_arms'])=={'left_front','right_front','left_rear'},3.)
            assert bad.switch_calls==count;result['mock_refuses_real_plugin_without_controller_commands']=True
            bad.plugin='mock_components/GenericSystem';wait(.4);reset()
            bad.deceleration=99.;client.wait(lambda:set(client.supervisor['blocked_arms'])=={'left_front','right_front','left_rear'},3.)
            wait(.2);answer=client.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request());assert answer.success
            client.wait(lambda:set(client.supervisor['blocked_arms'])=={'left_front','right_front','left_rear'},3.)
            result['changed_hold_bounds_stay_latched_during_independent_partial_reset']=True;bad.deceleration=cfg['braking_acceleration_rad_s2'];wait(.4);reset()
            # Watchdog, not the client, must acquire resources when supervisor dies.
            request=SwitchController.Request();request.activate_controllers=['joint_trajectory_controller']
            assert client.manager('right_rear',SwitchController,'switch_controller',request).ok
            goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=joint_names('right_rear');q=byid['right_rear'].q.copy();velocity=np.array([0,0,0,0,0,.005])
            from trajectory_msgs.msg import JointTrajectoryPoint
            first=JointTrajectoryPoint(positions=q.tolist(),velocities=velocity.tolist());last=JointTrajectoryPoint(positions=(q+np.array([0,0,0,0,0,.02])).tolist(),velocities=velocity.tolist());last.time_from_start.sec=4;goal.trajectory.points=[first,last]
            future=client.actions['right_rear'].send_goal_async(goal);client.wait(future.done,3.);assert future.result().accepted;wait(.2)
            assert byid['right_rear'].q[-1]>q[-1]+.0001
            executor.remove_node(roles[1]);client.wait(lambda:roles[2].tripped and all(m.states[HOLD]=='active' for m in managers),3.)
            assert roles[0].supervisor.fresh(time.monotonic(),cfg['heartbeat_timeout_s']) is False
            result['supervisor_loss_independent_watchdog_owns_all_resources']=True
            stopped=byid['right_rear'].q.copy();wait(.2);assert np.max(abs(byid['right_rear'].q-stopped))<1e-8
            result['supervisor_loss_stops_active_motion_without_client_fallback']=True
            executor.add_node(roles[1]);wait(.7);assert client.supervisor['blocked_arms'];reset()
            executor.remove_node(roles[2]);client.wait(lambda:set(client.supervisor['held_arms'])==set(ROBOT_IDS),3.)
            result['watchdog_loss_latches_supervisor']=True;executor.add_node(roles[2]);wait(.7);reset()
            client.destroy_node();client=None
            # Both methods use actual backend state and the same validated model.
            reader=HardwareClient(model,'mock');reader.connect(guard=False);reader.health();start_q=dict(reader.positions);reader.destroy_node()
            for method in ('rrtconnect','circular'):
                target=[start_q[j] for j in joint_names('right_rear')];target[-1]+=.003
                request=Path(directory)/(method+'-request.json');dump(request,dict(start=start_q,goals={'right_rear':target},hardware_binding=model.binding,execution_mode='mock'))
                planfile=Path(output).with_name(Path(output).stem+'-'+method+'-plan.json');path=Path(output).with_name(Path(output).stem+'-'+method+'.json')
                script=Path(__file__).parents[1]/'scripts/cell_hardware_motion'
                base=[sys.executable,str(script),'--mode','mock','--inventory',str(file),'--config',str(Path(__file__).parents[1]/'config/hardware_motion.yaml')]
                # Production geometry/stop processes must not share the GIL of
                # offline MoveIt/model loading or planning/execution clients.
                planprocess=subprocess.run(base+['plan',str(request),'--method',method,'--output',str(planfile)],capture_output=True,text=True,timeout=30.)
                assert planprocess.returncode==0,planprocess.stdout+planprocess.stderr
                process=subprocess.run(base+['execute',str(planfile),'--output',str(path)],capture_output=True,text=True,timeout=30.)
                execution=json.loads(path.read_text());assert execution['success'],execution.get('error') or process.stdout+process.stderr
                result[method+'_hardware_adapter_execution']=True
                reader=HardwareClient(model,'mock');reader.connect(guard=False);reader.health();start_q=dict(reader.positions);reader.destroy_node()
            result['all_targets_use_same_model_and_no_tcp']=True;result['success']=True
        except BaseException as error:
            import traceback
            result.update(success=False,error=str(error),traceback=traceback.format_exc())
            if client:result['guard']=client.guard;result['supervisor']=client.supervisor
        finally:
            for manager in managers:
                with manager.lock:manager.states={k:('active' if k==HOLD else 'inactive') for k in manager.states};manager.v=np.zeros(6)
            if client:client.destroy_node()
            if executor:executor.shutdown(timeout_sec=3.)
            if worker:worker.join(timeout=3.)
            for node in roles+managers:node.destroy_node()
            rclpy.shutdown();socket.create_connection=previous
            result['qualification']='Fake ROS managers/actions, no UR dynamics or real stopping-budget proof';dump(output,result)
    if not result.get('success'):raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--config',type=Path)
    args=parser.parse_args();check(args.output,args.config)

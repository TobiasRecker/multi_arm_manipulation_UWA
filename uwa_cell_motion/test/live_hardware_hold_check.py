"""Opt-in six-joint plugin proof on a private GenericSystem manager, domain67."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory,JointTrajectoryPoint
from controller_manager_msgs.srv import ListControllers,SwitchController,ListHardwareComponents
from rcl_interfaces.srv import GetParameters
from match_ur_hardware.profiles import load_profiles
from uwa_cell_motion.common import config,dump
from uwa_cell_motion.hardware_ports import HOLD,provision,StopPort,matching_hardware
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_motion.node import MotionNode


def check(inventory,output):
    require_domain('mock');profiles=load_profiles(inventory);assert len(profiles)==1
    profile=next(iter(profiles.values()));assert profile['namespace'].startswith('/uwa_mock_validation/')
    cfg=config(Path(__file__).parents[1]/'config/hardware_motion.yaml');rclpy.init();node=MotionNode('hardware_hold_plugin_check')
    result={};executor=None
    try:
        def basic(kind,suffix,request):
            client=node.create_client(kind,profile['namespace']+'/controller_manager/'+suffix)
            try:
                assert client.wait_for_service(timeout_sec=15.)
                future=client.call_async(request);rclpy.spin_until_future_complete(node,future,timeout_sec=5.)
                assert future.done();return future.result()
            finally:node.destroy_client(client)
        end=time.monotonic()+30.
        while True:
            controllers=basic(ListControllers,'list_controllers',ListControllers.Request()).controller
            if any(c.name=='joint_trajectory_controller' and c.state=='inactive' for c in controllers):break
            if time.monotonic()>end:raise RuntimeError('Mock trajectory controller did not initialize')
            time.sleep(.2)
        hardware=basic(ListHardwareComponents,'list_hardware_components',ListHardwareComponents.Request())
        assert matching_hardware(hardware.component,profile['joint_names'],'mock')
        provision(node,profiles,cfg,'mock');result['provision_inactive_six_joint_cpp_plugin']=True
        executor=SingleThreadedExecutor();executor.add_node(node)
        def call(kind,suffix,request):
            client=node.create_client(kind,profile['namespace']+'/controller_manager/'+suffix)
            try:
                assert client.wait_for_service(timeout_sec=3.);future=client.call_async(request);end=time.monotonic()+5.
                while not future.done() and time.monotonic()<end:executor.spin_once(timeout_sec=.01)
                assert future.done();return future.result()
            finally:node.destroy_client(client)
        positions={}
        node.create_subscription(JointState,profile['namespace']+'/joint_states',lambda msg:positions.update(zip(msg.name,msg.position)),10)
        def wait(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:executor.spin_once(timeout_sec=.01)
        wait(.3);assert all(j in positions for j in profile['joint_names'])
        before=np.asarray([positions[j] for j in profile['joint_names']])
        request=SwitchController.Request();request.activate_controllers=[HOLD];request.strictness=SwitchController.Request.STRICT;request.timeout.sec=1
        assert call(SwitchController,'switch_controller',request).ok;wait(.2)
        controllers=call(ListControllers,'list_controllers',ListControllers.Request()).controller
        hold=next(c for c in controllers if c.name==HOLD)
        assert hold.type=='uwa_cell_motion/CollisionHold' and hold.state=='active'
        assert set(hold.claimed_interfaces)=={j+'/position' for j in profile['joint_names']}
        result['six_actual_position_interfaces_claimed']=True
        request=SwitchController.Request();request.activate_controllers=['joint_trajectory_controller'];request.strictness=SwitchController.Request.STRICT;request.timeout.sec=1
        assert not call(SwitchController,'switch_controller',request).ok;result['position_controller_activation_conflict_rejected']=True
        pub=node.create_publisher(JointTrajectory,profile['namespace']+'/joint_trajectory_controller/joint_trajectory',10)
        message=JointTrajectory();message.joint_names=profile['joint_names'];point=JointTrajectoryPoint(positions=(before+.1).tolist());point.time_from_start.sec=1;message.points=[point]
        wait(.2);pub.publish(message);wait(.4)
        assert np.max(abs(np.asarray([positions[j] for j in profile['joint_names']])-before))<1e-8
        result['topic_during_hold_does_not_move_mock_joints']=True
        request=SwitchController.Request();request.activate_controllers=['forward_velocity_controller'];request.strictness=SwitchController.Request.BEST_EFFORT;request.timeout.sec=1
        result['generic_system_velocity_activation_response']=call(SwitchController,'switch_controller',request).ok
        port=StopPort(node,profile,cfg,'mock');end=time.monotonic()+3.
        while time.monotonic()<end:
            executor.spin_once(timeout_sec=.01);status=port.tick(True,True)
            if status['held']:break
        assert status['held'],status
        controllers=call(ListControllers,'list_controllers',ListControllers.Request()).controller
        assert not any(c.name=='forward_velocity_controller' and c.state=='active' for c in controllers)
        result['adapter_removes_other_command_interface_while_latched']=True
        result.update(success=True,qualification='Actual ros2_control + six-joint C++ plugin, GenericSystem only; no UR dynamics',namespace=profile['namespace'])
    except BaseException as error:
        import traceback
        result.update(success=False,error=str(error),traceback=traceback.format_exc())
    finally:
        dump(output,result)
        if executor:executor.shutdown(timeout_sec=2.)
        node.destroy_node();rclpy.shutdown()
    if not result.get('success'):raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inventory',required=True);parser.add_argument('--output',required=True);args=parser.parse_args();check(args.inventory,args.output)

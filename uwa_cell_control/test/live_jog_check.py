"""Operator-jog integration on one isolated mock arm; no physical addresses."""
import json
import os
from pathlib import Path
import tempfile
import time
import yaml

os.environ['ROS_DOMAIN_ID']='66';os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
os.environ['QT_QPA_PLATFORM']='offscreen'

from python_qt_binding import QtCore,QtWidgets
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.srv import GetParameters
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TwistStamped
from match_ur_hardware.operations import call,controller_list,switch
from match_ur_hardware.profiles import CARTESIAN
from uwa_cell_control.gui import Window


def main():
    workspace=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    logs=workspace/'setup/logs';app=QtWidgets.QApplication([])
    temporary=tempfile.TemporaryDirectory(prefix='uwa-jog-validation-')
    inventory=Path(temporary.name)/'inventory.yaml'
    data=yaml.safe_load((workspace/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml').read_text())
    data['ros_namespace']='/uwa_jog_validation'
    for index,arm in enumerate(data['robots'].values()):arm.update(ip=f'127.0.0.{index+1}',port_base=60000+index*1000)
    inventory.write_text(yaml.safe_dump(data))
    window=Window(inventory,arms=['right_rear']);window.timer.stop();window.show()
    arm=window.profiles['right_rear'];rclpy.init();node=rclpy.create_node('uwa_jog_validation')
    states=[];commands=[]
    state_sub=node.create_subscription(JointState,arm['namespace']+'/joint_states',states.append,qos_profile_sensor_data)
    command_sub=node.create_subscription(TwistStamped,arm['namespace']+'/'+CARTESIAN+'/equilibrium_twist_cmd',commands.append,10)
    report={'success':False,'hardware_started':False,'namespace':arm['namespace']}
    def pump():app.processEvents();rclpy.spin_once(node,timeout_sec=.01)
    def wait(predicate,timeout,label):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            pump()
            if predicate():return
        raise RuntimeError('Timeout: '+label)
    def dwell(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:pump()
    try:
        wait(lambda:not window.jobs,12,'initial status')
        window.buttons['start'].click()
        wait(lambda:states and any(c.name==CARTESIAN and c.state=='inactive' for c in
             (controller_list(node,arm,optional=True) or [])),90,'mock driver')
        # Put only the mock arm in a nonsingular pose before Cartesian testing.
        switch(node,arm,target='joint_trajectory_controller')
        action=ActionClient(node,FollowJointTrajectory,arm['namespace']+'/joint_trajectory_controller/follow_joint_trajectory')
        assert action.wait_for_server(timeout_sec=5.)
        goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=arm['joint_names']
        point=JointTrajectoryPoint();point.positions=[0.,-1.1,1.5,-1.9,-1.3,0.];point.time_from_start.sec=3
        goal.trajectory.points=[point]
        accepted=action.send_goal_async(goal);wait(accepted.done,8,'mock-only initial posture accepted')
        assert accepted.result().accepted
        result=accepted.result().get_result_async();wait(result.done,12,'mock initial posture')
        assert result.result().result.error_code==0
        window.buttons['jog'].click();dialog=window.jog_dialogs['right_rear']
        dwell(.5);assert not commands
        report['opening_does_not_command_motion']=True
        dialog.enable.click();wait(lambda:'cartesian' not in window.jobs,45,'Cartesian controller activation')
        assert any(c.name==CARTESIAN and c.state=='active' for c in controller_list(node,arm))
        request=GetParameters.Request();request.names=['admittance','wrench_twist_gain','use_ft_sensor','require_wrench']
        params=call(node,GetParameters,arm['namespace']+'/'+CARTESIAN+'/get_parameters',request)
        assert list(params.values[0].double_array_value)==[0.]*6
        assert list(params.values[1].double_array_value)==[0.]*6
        assert not params.values[2].bool_value and not params.values[3].bool_value
        report['effective_controller_compliance_off']=True
        wait(lambda:dialog.transport.subscribers()>0,5,'jog subscriber discovery')
        before=list(states[-1].position);dialog.axis_buttons['X+'].pressed.emit();dwell(1.)
        after=list(states[-1].position)
        delta=max(abs(a-b) for a,b in zip(after,before))
        assert delta>1e-5,(before,after)
        assert any(abs(msg.twist.linear.x-.01)<1e-10 for msg in commands)
        assert all(msg.header.frame_id=='right_rear_base_link' for msg in commands)
        report['held_translation_joint_delta_rad']=delta
        dialog.axis_buttons['X+'].released.emit();dwell(.5)
        assert commands[-1].twist.linear.x==0
        stable=list(states[-1].position);dwell(.5)
        drift=max(abs(a-b) for a,b in zip(states[-1].position,stable))
        assert drift<1e-4,drift
        report['release_stops_motion_drift_rad']=drift
        dialog.mode.setCurrentIndex(1);dialog.axis_buttons['Z+'].pressed.emit();dwell(.5)
        assert any(abs(msg.twist.angular.z-.1)<1e-10 for msg in commands)
        QtWidgets.QApplication.sendEvent(dialog,QtCore.QEvent(QtCore.QEvent.Type.WindowDeactivate));dwell(.4)
        assert commands[-1].twist.angular.z==0
        report['rotation_and_focus_loss_stop']=True
        dialog.grab().save(str(logs/'uwa-jog-dialog.png'))
        dialog.close();window.buttons['drivers_stop'].click()
        wait(lambda:not window.drivers,20,'owned mock teardown');report['success']=True
    except Exception as error:
        import traceback
        report['error']=repr(error);traceback.print_exc()
    finally:
        window.close();app.processEvents();node.destroy_node();rclpy.shutdown();temporary.cleanup()
        (logs/'uwa-jog-live.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0 if report['success'] else 1


if __name__=='__main__':raise SystemExit(main())

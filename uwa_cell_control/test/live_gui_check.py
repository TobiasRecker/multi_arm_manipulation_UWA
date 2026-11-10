"""Real ROS/mock-components integration of the UWA GUI, never real UR hardware."""
import json
from copy import deepcopy
import os
from pathlib import Path
import time
from types import SimpleNamespace

os.environ['ROS_DOMAIN_ID']='66'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
os.environ['QT_QPA_PLATFORM']='offscreen'

import numpy as np
from python_qt_binding import QtWidgets
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from match_ur_hardware.operations import controller_list
import match_ur_hardware.operations as operations
from match_ur_hardware.profiles import CARTESIAN,MOTION
from uwa_cell_control.gui import Window,ARM_IDS


def main():
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    out=ws/'setup/logs/uwa-control';out.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication([])
    window=Window(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml',arms=ARM_IDS)
    window.timer.stop();window.show()
    rclpy.init();node=rclpy.create_node('uwa_gui_mock_validation')
    report={'mode':'mock','hardware_started':False,'success':False}
    def pump(seconds=.15):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents();rclpy.spin_once(node,timeout_sec=.01)
    def wait(predicate,timeout,label):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            pump()
            if predicate():return
        raise RuntimeError('Timeout: '+label)
    def controllers():
        return {rid:controller_list(node,window.profiles[rid],optional=True) for rid in ARM_IDS}
    try:
        assert window.mock
        wait(lambda:not window.jobs,8,'initial status')
        window.buttons['start'].click()
        wait(lambda:all(cs and any(c.name==CARTESIAN and c.state=='inactive' for c in cs)
                        for cs in controllers().values()),110,'four mock drivers/controllers')
        initial=controllers()
        assert not any(c.name in MOTION and c.state=='active' for cs in initial.values() for c in cs)
        report['initial']={rid:{c.name:c.state for c in cs} for rid,cs in initial.items()}
        received={}
        subs=[node.create_subscription(JointState,window.profiles[rid]['namespace']+'/joint_states',
            lambda msg,rid=rid:received.update({rid:msg}),qos_profile_sensor_data) for rid in ARM_IDS]
        wait(lambda:len(received)==4,10,'four finite joint state streams')
        names=[]
        for rid,msg in received.items():
            assert len(msg.position)==6 and np.isfinite(msg.position).all()
            names.extend(msg.name)
        assert len(set(names))==24
        report['unique_joint_names']=len(set(names))
        # Exercise the hardware activation branch against these mock managers.
        # Dashboard is replaced locally; no physical camera/robot connection.
        profiles=deepcopy(window.profiles)
        for arm in profiles.values():
            arm['ip']='127.0.0.1';arm['external_control_program']='/mock/external.urp'
        original_dashboard=operations.dashboard
        operations.dashboard=lambda arm:{'reachable':True,'blocked':False,'remote_control':True,
            'queries':[{'command':cmd,'answer':answer} for cmd,answer in [
                ('safetystatus','Safetystatus: NORMAL'),('robotmode','Robotmode: RUNNING'),
                ('programState','PLAYING'),('get loaded program','Loaded program: /mock/external.urp')]]}
        try:
            for ids in [['right_rear'],['right_rear','right_front']]:
                args=SimpleNamespace(arms=ids,operation='trajectory',mode='hardware')
                assert operations._run_arms(args,profiles,node,{},False)==0
                assert all(any(c.name=='scaled_joint_trajectory_controller' and c.state=='active'
                               for c in controller_list(node,profiles[rid])) for rid in ids)
            try:
                operations._run_arms(SimpleNamespace(arms=['left_front'],operation='trajectory',mode='hardware'),
                                     profiles,node,{},False)
            except RuntimeError:report['third_arm_refused']=True
            else:raise AssertionError('Third arm was allowed')
            report['one_two_arm_hardware_branch_on_mock']=True
            for rid in ['right_rear','right_front']:operations.switch(node,profiles[rid])
        finally:operations.dashboard=original_dashboard
        window.buttons['cartesian'].click()
        wait(lambda:'cartesian' not in window.jobs,30,'mock Cartesian activation')
        activated=controllers()
        assert all(any(c.name==CARTESIAN and c.state=='active' for c in cs) for cs in activated.values())
        report['cartesian_active']=True
        window.operation('status');wait(lambda:not window.jobs,15,'GUI status')
        window.tabs.setCurrentIndex(1);pump(.5)
        window.grab().save(str(out/'mock-controller-gui.png'))
        window.stop_button.click();wait(lambda:'stop' not in window.jobs,30,'software stop')
        stopped=controllers()
        assert not any(c.name in MOTION and c.state=='active' for cs in stopped.values() for c in cs)
        report['stop_all_motion_inactive']=True
        window.buttons['drivers_stop'].click()
        wait(lambda:not window.drivers,20,'owned process teardown')
        report['owned_drivers_stopped']=True
        report['success']=True
    except Exception as error:
        report['error']=str(error)
    finally:
        window.close();app.processEvents();node.destroy_node();rclpy.shutdown()
        (out/'mock-gui-validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    return 0 if report['success'] else 1


if __name__=='__main__':raise SystemExit(main())

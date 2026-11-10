"""Real ROS/mock-components integration of the UWA GUI, never real UR hardware."""
import json
import os
from pathlib import Path
import time
import tempfile
import tarfile
import signal
import yaml
from types import SimpleNamespace

os.environ['ROS_DOMAIN_ID']='67'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
os.environ['QT_QPA_PLATFORM']='offscreen'

import numpy as np
from python_qt_binding import QtWidgets
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from controller_manager_msgs.srv import UnloadController
from match_ur_hardware.operations import controller_list
import match_ur_hardware.operations as operations
from match_ur_hardware.profiles import CARTESIAN,MOTION
from uwa_cell_control.gui import Window,ARM_IDS


def main():
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    out=ws/'setup/logs/uwa-control';out.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication([])
    temporary=tempfile.TemporaryDirectory(prefix='uwa-mock-validation-')
    inventory=Path(temporary.name)/'inventory.yaml'
    data=yaml.safe_load((ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml').read_text())
    data['ros_namespace']='/uwa_mock_validation'
    for i,arm in enumerate(data['robots'].values()):arm.update(ip='127.0.0.'+str(i+1),port_base=61000+i*1000)
    inventory.write_text(yaml.safe_dump(data))
    window=Window(inventory,arms=ARM_IDS)
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
        wait(lambda:not window.jobs,20,'initial status')
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
        profiles=window.profiles
        original_dashboard=operations.dashboard
        def no_dashboard(arm):raise AssertionError('Controller switch must not query Dashboard')
        operations.dashboard=no_dashboard
        try:
            for ids in [['right_rear'],['right_rear','right_front'],list(ARM_IDS)]:
                args=SimpleNamespace(arms=ids,operation='trajectory',mode='hardware')
                assert operations._run_arms(args,profiles,node,{},False)==0
                assert all(any(c.name=='scaled_joint_trajectory_controller' and c.state=='active'
                               for c in controller_list(node,profiles[rid])) for rid in ids)
            report['direct_one_two_four_arm_switch_on_mock']=True
            for rid in ARM_IDS:operations.switch(node,profiles[rid])
        finally:operations.dashboard=original_dashboard
        samples=operations.read_joints(node,profiles,ARM_IDS)
        assert all(len(s['positions'])==6 for s in samples.values())
        report['joint_reader_without_program_preflight']=True
        request=UnloadController.Request();request.name='forward_velocity_controller'
        assert operations.call(node,UnloadController,profiles['right_rear']['namespace']+
            '/controller_manager/unload_controller',request).ok
        operations.load_controllers(node,profiles['right_rear'],mock=True)
        assert any(c.name=='forward_velocity_controller' and c.state=='inactive'
                   for c in controller_list(node,profiles['right_rear']))
        operations.load_controllers(node,profiles['right_rear'],mock=True)
        report['controller_reload_idempotent']=True
        window.buttons['cartesian'].click()
        wait(lambda:'cartesian' not in window.jobs,30,'mock Cartesian activation')
        activated=controllers()
        assert all(any(c.name==CARTESIAN and c.state=='active' for c in cs) for cs in activated.values())
        report['cartesian_active']=True
        window.operation('status');wait(lambda:not window.jobs,15,'GUI status')
        window.tabs.setCurrentIndex(1);pump(.5)
        window.grab().save(str(out/'mock-controller-gui.png'))
        window.save_logs_button.click()
        wait(lambda:window.export_worker is None,25,'log archive export during active mock controllers')
        archive_path=Path((out/'latest-export.txt').read_text().strip())
        with tarfile.open(archive_path) as archive:
            manifest=json.load(archive.extractfile('manifest.json'))
            assert len(manifest['snapshot']['driver_pids'])==4
            assert manifest['snapshot']['mode']=='mock'
            assert any(name.startswith('ros/') for name in archive.getnames())
            assert any(name.startswith('session/processes/') for name in archive.getnames())
        report['log_export']=str(archive_path)
        window.stop_button.click();wait(lambda:'stop' not in window.jobs,30,'software stop')
        stopped=controllers()
        assert not any(c.name in MOTION and c.state=='active' for cs in stopped.values() for c in cs)
        report['stop_all_motion_inactive']=True
        # A manager failure must release that launch/lock, without touching other arms.
        root_pid=int(window.drivers['left_front'].processId())
        processes={}
        for directory in Path('/proc').iterdir():
            if not directory.name.isdigit():continue
            try:
                stat=(directory/'stat').read_text()
                parent=int(stat[stat.rfind(')')+2:].split()[1])
                command=(directory/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
                processes[int(directory.name)]=(parent,command)
            except (OSError,ValueError):continue
        descendants={root_pid}
        while True:
            children={pid for pid,(parent,_) in processes.items() if parent in descendants}
            if children<=descendants:break
            descendants|=children
        candidates=[pid for pid in descendants if pid in processes and
                    'controller_manager/ros2_control_node' in processes[pid][1] and
                    '/uwa_mock_validation/left_front' in processes[pid][1]]
        assert len(candidates)==1
        os.kill(candidates[0],signal.SIGTERM)
        wait(lambda:'left_front' not in window.drivers,25,'failed-manager launch cleanup')
        assert len(window.drivers)==3
        for rid,box in window.checks.items():box.setChecked(rid=='left_front')
        window.buttons['start'].click()
        wait(lambda:any(c.name==CARTESIAN and c.state=='inactive' for c in
                        (controller_list(node,window.profiles['left_front'],optional=True) or [])),45,
             'restart after manager exit releases arm lock')
        report['manager_exit_cleanup_and_restart']=True
        for box in window.checks.values():box.setChecked(True)
        window.buttons['drivers_stop'].click()
        wait(lambda:not window.drivers,20,'owned process teardown')
        report['owned_drivers_stopped']=True
        report['success']=True
    except Exception as error:
        report['error']=str(error)
    finally:
        window.close();app.processEvents();node.destroy_node();rclpy.shutdown();temporary.cleanup()
        (out/'mock-gui-validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    return 0 if report['success'] else 1


if __name__=='__main__':raise SystemExit(main())

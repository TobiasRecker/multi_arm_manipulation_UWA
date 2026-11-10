"""One isolated mock driver plus three static mock sensor streams, domain67.

Never reads the physical inventory addresses into a running hardware driver.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

import numpy as np
import yaml

os.environ['ROS_DOMAIN_ID']='67';os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
os.environ['MPLCONFIGDIR']='/tmp/uwa-parking-matplotlib'
import rclpy
from sensor_msgs.msg import JointState
from match_ur_hardware.operations import controller_list
from match_ur_hardware.profiles import load_profiles
from match_ur_hardware.trajectory import execute_trajectory
from uwa_cell_gazebo.configuration import load_layout,joint_names,ROBOT_IDS
from uwa_cell_control.park_arm import JointObserver
from uwa_cell_control.parking import make_model,complete_state,plan_parking,save_plan


def main():
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    logs=ws/'setup/logs';out=ws/'setup/calibration/parking/mock-live';out.mkdir(parents=True,exist_ok=True)
    report={'success':False,'hardware_started':False,'domain':67}
    with tempfile.TemporaryDirectory(prefix='uwa-parking-validation-') as temporary:
        inventory=Path(temporary)/'inventory.yaml'
        data=yaml.safe_load((ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml').read_text())
        data['ros_namespace']='/uwa_parking_validation'
        for i,arm in enumerate(data['robots'].values()):arm.update(ip=f'127.0.0.{i+1}',port_base=45000+i*1000)
        inventory.write_text(yaml.safe_dump(data));profiles=load_profiles(inventory)
        assert all(p['ip'].startswith('127.0.0.') for p in profiles.values())
        stream=(logs/'uwa-parking-mock-driver.log').open('w')
        driver=subprocess.Popen(['ros2','launch','uwa_cell_control','arms.launch.py',f'inventory:={inventory}',
            'arms:=right_front','mode:=mock'],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        child=None;rclpy.init();node=rclpy.create_node('uwa_parking_validation_observer')
        observer=JointObserver(node,profiles,ROBOT_IDS,'mock');layout=load_layout()
        fixed={r:layout['robots'][r]['initial_positions'] for r in ROBOT_IDS if r!='right_front'}
        pubs={r:node.create_publisher(JointState,profiles[r]['namespace']+'/joint_states',10) for r in fixed}
        enabled=set(fixed)
        def publish():
            for r in enabled:
                msg=JointState();msg.header.stamp=node.get_clock().now().to_msg()
                msg.name=joint_names(r);msg.position=fixed[r];pubs[r].publish(msg)
        timer=node.create_timer(.05,publish)
        def pump(seconds=.1):
            end=time.monotonic()+seconds
            while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.01)
        def wait(predicate,timeout,label):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                pump()
                if predicate():return
            raise RuntimeError('Timeout: '+label)
        arm=profiles['right_front']
        try:
            wait(lambda:any(c.name=='joint_trajectory_controller' for c in
                (controller_list(node,arm,optional=True) or [])),70,'mock controller startup')
            wait(lambda:len(observer.received)==4,5,'four mock joint sensors')
            # Only mock setup: put the fake arm into the known fixture state.
            q0=observer.received['right_front']['positions'];q1=layout['robots']['right_front']['initial_positions']
            points=[{'time':t,'positions':q,'velocities':[0.]*6,'accelerations':[0.]*6} for t,q in [(0.,q0),(3.,q1)]]
            execute_trajectory(node,arm,points,mock=True);pump(.4)
            model,layout=make_model(layout,profiles,out)
            def artifact(target=None):
                readings={r:dict(record) for r,record in observer.received.items()}
                start,sources,missing=complete_state(layout,readings)
                path=plan_parking(model,layout,'right_front',start,target=target)
                path['layout_file']=str(ws/'src/multi_arm_manipulation_UWA/uwa_cell_description/config/cell_layout.yaml')
                return save_plan(out,path,model,layout,profiles,sources,missing,'mock')
            plan=artifact();pump(.4)
            before={r:list(record['positions']) for r,record in observer.received.items()}
            execution_log=(logs/'uwa-parking-mock-execute.log').open('w')
            command=['ros2','run','uwa_cell_control','park_arm','execute',str(out/'plan.json'),'--inventory',str(inventory)]
            child=subprocess.Popen(command,stdout=execution_log,stderr=subprocess.STDOUT)
            wait(lambda:child.poll() is not None,plan['duration']*3+35,'checked parking execution')
            assert child.returncode==0;execution_log.close();pump(.4)
            error=max(abs(np.array(observer.received['right_front']['positions'])-plan['target']))
            assert error<.03,error
            report['parking_error_rad']=float(error);report['duration_s']=plan['duration']
            for r in fixed:assert observer.received[r]['positions']==before[r]
            report['other_arm_states_unchanged']=True
            plan=artifact(target=q1);pump(.4)
            cancel_log=(logs/'uwa-parking-mock-cancel.log').open('w')
            child=subprocess.Popen(command,stdout=cancel_log,stderr=subprocess.STDOUT)
            parked=list(observer.received['right_front']['positions'])
            wait(lambda:max(abs(np.array(observer.received['right_front']['positions'])-parked))>1e-4,
                 20,'second checked trajectory actually moving before telemetry fault')
            enabled.remove('right_rear')
            wait(lambda:child.poll() is not None,7,'stale obstacle stream cancels goal')
            assert child.returncode!=0;cancel_log.close();pump(.4)
            assert not any(c.state=='active' and c.name=='joint_trajectory_controller' for c in controller_list(node,arm))
            stable=list(observer.received['right_front']['positions']);pump(.5)
            drift=max(abs(np.array(observer.received['right_front']['positions'])-stable))
            assert drift<.001,drift
            report.update(telemetry_loss_cancels_and_deactivates=True,post_cancel_drift_rad=float(drift),success=True)
        except Exception as error:
            import traceback
            traceback.print_exc();report['error']=repr(error)
        finally:
            if child is not None and child.poll() is None:child.send_signal(signal.SIGINT);child.wait(timeout=10)
            if driver.poll() is None:os.killpg(driver.pid,signal.SIGINT)
            try:driver.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(driver.pid,signal.SIGTERM);driver.wait(timeout=5)
            stream.close();observer.close();node.destroy_node();rclpy.shutdown()
            (logs/'uwa-parking-live.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0 if report['success'] else 1


if __name__=='__main__':raise SystemExit(main())

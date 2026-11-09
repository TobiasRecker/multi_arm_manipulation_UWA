"""Real Qt/ROS diagonal-pair acceptance and interruption checks, simulation only."""
import argparse,json,os,threading,time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import JointState
from uwa_cell_calibration.gui import Window,QtWidgets
from uwa_cell_calibration.client import Client
from uwa_cell_calibration.diagonal import DIAGONALS
from uwa_cell_calibration.storage import atomic_json
from uwa_cell_gazebo.configuration import ROBOT_IDS,joint_names


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['full','stop','pause','disconnect','capture','parking'],default='stop')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--screenshot')
    a=p.parse_args()
    rclpy.init();node=Client();executor=SingleThreadedExecutor();executor.add_node(node)
    telemetry={};observed={};errors=[];plan={};park_drift=[]
    def joints(message):
        telemetry.update(positions=dict(zip(message.name,message.position)),velocities=dict(zip(message.name,message.velocity)))
        state=node.state;ids=state.get('active_robots',[])
        if state.get('phase')=='MOVING' and len(ids)==2 and all(any(abs(telemetry['velocities'].get(j,0))>.01 for j in joint_names(r)) for r in ids):
            key='+'.join(ids);observed[key]=observed.get(key,0)+1
            if tuple(ids) not in DIAGONALS:errors.append('Unexpected moving pair '+key)
            for rid in ROBOT_IDS:
                if rid not in ids and rid in plan.get('parking',{}):
                    drift=max(abs(telemetry['positions'][j]-q) for j,q in zip(joint_names(rid),plan['parking'][rid]))
                    park_drift.append(drift)
    node.create_subscription(JointState,'/uwa_cell/joint_states',joints,10)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    app=QtWidgets.QApplication([]);window=Window(node);window.show()
    last_message=['']
    def until(condition,seconds=120):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents();time.sleep(.02)
            message=f"{node.state.get('phase','')} {node.state.get('active_robots',[])} {node.state.get('accepted',0)} {node.state.get('message','')}"
            if message!=last_message[0]:print(message,flush=True);last_message[0]=message
            if errors:raise AssertionError(errors)
            if node.error:raise RuntimeError(node.error)
            if condition():return
            if node.state.get('client_id')==node.client_id and node.state.get('phase')=='ERROR':raise RuntimeError(node.state['message'])
        raise TimeoutError(str(node.state))
    try:
        until(lambda:len(node.images)==4 and node.state.get('phase') in ('IDLE','COMPLETE','STOPPED','READY','ERROR'))
        assert window.diagonal.isChecked()
        window.prepare_button.click()
        until(lambda:node.state.get('phase')=='READY' and node.state.get('client_id')==node.client_id)
        root=Path(os.environ['UWA_WS'])/'setup/calibration'
        for file in sorted(root.glob('*/plan.json'),reverse=True):
            candidate=json.loads(file.read_text())
            if candidate['plan_id']==node.state['plan_id']:plan.update(candidate);break
        assert plan['mode']=='diagonal_pairs'
        until(lambda:window.start_button.isEnabled());window.start_button.click()
        def pair_moving():
            ids=node.state.get('active_robots',[])
            return node.state.get('phase')=='MOVING' and len(ids)==2 and all(any(abs(telemetry.get('velocities',{}).get(j,0))>.01 for j in joint_names(r)) for r in ids)
        if a.mode=='full':
            until(lambda:node.result is not None,3600)
            assert node.result.success,node.result.message
            until(lambda:node.state.get('phase')=='COMPLETE')
            assert all(node.state['counts'][r]==40 for r in ROBOT_IDS)
            assert set(observed)=={'+'.join(pair) for pair in DIAGONALS}
            completed_plan=json.loads((Path(plan['session_dir'])/'plan.json').read_text())
            return_error=max(abs(telemetry['positions'][j]-completed_plan['run_start'][j]) for rid in ROBOT_IDS for j in joint_names(rid))
            assert return_error<.02
        else:
            if a.mode=='parking':
                until(lambda:node.state.get('phase')=='PARKING' and any(abs(v)>.01 for j,v in telemetry.get('velocities',{}).items() if 'robotiq' not in j))
            elif a.mode=='capture':until(lambda:node.state.get('phase')=='CAPTURING' and len(node.state.get('active_robots',[]))==2,180)
            else:until(pair_moving,180)
            if a.mode=='pause':
                window.pause_button.click();until(lambda:node.state.get('phase')=='PAUSED' and node.state.get('stopped'),8)
                q=dict(telemetry['positions']);start=time.monotonic()
                until(lambda:time.monotonic()-start>.4)
                assert max(abs(telemetry['positions'][j]-v) for j,v in q.items() if 'robotiq' not in j)<.005
                until(lambda:window.pause_button.isEnabled());window.pause_button.click();until(pair_moving,30)
            start=time.monotonic()
            if a.mode=='disconnect':window.timer.stop()
            else:window.stop_button.click()
            until(lambda:node.state.get('phase')=='STOPPED' and node.state.get('stopped'),8)
            stop_seconds=time.monotonic()-start;q=dict(telemetry['positions']);counts=dict(node.state.get('counts',{}))
            until(lambda:time.monotonic()-start>max(1.,stop_seconds+.5))
            assert node.state['phase']=='STOPPED' and node.state['counts']==counts
            assert max(abs(telemetry['positions'][j]-v) for j,v in q.items() if 'robotiq' not in j)<.005
        assert not park_drift or max(park_drift)<.02
        report={'mode':a.mode,'session':plan['session_dir'],'observed_simultaneous_native_motion':observed,
                'max_parked_arm_joint_error_rad':max(park_drift,default=0.),'passed':True,
                'reason':node.state.get('message'),'result_path':node.state.get('result_path')}
        if a.mode!='full':report['seconds_to_stop_both']=stop_seconds
        else:report['max_return_error_rad']=return_error
        if a.screenshot:app.processEvents();assert window.grab().save(a.screenshot)
        atomic_json(a.output,report);print(json.dumps(report,indent=2))
    finally:
        if node.state.get('client_id')==node.client_id and node.state.get('phase') not in ('IDLE','COMPLETE','STOPPED','ERROR'):
            node.command('stop');time.sleep(.5)
        window.timer.stop();window.allow_close=True;window.close()
        executor.shutdown(timeout_sec=3);thread.join(timeout=3);node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()

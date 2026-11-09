"""Live Qt smoke check; observer mode never interrupts another session.

--exercise prepares/starts its own session and clicks the actual red Stop button.
--freeze instead freezes GUI heartbeats to verify the independent backend watchdog.
"""
import argparse,json,threading,time
from pathlib import Path
import rclpy
from rclpy.executors import SingleThreadedExecutor
from python_qt_binding import QtWidgets
from sensor_msgs.msg import JointState
from uwa_cell_calibration.client import Client
from uwa_cell_calibration.gui import Window


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--screenshot');p.add_argument('--exercise',action='store_true');p.add_argument('--freeze',action='store_true')
    p.add_argument('--planning',action='store_true');p.add_argument('--capture',action='store_true')
    p.add_argument('--world-pause',action='store_true')
    p.add_argument('--output');args=p.parse_args()
    rclpy.init();node=Client();executor=SingleThreadedExecutor();executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    telemetry={}
    node.create_subscription(JointState,'/uwa_cell/joint_states',lambda m:telemetry.update({
        'positions':dict(zip(m.name,m.position)),'velocities':dict(zip(m.name,m.velocity)),
        'stamp':m.header.stamp.sec+m.header.stamp.nanosec*1e-9}),10)
    app=QtWidgets.QApplication([]);window=Window(node);window.show()
    def until(condition,seconds=20):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents();time.sleep(.02)
            if condition():return
        raise TimeoutError(str(node.state)+' '+node.error)
    try:
        until(lambda:len(node.images)==4 and bool(node.state))
        assert window.count.minimum()==30 and window.count.maximum()==50
        assert window.stop_button.isEnabled() and 'bb1825' in window.stop_button.styleSheet()
        until(lambda:all(label.pixmap() is not None and not label.pixmap().isNull() for label in window.views.values()))
        result={'four_live_images':True,'red_stop_enabled':True,'count_range':[30,50]}
        if args.exercise or args.freeze or args.planning or args.capture:
            assert node.state['phase'] in ('IDLE','STOPPED','ERROR','READY','COMPLETE'), 'Another session is active'
            for rid,box in window.robots.items():box.setChecked(rid=='left_front')
            window.prepare_button.click()
            if args.planning:
                until(lambda:node.state.get('phase')=='PREPARING' and node.state.get('accepted',0)>0 and node.state.get('client_id')==node.client_id)
            else:
                until(lambda:node.state.get('phase')=='READY' and node.state.get('client_id')==node.client_id,45)
                until(lambda:window.start_button.isEnabled())
                window.start_button.click()
                if args.capture:until(lambda:node.state.get('phase')=='CAPTURING',45)
                else:until(lambda:node.state.get('phase')=='MOVING' and any(abs(v)>.01 for j,v in telemetry.get('velocities',{}).items() if j.startswith('left_front_') and 'robotiq' not in j),45)
            before=dict(telemetry['positions']);accepted_before=node.state.get('counts',{}).get('left_front',0)
            start=time.monotonic()
            if args.freeze:window.timer.stop()
            else:window.stop_button.click()
            until(lambda:node.state.get('phase')=='STOPPED' and node.state.get('stopped'),8)
            result.update(stopped=True,seconds_to_confirm=time.monotonic()-start,reason=node.state['message'])
            count=node.state.get('counts',{}).get('left_front',0)
            assert count<=accepted_before+int(args.capture)
            until(lambda:time.monotonic()-start>1)
            assert node.state['phase']=='STOPPED'
            assert node.state.get('counts',{}).get('left_front',0)==count
            if args.planning:assert max(abs(v-telemetry['positions'][j]) for j,v in before.items())<.01
        if args.world_pause:
            assert node.state['phase'] in ('IDLE','STOPPED','ERROR','READY','COMPLETE')
            from gz.transport import Node
            from gz.msgs.world_control_pb2 import WorldControl
            from gz.msgs.boolean_pb2 import Boolean
            transport=Node()
            try:
                window.world_button.click();until(lambda:window.world_paused)
                time.sleep(.2);stamp=telemetry['stamp'];start=time.monotonic()
                until(lambda:time.monotonic()-start>.4)
                assert telemetry['stamp']==stamp
                result['direct_gazebo_pause_confirmed']=True
            finally:
                ok,response=transport.request('/world/uwa_lab/control',WorldControl(pause=False),WorldControl,Boolean,1000)
                assert ok and response.data
            until(lambda:telemetry['stamp']>stamp)
            result['simulation_resumed']=True
        if args.screenshot:
            app.processEvents();assert window.grab().save(args.screenshot)
        if args.output:Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:
        window.timer.stop();window.allow_close=True;window.close()
        executor.shutdown(timeout_sec=2);thread.join(timeout=2);node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()

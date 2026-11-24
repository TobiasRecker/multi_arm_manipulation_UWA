"""Independent high-contrast STOP/status window for the hardware scan runner."""
import json
import fcntl
from pathlib import Path
import signal
import os
import sys
import time

from python_qt_binding import QtCore,QtWidgets
import rclpy
from std_msgs.msg import Empty,String
from std_srvs.srv import Trigger


def scan_gui_policy(minimal):
    return dict(pause_service='/uwa_cell/protection/pause_all' if minimal else '/uwa_object_scan/stop',
                resume_service='/uwa_cell/protection/resume_all' if minimal else None,
                heartbeat=not minimal, stop_on_close=not minimal)


def main():
    minimal=False
    if os.environ.get('UWA_PROTECTION_BACKEND', 'legacy') != 'legacy':
        from uwa_cell_motion.protection_backend import minimal_enabled
        minimal=minimal_enabled()
    policy=scan_gui_policy(minimal)
    os.environ['ROS_DOMAIN_ID']='66';os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    folder=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))/'setup/digitization'
    folder.mkdir(parents=True,exist_ok=True)
    lock=(folder/'.four_arm_scan_gui.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print('STOP window already open; use the existing window.',file=sys.stderr)
        return 1
    from rclpy.signals import SignalHandlerOptions
    rclpy.init(args=[],signal_handler_options=SignalHandlerOptions.NO)
    node=rclpy.create_node('uwa_object_scan_stop_window')
    heartbeat=node.create_publisher(Empty,'/uwa_object_scan/heartbeat',10) if policy['heartbeat'] else None
    client=node.create_client(Trigger,policy['pause_service'])
    resume_client=node.create_client(Trigger,'/uwa_object_scan/resume')
    global_resume=node.create_client(Trigger,policy['resume_service']) if minimal else None
    app=QtWidgets.QApplication(sys.argv[:1])
    window=QtWidgets.QWidget();window.setWindowTitle('UWA Object Scan · STOP ALL FOUR')
    window.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint,True)
    layout=QtWidgets.QVBoxLayout(window)
    title=QtWidgets.QLabel('FOUR-ARM OBJECT SCAN');title.setStyleSheet('font-size:25px;font-weight:bold;');layout.addWidget(title)
    state=QtWidgets.QLabel('WAITING FOR BACKEND · No movement started by this window')
    state.setWordWrap(True);state.setMinimumSize(650,180)
    state.setStyleSheet('background:#ffe066;color:#000;font-size:22px;font-weight:bold;padding:15px;');layout.addWidget(state)
    command_error=['']
    def send_shared(service, action):
        command_error[0]=''
        if not service.service_is_ready():
            command_error[0]=action+' FAILED: shared protection service unavailable'
            state.setText(command_error[0]);return
        state.setText(action+' RECEIVED · waiting for command acknowledgement')
        def completed(future):
            try:
                response=future.result()
                detail=json.loads(response.message)
                if not response.success:
                    command_error[0]=action+' FAILED: '+str(detail.get('command_error',detail.get('error',response.message)))
                state.setText(command_error[0] or action+' ACCEPTED\n'+str(detail.get('state','')))
            except Exception as error:
                command_error[0]=action+' UNCONFIRMED: '+str(error);state.setText(command_error[0])
        service.call_async(Trigger.Request()).add_done_callback(completed)
    stop=QtWidgets.QPushButton('STOP ALL FOUR ARMS');stop.setMinimumHeight(130)
    stop.setStyleSheet('background:#c00000;color:white;border:5px solid white;font-size:31px;font-weight:bold;')
    layout.addWidget(stop)
    protection=[{}]
    global_continue=None
    if minimal:
        global_continue=QtWidgets.QPushButton('RESUME UNAVAILABLE · waiting for shared status')
        global_continue.setMinimumHeight(60);global_continue.setEnabled(False)
        global_continue.setStyleSheet('background:white;color:black;font-size:21px;font-weight:bold;')
        global_continue.clicked.connect(lambda:send_shared(global_resume,'RESUME'))
        layout.addWidget(global_continue)
    resume=QtWidgets.QPushButton('Continue after initial image review');resume.setMinimumHeight(55);resume.setEnabled(False)
    resume.setStyleSheet('background:white;color:black;font-size:20px;font-weight:bold;')
    resume.clicked.connect(lambda:resume_client.call_async(Trigger.Request()) if resume_client.service_is_ready() else None)
    layout.addWidget(resume)
    note=QtWidgets.QLabel('Shared software pause for all four arms; Resume keeps retained trajectories.\n'
        'Closing this window leaves the scan running.' if minimal else
        'Software stop for this scan. Closing this window also stops the scan.\nKeep the physical emergency stop accessible.')
    note.setStyleSheet('font-size:17px;');layout.addWidget(note)
    received=[0.];last=[None];requested=[False]
    def request():
        requested[0]=True
        state.setText('SOFTWARE PAUSE REQUESTED · waiting for controller acknowledgements' if minimal else
                      'STOP RECEIVED · Cancelling goals / deactivating controllers…\nStandstill is not yet confirmed.')
        state.setStyleSheet('background:#ffe066;color:#000;font-size:22px;font-weight:bold;padding:15px;')
        if minimal:
            requested[0]=False;send_shared(client,'SOFTWARE PAUSE');return
        if rclpy.ok() and client.service_is_ready():
            client.call_async(Trigger.Request())
            requested[0]=False
    stop.clicked.connect(request)
    def status(msg):
        last[0]=json.loads(msg.data);received[0]=time.monotonic()
        data=last[0];phase=data['phase']
        resume.setEnabled(phase=='PAUSED')
        text=phase
        if 'round' in data:text+=f" · Round {data['round']}/{data['total_rounds']}"
        if 'arms' in data:text+='\n'+', '.join(data['arms'])
        text+='\n'+data.get('message',data.get('error',data.get('directory','')))
        if 'standstill_confirmed' in data:text+='\nSTANDSTILL '+('CONFIRMED' if data['standstill_confirmed'] else 'NOT CONFIRMED')
        if minimal:
            shared=protection[0]
            text+='\n'+str(shared.get('state','WAITING FOR SHARED PROTECTION'))
            if shared.get('warnings'):text+='\n'+'\n'.join(shared['warnings'])
            if command_error[0]:text+='\n'+command_error[0]
        state.setText(text)
        color='#ffb4b4' if command_error[0] else '#8effa2' if phase in ('COMPLETE','CAPTURED','CHECKED','STOPPED') else '#ffb4b4' if phase in ('FAILED','STOP_UNCONFIRMED','RESTORE_FAILED') else '#ffe066'
        state.setStyleSheet(f'background:{color};color:#000;font-size:22px;font-weight:bold;padding:15px;')
    subscription=node.create_subscription(String,'/uwa_object_scan/status',status,10)
    if minimal:
        from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
        def shared_status(msg):
            try:protection[0]=json.loads(msg.data)
            except (ValueError,TypeError):return
            globally_paused=bool(protection[0].get('paused'))
            global_continue.setEnabled(globally_paused)
            global_continue.setText('RESUME ALL ARMS · retained trajectories' if globally_paused else
                                    'RESUME UNAVAILABLE · no software pause')
            if last[0]:status(String(data=json.dumps(last[0])))
            else:
                state.setText(str(protection[0].get('state','SHARED PROTECTION'))+'\n'+
                              '\n'.join(protection[0].get('warnings',[])))
        shared_subscription=node.create_subscription(String,'/uwa_cell/protection/status',shared_status,
            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE))
    def tick():
        if not rclpy.ok():
            timer.stop();app.quit();return
        if heartbeat is not None:heartbeat.publish(Empty())
        rclpy.spin_once(node,timeout_sec=0)
        if requested[0] and client.service_is_ready():
            if minimal:send_shared(client,'SOFTWARE PAUSE')
            else:client.call_async(Trigger.Request())
            requested[0]=False
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(50)
    if policy['stop_on_close']:app.aboutToQuit.connect(request)
    def signal_stop(signum,frame):
        if policy['stop_on_close']:request()
        app.quit()
    signal.signal(signal.SIGINT,signal_stop)
    signal.signal(signal.SIGTERM,signal_stop)
    window.setStyleSheet('background:#171c24;color:white;');window.resize(760,480);window.show()
    if os.environ.get('UWA_SCAN_GUI_SNAPSHOT'):
        QtCore.QTimer.singleShot(500,lambda:window.grab().save(os.environ['UWA_SCAN_GUI_SNAPSHOT']))
    try:return app.exec()
    finally:
        if policy['stop_on_close']:request()
        end=time.monotonic()+.3
        while rclpy.ok() and time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.02)
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        lock.close()


if __name__=='__main__':sys.exit(main())

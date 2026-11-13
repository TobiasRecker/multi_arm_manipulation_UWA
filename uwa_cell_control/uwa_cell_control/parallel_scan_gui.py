"""Independent high-contrast STOP/status window for the hardware scan runner."""
import json
import os
import sys
import time

from python_qt_binding import QtCore,QtWidgets
import rclpy
from std_msgs.msg import Empty,String
from std_srvs.srv import Trigger


def main():
    os.environ['ROS_DOMAIN_ID']='66';os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    rclpy.init(args=[]);node=rclpy.create_node('uwa_object_scan_stop_window')
    heartbeat=node.create_publisher(Empty,'/uwa_object_scan/heartbeat',10)
    client=node.create_client(Trigger,'/uwa_object_scan/stop')
    resume_client=node.create_client(Trigger,'/uwa_object_scan/resume')
    app=QtWidgets.QApplication(sys.argv[:1])
    window=QtWidgets.QWidget();window.setWindowTitle('UWA Object Scan · STOP ALL FOUR')
    window.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint,True)
    layout=QtWidgets.QVBoxLayout(window)
    title=QtWidgets.QLabel('FOUR-ARM OBJECT SCAN');title.setStyleSheet('font-size:25px;font-weight:bold;');layout.addWidget(title)
    state=QtWidgets.QLabel('WAITING FOR BACKEND · No movement started by this window')
    state.setWordWrap(True);state.setMinimumSize(650,180)
    state.setStyleSheet('background:#ffe066;color:#000;font-size:22px;font-weight:bold;padding:15px;');layout.addWidget(state)
    stop=QtWidgets.QPushButton('STOP ALL FOUR ARMS');stop.setMinimumHeight(130)
    stop.setStyleSheet('background:#c00000;color:white;border:5px solid white;font-size:31px;font-weight:bold;')
    layout.addWidget(stop)
    resume=QtWidgets.QPushButton('Continue after initial image review');resume.setMinimumHeight(55);resume.setEnabled(False)
    resume.setStyleSheet('background:white;color:black;font-size:20px;font-weight:bold;')
    resume.clicked.connect(lambda:resume_client.call_async(Trigger.Request()) if resume_client.service_is_ready() else None)
    layout.addWidget(resume)
    note=QtWidgets.QLabel('Software stop for this scan. Closing this window also stops the scan.\nKeep the physical emergency stop accessible.')
    note.setStyleSheet('font-size:17px;');layout.addWidget(note)
    received=[0.];last=[None];requested=[False]
    def request():
        requested[0]=True
        state.setText('STOP RECEIVED · Cancelling goals / deactivating controllers…\nStandstill is not yet confirmed.')
        state.setStyleSheet('background:#ffe066;color:#000;font-size:22px;font-weight:bold;padding:15px;')
        if client.service_is_ready():client.call_async(Trigger.Request())
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
        state.setText(text)
        color='#8effa2' if phase in ('COMPLETE','CAPTURED','CHECKED','STOPPED') else '#ffb4b4' if phase in ('FAILED','STOP_UNCONFIRMED','RESTORE_FAILED') else '#ffe066'
        state.setStyleSheet(f'background:{color};color:#000;font-size:22px;font-weight:bold;padding:15px;')
    subscription=node.create_subscription(String,'/uwa_object_scan/status',status,10)
    def tick():
        heartbeat.publish(Empty());rclpy.spin_once(node,timeout_sec=0)
        if requested[0] and client.service_is_ready():client.call_async(Trigger.Request());requested[0]=False
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(50)
    app.aboutToQuit.connect(request)
    window.setStyleSheet('background:#171c24;color:white;');window.resize(760,480);window.show()
    if os.environ.get('UWA_SCAN_GUI_SNAPSHOT'):
        QtCore.QTimer.singleShot(500,lambda:window.grab().save(os.environ['UWA_SCAN_GUI_SNAPSHOT']))
    try:return app.exec()
    finally:
        request()
        end=time.monotonic()+.3
        while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.02)
        node.destroy_node();rclpy.shutdown()


if __name__=='__main__':sys.exit(main())

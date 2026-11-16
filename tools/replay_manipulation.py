#!/usr/bin/env python3
"""Read-only RViz replay of an independently passed contact-simulation trace.

Publishes recorded joint states and visual markers in /uwa_grasp_replay only.
No Gazebo, controllers, actions, command topics or physical devices are started.
"""
import argparse
import atexit
import bisect
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

# Keep host Qt/ROS on host libraries when invoked from the VS Code Snap.
for key in ("GTK_PATH","GTK_EXE_PREFIX","GTK_IM_MODULE_FILE","GIO_MODULE_DIR","GSETTINGS_SCHEMA_DIR"):
    if "/snap/" in os.environ.get(key,""):os.environ.pop(key,None)

import numpy as np
import rclpy
from python_qt_binding import QtCore, QtGui, QtWidgets
from rclpy.qos import QoSProfile, DurabilityPolicy
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import JointState
from visualization_msgs.msg import Marker, MarkerArray
import yaml
from uwa_cell_tasks.core import verify

PHASES = {'observe':'Observe carton', 'review_strategy':'Review grasp strategy',
    'plan_approach':'Plan approach', 'review_plan':'Review trajectories',
    'approach':'Approach pregrasp', 'inspect_pregrasp':'Inspect pregrasp',
    'review_alignment':'Review alignment', 'grasp':'Enter and close grippers',
    'move_object':'Lift / hold rigid group', 'set_down':'Set down rigid group',
    'release':'Open on support', 'done':'Completed recorded cycle'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--qualification',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--speed',type=float,default=8.)
    args=p.parse_args()
    if os.environ.get('ROS_DOMAIN_ID')!='64' or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST':
        p.error('Source the simulation environment (domain64 / LOCALHOST).')
    if not .25<=args.speed<=32:p.error('Replay speed must be0.25–32.')
    run=args.run.resolve();scene=args.scene.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    qualification=verify(json.loads(args.qualification.read_text()))
    cases=[c for c in qualification['recipe_attempts'] if Path(c['scene']).name==scene.name and c['passed']]
    case=next((c for c in cases if c['run_id']==int(run.name.removeprefix('carton_grasp_run'))),None)
    if case is None:raise ValueError('Run must be a passed case in the qualification artifact.')
    trace=run/'evaluation-trace.jsonl'
    if hashlib.sha256(trace.read_bytes()).hexdigest()!=case['evidence_file_sha256']['evaluation-trace.jsonl']:
        raise ValueError('Recorded trace no longer matches its qualified hash.')
    report=verify(json.loads((run/'validation-report.json').read_text()));assert report['passed'] and report['sha256']==case['validation_sha256']
    model=verify(json.loads((scene/'scene.json').read_text()));assert model['sha256']==case['scene_sha256']
    if hashlib.sha256((scene/'robot.urdf').read_bytes()).hexdigest()!=model['robot_sha256']:raise ValueError('Robot description changed.')
    records=[json.loads(s) for s in trace.read_text().splitlines()]
    records=[r for r in records if r.get('object') and r.get('joints')]
    times=[r['elapsed_wall_s'] for r in records];start=times[0];end=times[-1]
    robot=ET.fromstring((scene/'robot.urdf').read_text())
    for tag in ('gazebo','ros2_control'):
        for element in list(robot.findall(tag)):robot.remove(element)
    for joint in robot.findall('joint'):
        for mimic in list(joint.findall('mimic')):joint.remove(mimic)
    params=out/'robot-state-publisher.yaml'
    params.write_text(yaml.safe_dump({'/**':{'ros__parameters':{'robot_description':ET.tostring(robot,encoding='unicode'),'publish_frequency':30.}}}))
    ns='/uwa_grasp_replay'
    app=QtWidgets.QApplication(sys.argv[:1])
    screen=app.screenAt(QtGui.QCursor.pos()) or app.primaryScreen();area=screen.availableGeometry()
    config={'Panels':[{'Class':'rviz_common/Displays','Name':'Displays'}],
      'Visualization Manager':{'Class':'','Enabled':True,'Name':'root','Value':True,
        'Global Options':{'Fixed Frame':'world','Background Color':'22; 25; 31','Frame Rate':30},
        'Displays':[{'Class':'rviz_default_plugins/Grid','Name':'Recorded scene grid','Enabled':True,'Cell Size':.5,'Plane Cell Count':12},
         {'Class':'rviz_default_plugins/RobotModel','Name':'RECORDED SIMULATION - measured joints','Enabled':True,'Alpha':1.,'Description Source':'Topic',
          'Description Topic':{'Value':ns+'/robot_description','Reliability Policy':'Reliable','Durability Policy':'Transient Local'},'Visual Enabled':True,'Collision Enabled':False},
         {'Class':'rviz_default_plugins/MarkerArray','Name':'REPLAY - carton pose and recorded contacts','Enabled':True,
          'Topic':{'Value':ns+'/markers','Reliability Policy':'Reliable','Durability Policy':'Transient Local','Depth':1}}],
        'Tools':[{'Class':'rviz_default_plugins/MoveCamera'},{'Class':'rviz_default_plugins/Select'}],
        'Views':{'Current':{'Class':'rviz_default_plugins/Orbit','Name':'Carton replay','Target Frame':'<Fixed Frame>',
          'Near Clip Distance':.01,'Distance':2.5,'Focal Point':{'X':0.,'Y':0.,'Z':1.05},'Pitch':.65,'Yaw':.18}}},
      'Window Geometry':{'Width':max(900,area.width()-455),'Height':max(700,area.height()-90),'X':area.x(),'Y':area.y()+35}}
    config_path=out/'carton-replay.rviz';config_path.write_text(yaml.safe_dump(config,sort_keys=False))
    rclpy.init(args=[])
    node=rclpy.create_node('recorded_carton_replay',namespace=ns)
    joints=node.create_publisher(JointState,ns+'/joint_states',10)
    markers=node.create_publisher(MarkerArray,ns+'/markers',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    children=[]
    def cleanup_children():
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=5.)
            except subprocess.TimeoutExpired:child.kill();child.wait()
    atexit.register(cleanup_children)
    for label,command in [('robot-state-publisher',['ros2','run','robot_state_publisher','robot_state_publisher','--ros-args','--params-file',str(params),'-r','__ns:='+ns,'-r','/tf:='+ns+'/tf','-r','/tf_static:='+ns+'/tf_static']),
      ('rviz',['rviz2','-d',str(config_path),'--ros-args','-r','__node:=carton_replay_view','-r','/tf:='+ns+'/tf','-r','/tf_static:='+ns+'/tf_static'])]:
        log=(out/(label+'.log')).open('w');children.append(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT));log.close()
    window=QtWidgets.QWidget();window.setWindowTitle('UWA Carton Replay - RECORDED SIMULATION')
    window.setStyleSheet('QWidget {background:#101318;color:white;font-size:18px;} QPushButton,QComboBox {background:#303d50;color:white;padding:12px;border:2px solid white;} QLabel {padding:5px;}')
    layout=QtWidgets.QVBoxLayout(window)
    headline=QtWidgets.QLabel(f'RECORDED SIMULATION\nRun{case["run_id"]} | 14 Nov2026');headline.setStyleSheet('font-size:25px;font-weight:bold;background:#243b59;');layout.addWidget(headline)
    explanation=QtWidgets.QLabel('Recorded actual joint and carton poses.\nPlayback only - no robot commands.');explanation.setWordWrap(True);layout.addWidget(explanation)
    status=QtWidgets.QLabel();status.setWordWrap(True);status.setMinimumHeight(160);layout.addWidget(status)
    play=QtWidgets.QPushButton('Play replay');pause=QtWidgets.QPushButton('Pause');restart=QtWidgets.QPushButton('Restart')
    for button in (play,pause,restart):layout.addWidget(button)
    speed=QtWidgets.QComboBox()
    for value in (1,2,4,8,16,32):speed.addItem(str(value)+'x recorded time',float(value))
    
    if speed.findData(args.speed)<0:speed.addItem(f'{args.speed:g}x recorded time',args.speed)
    speed.setCurrentIndex(speed.findData(args.speed));layout.addWidget(speed)
    seek=QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal);seek.setRange(0,1000);layout.addWidget(seek)
    close=QtWidgets.QPushButton('Close replay');layout.addWidget(close);close.clicked.connect(window.close)
    window.resize(430,700);window.move(area.x()+max(0,area.width()-450),area.y()+40)
    state={'time':start,'playing':False,'last':time.monotonic(),'last_save':0.,'phase':None}
    com=np.array(model['lift_reference_point_object_m']);first=np.array(records[0]['object']['T_world_object']);base=float((first[:3,:3]@com+first[:3,3])[2])
    def playing(value):state['playing']=value;state['last']=time.monotonic()
    play.clicked.connect(lambda:playing(True));pause.clicked.connect(lambda:playing(False))
    def reset():state['time']=start;playing(False)
    restart.clicked.connect(reset)
    seek.sliderMoved.connect(lambda v:state.update(time=start+(end-start)*v/1000.))
    def update():
        now=time.monotonic();delta=now-state['last'];state['last']=now
        if state['playing']:state['time']=min(end,state['time']+delta*float(speed.currentData()))
        if state['time']>=end:state['playing']=False
        command=out/'control.json'
        if command.exists():
            data=json.loads(command.read_text());command.unlink()
            if data['action']=='play':playing(True)
            elif data['action']=='pause':playing(False)
            elif data['action']=='restart':reset()
            elif data['action']=='close':window.close();return
        r=records[max(0,bisect.bisect_right(times,state['time'])-1)]
        stamp=node.get_clock().now().to_msg();msg=JointState();msg.header.stamp=stamp;msg.name=list(r['joints']['positions']);msg.position=[float(r['joints']['positions'][k]) for k in msg.name];joints.publish(msg)
        t=np.array(r['object']['T_world_object']);q=Rotation.from_matrix(t[:3,:3]).as_quat();arr=MarkerArray();m=Marker();m.header.frame_id='world';m.header.stamp=stamp;m.ns='recorded_carton';m.id=0;m.type=Marker.MESH_RESOURCE;m.action=Marker.ADD
        m.mesh_resource='package://uwa_cell_description/assets/carton_avocado_v1/carton.dae';m.mesh_use_embedded_materials=True
        m.pose.position.x,m.pose.position.y,m.pose.position.z=map(float,t[:3,3]);m.pose.orientation.x,m.pose.orientation.y,m.pose.orientation.z,m.pose.orientation.w=map(float,q);m.scale.x=m.scale.y=m.scale.z=1.;m.color.a=1.;arr.markers.append(m)
        label=Marker();label.header=m.header;label.ns='recorded_status';label.id=1;label.type=Marker.TEXT_VIEW_FACING;label.action=Marker.ADD;label.pose.position.z=1.92;label.pose.orientation.w=1.;label.scale.z=.055;label.color.r=label.color.g=label.color.b=label.color.a=1.;label.text=f'RECORDED SIMULATION / RUN{case["run_id"]}\n'+PHASES.get(r['phase'],r['phase']);arr.markers.append(label);markers.publish(arr)
        contact=r.get('contacts',{});pads=sum(bool(v) for a in contact.get('pads',{}).values() for v in a.values());lift=((t[:3,:3]@com+t[:3,3])[2]-base)*1000.
        phase=PHASES.get(r['phase'],r['phase']);mode='PLAYING' if state['playing'] else ('REPLAY COMPLETE' if state['time']>=end else 'PAUSED')
        status.setText(f'{mode} | {float(speed.currentData()):g}x\n{phase}\nRecorded lift: {lift:.1f} mm\nPad contacts: {pads}/4\n'+('Table support: YES' if contact.get('supported') else 'Table support: NO - carrying')+f'\nRecorded time: {state["time"]-start:.0f} / {end-start:.0f}s')
        if not seek.isSliderDown():seek.setValue(round(1000*(state['time']-start)/(end-start)))
        if now-state['last_save']>.5:
            data=dict(mode=mode,phase=r['phase'],recorded_time_s=state['time'],end_time_s=end,speed=float(speed.currentData()),lift_mm=float(lift),pads=pads,supported=contact.get('supported'),rviz_pid=children[1].pid,read_only_replay=True)
            tmp=out/'viewer-state.json.tmp';tmp.write_text(json.dumps(data));tmp.replace(out/'viewer-state.json');state['last_save']=now
        if r['phase']!=state['phase']:print('REPLAY PHASE: '+r['phase'],flush=True);state['phase']=r['phase']
        rclpy.spin_once(node,timeout_sec=0.)
    timer=QtCore.QTimer();timer.timeout.connect(update);timer.start(33);window.show();update()
    (out/'replay.json').write_text(json.dumps(dict(kind='recorded_simulation_replay',run=str(run),scene=str(scene),trace_sha256=case['evidence_file_sha256']['evaluation-trace.jsonl'],validation_sha256=report['sha256'],namespace=ns,robot_commands=False,controllers_started=False,recorded_date='2026-11-14',speed=args.speed),indent=2))
    try:return app.exec()
    finally:
        timer.stop()
        cleanup_children()
        node.destroy_node();rclpy.shutdown()

if __name__=='__main__':raise SystemExit(main())

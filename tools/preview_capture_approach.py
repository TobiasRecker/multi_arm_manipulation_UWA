#!/usr/bin/env python3
"""One sampled geometric proposal, then a command-free RViz review on domain74."""
import argparse,contextlib,json,os,time
from pathlib import Path
import numpy as np
import yaml
from uwa_cell_motion.common import ROBOT_IDS,config,joint_names
from uwa_cell_motion.hardware_model import HardwareProblem


def generate(snapshot,out):
    began=time.perf_counter();repo=Path(__file__).resolve().parents[1]
    saved=json.loads(snapshot.read_text());state=dict(saved['start']);out.mkdir(parents=True,exist_ok=False)
    targets=yaml.safe_load((repo/'config/view_designs/oak_shared_views_20261112.yaml').read_text())['targets_rad']
    names=[j for r in ROBOT_IDS for j in joint_names(r)];segments=[];checked=0
    with contextlib.nullcontext(out/'model') as directory:
        model=HardwareProblem(directory,config(repo/'uwa_cell_motion/config/hardware_right_front_stop_test.yaml'),repo/'config/hardware_inventory.yaml')
        for arm in ('left_front','left_rear','right_rear','right_front'):
            q0=np.array([state[j] for j in joint_names(arm)])
            goal=np.array([min((v+2*np.pi*k for k in range(-2,3) if model.collision.bounds[j][0]<=v+2*np.pi*k<=model.collision.bounds[j][1]),key=lambda x:abs(x-q)) for j,q,v in zip(joint_names(arm),q0,targets[arm])])
            delta=goal-q0;peak=float(max(abs(delta)))
            count=max(1,int(np.ceil(peak/.035)))
            for u in np.linspace(0,1,count+1):
                current=dict(state,**dict(zip(joint_names(arm),q0+u*delta)))
                if not model.collision.check(current)[0]:raise ValueError(f'{arm}: model collision at {u:.3f}')
                world,bounds=model.spheres.planning_world(current)
                from itertools import combinations
                if not all(model.spheres.pair_clear(world,bounds,a,b,.04) for a,b in combinations(ROBOT_IDS,2)):
                    raise ValueError(f'{arm}: less than40mm arm-envelope gap at {u:.3f}')
                checked+=1
            duration=max(1.,1.875*peak/.1,np.sqrt(5.774*peak/.2))
            segments.append(dict(arm=arm,start=[state[j] for j in names],duration_s=duration,
                target=dict(zip(joint_names(arm),goal.tolist()))))
            state.update(zip(joint_names(arm),goal.tolist()))
        # Use the ordinary visual model; the full opening envelope above was
        # only used for the single geometric check.
        import xml.etree.ElementTree as ET
        robot=ET.fromstring(model.original_description)
        for tag in ('gazebo','ros2_control'):
            for element in list(robot.findall(tag)):robot.remove(element)
        (out/'robot.yaml').write_text(yaml.safe_dump({'/**':{'ros__parameters':{'robot_description':ET.tostring(robot,encoding='unicode'),'publish_frequency':30.}}}))
        proposal=dict(kind='capture_approach_review_only',executable=False,source=str(snapshot.resolve()),
            source_label='Last valid measured start:17 Nov2026. Current arms are powered off; zero telemetry was rejected.',
            start=saved['start'],joint_names=names,segments=segments,duration_s=sum(s['duration_s'] for s in segments),
            target=state,check=dict(fcl_samples=checked,maximum_joint_step_rad=.035,static_arm_gap_m=.04,
                full_opening_envelopes=True,all_six_arm_pairs=True,dynamic_stop_reserve_qualification=False),
            calculation_s=time.perf_counter()-began)
        (out/'proposal.json').write_text(json.dumps(proposal,indent=2))
        print(json.dumps({k:proposal[k] for k in ('executable','duration_s','check','calculation_s')}),flush=True)


def view(out):
    if os.environ.get('ROS_DOMAIN_ID')!='74':raise ValueError('Preview requires isolated domain74')
    import atexit,signal,subprocess,sys
    import rclpy
    from python_qt_binding import QtCore,QtWidgets
    from sensor_msgs.msg import JointState
    from visualization_msgs.msg import Marker,MarkerArray
    from rclpy.qos import QoSProfile,DurabilityPolicy
    data=json.loads((out/'proposal.json').read_text());ns='/uwa_capture_proposal'
    app=QtWidgets.QApplication(sys.argv[:1]);area=app.primaryScreen().availableGeometry()
    displays=[{'Class':'rviz_default_plugins/Grid','Name':'Grid','Enabled':True,'Cell Size':.5,'Plane Cell Count':12},
      {'Class':'rviz_default_plugins/RobotModel','Name':'CAPTURE PATH PROPOSAL','Enabled':True,'Alpha':1.,'Description Source':'Topic',
       'Description Topic':{'Value':ns+'/robot_description','Reliability Policy':'Reliable','Durability Policy':'Transient Local'},'Visual Enabled':True,'Collision Enabled':False},
      {'Class':'rviz_default_plugins/MarkerArray','Name':'PROPOSAL STATUS','Enabled':True,
       'Topic':{'Value':ns+'/markers','Durability Policy':'Transient Local','Reliability Policy':'Reliable','Depth':1}}]
    cfg={'Panels':[{'Class':'rviz_common/Displays','Name':'Displays'}],
     'Visualization Manager':{'Global Options':{'Fixed Frame':'world','Background Color':'25; 30; 40','Frame Rate':30},'Displays':displays,
      'Tools':[{'Class':'rviz_default_plugins/MoveCamera'}],
      'Views':{'Current':{'Class':'rviz_default_plugins/Orbit','Distance':3.5,'Focal Point':{'X':0.,'Y':0.,'Z':1.3},'Pitch':.45,'Yaw':.6,'Target Frame':'<Fixed Frame>'}}},
     'Window Geometry':{'Width':max(900,area.width()-425),'Height':max(700,area.height()-65),'X':area.x(),'Y':area.y()+30}}
    (out/'proposal.rviz').write_text(yaml.safe_dump(cfg,sort_keys=False));children=[]
    def cleanup():
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill()
    atexit.register(cleanup)
    for name,cmd in [('state-publisher',['ros2','run','robot_state_publisher','robot_state_publisher','--ros-args','--params-file',str(out/'robot.yaml'),'-r','__ns:='+ns,'-r','/tf:='+ns+'/tf','-r','/tf_static:='+ns+'/tf_static']),
      ('rviz',['rviz2','-d',str(out/'proposal.rviz'),'--ros-args','-r','__node:=capture_proposal_view','-r','/tf:='+ns+'/tf','-r','/tf_static:='+ns+'/tf_static'])]:
        with (out/(name+'.log')).open('w') as log:children.append(subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT))
    rclpy.init(args=[]);node=rclpy.create_node('capture_proposal_player',namespace=ns)
    publisher=node.create_publisher(JointState,ns+'/joint_states',10)
    markers=node.create_publisher(MarkerArray,ns+'/markers',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    window=QtWidgets.QWidget();window.setWindowTitle('UWA Capture Path - PREVIEW ONLY')
    window.setStyleSheet('QWidget{background:#111a28;color:white;font-size:18px} QPushButton,QComboBox{background:#29405e;color:white;border:2px solid white;padding:12px} QLabel{padding:8px}')
    layout=QtWidgets.QVBoxLayout(window);label=QtWidgets.QLabel('CAPTURE PATH PROPOSAL\nWaiting for your review');label.setStyleSheet('background:#314e72;font-size:24px;font-weight:bold');layout.addWidget(label)
    source=QtWidgets.QLabel(data['source_label']);source.setWordWrap(True);layout.addWidget(source)
    status=QtWidgets.QLabel();status.setWordWrap(True);layout.addWidget(status)
    play=QtWidgets.QPushButton('Play preview');pause=QtWidgets.QPushButton('Pause');reset=QtWidgets.QPushButton('Back to start');goal=QtWidgets.QPushButton('Show final poses')
    for button in (play,pause,reset,goal):layout.addWidget(button)
    speed=QtWidgets.QComboBox()
    for value in (1,2,4,8):speed.addItem(f'{value}x preview speed',value)
    speed.setCurrentIndex(2);layout.addWidget(speed)
    slider=QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal);slider.setRange(0,1000);layout.addWidget(slider)
    state=dict(t=0.,playing=False,last=time.monotonic(),last_save=0.)
    play.clicked.connect(lambda:state.update(playing=True,t=0. if state['t']>=data['duration_s'] else state['t'],last=time.monotonic()))
    pause.clicked.connect(lambda:state.update(playing=False));reset.clicked.connect(lambda:state.update(t=0.,playing=False))
    goal.clicked.connect(lambda:state.update(t=data['duration_s'],playing=False))
    slider.sliderMoved.connect(lambda v:state.update(t=data['duration_s']*v/1000.,playing=False))
    def tick():
        now=time.monotonic()
        if state['playing']:state['t']=min(data['duration_s'],state['t']+(now-state['last'])*speed.currentData())
        state['last']=now
        if state['t']>=data['duration_s']:state['playing']=False
        elapsed=0.;positions=dict(data['start']);phase='ALL FOUR AT PROPOSED POSES'
        for segment in data['segments']:
            if state['t']<elapsed+segment['duration_s']:
                u=np.clip((state['t']-elapsed)/segment['duration_s'],0,1);s=10*u**3-15*u**4+6*u**5
                initial=dict(zip(data['joint_names'],segment['start']))
                positions.update({j:initial[j]+s*(q-initial[j]) for j,q in segment['target'].items()});phase='MOVING IN PREVIEW: '+segment['arm'];break
            positions.update(segment['target']);elapsed+=segment['duration_s']
        msg=JointState();msg.header.stamp=node.get_clock().now().to_msg();msg.name=list(positions);msg.position=list(positions.values());publisher.publish(msg)
        mode='PREVIEW PLAYING' if state['playing'] else 'PREVIEW PAUSED'
        status.setText(f'{mode}\n{phase}\n{state["t"]:.1f} / {data["duration_s"]:.1f} nominal seconds\nGeometric proposal | no robot commands')
        if not slider.isSliderDown():slider.setValue(round(1000*state['t']/data['duration_s']))
        marker=Marker();marker.header.frame_id='world';marker.header.stamp=msg.header.stamp;marker.ns='proposal';marker.id=0;marker.type=Marker.TEXT_VIEW_FACING;marker.action=Marker.ADD;marker.pose.position.z=2.5;marker.pose.orientation.w=1.;marker.scale.z=.07;marker.color.r=marker.color.g=marker.color.b=marker.color.a=1.;marker.text='PATH PROPOSAL - REVIEW ONLY\n'+phase
        markers.publish(MarkerArray(markers=[marker]));rclpy.spin_once(node,timeout_sec=0.)
        if now-state['last_save']>.5:
            (out/'viewer-state.json').write_text(json.dumps(dict(mode=mode,phase=phase,time_s=state['t'],rviz_running=children[1].poll() is None,domain=74,robot_commands=False)));state['last_save']=now
    signal.signal(signal.SIGTERM,lambda *_:window.close())
    signal.signal(signal.SIGINT,lambda *_:window.close())
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(33)
    window.resize(410,680);window.move(area.x()+max(0,area.width()-420),area.y()+40);window.show();tick()
    try:return app.exec()
    finally:timer.stop();cleanup();node.destroy_node();rclpy.shutdown()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--view',action='store_true');a=p.parse_args()
    if a.view:raise SystemExit(view(a.output.resolve()))
    generate(a.snapshot,a.output.resolve())

"""Static read-only design preview on isolated ROS domain70; no hardware clients."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

import numpy as np
import yaml


def preview(source, proposal):
    os.environ['ROS_DOMAIN_ID']='70'
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    from sensor_msgs.msg import JointState
    from geometry_msgs.msg import Point
    from visualization_msgs.msg import Marker,MarkerArray
    from ament_index_python.packages import get_package_share_directory
    source=Path(source);data=json.loads(Path(proposal).read_text());state=dict(data['state'])
    for joint in ET.fromstring((source/'cell.urdf').read_text()).findall('joint'):
        if joint.get('type') in ('revolute','prismatic','continuous') and joint.find('mimic') is None:
            state.setdefault(joint.get('name'),0.)
    environment=os.environ.copy()
    for key in ('GTK_PATH','GTK_EXE_PREFIX','GTK_IM_MODULE_FILE','GIO_MODULE_DIR','GSETTINGS_SCHEMA_DIR'):
        if '/snap/' in environment.get(key,''):environment.pop(key,None)
    stopped=False
    def stop(signum,frame):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=rclpy.create_node('uwa_oak_view_design_preview')
    publisher=node.create_publisher(JointState,'/joint_states',10)
    markers=node.create_publisher(MarkerArray,'/uwa_view_design/markers',10)
    children=[]
    try:
        with tempfile.TemporaryDirectory(prefix='uwa-oak-view-preview-') as tmp:
            tmp=Path(tmp)
            parameters=tmp/'robot.yaml';parameters.write_text(yaml.safe_dump({'/**':{'ros__parameters':{'robot_description':(source/'cell.urdf').read_text(),'use_sim_time':False}}}))
            cfg=yaml.safe_load((Path(get_package_share_directory('uwa_cell_gazebo'))/'rviz/cell.rviz').read_text())
            manager=cfg['Visualization Manager'];manager['Displays']=manager['Displays'][:2]+[{'Class':'rviz_default_plugins/MarkerArray','Name':'ROUGH OAK + shared views','Enabled':True,'Marker Topic':{'Value':'/uwa_view_design/markers'}}]
            manager['Displays'][1].update(Name='PROPOSED configuration - no hardware motion',Alpha=1.)
            manager['Displays'][1]['Description Topic']['Value']='/robot_description'
            cfg['Window Geometry']={'Width':1400,'Height':900}
            path=tmp/'design.rviz';path.write_text(yaml.safe_dump(cfg))
            for cmd in [['ros2','run','robot_state_publisher','robot_state_publisher','--ros-args','--params-file',str(parameters)],['ros2','run','rviz2','rviz2','-d',str(path)]]:
                children.append(subprocess.Popen(cmd,start_new_session=True,env=environment))
            while not stopped and rclpy.ok() and all(p.poll() is None for p in children):
                now=node.get_clock().now().to_msg();msg=JointState();msg.header.stamp=now;msg.name=list(state);msg.position=list(state.values());publisher.publish(msg)
                collection=[]
                def marker(kind,color):
                    m=Marker();m.header.frame_id='world';m.header.stamp=now;m.ns='view_design';m.id=len(collection);m.type=kind;m.action=Marker.ADD;m.pose.orientation.w=1.;m.color.r,m.color.g,m.color.b=color;m.color.a=1.;collection.append(m);return m
                label=marker(Marker.TEXT_VIEW_FACING,[1.,1.,1.]);label.pose.position.z=2.3;label.scale.z=.10;label.text='PROPOSAL ONLY - NO ROBOT MOTION - domain70\nRough OAK pose / approximate base mounts / hardware review pending'
                C=np.array(data['T_world_oak_optical']);eye=C[:3,3]
                body=marker(Marker.SPHERE,[1.,.2,.1]);body.pose.position.x,body.pose.position.y,body.pose.position.z=eye.tolist();body.scale.x=body.scale.y=body.scale.z=.08
                line=marker(Marker.LINE_LIST,[1.,.3,.1]);line.scale.x=.008
                floor=eye.copy();floor[2]=0.;line.points=[Point(x=float(x),y=float(y),z=float(z)) for x,y,z in [eye,floor,eye,eye+C[:3,2]*1.8]]
                colors=[[.3,.6,1.],[.3,1.,.5],[1.,.65,.1],[.8,.4,1.]]
                for (rid,entry),color in zip(data['arms'].items(),colors):
                    camera=np.array(entry['camera_world']);table='left' if rid.startswith('left') else 'right';B=np.array(data['world_boards'][table]);centre=(B@np.array([.14,.1,0,1]))[:3]
                    m=marker(Marker.LINE_LIST,color);m.scale.x=.005;m.points=[Point(x=float(x),y=float(y),z=float(z)) for x,y,z in [camera[:3,3],centre]]
                for table,pose in data['world_boards'].items():
                    B=np.array(pose);corners=np.array([[0,0,0],[.28,0,0],[.28,.2,0],[0,.2,0],[0,0,0]])@B[:3,:3].T+B[:3,3];m=marker(Marker.LINE_STRIP,[.2,1.,.3]);m.scale.x=.008;m.points=[Point(x=float(x),y=float(y),z=float(z)) for x,y,z in corners]
                markers.publish(MarkerArray(markers=collection));rclpy.spin_once(node,timeout_sec=.05);time.sleep(.05)
    finally:
        for child in children:
            if child.poll() is None:
                try:os.killpg(child.pid,signal.SIGINT)
                except ProcessLookupError:pass
        for child in children:
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        node.destroy_node();rclpy.shutdown()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--proposal',required=True);a=parser.parse_args();preview(a.source,a.proposal)


if __name__=='__main__':main()

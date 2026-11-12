"""Read-only animation in domain68; never imports hardware command clients."""
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


def preview(path,domain=68):
    if type(domain) is not int or not 68<=domain<=232:
        raise ValueError('Preview requires an isolated ROS domain68..232')
    import rclpy
    from sensor_msgs.msg import JointState
    from visualization_msgs.msg import Marker,MarkerArray
    from geometry_msgs.msg import Point
    plan=json.loads(Path(path).read_text())
    os.environ['ROS_DOMAIN_ID']=str(domain)
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    environment=os.environ.copy()
    # Same host-library cleanup as scripts/control.sh for VS Code Snap terminals.
    for key in ('GTK_PATH','GTK_EXE_PREFIX','GTK_IM_MODULE_FILE','GIO_MODULE_DIR','GSETTINGS_SCHEMA_DIR'):
        if '/snap/' in environment.get(key,''):environment.pop(key,None)
    processes=[]
    with tempfile.TemporaryDirectory(prefix='uwa-parking-preview-') as directory:
        directory=Path(directory)
        parameters=directory/'robot.yaml'
        parameters.write_text(yaml.safe_dump({'/**':{'ros__parameters':{
            'robot_description':plan['description'],'use_sim_time':False}}}))
        from ament_index_python.packages import get_package_share_directory
        config=yaml.safe_load((Path(get_package_share_directory('uwa_cell_gazebo'))/'rviz/cell.rviz').read_text())
        manager=config['Visualization Manager']
        grid=manager['Displays'][0]
        robot=manager['Displays'][1]
        robot.update(Name=plan.get('purpose','PARKING').upper()+' PREVIEW - no hardware commands',Alpha=1.)
        robot['Description Topic']['Value']='/robot_description'
        manager['Displays']=[grid,robot,{'Class':'rviz_default_plugins/MarkerArray','Name':'Path and limitations',
            'Enabled':True,'Marker Topic':{'Value':'/uwa_parking/preview_markers'}}]
        config['Window Geometry']={'Width':1200,'Height':850}
        config_path=directory/(plan['arm']+'_preview.rviz');config_path.write_text(yaml.safe_dump(config))
        rclpy.init(args=[]);node=rclpy.create_node('uwa_parking_preview')
        publisher=node.create_publisher(JointState,'/joint_states',10)
        markers=node.create_publisher(MarkerArray,'/uwa_parking/preview_markers',10)
        initial=dict(plan['start'])
        for joint in ET.fromstring(plan['description']).findall('joint'):
            if joint.get('type') in ('revolute','prismatic') and joint.find('mimic') is None:
                name=joint.get('name')
                if name not in initial:
                    rid=next((r for r in plan['layout']['robots'] if name.startswith(r+'_')),None)
                    initial[name]=plan['layout']['robots'][rid]['tools']['gripper_initial_position'] if rid else 0.
        start=time.monotonic();names=list(initial)
        times=[p['time'] for p in plan['points']]
        try:
            for args in [['ros2','run','robot_state_publisher','robot_state_publisher','--ros-args','--params-file',str(parameters)],
                         ['ros2','run','rviz2','rviz2','-d',str(config_path)]]:
                processes.append(subprocess.Popen(args,start_new_session=True,env=environment))
            while rclpy.ok() and all(p.poll() is None for p in processes):
                elapsed=((time.monotonic()-start)*4)%(plan['duration']+8)
                elapsed=min(elapsed,plan['duration'])
                q=[float(np.interp(elapsed,times,[p['positions'][i] for p in plan['points']])) for i in range(6)]
                state=dict(initial,**dict(zip(plan['joint_names'],q)))
                msg=JointState();msg.header.stamp=node.get_clock().now().to_msg()
                msg.name=names;msg.position=[state[j] for j in names];publisher.publish(msg)
                line=Marker();line.header.frame_id='world';line.ns='parking_path';line.id=0
                line.type=Marker.LINE_STRIP;line.action=Marker.ADD;line.pose.orientation.w=1.
                line.scale.x=.01;line.color.r=1.;line.color.g=.6;line.color.a=1.
                line.points=[Point(x=p[0],y=p[1],z=p[2]) for p in plan['tool_path_world']]
                label=Marker();label.header.frame_id='world';label.ns='parking_path';label.id=1
                label.type=Marker.TEXT_VIEW_FACING;label.action=Marker.ADD;label.pose.orientation.w=1.
                label.pose.position.z=2.1;label.scale.z=.09
                label.color.r=1.;label.color.g=1.;label.color.a=1.
                label.text=f"PREVIEW ONLY · {plan['mode'].upper()} · {plan['arm']} · playback 4x · domain{domain}\n"
                label.text+=('UNOBSERVED: '+', '.join(plan['unobserved_arms']) if plan['unobserved_arms']
                             else 'Checked model path · real geometry remains provisional')
                home=[r for r,s in plan['state_sources'].items() if s=='user_nominal_home']
                if home:label.text+='\nUser-declared nominal Home (not measured): '+', '.join(home)
                if plan.get('independent_diagonal_arm'):
                    label.text+='\nIndependent diagonal arm: '+plan['independent_diagonal_arm']+' (snapshot shown)'
                markers.publish(MarkerArray(markers=[line,label]))
                rclpy.spin_once(node,timeout_sec=.05)
            failed=[p.returncode for p in processes if p.poll() not in (None,0)]
            if failed:raise RuntimeError(f'Preview process failed: {failed}')
        finally:
            for process in processes:
                if process.poll() is None:
                    try:os.killpg(process.pid,signal.SIGINT)
                    except ProcessLookupError:pass
            for process in processes:
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:os.killpg(process.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
            node.destroy_node();rclpy.shutdown()

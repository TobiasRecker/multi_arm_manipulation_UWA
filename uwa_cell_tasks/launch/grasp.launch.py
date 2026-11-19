"""Separate world/ROS namespace in domain64; never replace the shared cell."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import yaml
import numpy as np
from scipy.spatial.transform import Rotation
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction,ExecuteProcess,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uwa_cell_description.configuration import default_layout_path,load_layout,controller_names
from uwa_cell_tasks.scene import verify_scene,physics_description


def setup(context):
    directory=Path(LaunchConfiguration('scene').perform(context)).resolve()
    verify_scene(directory)
    ns=LaunchConfiguration('namespace').perform(context).rstrip('/')
    if not ns.startswith('/uwa_grasp_'):raise ValueError('Use an isolated /uwa_grasp_* simulation namespace')
    layout_file=LaunchConfiguration('layout').perform(context);layout=load_layout(layout_file)
    params=yaml.safe_load((directory/'model/controllers.yaml').read_text())
    params={key.replace('/uwa_cell',ns,1):value for key,value in params.items()}
    params[ns+'/controller_manager']['ros__parameters']['enforce_command_limits']=False
    for value in params.values():
        constraints=value['ros__parameters'].get('constraints')
        if constraints:
            constraints['stopped_velocity_tolerance']=0.
    param_file=directory/'controllers.live.yaml';param_file.write_text(yaml.safe_dump(params))
    description=(directory/'robot.urdf').read_text().replace('/uwa_cell/',ns+'/')
    root=ET.fromstring(description)
    plugin=root.find("gazebo/plugin[@name='gz_ros2_control::GazeboSimROS2ControlPlugin']")
    plugin.find('parameters').text=str(param_file);plugin.find('ros/namespace').text=ns
    root.find("gazebo/plugin[@name='uwa_cell_tasks::TaskTelemetry']/ros_namespace").text=ns
    ET.SubElement(plugin.find('ros'),'remapping').text='/clock:='+ns+'/clock'
    for reference in root.findall('gazebo'):
        for sensor in list(reference.findall('sensor')):reference.remove(sensor)
    description=ET.tostring(root,encoding='unicode')
    physics_file=directory/'robot.physics.urdf';physics_file.write_text(physics_description(description))
    world=directory/'world.live.sdf';wroot=ET.parse(directory/'world.sdf').getroot()
    wroot=ET.fromstring(ET.tostring(wroot,encoding='unicode').replace('/uwa_cell/',ns+'/'))
    observer=wroot.find("world/plugin[@name='uwa_cell_tasks::ForceTelemetry']")
    if observer is not None:observer.find('ros_namespace').text=ns
    for model in wroot.find('world').findall('model'):
        for link in model.findall('link'):
            for sensor in list(link.findall('sensor')):link.remove(sensor)
    world.write_text(ET.tostring(wroot,encoding='unicode'))
    clock=[('/clock',ns+'/clock')]
    server=ExecuteProcess(cmd=['gz','sim','-s','-r',str(world),'--headless-rendering','-v','2'],output='screen')
    spawn=Node(package='ros_gz_sim',executable='create',namespace=ns,
        arguments=['-world','uwa_grasp_lab','-name','uwa_cell_grasp','-allow_renaming','false','-file',str(physics_file)],output='screen')
    pose=np.array(json.loads((directory/'scene.json').read_text())['T_world_object'])
    angles=Rotation.from_matrix(pose[:3,:3]).as_euler('xyz')
    pose_args=[str(v) for pair in zip(('-x','-y','-z','-R','-P','-Y'),[*pose[:3,3],*angles]) for v in pair]
    carton=Node(package='ros_gz_sim',executable='create',namespace=ns,
        arguments=['-world','uwa_grasp_lab','-name','uwa_grasp_carton','-allow_renaming','false','-file',str(directory/'carton.sdf')]+pose_args,output='screen')
    actions=[server,RegisterEventHandler(OnProcessExit(target_action=server,on_exit=[EmitEvent(event=Shutdown(reason='Own grasp world exited'))])),
        Node(package='robot_state_publisher',executable='robot_state_publisher',namespace=ns,
            parameters=[dict(robot_description=description,use_sim_time=True)],remappings=clock+[('/tf',ns+'/tf'),('/tf_static',ns+'/tf_static')],output='screen'),
        Node(package='uwa_cell_tasks',executable='cell_task',namespace=ns,
            arguments=['camera','--namespace',ns,'--scene',str(directory)],output='screen')]
    sequence=[spawn,carton]
    for name in controller_names(layout)+['rigid_object_controller']:
        inactive=name=='rigid_object_controller'
        sequence.append(Node(package='controller_manager',executable='spawner',namespace=ns,
            arguments=[name,'-c',ns+'/controller_manager','--controller-manager-timeout','90','--param-file',str(param_file)]+(['--inactive'] if inactive else []),output='screen'))
    for previous,following in zip(sequence,sequence[1:]):
        actions.append(RegisterEventHandler(OnProcessExit(target_action=previous,
            on_exit=lambda event,ctx,n=following:[n] if event.returncode==0 else [EmitEvent(event=Shutdown(reason='Own grasp startup failed'))])))
    actions.append(RegisterEventHandler(OnProcessExit(target_action=sequence[-1],on_exit=lambda event,ctx:
        [] if event.returncode==0 else [EmitEvent(event=Shutdown(reason='Own grasp startup failed'))])))
    actions.append(spawn)
    return actions


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('scene'),
        DeclareLaunchArgument('namespace',default_value='/uwa_grasp_validation'),
        DeclareLaunchArgument('layout',default_value=str(default_layout_path())),OpaqueFunction(function=setup)])

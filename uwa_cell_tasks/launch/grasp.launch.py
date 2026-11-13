"""Separate world/ROS namespace in domain64; never replace the shared cell."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction,ExecuteProcess,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uwa_cell_description.configuration import default_layout_path,load_layout,controller_names,joint_names,gripper_joint
from uwa_cell_tasks.guard import supervisor_remaps


def setup(context):
    directory=Path(LaunchConfiguration('scene').perform(context)).resolve()
    ns=LaunchConfiguration('namespace').perform(context).rstrip('/')
    if not ns.startswith('/') or ns in ('/','/uwa_hardware','/uwa_cell'):raise ValueError('Use an isolated simulation namespace')
    layout_file=LaunchConfiguration('layout').perform(context);layout=load_layout(layout_file)
    params=yaml.safe_load((directory/'model/controllers.yaml').read_text())
    params={key.replace('/uwa_cell',ns,1):value for key,value in params.items()}
    manager=params[ns+'/controller_manager']['ros__parameters']
    for arm in layout['robots']:
        name=arm+'_collision_hold_controller';manager[name]={'type':'uwa_cell_motion/CollisionHold'}
        params[ns+'/'+name]={'ros__parameters':dict(joints=joint_names(arm)+[gripper_joint(arm)],deceleration=.5,use_sim_time=True)}
    param_file=directory/'controllers.live.yaml';param_file.write_text(yaml.safe_dump(params))
    description=(directory/'robot.urdf').read_text().replace('/uwa_cell/',ns+'/')
    root=ET.fromstring(description)
    plugin=root.find("gazebo/plugin[@name='gz_ros2_control::GazeboSimROS2ControlPlugin']")
    plugin.find('parameters').text=str(param_file);plugin.find('ros/namespace').text=ns
    ET.SubElement(plugin.find('ros'),'remapping').text='/clock:='+ns+'/clock'
    for sensor in root.findall('gazebo/sensor'):
        if sensor.find('update_rate') is not None:sensor.find('update_rate').text='1'
    description=ET.tostring(root,encoding='unicode')
    world=directory/'world.live.sdf';wroot=ET.parse(directory/'world.sdf').getroot()
    sensors=ET.SubElement(wroot.find('world'),'plugin',filename='gz-sim-sensors-system',name='gz::sim::systems::Sensors')
    ET.SubElement(sensors,'render_engine').text='ogre2';world.write_text(ET.tostring(wroot,encoding='unicode'))
    clock=[('/clock',ns+'/clock')]
    server=ExecuteProcess(cmd=['gz','sim','-s','-r',str(world),'--headless-rendering','-v','2'],output='screen')
    spawn=Node(package='ros_gz_sim',executable='create',namespace=ns,
        arguments=['-world','uwa_grasp_lab','-name','uwa_cell_grasp','-allow_renaming','false','-topic',ns+'/robot_description'],output='screen')
    carton=Node(package='ros_gz_sim',executable='create',namespace=ns,
        arguments=['-world','uwa_grasp_lab','-name','uwa_grasp_carton','-allow_renaming','false','-file',str(directory/'carton.sdf')],output='screen')
    actions=[server,RegisterEventHandler(OnProcessExit(target_action=server,on_exit=[EmitEvent(event=Shutdown(reason='Own grasp world exited'))])),
        Node(package='robot_state_publisher',executable='robot_state_publisher',namespace=ns,
            parameters=[dict(robot_description=description,use_sim_time=True)],remappings=clock+[('/tf',ns+'/tf'),('/tf_static',ns+'/tf_static')],output='screen'),
        Node(package='uwa_cell_tasks',executable='cell_task',namespace=ns,
            arguments=['bridge','--namespace',ns,'--world','uwa_grasp_lab'],output='screen')]
    sequence=[spawn,carton]
    for name in controller_names(layout)+['rigid_object_controller']+[a+'_collision_hold_controller' for a in layout['robots']]:
        inactive=name=='rigid_object_controller' or name.endswith('_collision_hold_controller')
        sequence.append(Node(package='controller_manager',executable='spawner',namespace=ns,
            arguments=[name,'-c',ns+'/controller_manager','--controller-manager-timeout','90','--param-file',str(param_file)]+(['--inactive'] if inactive else []),output='screen'))
    guard_topics=['joint_states','tasks/object_truth','tasks/contacts','tasks/heartbeat','tasks/group','collision_supervisor/status']
    remaps=clock+[('/uwa_cell/'+t,ns+'/'+t) for t in guard_topics]
    guard=Node(package='uwa_cell_tasks',executable='cell_task',namespace=ns,name='collision_guard',
        arguments=['guard','--scene',str(directory),'--layout',layout_file],remappings=remaps,output='screen')
    supervisor=Node(package='uwa_cell_tasks',executable='cell_task',namespace=ns,name='collision_supervisor',
        arguments=['supervisor','--layout',layout_file],remappings=supervisor_remaps(ns),output='screen')
    for previous,following in zip(sequence,sequence[1:]):
        actions.append(RegisterEventHandler(OnProcessExit(target_action=previous,
            on_exit=lambda event,ctx,n=following:[n] if event.returncode==0 else [EmitEvent(event=Shutdown(reason='Own grasp startup failed'))])))
    actions.append(RegisterEventHandler(OnProcessExit(target_action=sequence[-1],on_exit=lambda event,ctx:[guard,supervisor] if event.returncode==0 else [])))
    actions.append(spawn)
    return actions


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('scene'),
        DeclareLaunchArgument('namespace',default_value='/uwa_grasp_validation'),
        DeclareLaunchArgument('layout',default_value=str(default_layout_path())),OpaqueFunction(function=setup)])

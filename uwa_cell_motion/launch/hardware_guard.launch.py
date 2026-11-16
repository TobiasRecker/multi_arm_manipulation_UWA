"""Explicit hardware backend. Default monitor never changes controllers/programs."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from pathlib import Path
import tempfile


def start(context):
    mode=LaunchConfiguration('mode').perform(context);inventory=LaunchConfiguration('inventory').perform(context)
    armed=LaunchConfiguration('armed').perform(context).lower()=='true'
    arguments=['--mode',mode,'--inventory',inventory]
    config=LaunchConfiguration('config').perform(context)
    if config:arguments+=['--config',config]
    layout=LaunchConfiguration('layout').perform(context)
    if layout:arguments+=['--layout',layout]
    nodes=[Node(package='uwa_cell_motion',executable='cell_hardware_motion',name='hardware_'+role,
        arguments=arguments+[role]+(['--armed'] if armed else []),output='screen') for role in ('guard','supervisor','watchdog')]
    from uwa_cell_motion.hardware_model import HardwareProblem
    from uwa_cell_motion.common import config as load_config
    from ament_index_python.packages import get_package_share_directory
    share=Path(get_package_share_directory('uwa_cell_motion'))
    with tempfile.TemporaryDirectory() as directory:
        model=HardwareProblem(directory,load_config(config or share/'config/hardware_motion.yaml'),inventory,layout or None)
        nodes.append(Node(package='robot_state_publisher',executable='robot_state_publisher',namespace='/uwa_cell',name='hardware_model',
            parameters=[{'robot_description':model.description,'use_sim_time':False,'publish_frequency':20.}],
            remappings=[('joint_states','/uwa_cell/model_joint_states')],output='screen'))
    if LaunchConfiguration('rviz').perform(context).lower()=='true':
        nodes.append(Node(package='rviz2',executable='rviz2',name='hardware_motion_rviz',arguments=['-d',str(share/'rviz/hardware.rviz')],output='screen'))
    return nodes


def generate_launch_description():
    from uwa_cell_motion.hardware_model import inventory_path
    return LaunchDescription([DeclareLaunchArgument('mode',default_value='mock'),
        DeclareLaunchArgument('inventory',default_value=str(inventory_path())),DeclareLaunchArgument('armed',default_value='false'),
        DeclareLaunchArgument('config',default_value=''),DeclareLaunchArgument('layout',default_value=''),DeclareLaunchArgument('rviz',default_value='false'),OpaqueFunction(function=start)])

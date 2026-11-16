"""Explicit hardware backend. Default monitor never changes controllers/programs."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    mode=LaunchConfiguration('mode').perform(context);inventory=LaunchConfiguration('inventory').perform(context)
    armed=LaunchConfiguration('armed').perform(context).lower()=='true'
    arguments=['--mode',mode,'--inventory',inventory]
    config=LaunchConfiguration('config').perform(context)
    if config:arguments+=['--config',config]
    layout=LaunchConfiguration('layout').perform(context)
    if layout:arguments+=['--layout',layout]
    return [Node(package='uwa_cell_motion',executable='cell_hardware_motion',name='hardware_'+role,
        arguments=arguments+[role]+(['--armed'] if armed else []),output='screen') for role in ('guard','supervisor','watchdog')]


def generate_launch_description():
    from uwa_cell_motion.hardware_model import inventory_path
    return LaunchDescription([DeclareLaunchArgument('mode',default_value='mock'),
        DeclareLaunchArgument('inventory',default_value=str(inventory_path())),DeclareLaunchArgument('armed',default_value='false'),
        DeclareLaunchArgument('config',default_value=''),DeclareLaunchArgument('layout',default_value=''),OpaqueFunction(function=start)])

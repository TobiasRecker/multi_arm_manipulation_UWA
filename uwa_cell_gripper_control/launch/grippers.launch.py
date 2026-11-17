"""Four persistent interfaces; zero physical command on launch or shutdown."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    from uwa_cell_gripper_control.api import ARMS
    mode=LaunchConfiguration('mode').perform(context)
    enabled=LaunchConfiguration('actuate').perform(context).lower()=='true'
    arguments=['--mode',mode,'--max-force-raw',LaunchConfiguration('max_force_raw').perform(context),
               '--max-speed-raw',LaunchConfiguration('max_speed_raw').perform(context)]
    if enabled:arguments.append('--actuate')
    return [Node(package='uwa_cell_gripper_control',executable='cell_gripper_node',
                 arguments=arguments+['--arm',arm],output='screen') for arm in ARMS]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('mode',default_value='mock'),
        DeclareLaunchArgument('actuate',default_value='false'),
        DeclareLaunchArgument('max_force_raw',default_value='0'),
        DeclareLaunchArgument('max_speed_raw',default_value='32'),OpaqueFunction(function=start)])

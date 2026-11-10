"""UWA client of shared MATCH UR bringup. Mock is the default."""
import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,IncludeLaunchDescription,SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration,PythonExpression


def generate_launch_description():
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    return LaunchDescription([
        DeclareLaunchArgument('inventory',default_value=str(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml')),
        DeclareLaunchArgument('arms',default_value='right_front,right_rear'),
        DeclareLaunchArgument('mode',default_value='mock',choices=['mock','hardware']),
        SetEnvironmentVariable('ROS_DOMAIN_ID',PythonExpression([
            "'67' if '",LaunchConfiguration('mode'),"' == 'mock' else '66'"])),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(Path(get_package_share_directory('match_ur_hardware'))/'launch/arms.launch.py')),
          launch_arguments={key:LaunchConfiguration(key) for key in ['inventory','arms','mode']}.items())])

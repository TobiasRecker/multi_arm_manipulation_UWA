"""Calibration processes only. The isolated Gazebo cell must already be running."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uwa_cell_gazebo.configuration import default_layout_path

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('gui',default_value='true'),
        DeclareLaunchArgument('layout',default_value=str(default_layout_path())),
        SetEnvironmentVariable('ROS_DOMAIN_ID','64'),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST'),
        SetEnvironmentVariable('GZ_PARTITION','uwa_cell_sim'),SetEnvironmentVariable('GZ_IP','127.0.0.1'),
        Node(package='uwa_cell_calibration',executable='calibration_backend',
             parameters=[{'layout':LaunchConfiguration('layout'),'use_sim_time':True}],output='screen'),
        # No exit handler kills the backend when the GUI disappears: its independent
        # wall-time watchdog must first cancel and confirm motion stop.
        Node(package='uwa_cell_calibration',executable='calibration_gui',
             condition=IfCondition(LaunchConfiguration('gui')),output='screen'),
    ])

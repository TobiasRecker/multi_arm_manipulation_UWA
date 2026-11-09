"""Calibration processes only. The isolated Gazebo cell must already be running."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,SetEnvironmentVariable,OpaqueFunction,LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uwa_cell_gazebo.configuration import default_layout_path
import fcntl,os,tempfile
from pathlib import Path


def backend_if_needed(context):
    with (Path(tempfile.gettempdir())/f'uwa-cell-calibration-{os.getuid()}-64.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return [LogInfo(msg='UWA calibration backend already running; attaching GUI to its current layout.')]
        fcntl.flock(lock,fcntl.LOCK_UN)
    return [Node(package='uwa_cell_calibration',executable='calibration_backend',
                 parameters=[{'layout':LaunchConfiguration('layout'),'use_sim_time':True}],output='screen')]

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('gui',default_value='true'),
        DeclareLaunchArgument('layout',default_value=str(default_layout_path())),
        SetEnvironmentVariable('ROS_DOMAIN_ID','64'),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST'),
        SetEnvironmentVariable('GZ_PARTITION','uwa_cell_sim'),SetEnvironmentVariable('GZ_IP','127.0.0.1'),
        OpaqueFunction(function=backend_if_needed),
        # No exit handler kills the backend when the GUI disappears: its independent
        # wall-time watchdog must first cancel and confirm motion stop.
        Node(package='uwa_cell_calibration',executable='calibration_gui',
             condition=IfCondition(LaunchConfiguration('gui')),output='screen'),
    ])

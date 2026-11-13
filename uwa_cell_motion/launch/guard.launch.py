"""Explicitly arm simulation-only guard and independent resource supervisor."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uwa_cell_description.configuration import default_layout_path
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('layout',default_value=str(default_layout_path())),
        DeclareLaunchArgument('config',default_value=str(Path(get_package_share_directory('uwa_cell_motion'))/'config/motion.yaml')),
        Node(package='uwa_cell_motion',executable='cell_motion',name='collision_guard',
             arguments=['guard','--layout',LaunchConfiguration('layout'),'--config',LaunchConfiguration('config')],output='screen'),
        Node(package='uwa_cell_motion',executable='cell_motion',name='collision_supervisor',
             arguments=['supervisor','--layout',LaunchConfiguration('layout'),'--config',LaunchConfiguration('config')],output='screen'),
    ])

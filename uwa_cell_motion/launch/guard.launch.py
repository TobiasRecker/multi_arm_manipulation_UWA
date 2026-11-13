"""Explicitly arm simulation-only guard and independent resource supervisor."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from uwa_cell_description.configuration import default_layout_path


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('layout',default_value=str(default_layout_path())),
        Node(package='uwa_cell_motion',executable='cell_motion',name='collision_guard',
             arguments=['guard','--layout',LaunchConfiguration('layout')],output='screen'),
        Node(package='uwa_cell_motion',executable='cell_motion',name='collision_supervisor',
             arguments=['supervisor','--layout',LaunchConfiguration('layout')],output='screen'),
    ])

"""Explicit real OAK use, camera-only domain65; tracker starts idle."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('reference'),DeclareLaunchArgument('fps',default_value='10.0'),
        SetEnvironmentVariable('ROS_DOMAIN_ID','65'),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST'),
        Node(package='uwa_cell_tracking',executable='oak_tracking_stream',output='screen',
             parameters=[{'fps':LaunchConfiguration('fps')}]),
        Node(package='uwa_cell_tracking',executable='object_tracker',output='screen',parameters=[{
            'reference':LaunchConfiguration('reference'),'use_sim_time':False,
            'image_topic':'/oak4/tracking/image_raw','camera_info_topic':'/oak4/tracking/camera_info'}])])

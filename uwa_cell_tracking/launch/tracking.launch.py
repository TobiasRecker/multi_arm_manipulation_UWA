"""Subscribe to explicit camera topics; no camera/robot is started implicitly."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    defaults={'reference':'','image_topic':'/uwa_cell/oak_overview/rgb/image_raw',
        'camera_info_topic':'/uwa_cell/oak_overview/rgb/camera_info','use_sim_time':'true'}
    return LaunchDescription([*[DeclareLaunchArgument(k,default_value=v) for k,v in defaults.items()],
        Node(package='uwa_cell_tracking',executable='object_tracker',output='screen',
             parameters=[{k:LaunchConfiguration(k) for k in defaults}])])

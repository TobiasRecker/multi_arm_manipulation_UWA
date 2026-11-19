"""Add marker props and optionally RViz to an isolated grasp cell."""
from pathlib import Path
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from uwa_cell_description.configuration import default_layout_path


def setup(context):
    ns = LaunchConfiguration('namespace').perform(context).rstrip('/')
    if not ns.startswith('/uwa_grasp_'):
        raise ValueError('Use an isolated /uwa_grasp_* simulation namespace')
    layout = LaunchConfiguration('layout').perform(context)
    remappings = [(name, ns+name) for name in ('/tf', '/tf_static', '/clock')]
    actions = [
        Node(package='uwa_cell_gazebo', executable='scene_assets', namespace=ns,
             parameters=[{'layout': layout, 'world': 'uwa_grasp_lab',
                          'marker_only': True, 'use_sim_time': True}],
             remappings=remappings, output='screen')
    ]
    if LaunchConfiguration('rviz').perform(context).lower() == 'true':
        share = Path(get_package_share_directory('uwa_cell_gazebo'))
        config = yaml.safe_load((share/'rviz/cell.rviz').read_text())
        manager = config['Visualization Manager']
        displays = []
        for display in manager['Displays']:
            kind = display['Class'].rsplit('/', 1)[-1]
            if kind in ('Grid', 'TF'):
                displays.append(display)
            elif kind == 'RobotModel' and display['Description Topic']['Value'] == '/uwa_cell/robot_description':
                display['Description Topic']['Value'] = ns+'/robot_description'
                displays.append(display)
            elif kind == 'MarkerArray' and display['Topic']['Value'] == '/uwa_cell/scene_assets/markers':
                display['Topic']['Value'] = ns+'/scene_assets/markers'
                display['Name'] = 'Marker and tabletop dock'
                displays.append(display)
        manager['Displays'] = displays
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rviz', prefix='uwa_grasp_', delete=False) as handle:
            yaml.safe_dump(config, handle)
        path = Path(handle.name)
        actions.extend([
            RegisterEventHandler(OnShutdown(on_shutdown=lambda event, ctx: path.unlink(missing_ok=True))),
            Node(package='rviz2', executable='rviz2', name='grasp_rviz', namespace=ns,
                 arguments=['-d', str(path)], parameters=[{'use_sim_time': True}],
                 remappings=remappings, output='screen')
        ])
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='/uwa_grasp_validation'),
        DeclareLaunchArgument('layout', default_value=str(default_layout_path())),
        DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false']),
        OpaqueFunction(function=setup),
    ])

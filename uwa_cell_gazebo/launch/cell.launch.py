"""An isolated, simulated cell; no Universal Robots hardware driver is used."""
from pathlib import Path
import shutil
import tempfile

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, EmitEvent, ExecuteProcess, LogInfo, OpaqueFunction,
    RegisterEventHandler, SetEnvironmentVariable,
)
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from uwa_cell_gazebo.configuration import (
    ROBOT_IDS, default_layout_path, load_layout, render_description,
)


def enabled(context, name):
    value = LaunchConfiguration(name).perform(context).lower()
    if value not in ('true', 'false'):
        raise ValueError(f'{name} must be true or false')
    return value == 'true'


def setup(context):
    layout_path = str(Path(LaunchConfiguration('layout').perform(context)).expanduser().resolve())
    layout = load_layout(layout_path)
    directory = Path(tempfile.mkdtemp(prefix='uwa_cell_'))
    try:
        description, controllers = render_description(layout, directory)
    except Exception:
        shutil.rmtree(directory)
        raise
    share = Path(get_package_share_directory('uwa_cell_gazebo'))
    world = share / 'worlds/uwa_lab.sdf'
    server = ExecuteProcess(
        cmd=['gz', 'sim', '-s', '-r', str(world), '-v', '2'],
        name='uwa_gazebo_server', output='screen')
    spawn = Node(
        package='ros_gz_sim', executable='create', name='spawn_cell', namespace='uwa_cell',
        arguments=['-world', 'uwa_lab', '-name', 'uwa_cell', '-allow_renaming', 'false',
                   '-topic', '/uwa_cell/robot_description'], output='screen')
    actions = [
        RegisterEventHandler(OnShutdown(on_shutdown=lambda event, ctx:
            shutil.rmtree(directory, ignore_errors=True))),
        LogInfo(msg='UWA simulation: ROS domain 64, localhost only; no hardware drivers.'),
        server,
        RegisterEventHandler(OnProcessExit(target_action=server, on_exit=[
            EmitEvent(event=Shutdown(reason='Gazebo server exited'))])),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             namespace='uwa_cell', name='robot_state_publisher',
             parameters=[{'robot_description': description, 'use_sim_time': True}],
             output='screen'),
        Node(package='uwa_cell_gazebo', executable='clock_bridge', name='clock_bridge',
             namespace='uwa_cell',
             output='screen'),
    ]
    if enabled(context, 'gui'):
        # The gz-sim-main wrapper leaves its GUI child behind on SIGINT on this
        # Jetty installation. Launch the packaged client directly instead.
        vendor = Path(get_package_prefix('gz_sim_vendor')) / 'opt/gz_sim_vendor'
        clients = list(vendor.glob('libexec/gz/sim*/gz-sim-gui-client'))
        if len(clients) != 1:
            raise RuntimeError(f'Expected one Gazebo GUI client under {vendor}, found {clients}')
        actions.append(ExecuteProcess(cmd=[str(clients[0]), '-v', '2',
                                          '--gui-config', str(share / 'worlds/cell.gui.config')],
                                      name='uwa_gazebo_gui', output='screen'))
    if enabled(context, 'rviz'):
        actions.append(Node(package='rviz2', executable='rviz2',
                            arguments=['-d', str(share / 'rviz/cell.rviz')],
                            parameters=[{'use_sim_time': True}], output='screen'))
    if enabled(context, 'scan'):
        actions.append(Node(package='uwa_cell_gazebo', executable='scan_reference',
                            namespace='uwa_cell', parameters=[{
                                'layout': layout_path, 'use_sim_time': True}], output='screen'))

    controllers_to_start = ['joint_state_broadcaster'] + [
        f'{robot_id}_trajectory_controller' for robot_id in ROBOT_IDS]
    spawners = [Node(
        package='controller_manager', executable='spawner', namespace='uwa_cell',
        arguments=[name, '-c', '/uwa_cell/controller_manager',
                   '--controller-manager-timeout', '90', '--param-file', str(controllers)],
        output='screen') for name in controllers_to_start]

    # Serialize spawners: controller_manager uses a shared loading/switching lock.
    sequence = [spawn] + spawners
    for previous, following in zip(sequence, sequence[1:]):
        def next_on_success(event, ctx, next_action=following):
            if event.returncode == 0:
                return [next_action]
            return [EmitEvent(event=Shutdown(reason='Cell spawn/controller startup failed'))]
        actions.append(RegisterEventHandler(OnProcessExit(
            target_action=previous, on_exit=next_on_success)))
    if enabled(context, 'controller_gui'):
        # Wait until all four controllers exist before opening the selector.
        controller_gui = Node(
            package='rqt_joint_trajectory_controller', executable='rqt_joint_trajectory_controller',
            namespace='uwa_cell', output='screen')
        def open_control(event, ctx):
            if event.returncode == 0:
                return [controller_gui]
            return [EmitEvent(event=Shutdown(reason='Final controller failed to start'))]
        actions.append(RegisterEventHandler(OnProcessExit(
            target_action=spawners[-1], on_exit=open_control)))
    actions.append(spawn)
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('layout', default_value=str(default_layout_path())),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('controller_gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('scan', default_value='false'),
        SetEnvironmentVariable('ROS_DOMAIN_ID', '64'),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST'),
        SetEnvironmentVariable('GZ_PARTITION', 'uwa_cell_sim'),
        SetEnvironmentVariable('GZ_IP', '127.0.0.1'),
        SetEnvironmentVariable('QT_QPA_PLATFORM', 'xcb'),
        OpaqueFunction(function=setup),
    ])

"""Read-only visualization; does not launch a UR hardware driver."""
import os
import fcntl
from pathlib import Path
import shutil
import tempfile

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction,RegisterEventHandler,SetEnvironmentVariable
from launch.actions import LogInfo
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from uwa_cell_visualization.model import ARMS,description,load_inputs,paths

_locks=[]


def setup(context):
    def value(name):return LaunchConfiguration(name).perform(context)
    lock=open(f'/tmp/uwa-measured-overlay-{os.getuid()}-{value("target_domain")}.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return [LogInfo(msg='Measured overlay already running in this domain; reusing it. Stop it before changing its layout/offset.')]
    _locks.append(lock)
    inventory=value('inventory');layout_path=value('layout');arms=value('arms').split(',')
    profiles,layout=load_inputs(inventory,layout_path,arms)
    if value('use_sim_time') not in ('true','false'):raise ValueError('use_sim_time must be true or false')
    offset=[float(value('offset_'+axis)) for axis in 'xyz']
    directory=Path(tempfile.mkdtemp(prefix='uwa-measured-models-'))
    actions=[RegisterEventHandler(OnShutdown(on_shutdown=lambda event,ctx:shutil.rmtree(directory,ignore_errors=True)))]
    for rid in arms:
        model=description(profiles[rid],layout,offset);(directory/(rid+'.urdf')).write_text(model)
        actions.append(Node(package='robot_state_publisher',executable='robot_state_publisher',
            name='measured_state_publisher',namespace='/uwa_cell/real/'+rid,
            parameters=[{'robot_description':ParameterValue(model,value_type=str),
                'use_sim_time':value('use_sim_time')=='true',
                'publish_frequency':30.,'ignore_timestamp':True}],
            remappings=[('robot_description','internal_description'),('/tf','/tf'),('/tf_static','/tf_static')],
            output='screen'))
    actions.append(Node(package='uwa_cell_visualization',executable='hardware_overlay',output='screen',
        arguments=['--inventory',inventory,'--layout',layout_path,'--arms',','.join(arms),
            '--models-dir',str(directory),'--source-domain',value('source_domain'),
            '--target-domain',value('target_domain'),'--use-sim-time',value('use_sim_time'),
            '--stale-after',value('stale_after'),'--offset',*map(str,offset)]))
    return actions


def generate_launch_description():
    workspace=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    defaults={'inventory':str(workspace/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'),
        'layout':str(paths()),'arms':','.join(ARMS),'source_domain':'66','target_domain':'64',
        'use_sim_time':'true','stale_after':'2.0','offset_x':'0.0','offset_y':'0.0','offset_z':'0.0'}
    return LaunchDescription([*[DeclareLaunchArgument(name,default_value=value) for name,value in defaults.items()],
        SetEnvironmentVariable('ROS_DOMAIN_ID',LaunchConfiguration('target_domain')),
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST'),OpaqueFunction(function=setup)])

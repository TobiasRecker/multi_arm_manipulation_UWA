#!/usr/bin/env python3
"""Four real GenericSystem managers plus the C++ core and Python execution adapter.

Domain67/LOCALHOST only. The generated URDF contains no physical driver and no
robot address. All controller goals are sent to synthetic, separated arms.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace as Box

os.environ['ROS_DOMAIN_ID'] = '67'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
os.environ['ROS_LOCALHOST_ONLY'] = '1'

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from controller_manager_msgs.srv import LoadController, ConfigureController, SwitchController, ListControllers
from sensor_msgs.msg import JointState
from std_msgs.msg import String, Float64MultiArray
from std_srvs.srv import Trigger
import yaml

from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.minimal_execution import MinimalHardwareClient

ARMS = tuple(ROBOT_IDS)
QOS = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                 reliability=ReliabilityPolicy.RELIABLE)


def model(directory, namespace):
    cell = '<robot name="four_mock"><link name="world"/>'
    config = dict(schema_version=1, model_signature='four-real-mock-managers',
                  urdf_path='cell.urdf', srdf_path='cell.srdf', arms={}, spheres={},
                  neighbor_margin_m=.04, rate_hz=20., state_timeout_s=.2)
    descriptions = {}
    controllers = {}
    for index, arm in enumerate(ARMS):
        ns = namespace + '/' + arm
        names = joint_names(arm)
        links = '<link name="base"/>'
        chain = ''
        parent = 'world'
        for j, name in enumerate(names):
            link = f'{arm}_link{j}'
            collision = '<collision><geometry><sphere radius="0.05"/></geometry></collision>' if j == 5 else ''
            cell += f'<link name="{link}">{collision}</link><joint name="{name}" type="revolute"><parent link="{parent}"/><child link="{link}"/>'
            if j == 0:
                cell += f'<origin xyz="{index*3} 0 1"/>'
            cell += '<axis xyz="0 0 1"/><limit lower="-3" upper="3" velocity="0.1" effort="10"/></joint>'
            parent = link
            links += f'<link name="link{j}"/>'
            chain += f'<joint name="{name}" type="revolute"><parent link="{"base" if j == 0 else "link"+str(j-1)}"/><child link="link{j}"/><axis xyz="0 0 1"/><limit lower="-3" upper="3" velocity="0.1" effort="10"/></joint>'
        interfaces = ''.join(f'<joint name="{name}"><command_interface name="position"/><command_interface name="velocity"/><state_interface name="position"><param name="initial_value">0</param></state_interface><state_interface name="velocity"><param name="initial_value">0</param></state_interface></joint>' for name in names)
        descriptions[arm] = '<robot name="mock_'+arm+'">'+links+chain+'<ros2_control name="mock_'+arm+'" type="system"><hardware><plugin>mock_components/GenericSystem</plugin><param name="calculate_dynamics">true</param></hardware>'+interfaces+'</ros2_control></robot>'
        config['arms'][arm] = dict(ip='', namespace=ns, joint_names=names)
        config['spheres'][arm] = [dict(link=parent, centre=[0.,0.,0.], radius=.05)]
        controller_file = directory/(arm+'.yaml')
        params = {ns+'/controller_manager': {'ros__parameters': dict(update_rate=100,
            joint_trajectory_controller=dict(type='uwa_cell_protection/PausableJointTrajectoryController',params_file=str(controller_file)),
            joint_state_broadcaster=dict(type='joint_state_broadcaster/JointStateBroadcaster',params_file=str(controller_file)),
            collision_hold_controller=dict(type='uwa_cell_motion/CollisionHold',params_file=str(controller_file)),
            forward_velocity_controller=dict(type='forward_command_controller/ForwardCommandController',params_file=str(controller_file)))},
            ns+'/joint_trajectory_controller': {'ros__parameters': dict(joints=names,
                command_interfaces=['position'], state_interfaces=['position','velocity'],
                allow_trajectory_replacement=False, pause_joint_acceleration=.2, pause_joint_velocity=.1,
                constraints=dict(stopped_velocity_tolerance=.2, goal_time=0.0))},
            ns+'/joint_state_broadcaster': {'ros__parameters': dict(joints=names,interfaces=['position','velocity'])},
            ns+'/collision_hold_controller': {'ros__parameters': dict(joints=names,deceleration=.2)},
            ns+'/forward_velocity_controller': {'ros__parameters': dict(joints=names,interface_name='velocity')}}
        # ROS parameter YAML forbids aliases; each controller gets its own list.
        controller_file.write_text(yaml.safe_dump(json.loads(json.dumps(params))))
        controllers[arm] = controller_file
    (directory/'cell.urdf').write_text(cell+'</robot>')
    (directory/'cell.srdf').write_text('<robot name="four_mock"/>')
    (directory/'model.json').write_text(json.dumps(config))
    return config, descriptions, controllers


def trajectory(arm, start, end, duration=2.):
    return dict(joint_names=joint_names(arm), duration_s=duration, points=[
        dict(time=0.,positions=[start]*6,velocities=[0.]*6,accelerations=[0.]*6),
        dict(time=duration,positions=[end]*6,velocities=[0.]*6,accelerations=[0.]*6)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    processes, logs = [], []
    rclpy.init()
    probe = rclpy.create_node('mock_cell_execution_validation')
    probe_executor = SingleThreadedExecutor()
    probe_executor.add_node(probe)
    namespace = '/uwa_mock_cell_'+str(os.getpid())
    status = {}
    pause_rows = defaultdict(dict)
    joint_rows = {}
    requested_ids = []
    captured_ids = []
    report = dict(success=False, domain=67, robot_commands=0, namespace=namespace, checks=[])
    with tempfile.TemporaryDirectory(prefix='uwa-mock-cell-') as temporary:
        directory = Path(temporary)
        os.environ['ROS_LOG_DIR'] = str(directory/'ros-logs')
        config, descriptions, controller_files = model(directory, namespace)
        def launch(command, name):
            log = (directory/(name+'.log')).open('w+')
            logs.append(log)
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,start_new_session=True)
            processes.append(process)
            return process
        def spin(seconds=.02):
            deadline = time.monotonic()+seconds
            while time.monotonic()<deadline:
                for process in processes:
                    if process.poll() is not None:
                        raise RuntimeError('Mock process exited: '+str(process.args))
                probe_executor.spin_once(timeout_sec=.005)
        def until(predicate, timeout=15.):
            deadline = time.monotonic()+timeout
            while not predicate():
                if time.monotonic()>deadline:
                    raise AssertionError('Mock integration timeout; protection='+repr(status))
                spin()
        rpc_clients = {}
        def rpc(kind,name,request):
            client = rpc_clients.get(name)
            if client is None:
                client = rpc_clients[name] = probe.create_client(kind,name)
            until(client.service_is_ready)
            future = client.call_async(request)
            until(future.done)
            return future.result()
        def switch(arm,activate=(),deactivate=()):
            return rpc(SwitchController,config['arms'][arm]['namespace']+'/controller_manager/switch_controller',
                       SwitchController.Request(activate_controllers=list(activate),deactivate_controllers=list(deactivate),strictness=2))
        def protection(operation):
            answer=rpc(Trigger,'/uwa_cell/protection/'+operation,Trigger.Request())
            if not answer.success:
                raise AssertionError(answer.message)
            return json.loads(answer.message)
        def got_status(msg):
            status.clear();status.update(json.loads(msg.data))
        probe.create_subscription(String,'/uwa_cell/protection/status',got_status,QOS)
        pubs=[]
        for arm in ARMS:
            ns=config['arms'][arm]['namespace']
            pub=probe.create_publisher(String,ns+'/robot_description',QOS)
            pubs.append(pub)
            probe.create_subscription(String,ns+'/joint_trajectory_controller/pause_status',
                lambda msg,arm=arm:pause_rows[arm].update(json.loads(msg.data)),QOS)
            probe.create_subscription(JointState,ns+'/joint_states',
                lambda msg,arm=arm:joint_rows.__setitem__(arm,msg),10)
            launch(['ros2','run','controller_manager','ros2_control_node','--ros-args','--params-file',str(controller_files[arm]),'-r','__ns:='+ns],arm)
            pub.publish(String(data=descriptions[arm]))
        launch([args.node,'--ros-args','-p','mode:=mock','-p','model_config:='+str(directory/'model.json')],'protection')
        active_client = None
        try:
            for arm in ARMS:
                ns=config['arms'][arm]['namespace']+'/controller_manager/'
                for controller in ('joint_trajectory_controller','joint_state_broadcaster','collision_hold_controller','forward_velocity_controller'):
                    assert rpc(LoadController,ns+'load_controller',LoadController.Request(name=controller)).ok
                    assert rpc(ConfigureController,ns+'configure_controller',ConfigureController.Request(name=controller)).ok
                assert switch(arm,['joint_trajectory_controller','joint_state_broadcaster']).ok
            until(lambda:status.get('collision_data_available') and len(pause_rows)==4)
            assert not status['paused'] and not status['known_collisions']
            report['checks'].append('four actual GenericSystem managers and C++ collision node')
            problem=Box(cfg={},names={arm:joint_names(arm) for arm in ARMS},signature=config['model_signature'],profiles=config['arms'])
            scenario=dict(task=0,started=None,phase='idle',pause_generation=None,held=None)
            def step(client):
                spin(.001)
                moving=ARMS[1:] if scenario['task']==3 else ARMS
                if scenario['task'] == 0 or not client.handles or len(client.handles)!=len(moving):
                    return
                if scenario['started'] is None:
                    if not all(pause_rows[a].get('action_active') for a in moving):
                        return
                    scenario['started']=time.monotonic()
                elapsed=time.monotonic()-scenario['started']
                if scenario['task']==1:
                    if scenario['phase']=='running' and elapsed>.35 and all(pause_rows[a].get('action_active') for a in ARMS):
                        ids={a:bytes(client.handles[a].goal_id.uuid).hex() for a in ARMS}
                        assert all(pause_rows[a]['active_goal'].replace('-','')==ids[a] for a in ARMS)
                        requested_ids.append(ids)
                        protection('pause_all');scenario['phase']='pausing'
                    elif scenario['phase']=='pausing' and all(pause_rows[a].get('factor',1.)==0. for a in ARMS):
                        scenario['held']={a:pause_rows[a]['phase_time_s'] for a in ARMS}
                        scenario['held_at']=time.monotonic();scenario['phase']='held'
                    elif scenario['phase']=='held' and time.monotonic()-scenario['held_at']>.7:
                        assert all(abs(pause_rows[a]['phase_time_s']-scenario['held'][a])<1e-9 for a in ARMS)
                        assert all(pause_rows[a].get('action_active') and pause_rows[a].get('resumable') for a in ARMS)
                        assert all(pause_rows[a]['active_goal'].replace('-','')==requested_ids[0][a] for a in ARMS)
                        captured_ids.append(dict(requested_ids[0]))
                        protection('resume_all');scenario['phase']='resumed'
                elif scenario['task']==2:
                    if scenario['phase']=='running' and elapsed>.25:
                        assert switch(ARMS[0],deactivate=['joint_state_broadcaster']).ok
                        scenario['pause_generation']=status['generation'];scenario['phase']='missing'
                    elif scenario['phase']=='missing' and ARMS[0] in status.get('unavailable_arms',[]):
                        assert not status['paused'] and status['generation']==scenario['pause_generation']
                        assert status['warnings'];scenario['warning_seen']=True
                elif scenario['task']==3:
                    if scenario['phase']=='running' and elapsed>.35:
                        assert joint_rows[ARMS[0]].position[0]>.101
                        scenario['mixed_ids']={a:bytes(client.handles[a].goal_id.uuid).hex() for a in moving}
                        protection('pause_all');scenario['phase']='pausing'
                    elif (scenario['phase']=='pausing' and
                          status.get('arms',{}).get(ARMS[0],{}).get('controller')=='collision_hold_controller' and
                          all(pause_rows[a].get('factor',1.)==0. for a in moving)):
                        scenario['manual_held']=list(joint_rows[ARMS[0]].position)
                        scenario['held_at']=time.monotonic();scenario['phase']='held'
                    elif scenario['phase']=='held' and time.monotonic()-scenario['held_at']>.5:
                        assert max(abs(a-b) for a,b in zip(joint_rows[ARMS[0]].position,scenario['manual_held']))<1e-8
                        assert all(pause_rows[a].get('action_active') and pause_rows[a]['active_goal'].replace('-','')==scenario['mixed_ids'][a] for a in moving)
                        protection('resume_all');scenario['phase']='resumed'
            class Client(MinimalHardwareClient):
                def spin_once(self,timeout_sec=.01):
                    super().spin_once(timeout_sec=timeout_sec)
                    step(self)
            active_client=Client(problem,'mock',ARMS)
            active_client.connect()
            for index,(start,end) in enumerate(((0.,.06),(.06,.1)),1):
                scenario.update(task=index,started=None,phase='running')
                segment={}
                active_client.follow_group({arm:trajectory(arm,start,end) for arm in ARMS},duration_s=2.,segment=segment)
                assert segment['executed']
                if index==1:
                    assert scenario['phase']=='resumed' and requested_ids==captured_ids
                    report['checks'].append('four goal UUIDs and phases retained through API pause/resume')
                else:
                    assert scenario.get('warning_seen') and not status['paused']
                    report['checks'].append('missing state warns during active second task without pause')
                report.setdefault('tasks',[]).append(dict(index=index,executed=segment['executed'],goal_ids={arm:bytes(handle.goal_id.uuid).hex() for arm,handle in active_client.handles.items()}))
            scenario['task']=0
            assert switch(ARMS[0],activate=['joint_state_broadcaster']).ok
            until(lambda:status.get('collision_data_available'))
            spin(.15)
            assert all(max(abs(q-.1) for q in joint_rows[a].position)<1e-6 for a in ARMS)
            report['checks'].append('two consecutive four-arm tasks completed at original targets')
            report['retained_goal_ids']=requested_ids[0]
            # A normal forward-velocity owner is stopped once by switching to
            # CollisionHold. Resume continues only the retained JTC goals.
            assert switch(ARMS[0],activate=['forward_velocity_controller'],deactivate=['joint_trajectory_controller']).ok
            velocity=probe.create_publisher(Float64MultiArray,config['arms'][ARMS[0]]['namespace']+'/forward_velocity_controller/commands',10)
            until(lambda:velocity.get_subscription_count()>0)
            velocity.publish(Float64MultiArray(data=[.02]*6))
            scenario.update(task=3,started=None,phase='running')
            active_client.follow_group({arm:trajectory(arm,.1,.14) for arm in ARMS[1:]},duration_s=2.)
            assert scenario['phase']=='resumed'
            scenario['task']=0
            spin(.2)
            assert max(abs(a-b) for a,b in zip(joint_rows[ARMS[0]].position,scenario['manual_held']))<1e-8
            inventory=rpc(ListControllers,config['arms'][ARMS[0]]['namespace']+'/controller_manager/list_controllers',ListControllers.Request()).controller
            active={c.name for c in inventory if c.state=='active'}
            assert 'collision_hold_controller' in active and 'forward_velocity_controller' not in active and 'joint_trajectory_controller' not in active
            report['checks'].append('mixed forward-velocity/JTC pause holds manual owner; resume retains only three JTC goals')
            report['mixed_retained_goal_ids']=scenario['mixed_ids']
            report['success']=True
            print(json.dumps(report,sort_keys=True))
        except BaseException:
            for log in logs:
                log.flush();log.seek(0)
                print('\n'+str(log.name)+'\n'+log.read()[-10000:])
            raise
        finally:
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(report,indent=2)+'\n')
            if active_client is not None:active_client.destroy_node()
            probe_executor.remove_node(probe);probe_executor.shutdown();probe.destroy_node();rclpy.shutdown()
            for process in reversed(processes):
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGINT)
                    try:process.wait(timeout=5.)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL);process.wait()
            for log in logs:log.close()
    return 0


if __name__=='__main__':
    raise SystemExit(main())

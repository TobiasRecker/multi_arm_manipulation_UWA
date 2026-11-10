"""Cross-domain proof using synthetic JointState only, never physical domains."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback

from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from tf2_ros import Buffer,TransformListener
from uwa_cell_visualization.bridge import LATCHED,SENSOR
from uwa_cell_visualization.model import ARMS,EMPTY_MODEL,JOINTS


def main():
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    workspace=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    logs=workspace/'setup/logs';logs.mkdir(exist_ok=True)
    os.environ['ROS_LOG_DIR']=str(logs/'uwa-twin-validation-ros')
    output=(logs/'uwa-twin-cross-domain-launch.log').open('w')
    process=subprocess.Popen(['ros2','launch','uwa_cell_visualization','hardware_overlay.launch.py',
        'source_domain:=174','target_domain:=175','use_sim_time:=true'],stdout=output,
        stderr=subprocess.STDOUT,start_new_session=True)
    source_context=Context();source_context.init(args=[],domain_id=174)
    target_context=Context();target_context.init(args=[],domain_id=175,initialize_logging=False)
    source=Node('synthetic_joint_source',context=source_context)
    target=Node('twin_validation',context=target_context,parameter_overrides=[Parameter('use_sim_time',value=True)])
    executor=SingleThreadedExecutor(context=target_context);executor.add_node(target)
    publishers={rid:source.create_publisher(JointState,f'/uwa_hardware/{rid}/joint_states',SENSOR) for rid in ARMS}
    clock=target.create_publisher(Clock,'/clock',10)
    received={};models={};status={};tf_buffer=Buffer();listener=TransformListener(tf_buffer,target)
    def store_status(msg):status.update(json.loads(msg.data))
    subs=[target.create_subscription(String,'/uwa_cell/real/status',store_status,LATCHED)]
    for rid in ARMS:
        subs += [target.create_subscription(JointState,f'/uwa_cell/real/{rid}/joint_states',
            lambda msg,rid=rid:received.update({rid:msg}),10),
            target.create_subscription(String,f'/uwa_cell/real/{rid}/robot_description',
            lambda msg,rid=rid:models.update({rid:msg.data}),LATCHED)]
    report={'success':False,'physical_domains_used':False,'test_domains':[174,175]}
    sending=[];q=[0.,-1.2,.6,-1.0,.3,0.];last_send=0.
    def pump():
        nonlocal last_send
        if time.monotonic()-last_send>.05:
            tick=Clock();tick.clock.sec=50;clock.publish(tick)  # deliberately paused display clock
            for rid in sending:
                msg=JointState();msg.name=[rid+'_'+j for j in JOINTS];msg.position=q
                msg.header.stamp.sec=1794290000;publishers[rid].publish(msg)
            last_send=time.monotonic()
        executor.spin_once(timeout_sec=.02)
    def wait(predicate,timeout,label):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            pump()
            if predicate():return
            if process.poll() is not None:raise RuntimeError('Overlay exited: '+str(process.returncode))
        raise RuntimeError('Timeout: '+label)
    try:
        wait(lambda:len(models)==2 and len(status.get('arms',{}))==2,25,'initial models/status')
        assert all(model==EMPTY_MODEL for model in models.values())
        assert all(arm['state']=='WAITING' for arm in status['arms'].values())
        report['no_fabricated_initial_pose']=True
        sending=list(ARMS)
        wait(lambda:len(received)==2 and all('real_right_' in model for model in models.values()) and
             all(msg.header.stamp.sec==50 for msg in received.values()),15,'two measured models')
        for rid,msg in received.items():
            assert msg.name==['real_'+rid+'_'+j for j in JOINTS]
            assert list(msg.position)==q and msg.header.stamp.sec==50
        wait(lambda:all(tf_buffer.can_transform('world','real_'+rid+'_tool0',Time()) for rid in ARMS),10,'live TF chains')
        for rid,y in [('right_front',-.675),('right_rear',.675)]:
            tf=tf_buffer.lookup_transform('world','real_'+rid+'_base_link',Time())
            xyz=tf.transform.translation
            assert abs(xyz.x-.45)<1e-8 and abs(xyz.y-y)<1e-8 and abs(xyz.z-.9)<1e-8
        report['two_renamed_models_joint_values_and_world_tf']=True
        report['display_stamp_50_despite_hardware_wall_time']=True
        pubs=source.get_publisher_names_and_types_by_node('uwa_measured_reader','/')
        assert all(topic in ['/parameter_events','/rosout'] for topic,_ in pubs)
        target_pubs=target.get_publisher_names_and_types_by_node('uwa_measured_display','/uwa_cell/real')
        assert not any(topic=='/uwa_cell/joint_states' or 'trajectory' in topic or 'command' in topic for topic,_ in target_pubs)
        report['source_publishers']=pubs;report['no_command_or_sim_joint_publishers']=True
        old_tool=tf_buffer.lookup_transform('world','real_right_front_tool0',Time()).transform.translation
        q=[.2,-1.0,.4,-1.1,.2,.1]
        wait(lambda:all(list(msg.position)==q for msg in received.values()),5,'changing measured angles')
        def tool_changed():
            position=tf_buffer.lookup_transform('world','real_right_front_tool0',Time()).transform.translation
            return sum((a-b)**2 for a,b in zip([position.x,position.y,position.z],[old_tool.x,old_tool.y,old_tool.z]))>1e-5
        wait(tool_changed,5,'TF follows hardware while simulation clock is paused')
        report['tf_updates_while_sim_clock_paused']=True
        sending=[]
        wait(lambda:all(arm['state']=='STALE' for arm in status.get('arms',{}).values()) and
             all(model==EMPTY_MODEL for model in models.values()),6,'stale models hidden with paused simulation clock')
        report['stale_hidden_while_sim_time_paused']=True
        sending=['right_front']
        wait(lambda:status['arms']['right_front']['state']=='LIVE' and status['arms']['right_rear']['state']=='STALE',5,'independent recovery')
        report['independent_arm_recovery']=True;report['success']=True
    except Exception as error:
        report['error']=repr(error);traceback.print_exc()
    finally:
        if process.poll() is None:
            try:os.killpg(process.pid,signal.SIGINT)
            except ProcessLookupError:pass
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=5)
        executor.shutdown();target.destroy_node();source.destroy_node()
        target_context.try_shutdown();source_context.try_shutdown();output.close()
        (logs/'uwa-twin-cross-domain.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    return 0 if report['success'] else 1


if __name__=='__main__':raise SystemExit(main())

"""One-way JointState display: domain 66 subscriptions -> domain 64 publishers."""
import argparse
import json
from pathlib import Path
import threading
import time

import rclpy
from rclpy.clock import Clock,ClockType
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,HistoryPolicy
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from visualization_msgs.msg import Marker,MarkerArray

from .model import ARMS,COLOURS,EMPTY_MODEL,JOINTS,load_inputs,map_positions,paths

LATCHED=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
SENSOR=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT,
                  history=HistoryPolicy.KEEP_LAST)


class MeasuredOverlay:
    def __init__(self,profiles,layout,models,*,source_domain=66,target_domain=64,
                 use_sim_time=True,stale_after=2.,offset=(0.,0.,0.)):
        if source_domain==target_domain:raise ValueError('Source and visualization domains must differ')
        self.profiles=profiles;self.layout=layout;self.models=models;self.stale_after=stale_after;self.offset=offset
        self.lock=threading.Lock();self.samples={};self.errors={};self.sequence=0;self.sent={};self.visible={}
        self.source_context=Context();self.target_context=Context()
        self.target_context.init(args=[],domain_id=target_domain)
        self.source_context.init(args=[],domain_id=source_domain,initialize_logging=False)
        self.target=Node('uwa_measured_display',context=self.target_context,namespace='/uwa_cell/real',
            parameter_overrides=[Parameter('use_sim_time',value=use_sim_time)])
        self.source=Node('uwa_measured_reader',context=self.source_context,enable_rosout=False,
                         start_parameter_services=False)
        self.state_pub={};self.description_pub={}
        for rid,profile in profiles.items():
            # The source node has no command publishers, service clients or actions.
            self.source.create_subscription(JointState,profile['namespace']+'/joint_states',
                lambda msg,rid=rid:self.receive(rid,msg),SENSOR)
            self.state_pub[rid]=self.target.create_publisher(JointState,f'{rid}/joint_states',10)
            self.description_pub[rid]=self.target.create_publisher(String,f'{rid}/robot_description',LATCHED)
            self.description_pub[rid].publish(String(data=EMPTY_MODEL));self.visible[rid]=False
        self.marker_pub=self.target.create_publisher(MarkerArray,'status_markers',LATCHED)
        self.status_pub=self.target.create_publisher(String,'status',LATCHED)
        self.source_domain=source_domain;self.target_domain=target_domain
        self.timer=self.target.create_timer(.05,self.publish,clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.last_status=0.
        self.source_executor=SingleThreadedExecutor(context=self.source_context)
        self.source_executor.add_node(self.source)
        self.target_executor=SingleThreadedExecutor(context=self.target_context)
        self.target_executor.add_node(self.target)
        self.thread=threading.Thread(target=self.source_executor.spin,name='measured-joint-reader')

    def receive(self,rid,msg):
        try:values=map_positions(msg.name,msg.position,self.profiles[rid])
        except (KeyError,ValueError,TypeError) as error:
            with self.lock:self.errors[rid]=str(error)
            return
        with self.lock:
            self.sequence+=1
            self.samples[rid]=(time.monotonic(),self.sequence,values)
            self.errors.pop(rid,None)

    def publish(self):
        now=time.monotonic();stamp=self.target.get_clock().now().to_msg()
        with self.lock:samples=dict(self.samples);errors=dict(self.errors)
        status={};markers=[]
        for index,(rid,profile) in enumerate(self.profiles.items()):
            sample=samples.get(rid);age=None if sample is None else now-sample[0]
            fresh=sample is not None and age<=self.stale_after
            if fresh and self.sent.get(rid)!=sample[1]:
                msg=JointState();msg.header.stamp=stamp
                msg.name=['real_'+rid+'_'+joint for joint in JOINTS];msg.position=sample[2]
                self.state_pub[rid].publish(msg);self.sent[rid]=sample[1]
            if fresh!=self.visible[rid]:
                self.description_pub[rid].publish(String(data=self.models[rid] if fresh else EMPTY_MODEL))
                self.visible[rid]=fresh
            state='LIVE' if fresh else 'WAITING' if sample is None else 'STALE'
            status[rid]={'state':state,'age_seconds':age,'input_topic':profile['namespace']+'/joint_states',
                         'frame_prefix':'real_'+rid+'_','error':errors.get(rid,''),
                         'freshness_basis':'ROS message receipt, not independent RTDE sensor freshness',
                         'mount_calibrated':False,'model_visible':fresh}
            mount=self.layout['robots'][rid];table=self.layout['tables'][mount['table']]
            marker=Marker();marker.header.frame_id='world';marker.header.stamp=stamp
            marker.ns='measured_data_status';marker.id=index;marker.type=Marker.TEXT_VIEW_FACING
            marker.pose.orientation.w=1.;marker.pose.position.x=table['xyz'][0]+self.offset[0]
            marker.pose.position.y=table['xyz'][1]+self.offset[1]+(-.6 if rid=='right_front' else .6)
            marker.pose.position.z=table['xyz'][2]+table['height']+self.offset[2]+1.25
            marker.scale.z=.08;marker.color.a=1.
            marker.color.r,marker.color.g,marker.color.b=COLOURS[rid] if fresh else (1.,.2,.1)
            label='FRONT' if rid=='right_front' else 'REAR'
            # Some RViz/Ogre font builds give spaces an excessive world width.
            marker.text=f'{label}:{state}\nBASE:PROVISIONAL'
            markers.append(marker)
        if now-self.last_status>=.5:
            self.marker_pub.publish(MarkerArray(markers=markers))
            self.status_pub.publish(String(data=json.dumps({'source_domain':self.source_domain,
                'display_domain':self.target_domain,'arms':status})))
            self.last_status=now

    def run(self):
        self.thread.start()
        try:
            while self.target_context.ok():self.target_executor.spin_once(timeout_sec=.1)
        except KeyboardInterrupt:pass
        finally:
            self.source_executor.shutdown();self.thread.join()
            self.target_executor.shutdown()
            self.source.destroy_node();self.target.destroy_node()
            self.source_context.try_shutdown();self.target_context.try_shutdown()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',required=True);parser.add_argument('--layout',default=str(paths()))
    parser.add_argument('--arms',default=','.join(ARMS));parser.add_argument('--models-dir',required=True)
    parser.add_argument('--source-domain',type=int,default=66);parser.add_argument('--target-domain',type=int,default=64)
    parser.add_argument('--use-sim-time',choices=['true','false'],default='true')
    parser.add_argument('--stale-after',type=float,default=2.)
    parser.add_argument('--offset',type=float,nargs=3,default=[0.,0.,0.])
    args=parser.parse_args(remove_ros_args()[1:])
    profiles,layout=load_inputs(args.inventory,args.layout,args.arms.split(','))
    profiles={rid:profiles[rid] for rid in args.arms.split(',')}
    models={rid:(Path(args.models_dir)/(rid+'.urdf')).read_text() for rid in profiles}
    if not 0.<args.stale_after<60.:raise ValueError('stale-after must be between 0 and 60 seconds')
    MeasuredOverlay(profiles,layout,models,source_domain=args.source_domain,target_domain=args.target_domain,
        use_sim_time=args.use_sim_time=='true',stale_after=args.stale_after,offset=args.offset).run()

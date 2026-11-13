"""Bounded, opt-in real-camera acceptance. No robot discovery/commands."""
import argparse
import json
import os
from pathlib import Path
import time

import cv2
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from std_srvs.srv import Trigger
from uwa_cell_tracking.oak_stream import OakStream
from uwa_cell_tracking.node import ObjectTracker


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,required=True);args=parser.parse_args()
    if os.environ.get('ROS_DOMAIN_ID')!='65':raise ValueError('Real camera test must use domain65')
    workspace=args.workspace.resolve();out=workspace/'setup/tracking/carton_cpu_20261113/live';out.mkdir(parents=True,exist_ok=True)
    rclpy.init(args=['--ros-args','-p','workspace:='+str(workspace),'-p','reference:='+str(workspace/'setup/tracking/carton_cpu_20261113/reference.npz'),
        '-p','image_topic:=/oak4/tracking/image_raw','-p','camera_info_topic:=/oak4/tracking/camera_info'])
    stream=tracker=test=None;executor=SingleThreadedExecutor();statuses=[];captures=[];poses=[];latest={};arrival=[]
    report=dict(success=False,hardware_robot_commands=False,requested_fps=10)
    try:
        stream=OakStream();tracker=ObjectTracker();test=Node('bounded_oak_tracking_check')
        for node in (stream,tracker,test):executor.add_node(node)
        def capture(msg):
            data=json.loads(msg.data)
            if data.get('status')=='LIVE':captures.append(data);arrival.append(time.monotonic())
        subscriptions=[test.create_subscription(String,'/oak4/tracking/capture_status',capture,10),
            test.create_subscription(String,'/uwa_tracking/object_tracker/status',lambda m:statuses.append(json.loads(m.data)),10),
            test.create_subscription(PoseStamped,'/uwa_tracking/object_tracker/pose',lambda m:poses.append(m),10),
            test.create_subscription(Image,'/uwa_tracking/object_tracker/overlay',lambda m:latest.update(overlay=m),qos_profile_sensor_data)]
        def spin(seconds):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:executor.spin_once(timeout_sec=.02)
        def service(name):
            client=test.create_client(Trigger,'/uwa_tracking/object_tracker/'+name)
            assert client.wait_for_service(timeout_sec=2);future=client.call_async(Trigger.Request())
            while not future.done():executor.spin_once(timeout_sec=.02)
            assert future.result().success;test.destroy_client(client)
        deadline=time.monotonic()+45
        while len(captures)<15 and time.monotonic()<deadline:executor.spin_once(timeout_sec=.02)
        assert len(captures)>=15,'Insufficient fresh OAK frames'
        service('localize');spin(5)
        report['static_statuses']=[s for s in statuses if s['status'] not in ('COLLECTING','STATIC')]
        static_ok=any(s['status']=='VALID' for s in statuses)
        service('start');statuses.clear();spin(12)
        report['dynamic_status_counts']={s:sum(v['status']==s for v in statuses) for s in sorted({v['status'] for v in statuses})}
        processing=[s['result']['processing_ms'] for s in statuses if s.get('result',{}).get('status')=='VALID']
        if processing:report['dynamic_processing_median_ms']=float(np.median(processing))
        service('stop');spin(.3)
        if 'overlay' in latest:
            msg=latest['overlay'];image=np.frombuffer(msg.data,np.uint8).reshape(msg.height,msg.width,3)
            cv2.imwrite(str(out/'overlay.jpg'),image)
        elapsed=arrival[-1]-arrival[0]
        dynamic_ok=sum(s['status']=='VALID' for s in statuses)>=5
        report.update(success=bool(static_ok and dynamic_ok),stream_success=True,
            static_localization_success=static_ok,dynamic_tracking_success=dynamic_ok,
            stream_worker_directory=str(stream.output),frames_received=len(captures),
            measured_receive_fps=(len(captures)-1)/elapsed,SDK_sequence_range=[captures[0]['sequence'],captures[-1]['sequence']],
            size=captures[-1]['size'],focus=captures[-1]['lens_position'],K=captures[-1]['K'],D=captures[-1]['D'],
            maximum_sdk_frame_age_s=max(x['sdk_frame_age_s'] for x in captures),pose_messages=len(poses),
            actual_object_motion_tested=False,absolute_accuracy_validated=False)
    except Exception as error:report['error']=str(error);raise
    finally:
        if tracker:tracker.close()
        if stream:stream.close()
        for node in (stream,tracker,test):
            if node:executor.remove_node(node);node.destroy_node()
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        rclpy.shutdown()
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

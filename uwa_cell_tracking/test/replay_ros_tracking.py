"""Isolated ROS adapter acceptance using saved photographs, no camera access.

Set ROS_DOMAIN_ID=71 / LOCALHOST. Synthetic replay timestamps, not live FPS.
"""
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
from sensor_msgs.msg import Image,CameraInfo
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from std_srvs.srv import Trigger
from uwa_cell_tracking.node import ObjectTracker


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,required=True);args=parser.parse_args()
    if os.environ.get('ROS_DOMAIN_ID')!='71':raise ValueError('Use isolated domain71')
    root=args.workspace.resolve();output=root/'setup/tracking/carton_cpu_20261113';output.mkdir(parents=True,exist_ok=True)
    rclpy.init(args=['--ros-args','-p','reference:='+str(output/'reference.npz'),
        '-p','image_topic:=/cpu_replay/image','-p','camera_info_topic:=/cpu_replay/info'])
    tracker=ObjectTracker();test=Node('cpu_tracker_test');executor=SingleThreadedExecutor();executor.add_node(tracker);executor.add_node(test)
    statuses=[];poses=[];overlays=[]
    subscriptions=[test.create_subscription(String,'/uwa_tracking/object_tracker/status',lambda m:statuses.append(json.loads(m.data)),10),
        test.create_subscription(PoseStamped,'/uwa_tracking/object_tracker/pose',lambda m:poses.append(m),10),
        test.create_subscription(Image,'/uwa_tracking/object_tracker/overlay',lambda m:overlays.append((m.width,m.height)),qos_profile_sensor_data)]
    image_pub=test.create_publisher(Image,'/cpu_replay/image',qos_profile_sensor_data)
    info_pub=test.create_publisher(CameraInfo,'/cpu_replay/info',qos_profile_sensor_data)
    cameras=json.loads((root/'setup/digitization/carton_multiview_20261113/refined_camera_models.json').read_text())
    images=[cv2.resize(cv2.imread(cameras[f'r{n}_oak4']['image']),(1600,1200)) for n in (1,3,5)]
    K=np.array(cameras['r1_oak4']['K']);K[:2]*=.2;D=cameras['r1_oak4']['D']
    def spin(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:executor.spin_once(timeout_sec=.01)
    def service(name):
        client=test.create_client(Trigger,'/uwa_tracking/object_tracker/'+name)
        assert client.wait_for_service(timeout_sec=3);future=client.call_async(Trigger.Request())
        deadline=time.monotonic()+3
        while not future.done() and time.monotonic()<deadline:executor.spin_once(timeout_sec=.01)
        assert future.done() and future.result().success;test.destroy_client(client)
    def publish(image,age=0):
        stamp=test.get_clock().now().to_msg()
        if age:stamp.sec-=age
        msg=Image();msg.header.stamp=stamp;msg.header.frame_id='cpu_replay_camera_optical'
        msg.width=1600;msg.height=1200;msg.encoding='bgr8';msg.step=4800;msg.data=image.tobytes()
        info=CameraInfo();info.header=msg.header;info.width=1600;info.height=1200;info.k=K.ravel().tolist();info.d=D
        info_pub.publish(info);spin(.04);image_pub.publish(msg)
    report=dict(success=False,domain=71,hardware_access=False,timestamps='synthetic replay, not live capture')
    try:
        spin(.5);service('localize')
        for image in images:publish(image);spin(.15)
        spin(3)
        assert any(s['status']=='VALID' for s in statuses),'Static registration not published'
        assert poses and overlays
        report['static_valid']=True;report['static_pose_camera_frame']=poses[-1].header.frame_id
        service('start');statuses.clear()
        for i in range(15):publish(images[i%3]);spin(.08)
        spin(.2)
        assert any(s['status']=='VALID' for s in statuses),'Dynamic tracker no valid pose'
        report['dynamic_valid']=True
        spin(1.4);assert any(s['status']=='STALE' for s in statuses)
        report['image_loss_invalidated']=True
        service('start');publish(images[0]);service('stop');count=len(poses);spin(1.)
        assert len(poses)==count,'Worker published an old pose after stop'
        report['stop_discards_inflight_result']=True
        report.update(success=True,pose_messages=len(poses),overlay_messages=len(overlays))
    except Exception as error:report['error']=str(error);raise
    finally:
        (output/'ros_replay.json').write_text(json.dumps(report,indent=2)+'\n')
        tracker.close();executor.remove_node(tracker);executor.remove_node(test);tracker.destroy_node();test.destroy_node();rclpy.shutdown()
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

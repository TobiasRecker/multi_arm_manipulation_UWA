"""ROS camera-topic adapter; latest-frame processing is separate from ROS spin.

No camera device control, model-world priors or robot command interfaces.
"""
import json
from pathlib import Path
import queue
from threading import Thread
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Image,CameraInfo
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .core import DynamicTracker,TexturePose,PoseResult
from .static import static_pose
from .cli import record,annotate


class ObjectTracker(Node):
    def __init__(self):
        super().__init__('object_tracker',namespace='uwa_tracking')
        for name,value in [('reference',''),('image_topic','/uwa_cell/oak_overview/rgb/image_raw'),
            ('camera_info_topic','/uwa_cell/oak_overview/rgb/camera_info'),('static_frames',3),
            ('maximum_input_age_s',1.),('maximum_static_result_age_s',5.),('maximum_frame_gap_s',.5)]:
            self.declare_parameter(name,value)
        reference=self.get_parameter('reference').value
        if not reference:raise ValueError('A prepared --reference is required')
        self.estimator=TexturePose(Path(reference));cv2.setNumThreads(2)
        self.jobs=queue.Queue(maxsize=1);self.results=queue.Queue();self.closing=False
        self.epoch=0;self.mode='IDLE';self.info=None;self.burst=[];self.last_stamp=None
        self.status=self.create_publisher(String,'~/status',10)
        self.pose=self.create_publisher(PoseStamped,'~/pose',10)
        self.overlay=self.create_publisher(Image,'~/overlay',qos_profile_sensor_data)
        self.create_subscription(CameraInfo,self.get_parameter('camera_info_topic').value,self.camera_info,qos_profile_sensor_data)
        self.create_subscription(Image,self.get_parameter('image_topic').value,self.image,qos_profile_sensor_data)
        for name,mode in [('localize','STATIC'),('start','DYNAMIC'),('stop','IDLE')]:
            self.create_service(Trigger,'~/'+name,lambda req,res,m=mode:self.change_mode(m,res))
        self.worker=Thread(target=self.process,daemon=True);self.worker.start()
        self.create_timer(.025,self.publish_results)
        self.create_timer(.25,self.watchdog)
        self.last_received=time.monotonic();self.report('IDLE','Call localize (static) or start (dynamic). No robot control.')

    def report(self,status,reason,**data):
        payload=dict(status=status,reason=reason,mode=self.mode,asset_id=self.estimator.metadata['asset_id'],
            absolute_accuracy_validated=False,manipulation_approved=False,**data)
        self.status.publish(String(data=json.dumps(payload,allow_nan=False)))

    def change_mode(self,mode,response):
        self.epoch+=1;self.mode=mode;self.burst=[];self.last_stamp=None
        while not self.jobs.empty():
            try:self.jobs.get_nowait()
            except queue.Empty:break
        self.report(mode,'Waiting for fresh calibrated frames' if mode!='IDLE' else 'Stopped; old worker results discarded')
        response.success=True;response.message=mode;return response

    def camera_info(self,msg):
        self.info=msg

    def image(self,msg):
        if self.mode not in ('STATIC','DYNAMIC'):return
        info=self.info
        if (info is None or info.header.frame_id!=msg.header.frame_id or not msg.header.frame_id or
                (info.width,info.height)!=(msg.width,msg.height)):
            self.report('LOST','Missing matching CameraInfo/frame/size');return
        if msg.encoding not in ('rgb8','bgr8','mono8'):
            self.report('LOST','Unsupported image encoding '+msg.encoding);return
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        age=self.get_clock().now().nanoseconds*1e-9-stamp
        if age<-.05 or age>self.get_parameter('maximum_input_age_s').value:
            self.report('STALE','Input timestamp not fresh/in the same clock domain',age_s=age);return
        if self.last_stamp is not None and stamp<=self.last_stamp:
            self.epoch+=1;self.burst=[];self.report('LOST','Time did not advance; tracker reset');self.last_stamp=stamp;return
        self.last_stamp=stamp;self.last_received=time.monotonic()
        channels=1 if msg.encoding=='mono8' else 3
        try:
            image=np.frombuffer(msg.data,np.uint8).reshape(msg.height,msg.step)[:,:msg.width*channels]
            image=image.reshape(msg.height,msg.width,channels).copy()
            if channels==1:image=image[:,:,0]
            elif msg.encoding=='rgb8':image=cv2.cvtColor(image,cv2.COLOR_RGB2BGR)
            K=np.array(info.k,float).reshape(3,3);D=np.array(info.d,float)
        except (ValueError,cv2.error):self.report('LOST','Malformed image or camera data');return
        if self.mode=='STATIC':
            if self.burst and (not np.array_equal(K,self.burst[0][1]) or not np.array_equal(D,self.burst[0][2])):
                self.burst=[];self.report('LOST','Camera model changed during static burst');return
            self.burst.append((image,K,D))
            if len(self.burst)<max(3,self.get_parameter('static_frames').value):
                self.report('COLLECTING','Static burst; camera AND object must remain stationary',frames=len(self.burst));return
            frames=[x[0] for x in self.burst];self.burst=[];self.mode='STATIC_PROCESSING'
            job=(self.epoch,'STATIC',frames,K,D,msg.header)
        else:job=(self.epoch,'DYNAMIC',[image],K,D,msg.header)
        try:self.jobs.put_nowait(job)
        except queue.Full:
            try:self.jobs.get_nowait()
            except queue.Empty:pass
            try:self.jobs.put_nowait(job)
            except queue.Full:pass

    def process(self):
        tracker=DynamicTracker(max_gap_s=self.get_parameter('maximum_frame_gap_s').value);epoch=None
        while not self.closing:
            try:job=self.jobs.get(timeout=.1)
            except queue.Empty:continue
            tag,mode,frames,K,D,header=job;stamp=header.stamp.sec+header.stamp.nanosec*1e-9
            if tag!=epoch:tracker.reset();epoch=tag
            try:
                if mode=='STATIC':result=static_pose(self.estimator,frames,K,D)
                elif tracker.gray is None:
                    result=self.estimator.register(frames[0],K,D,stamp)
                    tracker.initialize(frames[0],result,K,D,stamp)
                else:result=tracker.update(frames[0],K,D,stamp)
            except Exception as error:
                tracker.reset();result=PoseResult('LOST',reason=str(error))
            result.source_stamp=stamp
            preview=annotate(frames[-1],result,K,D) if self.overlay.get_subscription_count() else None
            self.results.put((tag,mode,result,header,preview))

    def publish_results(self):
        while not self.results.empty():
            tag,mode,result,header,preview=self.results.get_nowait()
            if tag!=self.epoch:continue
            age=self.get_clock().now().nanoseconds*1e-9-result.source_stamp
            limit=self.get_parameter('maximum_static_result_age_s' if mode=='STATIC' else 'maximum_input_age_s').value
            if age<-.05 or age>limit:
                result=PoseResult('STALE',reason='Result too old for requested mode',source_stamp=result.source_stamp)
            self.report(result.status,result.reason,result=record(result),age_s=age,camera_frame=header.frame_id)
            if preview is not None:
                image=Image();image.header=header;image.height,image.width=preview.shape[:2]
                image.encoding='bgr8';image.step=image.width*3;image.data=preview.tobytes();self.overlay.publish(image)
            if result.status=='VALID':
                msg=PoseStamped();msg.header=header;p=result.T_camera_object
                from scipy.spatial.transform import Rotation
                msg.pose.position.x,msg.pose.position.y,msg.pose.position.z=p[:3,3].tolist()
                q=Rotation.from_matrix(p[:3,:3]).as_quat().tolist()
                msg.pose.orientation.x,msg.pose.orientation.y,msg.pose.orientation.z,msg.pose.orientation.w=q
                self.pose.publish(msg)
            if mode=='STATIC':self.mode='IDLE'

    def watchdog(self):
        if self.mode!='DYNAMIC':return
        if time.monotonic()-self.last_received>self.get_parameter('maximum_input_age_s').value:
            self.epoch+=1;self.last_received=time.monotonic();self.report('STALE','No fresh image; pose invalidated')

    def close(self):
        self.closing=True;self.worker.join(timeout=6.)


def main():
    rclpy.init();node=None
    try:node=ObjectTracker();rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if node:node.close();node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()

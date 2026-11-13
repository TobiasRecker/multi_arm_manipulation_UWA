"""Opt-in OAK RGB topic provider, sharing the existing SDK/photo lease.

Launch only when wanted; owns its SDK worker, never another camera client.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo,Image
from std_msgs.msg import String
import yaml


class OakStream(Node):
    def __init__(self):
        super().__init__('oak_tracking_stream',namespace='oak4')
        if os.environ.get('ROS_DOMAIN_ID')!='65':raise ValueError('Real OAK stream uses isolated camera domain65')
        self.declare_parameter('workspace',os.environ.get('UWA_WS',''))
        self.declare_parameter('fps',10.)
        workspace=Path(self.get_parameter('workspace').value).resolve()
        if not (workspace/'src/oak_camera_calibration/AGENTS.md').is_file():raise ValueError('Invalid UWA workspace')
        inventory=yaml.safe_load((workspace/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml').read_text())['cameras']['oak4']
        self.output=workspace/'setup/tracking/oak_stream'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        self.output.mkdir(parents=True);self.log=(self.output/'worker.log').open('w');self.last=None;self.started=time.monotonic()
        self.image=self.create_publisher(Image,'/oak4/tracking/image_raw',qos_profile_sensor_data)
        self.info=self.create_publisher(CameraInfo,'/oak4/tracking/camera_info',qos_profile_sensor_data)
        self.status=self.create_publisher(String,'/oak4/tracking/capture_status',10)
        self.child=subprocess.Popen([str(workspace/'setup/oak4/bin/oakctl'),'run-script',
            str(workspace/'.venvs/oak4/bin/python'),'-u',str(workspace/'src/oak_camera_calibration/tools/oak4_board_preview.py'),
            '--ip',inventory['ip'],'--device-id',str(inventory['device_id']),
            '--output',str(self.output),'--focus','116','--width','1600','--height','1200',
            '--fps',str(self.get_parameter('fps').value),'--tracking-metadata',
            '--lock',str(workspace/'setup/oak4/photos/.capture.lock')],
            stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True,
            env={k:v for k,v in dict(os.environ,DEPTHAI_TELEMETRY='0',OAKCTL_ANALYTICS='0').items() if k!='PYTHONPATH'})
        self.create_timer(.01,self.receive);self.get_logger().info('OAK tracking stream starting; photo lease respected. '+str(self.output))

    def receive(self):
        if self.child.poll() is not None:
            self.status.publish(String(data=json.dumps(dict(status='FAILED',exit_code=self.child.returncode,log=str(self.output/'worker.log')))))
            raise RuntimeError('OAK SDK worker ended; see '+str(self.output/'worker.log'))
        path=self.output/'frame.bin'
        if not path.exists():
            if time.monotonic()-self.started>45:raise RuntimeError('No OAK frame within45s; no automatic device reset')
            return
        payload=path.read_bytes();header,jpeg=payload.split(b'\n',1);metadata=json.loads(header)
        if metadata['sequence']==self.last:return
        if self.last is not None and metadata['sequence']<self.last:raise RuntimeError('OAK sequence reversed')
        self.last=metadata['sequence']
        age=time.time()-metadata['received']
        if age>1 or age<-.05:raise RuntimeError('OAK packet stale/host clock changed')
        if metadata['lens_position']!=116:raise RuntimeError('OAK focus changed')
        image=cv2.imdecode(np.frombuffer(jpeg,np.uint8),cv2.IMREAD_COLOR)
        if image is None or [image.shape[1],image.shape[0]]!=metadata['size']:raise RuntimeError('Invalid OAK packet')
        stamp_ns=round((metadata['received']-metadata['sdk_frame_age_s'])*1e9)
        msg=Image();msg.header.stamp.sec=stamp_ns//1000000000;msg.header.stamp.nanosec=stamp_ns%1000000000
        msg.header.frame_id='oak4_tracking_rgb_optical';msg.height,msg.width=image.shape[:2]
        msg.encoding='bgr8';msg.step=msg.width*3;msg.data=image.tobytes()
        info=CameraInfo();info.header=msg.header;info.width=msg.width;info.height=msg.height
        info.k=np.asarray(metadata['K']).ravel().tolist();info.d=metadata['D'];info.distortion_model='rational_polynomial'
        self.info.publish(info);self.image.publish(msg)
        self.status.publish(String(data=json.dumps(dict(status='LIVE',**metadata))))

    def close(self):
        if self.child.poll() is None:
            # Same SDK worker's established graceful termination path. No broad kill.
            os.killpg(self.child.pid,signal.SIGTERM)
            try:self.child.wait(timeout=20)
            except subprocess.TimeoutExpired:raise RuntimeError('Own SDK worker did not close; inspect lease, do not reset camera')
        self.log.close()


def main():
    rclpy.init();node=None
    try:node=OakStream();rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if node:node.close();node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()

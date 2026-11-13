"""Own-world Gazebo telemetry. Never subscribe to the shared global /clock."""
from functools import partial
from threading import Lock
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image,CameraInfo
from gz.transport import Node as TransportNode
from gz.msgs.clock_pb2 import Clock as GzClock
from gz.msgs.contacts_pb2 import Contacts
from gz.msgs.pose_v_pb2 import Pose_V
from gz.msgs.image_pb2 import Image as GzImage
from gz.msgs.camera_info_pb2 import CameraInfo as GzInfo
from uwa_cell_gazebo.camera_bridge import image_message,info_message
from match_cooperative_handling.rigid_object import rigid
from scipy.spatial.transform import Rotation
import numpy as np
from .core import ARMS


class TelemetryBridge(Node):
    def __init__(self, namespace, world):
        super().__init__('task_telemetry',namespace=namespace)
        self.transport=TransportNode();self.lock=Lock();self.topics=[];self.closing=False
        self.clock=self.create_publisher(Clock,namespace+'/clock',qos_profile_sensor_data)
        self.contact=self.create_publisher(String,'tasks/contacts',10)
        self.pose=self.create_publisher(String,'tasks/object_truth',10)
        self.subscribe(GzClock,'/world/'+world+'/clock',self.clock_message)
        self.subscribe(Contacts,'/world/'+world+'/model/uwa_grasp_carton/link/body/sensor/carton_contacts/contact',self.contacts_message)
        self.subscribe(Pose_V,'/uwa_grasp_carton/pose',self.pose_message)
        self.outputs=[]
        for arm in ARMS:
            for suffix,gz_type,ros_type,convert in [('image_raw',GzImage,Image,image_message),('camera_info',GzInfo,CameraInfo,info_message)]:
                topic=namespace+'/'+arm+'/wrist_camera/'+suffix
                pub=self.create_publisher(ros_type,topic,qos_profile_sensor_data);self.outputs.append(pub)
                self.subscribe(gz_type,topic,partial(self.camera,pub,convert,arm))

    def subscribe(self,kind,topic,callback):
        if not self.transport.subscribe(kind,topic,callback):raise RuntimeError('Subscription failed '+topic)
        self.topics.append(topic)

    def clock_message(self,msg):
        if self.closing:return
        out=Clock();out.clock.sec=msg.sim.sec;out.clock.nanosec=msg.sim.nsec;self.clock.publish(out)

    def pose_message(self,msg):
        if self.closing:return
        for p in msg.pose:
            if p.name=='uwa_grasp_carton':
                t=np.eye(4);t[:3,3]=[p.position.x,p.position.y,p.position.z]
                t[:3,:3]=Rotation.from_quat([p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w]).as_matrix()
                self.pose.publish(String(data=json.dumps(dict(T_world_object=t.tolist(),
                    source='simulation_ground_truth',stamp=msg.header.stamp.sec+msg.header.stamp.nsec*1e-9))))

    def contacts_message(self,msg):
        if self.closing:return
        pads={a:dict(left_pad=False,right_pad=False) for a in ARMS};support=False;records=[]
        for c in msg.contact:
            names=(c.collision1.name,c.collision2.name)
            if not any('uwa_grasp_carton' in n for n in names):continue
            support |= any('table_plate' in n for n in names)
            for arm in ARMS:
                for side in ('left','right'):
                    if any(arm+'_robotiq_85_'+side+'_finger_tip' in n for n in names):pads[arm][side+'_pad']=True
            records.append(dict(collisions=list(names),positions=[[p.x,p.y,p.z] for p in c.position],
                depths=list(c.depth)))
        self.contact.publish(String(data=json.dumps(dict(pads=pads,supported=support,contacts=records,
            stamp=msg.header.stamp.sec+msg.header.stamp.nsec*1e-9))))

    def camera(self,publisher,convert,arm,msg):
        if not self.closing:publisher.publish(convert(msg,arm))

    def close(self):
        self.closing=True
        for topic in self.topics:self.transport.unsubscribe(topic)
        self.topics=[]

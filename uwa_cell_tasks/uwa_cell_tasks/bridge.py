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
from pathlib import Path
from collections import deque
from std_srvs.srv import Trigger
import uuid


class TelemetryBridge(Node):
    def __init__(self, namespace, world):
        super().__init__('task_telemetry',namespace=namespace)
        self.transport=TransportNode();self.lock=Lock();self.topics=[];self.closing=False;self.sim_stamp=0.
        self.clock=self.create_publisher(Clock,namespace+'/clock',qos_profile_sensor_data)
        self.contact=self.create_publisher(String,'tasks/contacts',10)
        self.pose=self.create_publisher(String,'tasks/object_truth',10)
        self.subscribe(GzClock,'/world/'+world+'/clock',self.clock_message)
        self.subscribe(Contacts,'/world/'+world+'/model/uwa_grasp_carton/link/body/sensor/carton_contacts/contact',self.contacts_message)
        self.subscribe(Pose_V,'/uwa_grasp_carton/pose',self.pose_message)

    def subscribe(self,kind,topic,callback):
        if not self.transport.subscribe(kind,topic,callback):raise RuntimeError('Subscription failed '+topic)
        self.topics.append(topic)

    def clock_message(self,msg):
        if self.closing:return
        self.sim_stamp=msg.sim.sec+msg.sim.nsec/1e9
        out=Clock();out.clock.sec=msg.sim.sec;out.clock.nanosec=msg.sim.nsec;self.clock.publish(out)

    def pose_message(self,msg):
        if self.closing:return
        for p in msg.pose:
            if p.name=='uwa_grasp_carton':
                t=np.eye(4);t[:3,3]=[p.position.x,p.position.y,p.position.z]
                t[:3,:3]=Rotation.from_quat([p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w]).as_matrix()
                self.pose.publish(String(data=json.dumps(dict(T_world_object=t.tolist(),
                    source='simulation_ground_truth',stamp=self.sim_stamp,stamp_source='world_clock_at_receipt'))))

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

    def close(self):
        self.closing=True
        for topic in self.topics:self.transport.unsubscribe(topic)
        self.topics=[]


class ImageCapture(Node):
    """Photo traffic never enters the clock/contact/command Python processes."""
    def __init__(self,namespace,directory):
        super().__init__('task_image_capture',namespace=namespace)
        self.directory=Path(directory)/'captures';self.directory.mkdir(parents=True,exist_ok=True)
        self.transport=TransportNode();self.lock=Lock();self.topics=[];self.closing=False
        self.frames={a:deque(maxlen=3) for a in ARMS+('oak',)};self.info={}
        for arm in self.frames:
            base=namespace+('/oak_overview/rgb/' if arm=='oak' else '/'+arm+'/wrist_camera/')
            for suffix,kind,callback in [('image_raw',GzImage,self.image),('camera_info',GzInfo,self.camera_info)]:
                topic=base+suffix
                if not self.transport.subscribe(kind,topic,partial(callback,arm)):raise RuntimeError('Camera subscription failed '+topic)
                self.topics.append(topic)
        self.create_service(Trigger,'tasks/camera_capture',self.capture)

    def camera_info(self,arm,msg):
        with self.lock:self.info[arm]=msg

    def image(self,arm,msg):
        from gz.msgs.image_pb2 import RGB_INT8
        with self.lock:
            if self.closing or arm not in self.info or msg.pixel_format_type!=RGB_INT8:return
            info=self.info[arm]
            stamp=msg.header.stamp.sec+msg.header.stamp.nsec/1e9
            if self.frames[arm] and stamp<=self.frames[arm][-1]['stamp']:return
            if (msg.width,msg.height)!=(info.width,info.height):return
            # No ROS Image serialization and no image processing here.
            pixels=np.frombuffer(msg.data,np.uint8).reshape(msg.height,msg.step)[:,:msg.width*3].reshape(msg.height,msg.width,3)
            self.frames[arm].append(dict(arm=arm,stamp=stamp,K=list(info.intrinsics.k),D=list(info.distortion.k),
                pixels=pixels,environment='own_gazebo_renderer'))

    def capture(self,req,res):
        with self.lock:
            for frames in self.frames.values():frames.clear()
        deadline=time.monotonic()+30.
        snapshot=None
        while time.monotonic()<deadline and not self.closing:
            with self.lock:
                if all(len(frames)==3 for frames in self.frames.values()):
                    snapshot=[dict(frame) for frames in self.frames.values() for frame in frames];break
            time.sleep(.02)
        if snapshot is None:
            res.success=False;res.message='WAITING for three fresh frames per renderer';return res
        destination=self.directory/uuid.uuid4().hex;destination.mkdir()
        records=[]
        for index,frame in enumerate(snapshot):
            path=destination/f'{frame["arm"]}-{index}.npy'
            np.save(path,frame.pop('pixels')[:,:,::-1])
            records.append(dict(frame,image=str(path.resolve())))
        res.success=True;res.message=json.dumps(records);return res

    def close(self):
        self.closing=True
        for topic in self.topics:self.transport.unsubscribe(topic)
        self.topics=[]

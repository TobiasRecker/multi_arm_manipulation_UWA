"""Own only the static overview camera; never restart the cell or command arms."""
import fcntl
from functools import partial
import os
from pathlib import Path
import time
from threading import Lock
import xml.etree.ElementTree as ET
import numpy as np

from geometry_msgs.msg import Point, TransformStamped
from gz.msgs.boolean_pb2 import Boolean
from gz.msgs.camera_info_pb2 import CameraInfo as GzInfo
from gz.msgs.entity_factory_pb2 import EntityFactory
from gz.msgs.entity_pb2 import Entity
from gz.msgs.image_pb2 import Image as GzImage
from gz.transport import Node as TransportNode
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import CameraInfo, Image
from std_srvs.srv import Trigger
from tf2_ros import StaticTransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray

from .camera_bridge import image_message, info_message
from .configuration import default_layout_path, load_layout
from .overview import MODEL, FRAME, TOPIC, camera_config, intrinsic, model_sdf, transforms


class Overview(Node):
    def __init__(self):
        super().__init__('oak_overview', namespace='uwa_cell')
        self.declare_parameter('layout', str(default_layout_path()))
        self.declare_parameter('world', 'uwa_lab')
        self.world = self.get_parameter('world').value
        self.transport = TransportNode()
        self.broadcaster = StaticTransformBroadcaster(self)
        self.markers = self.create_publisher(MarkerArray, '/uwa_cell/oak_overview/markers',
            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.ready, self.closing = False, False
        self.callback_lock = Lock()
        self.subscriptions_gz = []
        self.callbacks = []
        for suffix, gz_type, ros_type, convert in (
                ('image_raw', GzImage, Image, image_message),
                ('camera_info', GzInfo, CameraInfo, info_message)):
            topic = TOPIC + '/' + suffix
            pub = self.create_publisher(ros_type, topic, qos_profile_sensor_data)
            callback = partial(self.receive, pub, convert)
            self.callbacks.append(callback)
            if not self.transport.subscribe(gz_type, topic, callback):
                raise RuntimeError(f'Could not subscribe to {topic}')
            self.subscriptions_gz.append(topic)
        self.reload_service = self.create_service(Trigger, '~/reload', self.reload)
        deadline = time.monotonic() + 60
        while rclpy.ok():
            try:
                self.apply()
                break
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)

    def request(self, suffix, message, request_type, timeout=4000):
        ok, response = self.transport.request(
            f'/world/{self.world}/{suffix}', message, request_type, Boolean, timeout)
        return ok and response.data

    def remove(self):
        return self.request('remove', Entity(name=MODEL, type=Entity.MODEL), Entity, 1000)

    def apply(self):
        layout = load_layout(self.get_parameter('layout').value)
        cfg = camera_config(layout)  # Validate before touching an existing camera.
        self.ready = False
        self.remove()
        if cfg['enabled']:
            time.sleep(.15)
            if not self.request('create', EntityFactory(sdf=model_sdf(cfg), name=MODEL,
                                                       allow_renaming=False), EntityFactory):
                raise RuntimeError('Could not spawn OAK overview; is the Gazebo cell running?')
            _, optical = transforms(cfg)
            msg = TransformStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id, msg.child_frame_id = 'world', FRAME
            msg.transform.translation.x, msg.transform.translation.y, msg.transform.translation.z = optical[:3,3].tolist()
            q = Rotation.from_matrix(optical[:3,:3]).as_quat()
            msg.transform.rotation.x, msg.transform.rotation.y, msg.transform.rotation.z, msg.transform.rotation.w = q.tolist()
            self.broadcaster.sendTransform(msg)
            self.ready = True
        self.get_logger().info(f'OAK overview: enabled={cfg["enabled"]}, '
            f'{cfg["width"]}x{cfg["height"]}@{cfg["rate"]}, '
            f'xyz={cfg["xyz"]}, target={cfg["look_at"]}; nominal, uncalibrated')
        self.publish_markers(cfg)

    def publish_markers(self, cfg):
        clear = Marker(action=Marker.DELETEALL)
        clear.header.frame_id = 'world'
        message = MarkerArray(markers=[clear])
        if cfg['enabled']:
            def pose_matrix(text):
                values = np.fromstring(text or '0 0 0 0 0 0',sep=' ')
                result = np.eye(4)
                result[:3,3] = values[:3]
                result[:3,:3] = Rotation.from_euler('xyz',values[3:]).as_matrix()
                return result
            for link in ET.fromstring(model_sdf(cfg)).findall('model/link'):
                parent = pose_matrix(link.findtext('pose'))
                for visual in link.findall('visual'):
                    pose = parent @ pose_matrix(visual.findtext('pose'))
                    marker = Marker(ns='oak_overview', id=len(message.markers), type=Marker.CUBE)
                    marker.header.frame_id = 'world'
                    marker.pose.position.x,marker.pose.position.y,marker.pose.position.z = pose[:3,3].tolist()
                    q = Rotation.from_matrix(pose[:3,:3]).as_quat().tolist()
                    marker.pose.orientation.x,marker.pose.orientation.y,marker.pose.orientation.z,marker.pose.orientation.w = q
                    marker.scale.x,marker.scale.y,marker.scale.z = map(float,visual.findtext('geometry/box/size').split())
                    marker.color.r,marker.color.g,marker.color.b,marker.color.a = map(float,visual.findtext('material/diffuse').split())
                    message.markers.append(marker)
            # A fixed-length frustum symbol, not a guarantee against occlusion.
            optical = transforms(cfg)[1]
            pixels = np.array([[0,0,1],[cfg['width'],0,1],
                               [cfg['width'],cfg['height'],1],[0,cfg['height'],1]])
            rays = pixels @ np.linalg.inv(intrinsic(cfg)).T * 2.5
            corners = rays @ optical[:3,:3].T + optical[:3,3]
            frustum = Marker(ns='oak_overview',id=len(message.markers),type=Marker.LINE_LIST)
            frustum.header.frame_id='world'
            frustum.pose.orientation.w=1.
            frustum.scale.x=.008
            frustum.color.r,frustum.color.g,frustum.color.b,frustum.color.a=.15,.6,1.,.45
            for i in range(4):
                for a,b in [(optical[:3,3],corners[i]),(corners[i],corners[(i+1)%4])]:
                    frustum.points.extend([Point(x=float(a[0]),y=float(a[1]),z=float(a[2])),
                                           Point(x=float(b[0]),y=float(b[1]),z=float(b[2]))])
            message.markers.append(frustum)
        self.markers.publish(message)

    def reload(self, request, response):
        try:
            self.apply()
            response.success, response.message = True, 'Overview camera reloaded; robot state preserved.'
        except Exception as error:
            response.success, response.message = False, str(error)
        return response

    def receive(self, publisher, convert, source):
        with self.callback_lock:
            if self.ready and not self.closing and rclpy.ok():
                try:
                    publisher.publish(convert(source, frame_id=FRAME))
                except Exception as error:
                    if rclpy.ok():
                        self.get_logger().error(str(error), throttle_duration_sec=5)

    def disconnect(self):
        with self.callback_lock:
            self.closing = True
        for topic in self.subscriptions_gz:
            self.transport.unsubscribe(topic)
        self.remove()


def main():
    # A manual start can coexist with a later normal cell launch; one owner only.
    partition = ''.join(c for c in os.environ.get('GZ_PARTITION','default') if c.isalnum() or c in '_-')
    lock = Path(f'/tmp/uwa-oak-overview-{os.getuid()}-{partition}.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('OAK overview is already managed in this Gazebo partition.', flush=True)
        return
    rclpy.init()
    node = None
    try:
        node = Overview()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node:
            node.disconnect()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        lock.close()

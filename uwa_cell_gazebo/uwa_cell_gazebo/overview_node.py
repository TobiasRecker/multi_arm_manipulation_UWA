"""Own only the static overview camera; never restart the cell or command arms."""
import fcntl
from copy import deepcopy
from functools import partial
import os
from pathlib import Path
import time
from threading import Lock
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
from .overview import camera_config, camera_keys, intrinsic, model_sdf, transforms
from .overview_visuals import sdf_visual_markers


class Overview(Node):
    def __init__(self):
        super().__init__('oak_overview', namespace='uwa_cell')
        self.declare_parameter('layout', str(default_layout_path()))
        self.declare_parameter('world', 'uwa_lab')
        self.declare_parameter('image_sensors',True)
        self.image_sensors=self.get_parameter('image_sensors').value
        self.world = self.get_parameter('world').value
        self.transport = TransportNode()
        self.broadcaster = StaticTransformBroadcaster(self)
        self.markers = self.create_publisher(MarkerArray, '/uwa_cell/oak_overview/markers',
            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.ready, self.closing = False, False
        self.callback_lock = Lock()
        self.bridges = {}
        self.models = set()
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

    def bridge_images(self, configs):
        desired = {cfg['topic']+'/'+suffix: (cfg['frame_id'], gz_type, ros_type, convert)
                   for cfg in configs if cfg['enabled'] and self.image_sensors
                   for suffix, gz_type, ros_type, convert in (
                       ('image_raw', GzImage, Image, image_message),
                       ('camera_info', GzInfo, CameraInfo, info_message))}
        for topic in self.bridges.keys() - desired.keys():
            self.transport.unsubscribe(topic)
            publisher, _ = self.bridges.pop(topic)
            self.destroy_publisher(publisher)
        for topic, (frame, gz_type, ros_type, convert) in desired.items():
            if topic in self.bridges:
                continue
            pub = self.create_publisher(ros_type, topic, qos_profile_sensor_data)
            callback = partial(self.receive, pub, convert, frame)
            if not self.transport.subscribe(gz_type, topic, callback):
                self.destroy_publisher(pub)
                raise RuntimeError(f'Could not subscribe to {topic}')
            self.bridges[topic] = (pub, callback)

    def remove(self, model):
        return self.request('remove', Entity(name=model, type=Entity.MODEL), Entity, 1000)

    def apply(self):
        layout = load_layout(self.get_parameter('layout').value)
        configs = [camera_config(layout, key) for key in camera_keys(layout)]
        models = [(cfg, model_sdf(cfg, image_sensors=self.image_sensors))
                  for cfg in configs if cfg['enabled']]
        self.ready = False
        self.bridge_images(configs)
        desired = {cfg['model'] for cfg, _ in models}
        for name in self.models | {cfg['model'] for cfg in configs}:
            self.remove(name)
        self.models = desired
        frames = []
        if models:
            time.sleep(.15)
        for cfg, sdf in models:
            if not self.request('create', EntityFactory(sdf=sdf, name=cfg['model'],
                                                       allow_renaming=False), EntityFactory):
                raise RuntimeError(f"Could not spawn {cfg['model']} in {self.world}")
            msg = TransformStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            if 'board_optical' in cfg and layout['charuco']['enabled']:
                msg.header.frame_id = 'right_charuco'
                optical = np.asarray(cfg['board_optical'])
            else:
                msg.header.frame_id = 'world'
                optical = transforms(cfg)[1]
            msg.child_frame_id = cfg['frame_id']
            msg.transform.translation.x, msg.transform.translation.y, msg.transform.translation.z = optical[:3,3].tolist()
            q = Rotation.from_matrix(optical[:3,:3]).as_quat()
            msg.transform.rotation.x, msg.transform.rotation.y, msg.transform.rotation.z, msg.transform.rotation.w = q.tolist()
            frames.append(msg)
            if cfg.get('real_frame_id'):
                real = deepcopy(msg)
                real.child_frame_id = cfg['real_frame_id']
                frames.append(real)
            self.get_logger().info(f"{cfg['model']}: {cfg['width']}x{cfg['height']}, frame={cfg['frame_id']}, "
                                   f"reference={msg.header.frame_id}, images={self.image_sensors}")
        if frames:
            self.broadcaster.sendTransform(frames)
        self.publish_markers(models)
        self.ready = True

    def publish_markers(self, models):
        clear = Marker(action=Marker.DELETEALL)
        clear.header.frame_id = 'world'
        message = MarkerArray(markers=[clear])
        for cfg, sdf in models:
            namespace = 'oak_overview' if cfg['camera']=='oak4' else 'oak_usb'
            message.markers.extend(sdf_visual_markers(sdf, namespace))
            # A fixed-length frustum symbol, not a guarantee against occlusion.
            optical = transforms(cfg)[1]
            pixels = np.array([[0,0,1],[cfg['width'],0,1],
                               [cfg['width'],cfg['height'],1],[0,cfg['height'],1]])
            import cv2
            rays_xy = cv2.undistortPoints(pixels[:,:2].reshape(-1,1,2).astype(float),
                intrinsic(cfg),np.asarray(cfg.get('distortion',np.zeros(5)))).reshape(-1,2)
            rays = np.c_[rays_xy,np.ones(4)] * 2.5
            corners = rays @ optical[:3,:3].T + optical[:3,3]
            frustum = Marker(ns=namespace,id=len(message.markers),type=Marker.LINE_LIST)
            frustum.header.frame_id='world'
            frustum.pose.orientation.w=1.
            frustum.scale.x=.008
            frustum.color.r,frustum.color.g,frustum.color.b,frustum.color.a=.15,.6,1.,.45
            if cfg['camera'] == 'oak_usb':
                frustum.color.r, frustum.color.g, frustum.color.b = 1., .55, .1
            for i in range(4):
                for a,b in [(optical[:3,3],corners[i]),(corners[i],corners[(i+1)%4])]:
                    frustum.points.extend([Point(x=float(a[0]),y=float(a[1]),z=float(a[2])),
                                           Point(x=float(b[0]),y=float(b[1]),z=float(b[2]))])
            message.markers.append(frustum)
            if cfg.get('quality_status'):
                label = Marker(ns=namespace,id=len(message.markers),type=Marker.TEXT_VIEW_FACING)
                label.header.frame_id='world'
                label.pose.orientation.w=1.
                label.pose.position.x,label.pose.position.y,label.pose.position.z=(optical[:3,3]+[0,0,.18]).tolist()
                label.scale.z=.055
                label.color.r,label.color.g,label.color.b,label.color.a=1.,.85,.15,1.
                if 'board_optical' in cfg:
                    name = 'OAK4' if cfg['camera']=='oak4' else 'USB OAK-D Pro'
                    label.text = f"{name} | right_charuco | focus {cfg['focus']}"
                else:
                    label.text='OAK: PRELIMINARY / USER ACCEPTED\nWorld anchor provisional'
                message.markers.append(label)
        self.markers.publish(message)

    def reload(self, request, response):
        try:
            self.apply()
            response.success, response.message = True, 'Overview camera reloaded; robot state preserved.'
        except Exception as error:
            response.success, response.message = False, str(error)
        return response

    def receive(self, publisher, convert, frame, source):
        with self.callback_lock:
            if self.ready and not self.closing and rclpy.ok():
                try:
                    publisher.publish(convert(source, frame_id=frame))
                except Exception as error:
                    if rclpy.ok():
                        self.get_logger().error(str(error), throttle_duration_sec=5)

    def disconnect(self):
        with self.callback_lock:
            self.closing = True
        for topic in self.bridges:
            self.transport.unsubscribe(topic)
        for name in self.models:
            self.remove(name)


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

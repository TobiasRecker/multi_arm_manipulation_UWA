"""Own only the static overview camera; never restart the cell or command arms."""
import fcntl
from functools import partial
import os
from pathlib import Path
import time
from threading import Lock

from geometry_msgs.msg import TransformStamped
from gz.msgs.boolean_pb2 import Boolean
from gz.msgs.camera_info_pb2 import CameraInfo as GzInfo
from gz.msgs.entity_factory_pb2 import EntityFactory
from gz.msgs.entity_pb2 import Entity
from gz.msgs.image_pb2 import Image as GzImage
from gz.transport import Node as TransportNode
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import CameraInfo, Image
from std_srvs.srv import Trigger
from tf2_ros import StaticTransformBroadcaster

from .camera_bridge import image_message, info_message
from .configuration import default_layout_path, load_layout
from .overview import MODEL, FRAME, TOPIC, camera_config, model_sdf, transforms


class Overview(Node):
    def __init__(self):
        super().__init__('oak_overview', namespace='uwa_cell')
        self.declare_parameter('layout', str(default_layout_path()))
        self.declare_parameter('world', 'uwa_lab')
        self.world = self.get_parameter('world').value
        self.transport = TransportNode()
        self.broadcaster = StaticTransformBroadcaster(self)
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

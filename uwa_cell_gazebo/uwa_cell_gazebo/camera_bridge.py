"""Bridge the cell's RGB cameras, disconnecting transport before ROS shutdown.

Uses the same Python Gazebo bindings as clock_bridge to avoid this installation's
C++ parameter_bridge library-unloading crash. All image headers use optical TFs.
"""
from functools import partial
from threading import Lock

from gz.msgs.camera_info_pb2 import CameraInfo as GazeboCameraInfo
from gz.msgs.image_pb2 import Image as GazeboImage
from gz.msgs.image_pb2 import RGB_INT8
from gz.transport import Node as TransportNode
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image

from .configuration import ROBOT_IDS


def header(target, source, robot_id, frame_id=None):
    target.stamp.sec = source.stamp.sec
    target.stamp.nanosec = source.stamp.nsec
    target.frame_id = frame_id or f'{robot_id}_wrist_camera_optical_frame'


def image_message(source, robot_id=None, *, frame_id=None):
    if source.pixel_format_type != RGB_INT8:
        raise ValueError(f'Expected RGB_INT8, got {source.pixel_format_type}')
    target = Image()
    header(target.header, source.header, robot_id, frame_id)
    target.width, target.height = source.width, source.height
    target.encoding, target.is_bigendian = 'rgb8', 0
    target.step, target.data = source.step, source.data
    return target


def info_message(source, robot_id=None, *, frame_id=None):
    target = CameraInfo()
    header(target.header, source.header, robot_id, frame_id)
    target.width, target.height = source.width, source.height
    target.distortion_model = 'plumb_bob'
    target.d = list(source.distortion.k)
    target.k = list(source.intrinsics.k)
    target.p = list(source.projection.p)
    target.r = list(source.rectification_matrix) or [1., 0., 0., 0., 1., 0., 0., 0., 1.]
    return target


class CameraBridge(Node):
    def __init__(self):
        super().__init__('camera_bridge')
        self.declare_parameter('robot_ids', list(ROBOT_IDS))
        robot_ids = self.get_parameter('robot_ids').value
        if not robot_ids or not set(robot_ids) <= set(ROBOT_IDS):
            raise ValueError('robot_ids must contain cell robot IDs')
        self.lock, self.closing = Lock(), False
        self.transport, self.topics, self.callbacks = TransportNode(), [], []
        self.outputs = []
        try:
            for robot_id in robot_ids:
                for suffix, gz_type, ros_type, convert in (
                    ('image_raw', GazeboImage, Image, image_message),
                    ('camera_info', GazeboCameraInfo, CameraInfo, info_message),
                ):
                    topic = f'/uwa_cell/{robot_id}/wrist_camera/{suffix}'
                    publisher = self.create_publisher(ros_type, topic, qos_profile_sensor_data)
                    self.outputs.append(publisher)
                    callback = partial(self.receive, publisher, convert, robot_id)
                    self.callbacks.append(callback)
                    if not self.transport.subscribe(gz_type, topic, callback):
                        raise RuntimeError(f'Could not subscribe to {topic}')
                    self.topics.append(topic)
        except Exception:
            self.disconnect()
            raise

    def receive(self, publisher, convert, robot_id, message):
        with self.lock:
            if self.closing or not rclpy.ok():
                return
            try:
                publisher.publish(convert(message, robot_id))
            except Exception as error:
                if rclpy.ok():
                    self.get_logger().error(f'{robot_id}: camera conversion failed: {error}',
                                            throttle_duration_sec=5)

    def disconnect(self):
        with self.lock:
            self.closing = True
        for topic in self.topics:
            self.transport.unsubscribe(topic)
        self.topics.clear()


def main():
    rclpy.init()
    node = CameraBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.disconnect()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

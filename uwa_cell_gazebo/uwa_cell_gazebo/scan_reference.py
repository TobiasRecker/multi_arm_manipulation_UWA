"""Optional RViz reference, deliberately unrelated to Gazebo collision shapes."""
import numpy as np
from scipy.spatial.transform import Rotation

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import TransformStamped
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header
from tf2_ros import StaticTransformBroadcaster

from .configuration import load_layout
from .scan import prepare_scan
from .scan_filter import filter_reference


class ScanReference(Node):
    def __init__(self):
        super().__init__('scan_reference')
        layout = self.declare_parameter('layout', '').value or None
        layout = load_layout(layout)
        settings = layout['scan']
        path = prepare_scan(settings['source'], settings)
        with np.load(path, allow_pickle=False) as data:
            xyz = np.asarray(data['xyz'], dtype=np.float32) * settings['scale']
            rgb = np.asarray(data['rgb'], dtype=np.uint32)
        if not np.isfinite(xyz).all():
            raise ValueError('Scaled scan coordinates are not finite; check scan.scale')
        xyz, rgb, cleanup = filter_reference(xyz, rgb, layout)
        self.get_logger().info(
            f'Scan display cleanup: {cleanup["input_points"]} -> {len(xyz)} points; '
            f'{cleanup["outside_radius"]} outside radius; '
            f'{sum(cleanup["excluded_by_box"].values())} inside fixed robot masks.')
        points = np.empty(len(xyz), dtype=[
            ('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('rgb', '<u4')])
        for index, key in enumerate(('x', 'y', 'z')):
            points[key] = xyz[:, index]
        points['rgb'] = (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]
        fields = [PointField(name=key, offset=index * 4,
                             datatype=PointField.FLOAT32 if key != 'rgb' else PointField.UINT32,
                             count=1) for index, key in enumerate(('x', 'y', 'z', 'rgb'))]
        self.cloud = point_cloud2.create_cloud(Header(frame_id='uwa_scan_reference'), fields, points)
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(PointCloud2, 'scan_reference', qos)
        transform = TransformStamped()
        transform.header.frame_id = 'world'
        transform.child_frame_id = 'uwa_scan_reference'
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.transform.translation.x = settings['xyz'][0]
        transform.transform.translation.y = settings['xyz'][1]
        transform.transform.translation.z = settings['xyz'][2]
        q = Rotation.from_euler('xyz', settings['rpy']).as_quat()
        transform.transform.rotation.x, transform.transform.rotation.y = float(q[0]), float(q[1])
        transform.transform.rotation.z, transform.transform.rotation.w = float(q[2]), float(q[3])
        self.broadcaster = StaticTransformBroadcaster(self)
        self.broadcaster.sendTransform(transform)
        self.timer = self.create_timer(2.0, self.publish)
        self.publish()
        self.get_logger().warning(
            f'UNREGISTERED scan reference: {len(points)} points. '
            'Scale/pose are estimates; these points never enter collision physics.')

    def publish(self):
        self.cloud.header.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(self.cloud)


def main():
    rclpy.init()
    node = None
    try:
        node = ScanReference()
        rclpy.spin(node)
    except (OSError, ValueError, KeyError) as exc:
        # This is an optional reference; the separate Gazebo launch keeps running.
        rclpy.logging.get_logger('scan_reference').error(f'Scan reference unavailable: {exc}')
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

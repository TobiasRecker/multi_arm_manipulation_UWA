"""Forward Gazebo simulation time, explicitly disconnecting transport on exit."""
from threading import Lock

from gz.msgs.clock_pb2 import Clock as GazeboClock
from gz.transport import Node as TransportNode
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock


class ClockBridge(Node):
    def __init__(self):
        super().__init__('clock_bridge')
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        self.publisher = self.create_publisher(Clock, '/clock', qos)
        self.lock = Lock()
        self.closing = False
        self.transport = TransportNode()
        if not self.transport.subscribe(GazeboClock, '/clock', self.receive):
            raise RuntimeError('Could not subscribe to Gazebo /clock')

    def receive(self, message):
        with self.lock:
            if self.closing or not rclpy.ok():
                return
            clock = Clock()
            clock.clock.sec = message.sim.sec
            clock.clock.nanosec = message.sim.nsec
            try:
                self.publisher.publish(clock)
            except Exception:
                if rclpy.ok():
                    raise

    def disconnect(self):
        with self.lock:
            self.closing = True
        # Unsubscribe before destroying the ROS publisher/context. Gazebo invokes
        # transport callbacks on its own thread, independently of the ROS executor.
        self.transport.unsubscribe('/clock')


def main():
    rclpy.init()
    node = ClockBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.disconnect()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

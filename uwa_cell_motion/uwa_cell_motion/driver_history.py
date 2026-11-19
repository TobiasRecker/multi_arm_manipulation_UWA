"""Receive driver samples while the task thread checks geometry or waits on RPC.

This receiver sends no commands. The consumer still checks each source time,
clock epoch, sampling gap and spatial comparison before admitting motion.
"""
import threading

from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import JointState

from .node import MotionNode


class DriverHistoryReceiver:
    def __init__(self, profiles, arms, receive):
        self.node=MotionNode('hardware_driver_history',namespace='/uwa_cell')
        self.executor=SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.done=threading.Event()
        self.error=None
        # Keep the existing sensor-data depth: a deep FIFO can stay permanently
        # older than the 200-ms gate at 500Hz. Independent acquisition, rather
        # than a large queue, bridges task-thread geometry/RPC work.
        qos=QoSProfile(depth=5,reliability=ReliabilityPolicy.BEST_EFFORT,
                       durability=DurabilityPolicy.VOLATILE)
        for arm in arms:
            self.node.create_subscription(JointState,profiles[arm]['namespace']+'/joint_states',
                lambda msg,r=arm:receive(r,msg),qos)
        self.worker=threading.Thread(target=self._run,name='driver-history',daemon=True)
        self.worker.start()

    def _run(self):
        try:
            while not self.done.is_set():
                self.executor.spin_once(timeout_sec=.01)
        except Exception as error:
            self.error=str(error)
            self.done.set()

    def close(self):
        self.done.set()
        self.executor.wake()
        self.worker.join(timeout=1.)
        if self.worker.is_alive():
            raise RuntimeError('Driver history receiver did not stop')
        self.executor.remove_node(self.node)
        self.executor.shutdown(timeout_sec=1.)
        self.node.destroy_node()

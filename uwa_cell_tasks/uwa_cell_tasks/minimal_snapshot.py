"""Read the shared native-state snapshot, without stationary or gripper probes."""
import json
import time

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from uwa_cell_motion.common import ROBOT_IDS
from uwa_cell_motion.hardware_state import require_domain


def observe(mode='hardware', timeout=15.):
    require_domain(mode)
    owns = not rclpy.ok()
    if owns:
        rclpy.init(args=[])
    node = rclpy.create_node('minimal_planning_snapshot')
    latest = {}
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
    def receive(msg):
        try:
            value = json.loads(msg.data)
            if isinstance(value, dict):
                latest.clear()
                latest.update(value)
        except (ValueError, TypeError):
            pass
    node.create_subscription(String, '/uwa_cell/protection/state', receive, qos)
    deadline = time.monotonic()+timeout
    try:
        while True:
            rclpy.spin_once(node, timeout_sec=.05)
            records = latest.get('records', {})
            now = time.monotonic()
            if set(records) == set(ROBOT_IDS) and all(
                    now-row.get('received_monotonic_s', row.get('received', 0.)) <= .2
                    for row in records.values()):
                break
            if now >= deadline:
                raise TimeoutError('Current native positions unavailable for planning snapshot')
        arms = {}
        for arm, row in records.items():
            sample = dict(actual_q=row['q'], actual_qd=row.get('v', [0.]*6),
                          device_timestamp_s=row.get('device_timestamp', row.get('device_timestamp_s')),
                          received_monotonic_s=row.get('received_monotonic_s', row.get('received')))
            arms[arm] = dict(observed=True, samples=[sample],
                             source='Shared C++ RTDE source; no stationarity test')
        return dict(protection_backend='minimal', model_signature=latest.get('model_signature'),
                    arms=arms, grippers={}, commands_sent=[])
    finally:
        node.destroy_node()
        if owns and rclpy.ok():
            rclpy.shutdown()

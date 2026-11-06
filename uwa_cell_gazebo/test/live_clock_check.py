"""Optional live transport/shutdown test; requires the simulated Gazebo world."""
import os
from pathlib import Path
import signal
import subprocess
import time

from ament_index_python.packages import get_package_prefix
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock


def main():
    assert os.environ.get('ROS_DOMAIN_ID') == '64'
    rclpy.init()
    node = rclpy.create_node('uwa_clock_bridge_check')
    samples = []
    node.create_subscription(Clock, '/uwa_cell_test_clock',
                             lambda m: samples.append(m.clock.sec + m.clock.nanosec * 1e-9),
                             qos_profile_sensor_data)
    executable = Path(get_package_prefix('uwa_cell_gazebo')) / 'lib/uwa_cell_gazebo/clock_bridge'
    try:
        for trial in range(3):
            samples.clear()
            process = subprocess.Popen([str(executable), '--ros-args',
                                        '-r', '/clock:=/uwa_cell_test_clock'])
            try:
                end = time.monotonic() + 10
                while len(samples) < 10 and time.monotonic() < end:
                    rclpy.spin_once(node, timeout_sec=.1)
                assert len(samples) >= 10 and samples[-1] > samples[0], samples
            finally:
                process.send_signal(signal.SIGINT)
                code = process.wait(timeout=8)
            assert code == 0, code
            print(f'Trial {trial + 1}: clock advances, clean shutdown', flush=True)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

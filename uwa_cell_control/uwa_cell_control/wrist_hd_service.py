"""Camera-only ROS HD capture service; no motion, power, brake or program calls."""
import argparse
import json
import os
from pathlib import Path
import threading

from .wrist_hd import NativeCapture, SSH, control_path


def main():
    from match_ur_hardware.profiles import load_profiles
    ws = Path(os.environ.get('UWA_WS', str(Path.home() / 'UWA_ws')))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', default=str(ws / 'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'))
    parser.add_argument('--arm', required=True)
    parser.add_argument('--connect', action='store_true', help='Only establish interactive SSH authentication, then exit')
    parser.add_argument('--output', default=str(ws / 'setup/calibration/wrist_hd/service'))
    args = parser.parse_args()
    profiles = load_profiles(args.inventory)
    if args.arm not in profiles or not profiles[args.arm]['ip']:
        parser.error('Select a configured physical arm')
    profile = profiles[args.arm]
    ssh = SSH(profile['ip'], control_path(args.arm, profile['ip']))
    if args.connect:
        ssh.connect()
        print('SSH session ready. No password saved. Start the HD service separately.')
        return 0
    os.environ['ROS_DOMAIN_ID'] = '66'
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    import rclpy
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.qos import QoSProfile, DurabilityPolicy
    from sensor_msgs.msg import CompressedImage
    from std_srvs.srv import Trigger
    rclpy.init()
    node = rclpy.create_node('wrist_camera_hd', namespace=profile['namespace'])
    capture = NativeCapture(profile['ip'], ssh, Path(args.output) / args.arm)
    lock = threading.Lock()
    state = {'phase': 'IDLE', 'arm': args.arm, 'ip': profile['ip'], 'last_result': None}
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    pub = node.create_publisher(CompressedImage, 'wrist_camera_hd/image/compressed', qos)
    group = ReentrantCallbackGroup()

    def snapshot(request, response):
        response.success = True
        response.message = json.dumps(state)
        return response

    def take(request, response):
        if not lock.acquire(blocking=False):
            response.success = False
            response.message = 'Another HD transaction is active'
            return response
        try:
            state['phase'] = 'CAPTURING'
            result = capture.capture()
            path = Path(result['directory']) / result['frames_metadata'][-1]['image']
            message = CompressedImage()
            # Receipt time only. Native device times remain in capture.log.
            message.header.stamp = node.get_clock().now().to_msg()
            message.header.frame_id = args.arm + '_wrist_camera_optical_frame'
            message.format = 'jpeg'
            message.data = path.read_bytes()
            pub.publish(message)
            state.update(phase='READY', last_result=result['directory'])
            response.success = True
            response.message = json.dumps(result)
        except Exception as error:
            state.update(phase='FAILED', error=str(error))
            node.get_logger().error(str(error))
            response.success = False
            response.message = str(error)
        finally:
            lock.release()
        return response

    node.create_service(Trigger, 'wrist_camera_hd/capture', take, callback_group=group)
    node.create_service(Trigger, 'wrist_camera_hd/status', snapshot, callback_group=group)
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    node.get_logger().info('HD capture ready: ' + profile['namespace'] + '/wrist_camera_hd/capture')
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        # Do not terminate a transaction during its restoration.
        executor.shutdown(wait_for_threads=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0

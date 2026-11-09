"""Observe both ChArUco boards from the overview image, without moving robots."""
import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image

from .charuco import detect_pose
from .configuration import default_layout_path, load_layout
from .overview import TOPIC, coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', type=Path, default=default_layout_path())
    parser.add_argument('--output', type=Path, default=Path('/tmp/uwa-oak-overview-check'))
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args()
    layout = load_layout(args.layout)
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = rclpy.create_node('overview_check', namespace='uwa_cell')
    latest = {}
    subs = [node.create_subscription(typ, TOPIC+'/'+suffix,
        lambda msg, key=suffix: latest.update({key: msg}), qos_profile_sensor_data)
        for typ, suffix in [(Image,'image_raw'), (CameraInfo,'camera_info')]]
    deadline = time.monotonic()+args.timeout
    report = {'coverage_prediction': coverage(layout), 'success': False, 'boards': {}}
    # Retry several actual frames: anti-aliasing and temporary robot occlusion matter.
    seen = set()
    try:
        while time.monotonic()<deadline:
            rclpy.spin_once(node, timeout_sec=.2)
            if set(latest) != {'image_raw','camera_info'}:
                continue
            msg, info = latest['image_raw'], latest['camera_info']
            stamp = (msg.header.stamp.sec,msg.header.stamp.nanosec)
            if stamp in seen:
                continue
            seen.add(stamp)
            if (msg.width,msg.height,msg.header.frame_id)!=(info.width,info.height,info.header.frame_id):
                continue
            if msg.encoding not in ('rgb8','bgr8'):
                raise ValueError(f'Unsupported encoding {msg.encoding}')
            rgb = np.frombuffer(msg.data,dtype=np.uint8).reshape(msg.height,msg.step)[:, :msg.width*3].reshape(msg.height,msg.width,3)
            image = cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR) if msg.encoding=='rgb8' else rgb.copy()
            K = np.array(info.k).reshape(3,3)
            report.update(image_size=[msg.width,msg.height],frame_id=msg.header.frame_id,
                          distinct_frames=len(seen),camera_matrix=K.tolist())
            report['boards'] = {}
            for table in ('left','right'):
                # ArUco's default rejects markers <30px wide in a 4000px image.
                # Use a 32px perimeter floor, independent of world/board poses.
                found = detect_pose(image,K,np.array(info.d),layout['charuco'],table,
                                    min_marker_perimeter_rate=min(.03,32/max(image.shape[:2])))
                if found:
                    report['boards'][table] = {key:found[key] for key in ('corners','reprojection_rms_px')}
                    report['boards'][table]['T_camera_board'] = found['T_camera_board'].tolist()
                    cv2.imwrite(str(args.output/f'{table}-detected.jpg'),found['annotated'])
            cv2.imwrite(str(args.output/'overview.jpg'),image)
            report['success'] = all(report['boards'].get(t,{}).get('corners',0)>=layout['charuco']['min_corners'] for t in ('left','right'))
            if report['success']:
                break
    finally:
        node.destroy_node()
        rclpy.shutdown()
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['success'] else 1)

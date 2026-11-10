"""Explicitly authorized, camera-only focus test on right_rear; restore in finally."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

import cv2
import numpy as np
import yaml
from uwa_cell_control.wrist_camera import WristCamera, save_snapshot


def main():
    ws = Path(os.environ.get('UWA_WS', str(Path.home()/'UWA_ws')))
    repo = ws/'src/multi_arm_manipulation_UWA'
    ip = yaml.safe_load((repo/'config/hardware_inventory.yaml').read_text())['robots']['right_rear']['ip']
    root = ws/'setup/calibration/wrist_focus'/datetime.now(ZoneInfo('Australia/Perth')).strftime('test_%Y%m%d_%H%M%S')
    root.mkdir(parents=True)
    client = WristCamera(ip)
    original = client.settings()
    (root/'original_settings.json').write_text(json.dumps(original, indent=2)+'\n')
    report = {'robot_id': 'right_rear', 'ip': ip, 'original': original,
              'robot_commands_sent': False, 'directory': str(root), 'frames': []}

    def capture(stage):
        jpeg = client.image()
        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('JPEG decode failed')
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        settings = client.settings()
        path = save_snapshot(root, stage, jpeg, settings, dimensions=[image.shape[1], image.shape[0]])
        item = {'stage': stage, 'path': str(path), 'sha256': hashlib.sha256(jpeg).hexdigest(),
                'laplacian_variance': float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                'focus': settings['focus'], 'focusAuto': settings['focusAuto']}
        report['frames'].append(item)
        print(json.dumps(item), flush=True)

    try:
        capture('before')
        # One midpoint focus setting, not a sweep or guessed metre conversion.
        report['write_response'] = client.manual(511)  # API focus 512.
        for i in range(4):
            time.sleep(.65)
            capture(f'manual_512_{i}')
        report['manual_readback_ok'] = report['write_response']['focus'] == 512 and not report['write_response']['focusAuto']
        report['image_bytes_changed'] = any(f['sha256'] != report['frames'][0]['sha256'] for f in report['frames'][1:])
    except Exception as error:
        report['error'] = str(error)
    finally:
        try:
            report['restored'] = client.restore(original)
            report['restore_focus_mode_ok'] = report['restored']['focusAuto'] == original['focusAuto'] and (
                original['focusAuto'] or report['restored']['focus'] == original['focus'])
            report['restore_unrelated_settings_ok'] = all(report['restored'][k] == original[k] for k in original if k not in ('focus', 'focusAuto'))
            # Restored Auto mode may legitimately select a different numeric focus.
            time.sleep(2.)
            capture('restored')
        except Exception as error:
            report['restore_error'] = str(error)
        (root/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('REPORT '+str(root/'report.json'), flush=True)
    if report.get('error') or not report.get('restore_focus_mode_ok') or not report.get('restore_unrelated_settings_ok'):
        raise RuntimeError(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

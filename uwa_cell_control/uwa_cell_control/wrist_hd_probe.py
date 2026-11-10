"""Experimental, camera-only HD probe. Explicit --execute; restore in finally."""
import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time
from zoneinfo import ZoneInfo

from .wrist_camera import WristCamera, CameraError, save_snapshot


def probe(camera, directory):
    import cv2
    import numpy as np

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    report = {'success': False, 'robot_commands_sent': False, 'steps': []}
    original = None
    changed = False

    def checkpoint():
        (directory/'report.json').write_text(json.dumps(report, indent=2)+'\n')

    def step(path, **kwargs):
        entry = {'path': path, 'method': 'POST' if kwargs.get('post') or kwargs.get('body') is not None else 'GET'}
        report['steps'].append(entry)
        checkpoint()
        try:
            value = camera.request(path, **kwargs)
            entry['response'] = value if not isinstance(value, bytes) else {'bytes': len(value)}
            print(path, entry['response'], flush=True)
            checkpoint()
            return value
        except Exception as error:
            entry['error'] = str(error)
            checkpoint()
            raise

    def wait_state(expected, timeout=8.):
        deadline = time.monotonic()+timeout
        while True:
            state = step('/status').get('current state')
            if state == expected:
                return
            if time.monotonic() >= deadline:
                raise CameraError(f'Expected camera state {expected}, got {state}')
            time.sleep(.2)

    try:
        wait_state('Normal', timeout=.1)
        original = camera.settings()
        report['original_settings'] = original
        (directory/'original_settings.json').write_text(json.dumps(original, indent=2)+'\n')
        save_snapshot(directory, 'before', camera.image(), original)
        checkpoint()
        changed = True  # A timed-out state-changing request may still have executed.
        step('/beginbarcode', post=True)
        wait_state('barcode')
        step('/create?barcodeType=0', post=True)
        # State entry may choose defaults: put the user's actual settings back.
        step('/setcamerasettings?setManualValuesIfModeChanged=true', body={'cameraSettings': original})
        try:
            step('/process', post=True)
        except CameraError as error:
            # Native code acquires HD before barcode detection. No barcode in view
            # may fail detection; an independent HD source check is still required.
            if '49156' not in str(error) or 'barcode process failed' not in str(error):
                raise
            report['barcode_detection_failed'] = True
        time.sleep(.5)
        preview = step('/last.jpg?type=color', image=True)
        save_snapshot(directory, 'module_preview', preview, camera.settings())
        mapping = step('/map?type=scaletosource&x=640&y=480')
        report['source_mapping_after_process'] = mapping
        # Do not repeat the earlier invalid export without evidence of an HD source.
        if mapping.get('x', 0) < 1920 or mapping.get('y', 0) < 1080:
            raise CameraError('No HD source confirmed by module/display mapping; native export not attempted')
        step('/rejectmodule', post=True)
        wait_state('Normal')
        step('/beginoperationmode?constantillumination=true')
        wait_state('OperationMode')
        # Deliberately no /captureimage here: keep the previously acquired HD frame.
        jpeg = step('/lastCapture.jpg', image=True)
        decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise CameraError('Native JPEG could not be decoded')
        height, width = decoded.shape[:2]
        report['dimensions'] = [width, height]
        path = save_snapshot(directory, 'native_capture', jpeg, original, dimensions=[width, height])
        report['photo'] = str(path)
        if width*height < 4_000_000:
            raise CameraError(f'Export is {width}×{height}, not a full-resolution 5 MP image')
        report['success'] = True
    except Exception as error:
        report['error'] = str(error)
    finally:
        if changed and original is not None:
            try:
                # Give the vendor watchdog a bounded opportunity to recover after a fault.
                deadline = time.monotonic()+20
                while True:
                    try:
                        state = camera.request('/status').get('current state')
                        break
                    except Exception:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(.5)
                if state == 'barcode':
                    step('/rejectmodule', post=True)
                elif state == 'OperationMode':
                    step('/endoperationmode')
                elif state != 'Normal':
                    raise CameraError(f'Unexpected cleanup state {state}; no global reset sent')
                wait_state('Normal')
                step('/setcamerasettings?setManualValuesIfModeChanged=true', body={'cameraSettings': original})
                if original['focusAuto'] or original['exposureAuto']:
                    camera.trigger(focus=original['focusAuto'], exposure=original['exposureAuto'])
                    # Exposure algorithm may adjust LED. Restore the selected LED controls.
                    camera.request('/setcamerasettings?setManualValuesIfModeChanged=true',
                                   body={'cameraSettings': {k: original[k] for k in ('lightingMode', 'lightingValue')}})
                after = camera.settings()
                report['restored_settings'] = after
                keys = ['focusAuto', 'exposureAuto', 'exposureSensitivity', 'lightingMode', 'lightingValue']
                if not original['focusAuto']:
                    keys += ['focus']
                if not original['exposureAuto']:
                    keys += ['exposure', 'gain']
                report['restore_mismatches'] = [k for k in keys if after.get(k) != original.get(k)]
                report['restore_ok'] = not report['restore_mismatches']
                save_snapshot(directory, 'restored_preview', camera.image(), after)
            except Exception as error:
                report['restore_error'] = str(error)
                report['restore_ok'] = False
        checkpoint()
    return report


def main():
    import yaml
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Perform the explicitly authorized camera-only probe')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.execute:
        print('Dry run. No connection. With --execute: save settings → barcode HD module → '
              'confirm HD source → native export → restore settings. Close camera viewer first.')
        return 0
    ws = Path(os.environ.get('UWA_WS', str(Path.home()/'UWA_ws')))
    inventory = yaml.safe_load((ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml').read_text())
    ip = inventory['robots']['right_rear']['ip']
    root = args.output or ws/'setup/calibration/wrist_hd'/datetime.now(ZoneInfo('Australia/Perth')).strftime('%Y%m%d_%H%M%S')
    with (Path(tempfile.gettempdir())/f'uwa-wrist-focus-{ip}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        result = probe(WristCamera(ip, timeout=6.), root)
    print(json.dumps(result, indent=2))
    return 0 if result['success'] and result.get('restore_ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())

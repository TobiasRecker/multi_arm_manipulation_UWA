#!/usr/bin/env python3
"""Open or reuse the normal native six-camera capture GUI. No robot commands."""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
sys.path.insert(0, str(REPO / 'uwa_cell_control'))
from uwa_cell_control.capture_window import active_window, request_activation

CAMERAS = {'left_front', 'left_rear', 'right_front', 'right_rear', 'oak4', 'oak_usb'}


def reuse(workspace):
    value = active_window(workspace)
    if value:
        if set(value['cameras']) != CAMERAS:
            raise RuntimeError('A different capture window is open. Finish and close it before opening six cameras.')
        request_activation(workspace, value)
        return dict(gui='Using the existing six-camera capture window.', session=value['session'], reused=True)


def open_window(workspace=WORKSPACE):
    if result := reuse(workspace):
        return result
    lock = workspace / 'setup/calibration/three_camera_mobile/.rig.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as lease:
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('UWA Camera Capture is already open. Use its existing window; no camera session was restarted.') from None
    log_path = workspace / 'setup/calibration/six_camera_mobile/window.log'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('ab') as log:
        process = subprocess.Popen(['/bin/bash', str(REPO / 'scripts/camera_capture.sh'),
            '--workspace', str(workspace), '--six-cameras', '--board', 'mobile',
            '--telemetry-source', 'rtde', '--keep-camera-settings'], cwd=workspace,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if result := reuse(workspace):
            return dict(result, gui='Opened the six-camera capture window.', reused=False)
        if process.poll() is not None:
            raise RuntimeError(f'Capture window exited. See {log_path}')
        time.sleep(.2)
    raise RuntimeError(f'Capture window has not registered yet. See {log_path}; do not start a duplicate.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=WORKSPACE)
    print(json.dumps(open_window(parser.parse_args().workspace)))

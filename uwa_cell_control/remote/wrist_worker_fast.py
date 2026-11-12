"""Verified single-switch HD transaction; reuse the proven lock/watchdog. MIT."""
from __future__ import print_function
import json
import os
import subprocess
import sys
import time
import wrist_worker as worker

original_restore = worker.restore
DIRECTORY = None
BINARY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wrist_capture')


def verify_mode():
    output = subprocess.check_output([BINARY, '--verify-mode', '/dev/video0', DIRECTORY],
                                     stderr=subprocess.STDOUT)
    result = json.loads(output.decode('utf-8'))
    if result.get('verified') is not True:
        raise RuntimeError('Actual V4L2 mode restoration not confirmed')
    return result


def restore(service, original):
    started = time.time()
    result = original_restore(service, original)
    restored = time.time()
    try:
        result['v4l2_mode'] = verify_mode()
        result['format_restore_strategy'] = 'visionserver_single_switch'
    except Exception as error:
        # Some firmware may not restore the original interval/format. Fall
        # back to the previous explicit switch, with the same exact supervisor.
        actual_service, pid = worker.service_for_vision()
        if actual_service != service:
            raise RuntimeError('Vision service identity changed during format recovery')
        subprocess.check_call(['sv', 'down', service], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        worker.wait_vision_exit(pid)
        subprocess.check_call([BINARY, '--restore-mode', '/dev/video0', DIRECTORY],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result = original_restore(service, original)
        result['v4l2_mode'] = verify_mode()
        result['format_restore_strategy'] = 'explicit_fallback'
        result['format_restore_fallback_reason'] = str(error)
    result['timing_seconds'] = {'settings_and_normal': restored - started,
                                'mode_verification_and_fallback': time.time() - restored}
    return result


worker.restore = restore


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('One unique absolute output directory required')
        DIRECTORY = sys.argv[1]
        if not DIRECTORY.startswith('/tmp/uwa_hd_') or '/' in DIRECTORY[len('/tmp/uwa_hd_'):]:
            raise ValueError('Unexpected capture directory')
        started = time.time()
        result = worker.capture(DIRECTORY)
        result['transaction_seconds'] = time.time() - started
        worker.save(DIRECTORY + '/report.json', result)
        print(json.dumps(result))
        sys.exit(0 if result['success'] else 1)
    except Exception as error:
        print(json.dumps({'success': False, 'restore_ok': False, 'error': str(error)}))
        sys.exit(1)

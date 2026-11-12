"""Legacy native format recovery with the shared activity LED restore. MIT."""
from __future__ import print_function
import json
import sys
import wrist_worker as worker
import wrist_led_restore

original_restore = worker.restore


def restore(service, original):
    return wrist_led_restore.restore(original_restore, worker, service, original)


worker.restore = restore

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('One unique absolute output directory required')
        directory = sys.argv[1]
        if not directory.startswith('/tmp/uwa_hd_') or '/' in directory[len('/tmp/uwa_hd_'):]:
            raise ValueError('Unexpected capture directory')
        result = worker.capture(directory)
        print(json.dumps(result))
        sys.exit(0 if result['success'] else 1)
    except Exception as error:
        print(json.dumps({'success': False, 'restore_ok': False, 'error': str(error)}))
        sys.exit(1)

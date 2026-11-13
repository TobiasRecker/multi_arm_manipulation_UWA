"""Python 2.7/3: change only LED fields under the native camera lock. MIT."""
from __future__ import print_function
import fcntl
import json
import sys
import time
try:
    from urllib.request import Request, build_opener, ProxyHandler
except ImportError:
    from urllib2 import Request, build_opener, ProxyHandler


def apply(desired):
    opener = build_opener(ProxyHandler({}))
    def request(path, change=None):
        body = None if change is None else json.dumps({'cameraSettings': change}).encode('utf-8')
        response = opener.open(Request('http://127.0.0.1:4242' + path, data=body,
            headers={'Content-Type': 'application/json'}), timeout=3)
        return json.loads(response.read().decode('utf-8'))
    def settings():
        result = request('/getcamerasettings?forceRefresh=true')
        if result.get('status') != 'succeeded':
            raise RuntimeError('LED operation: camera settings unavailable')
        return result['cameraSettings']
    with open('/tmp/uwa_wrist_hd_capture.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if request('/status').get('current state') != 'Normal':
            raise RuntimeError('LED operation: camera is not Normal')
        before = settings()
        if desired is None:
            return {'before': before, 'settings': before, 'verified': True}
        if set(desired) != set(('lightingMode', 'lightingValue')):
            raise ValueError('Only LED mode and intensity may be changed')
        if (type(desired['lightingMode']) is not int or desired['lightingMode'] not in (0, 1, 2)
                or type(desired['lightingValue']) is not int or not 0 <= desired['lightingValue'] <= 175):
            raise ValueError('Invalid LED profile')
        version = request('/hello').get('version', '')
        known_readback = version.startswith(('UCC-4.1.0.', 'UCC-1.11.1.', 'UCC-3.44.0.'))
        # Off is API setter mode 1 on all tested releases. Force-refresh reports
        # the hardware switch (0=off, 1=enabled), not the API setter enum.
        off = desired['lightingMode'] == 1 and desired['lightingValue'] == 0
        expected_mode = 0 if off and known_readback else desired['lightingMode']
        # A setter error alone is inconclusive on UCC4.1; actual readback decides.
        response = request('/setcamerasettings?setManualValuesIfModeChanged=' +
                           ('false' if off else 'true'), desired)
        automatic = set()
        if before.get('focusAuto'):
            automatic.add('focus')
        if before.get('exposureAuto'):
            automatic.update(('exposure', 'gain'))
        for attempt in range(12):
            actual = settings()
            unrelated = [k for k in before if k not in automatic and k not in desired
                         and actual.get(k) != before[k]]
            mode = actual.get('lightingMode')
            level = actual.get('lightingValue')
            matches = mode == expected_mode and level == desired['lightingValue']
            # Mode 2 enables manual light; require acknowledgement when the
            # firmware returns the hardware boolean instead of the mode enum.
            if known_readback and desired['lightingMode'] == 2 and mode == 1:
                matches = response.get('status') == 'succeeded' and level == desired['lightingValue']
            # Force-refresh can momentarily return mixed focus-window values.
            # Require the original settings to settle; don't waive the check.
            if matches and not unrelated:
                return {'before': before, 'settings': actual, 'verified': True}
            time.sleep(.1)
        if unrelated:
            raise RuntimeError('LED operation changed other camera fields: ' + str(unrelated))
        raise RuntimeError('LED readback mismatch: ' + str(actual))


if __name__ == '__main__':
    try:
        print(json.dumps(apply(json.load(sys.stdin))))
    except Exception as error:
        print(json.dumps({'verified': False, 'error': str(error)}))
        sys.exit(1)

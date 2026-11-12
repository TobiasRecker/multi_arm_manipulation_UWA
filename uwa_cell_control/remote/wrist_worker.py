"""Python 2.7/3 camera-only transaction, installed temporarily via explicit SSH.

Never controls UR programs, motors, ROS drivers or robot safety. MIT.
"""
from __future__ import print_function
import errno
import fcntl
import glob
import json
import os
import select
import signal
import subprocess
import sys
import time
try:
    from urllib.request import Request, build_opener, ProxyHandler
except ImportError:
    from urllib2 import Request, build_opener, ProxyHandler

BASE = 'http://127.0.0.1:4242'
OPENER = build_opener(ProxyHandler({}))


def request(path, data=None):
    body = None if data is None else json.dumps(data).encode('utf-8')
    req = Request(BASE + path, data=body, headers={'Content-Type': 'application/json'})
    return json.loads(OPENER.open(req, timeout=3).read().decode('utf-8'))


def save(path, data):
    with open(path, 'w') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')


def normal(timeout=25):
    end = time.time() + timeout
    while time.time() < end:
        try:
            result = request('/status')
            if result.get('status') == 'succeeded' and result.get('current state') == 'Normal':
                return
        except Exception:
            pass
        time.sleep(.25)
    raise RuntimeError('Camera did not enter Normal; no further capture allowed')


def settings():
    result = request('/getcamerasettings?forceRefresh=true')
    if result.get('status') != 'succeeded' or not isinstance(result.get('cameraSettings'), dict):
        raise RuntimeError('Actual camera settings unavailable')
    return result['cameraSettings']


def service_for_vision():
    """Identify only the actual port4242 camera process and its runit supervisor."""
    found = []
    for proc in glob.glob('/proc/[0-9]*'):
        try:
            args = open(proc + '/cmdline', 'rb').read().decode('utf-8').split('\0')
            if os.path.basename(args[0]) != 'visionserver' or '--portnum' not in args:
                continue
            if args[args.index('--portnum') + 1] != '4242':
                continue
            # /proc/stat comm can contain spaces, so split after the last ')'.
            parent = int(open(proc + '/stat').read().rsplit(')', 1)[1].split()[1])
            wrapper = '/proc/' + str(parent)
            wrapper_args = open(wrapper + '/cmdline', 'rb').read().decode('utf-8').split('\0')
            scripts = [a for a in wrapper_args if a.endswith('/vision_server.sh')]
            if len(scripts) != 1:
                continue
            supervisor = int(open(wrapper + '/stat').read().rsplit(')', 1)[1].split()[1])
            sup = '/proc/' + str(supervisor)
            sa = open(sup + '/cmdline', 'rb').read().decode('utf-8').split('\0')
            if os.path.basename(sa[0]) != 'runsv' or not sa[1]:
                continue
            # runsv chdirs into its service before spawning the wrapper.
            service = os.path.realpath(os.readlink(sup + '/cwd'))
            run = open(service + '/run').read()
            if scripts[0] not in run:
                continue
            found.append((service, int(proc.split('/')[-1])))
        except (IOError, OSError, ValueError, IndexError):
            continue
    if len(found) != 1:
        raise RuntimeError('Cannot uniquely identify existing camera-only runit service: ' + str(found))
    return found[0]


def restore(service, original):
    subprocess.check_call(['sv', 'up', service], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    normal()
    responses = []
    # Auto-LED setter on UCC4.1 can report error15 after applying its value.
    # Return actual full readback rather than accepting/rejecting on status alone.
    changes = [original,
               {k: original[k] for k in ('focus', 'focusAuto')},
               {k: original[k] for k in ('exposure', 'exposureAuto', 'gain')},
               {'lightingMode': original['lightingMode']},
               {'lightingValue': original['lightingValue']}]
    for change in changes:
        responses.append(request('/setcamerasettings?setManualValuesIfModeChanged=true', {'cameraSettings': change}))
    # Older UCC versions acknowledge setters before the device/readback settles.
    # Auto-controlled outputs are not fixed settings; their modes and all other
    # fields must still match. In manual mode focus/exposure/gain remain exact.
    automatic = set()
    if original.get('focusAuto'):
        automatic.add('focus')
    if original.get('exposureAuto'):
        automatic.update(('exposure', 'gain'))
    legacy_led_mapping = None
    for attempt in range(21):
        actual = settings()
        differences = {k: [v, actual.get(k)] for k, v in original.items()
                       if k not in automatic and actual.get(k) != v}
        if attempt == 0 and 'lightingMode' in differences and original['lightingMode'] in (0, 1):
            version = request('/hello').get('version', '')
            # Measured on these exact legacy branches: setter0 reads back1,
            # setter1 reads back0. Never assume this for untested firmware.
            if version.startswith(('UCC-1.11.1.', 'UCC-3.44.0.')):
                legacy_led_mapping = 1 - original['lightingMode']
                responses.append(request('/setcamerasettings?setManualValuesIfModeChanged=true',
                                         {'cameraSettings': {'lightingMode': legacy_led_mapping}}))
        if not differences:
            return {'settings': actual, 'setter_responses': responses,
                    'all_original_fields_match': actual == original,
                    'all_configuration_fields_match': True,
                    'legacy_led_write_value': legacy_led_mapping,
                    'automatic_output_fields': sorted(automatic)}
        if attempt < 20:
            time.sleep(.25)
    raise RuntimeError('Camera restoration readback mismatch: ' + str(differences))


def capture(directory):
    os.umask(0o077)
    os.mkdir(directory)
    lock = open('/tmp/uwa_wrist_hd_capture.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        raise RuntimeError('Another native camera transaction is active')
    normal(timeout=4)
    original = settings()
    hello = request('/hello')
    if hello.get('version', '').startswith('UCC-1.11.1.') and original.get('focusAuto'):
        # Real right-rear tests found accumulating ROI shifts after each native
        # mode/server restart. Do not repeat a known non-restorable transaction.
        report = {'schema_version': 1, 'success': False, 'restore_ok': True,
                  'state_changed': False, 'motion_commands': False,
                  'camera': hello, 'original_settings': original,
                  'error': 'UCC1.11.1 autofocus ROI restoration is not supported; '
                           'no camera mode/service changes made. Use a verified '
                           'manual-focus profile or update and retest the URCap.'}
        save(directory + '/original-settings.json', original)
        save(directory + '/report.json', report)
        return report
    service, vision_pid = service_for_vision()
    save(directory + '/original-settings.json', original)
    report = {'schema_version': 1, 'success': False, 'restore_ok': False,
              'camera': hello, 'original_settings': original, 'service': service,
              'vision_pid_before': vision_pid, 'transport': 'native_v4l2_mjpeg',
              'requested_size': [2592, 1944], 'sensor_exposure_timestamp_available': False,
              'color_pipeline': 'native MJPEG; visible green cast may remain',
              'motion_commands': False}
    done = directory + '/restored'
    read_pipe, write_pipe = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(write_pipe)
        os.setsid()
        # Restore on parent death (EOF) or capture deadline; normal completion
        # writes a byte and lets this watchdog exit immediately.
        ready = select.select([read_pipe], [], [], 60)[0]
        completed = os.read(read_pipe, 1) if ready else b''
        if not completed and not os.path.exists(done):
            try:
                # Only the native helper belonging to THIS request may be
                # terminated before releasing the camera back to its service.
                pidfile = directory + '/capture.pid'
                if os.path.exists(pidfile):
                    capture_pid = int(open(pidfile).read())
                    try:
                        args = open('/proc/%d/cmdline' % capture_pid, 'rb').read().decode('utf-8').split('\0')
                        if os.path.basename(args[0]) == 'wrist_capture' and args[1:3] == ['/dev/video0', directory]:
                            os.kill(capture_pid, signal.SIGTERM)
                            time.sleep(.5)
                    except (IOError, OSError):
                        pass
                result = restore(service, original)
                save(directory + '/watchdog-restoration.json', result)
            except Exception as error:
                save(directory + '/watchdog-error.json', {'error': str(error)})
        os._exit(0)
    os.close(read_pipe)
    started = False
    try:
        started = True  # sv down may succeed even if its caller is interrupted.
        subprocess.check_call(['sv', 'down', service], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        binary = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wrist_capture')
        for attempt in range(20):
            log_path = directory + '/capture.log'
            with open(log_path, 'w') as log:
                process = subprocess.Popen([binary, '/dev/video0', directory], stdout=log, stderr=subprocess.STDOUT)
                open(directory + '/capture.pid', 'w').write(str(process.pid))
                code = process.wait()
            report['capture_attempts'] = attempt + 1
            report['capture_returncode'] = code
            if code == 0:
                break
            if 'S_FMT: Device or resource busy' not in open(log_path).read():
                break
            time.sleep(.25)
        files = ['frame_%03d.jpg' % i for i in range(3)]
        if code or not all(os.path.getsize(directory + '/' + f) > 0 for f in files):
            raise RuntimeError('Native burst failed; see capture.log')
        report['frames'] = files
        report['capture_log'] = open(log_path).read()
        report['success'] = True
    except BaseException as error:
        report['error'] = str(error) or type(error).__name__
    finally:
        if started:
            try:
                report['restoration'] = restore(service, original)
                report['restore_ok'] = True
                open(done, 'w').write('Actual settings match original')
                os.write(write_pipe, b'1')
            except Exception as error:
                report['restore_error'] = str(error)
        os.close(write_pipe)
        # If restoration failed, the watchdog receives EOF and retries it.
        os.waitpid(child, 0)
        if not report['restore_ok'] and os.path.exists(directory + '/watchdog-restoration.json'):
            report['restoration'] = json.load(open(directory + '/watchdog-restoration.json'))
            report['restore_ok'] = True
        report['success'] = report['success'] and report['restore_ok']
        save(directory + '/report.json', report)
    return report


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('One unique absolute output directory required')
        directory = sys.argv[1]
        if not directory.startswith('/tmp/uwa_hd_') or '/' in directory[len('/tmp/uwa_hd_'):]:
            raise ValueError('Unexpected capture directory')
        result = capture(directory)
        print(json.dumps(result))
        sys.exit(0 if result['success'] else 1)
    except Exception as error:
        print(json.dumps({'success': False, 'restore_ok': False, 'error': str(error)}))
        sys.exit(1)

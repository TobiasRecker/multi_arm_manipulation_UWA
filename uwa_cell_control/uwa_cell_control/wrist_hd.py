"""Authenticated native Wrist-camera bursts; passwords never enter this API."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
import uuid

import cv2
import numpy as np

from .wrist_camera import WristCamera


HD_SIZE = (2592, 1944)
SOURCE = {'kind': 'wrist_hd_service', 'width': 2592, 'height': 1944,
          'encoding': 'native_mjpeg', 'color_pipeline': 'native_unprocessed'}


def control_path(arm, ip):
    root = Path('/tmp') / f'uwa-wrist-hd-{os.getuid()}'
    root.mkdir(mode=0o700, exist_ok=True)
    if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError('SSH socket directory must be private and owned by this user')
    return root / f'{arm}-{ip.replace(".", "_")}.sock'


class SSH:
    def __init__(self, ip, path):
        self.ip, self.path = ip, Path(path)

    def identity_options(self):
        legacy = Path.home() / ('.ssh/uwa_wrist_camera_' + self.ip.replace('.', '_') + '_rsa')
        if legacy.is_file():
            # Old CB3 OpenSSH6.0 predates Ed25519/RSA-SHA2. Scope compatibility
            # to the explicitly provisioned controller, never all SSH hosts.
            return ['-i', str(legacy), '-o', 'IdentitiesOnly=yes',
                    '-o', 'PubkeyAcceptedAlgorithms=+ssh-rsa']
        key = Path.home() / '.ssh/uwa_wrist_camera_ed25519'
        return ['-i', str(key), '-o', 'IdentitiesOnly=yes'] if key.is_file() else []

    def known_hosts(self):
        durable = Path.home() / '.ssh/uwa_wrist_known_hosts'
        return durable if durable.is_file() else self.path.parent / 'known_hosts'

    def base(self):
        return ['ssh', *self.identity_options(), '-S', str(self.path),
                '-o', 'ControlMaster=auto', '-o', 'ControlPersist=3600',
                '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(self.known_hosts()), 'root@' + self.ip]

    def connect(self):
        # Interactive SSH handles authentication itself. No password argument,
        # environment variable, saved password, or custom authentication script.
        subprocess.run(['ssh', *self.identity_options(), '-M', '-S', str(self.path), '-o', 'ControlPersist=3600',
                        '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=accept-new',
                        '-o', 'UserKnownHostsFile=' + str(self.known_hosts()),
                        '-fNT', 'root@' + self.ip], check=True)

    def run(self, command, *, data=None, timeout=100):
        result = subprocess.run(self.base() + [command], input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout)
        if result.returncode:
            # A failed transaction can still have a useful JSON report.
            raise RuntimeError((result.stdout + result.stderr).decode(errors='replace')[-6000:])
        return result.stdout

    def fetch(self, remote, local):
        subprocess.run(['scp', *self.identity_options(), '-O', '-r', '-o', 'ControlPath=' + str(self.path),
                        '-o', 'ControlMaster=auto', '-o', 'ControlPersist=3600',
                        '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                        '-o', 'UserKnownHostsFile=' + str(self.known_hosts()), 'root@' + self.ip + ':' + remote, str(local)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)


def validate_burst(directory, expected_ip):
    """Reject scaled/faulty/stale data or any unconfirmed restoration."""
    directory = Path(directory)
    report = json.loads((directory / 'report.json').read_text())
    if not report.get('success') or not report.get('restore_ok'):
        raise ValueError('Native capture or camera restoration was not confirmed')
    if report.get('transport') != 'native_v4l2_mjpeg' or report.get('requested_size') != list(HD_SIZE):
        raise ValueError('Unexpected native capture mode')
    files = report.get('frames', [])
    if files != ['frame_000.jpg', 'frame_001.jpg', 'frame_002.jpg']:
        raise ValueError('Expected three native frames')
    metrics = []
    for name in files:
        path = directory / name
        jpeg = path.read_bytes()
        frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if frame is None or frame.shape[:2] != HD_SIZE[::-1]:
            raise ValueError('Native JPEG is not2592×1944')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        metrics.append({'image': name, 'sha256': hashlib.sha256(jpeg).hexdigest(),
                        'pixel_sha256': hashlib.sha256(frame.tobytes()).hexdigest(),
                        'sharpness_laplacian_variance': float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                        'fraction_gray_ge_250': float(np.mean(gray >= 250)),
                        'fraction_gray_le_5': float(np.mean(gray <= 5))})
    if len({m['pixel_sha256'] for m in metrics}) < 2:
        raise ValueError('Native frame payloads did not change')
    report.update(ip=expected_ip, image_size=list(HD_SIZE), frames_metadata=metrics,
                  sensor_controls=[json.loads(line[len('CONTROLS '):]) for line in
                                   report.get('capture_log','').splitlines() if line.startswith('CONTROLS ')],
                  received_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  timestamp_kind='PC receipt after transaction; no exposure synchronization',
                  capture_source=SOURCE, directory=str(directory.resolve()))
    (directory / 'validated.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


class NativeCapture:
    def __init__(self, ip, ssh, output, resources=None, *, fast=True):
        self.ip, self.ssh, self.output = ip, ssh, Path(output)
        self.fast = fast
        self.worker_entrypoint = 'wrist_worker.py'
        if resources is None:
            from ament_index_python.packages import get_package_share_directory
            resources = Path(get_package_share_directory('uwa_cell_control')) / 'remote'
        self.resources = Path(resources)
        self.remote = None

    def bootstrap(self):
        if self.fast:
            sources = {'wrist_worker_fast.py': (self.resources / 'wrist_worker_fast.py').read_bytes(),
                       'wrist_worker.py': (self.resources / 'wrist_worker.py').read_bytes(),
                       'wrist_capture.c': (self.resources / 'wrist_capture_fast.c').read_bytes()}
        else:
            sources = {n: (self.resources / n).read_bytes() for n in ('wrist_worker.py', 'wrist_capture.c')}
        for name in ('wrist_led_restore.py', 'wrist_worker_managed.py'):
            if (self.resources / name).exists():
                sources[name] = (self.resources / name).read_bytes()
        tag = hashlib.sha256(b''.join(sources.values())).hexdigest()[:16]
        remote = '/tmp/uwa_hd_tools_' + tag
        if self.remote == remote:
            return
        self.ssh.run('umask 077; mkdir -p ' + shlex.quote(remote))
        for name, data in sources.items():
            self.ssh.run('umask 077; cat > ' + shlex.quote(remote + '/' + name), data=data)
        self.ssh.run('gcc -std=gnu99 -Wall -Wextra -O2 ' + shlex.quote(remote + '/wrist_capture.c') +
                     ' -o ' + shlex.quote(remote + '/wrist_capture'), timeout=30)
        self.remote = remote
        self.worker_entrypoint = ('wrist_worker_fast.py' if self.fast else
            'wrist_worker_managed.py' if 'wrist_worker_managed.py' in sources else 'wrist_worker.py')

    def capture(self):
        with WristCamera(self.ip).activity() as use:
            self.managed_led = use.lease is not None
            return self._capture()

    def _capture(self):
        self.bootstrap()
        token = uuid.uuid4().hex
        remote = '/tmp/uwa_hd_' + token
        destination = self.output / token
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Camera-only transaction has its own remote lock/watchdog/finally.
        command = 'python ' + shlex.quote(self.remote + '/' + self.worker_entrypoint) + ' ' + shlex.quote(remote)
        if self.managed_led:
            if self.worker_entrypoint == 'wrist_worker.py':
                raise RuntimeError('Frozen camera resources do not support managed LEDs; update only after the active series')
            command = 'UWA_WRIST_MANAGED_LED=1 ' + command
        try:
            self.ssh.run(command, timeout=100)
        finally:
            # Preserve diagnostics even after a failed transaction when possible.
            self.ssh.fetch(remote, destination)
        result = validate_burst(destination, self.ip)
        # Remove only this successful, locally verified request; never wildcard.
        self.ssh.run('rm -rf -- ' + shlex.quote(remote), timeout=5)
        return result

    def restore_configuration(self, original):
        """Camera-only, fully verified restore, also after a temporary focus lock."""
        camera = WristCamera(self.ip)
        with camera.activity() as use:
            desired = dict(original)
            if use.lease is not None:
                actual = camera.settings(refresh=True)
                desired.update({k: actual[k] for k in ('lightingMode', 'lightingValue')})
            return self._restore_configuration(desired, use.lease is not None)

    def _restore_configuration(self, original, managed_led):
        self.bootstrap()
        module = 'wrist_worker_managed as m;w=m.worker' if (self.resources / 'wrist_worker_managed.py').exists() else 'wrist_worker as w'
        script = ('import sys,json;sys.path.insert(0,' + repr(self.remote) + ');'
                  'import ' + module + ';original=json.load(sys.stdin);'
                  'service,_=w.service_for_vision();print(json.dumps(w.restore(service,original)))')
        command = ('UWA_WRIST_MANAGED_LED=1 ' if managed_led else '') + 'python -c ' + shlex.quote(script)
        return json.loads(self.ssh.run(command,
                                      data=json.dumps(original).encode(), timeout=40))


class LeftFrontNativeCapture(NativeCapture):
    def __init__(self, ip, ssh, output):
        if ip != '192.168.8.2':
            raise ValueError('The 32-bit helper is scoped to the left-front CB3')
        super().__init__(ip, ssh or SSH(ip, control_path('left_front_hd', ip)), output)

    def bootstrap(self):
        sources = {'wrist_worker.py': (self.resources / 'wrist_worker.py').read_bytes(),
                   'wrist_capture': (self.resources / ('wrist_capture_i686_fast.py' if self.fast else 'wrist_capture_i686.py')).read_bytes()}
        if self.fast:
            sources['wrist_worker_fast.py'] = (self.resources / 'wrist_worker_fast.py').read_bytes()
        for name in ('wrist_led_restore.py', 'wrist_worker_managed.py'):
            sources[name] = (self.resources / name).read_bytes()
        tag = hashlib.sha256(b'\0'.join(sources.values())).hexdigest()[:16]
        remote = '/tmp/uwa_hd_tools_' + tag
        if self.remote == remote:
            return
        self.ssh.run('umask 077; mkdir -p ' + shlex.quote(remote))
        for name, data in sources.items():
            path = shlex.quote(remote + '/' + name)
            self.ssh.run('umask 077; cat > ' + path, data=data)
        self.ssh.run('chmod 700 ' + shlex.quote(remote + '/wrist_capture'))
        self.remote = remote
        self.worker_entrypoint = 'wrist_worker_fast.py' if self.fast else 'wrist_worker_managed.py'


class HDCamera(WristCamera):
    """ROS service client that keeps calibration joint monitoring spinning."""
    capture_source = SOURCE

    def __init__(self, ip, node, service, *, timeout=100):
        super().__init__(ip)
        from std_srvs.srv import Trigger
        self.node, self.timeout = node, timeout
        self.client = node.create_client(Trigger, service)
        self.last_burst = None

    def capture_burst(self, monitor):
        import rclpy
        from std_srvs.srv import Trigger
        if not self.client.wait_for_service(timeout_sec=3):
            raise ValueError('HD capture service unavailable')
        future = self.client.call_async(Trigger.Request())
        end = time.monotonic() + self.timeout
        violation = None
        while not future.done():
            rclpy.spin_once(self.node, timeout_sec=.03)
            try:
                monitor()
            except Exception as error:
                violation = violation or error
            if time.monotonic() > end:
                raise ValueError('HD transaction timed out; confirm remote recovery before continuing')
        response = future.result()
        if not response.success:
            raise ValueError('HD service failed: ' + response.message)
        # Wait for the service's finally/restore even after detected robot motion.
        if violation:
            raise violation
        report = json.loads(response.message)
        if report.get('ip') != self.base.split('//')[1].split(':')[0]:
            raise ValueError('HD service camera identity differs from selected robot')
        directory = Path(report['directory'])
        actual = validate_burst(directory, report['ip'])
        self.last_burst = actual
        return [(directory / item['image']).read_bytes() for item in actual['frames_metadata']]


def make_camera(ip, node, args=None, metadata=None, rid=None):
    source = (metadata or {}).get('capture_source')
    requested = getattr(args, 'camera_source', None)
    kind = requested or (source or {}).get('kind', 'http_vga')
    if source and requested and requested != source['kind']:
        raise ValueError('Cannot change image source inside an existing calibration session')
    if kind == 'wrist_hd_service':
        service = getattr(args, 'hd_service', None) or f'/uwa_hardware/{rid}/wrist_camera_hd/capture'
        camera = HDCamera(ip, node, service)
        camera.require_native_controls = bool(getattr(args,'require_native_controls',False) or
                                              (metadata or {}).get('native_control_readback_required',False))
        return camera
    if kind != 'http_vga':
        raise ValueError('Unknown image source')
    return WristCamera(ip)

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

    def base(self):
        return ['ssh', '-S', str(self.path), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(self.path.parent / 'known_hosts'), 'root@' + self.ip]

    def connect(self):
        # Interactive SSH handles authentication itself. No password argument,
        # environment variable, saved password, or custom authentication script.
        subprocess.run(['ssh', '-M', '-S', str(self.path), '-o', 'ControlPersist=3600',
                        '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=accept-new',
                        '-o', 'UserKnownHostsFile=' + str(self.path.parent / 'known_hosts'),
                        '-fNT', 'root@' + self.ip], check=True)

    def run(self, command, *, data=None, timeout=100):
        result = subprocess.run(self.base() + [command], input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout)
        if result.returncode:
            # A failed transaction can still have a useful JSON report.
            raise RuntimeError((result.stdout + result.stderr).decode(errors='replace')[-6000:])
        return result.stdout

    def fetch(self, remote, local):
        subprocess.run(['scp', '-O', '-r', '-o', 'ControlPath=' + str(self.path),
                        '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                        '-o', 'UserKnownHostsFile=' + str(self.path.parent / 'known_hosts'), 'root@' + self.ip + ':' + remote, str(local)], check=True,
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
                  received_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  timestamp_kind='PC receipt after transaction; no exposure synchronization',
                  capture_source=SOURCE, directory=str(directory.resolve()))
    (directory / 'validated.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


class NativeCapture:
    def __init__(self, ip, ssh, output, resources=None):
        self.ip, self.ssh, self.output = ip, ssh, Path(output)
        if resources is None:
            from ament_index_python.packages import get_package_share_directory
            resources = Path(get_package_share_directory('uwa_cell_control')) / 'remote'
        self.resources = Path(resources)
        self.remote = None

    def bootstrap(self):
        sources = {n: (self.resources / n).read_bytes() for n in ('wrist_worker.py', 'wrist_capture.c')}
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

    def capture(self):
        self.bootstrap()
        token = uuid.uuid4().hex
        remote = '/tmp/uwa_hd_' + token
        destination = self.output / token
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Camera-only transaction has its own remote lock/watchdog/finally.
        command = 'python ' + shlex.quote(self.remote + '/wrist_worker.py') + ' ' + shlex.quote(remote)
        try:
            self.ssh.run(command, timeout=100)
        finally:
            # Preserve diagnostics even after a failed transaction when possible.
            self.ssh.fetch(remote, destination)
        result = validate_burst(destination, self.ip)
        # Remove only this successful, locally verified request; never wildcard.
        self.ssh.run('rm -rf -- ' + shlex.quote(remote), timeout=5)
        return result


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
        return HDCamera(ip, node, service)
    if kind != 'http_vga':
        raise ValueError('Unknown image source')
    return WristCamera(ip)

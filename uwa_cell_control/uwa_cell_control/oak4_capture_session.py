"""Local control channel for the native OAK4 photo and preview session."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import uuid

from .board_capture import OakPreview


class Oak4CaptureSession(OakPreview):
    def __init__(self, workspace, camera, output, focus):
        super().__init__(workspace, camera, output, focus)
        self.socket_dir = self.listener = self.connection = self.reader = None

    def start(self):
        with self.lock:
            if self.child is not None and self.child.poll() is None:
                return
            self.stop()
            self.output.mkdir(parents=True, exist_ok=True)
            (self.output / 'frame.bin').unlink(missing_ok=True)
            try:
                self.socket_dir = tempfile.TemporaryDirectory(prefix='uwa-oak4-')
                address = str(Path(self.socket_dir.name) / 'control')
                self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.listener.bind(address)
                self.listener.listen(1)
                self.listener.settimeout(.2)
                self.log = (self.output / 'preview.log').open('a')
                self.child = subprocess.Popen([
                    str(self.ws / 'setup/oak4/bin/oakctl'), 'run-script',
                    str(self.ws / '.venvs/oak4/bin/python'), '-u',
                    str(self.ws / 'src/oak_camera_calibration/tools/oak4_session_capture.py'),
                    '--ip', self.camera['ip'], '--device-id', str(self.camera['device_id']),
                    '--output', str(self.output), '--socket', address, '--focus', str(self.focus),
                    '--lock', str(self.ws / 'setup/oak4/photos/.capture.lock')],
                    env={k: v for k, v in dict(os.environ, DEPTHAI_TELEMETRY='0',
                         OAKCTL_ANALYTICS='0').items() if k != 'PYTHONPATH'},
                    stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
            except BaseException:
                self.stop()
                raise

    def stop(self):
        with self.lock:
            if self.connection:
                try:
                    self.connection.shutdown(socket.SHUT_WR)
                except OSError:
                    pass  # Worker may already have closed its socket.
            for channel in (self.reader, self.connection, self.listener):
                if channel:
                    channel.close()
            self.reader = self.connection = self.listener = None
            super().stop()
            self.child = None
            if self.socket_dir:
                self.socket_dir.cleanup()
                self.socket_dir = None

    def read(self):
        jpeg, metadata = super().read()
        if time.time() - metadata['received'] > 4:
            raise RuntimeError('Waiting for a fresh OAK4 preview')
        return jpeg, metadata

    def capture(self, directory, *, on_acquired=None):
        with self.lock:
            self.start()
            deadline = time.monotonic() + 30
            while self.connection is None:
                if self.child.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError(f'OAK4 camera worker unavailable; see {self.output / "preview.log"}')
                try:
                    self.connection, _ = self.listener.accept()
                except TimeoutError:
                    continue
                self.connection.settimeout(45)
                self.reader = self.connection.makefile('rb')
            request = dict(id=uuid.uuid4().hex, directory=str(Path(directory).resolve()))
            try:
                self.connection.sendall(json.dumps(request).encode() + b'\n')
                acquired = False
                while True:
                    line = self.reader.readline()
                    if not line:
                        raise EOFError(f'OAK4 worker disconnected; see {self.output / "preview.log"}')
                    reply = json.loads(line)
                    if reply['id'] != request['id']:
                        raise ValueError('OAK4 response does not match this trigger')
                    if reply['event'] == 'error':
                        raise RuntimeError(reply['error'])
                    if reply['event'] == 'acquired' and not acquired:
                        acquired = True
                        if on_acquired:
                            on_acquired()
                    elif reply['event'] == 'saved' and acquired:
                        return Path(directory) / 'image.png', reply['metadata']
                    else:
                        raise ValueError('Unexpected OAK4 acquisition response')
            except (OSError, EOFError, ValueError):
                self.stop()
                raise

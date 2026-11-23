"""Persistent native Robotiq camera session for the shared calibration capture GUI."""
import io
import json
import os
from pathlib import Path
import select
import shlex
import subprocess
import tarfile
import threading
import time
import uuid

from .wrist_camera import WristCamera
from .wrist_hd import HD_SIZE, SSH, control_path


class ReplyReader:
    def __init__(self, pipe):
        self.fd = pipe.fileno()
        self.buffer = bytearray()

    def _receive(self, deadline):
        if not select.select([self.fd], [], [], max(0., deadline-time.monotonic()))[0]:
            raise TimeoutError('Timed out waiting for the native wrist camera')
        data = os.read(self.fd, 131072)
        if not data:
            raise EOFError('Native wrist camera connection closed')
        self.buffer.extend(data)

    def reply(self, timeout, on_acquired=None):
        deadline = time.monotonic() + timeout
        while b'\n' not in self.buffer:
            if len(self.buffer) > 65536:
                raise ValueError('Oversized native wrist frame header')
            self._receive(deadline)
        end = self.buffer.index(b'\n')
        if end > 65536:
            raise ValueError('Oversized native wrist frame header')
        header = json.loads(bytes(self.buffer[:end]))
        del self.buffer[:end+1]
        size = header['bytes']
        if type(size) is not int or not 0 <= size <= 32*1024*1024:
            raise ValueError('Invalid native wrist frame payload length')
        if header.get('event') == 'frame' and size and on_acquired is not None:
            on_acquired()
        while len(self.buffer) < size:
            self._receive(deadline)
        data = bytes(self.buffer[:size])
        del self.buffer[:size]
        return header, data


class WristStream:
    """One camera owner. No UR program, robot motion or driver interfaces."""
    files = ('wrist_stream_worker.py', 'wrist_stream_v4l2.py', 'wrist_capture_i686_fast.py',
             'wrist_worker.py', 'wrist_led_restore.py')

    def __init__(self, name, ip, session_dir, expected_focus):
        self.name, self.ip, self.focus = name, ip, int(expected_focus)
        self.session_dir = Path(session_dir)
        self.ssh = SSH(ip, control_path('stream_'+name, ip))
        self.lock = threading.Lock()
        self.finished = threading.Event()
        self.process = self.activity = self.heartbeat = None
        self.error = None

    def _install(self):
        from ament_index_python.packages import get_package_share_directory
        files = Path(get_package_share_directory('uwa_cell_control'))/'remote'
        archive = io.BytesIO()
        # Colcon symlink installs point back to ROSmini's build tree.
        with tarfile.open(fileobj=archive, mode='w:gz', dereference=True) as tar:
            for name in self.files:
                tar.add(files/name, arcname=name, recursive=False)
        self.ssh.run('umask 077; mkdir ' + self.remote + ' && tar -xzf - -C ' + self.remote,
                     data=archive.getvalue(), timeout=15)

    def start(self):
        with self.lock:
            if self.process is not None:
                if self.error:
                    raise RuntimeError(self.error)
                return
            self.finished = threading.Event()
            self.error = None
            self.previous_sequence = None
            token = uuid.uuid4().hex
            self.remote = '/tmp/uwa_wrist_stream_' + token
            self.directory = self.session_dir / self.name / token
            self.directory.mkdir(parents=True)
            self._install()
            activity = WristCamera(self.ip).activity()
            activity.__enter__()
            self.activity = activity
            try:
                command = ['python', '-u', self.remote+'/wrist_stream_worker.py', str(self.focus)]
                if activity.lease is not None:
                    command.insert(0, 'UWA_WRIST_MANAGED_LED=1')
                with (self.directory/'session.log').open('ab') as log:
                    self.process = subprocess.Popen(self.ssh.base()+[shlex.join(command)],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, bufsize=0)
                self.reader = ReplyReader(self.process.stdout)
                ready, _ = self.reader.reply(50)
                if ready.get('event') != 'ready':
                    self._record_close(ready)
                    raise RuntimeError(ready.get('error') or ready.get('session_error') or 'Wrist stream failed to start')
                self.ready = ready
                (self.directory/'ready.json').write_text(json.dumps(ready, indent=2)+'\n')
                self.heartbeat = threading.Thread(target=self._maintain, args=(self.finished,), daemon=True)
                self.heartbeat.start()
            except BaseException:
                self._disconnect()
                raise

    def _maintain(self, ended):
        while not ended.wait(4.):
            if not self.lock.acquire(blocking=False):
                continue
            try:
                if ended.is_set() or self.process is None:
                    return
                self._exchange(b'P', 'pong', timeout=5.)
            except Exception as error:
                self.error = str(error)
                self.process.stdin.close()  # Ends the camera lease at the controller.
                return
            finally:
                self.lock.release()

    def _record_close(self, header):
        if header.get('event') == 'closed':
            (self.directory/'restoration.json').write_text(json.dumps(header, indent=2)+'\n')

    def _exchange(self, command, event, *, timeout, on_acquired=None):
        self.process.stdin.write(command)
        header, data = self.reader.reply(timeout, on_acquired)
        if header.get('event') != event:
            self._record_close(header)
            raise RuntimeError(header.get('error') or header.get('session_error') or 'Unexpected wrist camera reply')
        return header, data

    def _frame(self, command, callback=None):
        with self.lock:
            if self.error or self.process is None or self.finished.is_set():
                raise RuntimeError(self.error or 'Wrist camera stream is closed')
            requested = time.monotonic()
            try:
                header, data = self._exchange(command, 'frame', timeout=6., on_acquired=callback)
                if header['image_size'] != list(HD_SIZE) or not data.startswith(b'\xff\xd8'):
                    raise ValueError('Expected a native 2592×1944 MJPEG frame')
                controls = header['sensor_controls']
                if controls.get('focus_absolute') != self.focus or controls.get('focus_auto') != 0:
                    raise ValueError('Native focus differs from session profile')
                if header['device_sequence'] == self.previous_sequence:
                    raise ValueError('Duplicate wrist frame sequence')
            except BaseException as error:
                self.error = str(error)
                self.process.stdin.close()
                raise
            self.previous_sequence = header['device_sequence']
            header.update(camera=self.name, source='wrist_native_continuous_mjpeg',
                camera_identity=self.ready['camera_identity'], settings=self.ready['settings'],
                focus=self.focus, received=time.time(), sequence=header['device_sequence'], kind='LIVE NATIVE',
                host_requested_monotonic=requested, host_received_monotonic=time.monotonic(),
                timestamp_kind='V4L2 buffer timestamp on this controller; cross-camera clocks unsynchronized')
            return data, header

    def read(self):
        return self._frame(b'V')

    def capture(self, directory, *, on_acquired=None):
        data, metadata = self._frame(b'C', on_acquired)
        output = Path(directory) / 'image.jpg'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        return output, metadata

    def _disconnect(self):
        # Closing stdin first also triggers the independent restoration supervisor
        # when the GUI was interrupted while waiting for the initial ready reply.
        try:
            if self.process is not None:
                self.process.stdin.close()
                try:
                    # Drain any pending JPEG or final report so the remote worker
                    # cannot block on stdout during an interrupted request.
                    self.process.stdin = None
                    self.process.communicate(timeout=65.)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3.)
                finally:
                    self.process = None
                if not (self.directory/'restoration.json').exists():
                    try:
                        data = self.ssh.run('cat '+self.remote+'/restoration.json', timeout=5.)
                        self._record_close(dict(json.loads(data), event='closed'))
                    except Exception:
                        # A disconnected network can prevent confirmation until
                        # it returns. The supervisor keeps its report on the UR.
                        pass
        finally:
            if self.activity is not None:
                activity, self.activity = self.activity, None
                activity.__exit__(None, None, None)

    def stop(self):
        self.finished.set()
        with self.lock:
            if self.process is None:
                return
            try:
                if self.error:
                    raise RuntimeError(self.error)
                header, _ = self._exchange(b'X', 'closed', timeout=70.)
                self._record_close(header)
                if not header.get('restore_ok') or header.get('session_error'):
                    raise RuntimeError(header.get('error') or header.get('session_error') or 'Unconfirmed wrist camera restoration')
            finally:
                try:
                    self._disconnect()
                finally:
                    verified = self.directory/'restoration.json'
                    if verified.exists() and json.loads(verified.read_text()).get('restore_ok'):
                        # Only this generated camera-session directory is ours.
                        self.ssh.run('rm -rf -- '+shlex.quote(self.remote), timeout=5.)

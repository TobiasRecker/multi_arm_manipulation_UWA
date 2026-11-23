"""Camera-only N100 transport with exclusive SDK lease and orderly release."""
import json
import os
import queue
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import threading
import time
import uuid

import cv2


class N100UsbCamera:
    device_id = '18443010314F3B1300'
    display_rotation_deg = 180

    def __init__(self, workspace, output, focus=112):
        self.ws, self.output, self.focus = Path(workspace), Path(output), focus
        self.config = self.ws/'setup/n100/ssh_config'
        self.child = self.log = self.reader = None
        self.latest = None
        self.error = None
        self.lock = threading.RLock()
        self.pending = None

    def ssh(self):
        return ['ssh','-F',str(self.config),'-o','BatchMode=yes','-o','ConnectTimeout=8',
                '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','uwa-n100-robot-lan']

    def command(self, script, *args):
        return shlex.join(['env','DEPTHAI_PROTOCOL=usb','DEPTHAI_TELEMETRY=0',
            'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','uwa-camera/.venv/bin/python','-u',
            'uwa-camera/'+script,*map(str,args)])

    def start(self):
        if self.child is not None:
            if self.child.poll() is None:
                return
            self._close_transport()
        self.output.mkdir(parents=True,exist_ok=True)
        self.latest = self.error = None
        self.log = (self.output/'preview.log').open('ab',buffering=0)
        self.child = subprocess.Popen([*self.ssh(),self.command('usb_oak_board_stream.py',
            '--device-id',self.device_id,'--focus',self.focus)],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=self.log)
        self.reader = threading.Thread(target=self._receive, args=(self.child,),daemon=True)
        self.reader.start()

    def _receive(self, child):
        try:
            while True:
                header = child.stdout.readline()
                if not header:
                    break
                kind, _, data = header.partition(b' ')
                if kind not in (b'UWA_FRAME', b'UWA_ACQUIRED', b'UWA_PHOTO', b'UWA_ERROR'):
                    if self.log:
                        self.log.write(header)
                    continue  # SDK startup messages share stdout.
                meta = json.loads(data)
                payload = None
                if kind in (b'UWA_PHOTO', b'UWA_FRAME'):
                    length = meta.pop('bytes')
                    limit = 40_000_000 if kind == b'UWA_PHOTO' else 8_000_000
                    if not isinstance(length, int) or not 0 < length <= limit:
                        raise ValueError('Invalid USB image packet length')
                    payload = child.stdout.read(length)
                    if len(payload) != length:
                        raise EOFError('Incomplete USB camera image')
                if kind == b'UWA_FRAME':
                    if meta['device_id'] != self.device_id or meta['lens_position'] != self.focus:
                        raise ValueError('USB preview identity/focus mismatch')
                    meta.update(remote_received=meta['received'], received=time.time(),
                        display_rotation_deg=self.display_rotation_deg, bytes=len(payload))
                    with self.lock:
                        self.latest = payload, meta, time.monotonic()
                else:
                    with self.lock:
                        if self.pending and self.pending[0] == meta['request_id']:
                            self.pending[1].put((kind, meta, payload))
        except Exception as error:
            self.error = str(error)
        finally:
            with self.lock:
                if self.pending:
                    self.pending[1].put((b'UWA_ERROR',
                        {'error': self.error or 'N100 USB worker closed during capture'}, None))

    def read(self):
        with self.lock:
            if self.child is None or self.child.poll() is not None:
                raise RuntimeError('N100 USB preview stopped; see '+str(self.output/'preview.log'))
            if self.error:
                raise RuntimeError(self.error)
            if self.latest is None or time.monotonic()-self.latest[2]>4:
                raise RuntimeError('Waiting for a fresh N100 USB frame')
            return self.latest[:2]

    def stop(self):
        if self.child is None:
            return
        child = self.child
        if child.poll() is None:
            try:
                child.stdin.write(b'stop\n');child.stdin.flush();child.stdin.close()
            except (BrokenPipeError,OSError):
                pass
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                raise RuntimeError('N100 USB preview release unconfirmed; native capture cancelled')
        self._close_transport()
        if child.returncode != 0:
            raise RuntimeError('N100 USB preview ended abnormally; check '+str(self.output/'preview.log'))

    def _close_transport(self):
        if self.reader:
            self.reader.join(timeout=2)
            self.reader = None
        for pipe in (self.child.stdin, self.child.stdout):
            if pipe is not None:
                pipe.close()
        if self.log:
            self.log.close()
            self.log = None
        self.child = None
        self.latest = None

    def capture(self, directory, *, on_acquired=None):
        """Capture the next fresh native frame, or a released cold one-shot for CLI callers."""
        if self.child is None:
            result = self._capture_single(directory)
            if on_acquired:
                on_acquired()
            return result
        with self.lock:
            if self.error or self.child.poll() is not None:
                raise RuntimeError(self.error or 'N100 USB session has ended')
            if self.pending:
                raise RuntimeError('N100 USB session already capturing')
            request_id = str(uuid.uuid4())
            replies = queue.Queue()
            self.pending = (request_id, replies)
        try:
            self.child.stdin.write((request_id + '\n').encode())
            self.child.stdin.flush()
            acquired = None
            while True:
                try:
                    kind, metadata, payload = replies.get(timeout=45)
                except queue.Empty as error:
                    raise TimeoutError('N100 USB session did not complete snapshot') from error
                if kind == b'UWA_ERROR':
                    raise RuntimeError(metadata['error'])
                if kind == b'UWA_ACQUIRED':
                    if acquired is not None:
                        raise ValueError('Duplicate N100 USB acquisition acknowledgement')
                    acquired = metadata['sequence']
                    if on_acquired:
                        on_acquired()
                elif kind == b'UWA_PHOTO':
                    if (acquired is None or metadata['photo']['sequence'] != acquired
                        or metadata['device_id'] != self.device_id or metadata['photo']['lens_position'] != self.focus
                        or metadata['native_size'] != [4056, 3040] or metadata['exposure_start_after_request_s'] <= 0):
                        raise ValueError('N100 USB native frame identity, sequence, size, focus or time mismatch')
                    return self._save(directory, metadata, payload)
        finally:
            with self.lock:
                self.pending = None

    def _save(self, directory, metadata, payload):
        if (payload[:8] != b'\x89PNG\r\n\x1a\n' or payload[12:16] != b'IHDR'
                or len(payload) < 24 or struct.unpack('>II', payload[16:24]) != (4056, 3040)):
            raise ValueError('Invalid native USB PNG')
        directory = Path(directory)
        native = directory/'native'
        native.mkdir()
        image = native/'native.png'
        image.write_bytes(payload)
        factory = metadata.pop('factory_calibration')
        (native/'factory-calibration.json').write_text(json.dumps(factory, sort_keys=True, indent=2))
        reduced = cv2.imread(str(image), cv2.IMREAD_REDUCED_COLOR_2)
        if reduced is None or not cv2.imwrite(str(native/'preview.jpg'),
                cv2.resize(reduced, (1600, round(3040*1600/4056))), [cv2.IMWRITE_JPEG_QUALITY, 94]):
            raise ValueError('Cannot read or preview the native USB PNG')
        (native/'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
        destination = directory/'image.png'
        os.link(image, destination)
        return destination, metadata

    def _capture_single(self, directory):
        """Original native one-shot for consumers without a running GUI session."""
        self.stop()
        remote = 'uwa-camera/results/gui-'+uuid.uuid4().hex
        result = subprocess.run([*self.ssh(),self.command('usb_oak_photo.py',
            '--device-id',self.device_id,'--focus',self.focus,'--output',remote)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=100)
        if result.returncode:
            raise RuntimeError((result.stderr+result.stdout).decode(errors='replace')[-2500:])
        native = Path(directory)/'native'
        subprocess.run(['scp','-F',str(self.config),'-o','BatchMode=yes','-o','ConnectTimeout=8',
            '-r','uwa-n100-robot-lan:'+remote,str(native)],check=True,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,timeout=60)
        metadata = json.loads((native/'metadata.json').read_text())
        if not (metadata.get('success') and metadata.get('camera_closed') and metadata.get('camera_lease_released')
            and metadata.get('device_id')==self.device_id and metadata.get('native_size')==[4056,3040]
            and metadata.get('photo',{}).get('lens_position')==self.focus
            and metadata.get('factory_sha256_before')==metadata.get('factory_sha256_after')):
            raise ValueError('N100 native USB capture identity, focus or lease result not confirmed')
        image = native/'native.png'
        raw = cv2.imread(str(image))
        if raw is None or raw.shape != (3040,4056,3):
            raise ValueError('N100 USB photo must be native4056×3040')
        destination = Path(directory)/'image.png'
        shutil.copy2(image,destination)
        return destination,metadata

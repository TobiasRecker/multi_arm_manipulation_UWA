"""Camera-only N100 transport with exclusive SDK lease and orderly release."""
import json
from pathlib import Path
import shlex
import shutil
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

    def ssh(self):
        return ['ssh','-F',str(self.config),'-o','BatchMode=yes','-o','ConnectTimeout=8',
                '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','uwa-n100-robot-lan']

    def command(self, script, *args):
        return shlex.join(['env','DEPTHAI_PROTOCOL=usb','DEPTHAI_TELEMETRY=0',
            'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','uwa-camera/.venv/bin/python','-u',
            'uwa-camera/'+script,*map(str,args)])

    def start(self):
        if self.child is not None and self.child.poll() is None:
            return
        self.output.mkdir(parents=True,exist_ok=True)
        self.latest = self.error = None
        self.log = (self.output/'preview.log').open('ab',buffering=0)
        self.child = subprocess.Popen([*self.ssh(),self.command('usb_oak_board_preview.py',
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
                if not header.startswith(b'UWA_FRAME '):
                    continue  # SDK startup text is not an image header.
                meta = json.loads(header[len(b'UWA_FRAME '):])
                length = meta['bytes']
                if not isinstance(length,int) or not 0 < length < 8_000_000:
                    raise ValueError('Invalid USB preview packet length')
                payload = bytearray()
                while len(payload)<length:
                    part = child.stdout.read(length-len(payload))
                    if not part:
                        raise EOFError('Incomplete USB preview image')
                    payload.extend(part)
                if meta['device_id'] != self.device_id or meta['lens_position'] != self.focus:
                    raise ValueError('USB preview identity/focus mismatch')
                meta.update(remote_received=meta['received'],received=time.time(),
                    display_rotation_deg=self.display_rotation_deg)
                with self.lock:
                    self.latest = bytes(payload),meta,time.monotonic()
        except Exception as error:
            self.error = str(error)

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
        if self.reader:
            self.reader.join(timeout=2)
        if self.log:
            self.log.close();self.log=None
        self.child = None
        self.latest = None
        if child.returncode != 0:
            raise RuntimeError('N100 USB preview ended abnormally; check '+str(self.output/'preview.log'))

    def capture(self, directory):
        """One native raw photo; the preview must have released its own lease."""
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

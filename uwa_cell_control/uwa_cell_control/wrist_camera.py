"""HTTP camera controls reconstructed from Robotiq UCC 1.11.3; no robot commands."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request


class CameraError(RuntimeError):
    pass


class WristCamera:
    def __init__(self, ip, *, timeout=3.0):
        self.base = f'http://{ip}:4242'
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, path, *, body=None, post=False, image=False):
        headers = {'Cache-Control': 'no-cache'}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        elif post:
            data = b''
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        with self.opener.open(req, timeout=self.timeout) as response:
            content = response.read(10_000_001)
        if len(content) > 10_000_000:
            raise CameraError('Camera response exceeds 10 MB')
        if image:
            if not content.startswith(b'\xff\xd8'):
                raise CameraError('Camera did not return a JPEG')
            return content
        try:
            result = json.loads(content)
        except (ValueError, UnicodeDecodeError) as error:
            raise CameraError('Camera returned invalid JSON') from error
        if not isinstance(result, dict) or result.get('status') != 'succeeded':
            raise CameraError(f'Camera rejected request: {result}')
        return result

    def settings(self):
        result = self.request('/getcamerasettings').get('cameraSettings')
        if not isinstance(result, dict) or type(result.get('focus')) is not int or type(result.get('focusAuto')) is not bool:
            raise CameraError('Camera response has no valid focus settings')
        return result

    def image(self):
        return self.request('/current.jpg?type=color', image=True)

    def update_focus(self, *, focus, auto):
        if type(focus) is not int or not 0 <= focus <= 1023 or type(auto) is not bool:
            raise ValueError('Focus must be an integer 0…1023; auto must be boolean')
        before = self.settings()
        desired = copy.deepcopy(before)
        desired.update(focus=focus, focusAuto=auto)
        self.request('/setcamerasettings?setManualValuesIfModeChanged=true',
                     body={'cameraSettings': desired})
        after = self.settings()
        if after['focusAuto'] != auto or (not auto and after['focus'] != focus):
            raise CameraError(f'Focus readback differs from request: {after}')
        unrelated = [k for k in before if k not in ('focus', 'focusAuto') and before[k] != after.get(k)]
        if unrelated:
            raise CameraError('Other camera settings changed during write: ' + ', '.join(unrelated))
        return after

    def manual(self, slider_value):
        if type(slider_value) is not int or not 0 <= slider_value <= 1023:
            raise ValueError('Slider value must be an integer 0…1023')
        return self.update_focus(focus=1023-slider_value, auto=False)

    def restore(self, original):
        # Keep current lighting/exposure etc.; restore only our two focus fields.
        result = self.update_focus(focus=original['focus'], auto=original['focusAuto'])
        if original['focusAuto']:
            result = self.refocus()
        return result

    def refocus(self, *, wait_seconds=12.):
        current = self.settings()
        if not current['focusAuto']:
            self.update_focus(focus=current['focus'], auto=True)
        self.request('/trigger?focus=true&exposure=false&whiteBalance=false', post=True)
        deadline = time.monotonic()+wait_seconds
        while True:
            result = self.request('/triggerinprogress')
            progress = result.get('triggerInProgress')
            if type(progress) is not bool:
                raise CameraError('Missing autofocus progress confirmation')
            if not progress:
                return self.settings()
            if time.monotonic() >= deadline:
                raise CameraError('Autofocus did not finish within the time limit')
            time.sleep(.1)


def save_snapshot(directory, name, jpeg, settings, *, dimensions=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{name}.jpg'
    path.write_bytes(jpeg)
    metadata = {'received_utc': datetime.now(timezone.utc).isoformat(),
                'image': path.name, 'sha256': hashlib.sha256(jpeg).hexdigest(),
                'bytes': len(jpeg), 'settings': settings,
                'timestamp_kind': 'PC receipt; sensor exposure time unavailable',
                'dimensions': dimensions}
    path.with_suffix('.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return path

"""HTTP camera controls reconstructed from Robotiq UCC 1.11.3; no robot commands."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request


def settings_differences(before, after, *, ignored=(), managed_led=False):
    """Compare configuration; leased manual LED readback uses enum1 or enum2."""
    ignored = set(ignored)
    if (managed_led and before.get('lightingMode') in (1, 2)
            and after.get('lightingMode') in (1, 2)
            and before.get('lightingValue') == after.get('lightingValue')):
        ignored.add('lightingMode')
    return [key for key in before if key not in ignored and before[key] != after.get(key)]


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

    def settings(self, *, refresh=False):
        result = self.request('/getcamerasettings'+('?forceRefresh=true' if refresh else '')).get('cameraSettings')
        if not isinstance(result, dict) or type(result.get('focus')) is not int or type(result.get('focusAuto')) is not bool:
            raise CameraError('Camera response has no valid focus settings')
        return result

    def update_controls(self, changes):
        """Only send named camera fields; never overwrite the user's focus."""
        bounds = {'exposure': (1, 66604), 'gain': (16, 1008),
                  'exposureSensitivity': (-7, 7), 'lightingMode': (0, 2),
                  'lightingValue': (0, 175)}
        for key, value in changes.items():
            if key == 'exposureAuto':
                if type(value) is not bool:
                    raise ValueError('exposureAuto must be boolean')
            elif key not in bounds or type(value) is not int or not bounds[key][0] <= value <= bounds[key][1]:
                raise ValueError(f'Invalid camera control: {key}={value}')
        before = self.settings()
        self.request('/setcamerasettings?setManualValuesIfModeChanged=true', body={'cameraSettings': changes})
        after = self.settings()
        for key, value in changes.items():
            if after.get(key) != value:
                raise CameraError(f'{key} readback differs: requested {value}, received {after.get(key)}')
        if any(before[k] != after[k] for k in ('focus', 'focusAuto')):
            raise CameraError('Focus changed during exposure/lighting operation')
        return after

    def exposure(self, microseconds, gain_multiplier=1):
        if type(gain_multiplier) is not int or not 1 <= gain_multiplier <= 63:
            raise ValueError('Gain multiplier must be 1…63')
        return self.update_controls({'exposureAuto': False, 'exposure': microseconds, 'gain': 16*gain_multiplier})

    def auto_exposure(self, ev=0):
        result = self.update_controls({'exposureAuto': True, 'exposureSensitivity': ev})
        self.trigger(exposure=True)
        return self.settings()

    def lighting(self, mode, percent):
        if type(percent) is not int or not 0 <= percent <= 100:
            raise ValueError('LED intensity must be 0…100 percent')
        from .wrist_activity import directory, configure
        ip = self.base.split('//')[1].split(':')[0]
        if (directory(ip) / 'enabled').exists():
            if mode not in (1, 2):
                raise CameraError('Managed LEDs use manual intensity. Select LED Manual or LED Off.')
            return configure(ip, 0 if mode == 1 else int(percent*1.75+.5))
        return self.update_controls({'lightingMode': mode, 'lightingValue': int(percent*1.75+.5)})

    def restore_appearance(self, original):
        changes = {key: original[key] for key in ('exposureAuto', 'exposureSensitivity', 'lightingMode', 'lightingValue')}
        from .wrist_activity import directory, configure
        ip = self.base.split('//')[1].split(':')[0]
        managed = (directory(ip) / 'enabled').exists()
        if managed:
            changes = {k: v for k, v in changes.items() if not k.startswith('lighting')}
        # Auto-mode cached defaults can be zero; never send them as manual values.
        if 1 <= original.get('exposure', 0) <= 66604:
            changes['exposure'] = original['exposure']
        if 16 <= original.get('gain', 0) <= 1008:
            changes['gain'] = original['gain']
        result = self.update_controls(changes)
        if managed:
            result = configure(ip, original['lightingValue'])
        if original['exposureAuto']:
            self.trigger(exposure=True)
            result = self.settings()
        return result

    def trigger(self, *, focus=False, exposure=False, wait_seconds=12.):
        self.request(f'/trigger?focus={str(focus).lower()}&exposure={str(exposure).lower()}&whiteBalance=false', post=True)
        deadline = time.monotonic()+wait_seconds
        while True:
            progress = self.request('/triggerinprogress').get('triggerInProgress')
            if type(progress) is not bool:
                raise CameraError('Missing camera trigger completion confirmation')
            if not progress:
                return
            if time.monotonic() >= deadline:
                raise CameraError('Camera trigger did not finish within the time limit')
            time.sleep(.1)

    def image(self):
        with self.activity() as use:
            if use.started:
                # Do not return the image cached before the light came on.
                self.trigger()
            return self.request('/current.jpg?type=color', image=True)

    def activity(self):
        from .wrist_activity import Activity
        return Activity(self.base.split('//')[1].split(':')[0])

    def update_focus(self, *, focus, auto):
        if type(focus) is not int or not 0 <= focus <= 1023 or type(auto) is not bool:
            raise ValueError('Focus must be an integer 0…1023; auto must be boolean')
        before = self.settings()
        desired = copy.deepcopy(before)
        desired.update(focus=focus, focusAuto=auto)
        from .wrist_activity import directory
        ip = self.base.split('//')[1].split(':')[0]
        managed = (directory(ip) / 'enabled').exists()
        if managed:
            # A full focus write contains getter LED mode1. Its setter enum
            # is manual2; preserve the current intensity rather than turning off.
            desired['lightingMode'] = 2
        self.request('/setcamerasettings?setManualValuesIfModeChanged=true',
                     body={'cameraSettings': desired})
        after = self.settings()
        if after['focusAuto'] != auto or (not auto and after['focus'] != focus):
            raise CameraError(f'Focus readback differs from request: {after}')
        ignored = {'focus', 'focusAuto'}
        if before.get('exposureAuto'):
            ignored.update(('exposure', 'gain'))
        unrelated = settings_differences(before, after, ignored=ignored, managed_led=managed)
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
        self.trigger(focus=True, wait_seconds=wait_seconds)
        return self.settings()


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

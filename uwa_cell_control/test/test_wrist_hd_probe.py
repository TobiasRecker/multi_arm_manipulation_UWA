"""A failed/low-resolution probe must restore controls and inhibit native export."""
import copy

import pytest
from uwa_cell_control.wrist_hd_probe import probe
from uwa_cell_control.wrist_camera import CameraError


@pytest.mark.parametrize('fail_processing', [False, True, 'no_code'])
def test_no_unconfirmed_native_export_and_restore(tmp_path, monkeypatch, fail_processing):
    monkeypatch.setattr('uwa_cell_control.wrist_hd_probe.time.sleep', lambda _: None)
    original = {'focus': 404, 'focusAuto': False, 'exposure': 40000, 'gain': 32,
                'exposureAuto': False, 'exposureSensitivity': 0,
                'lightingMode': 2, 'lightingValue': 53}

    class Camera:
        state = 'Normal'
        values = copy.deepcopy(original)
        calls = []

        def settings(self):
            return copy.deepcopy(self.values)

        def image(self):
            return b'\xff\xd8test\xff\xd9'

        def request(self, path, **kwargs):
            self.calls.append(path)
            if path == '/status':
                return {'status': 'succeeded', 'current state': self.state}
            if path == '/beginbarcode':
                self.state = 'barcode'
                self.values['focus'] = 100  # Vendor state entry resets user settings.
            elif path.startswith('/setcamerasettings'):
                self.values.update(kwargs['body']['cameraSettings'])
            elif path == '/process' and fail_processing == 'no_code':
                raise CameraError("Camera rejected request: {'code': 49156, 'message': 'barcode process failed', 'status': 'failed'}")
            elif path == '/process' and fail_processing:
                raise RuntimeError('Capture failed')
            elif path.startswith('/map'):
                return {'status': 'succeeded', 'x': 640, 'y': 480}
            elif path.startswith('/last.jpg'):
                return self.image()
            elif path == '/rejectmodule':
                self.state = 'Normal'
                self.values['focus'] = 0
            return {'status': 'succeeded'}

    camera = Camera()
    result = probe(camera, tmp_path/'session')
    assert result['success'] is False
    assert result['restore_ok'] is True
    assert camera.values == original
    assert '/lastCapture.jpg' not in camera.calls
    assert camera.state == 'Normal'

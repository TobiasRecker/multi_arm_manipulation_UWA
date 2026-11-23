"""Check the fresh USB snapshot reply and ordered frame acknowledgement."""
import io
from types import SimpleNamespace

import pytest

from uwa_cell_control.n100_usb_camera import N100UsbCamera


class WorkerInput(io.BytesIO):
    def __init__(self, camera, stale=False):
        super().__init__()
        self.camera = camera
        self.stale = stale
        self.requests = []

    def flush(self):
        request_id, replies = self.camera.pending
        assert self.getvalue().decode().splitlines()[-1] == request_id
        self.requests.append(request_id)
        sequence = len(self.requests) * 5
        replies.put((b'UWA_ACQUIRED', dict(sequence=sequence), None))
        replies.put((b'UWA_PHOTO', dict(photo=dict(lens_position=112, sequence=sequence),
            device_id=self.camera.device_id, native_size=[4056, 3040],
            exposure_start_after_request_s=-0.1 if self.stale else 0.1), b'photo'))


def test_warm_requests_share_worker_and_acknowledge_before_saving(tmp_path, monkeypatch):
    camera = N100UsbCamera(tmp_path, tmp_path)
    pipe = WorkerInput(camera)
    camera.child = SimpleNamespace(poll=lambda: None, stdin=pipe)
    events = []
    monkeypatch.setattr(camera, '_save', lambda directory, meta, data: events.append(('save', meta['photo']['sequence'])))
    for _ in range(2):
        camera.capture(tmp_path, on_acquired=lambda: events.append('frame'))
    assert events == ['frame', ('save', 5), 'frame', ('save', 10)]
    assert len(set(pipe.requests)) == 2
    assert camera.child.stdin is pipe


def test_warm_request_rejects_photo_with_pretrigger_exposure(tmp_path):
    camera = N100UsbCamera(tmp_path, tmp_path)
    camera.child = SimpleNamespace(poll=lambda: None, stdin=WorkerInput(camera, stale=True))
    with pytest.raises(ValueError, match='time mismatch'):
        camera.capture(tmp_path)
    assert camera.pending is None
    assert not list(tmp_path.iterdir())


def test_cli_with_no_session_delegates_to_released_single_capture(tmp_path, monkeypatch):
    camera = N100UsbCamera(tmp_path, tmp_path)
    monkeypatch.setattr(camera, '_capture_single', lambda directory: (directory, {'camera_closed': True}))
    assert camera.capture(tmp_path) == (tmp_path, {'camera_closed': True})
    assert camera.child is None

"""Board identity, partial observations and three-camera transaction boundaries."""
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import yaml

from uwa_cell_control.board_capture import MobileBoard, CaptureRig, CAMERAS


def config():
    return yaml.safe_load((Path(__file__).parents[2] /
        'uwa_cell_description/config/mobile_charuco_a4.yaml').read_text())


def board_image(first=75):
    c = config()
    c['marker_ids'] = list(range(first, first + 17))
    detector = MobileBoard(c)
    image = detector.board.generateImage((1400, 1000), marginSize=0)
    image = cv2.copyMakeBorder(image, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


def test_only_mobile_board_counts_not_fixed_tableboards():
    detector = MobileBoard(config())
    full, _ = detector.observe(board_image())
    assert full['full'] and full['usable'] and full['corners'] == 24
    assert set(full['marker_ids']) == set(range(75, 92))
    points = np.asarray(full['object_points'])
    assert np.allclose(points.min(axis=0), [.038, .038, 0])
    assert np.allclose(points.max(axis=0), [.228, .152, 0])
    for first in (0, 50):
        wrong, _ = detector.observe(board_image(first))
        assert wrong['corners'] == 0 and wrong['marker_ids'] == [] and not wrong['usable']


def test_partial_board_is_not_full_and_has_valid_correspondences():
    image = board_image()
    image[:, 750:] = 255
    result, _ = MobileBoard(config()).observe(image)
    assert 0 < result['corners'] < 24 and not result['full']
    assert result['status'] == 'PARTIAL BOARD'
    assert len(result['image_points']) == len(result['object_points']) == len(result['corner_ids'])
    assert np.isfinite(result['image_points']).all()
    with pytest.raises(ValueError):
        MobileBoard(config()).observe(None)


def rig(tmp_path, failing=None):
    r = CaptureRig.__new__(CaptureRig)
    r.session = tmp_path
    r.board_config = config()
    r.fixed_settings = {}
    r.telemetry = lambda: dict(arms={}, complete=False)
    r.busy = threading.Lock()
    calls = []
    r.preview = SimpleNamespace(stop=lambda: calls.append('stop'),
        start=lambda: calls.append('start'), focus=116)
    def capture(name, directory, native):
        assert calls == ['stop']
        directory.mkdir()
        if name == failing:
            raise RuntimeError('Camera offline')
        return dict(success=True, observation=dict(usable=True, full=True, corners=24))
    r.capture_one = capture
    return r, calls


def test_capture_releases_own_preview_before_parallel_photos_and_resumes(tmp_path):
    r, calls = rig(tmp_path)
    first = r.capture_all(resume_preview=True)
    assert first['all_captured'] and first['all_usable'] and first['all_full']
    assert not first['hardware_synchronized'] and not first['calibration_applied']
    assert calls == ['stop', 'start'] and set(first['cameras']) == set(CAMERAS)
    assert Path(first['directory'], 'manifest.json').exists()
    calls.clear()
    second = r.capture_all()
    assert first['directory'] != second['directory']
    assert json.loads(Path(first['directory'], 'manifest.json').read_text()) == first


def test_failed_camera_keeps_other_images_but_never_marks_set_complete(tmp_path):
    r, calls = rig(tmp_path, 'right_rear')
    result = r.capture_all(resume_preview=True)
    assert not result['all_captured'] and not result['all_usable'] and not result['all_full']
    assert result['cameras']['right_front']['success']
    assert not result['cameras']['right_rear']['success']
    assert calls == ['stop', 'start'] and not r.busy.locked()


def test_capture_reentry_is_rejected_without_changing_existing_transaction(tmp_path):
    r, calls = rig(tmp_path)
    r.busy.acquire()
    with pytest.raises(RuntimeError, match='already running'):
        r.capture_all()
    assert calls == [] and r.busy.locked()


def test_stop_waits_for_sdk_lock_after_wrapper_exit(tmp_path, monkeypatch):
    from uwa_cell_control import board_capture as module
    from uwa_cell_control.board_capture import OakPreview
    (tmp_path / 'setup/oak4/photos').mkdir(parents=True)
    preview = OakPreview(tmp_path, {}, tmp_path / 'preview')
    polls = iter([None, None])
    preview.child = SimpleNamespace(pid=12345, poll=lambda: next(polls), wait=lambda **k: 0)
    locked = [True, True, False]
    events = []
    def flock(file, flags):
        if flags == module.fcntl.LOCK_EX | module.fcntl.LOCK_NB and locked.pop(0):
            events.append('busy')
            raise BlockingIOError()
        events.append('released')
    monkeypatch.setattr(module.fcntl, 'flock', flock)
    monkeypatch.setattr(module.os, 'killpg', lambda *args: events.append('signal own process group'))
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    preview.stop()
    assert events == ['signal own process group', 'busy', 'busy', 'released', 'released']

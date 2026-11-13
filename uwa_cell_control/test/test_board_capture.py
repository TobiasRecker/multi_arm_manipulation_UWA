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


def test_focus_session_preserves_managed_led_mode_and_restores_without_native_restart(tmp_path, monkeypatch):
    from uwa_cell_control.wrist_camera import WristCamera
    from uwa_cell_control.wrist_activity import directory
    monkeypatch.setenv('UWA_WRIST_ACTIVITY_ROOT', str(tmp_path / 'leases'))
    folder = directory('192.168.8.169'); folder.mkdir(parents=True); (folder / 'enabled').touch()
    state = dict(focus=378, focusAuto=True, lightingMode=1, lightingValue=0,
                 exposureAuto=False, exposure=33333, gain=16, focusWindowX1=165)
    original = dict(state)
    client = WristCamera('192.168.8.169')
    writes = []
    def request(path, body=None, **kwargs):
        if body:
            change = dict(body['cameraSettings']); writes.append(change)
            # Real UCC getter1 / setter manual2; partial writes reset the mode.
            state.update(change)
            state['lightingMode'] = 1 if change.get('lightingMode') == 2 else 0
        return dict(status='succeeded', cameraSettings=dict(state))
    client.request = request
    r = CaptureRig.__new__(CaptureRig)
    r.session=tmp_path; r.wrist_cameras=('left_rear',); r.original_settings={}; r.fixed_settings={}
    r.optics={'wrist_manual_focus': {'left_rear':406}}; r.wrist=lambda name:client
    r.inventory={'robots':{'left_rear':{'ip':'192.168.8.169'}}}
    r.native=lambda *args: pytest.fail('Focus restoration must not restart vision')
    monkeypatch.setattr('uwa_cell_control.board_capture.time.sleep', lambda _:None)
    r.lock_focus()
    assert state['focus']==406 and not state['focusAuto'] and state['lightingMode']==1
    r.restore_focus()
    assert state==original
    assert all(write['lightingMode']==2 and 'focusWindowX1' not in write for write in writes)


def test_autofocus_restore_corrects_converted_roi_with_bounded_joint_writes(tmp_path, monkeypatch):
    from uwa_cell_control.board_capture import restore_session_focus
    from uwa_cell_control.wrist_activity import directory
    monkeypatch.setenv('UWA_WRIST_ACTIVITY_ROOT',str(tmp_path))
    folder=directory('192.168.8.2');folder.mkdir();(folder/'enabled').touch()
    original=dict(focus=335,focusAuto=True,lightingMode=1,lightingValue=0,
                  focusWindowX1=165,focusWindowY1=134,focusWindowX2=450,focusWindowY2=339)
    state=dict(original,focus=245,focusAuto=False);writes=[]
    def request(path,body):
        change=body['cameraSettings'];writes.append(change)
        state.update(change);state['lightingMode']=1
        if change.get('focusAuto'):
            state.update(focusWindowX1=158,focusWindowY1=118)
        if 'focusWindowX1' in change:
            assert all(key in change for key in ('focusWindowX1','focusWindowY1','focusWindowX2','focusWindowY2'))
            state['focusWindowX1']=max(158,change['focusWindowX1']-30)
            state['focusWindowY1']=max(118,change['focusWindowY1']-12)
    camera=SimpleNamespace(base='http://192.168.8.2:4242',settings=lambda **kwargs:dict(state),request=request)
    monkeypatch.setattr('uwa_cell_control.board_capture.time.sleep',lambda _:None)
    assert restore_session_focus(camera,original)==original
    assert len(writes)<=17

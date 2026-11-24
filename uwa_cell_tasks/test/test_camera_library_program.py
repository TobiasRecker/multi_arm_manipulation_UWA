"""Library routing and shared camera-session validity; no hardware or simulator."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
import carton_camera_session as camera
import run_carton_program as runner

spec = importlib.util.spec_from_file_location('camera_library_server', REPO/'scripts/skill_library_server.py')
library = importlib.util.module_from_spec(spec); spec.loader.exec_module(library)


def test_catalog_has_separate_calibration_and_shared_expiry(tmp_path, monkeypatch):
    runs = library.Runs(tmp_path)
    monkeypatch.setattr(runs, 'camera_status', lambda: dict(calibrate_available=True, live_blocker=None,
        camera_valid_from='2026-11-20T10:00:00+08:00', camera_valid_until='2026-11-20T22:00:00+08:00'))
    catalog = runs.catalog()
    programs = {p['id']: p for p in catalog['programs']}
    calibration = programs[runner.CAMERA_PROGRAM]
    carton = programs[runner.PROGRAM]
    assert calibration['kind'] == 'camera_calibration' and calibration['calibrate_available']
    assert not calibration['live_available'] and not calibration['demo_available']
    assert calibration['camera_valid_until'] == carton['camera_valid_until'] == catalog['camera_reference']['valid_until']
    assert carton['camera_program'] == runner.CAMERA_PROGRAM


def test_camera_program_cannot_start_robot_modes(tmp_path):
    runs = library.Runs(tmp_path)
    for mode in ('demo', 'live'):
        with pytest.raises(ValueError):
            runs.start(runner.CAMERA_PROGRAM, mode)
    assert not list(tmp_path.iterdir())


def test_camera_program_dispatches_calibration_only(tmp_path, monkeypatch):
    runs = library.Runs(tmp_path, live_config=tmp_path/'camera.json')
    monkeypatch.setattr(runs, 'camera_status', lambda: dict(calibrate_available=True, live_blocker='Calibration required'))
    child = Mock(pid=12345)
    popen = Mock(return_value=child)
    monkeypatch.setattr(library.subprocess, 'Popen', popen)
    monkeypatch.setattr(library, 'process_stamp', lambda pid: 'known-process')
    monkeypatch.setattr(library, 'Thread', Mock())
    result = runs.start(runner.CAMERA_PROGRAM, 'calibrate')
    command = popen.call_args.args[0]
    assert command[command.index('--program')+1] == runner.CAMERA_PROGRAM
    assert command[command.index('--mode')+1] == 'calibrate'
    assert result['program'] == runner.CAMERA_PROGRAM and result['state'] == 'running'


def test_reference_expires_exactly_twelve_hours_without_renewal(tmp_path):
    profile = dict(device_id='1479883285', focus=107, image_size=[8000, 6000], K=np.eye(3).tolist(), D=[0]*5)
    intrinsics = tmp_path/'intrinsics.json'; intrinsics.write_text(json.dumps(profile))
    start = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
    end = start + timedelta(hours=12)
    pose = np.eye(4); pose[2, 3] = 1.
    session = dict(schema_version=1, board='right_table_board', valid_from=start.isoformat(), valid_until=end.isoformat(),
        optics=profile, sources_sha256=camera.validation_sources(), T_camera_board=pose.tolist())
    original = json.dumps(session, sort_keys=True)
    camera.validate_session(session, intrinsics, now=end-timedelta(microseconds=1))
    assert json.dumps(session, sort_keys=True) == original
    with pytest.raises(ValueError, match='12-hour'):
        camera.validate_session(session, intrinsics, now=end)


@pytest.mark.parametrize('preview_ok', [True, False])
@pytest.mark.parametrize('fixed_fit', [True, False])
def test_calibration_publishes_only_complete_result_without_robot_calls(tmp_path, monkeypatch, preview_ok, fixed_fit):
    out = tmp_path/'run'; out.mkdir()
    capture = tmp_path/'capture'; capture.mkdir()
    (capture/'metadata.json').write_text('{}')
    shared = tmp_path/'shared.json'; shared.write_text('old reference')
    monkeypatch.setattr(runner, 'live_inputs', lambda _: dict(camera_session=shared, intrinsics=tmp_path/'K.json', focus=107))
    session = dict(right_marker_count=17, held_out_rms_px=1.2,
        valid_from='2026-11-20T10:00:00+08:00', valid_until='2026-11-20T22:00:00+08:00')
    monkeypatch.setattr(runner, 'create_session', lambda *args, **kwargs: session)
    monkeypatch.setattr(runner, 'measure_fixed_reference', lambda *args: capture if fixed_fit else None)
    capture_modes = []
    def capture_command(command, *args, **kwargs):
        mode = command[command.index('--mode')+1]
        capture_modes.append(mode)
        if mode == 'standard':
            assert command[-2:] == ['--focus', 107]
        return json.dumps(dict(mode=mode, directory=str(capture), metadata=str(capture/'metadata.json')))
    monkeypatch.setattr(runner, 'logged_command', capture_command)
    monkeypatch.setattr(runner, 'n100_preflight', Mock(side_effect=AssertionError('No robot preflight')))
    monkeypatch.setattr(runner, 'n100', Mock(side_effect=AssertionError('No robot RPC')))
    import cv2
    monkeypatch.setattr(cv2, 'imread', lambda _: np.zeros((2, 2, 3), np.uint8))
    def save(path, image):
        if preview_ok:
            Path(path).write_bytes(b'preview')
        return preview_ok
    monkeypatch.setattr(cv2, 'imwrite', save)
    if preview_ok:
        result = runner.calibrate_camera(runner.Progress(out), tmp_path/'config.json')
        assert json.loads(shared.read_text()) == session == json.loads((out/'camera-session.json').read_text())
        assert result['valid_until'] == session['valid_until']
        assert (out/result['artifacts']['camera_preview']).is_file()
    else:
        with pytest.raises(ValueError, match='preview'):
            runner.calibrate_camera(runner.Progress(out), tmp_path/'config.json')
        assert not shared.exists()
    assert capture_modes == (['standard'] if fixed_fit else ['standard', 'charuco'])

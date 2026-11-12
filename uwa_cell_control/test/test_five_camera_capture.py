"""Five independent photo jobs, stationary audit and per-table reference identity."""
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import yaml

from uwa_cell_control.board_capture import FIVE_CAMERAS, MobileBoard, reference_board
from uwa_cell_control.capture_telemetry import StationarityAudit
from test_board_capture import rig


def test_each_table_reference_keeps_its_actual_scale_and_marker_ids():
    raw = yaml.safe_load((Path(__file__).parents[2] / 'uwa_cell_description/config/cell_layout.yaml').read_text())
    for table, first in [('left', 0), ('right', 50)]:
        config = reference_board(raw, table)
        detector = MobileBoard(config)
        image = detector.board.generateImage((1400, 1000))
        image = cv2.copyMakeBorder(image, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
        observation, _ = detector.observe(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR))
        assert observation['full'] and set(observation['marker_ids']) == set(range(first, first + 17))
        np.testing.assert_allclose(np.min(observation['object_points'], axis=0), [.04, .04, 0])
    with pytest.raises(ValueError):
        reference_board(raw, 'mobile')


def test_fifth_camera_failure_is_never_hidden_by_three_successes(tmp_path):
    r, _ = rig(tmp_path, failing='left_rear')
    r.cameras, r.wrist_cameras = FIVE_CAMERAS, FIVE_CAMERAS[:-1]
    result = r.capture_all()
    assert len(result['cameras']) == 5 and not result['all_captured']
    assert result['cameras']['left_front']['success']
    assert not result['cameras']['left_rear']['success']


def test_five_camera_capture_requires_settle_before_requesting_any_photo(tmp_path):
    r, calls = rig(tmp_path)
    r.cameras, r.wrist_cameras, r.audit_stationarity = FIVE_CAMERAS, FIVE_CAMERAS[:-1], True
    def fail():
        raise RuntimeError('moving arm')
    r.capture_monitor = lambda directory: SimpleNamespace(wait_still=fail,
        finish=lambda: dict(stationarity_confirmed=False, violations=['moving arm']))
    result = r.capture_all()
    assert calls == ['stop'] and not result['cameras']
    assert not result['stationary_set_confirmed'] and not result['all_captured']
    assert not r.busy.locked()


def test_telemetry_motion_and_staleness_remain_failed_even_after_return():
    audit = StationarityAudit({'arm': list('abcdef')})
    for t in np.arange(0, 1.01, .05):
        audit.receive('arm', np.zeros(6), np.zeros(6), float(t))
    assert audit.ready(1.)
    audit.arm(1.)
    audit.receive('arm', [0, 0, .02, 0, 0, 0], np.zeros(6), 1.05)
    audit.receive('arm', np.zeros(6), np.zeros(6), 1.1)
    audit.check_freshness(2.)
    result = audit.summary()
    assert not result['stationarity_confirmed']
    assert result['max_joint_drift_rad']['arm'] == .02
    assert len(result['violations']) == 2


def test_settle_needs_all_arms_and_finite_low_velocity():
    audit = StationarityAudit({'a': list('abcdef'), 'b': list('abcdef')})
    for t in np.arange(0, 1.01, .05):
        audit.receive('a', np.zeros(6), np.zeros(6), float(t))
    assert not audit.ready(1.)
    for t in np.arange(0, 1.01, .05):
        audit.receive('b', np.zeros(6), np.full(6, .1), float(t))
    assert not audit.ready(1.)
    with pytest.raises(RuntimeError):
        audit.arm(1.)


def test_five_camera_gui_has_all_views_and_reports_failed_stationarity(tmp_path, monkeypatch):
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from python_qt_binding import QtWidgets
    from uwa_cell_control.board_capture_gui import Window, Worker
    from test_board_capture import config
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(Worker, 'start', lambda _: None)
    window = Window(SimpleNamespace(cameras=FIVE_CAMERAS, board_config=config(), session=tmp_path))
    assert set(window.labels) == set(FIVE_CAMERAS)
    assert window.capture.text() == 'CAPTURE ALL FIVE'
    window.on_result(dict(all_captured=True, all_usable=False, stationary_set_confirmed=False,
        cameras={name: {'observation': {'corners': 0}} for name in FIVE_CAMERAS}, directory=str(tmp_path)))
    assert window.action.text().startswith('FAILED STATIONARITY AUDIT')
    window.close()
    app.processEvents()


def test_metric_preparation_keeps_extra_cameras_without_inventing_intrinsics(tmp_path, monkeypatch):
    import hashlib
    import json
    from uwa_cell_control.object_digitization import prepare_capture
    from uwa_cell_description import configuration
    root = Path(__file__).parents[2]
    layout = yaml.safe_load((root / 'uwa_cell_description/config/cell_layout.yaml').read_text())
    reference = reference_board(layout, 'right')
    board = MobileBoard(reference)
    image = board.board.generateImage((1400, 1000))
    image = cv2.copyMakeBorder(image, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
    capture = tmp_path / 'set_001'
    capture.mkdir()
    profile = {'sha256': 'test-profile-sha', 'profile_id': 'test-profile', 'robots': {'right_front': {
        'camera': {'image_size': [1480, 1080], 'focus': 435,
                   'camera_matrix': [[1000., 0, 740.], [0, 1000., 540.], [0, 0, 1.]], 'distortion': [0.] * 5},
        'quality_status': {'intrinsics': 'passed'}}}}
    layout['calibration'] = profile
    monkeypatch.setattr(configuration, 'load_layout', lambda: layout)
    cameras = {name: {'success': True} for name in ['left_front', 'right_front', 'right_rear']}
    manifest = dict(all_captured=True, cameras=cameras, board=reference, stationary_set_confirmed=True)
    (capture / 'manifest.json').write_text(json.dumps(manifest))
    (tmp_path / 'calibration_context.json').write_text(json.dumps({'profile_sha256': profile['sha256']}))
    for name in cameras:
        directory = capture / name
        directory.mkdir()
        cv2.imwrite(str(directory / 'image.jpg'), image)
        record = dict(image='image.jpg', sha256=hashlib.sha256((directory / 'image.jpg').read_bytes()).hexdigest(),
                      settings_before={'focusAuto': False, 'focus': 435})
        (directory / 'record.json').write_text(json.dumps(record))
    models = prepare_capture(capture, tmp_path / 'prepared')
    assert set(models) == set(cameras) and models['right_front']['metric_usable']
    assert not models['left_front']['metric_usable'] and not models['right_rear']['metric_usable']
    assert 'K' not in models['left_front'] and 'K' not in models['right_rear']
    manifest['stationary_set_confirmed'] = False
    (capture / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='stationary'):
        prepare_capture(capture, tmp_path / 'invalid')


def test_dual_reference_detector_keeps_each_board_identity(tmp_path):
    raw = yaml.safe_load((Path(__file__).parents[2] / 'uwa_cell_description/config/cell_layout.yaml').read_text())
    primary = reference_board(raw, 'right')
    primary['alternate_boards'] = [reference_board(raw, 'left')]
    detector = MobileBoard(primary)
    for table in ['left', 'right']:
        board = MobileBoard(reference_board(raw, table))
        image = board.board.generateImage((1400, 1000))
        image = cv2.copyMakeBorder(image, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
        obs, _ = detector.observe(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR))
        assert obs['full'] and obs['board_id'] == table + '_table_board'


def test_velocity_violation_cannot_be_hidden_by_matching_endpoint_positions():
    audit = StationarityAudit({'a': list('abcdef')})
    for t in np.arange(0, 1.01, .05):
        audit.receive('a', np.zeros(6), np.zeros(6), float(t))
    audit.arm(1.)
    audit.receive('a', np.zeros(6), [.1, 0, 0, 0, 0, 0], 1.05)
    assert not audit.summary()['stationarity_confirmed']


def test_camera_failure_before_directory_creation_preserves_set_and_releases_busy(tmp_path):
    r, calls = rig(tmp_path)
    r.cameras, r.wrist_cameras, r.audit_stationarity = FIVE_CAMERAS, FIVE_CAMERAS[:-1], True
    original = r.capture_one
    def early_failure(name, directory, native):
        if name == 'left_rear':
            raise RuntimeError('Camera activity lock unavailable')
        return original(name, directory, native)
    r.capture_one = early_failure
    r.capture_monitor = lambda directory: SimpleNamespace(wait_still=lambda: None,
        finish=lambda: dict(stationarity_confirmed=True,
            reference_positions={name: [0.] * 6 for name in FIVE_CAMERAS[:-1]}))
    result = r.capture_all()
    assert not result['all_captured'] and not r.busy.locked()
    assert Path(result['directory'], 'left_rear/record.json').exists()
    assert result['cameras']['right_front']['success']

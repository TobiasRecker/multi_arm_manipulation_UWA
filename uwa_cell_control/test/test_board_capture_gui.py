"""Operator feedback: click acknowledgement, stale images, saved-vs-live states."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import hashlib
import time
from types import SimpleNamespace

from python_qt_binding import QtWidgets
from uwa_cell_control.board_capture_gui import Window, Worker
from uwa_cell_control.board_capture import CAMERAS


def test_gui_acknowledges_click_and_never_calls_snapshots_current(tmp_path, monkeypatch):
    from test_board_capture import config, board_image
    import cv2
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(Worker, 'start', lambda self: None)
    rig = SimpleNamespace(board_config=config(), session=tmp_path)
    window = Window(rig)
    jpeg = cv2.imencode('.jpg', board_image())[1].tobytes()
    observation = dict(usable=True, full=True, status='FULL BOARD', corners=24,
                       marker_ids=list(range(75, 92)), image_size=[1400, 1000])
    meta = dict(received=time.time(), observation=observation,
                payload_sha256=hashlib.sha256(jpeg).hexdigest(), kind='HTTP PREVIEW')
    for name in CAMERAS:
        window.on_frame(name, jpeg, dict(meta))
    assert window.overall.text().startswith('ALL THREE')
    window.on_frame('oak4', jpeg, dict(meta, kind='SAVED SNAPSHOT'))
    assert not window.overall.text().startswith('ALL THREE')
    window.on_frame('oak4', jpeg, dict(meta, received=time.time() - 20))
    assert 'STALE' in window.states['oak4'].text()
    window.capture.click()
    assert 'RECEIVED' in window.action.text() and window.busy
    assert not window.capture.isEnabled()
    assert window.worker.commands.get_nowait() == ('capture', True)
    window.close()
    app.processEvents()


def test_capture_progress_and_persistent_session_counts(tmp_path, monkeypatch):
    import json
    from test_board_capture import config
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(Worker, 'start', lambda self: None)
    rig = SimpleNamespace(board_config=config(), session=tmp_path)
    window = Window(rig)
    window.take()
    directory = tmp_path / 'set_120000'
    (directory / 'oak4').mkdir(parents=True)
    (directory / 'oak4' / 'record.json').write_text(json.dumps({'success': True}))
    window.refresh()
    assert 'RUNNING' in window.capture_state.text()
    assert '1/3 photos saved' in window.capture_state.text()
    assert window.progress.value() < window.progress.maximum()
    records = {name: dict(success=True, observation=dict(corners=24)) for name in CAMERAS}
    report = dict(directory=str(directory), all_captured=True, all_usable=True,
                  stationary_set_confirmed=True, cameras=records)
    window.on_result(report)
    window.on_message('LIVE · Preview resumed')
    assert window.capture_state.text().startswith('DONE')
    assert '1 complete sets · 1 usable sets · 3 saved photos' in window.totals.text()
    assert 'LAST CAPTURE · Set 1 · DONE' in window.last_result.text()
    # Re-delivery must not double count a completed set.
    window.on_result(report)
    assert '1 complete sets' in window.totals.text()
    window.on_result(dict(report, directory=str(tmp_path / 'set_120100'),
                          stationary_set_confirmed=False))
    assert '2 complete sets · 1 usable sets · 6 saved photos' in window.totals.text()
    assert window.capture_state.text().startswith('FAILED')
    window.on_message('PAUSED · Preview released')
    assert 'FAILED STATIONARITY AUDIT' in window.last_result.toolTip()
    window.take()
    window.on_finished()
    assert not window.busy and not window.capture.isEnabled()
    window.close()
    app.processEvents()


def test_five_live_images_do_not_expand_the_grid(tmp_path, monkeypatch):
    from test_board_capture import config, board_image
    from uwa_cell_control.board_capture import FIVE_CAMERAS
    import cv2
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(Worker, 'start', lambda self: None)
    rig = SimpleNamespace(board_config=config(), session=tmp_path, cameras=FIVE_CAMERAS)
    window = Window(rig)
    window.resize(1700, 1020)
    window.show()
    app.processEvents()
    jpeg = cv2.imencode('.jpg', board_image())[1].tobytes()
    meta = dict(received=time.time(), observation=dict(full=True, status='FULL BOARD',
        corners=24, marker_ids=list(range(75, 92)), image_size=[1400, 1000]),
        payload_sha256='frame', kind='HTTP PREVIEW')
    for _ in range(4):
        for name in FIVE_CAMERAS:
            window.on_frame(name, jpeg, dict(meta))
        app.processEvents()
    scroll = window.findChild(QtWidgets.QScrollArea)
    assert scroll.verticalScrollBar().maximum() == 0
    assert window.labels['oak4'].height() >= 145
    window.close()
    app.processEvents()

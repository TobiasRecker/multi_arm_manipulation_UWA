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

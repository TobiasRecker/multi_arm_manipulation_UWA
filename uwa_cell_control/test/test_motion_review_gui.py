"""Motion review never sends power commands in mock mode and uses the exact playable revision."""
import base64
import hashlib
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'uwa_cell_tasks'))

import numpy as np
import pytest
from PySide6 import QtCore, QtGui, QtWidgets
from motion_review_view import Timeline, Track
from ur_power_gui import Window
from uwa_cell_tasks.motion_review import ReviewStore, START_PERCENT


def track(name, distance, seconds):
    def point(t, value):
        return dict(time=t, positions=[value], velocities=[0.], accelerations=[0.])
    return dict(joint_names=[name], duration_s=seconds, points=[point(0., 0.), point(seconds, distance)])


def test_playback_uses_simultaneous_controller_quintics_and_holds():
    first = track('front_q', 1., 2.)
    rear = track('rear_q', 2., 1.)
    end = track('next_q', 1., 1.)
    preview = dict(start={'front_q': 0., 'rear_q': 0., 'next_q': 0., 'other_q': 2.},
        groups=[dict(phase='approach', arms=['front', 'rear'], trajectories=dict(front=first, rear=rear)),
                dict(phase='entry', arms=['next'], trajectories=dict(next=end))], duration_s=3.)
    timeline = Timeline(preview)
    phase, _, pose = timeline.at(.5)
    assert phase == 'approach'
    assert pose == pytest.approx(dict(front_q=.103515625, rear_q=1., next_q=0., other_q=2.))
    assert timeline.at(1.5)[2]['rear_q'] == 2.
    phase, _, pose = timeline.at(2.5)
    assert phase == 'entry' and pose == pytest.approx(dict(front_q=1., rear_q=2., next_q=.5, other_q=2.))
    first['points'][0]['velocities'] = [.1]
    first['points'][-1]['accelerations'] = [-.2]
    from scipy.interpolate import BPoly
    reference = BPoly.from_derivatives([0, 2], [[0,.1,0], [1,0,-.2]])
    actual = Track(first)
    for t in np.linspace(0, 2, 11):
        assert actual.at(t)[0] == pytest.approx(reference(t))
    with pytest.raises(ValueError, match='Playback time'):
        Timeline(dict(preview, duration_s=1.))


def test_mock_contact_photo_decision_and_quit(tmp_path, monkeypatch):
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, 'isSystemTrayAvailable', lambda: False)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    store = ReviewStore(tmp_path)
    image = QtGui.QImage(8, 8, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor('white'))
    buf = QtCore.QBuffer()
    buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buf, 'PNG')
    raw = bytes(buf.data())
    capture = hashlib.sha256(raw).hexdigest()
    photo = dict(mime_type='image/png', data_base64=base64.b64encode(raw).decode(),
                 original_sha256=capture, display_sha256=capture)
    meta = dict(task='carton_supported_grasp', stage='contact', risk='medium', reason='Mock contact',
                summary='Review the carton', components=['test'], arms=['right_rear','right_front'],
                duration_s=0., speed_percent=START_PERCENT, capture_sha256=capture)
    ticket = store.submit('photo', meta, dict(image=photo))
    window = Window(review_mock=tmp_path)
    window.show()
    panel = window.review

    def wait(condition):
        until = time.monotonic() + 5
        while not condition() and time.monotonic() < until:
            app.processEvents()
            time.sleep(.01)
        assert condition(), panel.feedback.text()

    try:
        wait(lambda: panel.export is not None)
        assert panel.picture.isVisible() and panel.key[0] == ticket
        assert not panel.decisions['approve'].isEnabled() and panel.decisions['reject'].isEnabled()
        assert not panel.save_speed.isEnabled()
        assert not window.start.isVisible() and not window.refresh_timer.isActive()
        panel.area_button.click()
        wait(lambda: panel.status['area_released'])
        assert panel.decisions['approve'].isEnabled()
        # A decodable image from an older revision cannot authorize this contact.
        current = panel.export
        panel.clear_export()
        panel.render_export(dict(current, sha256='stale'))
        panel.controls()
        assert not panel.decisions['approve'].isEnabled() and panel.decisions['replan'].isEnabled()
        with pytest.raises(ValueError, match='requested capture'):
            panel.render_export(dict(current, preview=dict(image=dict(photo, original_sha256='a'*64))))
        with pytest.raises(ValueError, match='preview bytes changed'):
            panel.render_export(dict(current, preview=dict(image=dict(photo, data_base64='AAAA'))))
        with pytest.raises(ValueError, match='decode'):
            panel.render_export(dict(current, preview=dict(image=dict(photo, display_sha256=None, data_base64='AAAA'))))
        assert panel.export is None
        panel.render_export(current)
        panel.controls()
        panel.decisions['approve'].click()
        wait(lambda: panel.item['status'] == 'approved')
        assert not panel.decisions['approve'].isEnabled()
        panel.refresh()
        window.close()
        wait(lambda: not window.isVisible())
        assert not store.status()['area_released']
    finally:
        if window.isVisible():
            window.finish_quit()

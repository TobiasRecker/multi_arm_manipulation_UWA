"""Exercise warm six-camera transactions with offline camera and telemetry peers."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import time

import cv2
import pytest

from test_board_capture import board_image, config
from uwa_cell_control.board_capture import SIX_CAMERAS
from uwa_cell_control.board_capture_session import ContinuousCaptureRig


class FakeStream:
    def __init__(self, name, trigger_barrier, photo_bytes, allow_save):
        self.name = name
        self.barrier = trigger_barrier
        self.photo_bytes = photo_bytes
        self.allow_save = allow_save
        self.focus = 100
        self.starts = self.stops = self.frames = 0
        self.failure = None

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1

    def capture(self, directory, *, on_acquired):
        assert self.starts == self.stops + 1
        # A serial or deferred request will never get all six streams to this barrier.
        self.barrier.wait(timeout=3)
        if self.failure == 'before_frame':
            raise IOError('Camera disconnected before frame')
        self.frames += 1
        on_acquired()
        if self.failure == 'after_frame':
            raise IOError('Photo storage failed after frame')
        assert self.allow_save.wait(timeout=3)
        path = directory / 'image.jpg'
        path.write_bytes(self.photo_bytes)
        return path, dict(sequence=self.frames, camera_identity=self.name,
                          settings=dict(focusAuto=False, focus=self.focus),
                          sensor_controls=dict(focus_auto=0))


class FakeObserver:
    def __init__(self):
        self.commands = []

    def start(self):
        self.commands.append('start')

    def stop(self):
        self.commands.append('stop')

    def request(self, command, directory=None):
        self.commands.append(command)
        if command == 'begin':
            assert directory.is_dir()
            return dict(arms={})
        assert command == 'end'
        return dict(stationarity_confirmed=True, endpoint_after=dict(arms={}),
                    reference_positions={name: [0.] * 6 for name in SIX_CAMERAS[:4]})


def session(tmp_path):
    rig = ContinuousCaptureRig.__new__(ContinuousCaptureRig)
    rig.session = tmp_path
    rig.cameras, rig.wrist_cameras = SIX_CAMERAS, SIX_CAMERAS[:4]
    rig.board_config = config()
    rig.fixed_settings = {}
    rig.audit_stationarity = True
    rig.busy = threading.Lock()
    rig.observer = FakeObserver()
    rig.requested_monotonic = None
    rig.on_frames_acquired = None
    trigger_barrier = threading.Barrier(len(rig.cameras))
    allow_save = threading.Event()
    image = cv2.resize(board_image(), (592, 432))
    jpeg = cv2.imencode('.jpg', image)[1].tobytes()
    rig.streams = {name: FakeStream(name, trigger_barrier, jpeg, allow_save) for name in rig.cameras}
    rig.preview, rig.usb = rig.streams['oak4'], rig.streams['oak_usb']
    return rig, allow_save


def test_two_parallel_six_camera_sets_signal_before_storage_and_release_session(tmp_path):
    rig, allow_save = session(tmp_path)
    frames_received = threading.Event()
    rig.on_frames_acquired = lambda elapsed: frames_received.set()
    rig.start_streams()
    with ThreadPoolExecutor(max_workers=1) as pool:
        for expected_sequence in (1, 2):
            frames_received.clear()
            allow_save.clear()
            rig.requested_monotonic = time.monotonic()
            task = pool.submit(rig.capture_all, resume_preview=True)
            try:
                assert frames_received.wait(timeout=3)
                assert not task.done()
                assert len(list(tmp_path.glob('set_*/manifest.json'))) == expected_sequence - 1
                assert not any(stream.stops for stream in rig.streams.values())
            finally:
                allow_save.set()
            report = task.result(timeout=10)
            assert report['all_captured'] and report['all_full'] and report['stationary_set_confirmed']
            assert not report['hardware_synchronized']
            assert set(report['frame_confirmed_after_s']) == set(SIX_CAMERAS)
            assert report['all_frames_received_after_s'] == max(report['frame_confirmed_after_s'].values())
            assert {row['camera_metadata']['sequence'] for row in report['cameras'].values()} == {expected_sequence}
            assert json.loads(Path(report['directory'], 'manifest.json').read_text()) == report
    rig.stop_streams()
    assert all((stream.starts, stream.stops) == (1, 1) for stream in rig.streams.values())
    assert rig.observer.commands == ['start', 'begin', 'end', 'begin', 'end', 'stop']


@pytest.mark.parametrize('failure', ['before_frame', 'after_frame'])
def test_partial_set_distinguishes_missing_frame_from_failed_storage(tmp_path, failure):
    rig, allow_save = session(tmp_path)
    allow_save.set()
    confirmations = []
    rig.on_frames_acquired = confirmations.append
    rig.streams['oak_usb'].failure = failure
    rig.start_streams()
    try:
        report = rig.capture_all()
        assert not report['all_captured'] and not report['all_usable']
        assert sum(row['success'] for row in report['cameras'].values()) == 5
        assert report['cameras']['oak_usb']['success'] is False
        assert len(confirmations) == (1 if failure == 'after_frame' else 0)
        assert ('oak_usb' in report['frame_confirmed_after_s']) == (failure == 'after_frame')
        assert 'error' in json.loads(Path(report['directory'], 'oak_usb', 'record.json').read_text())
        assert not rig.busy.locked()
    finally:
        rig.stop_streams()
    assert rig.observer.commands == ['start', 'begin', 'end', 'stop']


def test_gui_reports_release_of_board_while_set_is_still_saving(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    from python_qt_binding import QtWidgets
    from uwa_cell_control.board_capture_gui import Window, Worker

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(Worker, 'start', lambda _worker: None)
    monkeypatch.setattr(Worker, 'isRunning', lambda _worker: True)
    triggers = []
    monkeypatch.setattr(Worker, 'trigger', lambda _worker, native, when: triggers.append((native, when)))
    rig, _ = session(tmp_path)
    window = Window(rig)
    try:
        for name in SIX_CAMERAS:
            assert not window.capture.isEnabled()
            window.worker.publish(name, rig.streams[name].photo_bytes,
                                  dict(received=time.time(), kind='LIVE NATIVE STREAM'))
        assert window.capture.isEnabled()
        window.capture.click()
        assert triggers == [(True, window.started)]
        assert 'HOLD STILL' in window.capture_state.text()
        rig.on_frames_acquired(.62)
        app.processEvents()
        assert window.busy and not window.capture.isEnabled()
        assert 'FRAMES ACQUIRED' in window.capture_state.text()
        assert '0.62' in window.capture_state.text() and 'You may move' in window.capture_state.text()
        assert 'You may move' in window.action.text()
        assert not window.reports
    finally:
        monkeypatch.setattr(Worker, 'isRunning', lambda _worker: False)
        window.close()
        app.processEvents()


def test_worker_trigger_submits_without_waiting_for_the_preview_loop(tmp_path):
    from uwa_cell_control.board_capture_gui import Worker

    rig, _ = session(tmp_path)
    called = threading.Event()
    rig.capture_all = called.set
    worker = Worker(rig)
    with ThreadPoolExecutor(max_workers=1) as worker.writer:
        when = time.monotonic()
        worker.trigger(True, when)
        assert called.wait(timeout=1)
        assert worker.capture_job.result(timeout=1) is None
    assert rig.requested_monotonic == when and worker.commands.empty()


def test_release_attempts_every_camera_and_ends_observer_after_one_close_error(tmp_path, monkeypatch):
    rig, _ = session(tmp_path)
    rig.start_streams()
    usb = rig.streams['oak_usb']

    def failed_close():
        usb.stops += 1
        raise RuntimeError('Camera release unconfirmed')

    monkeypatch.setattr(usb, 'stop', failed_close)
    with pytest.raises(RuntimeError, match='oak_usb.*release unconfirmed'):
        rig.stop_streams()
    assert all(stream.stops == 1 for stream in rig.streams.values())
    assert rig.observer.commands == ['start', 'stop']

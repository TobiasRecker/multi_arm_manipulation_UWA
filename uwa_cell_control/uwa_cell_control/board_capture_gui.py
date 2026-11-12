"""English three-camera mobile ChArUco viewer; no robot control API."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import sys
import time

import cv2
import numpy as np
from python_qt_binding import QtCore, QtGui, QtWidgets

from .board_capture import CAMERAS, CaptureRig, MobileBoard


class Worker(QtCore.QThread):
    frame = QtCore.Signal(str, bytes, object)
    message = QtCore.Signal(str)
    result = QtCore.Signal(object)
    camera_error = QtCore.Signal(str, str)

    def __init__(self, rig):
        super().__init__()
        self.rig = rig
        self.commands = queue.Queue()
        self.quit_requested = False
        self.live = True
        self.detector = MobileBoard(rig.board_config)
        self.sequences = {}

    def publish(self, name, jpeg, metadata):
        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        observation, annotated = self.detector.observe(image)
        scale = min(1., 1050 / annotated.shape[1])
        annotated = cv2.resize(annotated, None, fx=scale, fy=scale)
        preview = cv2.imencode('.jpg', annotated)[1].tobytes()
        self.frame.emit(name, preview, dict(metadata, observation=observation,
            payload_sha256=hashlib.sha256(jpeg).hexdigest()))

    def run(self):
        try:
            self.message.emit('PREPARING · Applying fixed session focus (front 435 / rear 388 / OAK 116)…')
            self.rig.lock_focus()
            self.rig.preview.start()
            self.message.emit('LIVE VIEW STARTING · Hold the mobile A4 board in the shared field of view.')
            while not self.quit_requested:
                try:
                    command, value = self.commands.get_nowait()
                except queue.Empty:
                    command, value = None, None
                if command == 'capture':
                    self.message.emit('RUNNING · Taking three photos. HOLD BOARD STILL until DONE.')
                    report = self.rig.capture_all(native=value, resume_preview=self.live and not self.quit_requested)
                    self.result.emit(report)
                    # Actual saved images, not previous preview frames.
                    for name, record in report['cameras'].items():
                        if record.get('success'):
                            path = Path(report['directory']) / name / record['image']
                            self.publish(name, path.read_bytes(), dict(received=time.time(),
                                kind='SAVED SNAPSHOT', image_size=record['observation']['image_size']))
                elif command == 'live':
                    self.live = value
                    if value:
                        self.rig.preview.start()
                    else:
                        self.rig.preview.stop()
                    self.message.emit('Live view resumed.' if value else 'PAUSED · OAK released. Displayed images are snapshots.')
                if self.quit_requested:
                    break
                if not self.live:
                    self.msleep(100)
                    continue
                for name in CAMERAS:
                    if self.quit_requested or not self.commands.empty():
                        break
                    try:
                        if name == 'oak4':
                            jpeg, meta = self.rig.preview.read()
                            if meta['sequence'] == self.sequences.get(name):
                                continue
                            self.sequences[name] = meta['sequence']
                            meta['kind'] = 'LIVE SDK PREVIEW'
                        else:
                            camera = self.rig.wrist(name)
                            # /current.jpg can cache a previous view. Request a new
                            # image without asking AF/AE to change optical settings.
                            camera.trigger()
                            jpeg = camera.image()
                            meta = dict(received=time.time(), kind='HTTP PREVIEW',
                                timestamp_kind='host receipt; exposure timestamp unavailable')
                        self.publish(name, jpeg, meta)
                    except Exception as error:
                        self.camera_error.emit(name, str(error))
                self.msleep(200)
        except Exception as error:
            self.message.emit('FAILED · ' + str(error))
        finally:
            try:
                self.rig.preview.stop()
            except Exception as error:
                self.message.emit('Preview shutdown: ' + str(error))
            try:
                self.rig.restore_focus()
            except Exception as error:
                self.message.emit('FAILED · Focus restoration: ' + str(error))


class Window(QtWidgets.QMainWindow):
    def __init__(self, rig):
        super().__init__()
        self.rig = rig
        self.data, self.pixmaps, self.errors, self.changes = {}, {}, {}, {}
        self.busy = self.closing = False
        self.setWindowTitle('UWA Camera Capture · Mobile A4 Board')
        self.resize(1470, 820)
        self.setStyleSheet('QMainWindow,QWidget {background:#171c24;color:#ffffff;} '
            'QLabel {font-size:15px;} QPushButton {background:#f0f3f7;color:#111827;'
            'border:3px solid white;border-radius:5px;padding:12px;font-size:18px;font-weight:bold;}'
            'QPushButton:pressed {background:#ffe066;color:#000;border:5px solid #000;}'
            'QPushButton:disabled {background:#707b8b;color:#fff;border-color:#aab4c4;}'
            'QComboBox {background:white;color:#111827;font-size:16px;padding:8px;}')
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)
        title = QtWidgets.QLabel('MOBILE A4 · ChArUco IDs 75–91 · 38 mm squares · Camera controls only')
        title.setStyleSheet('font-size:21px;font-weight:bold;')
        layout.addWidget(title)
        self.overall = QtWidgets.QLabel('WAITING FOR THREE CAMERAS')
        self.overall.setMinimumHeight(48)
        layout.addWidget(self.overall)
        row = QtWidgets.QHBoxLayout()
        self.labels, self.states, self.details = {}, {}, {}
        for name in CAMERAS:
            column = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(name.replace('_', ' ').upper())
            label.setStyleSheet('font-size:20px;font-weight:bold;')
            column.addWidget(label)
            self.labels[name] = QtWidgets.QLabel('Waiting for camera…')
            self.labels[name].setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.labels[name].setMinimumSize(300, 320)
            self.labels[name].setStyleSheet('background:#000;border:2px solid #cbd5e1;')
            column.addWidget(self.labels[name], 1)
            self.states[name] = QtWidgets.QLabel('WAITING')
            self.states[name].setMinimumHeight(42)
            column.addWidget(self.states[name])
            self.details[name] = QtWidgets.QLabel('No image received')
            self.details[name].setWordWrap(True)
            self.details[name].setMinimumHeight(90)
            column.addWidget(self.details[name])
            row.addLayout(column, 1)
        layout.addLayout(row, 1)
        self.action = QtWidgets.QLabel('CONNECTING · Starting camera previews…')
        self.action.setWordWrap(True)
        self.action.setMinimumHeight(65)
        self.action.setStyleSheet('background:#fff;color:#111;font-size:19px;font-weight:bold;padding:8px;')
        layout.addWidget(self.action)
        controls = QtWidgets.QHBoxLayout()
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(['Native photos: Wrist 2592×1944 + OAK 8000×6000',
                            'Quick photos: Wrist 640×480 + OAK 8000×6000'])
        controls.addWidget(self.mode)
        self.capture = QtWidgets.QPushButton('CAPTURE ALL THREE')
        self.capture.clicked.connect(self.take)
        controls.addWidget(self.capture)
        self.pause = QtWidgets.QPushButton('Pause live view')
        self.pause.setCheckable(True)
        self.pause.clicked.connect(self.toggle_live)
        controls.addWidget(self.pause)
        folder = QtWidgets.QPushButton('Open photos')
        folder.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(rig.session))))
        controls.addWidget(folder)
        layout.addLayout(controls)
        note = QtWidgets.QLabel('Hold the board still for the ENTIRE capture (up to ~1 minute). '
            'Photos are NOT exposure-synchronized. Native mode briefly pauses wrist video. '
            'Focus is held for this session (OAK: 116). Intrinsics must match focus and resolution. '
            'Board detection is not a calibration quality check.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.worker = Worker(rig)
        self.worker.frame.connect(self.on_frame)
        self.worker.message.connect(self.action.setText)
        self.worker.camera_error.connect(self.on_error)
        self.worker.result.connect(self.on_result)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(250)

    def take(self):
        self.busy = True
        self.started = time.monotonic()
        self.capture.setEnabled(False)
        self.pause.setEnabled(False)
        self.mode.setEnabled(False)
        self.action.setText('RECEIVED · Capture all three requested. HOLD BOARD STILL.')
        self.worker.commands.put(('capture', self.mode.currentIndex() == 0))

    def toggle_live(self, checked):
        self.action.setText('RECEIVED · Pausing live view…' if checked else 'RECEIVED · Resuming live view…')
        self.pause.setText('Resume live view' if checked else 'Pause live view')
        self.worker.commands.put(('live', not checked))

    def on_frame(self, name, jpeg, metadata):
        previous = self.data.get(name)
        if not previous or previous['payload_sha256'] != metadata['payload_sha256']:
            self.changes[name] = time.time()
        self.data[name] = metadata
        self.errors.pop(name, None)
        self.pixmaps[name] = QtGui.QPixmap.fromImage(QtGui.QImage.fromData(jpeg))
        self.refresh()

    def on_error(self, name, text):
        self.errors[name] = text

    def on_result(self, report):
        self.busy = False
        self.capture.setEnabled(True)
        self.pause.setEnabled(True)
        self.mode.setEnabled(True)
        if report['all_captured']:
            counts = ', '.join(name + ': ' + str(r['observation']['corners']) + '/24'
                               for name, r in report['cameras'].items())
            text = 'DONE · Three photos saved. ' + counts
            if not report['all_usable']:
                text += ' · INCOMPLETE SHARED BOARD VIEW'
        else:
            text = 'FAILED / PARTIAL SET · ' + '; '.join(name + ': ' + r.get('error', 'saved')[-250:]
                for name, r in report['cameras'].items())
            text += ' ' + report.get('error', '')
        self.action.setText(text + '\n' + report['directory'])
        (self.rig.session / 'latest-set.txt').write_text(report['directory'] + '\n')

    def refresh(self):
        current = []
        for name in CAMERAS:
            meta = self.data.get(name)
            if not meta:
                text, color = 'WAITING / NO IMAGE', '#ffe066'
                detail = self.errors.get(name, 'Connecting…')
            else:
                age = max(0, time.time() - meta['received'])
                obs = meta['observation']
                stale_payload = time.time() - self.changes.get(name, 0) > 15
                fresh = age < 8 and not self.pause.isChecked() and not self.busy and not self.errors.get(name)
                fresh = fresh and not stale_payload and meta['kind'] != 'SAVED SNAPSHOT'
                if fresh:
                    text = obs['status'] + ' · ' + str(obs['corners']) + '/24'
                    color = '#8effa2' if obs['full'] else '#ffe066' if obs['corners'] else '#ffb4b4'
                    # Low-bandwidth wrist previews can have fewer interpolated
                    # corners than their native photos. Visibility is not the
                    # native dataset's stricter >=12-corner quality threshold.
                    current.append(obs['corners'] >= 4)
                else:
                    text, color = ('PAUSED / SNAPSHOT' if self.pause.isChecked() or self.busy or
                                   meta['kind'] == 'SAVED SNAPSHOT' else 'STALE / NO CURRENT IMAGE'), '#ffe066'
                    current.append(False)
                size = obs['image_size']
                detail = f"{meta['kind']} · {size[0]}×{size[1]} · received {age:.1f} s ago\n"
                detail += self.errors.get(name, f"Mobile markers: {len(obs['marker_ids'])}/17 · corners: {obs['corners']}/24")
                if stale_payload:
                    detail += '\nUnchanged payload >15 s; freshness unconfirmed.'
                pixmap = self.pixmaps[name]
                self.labels[name].setPixmap(pixmap.scaled(self.labels[name].size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            self.states[name].setText(text)
            self.states[name].setStyleSheet(f'background:{color};color:#000;font-size:17px;font-weight:bold;padding:5px;')
            self.details[name].setText(detail)
        ready = len(current) == 3 and all(current)
        self.overall.setText('ALL THREE DETECT MOBILE BOARD · Capture to check native detail (hold still)' if ready else
            'CHECK SHARED VIEW · Show the mobile A4 board to all three cameras; full board is best')
        self.overall.setStyleSheet('background:' + ('#8effa2' if ready else '#ffe066') +
            ';color:#000;font-size:19px;font-weight:bold;padding:8px;')
        if self.busy:
            self.capture.setText(f'CAPTURING · {time.monotonic() - self.started:.0f} s')
        else:
            self.capture.setText('CAPTURE ALL THREE')

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.closing = True
            self.worker.quit_requested = True
            self.action.setText('CLOSING · Finishing any active capture and restoring camera services. Please wait.')
            self.capture.setEnabled(False)
            self.pause.setEnabled(False)
            event.ignore()
        else:
            event.accept()

    def on_finished(self):
        if self.closing:
            self.close()
        else:
            self.capture.setEnabled(False)
            self.pause.setEnabled(False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, default=Path(os.environ.get('UWA_WS', Path.home() / 'UWA_ws')))
    p.add_argument('--output', type=Path)
    p.add_argument('--capture-only', action='store_true')
    p.add_argument('--quick', action='store_true', help='Capture-only: use wrist VGA rather than native HD')
    args = p.parse_args()
    rig = CaptureRig(args.workspace, args.output)
    if args.capture_only:
        try:
            rig.lock_focus()
            report = rig.capture_all(native=not args.quick)
        finally:
            rig.restore_focus()
        print(json.dumps(report, indent=2))
        return 0 if report['all_captured'] else 1
    app = QtWidgets.QApplication(sys.argv[:1])
    window = Window(rig)
    available = app.primaryScreen().availableGeometry()
    window.resize(min(1470, available.width() - 30), min(820, available.height() - 70))
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

"""English multi-camera ChArUco viewer; no robot control API."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import queue
import sqlite3
import sys
import time

import cv2
import numpy as np
from python_qt_binding import QtCore, QtGui, QtWidgets

from .board_capture import CAMERAS, FIVE_CAMERAS, SIX_CAMERAS, CaptureRig, MobileBoard, start_previews, stop_previews


class Worker(QtCore.QThread):
    frame = QtCore.Signal(str, bytes, object)
    message = QtCore.Signal(str)
    result = QtCore.Signal(object)
    frames_acquired = QtCore.Signal(float)
    camera_error = QtCore.Signal(str, str)

    def __init__(self, rig):
        super().__init__()
        self.rig = rig
        self.commands = queue.Queue()
        self.quit_requested = False
        self.live = True
        self.detector = MobileBoard(rig.board_config)
        self.sequences = {}
        self.wrist_usage = ExitStack()
        self.continuous = getattr(rig, 'continuous', False)
        self.capture_job = None
        self.writer = None
        if self.continuous:
            rig.on_frames_acquired = self.frames_acquired.emit

    def wrist_live(self, active):
        self.wrist_usage.close()
        if active:
            try:
                for name in getattr(self.rig, 'wrist_cameras', CAMERAS[:-1]):
                    camera = self.rig.wrist(name)
                    if hasattr(camera, 'activity'):
                        self.wrist_usage.enter_context(camera.activity())
            except BaseException:
                self.wrist_usage.close()
                raise

    def publish(self, name, jpeg, metadata):
        decode = cv2.IMREAD_REDUCED_COLOR_2 if self.continuous and name in self.rig.wrist_cameras else cv2.IMREAD_COLOR
        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), decode)
        observation, annotated = self.detector.observe(image)
        if name == 'oak_usb':
            annotated = cv2.rotate(annotated, cv2.ROTATE_180)
            metadata = dict(metadata, display_rotation_deg=180)
        scale = min(1., 1050 / annotated.shape[1])
        annotated = cv2.resize(annotated, None, fx=scale, fy=scale)
        preview = cv2.imencode('.jpg', annotated)[1].tobytes()
        self.frame.emit(name, preview, dict(metadata, observation=observation,
            payload_sha256=hashlib.sha256(jpeg).hexdigest()))

    def run(self):
        if self.continuous:
            self.run_continuous()
            return
        try:
            self.message.emit('PREPARING · Applying the selected fixed-focus profile…')
            self.wrist_live(True)
            self.rig.lock_focus()
            start_previews(self.rig)
            self.message.emit('LIVE VIEW STARTING · Hold the object and reference board still.')
            while not self.quit_requested:
                try:
                    command, value = self.commands.get_nowait()
                except queue.Empty:
                    command, value = None, None
                if command == 'capture':
                    self.message.emit(f'RUNNING · Taking {len(getattr(self.rig, "cameras", CAMERAS))} photos. HOLD STILL until DONE.')
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
                    self.wrist_live(value)
                    if value:
                        start_previews(self.rig)
                    else:
                        stop_previews(self.rig)
                    self.message.emit('LIVE · Wrist LEDs active while viewing.' if value else
                        'PAUSED · Wrist LEDs released (other viewers may keep them on). OAK released. Images are snapshots.')
                if self.quit_requested:
                    break
                if not self.live:
                    self.msleep(100)
                    continue
                for name in getattr(self.rig, 'cameras', CAMERAS):
                    if self.quit_requested or not self.commands.empty():
                        break
                    try:
                        if name in ('oak4','oak_usb'):
                            preview = getattr(self.rig,'previews',{'oak4':self.rig.preview})[name]
                            jpeg, meta = preview.read()
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
                stop_previews(self.rig)
            except Exception as error:
                self.message.emit('Preview shutdown: ' + str(error))
            try:
                self.rig.restore_focus()
            except Exception as error:
                self.message.emit('FAILED · Focus restoration: ' + str(error))
            try:
                self.wrist_usage.close()
            except Exception as error:
                self.message.emit('FAILED · Wrist LEDs could not be switched off: ' + str(error))

    def run_continuous(self):
        try:
            self.message.emit('PREPARING · Starting six native camera streams…')
            self.rig.lock_focus()
            self.rig.start_streams()
            with ThreadPoolExecutor(max_workers=1) as writer:
                self.writer = writer
                while not self.quit_requested:
                    if self.capture_job is not None and self.capture_job.done():
                        finished = self.capture_job
                        self.capture_job = None
                        self.result.emit(finished.result())
                    try:
                        command, value = self.commands.get_nowait()
                    except queue.Empty:
                        command, value = None, None
                    if command == 'live' and self.capture_job is None:
                        self.live = value
                        self.sequences.clear()
                        if value:
                            self.rig.lock_focus()
                            self.rig.start_streams()
                            self.message.emit('PREPARING · Waiting for six live camera streams…')
                        else:
                            self.rig.stop_streams()
                            self.message.emit('PAUSED · Cameras released. Resume to take photos.')
                    if self.live:
                        for name, stream in self.rig.streams.items():
                            if self.quit_requested or not self.commands.empty():
                                break
                            try:
                                jpeg, meta = stream.read()
                                sequence = meta['device_sequence'] if name in self.rig.wrist_cameras else meta['sequence']
                                if sequence == self.sequences.get(name):
                                    continue
                                self.sequences[name] = sequence
                                self.publish(name, jpeg, dict(meta, kind='LIVE NATIVE STREAM'))
                            except Exception as error:
                                self.camera_error.emit(name, str(error))
                    self.msleep(20)
                if self.capture_job is not None:
                    self.result.emit(self.capture_job.result())
                self.writer = None
        except Exception as error:
            self.message.emit('FAILED · ' + str(error))
        finally:
            try:
                self.rig.stop_streams()
            except Exception as error:
                self.message.emit('FAILED · Releasing camera streams: ' + str(error))
            try:
                self.rig.restore_focus()
            except Exception as error:
                self.message.emit('FAILED · Camera settings: ' + str(error))

    def trigger(self, native, click_time):
        if self.continuous:
            # Dispatch from the button immediately even during preview decoding.
            self.rig.requested_monotonic = click_time
            self.capture_job = self.writer.submit(self.rig.capture_all)
        else:
            self.commands.put(('capture', native))


class Window(QtWidgets.QMainWindow):
    def __init__(self, rig):
        super().__init__()
        self.rig = rig
        self.continuous = getattr(rig, 'continuous', False)
        self.frames_elapsed = None
        self.camera_names = getattr(rig, 'cameras', CAMERAS)
        self.count_label = {3: 'THREE', 5: 'FIVE', 6: 'SIX'}.get(len(self.camera_names), str(len(self.camera_names)))
        self.data, self.pixmaps, self.errors, self.changes = {}, {}, {}, {}
        self.busy = self.closing = False
        self.reports = {}
        self.capture_directory = None
        self.previous_sets = set()
        self.setWindowTitle('UWA Camera Capture · ' + rig.board_config['board_id'])
        self.resize(1470, 1020 if len(self.camera_names) > 3 else 900)
        self.setStyleSheet('QMainWindow,QWidget {background:#171c24;color:#ffffff;} '
            'QLabel {font-size:15px;} QPushButton {background:#f0f3f7;color:#111827;'
            'border:3px solid white;border-radius:5px;padding:12px;font-size:18px;font-weight:bold;}'
            'QPushButton:pressed {background:#ffe066;color:#000;border:5px solid #000;}'
            'QPushButton:disabled {background:#707b8b;color:#fff;border-color:#aab4c4;}'
            'QComboBox {background:white;color:#111827;font-size:16px;padding:8px;}')
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)
        board = rig.board_config
        references = [board] + board.get('alternate_boards', [])
        identity = ' / '.join(item['board_id'] for item in references)
        ids = ' / '.join(f"{min(item['marker_ids'])}–{max(item['marker_ids'])}" for item in references)
        title = QtWidgets.QLabel(f"{identity} · IDs {ids} · "
            f"{board['square_length'] * 1000:g} mm squares · Camera controls only")
        title.setStyleSheet('font-size:21px;font-weight:bold;')
        layout.addWidget(title)
        self.capture_state = QtWidgets.QLabel('CONNECTING · No capture running')
        self.capture_state.setWordWrap(True)
        self.capture_state.setStyleSheet('background:#fff;color:#000;font-size:26px;font-weight:bold;padding:10px;border:3px solid #fff;')
        layout.addWidget(self.capture_state)
        self.totals = QtWidgets.QLabel()
        self.totals.setStyleSheet('font-size:20px;font-weight:bold;padding:5px;')
        layout.addWidget(self.totals)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, len(self.camera_names) + 1)
        self.progress.setValue(0)
        self.progress.setFormat('No capture running')
        self.progress.setMinimumHeight(30)
        self.progress.setStyleSheet('QProgressBar {background:#fff;color:#000;border:2px solid white;text-align:center;font-weight:bold;} QProgressBar::chunk {background:#59bfff;}')
        capture_summary = QtWidgets.QHBoxLayout()
        capture_summary.addWidget(self.progress, 1)
        self.last_result = QtWidgets.QLabel('LAST CAPTURE · None in this session')
        self.last_result.setWordWrap(True)
        self.last_result.setStyleSheet('background:#fff;color:#000;font-size:17px;font-weight:bold;padding:7px;')
        capture_summary.addWidget(self.last_result, 2)
        layout.addLayout(capture_summary)
        self.gemini_status = QtWidgets.QLabel()
        self.gemini_status.setWordWrap(True)
        self.gemini_status.setStyleSheet('background:#fff;color:#111;font-size:16px;font-weight:bold;padding:4px;')
        self.gemini_status.setVisible(hasattr(rig, 'gemini_registration'))
        self.gemini_status.setText(getattr(rig, 'gemini_registration', ''))
        self.next_gemini_check = 0.
        layout.addWidget(self.gemini_status)
        self.update_totals()
        self.overall = QtWidgets.QLabel('WAITING FOR ' + self.count_label + ' CAMERAS')
        self.overall.setMinimumHeight(34)
        layout.addWidget(self.overall)
        row = QtWidgets.QGridLayout()
        self.labels, self.states, self.details = {}, {}, {}
        for index, name in enumerate(self.camera_names):
            column = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel('USB OAK · N100 · DISPLAY 180°' if name == 'oak_usb' else name.replace('_', ' ').upper())
            label.setStyleSheet('font-size:20px;font-weight:bold;')
            column.addWidget(label)
            self.labels[name] = QtWidgets.QLabel('Waiting for camera…')
            self.labels[name].setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.labels[name].setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,
                                           QtWidgets.QSizePolicy.Policy.Ignored)
            self.labels[name].setMinimumSize(240, 145 if len(self.camera_names) > 3 else 320)
            self.labels[name].setStyleSheet('background:#000;border:2px solid #cbd5e1;')
            column.addWidget(self.labels[name], 1)
            self.states[name] = QtWidgets.QLabel('WAITING')
            self.states[name].setMinimumHeight(42)
            column.addWidget(self.states[name])
            self.details[name] = QtWidgets.QLabel('No image received')
            self.details[name].setWordWrap(True)
            self.details[name].setMinimumHeight(50 if len(self.camera_names) > 3 else 90)
            column.addWidget(self.details[name])
            row.addLayout(column, index // 3, index % 3)
        if len(self.camera_names) > 3:
            camera_area = QtWidgets.QWidget()
            camera_area.setLayout(row)
            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(camera_area)
            layout.addWidget(scroll, 1)
        else:
            layout.addLayout(row, 1)
        self.action = QtWidgets.QLabel('CONNECTING · Starting camera previews…')
        self.action.setWordWrap(True)
        self.action.setMinimumHeight(45)
        self.action.setStyleSheet('background:#fff;color:#111;font-size:19px;font-weight:bold;padding:8px;')
        layout.addWidget(self.action)
        controls = QtWidgets.QHBoxLayout()
        self.mode = QtWidgets.QComboBox()
        self.mode.addItem('Native photos: Wrist 2592×1944 + OAK 8000×6000')
        if not self.continuous:
            self.mode.addItem('Quick photos: Wrist 640×480 + OAK 8000×6000')
        if 'oak_usb' in self.camera_names:
            for index in range(self.mode.count()):
                self.mode.setItemText(index,self.mode.itemText(index)+' + USB OAK 4056×3040')
        controls.addWidget(self.mode)
        self.capture = QtWidgets.QPushButton('CAPTURE ALL ' + self.count_label)
        self.capture.setEnabled(not self.continuous)
        self.capture.clicked.connect(self.take)
        controls.addWidget(self.capture)
        self.pause = QtWidgets.QPushButton('Release cameras' if self.continuous else 'Pause live view')
        self.pause.setCheckable(True)
        self.pause.clicked.connect(self.toggle_live)
        controls.addWidget(self.pause)
        folder = QtWidgets.QPushButton('Open photos')
        folder.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(rig.session))))
        controls.addWidget(folder)
        layout.addLayout(controls)
        note = QtWidgets.QLabel('Hold the board still for the ENTIRE capture (up to ~1 minute). '
            'Photos are NOT exposure-synchronized. Native mode briefly pauses wrist video. '
            'Focus is held for this session. Intrinsics must match focus and resolution. '
            'Board detection is not a calibration quality check.' +
            (' Turn the board toward different camera pairs between captures. USB display is rotated; raw photos are unchanged.'
             if 'oak_usb' in self.camera_names else ''))
        note.setWordWrap(True)
        if self.continuous:
            note.setText('Hold the board until FRAMES ACQUIRED. You can then move it while the photos are saved. '
                         'Each camera captures its next native frame on request, using its own clock.')
        layout.addWidget(note)
        self.worker = Worker(rig)
        self.worker.frame.connect(self.on_frame)
        self.worker.message.connect(self.on_message)
        self.worker.camera_error.connect(self.on_error)
        self.worker.result.connect(self.on_result)
        self.worker.frames_acquired.connect(self.on_frames_acquired)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(250)

    def take(self):
        if self.busy or self.closing:
            return
        self.busy = True
        self.frames_elapsed = None
        self.started = time.monotonic()
        self.previous_sets = set(self.rig.session.glob('set_*'))
        self.capture_directory = None
        self.capture_state.setText('RECEIVED · HOLD STILL · Capture requested')
        self.capture_state.setStyleSheet('background:#ffe066;color:#000;font-size:26px;font-weight:bold;padding:10px;border:3px solid #fff;')
        self.progress.setValue(0)
        self.progress.setFormat('Starting capture · HOLD STILL')
        self.capture.setEnabled(False)
        self.pause.setEnabled(False)
        self.mode.setEnabled(False)
        self.action.setText('RECEIVED · Capture all ' + self.count_label.lower() + ' requested. HOLD STILL.')
        self.worker.trigger(self.mode.currentIndex() == 0, self.started)

    def on_frames_acquired(self, elapsed):
        self.frames_elapsed = elapsed
        self.action.setText('All six frames acquired. You may move the board while the photos are saved.')
        self.capture_state.setStyleSheet('background:#8effa2;color:#000;font-size:26px;font-weight:bold;padding:10px;border:3px solid #fff;')
        self.refresh()

    def on_message(self, text):
        self.action.setText(text)
        if text.startswith('FAILED'):
            self.capture_state.setText(text)
        elif not self.busy and not self.reports:
            self.capture_state.setText('READY · No capture running' if text.startswith(('LIVE', 'PAUSED')) else text)

    def update_totals(self):
        reports = list(self.reports.values())
        saved = sum(bool(r.get('all_captured')) for r in reports)
        usable = sum(bool(r.get('has_shared_board_pair') if 'oak_usb' in self.camera_names else r.get('all_usable'))
                     and r.get('all_captured') and r.get('stationary_set_confirmed') is not False for r in reports)
        photos = sum(bool(c.get('success')) for r in reports for c in r.get('cameras', {}).values())
        self.totals.setText(f'THIS SESSION · {saved} complete sets · {usable} usable sets · {photos} saved photos · {len(reports) - usable} sets need review')

    def toggle_live(self, checked):
        self.action.setText('RECEIVED · Pausing live view…' if checked else 'RECEIVED · Resuming live view…')
        if self.continuous:
            self.pause.setText('Resume cameras' if checked else 'Release cameras')
            self.data.clear()
            self.errors.clear()
            self.capture.setEnabled(False)
        else:
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
        self.reports[report['directory']] = report
        self.update_totals()
        self.capture.setEnabled(not self.closing)
        self.pause.setEnabled(not self.closing)
        self.mode.setEnabled(True)
        if report['all_captured']:
            counts = ', '.join(name + ': ' + str(r['observation']['corners']) + '/24'
                               for name, r in report['cameras'].items())
            text = f'DONE · {len(report["cameras"])} photos saved. ' + counts
            if 'oak_usb' in self.camera_names:
                text += ' · Shared board: '+', '.join(report.get('shared_board_cameras',[]))
            elif not report['all_usable']:
                text += ' · INCOMPLETE SHARED BOARD VIEW'
            if report.get('stationary_set_confirmed') is False:
                text = 'FAILED STATIONARITY AUDIT · Images saved for diagnosis only. ' + text
        else:
            text = 'FAILED / PARTIAL SET · ' + '; '.join(name + ': ' + r.get('error', 'saved')[-250:]
                for name, r in report['cameras'].items())
            text += ' ' + report.get('error', '')
        self.action.setText(text + '\n' + report['directory'])
        complete = report['all_captured'] and report.get('stationary_set_confirmed') is not False
        usable = complete and (report.get('has_shared_board_pair',False) if 'oak_usb' in self.camera_names else report.get('all_usable', False))
        outcome = 'DONE · Usable board views' if usable else 'DONE · Board views need review' if complete else 'FAILED · Review diagnostics'
        self.last_result.setText(f'LAST CAPTURE · Set {len(self.reports)} · {outcome}')
        self.last_result.setToolTip(text + '\n' + report['directory'])
        self.capture_state.setText(('DONE · Capture finished · You may move the board' if usable else
            'DONE · Board view needs review · You may move the board' if complete else
            'FAILED / PARTIAL · Capture ended · Review the saved diagnostics'))
        self.capture_state.setStyleSheet('background:' + ('#8effa2' if usable else '#ffe066' if complete else '#ffb4b4') +
            ';color:#000;font-size:26px;font-weight:bold;padding:10px;border:3px solid #fff;')
        self.progress.setValue(len(self.camera_names) + 1)
        self.progress.setFormat('Capture finished' if complete else 'Capture ended with errors')
        (self.rig.session / 'latest-set.txt').write_text(report['directory'] + '\n')

    def refresh(self):
        if hasattr(self.rig, 'gemini_registration') and self.reports and time.monotonic() >= self.next_gemini_check:
            self.next_gemini_check = time.monotonic() + 1.5
            last = Path(next(reversed(self.reports)))
            status_file = last / 'gemini-charuco' / 'status.json'
            try:
                cameras = json.loads(status_file.read_text())['cameras']
                done = sum(r['state'] == 'completed' for r in cameras.values())
                retry = sum(r['state'] == 'retrying' for r in cameras.values())
                uncertain = sum(r.get('verdict') == 'uncertain' for r in cameras.values())
                self.gemini_status.setText(f'GEMINI · Last set: {done}/{len(cameras)} reviewed · {uncertain} uncertain · {retry} retrying')
                self.gemini_status.setToolTip(str(status_file.parent))
            except (OSError, ValueError, KeyError):
                self.gemini_status.setText(self.rig.gemini_registration)
        current = []
        for name in getattr(self.rig, 'cameras', CAMERAS):
            meta = self.data.get(name)
            if not meta:
                text, color = 'WAITING / NO IMAGE', '#ffe066'
                detail = self.errors.get(name, 'Connecting…')
            else:
                age = max(0, time.time() - meta['received'])
                obs = meta['observation']
                stale_payload = time.time() - self.changes.get(name, 0) > 15
                fresh = age < 8 and not self.pause.isChecked() and not self.busy and not self.errors.get(name)
                snapshot = meta['kind'].startswith('SAVED SNAPSHOT')
                fresh = fresh and not stale_payload and not snapshot
                if fresh:
                    text = obs['status'] + ' · ' + str(obs['corners']) + '/24'
                    color = '#8effa2' if obs['full'] else '#ffe066' if obs['corners'] else '#ffb4b4'
                    # Low-bandwidth wrist previews can have fewer interpolated
                    # corners than their native photos. Visibility is not the
                    # native dataset's stricter >=12-corner quality threshold.
                    current.append(obs['corners'] >= 4)
                else:
                    text, color = ('PAUSED / SNAPSHOT' if self.pause.isChecked() or self.busy or
                                   snapshot else 'STALE / NO CURRENT IMAGE'), '#ffe066'
                    current.append(False)
                size = obs['image_size']
                detail = f"{meta['kind']} · {size[0]}×{size[1]} · received {age:.1f} s ago\n"
                detail += self.errors.get(name, f"Reference markers: {len(obs['marker_ids'])}/17 · corners: {obs['corners']}/24")
                if stale_payload:
                    detail += '\nUnchanged payload >15 s; freshness unconfirmed.'
                pixmap = self.pixmaps[name]
                self.labels[name].setPixmap(pixmap.scaled(self.labels[name].size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            self.states[name].setText(text)
            self.states[name].setStyleSheet(f'background:{color};color:#000;font-size:17px;font-weight:bold;padding:5px;')
            self.details[name].setText(detail)
        ready = len(current) == len(self.camera_names) and all(current)
        self.overall.setText('ALL ' + self.count_label + ' DETECT REFERENCE BOARD · Capture to check native detail (hold still)' if ready else
            'CHECK SHARED VIEW · Show the selected reference board to all cameras; full board is best')
        if 'oak_usb' in self.camera_names:
            count = sum(current)
            self.overall.setText(f'{count}/6 CAMERAS SEE BOARD · Hold still for capture; turn board toward other pairs between sets')
            if self.busy and self.frames_elapsed is not None:
                self.overall.setText('FRAME CAPTURE COMPLETE · You may turn the board for the next set')
        self.overall.setStyleSheet('background:' + ('#8effa2' if ready else '#ffe066') +
            ';color:#000;font-size:19px;font-weight:bold;padding:8px;')
        if self.busy:
            elapsed = time.monotonic() - self.started
            self.capture.setText(f'CAPTURING · {elapsed:.0f} s')
            if self.capture_directory is None:
                new = set(self.rig.session.glob('set_*')) - self.previous_sets
                if new:
                    self.capture_directory = sorted(new)[-1]
            records = {}
            if self.capture_directory:
                for name in self.camera_names:
                    try:
                        records[name] = json.loads((self.capture_directory / name / 'record.json').read_text())
                    except (OSError, ValueError):
                        pass  # A record may still be in the process of being written.
            saved = sum(bool(r.get('success')) for r in records.values())
            failed = sum(not r.get('success', False) for r in records.values())
            self.progress.setValue(len(records))
            phase = 'Checking stationarity / resuming preview' if len(records) == len(self.camera_names) else 'Taking photos'
            self.progress.setFormat(f'{saved}/{len(self.camera_names)} photos saved · {failed} failed · {phase}')
            self.capture_state.setText(f'RUNNING · HOLD STILL · {elapsed:.0f} s · {saved}/{len(self.camera_names)} photos saved')
            if self.continuous and self.frames_elapsed is not None:
                self.capture_state.setText(f'FRAMES ACQUIRED in {self.frames_elapsed:.2f} s · You may move the board · Saving photos')
                self.progress.setFormat(f'{saved}/{len(self.camera_names)} photos checked')
            for name in self.camera_names:
                record = records.get(name)
                self.states[name].setText('PHOTO SAVED · Awaiting set checks' if record and record.get('success') else
                    'PHOTO FAILED · See result' if record else 'CAPTURE PENDING / RUNNING')
        else:
            self.capture.setText('CAPTURE ALL ' + self.count_label)
            if self.continuous:
                live = (not self.closing and self.worker.isRunning() and not self.pause.isChecked()
                        and all(name in self.data and name not in self.errors and
                                time.time() - self.data[name]['received'] < 8 for name in self.camera_names))
                self.capture.setEnabled(live)
                if live and not self.reports:
                    self.capture_state.setText('READY · Six native camera streams running')
                    self.action.setText('Ready to capture. Hold the board still and press CAPTURE ALL SIX.')

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
        self.busy = False
        if self.closing:
            self.close()
        else:
            self.capture_state.setText('FAILED · Camera worker stopped · Capture unavailable')
            self.capture_state.setStyleSheet('background:#ffb4b4;color:#000;font-size:26px;font-weight:bold;padding:10px;')
            self.progress.setFormat('Worker stopped · Review status below')
            self.capture.setEnabled(False)
            self.pause.setEnabled(False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, default=Path(os.environ.get('UWA_WS', Path.home() / 'UWA_ws')))
    p.add_argument('--output', type=Path)
    p.add_argument('--capture-only', action='store_true')
    p.add_argument('--single-shot', action='store_true', help='Use the original single-shot camera sessions in the GUI')
    p.add_argument('--quick', action='store_true', help='Capture-only: use wrist VGA rather than native HD')
    p.add_argument('--five-cameras', action='store_true', help='Four wrists plus OAK; separate object-scan focus profile')
    p.add_argument('--six-cameras', action='store_true', help='Four wrists plus Ethernet OAK4 and N100 USB OAK')
    p.add_argument('--cameras', nargs='+', choices=SIX_CAMERAS, help='Selected distinct cameras including oak4')
    p.add_argument('--keep-camera-settings', action='store_true', help='Retain useful focus/settings on exit and record their readback')
    p.add_argument('--board', choices=('mobile', 'left', 'right', 'both'), help='Default mobile, or both tables with --five-cameras')
    p.add_argument('--telemetry-source',choices=('ros','rtde'),default='ros',help='Stationarity observer; rtde only subscribes to controller outputs')
    args = p.parse_args()
    if sum(bool(v) for v in (args.five_cameras,args.six_cameras,args.cameras)) > 1:
        p.error('--five-cameras, --six-cameras and --cameras are mutually exclusive')
    options = {}
    if args.cameras:
        options['cameras'] = tuple(args.cameras)
    if args.five_cameras:
        options = dict(cameras=FIVE_CAMERAS, optics_path=args.workspace /
            'src/multi_arm_manipulation_UWA/config/digitization/five_camera_capture.yaml')
        if args.output is None:
            args.output = args.workspace / 'setup/digitization/five_camera'
    if args.six_cameras:
        options = dict(cameras=SIX_CAMERAS,optics_path=args.workspace /
            'src/multi_arm_manipulation_UWA/config/digitization/six_camera_capture.yaml')
        if args.output is None:
            args.output = args.workspace / 'setup/calibration/six_camera_mobile'
    elif args.cameras and 'oak_usb' in args.cameras:
        options['optics_path'] = args.workspace / 'src/multi_arm_manipulation_UWA/config/digitization/six_camera_capture.yaml'
    rig_type = CaptureRig
    if (set(options.get('cameras', ())) == set(SIX_CAMERAS)
            and not args.capture_only and not args.single_shot):
        from .board_capture_session import ContinuousCaptureRig
        rig_type = ContinuousCaptureRig
    rig = rig_type(args.workspace, args.output, board=args.board or ('both' if args.five_cameras else 'mobile'),telemetry_source=args.telemetry_source, keep_camera_settings=args.keep_camera_settings, **options)
    # Register actual camera application sessions, including custom output paths.
    # Library callers such as simulations and unrelated scan tools own their data.
    from .gemini_photo_queue import register_session
    try:
        register_session(args.workspace, rig.session)
        rig.gemini_registration = 'GEMINI · Waiting for saved camera photos'
    except (OSError, ValueError, sqlite3.Error) as error:
        rig.gemini_registration = 'GEMINI REGISTRATION FAILED · ' + str(error)
        print(rig.gemini_registration, file=sys.stderr)
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
    window.resize(min(1470, available.width() - 30), min(1020 if len(rig.cameras) > 3 else 900, available.height() - 70))
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

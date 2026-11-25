#!/usr/bin/env python3
"""Small local operator window for the four physical UWA arms."""

import argparse
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
import socket
import time
from pathlib import Path
import sys

from PySide6 import QtCore, QtGui, QtWidgets
from motion_review_panel import ReviewPanel, use_host_desktop_libraries, remote_runtime_command
from power_log_view import SafetyLogDialog, power_session, report_command


ROOT = Path(__file__).resolve().parents[1]
N100_SSH_CONFIG = ROOT.parents[1]/'setup/n100/ssh_config'
LABELS = {'left_front': 'Left front', 'left_rear': 'Left rear',
          'right_front': 'Right front', 'right_rear': 'Right rear'}
GUIDANCE = {
    'program_in_use': 'Another program is active. Review it at the Teach Pendant.',
    'local_control': 'Select Remote Control at the Teach Pendant.',
    'safety_blocked': 'Check the safety message at the Teach Pendant.',
    'confirm_safety': ('Controller reports CONFIRM_SAFETY. If it persists, '
                       'check the safety message at the Teach Pendant.'),
    'unsaved_program': 'Save or discard the program edits at the Teach Pendant.',
    'unreachable': 'Check the control box, Ethernet and Dashboard Server.',
    'readback_lost': 'Status lost after a command. Check the Teach Pendant.',
    'command_outcome_unknown': 'No command acknowledgement. Check the Teach Pendant.',
    'command_rejected': 'Dashboard rejected the command. Check the Teach Pendant.',
    'transition_timeout': 'The requested state was not confirmed. Check the Teach Pendant.',
    'ros_driver_missing': 'Start the local ROS driver in UWA Arms.',
    'ros_driver_start_failed': 'The ROS driver did not start. Check UWA Arms or the driver log.',
    'ros_not_connected': 'Check the ROS driver and External Control settings.',
    'play_not_confirmed': 'Check ros.urp and the External Control node at the Teach Pendant.',
    'load_rejected': 'Check ros.urp and its installation at the Teach Pendant.',
    'identity_mismatch': 'Controller serial number differs from the inventory.',
    'unexpected_dashboard': 'Unexpected Dashboard endpoint.',
    'invalid_readback': 'Unexpected Dashboard answer. Check the Teach Pendant.',
    'robot_mode_blocked': 'Check initialization and robot mode at the Teach Pendant.',
    'unsupported_polyscope': 'Unexpected PolyScope generation. Check the inventory.',
    'transport_status_unavailable': 'Could not read the local ROS connections.',
    'state_inconsistent': 'Program and arm status disagree. Check the Teach Pendant.',
    'state_changed': 'Robot status changed during preparation. Review it before retrying.',
}
ACTIONS = {'standby': 'Standby', 'start': 'Start + ROS'}


def instance_address(uid=None, candidate=None):
    """Keep a candidate window separate from the existing operational GUI."""
    address = f'\0uwa-robot-power-{os.getuid() if uid is None else uid}'
    runtime = os.environ.get('UWA_MINIMAL_RUNTIME', '') if candidate is None else candidate
    if runtime:
        if not Path(runtime).is_absolute():
            raise ValueError('UWA_MINIMAL_RUNTIME must be an absolute N100 runtime path')
        identity = hashlib.sha256(os.path.normpath(runtime).encode()).hexdigest()[:16]
        address += '-minimal-' + identity
    return address


def protection_command(n100=False, mock=False):
    if n100:
        return ['/usr/bin/ssh', '-F', str(N100_SSH_CONFIG), '-o', 'ConnectTimeout=5',
                '-o', 'BatchMode=yes', 'uwa-n100-robot-lan',
                remote_runtime_command('protection.sh', ['bridge', '--mode', 'hardware'])]
    return ['/usr/bin/bash', '-c',
            'source "$1"; exec /usr/bin/python3 "$2" --mode "$3"', 'uwa-protection',
            str(ROOT/'scripts/control_env.bash'), str(ROOT/'scripts/protection_bridge.py'),
            'mock' if mock else 'hardware']


class ProtectionControls(QtWidgets.QFrame):
    """Independent transport keeps the stop button usable during power/review work."""
    audit = QtCore.Signal(str, object)

    def __init__(self, command, parent=None):
        super().__init__(parent)
        self.command = command
        self.closed = False
        self.available = False
        self.paused = False
        self.sequence = 0
        self.stdout = bytearray()
        self.last_status = 0.
        self.last_status_audit = None
        self.pending = {}
        self.setStyleSheet('QFrame{background:#fff;color:#102744;border-radius:8px}'
                           'QLabel{border:0}'
                           'QPushButton#softwareStop{background:#960d18;color:white;border:3px solid #310000;'
                           'font-size:18px;font-weight:800;padding:12px}'
                           'QPushButton#softwareResume{background:#173b5a;color:white;border:2px solid #081d31;'
                           'font-weight:800;padding:12px}'
                           'QPushButton#softwareResume:disabled{background:#d9e0e7;color:#465665}')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(5)
        buttons = QtWidgets.QHBoxLayout()
        self.pause_button = QtWidgets.QPushButton('SOFTWARE STOP ALL ARMS', objectName='softwareStop')
        self.pause_button.setMinimumHeight(60)
        self.pause_button.setToolTip('Pause all arm motion through ROS controllers. Grippers retain their targets.')
        self.resume_button = QtWidgets.QPushButton('RESUME', objectName='softwareResume')
        self.resume_button.setEnabled(False)
        self.resume_button.setMinimumHeight(60)
        self.resume_button.setToolTip('Explicitly continue retained trajectories. Manual jog needs a fresh command.')
        self.pause_button.clicked.connect(lambda: self.request('pause_all'))
        self.resume_button.clicked.connect(lambda: self.request('resume_all'))
        buttons.addWidget(self.pause_button, 3)
        buttons.addWidget(self.resume_button, 1)
        layout.addLayout(buttons)
        self.state_label = QtWidgets.QLabel('CONNECTING · minimal protection endpoint')
        self.state_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.state_label.setStyleSheet('font-weight:800;font-size:14px')
        layout.addWidget(self.state_label)
        self.result_label = QtWidgets.QLabel('Controller acknowledgements are shown here; physical standstill is not measured.')
        self.result_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        grid = QtWidgets.QGridLayout()
        self.arm_labels = {}
        for i, (rid, label) in enumerate(LABELS.items()):
            item = QtWidgets.QLabel(label + ': UNCONFIRMED')
            item.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            item.setWordWrap(True)
            self.arm_labels[rid] = item
            grid.addWidget(item, i // 2, i % 2)
        layout.addLayout(grid)
        self.warning_label = QtWidgets.QLabel()
        self.warning_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet('background:#fff0c2;color:#482000;font-weight:750;padding:4px')
        self.warning_label.hide()
        layout.addWidget(self.warning_label)
        self.process = QtCore.QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.disconnected)
        self.process.errorOccurred.connect(lambda error: self.disconnected() if
            error == QtCore.QProcess.ProcessError.FailedToStart else None)
        self.timer = QtCore.QTimer(self, interval=1000)
        self.timer.timeout.connect(self.check_transport)
        self.timer.start()
        QtCore.QTimer.singleShot(0, self.connect_transport)

    def connect_transport(self):
        if self.closed or self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            return
        self.stdout.clear()
        self.process.start(self.command[0], self.command[1:])

    def request(self, operation):
        self.sequence += 1
        request_id = str(self.sequence)
        title = 'SOFTWARE STOP' if operation == 'pause_all' else 'RESUME'
        self.audit.emit('protection request', dict(id=request_id, operation=operation))
        if self.process.state() != QtCore.QProcess.ProcessState.Running:
            self.result_label.setText(title + ' FAILED · transport unavailable; command not sent.')
            self.connect_transport()
            return
        self.pending[request_id] = operation
        self.result_label.setText(title + ' RECEIVED · sending controller command…')
        self.process.write((json.dumps(dict(id=request_id, op=operation)) + '\n').encode())

    def read_output(self):
        self.stdout.extend(bytes(self.process.readAllStandardOutput()))
        while b'\n' in self.stdout:
            line, _, self.stdout = self.stdout.partition(b'\n')
            try:
                self.handle(json.loads(line))
            except (ValueError, TypeError, KeyError):
                continue

    def handle(self, packet):
        if not isinstance(packet, dict):
            return
        if packet.get('event') == 'status':
            if packet.get('available') and isinstance(packet.get('status'), dict):
                self.render_status(packet['status'])
            else:
                self.unavailable(packet.get('error') or 'Protection status unavailable.')
        elif packet.get('event') == 'command_result':
            operation = packet.get('operation')
            if operation not in ('pause_all', 'resume_all'):
                return
            if isinstance(packet.get('status'), dict):
                self.render_status(packet['status'])
            title = 'SOFTWARE STOP' if operation == 'pause_all' else 'RESUME'
            phase = packet.get('phase', 'failed')
            if phase == 'done':
                detail = 'command accepted; controller acknowledgements below.'
            elif phase == 'failed':
                detail = packet.get('message') or 'Command outcome unconfirmed.'
            else:
                detail = 'controller command in progress…'
            if phase in ('done', 'failed'):
                self.pending.pop(packet.get('id'), None)
                self.audit.emit('protection result', packet)
            # A late earlier response must not replace a newer stop acknowledgement.
            try:
                if int(packet.get('id', self.sequence)) < self.sequence:
                    return
            except (ValueError, TypeError):
                pass
            self.result_label.setText(title + ' ' + phase.upper() + ' · ' + detail)

    def render_status(self, status):
        self.last_status = time.monotonic()
        self.available = True
        self.paused = status.get('paused') is True
        state = str(status.get('state') or ('PAUSED' if self.paused else 'RUNNING ENABLED'))
        self.state_label.setText(state +
                                ' · ' + str(status.get('reason') or 'minimal collision protection'))
        self.state_label.setStyleSheet('font-weight:800;font-size:14px;color:' +
                                      ('#840611' if self.paused else '#102744'))
        self.resume_button.setEnabled(self.paused)
        arm_events = {}
        for rid, label in self.arm_labels.items():
            row = status.get('arms', {}).get(rid, {})
            state = 'UNCONFIRMED'
            if row.get('confirmed') is True:
                if row.get('controller') == 'collision_hold_controller':
                    state = 'HELD · fresh manual start required'
                elif row.get('paused', self.paused):
                    factor = row.get('factor', 0.)
                    state = 'PAUSING' if isinstance(factor, (int, float)) and factor > 0 else 'PAUSED'
                else:
                    state = 'RUNNING ENABLED'
                text = 'ACKNOWLEDGED · ' + state
            else:
                text = 'UNCONFIRMED'
            if row.get('error'):
                text += ' · ' + str(row['error'])
            label.setText(LABELS[rid] + ': ' + text)
            arm_events[rid] = dict(confirmed=row.get('confirmed') is True,
                                  state=state, controller=row.get('controller'),
                                  error=row.get('error') or '')
        warnings = [str(w) for w in status.get('warnings', [])]
        if status.get('collision_data_available') is False and not warnings:
            warnings.append('Collision data unavailable; automatic collision checking is incomplete.')
        self.warning_label.setText('WARNING · ' + ' · '.join(warnings))
        self.warning_label.setVisible(bool(warnings))
        phase = 'RUNNING'
        if self.paused:
            phase = ('PAUSING' if status.get('pausing') or status.get('state') == 'PAUSE REQUESTED'
                     or any(row['state'] == 'PAUSING' for row in arm_events.values()) else 'PAUSED')
        event = dict(generation=status.get('generation'), state=phase,
                     reason=status.get('reason'), known_collisions=status.get('known_collisions', []),
                     warnings=warnings, arms=arm_events,
                     collision_data_available=status.get('collision_data_available'))
        # Record the measured distance when an event changes. Repeated samples
        # of the same collision while braking are still the same event.
        collision_identity = [{k:v for k,v in row.items() if k != 'distance_m'}
                              if isinstance(row, dict) else row for row in event['known_collisions']]
        key = json.dumps(dict(event, known_collisions=collision_identity), sort_keys=True)
        if key != self.last_status_audit:
            self.last_status_audit = key
            self.audit.emit('protection status', json.loads(json.dumps(event)))

    def unavailable(self, detail):
        self.available = False
        self.resume_button.setEnabled(False)
        self.state_label.setText('UNAVAILABLE · minimal protection endpoint')
        self.state_label.setStyleSheet('font-weight:800;font-size:14px;color:#840611')
        self.warning_label.setText('WARNING · ' + str(detail) + ' No controller acknowledgement available.')
        self.warning_label.show()
        for rid, label in self.arm_labels.items():
            label.setText(LABELS[rid] + ': UNCONFIRMED')

    def disconnected(self, *_):
        if self.closed:
            return
        self.unavailable('Protection connection lost.')
        if self.pending:
            self.result_label.setText('FAILED · command outcome unconfirmed after connection loss.')
            self.pending.clear()

    def check_transport(self):
        if self.closed:
            return
        if self.process.state() == QtCore.QProcess.ProcessState.NotRunning:
            self.connect_transport()
        elif self.last_status and time.monotonic() - self.last_status > 4.:
            self.unavailable('Protection status is out of date.')

    def shutdown(self):
        self.closed = True
        self.timer.stop()
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.process.closeWriteChannel()
            if not self.process.waitForFinished(350):
                self.process.terminate()
                if not self.process.waitForFinished(350):
                    self.process.kill()
                    self.process.waitForFinished(350)


def present(row):
    code, data = row.get('code'), row.get('state') or {}
    details = []
    if data.get('safety') and data['safety'] != 'NORMAL':
        details.append('Safety: '+data['safety'].replace('_', ' ').title())
    if data.get('remote') is False and code != 'local_control':
        details.append('Local Control')
    if code == 'ready':
        return 'ROS READY', 'good', ' · '.join(['Drives on · ros.urp connected', *details])
    if code == 'standby':
        return 'DRIVES OFF', 'off', ' · '.join(['Control box online', *details])
    if code == 'needs_preparation':
        mode = data.get('mode', 'unknown').replace('_', ' ').title()
        playback = data.get('playback', 'unknown').title()
        if playback == 'Playing' and data.get('program') not in (None, '/programs/ros.urp'):
            details.append('Another program is running')
        return 'NOT READY', 'warn', ' · '.join([f'{mode} · Program {playback.lower()}', *details])
    guidance = GUIDANCE.get(code, 'Check the arm at its Teach Pendant.')
    return ('OFFLINE' if code == 'unreachable' else 'CHECK ARM', 'warn',
            ' · '.join([guidance, *details]))


class Window(QtWidgets.QWidget):
    def __init__(self, backend=None, *, n100=False, review_mock=None, program_library=False,
                 protection_backend='minimal', protection_transport=None):
        super().__init__()
        self.n100 = n100
        self.mock = review_mock is not None
        self.exiting = False
        self.tray = None
        self.review = None
        self.log_view = None
        self.library_process = None
        self.library_url = None
        self.log_command = report_command(n100, review_mock, backend=protection_backend)
        self.logged = {}
        try:
            self.log_session = power_session()
        except OSError:
            self.log_session = None
        self.record('window', 'Mock review' if self.mock else 'N100' if n100 else 'Local')
        if backend is not None:
            self.backend = backend
        elif n100:
            self.backend = ['/usr/bin/ssh', '-F', str(N100_SSH_CONFIG),
                            '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes',
                            'uwa-n100-robot-lan', remote_runtime_command('power.sh', environment=True)]
        else:
            self.backend = [sys.executable, str(ROOT/'scripts/ur_cell_power.py')]
        self.setWindowTitle('UWA Robot Power · Minimal candidate' if
                            n100 and os.environ.get('UWA_MINIMAL_RUNTIME') else 'UWA Robot Power')
        self.setWindowIcon(QtGui.QIcon(str(ROOT/'assets/uwa-robot-power.svg')))
        self.setMinimumWidth(555)
        self.resize(660, 473)
        self.setStyleSheet('''
            QWidget#window {background:#f4f7fb;color:#12253d;font-size:14px}
            QLabel#title {font-size:25px;font-weight:750;color:#102744}
            QLabel#intro {font-size:14px;color:#263e55}
            QFrame#list {background:#fff;border:1px solid #cad5df;border-radius:12px}
            QLabel#armTitle {color:#102744;font-weight:700}
            QLabel#armDetail {color:#31475f;font-size:13px}
            QLabel#state {font-weight:750;font-size:12px;border-radius:6px;padding:4px 8px}
            QLabel#feedback {background:#e5edf6;color:#152b44;font-weight:700;
                             border-radius:8px;padding:8px}
            QPushButton {border-radius:8px;padding:10px 13px;font-weight:700;
                         color:#102744;background:#edf2f9;border:1px solid #bdcddd}
            QPushButton#start {background:#075d54;color:#fff;border-color:#075d54}
            QPushButton#standby {background:#20374e;color:#fff;border-color:#20374e}
            QPushButton:focus {border:2px solid #2079c5}
            QPushButton:hover {border-color:#2079c5}
            QPushButton:disabled {background:#e8edf4;color:#596a7c;border-color:#c9d3df}
        ''')
        self.setObjectName('window')
        page = QtWidgets.QVBoxLayout(self)
        page.setContentsMargins(22, 19, 22, 17)
        page.setSpacing(11)

        header = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel()
        icon.setPixmap(self.windowIcon().pixmap(43, 43))
        header.addWidget(icon)
        words = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel('UWA Robot Power', objectName='title')
        intro_text = 'Four arms · N100 driver host' if n100 else 'Four arms · Control boxes stay online'
        intro = QtWidgets.QLabel(intro_text, objectName='intro')
        words.addWidget(title)
        words.addWidget(intro)
        words.setSpacing(0)
        header.addLayout(words, 1)
        self.refresh = QtWidgets.QPushButton('Refresh')
        self.refresh.clicked.connect(self.refresh_all)
        header.addWidget(self.refresh)
        self.log_button = QtWidgets.QPushButton('Safety log')
        self.log_button.clicked.connect(self.show_logs)
        header.addWidget(self.log_button)
        page.addLayout(header)
        if protection_backend != 'minimal':
            raise ValueError('Unknown protection backend: ' + str(protection_backend))
        self.protection = ProtectionControls(protection_transport or protection_command(n100, self.mock), self)
        self.protection.audit.connect(self.record)
        page.addWidget(self.protection)
        if program_library:
            self.library_button = QtWidgets.QPushButton('Starting program library…')
            self.library_button.setEnabled(False)
            self.library_button.clicked.connect(self.open_program_library)
            page.addWidget(self.library_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        power = QtWidgets.QWidget()
        power_page = QtWidgets.QVBoxLayout(power)
        frame = QtWidgets.QFrame(objectName='list')
        rows = QtWidgets.QVBoxLayout(frame)
        rows.setContentsMargins(13, 8, 13, 8)
        rows.setSpacing(8)
        self.rows = {}
        for rid, name in LABELS.items():
            group = QtWidgets.QGridLayout()
            group.setHorizontalSpacing(12)
            group.setVerticalSpacing(2)
            caption = QtWidgets.QLabel(name, objectName='armTitle')
            badge = QtWidgets.QLabel('CHECKING', objectName='state')
            badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            body = QtWidgets.QLabel('Waiting for robot status.', objectName='armDetail')
            body.setWordWrap(True)
            group.addWidget(caption, 0, 0)
            group.addWidget(badge, 0, 1, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
            group.addWidget(body, 1, 0, 1, 2)
            rows.addLayout(group)
            self.rows[rid] = (badge, body)
        power_page.addWidget(frame)
        self.feedback = QtWidgets.QLabel('Checking robot status…', objectName='feedback')
        self.feedback.setWordWrap(True)
        power_page.addWidget(self.feedback)

        buttons = QtWidgets.QHBoxLayout()
        self.standby = QtWidgets.QPushButton('Standby', objectName='standby')
        self.start = QtWidgets.QPushButton('Start + ROS', objectName='start')
        self.standby.setToolTip('Stop ros.urp and switch off the arm drives.')
        self.start.setToolTip('Switch on the arm drives, release the brakes and connect ROS.')
        self.standby.clicked.connect(lambda: self.launch('standby'))
        self.start.clicked.connect(lambda: self.launch('start'))
        buttons.addWidget(self.standby, 1)
        buttons.addWidget(self.start, 1)
        power_page.addLayout(buttons)
        caption = QtWidgets.QLabel(
            'Finish the experiment before Standby. Keep the work area clear for Start.',
            objectName='armDetail')
        caption.setWordWrap(True)
        power_page.addWidget(caption)
        if n100 or self.mock:
            self.tabs = QtWidgets.QTabWidget()
            if not self.mock:
                self.tabs.addTab(power, 'Robot power')
                review_backend = self.backend[:-1]
            else:
                power.setParent(self)
                power.hide()
                review_backend = [sys.executable, str(ROOT/'tools/motion_review.py'),
                                  '--store', str(review_mock.resolve())]
                intro.setText('MOCK · Local review store')
                self.setWindowTitle('UWA Robot Power · Mock review')
            self.review = ReviewPanel(review_backend, remote=n100, parent=self)
            self.review.audit.connect(self.record)
            self.review.attention.connect(self.show_review)
            self.review.faultNotice.connect(self.show_fault)
            self.review.safeToQuit.connect(self.finish_quit)
            self.tabs.addTab(self.review, 'Motion review')
            page.addWidget(self.tabs)
            self.install_tray()
            self.resize(760, 740)
        else:
            page.addWidget(power)

        self.mode = None
        self.have_result = False
        self.stdout = bytearray()
        self.completed = False
        self.changed = set()
        self.last_issues = {}
        self.process = QtCore.QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.refresh_timer = QtCore.QTimer(self, interval=5000)
        self.refresh_timer.timeout.connect(lambda: self.launch('status'))
        if not self.mock:
            self.refresh_timer.start()
            QtCore.QTimer.singleShot(0, lambda: self.launch('status'))
        if program_library:
            self.start_program_library(review_mock)
        self.refresh.setFocus()

    def start_program_library(self, review_mock):
        self.library_stdout = bytearray()
        self.library_process = QtCore.QProcess(self)
        self.library_process.readyReadStandardOutput.connect(self.read_library_url)
        self.library_process.finished.connect(self.program_library_closed)
        self.library_process.errorOccurred.connect(self.program_library_closed)
        args = [str(ROOT / 'scripts/skill_library_server.py'), '--port', '0']
        if review_mock is not None:
            args += ['--runs', str(review_mock.resolve() / 'program-runs')]
        elif self.n100:
            args += ['--live-config', str(ROOT.parents[1] / 'setup/skill_library/live-carton.json')]
        self.library_process.start(sys.executable, args)

    def read_library_url(self):
        self.library_stdout.extend(self.library_process.readAllStandardOutput().data())
        line, separator, remainder = self.library_stdout.partition(b'\n')
        if not separator:
            return
        self.library_stdout = remainder
        url = QtCore.QUrl(line.decode(errors='replace').strip())
        if url.scheme() == 'http' and url.host() == '127.0.0.1' and url.port() > 0:
            self.library_url = url
            self.library_button.setText('Program library')
            self.library_button.setToolTip(url.toString())
            self.library_button.setEnabled(True)

    def program_library_closed(self, *_):
        self.library_url = None
        self.library_button.setText('Program library unavailable')
        self.library_button.setEnabled(False)
        error = self.library_process.readAllStandardError().data().decode(errors='replace').strip()
        self.library_button.setToolTip(error.splitlines()[-1] if error else self.library_process.errorString())

    def open_program_library(self):
        if self.library_url and not QtGui.QDesktopServices.openUrl(self.library_url):
            self.feedback.setText('Open the program library in your browser: ' + self.library_url.toString())

    def controls(self):
        for item in (self.start, self.standby, self.refresh):
            item.setEnabled(self.mode is None)

    def record(self, kind, value, *, repeat=False):
        if not self.log_session or (not repeat and self.logged.get(kind) == value):
            return
        try:
            entry = {'at': datetime.now(timezone.utc).isoformat(), 'event': kind, 'value': value}
            self.log_session.note(json.dumps(entry, ensure_ascii=False))
            self.logged[kind] = value
        except OSError:
            pass  # Diagnostic storage cannot interrupt the control or review windows.

    def show_logs(self):
        if self.log_view is None:
            if self.log_session is None:
                try:
                    self.log_session = power_session()
                except OSError as exc:
                    QtWidgets.QMessageBox.warning(self, 'Safety log', f'Could not create the local log directory.\n{exc}')
                    return
            self.log_view = SafetyLogDialog(self.log_session, self.log_command, self)
        self.log_view.showNormal()
        self.log_view.raise_()
        self.log_view.activateWindow()

    def set_arm(self, rid, title, style, detail):
        if rid not in self.rows:
            return
        badge, body = self.rows[rid]
        color, background = {'good': ('#08483c', '#ccf1e7'), 'off': ('#1f405f', '#e2ebf4'),
                             'warn': ('#692800', '#ffe7c4'), 'busy': ('#073365', '#d7ebff')}[style]
        badge.setStyleSheet(f'background:{background};color:{color};')
        badge.setText(title)
        body.setText(detail)

    def launch(self, mode):
        if self.mock or self.mode is not None:
            return
        self.mode, self.completed = mode, False
        self.changed.clear()
        self.stdout.clear()
        self.controls()
        if mode != 'status':
            self.record('power request', mode, repeat=True)
            self.last_issues.clear()
            self.feedback.setText(f'{ACTIONS[mode]} in progress…')
            for rid in self.rows:
                self.set_arm(rid, 'PENDING', 'busy', 'Waiting for its turn.')
        self.process.start(self.backend[0], [*self.backend[1:], mode])

    def read_output(self):
        self.stdout.extend(bytes(self.process.readAllStandardOutput()))
        while b'\n' in self.stdout:
            packet, _, self.stdout = self.stdout.partition(b'\n')
            try:
                self.handle(json.loads(packet))
            except (ValueError, TypeError, KeyError):
                continue

    def handle(self, packet):
        event = packet['event']
        if event == 'progress':
            rid = packet['arm']
            self.set_arm(rid, 'IN PROGRESS', 'busy', f'{ACTIONS[self.mode]} commands in progress.')
            self.feedback.setText(f'{ACTIONS[self.mode]} · {LABELS[rid]}')
        elif event == 'arm':
            row = packet['result']
            rid = row['arm']
            self.record(f'{self.mode} · {rid}', row, repeat=self.mode in ACTIONS)
            self.changed.add(rid)
            title, style, detail = present(row)
            if self.mode in ACTIONS:
                if row['code'] not in ('ready', 'standby'):
                    self.last_issues[rid] = detail
                else:
                    self.last_issues.pop(rid, None)
            if self.mode == 'status' and self.last_issues.get(rid, detail) != detail:
                detail += ' · Last action: '+self.last_issues[rid]
            self.set_arm(rid, title, style, detail)
        elif event == 'done':
            self.completed = True
            if self.mode == 'status':
                if not self.have_result:
                    self.feedback.setText('Select Standby or Start + ROS.')
            else:
                self.record('power result', packet, repeat=True)
                self.have_result = True
                self.feedback.setText(f'{ACTIONS[self.mode]} complete for all four arms.'
                    if packet['success'] else f'{ACTIONS[self.mode]} incomplete. Check the arm messages above.')
        elif event == 'error':
            self.record(f'{self.mode} error', packet, repeat=self.mode in ACTIONS)
            self.completed = True
            self.have_result = True
            if self.n100:
                self.feedback.setText('N100 action unavailable. Check the runtime status and refresh.')
            else:
                self.feedback.setText('Action unavailable. Another operation may be running; refresh and try again.')
            for rid in set(self.rows)-self.changed:
                self.set_arm(rid, 'UNKNOWN', 'warn', 'No current status available.')

    def finished(self, code=None, *_):
        self.read_output()
        stderr = bytes(self.process.readAllStandardError()).decode(errors='replace').strip()
        self.record(f'{self.mode} transport', {'exit_code': code, 'complete': self.completed,
                                               'stderr': stderr[-2000:]})
        if not self.completed:
            self.have_result = True
            if self.n100:
                self.feedback.setText('N100 connection or response lost. Refresh to check the arm states before retrying.')
            else:
                self.feedback.setText('Status update ended early. Refresh before retrying.')
            for rid in set(self.rows)-self.changed:
                self.set_arm(rid, 'UNKNOWN', 'warn', 'No current status available.')
        self.mode = None
        self.controls()

    def process_error(self, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart:
            self.finished()

    def raise_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def refresh_all(self):
        if not self.mock:
            self.launch('status')
        if self.review:
            self.review.failed_export = None
            self.review.refresh()

    def show_review(self, message=None):
        self.tabs.setCurrentWidget(self.review)
        self.raise_window()
        if message:
            QtWidgets.QApplication.alert(self)
        if message and self.tray and self.tray.supportsMessages():
            self.tray.showMessage('UWA · Decision required', message,
                                  QtWidgets.QSystemTrayIcon.MessageIcon.Information)

    def show_fault(self, message):
        if self.tray and self.tray.supportsMessages():
            self.tray.showMessage('UWA · Carton task interrupted', message,
                                  QtWidgets.QSystemTrayIcon.MessageIcon.Warning)
        else:
            QtWidgets.QApplication.alert(self)

    def install_tray(self):
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QtWidgets.QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip(self.windowTitle())
        menu = QtWidgets.QMenu(self)
        menu.addAction('Open motion review', self.show_review)
        menu.addAction('Quit', self.review.request_quit)
        self.tray.setContextMenu(menu)
        self.tray.messageClicked.connect(self.show_review)
        self.tray.activated.connect(lambda reason: self.show_review() if
            reason in (QtWidgets.QSystemTrayIcon.ActivationReason.Trigger,
                       QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        self.tray.show()

    def finish_quit(self):
        self.exiting = True
        # A closeEvent may be awaiting this signal already.
        QtCore.QTimer.singleShot(0, self.close)

    def closeEvent(self, event):
        if self.mode not in (None, 'status'):
            self.exiting = False
            self.feedback.setText('Please wait for the current power action to finish.')
            event.ignore()
            return
        if self.review and not self.exiting:
            event.ignore()
            if self.tray:
                self.hide()
            else:
                self.review.request_quit()
            return
        if self.review:
            self.review.shutdown()
        self.protection.shutdown()
        if self.log_view:
            self.log_view.shutdown()
        if self.library_process and self.library_process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.library_process.terminate()
            if not self.library_process.waitForFinished(350):
                self.library_process.kill()
                self.library_process.waitForFinished(350)
        if self.tray:
            self.tray.hide()
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(350)
        event.accept()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    host = parser.add_mutually_exclusive_group()
    host.add_argument('--n100', action='store_true', help='Use the N100 driver host over Ethernet SSH')
    host.add_argument('--review-mock', type=Path, metavar='DIRECTORY',
                      help='Review a local mock store. No power or robot connection.')
    parser.add_argument('--safety-log', action='store_true',
                        help='Open only the read-only safety log, alongside an existing window.')
    parser.add_argument('--protection-backend', choices=('minimal',),
                        default=os.environ.get('UWA_PROTECTION_BACKEND', 'minimal'),
                        help='Use the minimal protection API; unavailable endpoints never fall back to the old guard.')
    args, qt_args = parser.parse_known_args()
    use_host_desktop_libraries()
    app = QtWidgets.QApplication([sys.argv[0], *qt_args])
    app.setDesktopFileName('uwa-robot-power')
    app.setApplicationName('uwa-robot-power')
    app.setApplicationDisplayName('UWA Robot Power')
    if args.safety_log:
        dialog = SafetyLogDialog(power_session(), report_command(args.n100, args.review_mock,
                                 backend=args.protection_backend))
        dialog.show()
        try:
            return app.exec()
        finally:
            dialog.shutdown()
    if args.review_mock is not None:
        window = Window(review_mock=args.review_mock, program_library=True,
                        protection_backend=args.protection_backend)
        window.show()
        return app.exec()
    # An abstract Unix socket is released by the kernel when the app exits.
    address = instance_address()
    requested_host = b'n100' if args.n100 else b'local'
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        peer.bind(address)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        with peer:
            peer.settimeout(.3)
            peer.sendto(requested_host, address)
        return 0
    peer.setblocking(False)
    window = Window(n100=args.n100, program_library=True, protection_backend=args.protection_backend)
    notifier = QtCore.QSocketNotifier(peer.fileno(), QtCore.QSocketNotifier.Type.Read, window)

    def activate(*_):
        while True:
            try:
                host = peer.recv(64)
            except BlockingIOError:
                break
            if host in (b'n100', b'local') and host != requested_host and window.mode not in ACTIONS:
                window.feedback.setText('Close this window before opening UWA Robot Power for the other driver host.')
        window.raise_window()

    notifier.activated.connect(activate)
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

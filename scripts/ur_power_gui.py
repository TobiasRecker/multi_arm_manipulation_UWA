#!/usr/bin/env python3
"""Small local operator window for the four physical UWA arms."""

import argparse
import errno
import json
import os
import socket
from pathlib import Path
import sys

from PySide6 import QtCore, QtGui, QtWidgets


ROOT = Path(__file__).resolve().parents[1]
N100_SSH_CONFIG = ROOT.parents[1]/'setup/n100/ssh_config'
LABELS = {'left_front': 'Left front', 'left_rear': 'Left rear',
          'right_front': 'Right front', 'right_rear': 'Right rear'}
GUIDANCE = {
    'program_in_use': 'Another program is active. Review it at the Teach Pendant.',
    'local_control': 'Select Remote Control at the Teach Pendant.',
    'safety_blocked': 'Check the safety message at the Teach Pendant.',
    'confirm_safety': 'Review the installation and safety confirmation at the Teach Pendant.',
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
    def __init__(self, backend=None, *, n100=False):
        super().__init__()
        self.n100 = n100
        if backend is not None:
            self.backend = backend
        elif n100:
            self.backend = ['/usr/bin/ssh', '-F', str(N100_SSH_CONFIG),
                            '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes',
                            'uwa-n100-robot-lan', 'bash ~/uwa-ur-runtime/power.sh']
        else:
            self.backend = [sys.executable, str(ROOT/'scripts/ur_cell_power.py')]
        self.setWindowTitle('UWA Robot Power')
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
        self.refresh.clicked.connect(lambda: self.launch('status'))
        header.addWidget(self.refresh)
        page.addLayout(header)

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
        page.addWidget(frame)
        self.feedback = QtWidgets.QLabel('Checking robot status…', objectName='feedback')
        self.feedback.setWordWrap(True)
        page.addWidget(self.feedback)

        buttons = QtWidgets.QHBoxLayout()
        self.standby = QtWidgets.QPushButton('Standby', objectName='standby')
        self.start = QtWidgets.QPushButton('Start + ROS', objectName='start')
        self.standby.setToolTip('Stop ros.urp and switch off the arm drives.')
        self.start.setToolTip('Switch on the arm drives, release the brakes and connect ROS.')
        self.standby.clicked.connect(lambda: self.launch('standby'))
        self.start.clicked.connect(lambda: self.launch('start'))
        buttons.addWidget(self.standby, 1)
        buttons.addWidget(self.start, 1)
        page.addLayout(buttons)
        caption = QtWidgets.QLabel(
            'Finish the experiment before Standby. Keep the work area clear for Start.',
            objectName='armDetail')
        caption.setWordWrap(True)
        page.addWidget(caption)

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
        self.refresh_timer.start()
        QtCore.QTimer.singleShot(0, lambda: self.launch('status'))
        self.refresh.setFocus()

    def controls(self):
        for item in (self.start, self.standby, self.refresh):
            item.setEnabled(self.mode is None)

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
        if self.mode is not None:
            return
        self.mode, self.completed = mode, False
        self.changed.clear()
        self.stdout.clear()
        self.controls()
        if mode != 'status':
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
                self.have_result = True
                self.feedback.setText(f'{ACTIONS[self.mode]} complete for all four arms.'
                    if packet['success'] else f'{ACTIONS[self.mode]} incomplete. Check the arm messages above.')
        elif event == 'error':
            self.completed = True
            self.have_result = True
            if self.n100:
                self.feedback.setText('N100 action unavailable. Check the runtime status and refresh.')
            else:
                self.feedback.setText('Action unavailable. Another operation may be running; refresh and try again.')
            for rid in set(self.rows)-self.changed:
                self.set_arm(rid, 'UNKNOWN', 'warn', 'No current status available.')

    def finished(self, *_):
        self.read_output()
        if not self.completed:
            self.have_result = True
            if self.n100:
                self.feedback.setText('N100 connection or response lost. Refresh to check the arm states before retrying.')
            else:
                self.feedback.setText('Status update ended early. Refresh before retrying.')
            for rid in set(self.rows)-self.changed:
                self.set_arm(rid, 'UNKNOWN', 'warn', 'No current status available.')
        self.process.readAllStandardError()
        self.mode = None
        self.controls()

    def process_error(self, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart:
            self.finished()

    def raise_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self.mode not in (None, 'status'):
            self.feedback.setText('Please wait for the current power action to finish.')
            event.ignore()
            return
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(350)
        event.accept()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n100', action='store_true', help='Use the N100 driver host over Ethernet SSH')
    args, qt_args = parser.parse_known_args()
    if os.environ.get('GTK_PATH', '').startswith('/snap/'):
        os.environ.pop('GTK_PATH')
    app = QtWidgets.QApplication([sys.argv[0], *qt_args])
    app.setDesktopFileName('uwa-robot-power')
    app.setApplicationName('uwa-robot-power')
    app.setApplicationDisplayName('UWA Robot Power')
    # An abstract Unix socket is released by the kernel when the app exits.
    address = f'\0uwa-robot-power-{os.getuid()}'
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
    window = Window(n100=args.n100)
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

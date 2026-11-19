"""Read and export recorded safety events independently of robot controls."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from PySide6 import QtCore, QtWidgets

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'uwa_cell_control'))
from uwa_cell_control.session_logs import SessionLogs

COLLECTOR = ROOT / 'scripts/power_safety_report.py'


def power_session():
    workspace = Path(os.environ.get('UWA_WS', ROOT.parents[1]))
    return SessionLogs(workspace, include_host_logs=False)


def report_command(n100=False, mock_store=None):
    if mock_store is not None:
        return [sys.executable, str(COLLECTOR), '--mock-store', str(mock_store.resolve())]
    if n100:
        return ['/usr/bin/ssh', '-T', '-F', str(ROOT.parents[1] / 'setup/n100/ssh_config'),
                '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', 'uwa-n100-robot-lan',
                'cd ~/uwa-ur-runtime && /usr/bin/python3 - --workspace .']
    return [sys.executable, str(COLLECTOR), '--workspace', str(ROOT.parents[1])]


class SaveReport(QtCore.QThread):
    def __init__(self, session, report, source, parent):
        super().__init__(parent)
        self.session, self.report, self.source = session, report, source
        self.path = self.error = ''

    def run(self):
        try:
            path = self.session.directory
            (path / 'safety-report.json').write_text(json.dumps(self.report, indent=2, allow_nan=False) + '\n')
            (path / 'safety-report.txt').write_text(self.report['summary_text'] + '\n')
            self.path = str(self.session.export({'app': 'UWA Robot Power', 'source': self.source,
                                                 'collection_error': self.report.get('collection_error')}))
        except Exception as exc:
            self.error = str(exc)


class SafetyLogDialog(QtWidgets.QDialog):
    def __init__(self, session, command, parent=None):
        super().__init__(parent)
        self.session, self.command = session, command
        self.remote = command[0] == '/usr/bin/ssh'
        self.source = 'N100' if self.remote else 'Mock' if '--mock-store' in command else 'Local'
        self.saving = False
        self.worker = None
        self.timed_out = False
        self.setWindowTitle(f'UWA Robot Power · Safety log · {self.source}')
        self.resize(840, 560)
        layout = QtWidgets.QVBoxLayout(self)
        self.summary = QtWidgets.QPlainTextEdit(readOnly=True)
        self.summary.setAccessibleName('Recorded safety events')
        layout.addWidget(self.summary)
        self.feedback = QtWidgets.QLabel()
        self.feedback.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.feedback.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.feedback.setStyleSheet('background:#17314a;color:white;font-weight:bold;padding:8px')
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        row = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton('Refresh log')
        self.refresh_button.clicked.connect(lambda: self.load())
        self.save_button = QtWidgets.QPushButton('Save logs')
        self.save_button.clicked.connect(lambda: self.load(save=True))
        row.addWidget(self.refresh_button)
        row.addWidget(self.save_button)
        layout.addLayout(row)
        self.process = QtCore.QProcess(self)
        self.process.finished.connect(self.received)
        self.process.errorOccurred.connect(self.process_error)
        self.deadline = QtCore.QTimer(self, singleShot=True, interval=30000)
        self.deadline.timeout.connect(self.expire)
        self.loading = False

    def showEvent(self, event):
        super().showEvent(event)
        self.load()

    def load(self, save=False):
        if self.worker is not None or self.loading:
            return
        self.loading = True
        self.saving = save
        self.timed_out = False
        self.feedback.setText(f'Reading recorded events · {self.source}…')
        self.refresh_button.setEnabled(False)
        self.save_button.setEnabled(False)
        if self.remote:
            self.process.setStandardInputFile(str(COLLECTOR))
        self.deadline.start()
        self.process.start(self.command[0], self.command[1:])

    def process_error(self, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart:
            self.received(-1)

    def expire(self):
        self.timed_out = True
        self.process.kill()

    def received(self, code, *_):
        if not self.loading:
            return
        self.deadline.stop()
        self.loading = False
        raw = bytes(self.process.readAllStandardOutput())
        stderr = bytes(self.process.readAllStandardError()).decode(errors='replace').strip()
        try:
            if self.timed_out:
                raise ValueError('Collection timed out.')
            if code:
                raise ValueError(stderr[-700:] or self.process.errorString() or f'Collector exited with {code}.')
            report = json.loads(raw)
            if not isinstance(report, dict) or report.get('schema_version') != 1 or not isinstance(report.get('summary_text'), str):
                raise ValueError('Unexpected report format.')
        except (ValueError, UnicodeError) as exc:
            report = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
                      'collection_error': str(exc), 'summary_text': f'{self.source} report unavailable.\n{exc}'}
        self.summary.setPlainText(report['summary_text'])
        self.summary.moveCursor(self.summary.textCursor().MoveOperation.Start)
        self.partial = bool(report.get('collection_error') or any(
            source.get('status') in ('unavailable', 'error', 'partial', 'truncated', 'missing')
            for source in report.get('sources', [])))
        if self.saving:
            self.feedback.setText('Saving diagnostic archive…')
            self.worker = SaveReport(self.session, report, self.source, self)
            self.worker.finished.connect(self.saved)
            self.worker.start()
        else:
            self.feedback.setText('Some records are unavailable. See the source details above.'
                                  if self.partial else f'Log loaded · {self.source}')
            self.enable_actions()

    def enable_actions(self):
        self.saving = False
        self.save_button.setEnabled(True)
        self.refresh_button.setEnabled(True)

    def saved(self):
        worker, self.worker = self.worker, None
        if worker.error:
            self.feedback.setText('Save failed · ' + worker.error)
        else:
            prefix = 'Saved with incomplete source data' if self.partial else 'Saved'
            self.feedback.setText(f'{prefix} · {worker.path}')
        worker.deleteLater()
        self.enable_actions()

    def shutdown(self):
        self.deadline.stop()
        self.loading = False
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        if self.worker is not None:
            self.worker.wait()

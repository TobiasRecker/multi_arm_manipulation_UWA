"""Operator decisions and trajectory previews for UWA Robot Power."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile

from PySide6 import QtCore, QtGui, QtWidgets


ROOT = Path(__file__).resolve().parents[1]
TRUST = ('Unsure · review every path', 'Familiar · auto-approve low risk', 'Confident · auto-approve low and medium risk')


def use_host_desktop_libraries():
    """Use the desktop's Qt/GTK schemas when launched inside the VS Code Snap."""
    for key in ('GTK_PATH', 'GTK_EXE_PREFIX', 'GTK_IM_MODULE_FILE', 'GIO_MODULE_DIR',
                'GSETTINGS_SCHEMA_DIR', 'GDK_PIXBUF_MODULEDIR', 'GDK_PIXBUF_MODULE_FILE'):
        if '/snap/' in os.environ.get(key, ''):
            os.environ.pop(key)
    if '/snap/' in os.environ.get('XDG_DATA_DIRS', ''):
        os.environ['XDG_DATA_DIRS'] = (os.environ.get('XDG_DATA_DIRS_VSCODE_SNAP_ORIG')
            or ':'.join(path for path in os.environ['XDG_DATA_DIRS'].split(':') if '/snap/' not in path))


def plain(text=''):
    label = QtWidgets.QLabel(text)
    label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


def speed_text(percent):
    return f'{percent:.4g}%  ·  {2.5*percent:.4g} mm/s TCP  ·  {0.003*percent:.4g} rad/s per joint'


def remote_runtime_command(script, args=(), *, environment=False):
    runtime = os.environ.get('UWA_MINIMAL_RUNTIME')
    if not runtime:
        return 'bash ~/uwa-ur-runtime/' + script + (' ' + shlex.join(args) if args else '')
    if not Path(runtime).is_absolute():
        raise ValueError('UWA_MINIMAL_RUNTIME must be an absolute N100 runtime path')
    command = ['bash', str(Path(runtime)/script), *args]
    if environment:
        command = ['env', 'UWA_PROTECTION_BACKEND=minimal',
                   'UWA_MINIMAL_RUNTIME='+runtime,
                   'UWA_MINIMAL_INSTALL='+str(Path(runtime)/'install_lyrical'), *command]
    return shlex.join(command)


class ReviewPanel(QtWidgets.QWidget):
    attention = QtCore.Signal(str)
    faultNotice = QtCore.Signal(str)
    audit = QtCore.Signal(str, object)
    safeToQuit = QtCore.Signal()

    def __init__(self, backend, *, remote=False, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.remote = remote
        self.status = None
        self.item = None
        self.export = None
        self.key = None
        self.failed_export = None
        self.export_request_key = None
        self.retried_export = None
        self.next_action = None
        self.current = None
        self.closing_session = False
        self.active_session = None
        self.stopping = False
        self.revoking = False
        self.ignore_reply = False
        self.unseen = set()
        self.history_ids = None
        self.speed_draft = None
        self.photo = QtGui.QPixmap()
        self.photo_dialog = None
        self.cache = tempfile.TemporaryDirectory(prefix='uwa-review-gui-')
        self.preview_path = Path(self.cache.name) / 'revision.json'
        self.player = QtCore.QProcess(self)
        self.player.finished.connect(self.player_finished)
        self.player.errorOccurred.connect(lambda _: self.feedback.setText('RViz could not start.') if
                                         self.player.error() == QtCore.QProcess.ProcessError.FailedToStart else None)
        self.rpc = QtCore.QProcess(self)
        self.rpc.finished.connect(self.receive)
        self.rpc.errorOccurred.connect(self.rpc_error)
        self.veto = QtCore.QProcess(self)
        self.veto.finished.connect(self.veto_finished)
        self.veto.errorOccurred.connect(lambda error: self.veto_finished(127) if
            error == QtCore.QProcess.ProcessError.FailedToStart else None)
        page = QtWidgets.QVBoxLayout(self)
        page.setContentsMargins(10, 6, 10, 8)

        self.session = plain('Checking the work-area release…')
        self.session.setStyleSheet('font-weight:bold;color:#17394f')
        self.area_button = QtWidgets.QPushButton('Release work area for session')
        self.area_button.clicked.connect(self.toggle_area)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.session, 1)
        row.addWidget(self.area_button)
        page.addLayout(row)

        self.requests = QtWidgets.QComboBox()
        self.requests.currentIndexChanged.connect(self.select)
        page.addWidget(self.requests)
        self.summary = plain('Checking for a motion request…')
        self.summary.setStyleSheet('background:#e5edf6;color:#142841;font-weight:700;padding:8px')
        page.addWidget(self.summary)
        self.details = plain()
        page.addWidget(self.details)
        self.schedule = plain()
        self.schedule.hide()
        page.addWidget(self.schedule)
        self.picture = QtWidgets.QPushButton()
        self.picture.setAccessibleName('Inspect the supplied contact photograph')
        self.picture.clicked.connect(self.show_photo)
        self.picture.setStyleSheet('text-align:left;background:white;color:#10253c;border:2px solid #294866')
        self.picture.hide()
        page.addWidget(self.picture)
        row = QtWidgets.QHBoxLayout()
        self.preview = QtWidgets.QPushButton('Open RViz')
        self.preview.clicked.connect(self.open_preview)
        row.addWidget(self.preview)
        self.decisions = {}
        for action, label in [('approve', 'Approve'), ('replan', 'Request new plan'), ('reject', 'Reject')]:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _, value=action: self.decide(value))
            self.decisions[action] = button
            row.addWidget(button)
        self.decisions['approve'].setStyleSheet(
            'QPushButton:enabled{background:#075d54;color:white;border:1px solid #075d54}'
            'QPushButton:disabled{background:#e8edf4;color:#596a7c}')
        page.addLayout(row)

        settings = QtWidgets.QGroupBox('Task settings')
        grid = QtWidgets.QGridLayout(settings)
        self.trust = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.trust.setRange(0, 2)
        self.trust.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.trust.setTickInterval(1)
        self.trust.setAccessibleName('Task confidence')
        self.trust_value = plain()
        self.trust.valueChanged.connect(lambda value: self.trust_value.setText(TRUST[value]))
        self.save_trust = QtWidgets.QPushButton('Apply trust')
        self.save_trust.clicked.connect(lambda: self.command(['settings', '--trust', str(50*self.trust.value())]))
        grid.addWidget(plain('Trust'), 0, 0)
        grid.addWidget(self.trust, 0, 1)
        grid.addWidget(self.trust_value, 1, 1)
        grid.addWidget(self.save_trust, 0, 2)

        self.speed = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        # Thirds of one percent represent the existing 0.1 rad/s baseline exactly.
        self.speed.setRange(1, 300)
        self.speed.setAccessibleName('Motion speed limit in percent')
        self.speed_value = plain()
        self.speed.valueChanged.connect(self.change_speed)
        self.save_speed = QtWidgets.QPushButton('Apply speed')
        self.save_speed.clicked.connect(lambda: self.command(['settings', '--speed-percent', str(self.speed_draft)]))
        grid.addWidget(plain('Speed limit'), 2, 0)
        grid.addWidget(self.speed, 2, 1)
        grid.addWidget(self.speed_value, 3, 1)
        grid.addWidget(self.save_speed, 2, 2)

        self.series = plain()
        self.series_button = QtWidgets.QPushButton('Authorize test series…')
        self.series_button.clicked.connect(self.edit_series)
        grid.addWidget(self.series, 4, 0, 1, 2)
        grid.addWidget(self.series_button, 4, 2)
        page.addWidget(settings)
        self.feedback = plain('Connecting…')
        self.feedback.setStyleSheet('background:#17314a;color:white;font-weight:700;padding:8px')
        page.addWidget(self.feedback)
        page.addStretch(1)
        self.controls()
        self.timer = QtCore.QTimer(self, interval=2000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        QtCore.QTimer.singleShot(0, self.refresh)

    def controls(self):
        connected = self.status is not None
        busy = (self.current and self.current[0] not in ('status', 'export')) or self.next_action or self.revoking
        enabled = connected and not busy
        for control in (self.area_button, self.trust, self.speed, self.save_trust,
                        self.save_speed, self.series_button):
            control.setEnabled(bool(enabled))
        self.save_speed.setEnabled(bool(enabled and self.speed_draft is not None))
        self.area_button.setEnabled(bool((self.active_session or enabled) and not self.revoking))
        self.series_button.setEnabled(bool(enabled and self.status['area_released']))
        self.preview.setEnabled(bool(self.export and self.export['preview'].get('robot_description')
                                     and self.export['preview'].get('start')))
        pending = self.item and self.item.get('status') == 'pending'
        for kind, button in self.decisions.items():
            allowed = enabled and pending
            if kind == 'approve':
                allowed = allowed and self.export and self.status.get('area_released')
                if self.item and self.item.get('stage') == 'contact':
                    allowed = allowed and not self.photo.isNull()
            button.setEnabled(bool(allowed))

    def change_speed(self, value):
        self.speed_draft = value / 3
        self.speed_value.setText(speed_text(self.speed_draft))
        self.controls()

    def refresh(self):
        if self.current is None and not (self.revoking or self.closing_session or self.stopping):
            self.run(['status'])

    def command(self, args):
        if self.current:
            if self.current[0] in ('status', 'export') and self.next_action is None:
                self.next_action = args
                self.controls()
            return
        self.run(args)

    def run(self, args):
        self.current = args
        if args[0] == 'export':
            self.export_request_key = self.key
        if args[0] not in ('status', 'export'):
            self.feedback.setText('Sending operator decision…')
        self.controls()
        self.start_rpc(self.rpc, args)

    def start_rpc(self, process, args):
        params = [*args, '--json']
        if self.remote:
            # SSH joins argv into a remote shell command. Quote user-supplied series names.
            params = [remote_runtime_command('review.sh', params, environment=True)]
        process.start(self.backend[0], [*self.backend[1:], *params])

    def rpc_error(self, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart and self.current:
            self.receive(127)

    def receive(self, code, *_):
        if not self.current or self.stopping:
            return
        args, self.current = self.current, None
        verb = args[0]
        raw = bytes(self.rpc.readAllStandardOutput())
        error = bytes(self.rpc.readAllStandardError()).decode(errors='replace').strip()
        if self.ignore_reply:
            self.ignore_reply = False
            self.refresh()
            return
        if verb == 'export' and self.export_request_key != self.key:
            self.continue_requests()
            return
        try:
            # The remote backend is ssh. A broken connection may leave a
            # partial JSON document. The backend itself reports domain errors as JSON.
            if verb == 'export' and self.remote and code == 255:
                raise ConnectionError(error.splitlines()[-1] if error else 'SSH connection lost')
            data = json.loads(raw) if raw.strip() else {}
            if code or data.get('error'):
                raise ValueError(data.get('error') or (error.splitlines()[-1] if error else f'Backend exited ({code})'))
            if verb == 'status':
                self.render_status(data)
            elif verb == 'export':
                if self.export_request_key != (data['id'], data['sha256']):
                    raise ValueError('Export revision has changed. Refresh the request.')
                self.render_export(data)
                if self.retried_export == self.key:
                    self.feedback.setText('Reviewed preview loaded after retry.')
            else:
                self.render_status(data)
                self.feedback.setText('Decision recorded.')
        except (ConnectionError, ValueError, TypeError, KeyError, IndexError) as exc:
            self.audit.emit('review connection' if verb == 'status' else 'review error', str(exc)[:700])
            retry = verb == 'export' and isinstance(exc, ConnectionError) and self.retried_export != self.key
            if verb == 'status':
                self.status = None
                self.session.setText('CONNECTION LOST · Work area status unknown')
                self.summary.setText('Motion review unavailable')
                self.item = None
                self.clear_export()
                self.key = None
            elif verb == 'export':
                if retry:
                    self.retried_export = self.key
                else:
                    self.failed_export = self.key
                self.clear_export()
            self.closing_session = False
            self.feedback.setText(('Retrying preview transfer · ' if retry else 'Request failed · ') + str(exc)[:350])
        self.continue_requests()

    def continue_requests(self):
        self.controls()
        queued, self.next_action = self.next_action, None
        if queued and self.status:
            self.run(queued)
        else:
            self.fetch_if_needed()

    def revoke_area(self):
        # Keep revocation responsive during an image transfer or outstanding decision.
        if not self.active_session or self.revoking:
            return
        self.revoking = True
        self.ignore_reply = self.current is not None
        self.next_action = None
        self.feedback.setText('Revoking the work-area release…')
        self.controls()
        self.start_rpc(self.veto, ['area', '--state', 'revoke', '--session', self.active_session])

    def veto_finished(self, code, *_):
        if not self.revoking or self.stopping:
            return
        self.revoking = False
        raw = bytes(self.veto.readAllStandardOutput())
        self.veto.readAllStandardError()
        try:
            data = json.loads(raw) if raw.strip() else {}
            if code or data.get('error') or data['area_released']:
                raise ValueError(data.get('error') or 'No acknowledgement')
            self.render_status(data)
            self.feedback.setText('WORK AREA RELEASE REVOKED')
            if self.closing_session:
                self.timer.stop()
                self.safeToQuit.emit()
        except (TypeError, KeyError, ValueError) as exc:
            self.closing_session = False
            self.feedback.setText('REVOCATION UNCONFIRMED · ' + str(exc))
        self.controls()

    def awaiting_operator(self, item):
        settings = self.status["settings"]
        threshold = {"low": 50, "medium": 100}.get(item.get("risk"), 101)
        return (not self.status.get("area_released") or item.get("explicit_regular_start")
                or settings["trust"] < threshold or item.get("task") != settings.get("task"))

    def render_status(self, data):
        settings, items = data['settings'], data['pending']
        self.audit.emit('review connection', 'connected')
        self.audit.emit('review state', {'area_released': data['area_released'], 'settings': settings,
                                        'requests': [(row['id'], row['status']) for row in items],
                                        'latest': (data.get('history') or [None])[0]})
        previous = (self.status or {}).get('settings', {})
        reconnect = self.status is None
        self.status = data
        self.active_session = data['session_id'] if data['area_released'] else None
        self.session.setText('WORK AREA RELEASED · Current session' if data['area_released'] else 'WORK AREA AWAITS RELEASE')
        self.area_button.setText('Revoke area release' if data['area_released'] else 'Release work area for session')
        if settings['trust'] != previous.get('trust'):
            self.trust.setValue((0, 50, 100).index(settings['trust']))
            self.trust_value.setText(TRUST[self.trust.value()])
        if settings['speed_percent'] != previous.get('speed_percent'):
            with QtCore.QSignalBlocker(self.speed):
                self.speed.setValue(round(3*settings['speed_percent']))
            self.speed_draft = None
            self.speed_value.setText(speed_text(settings['speed_percent']))
        series = settings.get('series')
        self.series.setText(f"Test series · {series['name']} · minimum {series['min_percent']:g}%"
                            if series else 'Agent speed reductions require your consent.')
        self.series_button.setText('End test series' if series else 'Authorize test series…')
        fresh = [item for item in items if item['status'] == 'pending' and item['id'] not in self.unseen and self.awaiting_operator(item)]
        self.unseen = {item['id'] for item in items if self.awaiting_operator(item)}
        prev_id = fresh[0]['id'] if fresh else self.key[0] if self.key else None
        with QtCore.QSignalBlocker(self.requests):
            self.requests.clear()
            for item in items:
                self.requests.addItem(f"{item['status'].upper()} · {item['summary']}", item)
            index = next((i for i, item in enumerate(items) if item['id'] == prev_id), 0 if items else -1)
            self.requests.setCurrentIndex(index)
        self.requests.setVisible(len(items) > 1)
        self.select()
        if fresh:
            self.attention.emit(fresh[0]['summary'])
        history = data.get('history') or []
        recent = next(iter(history), None)
        if recent and not items:
            self.details.setText('Last request · ' + recent['status'].upper()
                                 + (' · ' + recent['reason'] if recent.get('reason') else ''))
            if recent['status'] in ('blocked', 'failed', 'interrupted'):
                self.summary.setText('CARTON PILOT · ' + recent['status'].upper())
        if self.history_ids is not None:
            faults = [row for row in history if row['id'] not in self.history_ids
                      and row['status'] in ('blocked', 'failed', 'interrupted')]
            if faults:
                message = faults[0].get('reason') or 'Carton execution interrupted'
                if len(faults) > 1:
                    message = f'{len(faults)} interrupted requests · Latest: {message}'
                self.faultNotice.emit(message)
        self.history_ids = {row['id'] for row in history}
        if reconnect or self.feedback.text().startswith('Decision recorded.'):
            self.feedback.setText('Motion review connected.' if reconnect else 'Decision recorded.')
        self.controls()

    def clear_export(self):
        if self.photo_dialog is not None:
            self.photo_dialog.close()
        self.export = None
        self.photo = QtGui.QPixmap()
        self.picture.hide()
        self.schedule.hide()
        if self.player.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.player.terminate()

    def select(self, *_):
        item = self.requests.currentData()
        key = (item['id'], item['sha256']) if item else None
        changed = self.key != key
        self.key, self.item = key, item
        if changed:
            self.clear_export()
            self.failed_export = None
            self.retried_export = None
        if not item:
            self.summary.setText('No pending motion review')
            self.details.clear()
            self.controls()
            return
        state = 'DECISION REQUIRED' if item['status'] == 'pending' else item['status'].upper()
        if item['status'] == 'pending' and not self.awaiting_operator(item):
            state = 'AWAITING AUTOMATIC RELEASE'
        self.summary.setText(state + ' · ' + item['summary'])
        arms = ', '.join(arm.replace('_', ' ').capitalize() for arm in item['arms'])
        clock = f"  ·  {item['duration_s']:.1f} s" if item['stage'] == 'motion' else '  ·  Held in place'
        self.details.setText(f"{item['risk'].upper()} risk  ·  {item['reason']}\n{arms}{clock}\n"
                             f"Arm speed cap  ·  {speed_text(item['speed_percent'])}  ·  Plan {item['sha256'][:12]}")
        self.preview.setText('Show held pose in RViz' if item['stage'] == 'contact' else 'Open RViz')
        if item.get('explicit_regular_start'):
            self.details.setText(self.details.text() + '\nIncludes a regular External Control program start.'
                                 + (' Required for ' + ', '.join(item['program_start_arms']) if item.get('program_start_arms') else ''))
        self.controls()
        if changed and not self.current and self.export is None:
            QtCore.QTimer.singleShot(0, self.fetch_if_needed)

    def fetch_if_needed(self):
        if self.key and not (self.current or self.revoking or self.closing_session or self.stopping) and self.export is None and self.key != self.failed_export:
            self.run(['export', '--id', self.key[0]])

    def render_export(self, data):
        if self.key != (data['id'], data['sha256']):
            return
        groups = data['preview'].get('groups', [])
        if groups:
            names = {'high': 'High approach', 'entry': 'Open entry'}
            lines = []
            for group in groups:
                arms = ' + '.join(arm.replace('_', ' ') for arm in group['arms'])
                lines.append(f"{names.get(group['phase'], group['phase'])}  ·  {arms}")
            self.schedule.setText('  →  '.join(lines))
            self.schedule.show()
        image = data['preview'].get('image')
        if self.item['stage'] == 'contact':
            original = self.item.get('capture_sha256', '')
            if not image or len(original) != 64 or image.get('original_sha256') != original:
                raise ValueError('Contact photograph does not match the requested capture')
        if image:
            raw = base64.b64decode(image['data_base64'], validate=True)
            if image.get('display_sha256') and hashlib.sha256(raw).hexdigest() != image['display_sha256']:
                raise ValueError('Contact photograph preview bytes changed')
            pixmap = QtGui.QPixmap()
            formats = {'image/jpeg': 'JPEG', 'image/png': 'PNG'}
            if image.get('mime_type') not in formats or not pixmap.loadFromData(raw, formats[image['mime_type']]):
                raise ValueError('Image could not be decoded')
            self.photo = pixmap
            caption = 'Inspect contact photograph'
            if image.get('captured_at'):
                caption += '\n' + image['captured_at']
            self.picture.setText(caption)
            self.picture.setIcon(QtGui.QIcon(pixmap))
            self.picture.setIconSize(QtCore.QSize(180, 92))
            self.picture.show()
        self.preview_path.write_text(json.dumps(data, allow_nan=False))
        self.export = data

    def show_photo(self):
        if self.photo.isNull():
            return
        viewer = QtWidgets.QDialog(self)
        viewer.setWindowTitle('Contact photograph · ' + self.key[1][:12])
        self.photo_dialog = viewer
        layout = QtWidgets.QVBoxLayout(viewer)
        instruction = (' · Check the open left-rear pads around the pen adapter, the holder rim and vertical lift clearance.'
                       if self.item.get('task') == 'pen_holder_grasp'
                       else ' · Check support and both open grippers around the carton walls.')
        layout.addWidget(plain(f'Contact review · {self.photo.width()} × {self.photo.height()} pixels' + instruction))
        scene = QtWidgets.QGraphicsScene(viewer)
        item = scene.addPixmap(self.photo)
        canvas = QtWidgets.QGraphicsView(scene, viewer)
        canvas.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        canvas.setBackgroundBrush(QtGui.QColor('#10253c'))
        canvas.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        layout.addWidget(canvas)
        actions = QtWidgets.QHBoxLayout()
        fit = lambda: canvas.fitInView(item, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        for caption, action in [('Fit image', fit), ('100%', canvas.resetTransform),
                                ('Zoom in', lambda: canvas.scale(1.5, 1.5)),
                                ('Zoom out', lambda: canvas.scale(1/1.5, 1/1.5))]:
            button = QtWidgets.QPushButton(caption)
            button.clicked.connect(action)
            actions.addWidget(button)
        layout.addLayout(actions)
        available = self.screen().availableGeometry()
        viewer.resize(min(1200, available.width()-50), min(850, available.height()-50))
        QtCore.QTimer.singleShot(0, fit)
        viewer.exec()
        self.photo_dialog = None

    def open_preview(self):
        if not self.export or self.player.state() != QtCore.QProcess.ProcessState.NotRunning:
            return
        self.feedback.setText('Opening the reviewed trajectory in RViz…')
        self.player.start('/usr/bin/bash', ['-c',
            'source "$1" && exec /usr/bin/python3 "$2" "$3"', 'uwa-review',
            str(ROOT.parents[1] / 'install_lyrical/setup.bash'), str(ROOT/'scripts/motion_review_view.py'),
            str(self.preview_path)])

    def player_finished(self, code, *_):
        detail = bytes(self.player.readAllStandardError()).decode(errors='replace').strip()
        self.player.readAllStandardOutput()
        if code and self.export:
            self.feedback.setText('RViz closed · ' + (detail.splitlines()[-1][-250:] if detail else str(code)))
        elif self.feedback.text().startswith('Opening'):
            self.feedback.setText('RViz preview closed.')

    def decide(self, decision):
        if self.key and self.decisions[decision].isEnabled():
            self.command(['decide', '--id', self.key[0], '--sha256', self.key[1], '--decision', decision])

    def toggle_area(self):
        if self.active_session:
            self.revoke_area()
        elif self.status:
            self.command(['area', '--state', 'release', '--session', self.status['session_id'] or 'new'])

    def edit_series(self):
        settings = self.status['settings']
        if settings.get('series'):
            self.command(['settings', '--end-series'])
            return
        name, ok = QtWidgets.QInputDialog.getText(self, 'Authorize test series', 'Test series name')
        if not ok or not name.strip():
            return
        current = settings['speed_percent']
        minimum, ok = QtWidgets.QInputDialog.getDouble(self, 'Authorize agent speed reductions',
            'Lowest speed the agent may select for this series (%)', current, min(.01, current), current, 2)
        if ok:
            self.command(['settings', '--series-name', name.strip(), '--series-min-percent', str(minimum)])

    def request_quit(self):
        if self.active_session:
            self.closing_session = True
            self.revoke_area()
        elif self.next_action or (self.current and self.current[0] not in ('status', 'export')):
            self.feedback.setText('Waiting for the current decision to finish. Try Quit again.')
        else:
            self.safeToQuit.emit()

    def shutdown(self):
        self.stopping = True
        self.timer.stop()
        for process in (self.rpc, self.veto):
            if process.state() != QtCore.QProcess.ProcessState.NotRunning:
                process.kill()
                process.waitForFinished(800)
        if self.player.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.player.terminate()
            self.player.waitForFinished(7000)
        self.cache.cleanup()

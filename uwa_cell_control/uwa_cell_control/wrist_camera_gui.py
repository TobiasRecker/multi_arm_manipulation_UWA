"""Independent Qt window for the real Robotiq camera; no ROS/motion connection."""
import os
for _name in ('GTK_PATH', 'GTK_EXE_PREFIX', 'GTK_IM_MODULE_FILE', 'GIO_MODULE_DIR'):
    if '/snap/' in os.environ.get(_name, ''):
        os.environ.pop(_name, None)

import argparse
from datetime import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import queue
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

from python_qt_binding import QtCore, QtGui, QtWidgets
import yaml
from .wrist_camera import WristCamera, save_snapshot


class CameraWorker(QtCore.QThread):
    frame = QtCore.Signal(bytes, object)
    settings_ready = QtCore.Signal(object)
    message = QtCore.Signal(str, bool)

    def __init__(self, camera, directory, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.directory = Path(directory)
        self.commands = queue.Queue()
        self.original = None
        self.current = None
        self.last_image = None
        self.focus_touched = False

    def run(self):
        try:
            self.original = self.camera.settings()
            self.current = self.original
            self.directory.mkdir(parents=True, exist_ok=True)
            (self.directory/'original_settings.json').write_text(json.dumps(self.original, indent=2)+'\n')
            self.settings_ready.emit(self.current)
            self.message.emit('Connected. Focus unchanged; preview polling at 2 Hz.', False)
        except Exception as error:
            self.message.emit(f'Connection failed: {error}. Close and reopen to retry.', True)
            return
        deadline = 0.
        settings_deadline = time.monotonic()+3
        while True:
            try:
                action, value = self.commands.get(timeout=.05)
            except queue.Empty:
                action, value = '', None
            try:
                if action in ('close', 'restore'):
                    if action == 'restore' or (value and self.focus_touched):
                        self.current = self.camera.restore(self.original)
                        self.settings_ready.emit(self.current)
                        self.message.emit('Original focus and Auto/Manual mode restored.', False)
                        self.focus_touched = False
                    if action == 'close':
                        return
                elif action == 'manual':
                    self.focus_touched = True
                    self.current = self.camera.manual(value)
                    self.settings_ready.emit(self.current)
                    self.message.emit(f'Applied and read back: manual focus {value} (API {1023-value}).', False)
                    settings_deadline = time.monotonic()+3
                elif action == 'autofocus':
                    self.focus_touched = True
                    self.current = self.camera.refocus()
                    self.settings_ready.emit(self.current)
                    self.message.emit('Autofocus trigger completed; check the image.', False)
                elif action == 'save':
                    self.current = self.camera.settings()
                    jpeg = self.camera.image()
                    name = datetime.now(ZoneInfo('Australia/Perth')).strftime('%Y%m%d_%H%M%S_%f')
                    path = save_snapshot(self.directory, name, jpeg, self.current)
                    self.message.emit(f'Saved {path}', False)
                if time.monotonic() >= settings_deadline:
                    self.current = self.camera.settings()
                    self.settings_ready.emit(self.current)
                    settings_deadline = time.monotonic()+3
                if time.monotonic() >= deadline:
                    jpeg = self.camera.image()
                    self.last_image = jpeg
                    self.frame.emit(jpeg, {'received': time.time(), 'settings': dict(self.current)})
                    deadline = time.monotonic()+.5
            except Exception as error:
                self.message.emit(f'{action or "Preview"} failed: {error}', True)
                deadline = settings_deadline = time.monotonic()+2


class Window(QtWidgets.QMainWindow):
    def __init__(self, ip, directory):
        super().__init__()
        self.lock = (Path(tempfile.gettempdir())/f'uwa-wrist-focus-{ip}.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('A focus window already owns this camera')
        self.directory = Path(directory)
        self.pixmap = None
        self.previous_hash = None
        self.changed_at = time.monotonic()
        self.closing = False
        self.slider_edited = False
        self.setWindowTitle('UWA · Right rear wrist camera')
        self.resize(1060, 900)
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)
        heading = QtWidgets.QLabel(f'RIGHT REAR · {ip}:4242 · Camera controls only')
        heading.setStyleSheet('font-size: 20px; font-weight: bold;')
        layout.addWidget(heading)
        self.image_label = QtWidgets.QLabel('Connecting to camera…')
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet('background: #141414; color: white;')
        layout.addWidget(self.image_label, 1)
        self.image_status = QtWidgets.QLabel('No image received')
        self.image_status.setWordWrap(True)
        layout.addWidget(self.image_status)
        self.settings_label = QtWidgets.QLabel('Reading focus settings…')
        layout.addWidget(self.settings_label)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel('Manual focus (Robotiq scale):'))
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1023)
        self.slider.setValue(512)
        self.spin = QtWidgets.QSpinBox()
        self.spin.setRange(0, 1023)
        self.spin.setValue(512)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        self.slider.valueChanged.connect(self.edited)
        row.addWidget(self.slider, 1)
        row.addWidget(self.spin)
        layout.addLayout(row)
        hint = QtWidgets.QLabel('Adjust the slider, then Apply manual focus. Units are not metres. '
                               'Original focus is saved on connection. Preview has no sensor timestamp.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QtWidgets.QHBoxLayout()
        self.apply_button = QtWidgets.QPushButton('Apply manual focus')
        self.restore_button = QtWidgets.QPushButton('Restore original focus')
        self.auto_button = QtWidgets.QPushButton('Run autofocus')
        self.save_button = QtWidgets.QPushButton('Save photo + settings')
        self.buttons = (self.apply_button, self.auto_button, self.restore_button, self.save_button)
        for button in self.buttons:
            button.setMinimumHeight(46)
            button.setEnabled(False)
            buttons.addWidget(button)
        self.apply_button.clicked.connect(lambda: self.submit('manual', self.spin.value()))
        self.restore_button.clicked.connect(lambda: self.submit('restore'))
        self.auto_button.clicked.connect(lambda: self.submit('autofocus'))
        self.save_button.clicked.connect(lambda: self.submit('save'))
        layout.addLayout(buttons)
        self.restore_on_close = QtWidgets.QCheckBox('Restore original focus when closing')
        self.restore_on_close.setChecked(True)
        layout.addWidget(self.restore_on_close)
        self.feedback = QtWidgets.QLabel('CONNECTING')
        self.feedback.setWordWrap(True)
        self.feedback.setMinimumHeight(64)
        layout.addWidget(self.feedback)
        self.worker = CameraWorker(WristCamera(ip), directory, self)
        self.worker.frame.connect(self.show_frame)
        self.worker.settings_ready.connect(self.show_settings)
        self.worker.message.connect(self.show_message)
        self.worker.finished.connect(self.worker_done)
        self.worker.start()

    def edited(self):
        self.slider_edited = True

    def submit(self, action, value=None):
        for button in self.buttons:
            button.setEnabled(False)
        self.show_message(f'RUNNING · {action}', False)
        self.worker.commands.put((action, value))

    def show_settings(self, settings):
        self.settings_label.setText(f'Server mode: {"AUTO" if settings["focusAuto"] else "MANUAL"} · '
                                    f'API focus value: {settings["focus"]} · Robotiq display: {1023-settings["focus"]}')
        if not self.slider_edited:
            self.slider.setValue(max(0, min(1023, 1023-settings['focus'])))
            self.slider_edited = False

    def show_message(self, message, failed):
        if failed and self.closing:
            self.closing = False
        self.feedback.setText(('FAILED · ' if failed else '')+message)
        self.feedback.setStyleSheet('background: '+('#9c1c20' if failed else '#13446b')+
                                    '; color: white; padding: 10px; font-size: 17px; font-weight: bold;')
        if self.worker.original is not None and not self.closing and not message.startswith('RUNNING'):
            for button in self.buttons:
                button.setEnabled(True)

    def show_frame(self, jpeg, metadata):
        img = QtGui.QImage.fromData(jpeg)
        if img.isNull():
            self.show_message('JPEG could not be decoded', True)
            return
        digest = hashlib.sha256(jpeg).hexdigest()
        if digest != self.previous_hash:
            self.changed_at = time.monotonic()
        self.previous_hash = digest
        self.pixmap = QtGui.QPixmap.fromImage(img)
        self.render_image()
        age = time.monotonic()-self.changed_at
        received = datetime.fromtimestamp(metadata['received'], ZoneInfo('Australia/Perth')).strftime('%H:%M:%S')
        self.image_status.setText(f'{img.width()} × {img.height()} px · received {received} AWST · '
                                  f'image bytes unchanged for {age:.1f} s · '
                                  'HTTP preview; exposure timestamp unavailable')

    def render_image(self):
        if self.pixmap is not None:
            self.image_label.setPixmap(self.pixmap.scaled(self.image_label.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'image_label'):
            self.render_image()

    def closeEvent(self, event):
        if self.worker.isRunning():
            event.ignore()
            if not self.closing:
                self.closing = True
                self.submit('close', self.restore_on_close.isChecked())
            return
        self.lock.close()
        event.accept()

    def worker_done(self):
        if self.closing:
            self.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    ws = Path(os.environ.get('UWA_WS', str(Path.home()/'UWA_ws')))
    parser.add_argument('--inventory', type=Path, default=ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    inventory = yaml.safe_load(args.inventory.read_text())
    ip = inventory['robots']['right_rear']['ip']
    if not ip:
        parser.error('right_rear has no IP in the hardware inventory')
    directory = args.output or ws/'setup/calibration/wrist_focus'/datetime.now(ZoneInfo('Australia/Perth')).strftime('%Y%m%d_%H%M%S')
    app = QtWidgets.QApplication(sys.argv[:1])
    window = Window(ip, directory)
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

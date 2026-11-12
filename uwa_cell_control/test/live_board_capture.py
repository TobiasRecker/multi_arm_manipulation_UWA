"""Explicit camera-only GUI acceptance run; takes one real three-camera set.

Run manually in the control environment. Never collected by pytest.
"""
import fcntl
import json
from pathlib import Path
import sys
import time

from python_qt_binding import QtCore, QtWidgets
from uwa_cell_control.board_capture import CaptureRig, CAMERAS, write_json
from uwa_cell_control.board_capture_gui import Window


def main():
    ws = Path.home() / 'UWA_ws'
    root = ws / 'setup/calibration/three_camera_20261112/gui_check'
    rig = CaptureRig(ws, root)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = Window(rig)
    window.resize(1400, 850)
    window.show()
    report = dict(session=str(rig.session), success=False)
    state = dict(phase='live', deadline=time.monotonic() + 100)

    def ready():
        return (len(window.data) == 3 and all(time.time() - v['received'] < 8 and
            v['kind'] != 'SAVED SNAPSHOT' for v in window.data.values()) and not window.errors)

    def captured(result):
        report['capture'] = result
        write_json(rig.session / 'gui-check.json', report)
        if not result['all_captured']:
            state.update(phase='failed', deadline=time.monotonic())
        else:
            state.update(phase='resumed', deadline=time.monotonic() + 60)
    window.worker.result.connect(captured)

    def tick():
        try:
            phase = state['phase']
            if time.monotonic() > state['deadline']:
                raise RuntimeError('Acceptance timeout during ' + phase + ': ' + str(window.errors))
            if phase == 'live' and ready():
                report['live_before'] = {n: window.data[n] for n in CAMERAS}
                window.grab().save(str(rig.session / 'live-before.png'))
                window.capture.click()
                report['click_acknowledged'] = 'RECEIVED' in window.action.text() and not window.capture.isEnabled()
                state.update(phase='capturing', deadline=time.monotonic() + 150)
            elif phase == 'resumed' and ready():
                report['live_after'] = {n: window.data[n] for n in CAMERAS}
                window.grab().save(str(rig.session / 'live-after.png'))
                window.pause.click()
                state.update(phase='paused', deadline=time.monotonic() + 35)
            elif phase == 'paused' and not window.worker.live and rig.preview.child.poll() is not None:
                with (ws / 'setup/oak4/photos/.capture.lock').open('a') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    report['preview_lock_released'] = True
                report['success'] = report['capture']['all_captured'] and report['click_acknowledged']
                write_json(rig.session / 'gui-check.json', report)
                state.update(phase='closing', deadline=time.monotonic() + 60)
                window.close()
        except Exception as error:
            report['error'] = str(error)
            write_json(rig.session / 'gui-check.json', report)
            state.update(phase='closing', deadline=time.monotonic() + 60)
            window.close()
    timer = QtCore.QTimer()
    timer.timeout.connect(tick)
    timer.start(250)
    app.exec()
    restoration = json.loads((rig.session / 'focus_restoration.json').read_text())
    report['focus_restoration'] = restoration
    report['success'] = report['success'] and all('error' not in value for value in restoration.values())
    write_json(rig.session / 'gui-check.json', report)
    print(json.dumps(dict(success=report['success'], session=str(rig.session), error=report.get('error'))))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    sys.exit(main())

"""Open and verify the real Qt camera window; --exercise tests camera writes only."""
import argparse
import json
import os
from pathlib import Path
import time

from uwa_cell_control.wrist_camera_gui import Window, QtWidgets
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ws = Path(os.environ.get('UWA_WS', str(Path.home()/'UWA_ws')))
    ip = yaml.safe_load((ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml').read_text())['robots']['right_rear']['ip']
    args.output.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication([])
    window = Window(ip, args.output/'photos')
    window.show()
    report = {'ip': ip, 'camera_only': True}

    def wait(predicate, timeout, description):
        deadline = time.monotonic()+timeout
        while not predicate():
            app.processEvents()
            if time.monotonic() > deadline:
                raise TimeoutError(description+': '+window.feedback.text())
            time.sleep(.02)

    def settle(seconds):
        start = time.monotonic()
        wait(lambda: time.monotonic()-start >= seconds, seconds+1, 'settle')

    try:
        wait(lambda: window.pixmap is not None and window.apply_button.isEnabled(), 15, 'preview connection')
        report['live_image'] = True
        if args.exercise:
            window.spin.setValue(511)
            window.apply_button.click()
            wait(lambda: not window.worker.current['focusAuto'] and window.worker.current['focus'] == 512
                 and window.apply_button.isEnabled(), 10, 'manual focus readback')
            settle(2)
            window.grab().save(str(args.output/'manual-focus.png'))
            window.save_button.click()
            wait(lambda: 'Saved ' in window.feedback.text(), 10, 'photo saved')
            report['manual_focus_verified'] = True
            report['photo_saved'] = [str(p) for p in (args.output/'photos').glob('*.jpg')]
            window.restore_button.click()
            wait(lambda: window.worker.current['focusAuto'] == window.worker.original['focusAuto']
                 and 'restored' in window.feedback.text(), 20, 'original focus mode restored')
            settle(3)
            report['restored_mode'] = window.worker.current
            report['original'] = window.worker.original
            report['unrelated_settings_preserved'] = all(window.worker.current[k] == v for k, v in window.worker.original.items()
                                                        if k not in ('focus', 'focusAuto'))
        report['status'] = window.image_status.text()
        report['feedback'] = window.feedback.text()
        window.grab().save(str(args.output/'ready.png'))
        report['success'] = True
    except Exception as error:
        report['error'] = str(error)
        window.close()
        wait(lambda: not window.worker.isRunning(), 20, 'close/restore')
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    if not report.get('success'):
        return 1
    return app.exec()  # Keep the checked window available for the user.


if __name__ == '__main__':
    raise SystemExit(main())

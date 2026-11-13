"""Camera transactions in a separate process; no robot command interfaces."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


class CameraProcess:
    """Disk replies keep native/SDK stdout and large images out of ROS control."""
    def __init__(self, workspace, output):
        self.output = Path(output)
        self.ipc = self.output / 'camera_ipc'
        self.ipc.mkdir(parents=True, exist_ok=False)
        self.log = (self.ipc / 'worker.log').open('w')
        self.child = subprocess.Popen([sys.executable, '-m', __name__, '--workspace', str(workspace),
            '--output', str(self.output / 'photos'), '--ipc', str(self.ipc)],
            stdin=subprocess.PIPE, stdout=self.log, stderr=subprocess.STDOUT,
            text=True, start_new_session=True)
        self.session = None

    def submit(self, method):
        if method not in ('focus', 'capture', 'restore', 'close'):
            raise ValueError('Unknown camera-only request')
        token = uuid.uuid4().hex
        self.child.stdin.write(json.dumps(dict(token=token, method=method))+'\n')
        self.child.stdin.flush()
        return token

    def ready(self, token):
        return (self.ipc / (token+'.json')).exists()

    def result(self, token):
        data = json.loads((self.ipc / (token+'.json')).read_text())
        if not data['success']:
            raise RuntimeError('Camera worker: '+data['error'])
        if 'session' in data:
            self.session = data['session']
        return data.get('result')

    def close(self, spin=lambda: time.sleep(.02)):
        # Never kill a native transaction: EOF/close are handled only AFTER its
        # finally restoration. Robot controllers have already been deactivated.
        try:
            if self.child.poll() is None:
                token = self.submit('close')
                while not self.ready(token) and self.child.poll() is None:
                    spin()
                if self.ready(token):
                    self.result(token)
                else:
                    raise RuntimeError('Camera worker exited without restore confirmation')
        finally:
            self.child.stdin.close()
            while self.child.poll() is None:
                spin()
            self.log.close()


def serve(workspace, output, ipc):
    from .board_capture import CaptureRig, FIVE_CAMERAS
    import cv2
    cv2.setNumThreads(2)  # Bound image-analysis CPU fan-out beside native UR loops.
    workspace, output, ipc = Path(workspace), Path(output), Path(ipc)
    rig = CaptureRig(workspace, output, cameras=FIVE_CAMERAS,
        optics_path=workspace/'src/multi_arm_manipulation_UWA/config/digitization/five_camera_capture.yaml', board='both')
    restored = False
    try:
        for line in sys.stdin:
            request = json.loads(line)
            token, method = request['token'], request['method']
            if len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
                raise ValueError('Invalid request token')
            reply = dict(success=False, session=str(rig.session))
            try:
                if method == 'focus':
                    rig.lock_focus(); restored = False
                elif method == 'capture':
                    reply['result'] = rig.capture_all()
                elif method in ('restore', 'close'):
                    rig.restore_focus(); restored = True
                else:
                    raise ValueError('Unknown camera-only request')
                reply['success'] = True
            except Exception as error:
                reply['error'] = str(error)
            path = ipc/(token+'.json')
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(reply)+'\n'); temporary.replace(path)
            if method == 'close':
                return
    finally:
        if not restored:
            rig.restore_focus()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'output', 'ipc'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    serve(args.workspace, args.output, args.ipc)


if __name__ == '__main__':
    main()

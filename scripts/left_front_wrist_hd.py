#!/usr/bin/env python3
"""Camera-only native HD service for the older left-front CB3 controller."""
import hashlib
from pathlib import Path
import shlex
import sys

from uwa_cell_control import wrist_hd_service
from uwa_cell_control.wrist_hd import NativeCapture, SSH, control_path


IP = '192.168.8.2'
ARM = 'left_front'
RESOURCES = Path(__file__).resolve().parents[1] / 'uwa_cell_control' / 'remote'


class LeftFrontNativeCapture(NativeCapture):
    def __init__(self, ip, ssh, output):
        if ip != IP:
            raise ValueError('The 32-bit helper is scoped to the left-front CB3')
        super().__init__(ip, SSH(ip, control_path('left_front_hd', ip)), output, RESOURCES)

    def bootstrap(self):
        sources = {'wrist_worker.py': (self.resources / 'wrist_worker.py').read_bytes(),
                   'wrist_capture': (self.resources / 'wrist_capture_i686.py').read_bytes()}
        tag = hashlib.sha256(b'\0'.join(sources.values())).hexdigest()[:16]
        remote = '/tmp/uwa_hd_tools_' + tag
        if self.remote == remote:
            return
        self.ssh.run('umask 077; mkdir -p ' + shlex.quote(remote))
        for name, data in sources.items():
            path = shlex.quote(remote + '/' + name)
            self.ssh.run('umask 077; cat > ' + path, data=data)
        self.ssh.run('chmod 700 ' + shlex.quote(remote + '/wrist_capture'))
        self.remote = remote


def main():
    wrist_hd_service.NativeCapture = LeftFrontNativeCapture
    sys.argv = [sys.argv[0], '--arm', ARM]
    return wrist_hd_service.main()


if __name__ == '__main__':
    raise SystemExit(main())

"""Shared photo/video LED leases and crash cleanup for the four UWA wrists."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import fcntl
import json
import os
from pathlib import Path
import shlex
import re
import subprocess
import time


def root():
    return Path(os.environ.get('UWA_WRIST_ACTIVITY_ROOT',
        str(Path(os.environ.get('UWA_WS', str(Path.home() / 'UWA_ws'))) / 'setup/wrist_lighting')))


def directory(ip):
    import ipaddress
    return root() / str(ipaddress.IPv4Address(ip))


def write_json(path, data):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def remote(ip, desired):
    from .wrist_hd import SSH, control_path
    script = Path(__file__).resolve().parents[1] / 'remote/wrist_lighting.py'
    if not script.is_file():
        from ament_index_python.packages import get_package_share_directory
        script = Path(get_package_share_directory('uwa_cell_control')) / 'remote/wrist_lighting.py'
    command = 'python -c ' + shlex.quote(script.read_text())
    result = json.loads(SSH(ip, control_path('lighting', ip)).run(command,
        data=json.dumps(desired).encode(), timeout=15))
    if not result.get('verified'):
        raise RuntimeError('LED change was not verified: ' + str(result))
    return result


def set_active(ip, active):
    """Caller holds the local mutex and exclusive use lock."""
    folder = directory(ip)
    profile = json.loads((folder / 'profile.json').read_text())
    desired = profile['active'] if active else {'lightingMode': 2, 'lightingValue': 0}
    result = remote(ip, desired)
    write_json(folder / 'state.json', dict(active=active, verified=True,
        verified_epoch=time.time(),
        updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), settings=result['settings']))
    return result


class Activity:
    def __init__(self, ip):
        self.ip = ip
        self.folder = directory(ip)
        self.lease = None
        self.started = False

    def __enter__(self):
        if not (self.folder / 'enabled').exists():
            return self
        with (self.folder / 'mutex.lock').open('a') as mutex:
            fcntl.flock(mutex, fcntl.LOCK_EX)
            self.lease = (self.folder / 'use.lock').open('a')
            try:
                try:
                    fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    fcntl.flock(self.lease, fcntl.LOCK_SH)
                else:
                    # Record intent BEFORE touching the camera: the guardian
                    # must also clean up a client killed during the LED write.
                    write_json(self.folder / 'state.json', {'active': True, 'verified': False})
                    set_active(self.ip, True)
                    self.started = True
                    fcntl.flock(self.lease, fcntl.LOCK_SH)
            except BaseException:
                self.lease.close()
                self.lease = None
                raise
        return self

    def __exit__(self, kind, error, trace):
        if self.lease is None:
            return
        with (self.folder / 'mutex.lock').open('a') as mutex:
            fcntl.flock(mutex, fcntl.LOCK_EX)
            self.lease.close()
            self.lease = None
            with (self.folder / 'use.lock').open('a') as use:
                try:
                    fcntl.flock(use, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return
                set_active(self.ip, False)


def photo_activity(function):
    """Cover settings, trigger, burst and restore with the same lighting lease."""
    from functools import wraps
    @wraps(function)
    def wrapped(camera, *args, **kwargs):
        with getattr(camera, 'activity', nullcontext)():
            return function(camera, *args, **kwargs)
    return wrapped


def enroll(ip):
    folder = directory(ip)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'mutex.lock').open('a') as mutex:
        fcntl.flock(mutex, fcntl.LOCK_EX)
        if not (folder / 'profile.json').exists():
            settings = remote(ip, None)['settings']
            write_json(folder / 'profile.json', {'ip': ip,
                'active': {'lightingMode': 2, 'lightingValue': settings['lightingValue'] or 53},
                'original_settings': settings})
        (folder / 'enabled').touch()
    reconcile(ip)


def configure(ip, intensity):
    """Change the active manual intensity; a closed viewer stays dark."""
    if type(intensity) is not int or not 0 <= intensity <= 175:
        raise ValueError('LED intensity must be 0…175')
    folder = directory(ip)
    with (folder / 'mutex.lock').open('a') as mutex:
        fcntl.flock(mutex, fcntl.LOCK_EX)
        profile = json.loads((folder / 'profile.json').read_text())
        profile['active'] = {'lightingMode': 2, 'lightingValue': intensity}
        write_json(folder / 'profile.json', profile)
        with (folder / 'use.lock').open('a') as use:
            try:
                fcntl.flock(use, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return set_active(ip, True)['settings']
            return set_active(ip, False)['settings']


def reconcile(ip):
    folder = directory(ip)
    if not (folder / 'enabled').exists():
        return
    with (folder / 'mutex.lock').open('a') as mutex:
        try:
            fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        with (folder / 'use.lock').open('a') as use:
            try:
                fcntl.flock(use, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            state_file = folder / 'state.json'
            state = json.loads(state_file.read_text()) if state_file.exists() else {}
            if (state.get('active') is False and state.get('verified')
                    and time.time() - state.get('verified_epoch', 0) < 15):
                return
            return set_active(ip, False)


def pending_enrollment(path):
    """Finish a queued camera-only rollout after its measurement owner is done."""
    job = json.loads(path.read_text())
    if job.get('phase') == 'COMPLETE':
        return
    status = Path(job['work_file']).read_text()
    if not re.search(r'^- Status:\s*\*\*abgeschlossen\b', status, re.I | re.M):
        return
    if job.get('phase', 'WAITING') == 'WAITING':
        # Also prove that the controller's native transaction lock is free.
        remote(job['ip'], None)
        job['phase'] = 'STOPPING_OLD_CAMERA_SERVICE'
        write_json(path, job)
        try:
            subprocess.run(['systemctl', '--user', 'stop', job['old_service']], check=True, timeout=5)
        except subprocess.TimeoutExpired:
            return
    state = subprocess.run(['systemctl', '--user', 'show', job['old_service'],
        '-p', 'ActiveState', '--value'], capture_output=True, text=True, timeout=5).stdout.strip()
    if state not in ('inactive', 'failed', ''):
        return
    subprocess.run(['systemctl', '--user', 'start', job['new_service']], check=True, timeout=10)
    enroll(job['ip'])
    job.update(phase='COMPLETE', completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    write_json(path, job)
    print('DEFERRED LED POLICY ENABLED · ' + job['ip'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enroll', nargs='+', help='Enroll idle cameras and save their active lighting profile')
    args = parser.parse_args()
    if args.enroll:
        for ip in args.enroll:
            enroll(ip)
            print('LED POLICY ENABLED · ' + ip, flush=True)
        return
    def check(folder):
        try:
            reconcile(folder.name)
        except Exception as error:
            print('LED CLEANUP RETRY · ' + folder.name + ': ' + str(error), flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        while True:
            if root().exists():
                list(pool.map(check, [p for p in root().iterdir() if p.is_dir() and p.name != 'pending']))
                for path in (root() / 'pending').glob('*.json'):
                    try:
                        pending_enrollment(path)
                    except Exception as error:
                        print('DEFERRED LED POLICY WAITING · ' + str(error), flush=True)
            time.sleep(1)


if __name__ == '__main__':
    main()

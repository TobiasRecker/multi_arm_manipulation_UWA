"""Local discovery/activation of the capture window, without camera ownership changes."""
import json
import os
from pathlib import Path


def process_stamp(pid):
    try:
        fields = Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()
        return fields[19] if fields[0] not in {'Z', 'X'} else None
    except (OSError, ValueError, IndexError):
        return None


def state_path(workspace):
    return Path(workspace) / 'setup/calibration/three_camera_mobile/active-window.json'


def active_window(workspace):
    try:
        value = json.loads(state_path(workspace).read_text())
        if value['stamp'] and process_stamp(value['pid']) == value['stamp']:
            return value
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def register_window(workspace, session, cameras, *, pid=None):
    pid = os.getpid() if pid is None else pid
    value = dict(pid=pid, stamp=process_stamp(pid), session=str(session), cameras=list(cameras))
    if value['stamp'] is None:
        raise ValueError('Capture window process is not running')
    path = state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value) + '\n')
    temporary.replace(path)
    return value


def activation_path(workspace):
    return state_path(workspace).with_name('activate-window.json')


def request_activation(workspace, value):
    path = activation_path(workspace)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(pid=value['pid'], stamp=value['stamp'])) + '\n')
    temporary.replace(path)


def unregister_window(workspace):
    value = active_window(workspace)
    if value and value['pid'] == os.getpid():
        state_path(workspace).unlink(missing_ok=True)


def take_activation(workspace):
    path = activation_path(workspace)
    try:
        value = json.loads(path.read_text())
        path.unlink(missing_ok=True)
        return value == dict(pid=os.getpid(), stamp=process_stamp(os.getpid()))
    except (OSError, ValueError):
        return False

"""LED ownership across nested callers, crashes and failed network writes."""
import fcntl
import json
import multiprocessing
import os
import time

import pytest

from uwa_cell_control import wrist_activity as activity

IP = '192.0.2.1'


@pytest.fixture
def managed(tmp_path, monkeypatch):
    monkeypatch.setenv('UWA_WRIST_ACTIVITY_ROOT', str(tmp_path))
    folder = activity.directory(IP)
    folder.mkdir()
    (folder / 'enabled').touch()
    (folder / 'profile.json').write_text(json.dumps({'active': {'lightingMode': 0, 'lightingValue': 42}}))
    calls = []
    def remote(ip, desired):
        calls.append(desired)
        return {'verified': True, 'settings': dict(desired)}
    monkeypatch.setattr(activity, 'remote', remote)
    return folder, calls


def test_nested_and_independent_users_keep_lights_until_last_release(managed):
    folder, calls = managed
    with activity.Activity(IP):
        with activity.Activity(IP):
            activity.reconcile(IP)
            assert len(calls) == 1
        assert len(calls) == 1
    assert calls == [{'lightingMode': 0, 'lightingValue': 42}, {'lightingMode': 2, 'lightingValue': 0}]
    assert json.loads((folder / 'state.json').read_text())['active'] is False


def test_unenrolled_camera_is_untouched(tmp_path, monkeypatch):
    monkeypatch.setenv('UWA_WRIST_ACTIVITY_ROOT', str(tmp_path))
    monkeypatch.setattr(activity, 'remote', lambda *a: pytest.fail('Unexpected hardware access'))
    with activity.Activity(IP) as lease:
        assert not lease.started
    assert not list(tmp_path.iterdir())


def test_capture_failure_still_switches_lights_off(managed):
    _, calls = managed
    with pytest.raises(RuntimeError, match='JPEG'):
        with activity.Activity(IP):
            raise RuntimeError('JPEG failed')
    assert calls[-1] == {'lightingMode': 2, 'lightingValue': 0}


def test_failed_on_write_leaves_cleanup_intent_for_guardian(managed, monkeypatch):
    folder, calls = managed
    remote = activity.remote
    monkeypatch.setattr(activity, 'remote', lambda *a: (_ for _ in ()).throw(RuntimeError('Lost connection')))
    with pytest.raises(RuntimeError):
        with activity.Activity(IP):
            pytest.fail('Must not capture when illumination is unverified')
    assert json.loads((folder / 'state.json').read_text())['active'] is True
    monkeypatch.setattr(activity, 'remote', remote)
    activity.reconcile(IP)
    assert calls == [{'lightingMode': 2, 'lightingValue': 0}]


def test_process_death_releases_kernel_lease_and_guardian_turns_off(managed):
    folder, calls = managed
    ctx = multiprocessing.get_context('fork')
    ready = ctx.Event()
    def holder():
        with activity.Activity(IP):
            ready.set()
            while True:
                time.sleep(.1)
    process = ctx.Process(target=holder)
    process.start()
    try:
        assert ready.wait(3)
        activity.reconcile(IP)
        assert not calls
        process.kill()
        process.join(3)
        activity.reconcile(IP)
        assert calls == [{'lightingMode': 2, 'lightingValue': 0}]
    finally:
        if process.is_alive():
            process.kill()
            process.join(3)


def test_remote_legacy_led_mapping_and_unrelated_focus_are_verified(monkeypatch):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'remote/wrist_lighting.py'
    spec = importlib.util.spec_from_file_location('lighting_test', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    current = dict(focus=388, focusAuto=False, exposureAuto=False, exposure=60000,
                   gain=19, lightingMode=2, lightingValue=0)
    class Response:
        def __init__(self, value): self.value = value
        def read(self): return json.dumps(self.value).encode()
    class Opener:
        def open(self, request, timeout):
            if '/status' in request.full_url:
                return Response({'current state': 'Normal'})
            if '/hello' in request.full_url:
                return Response({'version': 'UCC-1.11.1.10337'})
            if '/setcamera' in request.full_url:
                desired = json.loads(request.data)['cameraSettings']
                current.update(desired)
                if current['lightingMode'] in (0, 1):
                    current['lightingMode'] = 1 - current['lightingMode']
                return Response({'status': 'failed', 'code': 15})
            return Response({'status': 'succeeded', 'cameraSettings': dict(current)})
    monkeypatch.setattr(m, 'build_opener', lambda *a: Opener())
    result = m.apply({'lightingMode': 1, 'lightingValue': 0})
    assert result['verified'] and result['settings']['focus'] == 388
    assert result['settings']['lightingMode'] == 1


def test_adjusting_closed_viewer_keeps_lights_off_and_open_viewer_updates_profile(managed):
    folder, calls = managed
    activity.configure(IP, 70)
    assert calls[-1] == {'lightingMode': 2, 'lightingValue': 0}
    with activity.Activity(IP):
        assert calls[-1]['lightingValue'] == 70
        activity.configure(IP, 35)
        assert calls[-1]['lightingValue'] == 35
    assert calls[-1]['lightingValue'] == 0
    assert json.loads((folder / 'profile.json').read_text())['active']['lightingValue'] == 35


def test_deferred_rollout_waits_for_owner_completion_and_free_native_lock(tmp_path, monkeypatch):
    work = tmp_path / 'work.md'
    job = tmp_path / 'pending.json'
    original = dict(ip=IP, phase='WAITING', work_file=str(work), old_service='old-camera', new_service='new-camera')
    job.write_text(json.dumps(original))
    work.write_text('- Status: **in Arbeit**\n')
    monkeypatch.setattr(activity, 'remote', lambda *a: pytest.fail('Must not touch active camera'))
    monkeypatch.setattr(activity.subprocess, 'run', lambda *a, **k: pytest.fail('Must not stop active camera'))
    activity.pending_enrollment(job)
    work.write_text('- Status: **abgeschlossen**, test\n')
    def busy(*a): raise RuntimeError('Native lock busy')
    monkeypatch.setattr(activity, 'remote', busy)
    with pytest.raises(RuntimeError, match='lock busy'):
        activity.pending_enrollment(job)
    assert json.loads(job.read_text())['phase'] == 'WAITING'


def test_deferred_rollout_stops_only_old_camera_then_starts_new_and_enrolls_once(tmp_path, monkeypatch):
    from types import SimpleNamespace
    work = tmp_path / 'work.md'
    work.write_text('- Status: **abgeschlossen**\n')
    job = tmp_path / 'pending.json'
    job.write_text(json.dumps(dict(ip=IP, phase='WAITING', work_file=str(work),
        old_service='old-camera', new_service='new-camera')))
    calls = []
    monkeypatch.setattr(activity, 'remote', lambda *a: {'verified': True})
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout='inactive\n')
    monkeypatch.setattr(activity.subprocess, 'run', run)
    monkeypatch.setattr(activity, 'enroll', lambda ip: calls.append(['enroll', ip]))
    activity.pending_enrollment(job)
    assert calls[0] == ['systemctl', '--user', 'stop', 'old-camera']
    assert calls[-2] == ['systemctl', '--user', 'start', 'new-camera']
    assert calls[-1] == ['enroll', IP]
    assert json.loads(job.read_text())['phase'] == 'COMPLETE'
    count = len(calls)
    activity.pending_enrollment(job)
    assert len(calls) == count

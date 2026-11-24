"""The minimal scan consumes shared protection, with no legacy live watchers."""
import io
import json
import sys
from types import SimpleNamespace

import pytest

from uwa_cell_control import parallel_scan as scan


class FakeClient:
    def __init__(self, problem, mode, selected):
        self.problem, self.mode, self.selected = problem, mode, selected
        self.positions = {j: 0. for profile in problem.profiles.values() for j in profile['joint_names']}
        self.handles = {}
        self.calls = []
        self.fail = False

    def create_publisher(self, *args):
        return SimpleNamespace(publish=lambda message: self.calls.append(('status', json.loads(message.data))))

    def create_service(self, kind, name, callback):
        return SimpleNamespace(callback=callback)

    def create_client(self, kind, name):
        return SimpleNamespace(service_is_ready=lambda: True,
                               call_async=lambda request: self.calls.append(('pause_async', name)))

    def connect(self): self.calls.append(('connect',))
    def health(self): self.calls.append(('shared_status',))
    def spin_once(self, timeout_sec): self.calls.append(('spin', timeout_sec))
    def destroy_node(self): self.calls.append(('close',))
    def stop(self): self.calls.append(('pause_all',)); return dict(accepted=True)

    def follow_group(self, trajectories, *, duration_s):
        self.calls.append(('follow_group', trajectories, duration_s))
        if self.fail:
            raise RuntimeError('Ordinary controller rejection')
        for arm, trajectory in trajectories.items():
            self.positions.update(zip(trajectory['joint_names'], trajectory['points'][-1]['positions']))
            self.handles[arm] = SimpleNamespace(accepted=True)


def minimal_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, 'ScanObserver', lambda *a, **k: pytest.fail('Legacy observer started'))
    monkeypatch.setattr(scan, 'DashboardWatch', lambda *a, **k: pytest.fail('Legacy Dashboard watcher started'))
    profiles = {rid: dict(joint_names=[f'{rid}_{i}' for i in range(6)], namespace='/'+rid)
                for rid in scan.ROBOT_IDS}
    problem = SimpleNamespace(profiles=profiles)
    return scan.MinimalParallelMotion(None, profiles, tmp_path, problem=problem,
                                     client_factory=FakeClient, mock=True)


def steps_for(runner):
    return [dict(arm=arm, target=[.01]*6,
                 points=[dict(time=0., positions=[0.]*6, velocities=[0.]*6, accelerations=[0.]*6),
                         dict(time=float(i+1), positions=[.01]*6, velocities=[0.]*6, accelerations=[0.]*6)])
            for i, arm in enumerate(runner.profiles)]


def test_minimal_round_keeps_original_points_and_timing_without_watchers(tmp_path, monkeypatch):
    runner = minimal_runner(tmp_path, monkeypatch)
    expected = {arm: [0.]*6 for arm in runner.profiles}
    runner.wait_ready(expected)
    runner.wait_ready(expected)
    runner.guard()  # No GUI heartbeat, live clock, stationary history or Dashboard state.
    assert not hasattr(runner, 'observer') and not hasattr(runner, 'dashboard_watch')
    steps = steps_for(runner)
    runner.batch(steps)
    call = next(row for row in runner.client.calls if row[0] == 'follow_group')
    assert call[2] == 4.
    for step in steps:
        assert call[1][step['arm']]['points'] is step['points']
        assert call[1][step['arm']]['joint_names'] == runner.profiles[step['arm']]['joint_names']
    assert runner.deactivate() == []
    runner.close()
    assert len([row for row in runner.client.calls if row[0] == 'connect']) == 1
    assert not any(row[0].startswith('pause') for row in runner.client.calls)


def test_controller_error_and_cleanup_do_not_add_a_global_stop(tmp_path, monkeypatch):
    runner = minimal_runner(tmp_path, monkeypatch)
    runner.client.fail = True
    with pytest.raises(RuntimeError, match='controller rejection'):
        runner.batch(steps_for(runner))
    runner.close()
    assert not any(row[0].startswith('pause') for row in runner.client.calls)


def test_only_explicit_cancel_requests_shared_pause(tmp_path, monkeypatch):
    runner = minimal_runner(tmp_path, monkeypatch)
    runner.stop_requested = True
    with pytest.raises(scan.ScanCancelled): runner.guard()
    runner.abort()
    runner.close()
    assert len([row for row in runner.client.calls if row[0] == 'pause_all']) == 1
    report = json.loads((tmp_path/'runtime.json').read_text())
    assert report['phase'] == 'PAUSE_REQUESTED'
    assert report['standstill_confirmed'] is False and report['protection_backend'] == 'minimal'


def test_start_admission_keeps_checked_path_without_retiming(tmp_path, monkeypatch):
    runner = minimal_runner(tmp_path, monkeypatch)
    runner.client.positions[next(iter(runner.client.positions))] = .002
    with pytest.raises(ValueError, match='batch start differs'):
        runner.batch(steps_for(runner))
    assert not any(row[0] == 'follow_group' for row in runner.client.calls)
    assert not any(row[0].startswith('pause') for row in runner.client.calls)


def test_backend_selection_keeps_legacy_default(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, 'MinimalParallelMotion', lambda *a, **k: 'minimal')
    monkeypatch.setattr(scan, 'ParallelMotion', lambda *a, **k: 'legacy')
    monkeypatch.delenv('UWA_PROTECTION_BACKEND', raising=False)
    assert scan.scan_runner(None, {}, tmp_path, workspace=tmp_path) == 'legacy'
    monkeypatch.setenv('UWA_PROTECTION_BACKEND', 'minimal')
    assert scan.scan_runner(None, {}, tmp_path, workspace=tmp_path) == 'minimal'


@pytest.mark.parametrize('backend,audit', [('minimal', False), ('legacy', True)])
def test_camera_worker_does_not_start_standstill_audit_in_minimal(tmp_path, monkeypatch, backend, audit):
    from uwa_cell_control import board_capture, scan_camera_worker
    class Rig:
        def __init__(self, *args, **kwargs): self.audit_stationarity = True; self.session = tmp_path
        def capture_all(self):
            assert self.audit_stationarity is audit
            return dict(all_captured=True)
        def restore_focus(self): pass
    monkeypatch.setattr(board_capture, 'CaptureRig', Rig)
    monkeypatch.setenv('UWA_PROTECTION_BACKEND', backend)
    requests = [dict(token='a'*32, method='capture'), dict(token='b'*32, method='close')]
    monkeypatch.setattr(sys, 'stdin', io.StringIO(''.join(json.dumps(row)+'\n' for row in requests)))
    scan_camera_worker.serve(tmp_path, tmp_path, tmp_path)
    report = json.loads((tmp_path/('a'*32+'.json')).read_text())
    assert report['success'] and report['result'] == dict(all_captured=True)


def test_minimal_gui_routes_shared_commands_without_heartbeat_or_close_stop():
    from uwa_cell_control.parallel_scan_gui import scan_gui_policy
    policy = scan_gui_policy(True)
    assert policy['pause_service'] == '/uwa_cell/protection/pause_all'
    assert policy['resume_service'] == '/uwa_cell/protection/resume_all'
    assert policy['heartbeat'] is False and policy['stop_on_close'] is False
    assert scan_gui_policy(False)['stop_on_close'] is True

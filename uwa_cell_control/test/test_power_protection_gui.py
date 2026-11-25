"""Software stop uses an independent transport and reports acknowledgements truthfully."""
import json
import os
import shlex
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
REPO = Path(__file__).resolve().parents[2]
for directory in ('scripts', 'uwa_cell_control', 'uwa_cell_tasks'):
    sys.path.insert(0, str(REPO / directory))

from PySide6 import QtCore, QtWidgets
from protection_bridge import response_packet
from motion_review_panel import ReviewPanel, remote_runtime_command
from ur_power_gui import ProtectionControls, Window, protection_command, instance_address, present


def wait_for(app, condition):
    deadline = time.monotonic() + 6
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert condition()


def test_confirm_safety_guidance_reports_mode_without_claiming_configuration_changed():
    heading, level, guidance = present(dict(
        code='confirm_safety', state=dict(mode='CONFIRM_SAFETY', safety='NORMAL')))
    assert (heading, level) == ('CHECK ARM', 'warn')
    assert guidance == ('Controller reports CONFIRM_SAFETY. If it persists, '
                        'check the safety message at the Teach Pendant.')
    assert 'configuration' not in guidance.lower()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, 'isSystemTrayAvailable', lambda: False)
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def bridge_command(tmp_path, *, disconnect=False):
    """A local JSON-lines peer; no ROS or robot/network connection."""
    path = tmp_path / 'peer.py'
    requests = tmp_path / 'requests.jsonl'
    status = dict(mode='mock', paused=False, reason='TEST MOCK', collision_data_available=False,
                  warnings=['Missing collision data: test arm'], arms={})
    path.write_text(
        'import json,sys,time\nfrom pathlib import Path\n'
        f'status={status!r}\nrequests=Path({str(requests)!r})\n'
        'def emit(p): print(json.dumps(p),flush=True)\n'
        'emit(dict(event="status",available=True,status=status))\n'
        'for line in sys.stdin:\n'
        ' req=json.loads(line)\n'
        ' with requests.open("a") as f: f.write(line)\n'
        ' op=req["op"]; rid=req["id"]\n'
        ' emit(dict(event="command_result",operation=op,id=rid,phase="running"))\n'
        + (' sys.exit(0)\n' if disconnect else
           ' time.sleep(.08)\n'
           ' status["paused"]=op=="pause_all"\n'
           ' status["arms"]={a:dict(confirmed=True,paused=status["paused"]) '
           'for a in ("left_front","left_rear","right_front","right_rear")}\n'
           ' emit(dict(event="command_result",operation=op,id=rid,phase="done",success=True,status=status))\n')
    )
    return [sys.executable, str(path)], requests


def test_stop_remains_available_during_power_action_and_above_tabs(tmp_path, monkeypatch, app):
    monkeypatch.setenv('UWA_WS', str(tmp_path))
    command, requests = bridge_command(tmp_path)
    # The normal power transport is local and deliberately busy.
    power = [sys.executable, '-c', 'import time; time.sleep(30)']
    window = Window(power, n100=True, protection_transport=command)
    try:
        window.show()
        wait_for(app, lambda: window.protection.available and window.mode == 'status')
        window.mode = 'start'
        window.controls()
        assert not window.start.isEnabled()
        assert window.protection.pause_button.isEnabled()
        assert window.layout().indexOf(window.protection) < window.layout().indexOf(window.tabs)
        window.protection.pause_button.click()
        wait_for(app, lambda: window.protection.paused and 'DONE' in window.protection.result_label.text())
        assert json.loads(requests.read_text().splitlines()[0])['op'] == 'pause_all'
        assert 'Missing collision data' in window.protection.warning_label.text()
        assert all('ACKNOWLEDGED' in item.text() for item in window.protection.arm_labels.values())
        assert 'standstill confirmed' not in window.protection.result_label.text().lower()
        window.tabs.setCurrentWidget(window.review)
        assert window.protection.isVisible()
        window.protection.resume_button.click()
        wait_for(app, lambda: not window.protection.paused and 'RESUME DONE' in window.protection.result_label.text())
        assert [json.loads(line)['op'] for line in requests.read_text().splitlines()] == ['pause_all', 'resume_all']
    finally:
        window.refresh_timer.stop()
        window.process.kill()
        window.process.waitForFinished(500)
        window.mode = None
        window.exiting = True
        window.close()
        app.processEvents()


def test_missing_endpoint_and_transport_loss_never_claim_stop_or_replay(tmp_path, app):
    command, requests = bridge_command(tmp_path, disconnect=True)
    panel = ProtectionControls(command)
    try:
        panel.show()
        wait_for(app, lambda: panel.available)
        panel.pause_button.click()
        wait_for(app, lambda: not panel.available and 'unconfirmed' in panel.result_label.text())
        assert 'UNCONFIRMED' in panel.arm_labels['left_front'].text()
        assert not panel.resume_button.isEnabled()
        panel.connect_transport()
        wait_for(app, lambda: panel.available)
        assert len(requests.read_text().splitlines()) == 1
        panel.handle(dict(event='status', available=False, error='Minimal protection endpoint unavailable'))
        assert 'UNAVAILABLE' in panel.state_label.text()
        assert panel.pause_button.isEnabled()
        assert not panel.resume_button.isEnabled()
    finally:
        panel.shutdown()
        panel.close()


def test_command_result_keeps_warning_and_does_not_turn_ack_into_physical_stop(tmp_path, app):
    panel = ProtectionControls([str(tmp_path / 'does-not-exist')])
    try:
        status = dict(paused=True, reason='operator', collision_data_available=False,
                      warnings=['Camera-independent joint data unavailable'],
                      arms={'left_front': dict(confirmed=False, paused=True)})
        response = response_packet('pause_all', '12', SimpleNamespace(success=True, message=json.dumps(status)))
        panel.handle(response)
        assert 'DONE' in panel.result_label.text()
        assert 'UNCONFIRMED' in panel.arm_labels['left_front'].text()
        assert 'unavailable' in panel.warning_label.text()
        panel.handle(dict(event='status', available=True, status=status))
        assert 'DONE' in panel.result_label.text()
        assert 'unavailable' in panel.warning_label.text()
    finally:
        panel.shutdown()


def test_bridge_mode_and_n100_command_are_explicit(monkeypatch):
    monkeypatch.delenv('UWA_MINIMAL_RUNTIME', raising=False)
    assert protection_command(mock=True)[-1] == 'mock'
    assert protection_command(mock=False)[-1] == 'hardware'
    remote = protection_command(n100=True)
    assert 'uwa-n100-robot-lan' in remote
    assert remote[-1] == 'bash ~/uwa-ur-runtime/protection.sh bridge --mode hardware'
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME', '/home/rosmatch/review candidates/minimal;literal')
    assert protection_command(n100=True)[-1] == (
        "bash '/home/rosmatch/review candidates/minimal;literal/protection.sh' bridge --mode hardware")
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME', 'relative-runtime')
    with pytest.raises(ValueError, match='absolute'):
        protection_command(n100=True)


def test_pause_ramp_and_manual_hold_are_not_presented_as_completed_trajectory_pause(tmp_path, app):
    panel = ProtectionControls([str(tmp_path/'does-not-exist')])
    try:
        panel.render_status(dict(paused=True, state='PAUSE REQUESTED', arms={
            'left_front':dict(confirmed=True, paused=True, factor=.6),
            'right_front':dict(confirmed=True, controller='collision_hold_controller')}))
        assert panel.state_label.text().startswith('PAUSE REQUESTED')
        assert 'PAUSING' in panel.arm_labels['left_front'].text()
        assert 'fresh manual start required' in panel.arm_labels['right_front'].text()
    finally:
        panel.shutdown()


def test_candidate_power_and_review_commands_keep_runtime_and_literal_arguments(monkeypatch):
    runtime = '/home/rosmatch/review candidates/minimal;literal'
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME', runtime)
    power = shlex.split(remote_runtime_command('power.sh', environment=True))
    assert power == ['env', 'UWA_PROTECTION_BACKEND=minimal', 'UWA_MINIMAL_RUNTIME='+runtime,
                     'UWA_MINIMAL_INSTALL='+runtime+'/install_lyrical', 'bash', runtime+'/power.sh']
    captured = []
    process = SimpleNamespace(start=lambda command,args:captured.append((command,args)))
    panel = SimpleNamespace(remote=True,backend=['ssh','test-host'])
    ReviewPanel.start_rpc(panel,process,['settings','--series-name','literal;$(no command)'])
    assert captured[0][0] == 'ssh' and captured[0][1][0] == 'test-host'
    review = shlex.split(captured[0][1][-1])
    assert review[:6] == power[:5]+[runtime+'/review.sh']
    assert review[6:] == ['settings','--series-name','literal;$(no command)','--json']


def test_status_audit_records_semantic_events_once_and_keeps_collision_evidence(tmp_path, app):
    panel = ProtectionControls([str(tmp_path/'does-not-exist')])
    events = []
    panel.audit.connect(lambda kind, value:events.append((kind,value)))
    status = dict(generation=17, paused=True, pausing=True, reason='COLLISION',
        evaluated_monotonic_s=1., warnings=['Missing collision data: left rear'],
        collision_data_available=False,
        known_collisions=[dict(kind='neighbor_margin',links=['a','b'],distance_m=.039,threshold_m=.04)],
        arms={'left_front':dict(confirmed=True,paused=True,factor=.8,phase_time_s=2.,error='')})
    try:
        panel.render_status(status)
        status['evaluated_monotonic_s'] = 20.
        status['arms']['left_front'].update(factor=.3, phase_time_s=2.3)
        status['known_collisions'][0]['distance_m'] = .038
        panel.render_status(status)
        assert len(events) == 1
        kind, value = events[0]
        assert kind == 'protection status' and value['generation'] == 17
        assert value['reason'] == 'COLLISION' and value['state'] == 'PAUSING'
        assert value['known_collisions'][0]['distance_m'] == .039
        assert value['warnings'] == status['warnings']
        assert value['arms']['left_front']['confirmed'] is True
        assert 'factor' not in value['arms']['left_front']
        assert 'evaluated_monotonic_s' not in value
        status['pausing'] = False
        status['arms']['left_front']['factor'] = 0.
        panel.render_status(status)
        panel.render_status(dict(status, evaluated_monotonic_s=21.))
        assert len(events) == 2 and events[-1][1]['state'] == 'PAUSED'
        status['arms']['left_front']['error'] = 'Controller acknowledgement unavailable'
        panel.render_status(status)
        assert len(events) == 3
        assert events[-1][1]['arms']['left_front']['error'] == 'Controller acknowledgement unavailable'
    finally:
        panel.shutdown()


def test_candidate_ipc_identity_is_separate_and_stable_without_changing_default(monkeypatch):
    monkeypatch.delenv('UWA_MINIMAL_RUNTIME',raising=False)
    assert instance_address(uid=1000)=='\0uwa-robot-power-1000'
    first=instance_address(uid=1000,candidate='/home/rosmatch/minimal-a')
    assert first!=instance_address(uid=1000)
    assert first==instance_address(uid=1000,candidate='/home/rosmatch/minimal-a/')
    assert first!=instance_address(uid=1000,candidate='/home/rosmatch/minimal-b')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME','/home/rosmatch/minimal-a')
    assert first==instance_address(uid=1000)
    with pytest.raises(ValueError,match='absolute'):
        instance_address(uid=1000,candidate='relative/minimal')


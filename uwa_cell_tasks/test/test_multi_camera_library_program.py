"""Program routing and failure sequencing without connecting to robots/cameras."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
import run_multi_camera_program as runner
import open_multi_camera_capture as launcher
from uwa_cell_control import capture_window

spec = importlib.util.spec_from_file_location('multi_camera_library', REPO / 'scripts/skill_library_server.py')
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


def test_capture_catalog_independent_of_expired_oak_reference(tmp_path, monkeypatch):
    runs = library.Runs(tmp_path, live_config=tmp_path / 'live.json')
    monkeypatch.setattr(runs, 'camera_status', lambda: dict(calibrate_available=False, live_blocker='Expired'))
    card = next(p for p in runs.catalog()['programs'] if p['id'] == runner.PROGRAM)
    assert card['setup_available'] and card['gui_available']
    assert len(card['arms']) == 4 and len(card['stages']) == 4
    assert 'camera_valid_until' not in card


@pytest.mark.parametrize('mode', ['setup', 'gui'])
def test_routes_to_own_runner_without_carton_config(tmp_path, monkeypatch, mode):
    runs = library.Runs(tmp_path, live_config=tmp_path / 'live.json')
    monkeypatch.setattr(runs, 'camera_status', Mock(side_effect=AssertionError('No OAK reference required')))
    popen = Mock(return_value=Mock(pid=123))
    monkeypatch.setattr(library.subprocess, 'Popen', popen)
    monkeypatch.setattr(library, 'Thread', Mock())
    monkeypatch.setattr(library, 'process_stamp', lambda _: 'process')
    result = runs.start(runner.PROGRAM, mode)
    command = popen.call_args.args[0]
    assert command[1] == str(REPO / 'tools/run_multi_camera_program.py')
    assert command[command.index('--mode') + 1] == mode
    assert '--live-config' not in command and result['program'] == runner.PROGRAM


def test_mock_library_cannot_move_real_arms(tmp_path):
    with pytest.raises(ValueError, match='N100-enabled'):
        library.Runs(tmp_path).start(runner.PROGRAM, 'setup')


def test_gui_action_has_no_robot_preparation(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'prepare_and_move', Mock(side_effect=AssertionError('No robot action')))
    monkeypatch.setattr(runner, 'open_window', lambda: dict(gui='Reused', session='session', reused=True))
    result = runner.run('gui', runner.Progress(tmp_path))
    assert result['reused'] and 'no robot motion' in result['motion']
    assert json.loads((tmp_path / 'progress.json').read_text())['phase'] == 'complete'


def test_failed_motion_never_opens_camera_gui(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'prepare_and_move', Mock(side_effect=RuntimeError('Existing guard stopped')))
    camera = Mock(side_effect=AssertionError('No GUI after failed approach'))
    monkeypatch.setattr(runner, 'open_window', camera)
    with pytest.raises(RuntimeError, match='guard stopped'):
        runner.run('setup', runner.Progress(tmp_path))
    camera.assert_not_called()


def test_open_reuses_live_six_camera_owner_and_rejects_pid_reuse(tmp_path, monkeypatch):
    # Use this real test process as the registered window owner; no Qt needed.
    value = capture_window.register_window(tmp_path, tmp_path / 'session', launcher.CAMERAS)
    monkeypatch.setattr(launcher.subprocess, 'Popen', Mock(side_effect=AssertionError('Do not restart cameras')))
    result = launcher.open_window(tmp_path)
    assert result['reused'] and result['session'] == value['session']
    assert capture_window.take_activation(tmp_path)
    value['stamp'] = 'different-process'
    capture_window.state_path(tmp_path).write_text(json.dumps(value))
    assert capture_window.active_window(tmp_path) is None


def test_other_capture_window_is_preserved(tmp_path):
    capture_window.register_window(tmp_path, tmp_path / 'session', ['right_front', 'right_rear', 'oak4'])
    with pytest.raises(RuntimeError, match='different capture window'):
        launcher.open_window(tmp_path)


@pytest.mark.parametrize('segments, active, fails', [([], False, False), ([{'arm': 'left_front'}], True, True)])
def test_fresh_planning_and_no_replay_when_already_positioned_or_capturing(tmp_path, monkeypatch, segments, active, fails):
    calls = []
    def command(args, log, timeout):
        calls.append([str(a) for a in args])
        if 'prepare_calibration_observation_motion.py' in str(args):
            plans = tmp_path / 'plans'; plans.mkdir()
            (plans / 'sequence.json').write_text(json.dumps(dict(segments=segments)))
        return ''
    def download(remote, destination, log):
        observation = tmp_path / 'observation'; observation.mkdir()
        (observation / 'snapshot.json').write_text(json.dumps(dict(area_session='current-session')))
        (observation / 'model-context.json').write_text('{}')
    monkeypatch.setattr(runner, 'logged_command', command)
    monkeypatch.setattr(runner, 'upload', lambda *a: None)
    monkeypatch.setattr(runner, 'download', download)
    monkeypatch.setattr(runner, 'active_window', lambda _: {'session': 'active'} if active else None)
    if fails:
        with pytest.raises(RuntimeError, match='capture window is active'):
            runner.prepare_and_move(runner.Progress(tmp_path))
    else:
        assert 'no trajectory' in runner.prepare_and_move(runner.Progress(tmp_path))
    assert any('prepare_calibration_observation_motion.py' in str(c) for c in calls)
    assert not any('--sequence-sha256' in str(c) for c in calls)

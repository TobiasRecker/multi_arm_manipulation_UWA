"""Exercise the native dashboard protocol against a loopback controller."""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import socketserver
import sys
import threading

import pytest


script = Path(__file__).resolve().parents[2] / 'scripts/ur_bringup.py'
spec = importlib.util.spec_from_file_location('uwa_ur_bringup', script)
bringup = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bringup
spec.loader.exec_module(bringup)
TARGET = '/programs/ros.urp'
SERIAL = '2017356443'


class Robot:
    serial = SERIAL
    mode = 'POWER_OFF'
    safety = 'NORMAL'
    remote = True
    program = None
    playback = 'STOPPED'
    saved = True
    listener = True
    disable_link = False
    reject = ()
    dropped = ()

    def __init__(self, series, **kwargs):
        self.series = series
        self.commands = []
        self.all = []
        self.__dict__.update(kwargs)

    def reply(self, cmd):
        self.all.append(cmd)
        if cmd == 'get serial number':
            return self.serial
        if cmd == 'PolyscopeVersion':
            return f'URSoftware {self.series}.15.8.106339'
        if cmd == 'robotmode':
            return 'Robotmode: ' + self.mode
        if cmd == ('safetystatus' if self.series == 5 else 'safetymode'):
            return cmd.title() + ': ' + self.safety
        if cmd == 'is in remote control' and self.series == 5:
            return str(self.remote).lower()
        if cmd == 'programState':
            return f'{self.playback} '+(Path(self.program).name if self.program else 'null')
        if cmd == 'get loaded program':
            return 'Loaded program: '+self.program if self.program else 'No program loaded'
        if cmd == 'isProgramSaved':
            return str(self.saved).lower()+' '+self.program
        self.commands.append(cmd)
        if cmd in self.dropped:
            return None
        if cmd in self.reject:
            return 'Error while loading program: ros.urp'
        if cmd == 'load ' + Path(TARGET).name:
            self.program = TARGET
            return 'Loading program: ros.urp'
        if cmd == 'power on':
            self.mode = 'IDLE'
            return 'Powering on'
        if cmd == 'brake release':
            self.mode = 'RUNNING'
            return 'Brake releasing'
        if cmd == 'play':
            self.playback = 'PLAYING'
            return 'Starting program'
        return 'Unknown command: ' + cmd

    def transport(self, arm):
        return self.listener, self.playback == 'PLAYING' and not self.disable_link


@contextmanager
def dashboard(robot):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.wfile.write(b'Connected: Universal Robots Dashboard Server\n')
            for line in self.rfile:
                assert line.endswith(b'\n')
                response = robot.reply(line.decode().strip())
                if response is None:
                    break
                self.wfile.write((response+'\n').encode())
    with socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler) as server:
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, args=(.01,), daemon=True)
        thread.start()
        try:
            yield bringup.Arm('left_front', '127.0.0.1', SERIAL, robot.series,
                              server.server_address[1], TARGET, 51001, 51002)
        finally:
            server.shutdown()
            thread.join()


def run(robot, apply=True):
    with dashboard(robot) as arm:
        return bringup.run_arm(arm, apply, get_transport=robot.transport, transition_timeout=0)


@pytest.mark.parametrize('series', [3, 5])
def test_cold_start_in_order_and_repeat_is_noop(series):
    r = Robot(series)
    assert run(r)['code'] == 'ready'
    assert r.commands == ['load ' + Path(TARGET).name, 'power on', 'brake release', 'play']
    assert run(r)['code'] == 'ready'
    assert len(r.commands) == 4
    assert ('is in remote control' in r.all) == (series == 5)


@pytest.mark.parametrize('config,code', [
    ({'remote':False}, 'local_control'),
    ({'safety':'PROTECTIVE_STOP'}, 'safety_blocked'),
    ({'safety':'ROBOT_EMERGENCY_STOP'}, 'safety_blocked'),
    ({'mode':'CONFIRM_SAFETY'}, 'confirm_safety'),
    ({'program':'/programs/other.urp', 'playback':'PLAYING'}, 'program_in_use'),
    ({'program':TARGET, 'playback':'PAUSED'}, 'program_in_use'),
    ({'program':TARGET, 'saved':False}, 'unsaved_program'),
    ({'serial':'0000000000'}, 'identity_mismatch'),
])
def test_manual_intervention_never_sends_command(config, code):
    r = Robot(5, **config)
    report = run(r)
    assert report['code'] == code and report['manual_action']
    assert not r.commands


def test_status_never_writes():
    r = Robot(5, mode='IDLE', program=TARGET)
    assert 'brake release' in run(r, False)['message']
    assert not r.commands


def test_missing_local_driver_does_not_play():
    r = Robot(5, mode='RUNNING', program=TARGET, listener=False)
    assert run(r)['code'] == 'ros_driver_missing'
    assert not r.commands


def test_play_without_reverse_connection_is_not_ready_and_never_restarts():
    r = Robot(5, mode='RUNNING', program=TARGET, disable_link=True)
    report = run(r)
    assert report['code'] == 'ros_not_connected'
    assert report['state']['playback'] == 'PLAYING'
    assert run(r)['code'] == 'ros_not_connected'
    assert r.commands == ['play']


def test_load_rejection_never_powers_arm():
    r = Robot(5, reject=('load ' + Path(TARGET).name,))
    assert run(r)['code'] == 'load_rejected'
    assert r.commands == ['load ' + Path(TARGET).name]


def test_lost_ack_does_not_retry():
    r = Robot(5, program=TARGET, dropped=('power on',))
    result = run(r)
    assert result['code'] == 'command_outcome_unknown'
    assert r.commands == ['power on']


def test_pending_power_is_not_repeated():
    r = Robot(5, program=TARGET, mode='POWER_ON')
    assert run(r)['code'] == 'transition_timeout'
    assert not r.commands


def test_transport_only_counts_the_correct_ros_process_and_robot(monkeypatch):
    arm = bringup.Arm('left_front', '192.168.8.2', SERIAL, 3, 29999, TARGET, 51001, 51002)
    rows = [
        'LISTEN 0 10 0.0.0.0:51002 0.0.0.0:* users:(("python",pid=7,fd=3))',
        'ESTAB 0 0 192.168.8.209:51001 192.168.8.3:45500 users:(("ros2_control_no",pid=1,fd=4))',
    ]
    def ss(*args, **kwargs):
        return type('Result', (), {'stdout':'\n'.join(rows)})()
    monkeypatch.setattr(bringup.subprocess, 'run', ss)
    assert bringup.transport(arm) == (False, False)
    rows += [
        'LISTEN 0 10 0.0.0.0:51002 0.0.0.0:* users:(("ros2_control_no",pid=1,fd=3))',
        'ESTAB 0 0 [::ffff:192.168.8.209]:51001 [::ffff:192.168.8.2]:45500 users:(("ros2_control_no",pid=1,fd=4))',
    ]
    assert bringup.transport(arm) == (True, True)



def test_json_invocation_reports_all_arms_and_continues_past_local_mode(monkeypatch, capsys):
    from contextlib import ExitStack
    from dataclasses import replace
    import json
    controllers = {
        'left_front': Robot(3),
        'left_rear': Robot(5, remote=False),
        'right_front': Robot(5, mode='RUNNING', program=TARGET, playback='PLAYING'),
        'right_rear': Robot(5, mode='IDLE', program=TARGET),
    }
    with ExitStack() as stack:
        arms = {name: replace(stack.enter_context(dashboard(robot)), id=name)
                for name, robot in controllers.items()}
        monkeypatch.setattr(bringup, 'load_arms', lambda _: arms)
        from contextlib import nullcontext
        monkeypatch.setattr(bringup, 'operation_lock', nullcontext)
        # Keep the real arm routine and Dashboard socket, faking only ROS links.
        run_arm = bringup.run_arm
        monkeypatch.setattr(bringup, 'run_arm', lambda arm, apply, **kwargs:
                            run_arm(arm, apply, get_transport=controllers[arm.id].transport,
                                    transition_timeout=0))
        assert bringup.main(['--apply', '--json']) == 1
    report = json.loads(capsys.readouterr().out)
    assert not report['all_ready']
    assert {name: data['code'] for name, data in report['arms'].items()} == {
        'left_front': 'ready', 'left_rear': 'local_control',
        'right_front': 'ready', 'right_rear': 'ready',
    }
    assert controllers['left_rear'].commands == controllers['right_front'].commands == []
    assert [d['command'] for d in report['arms']['right_rear']['commands']] == ['brake release', 'play']



def test_apply_starts_missing_driver_before_energizing():
    robot = Robot(5, listener=False)
    launches = []
    def start_driver(arm, get_transport):
        assert robot.commands == []
        launches.append(arm.id)
        robot.listener = True
    with dashboard(robot) as arm:
        report = bringup.run_arm(arm, True, get_transport=robot.transport,
                                 transition_timeout=0, start_driver=start_driver)
    assert report['code'] == 'ready' and report['driver_start_attempted']
    assert launches == ['left_front']
    assert robot.commands == ['load ros.urp', 'power on', 'brake release', 'play']


@pytest.mark.parametrize('apply,remote', [(False, True), (True, False)])
def test_missing_driver_is_not_started_for_status_or_blocked_arm(apply, remote):
    robot = Robot(5, listener=False, remote=remote)
    with dashboard(robot) as arm:
        report = bringup.run_arm(
            arm, apply, get_transport=robot.transport, transition_timeout=0,
            start_driver=lambda *_: pytest.fail('Unexpected driver launch'))
    assert not report['driver_start_attempted'] and not robot.commands
    assert report['code'] == ('local_control' if apply else 'needs_preparation')


def test_failed_driver_launch_does_not_energize_arm():
    robot = Robot(5, listener=False)
    def failed(*_):
        raise bringup.Blocked('ros_driver_start_failed', 'Launch failed', 'Check the log.')
    with dashboard(robot) as arm:
        report = bringup.run_arm(arm, True, get_transport=robot.transport,
                                 transition_timeout=0, start_driver=failed)
    assert report['code'] == 'ros_driver_start_failed' and report['manual_action']
    assert not robot.commands

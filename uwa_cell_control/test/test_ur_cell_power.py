"""Safety and operator outcomes for the two actions, with fake Dashboard TCP."""
from contextlib import nullcontext
import sys

import pytest

from test_ur_bringup import Robot, TARGET, dashboard, script

sys.path.insert(0, str(script.parent))
import ur_cell_power as power


class StandbyRobot(Robot):
    def reply(self, cmd):
        if cmd == 'stop':
            self.commands.append(cmd)
            if cmd in self.reject:
                return 'Failed to execute: stop'
            self.playback = 'STOPPED'
            return 'Stopped'
        if cmd == 'power off':
            self.commands.append(cmd)
            self.mode = 'POWER_OFF'
            return 'Powering off'
        return super().reply(cmd)


@pytest.mark.parametrize('series', (3, 5))
def test_standby_stops_before_power_off_and_can_be_repeated(series):
    robot = StandbyRobot(series, program=TARGET, playback='PLAYING', mode='RUNNING')
    with dashboard(robot) as arm:
        report = power.stop_for_standby(arm)
        assert report['code'] == 'standby'
        assert report['state']['mode'] == 'POWER_OFF'
        assert report['state']['playback'] == 'STOPPED'
        assert power.stop_for_standby(arm)['commands'] == []
    assert robot.commands == ['stop', 'power off']


@pytest.mark.parametrize('state,code,commands', [
    ({'remote': False}, 'local_control', []),
    ({'program': '/programs/example.urp'}, 'program_in_use', []),
    ({'reject': ('stop',)}, 'command_rejected', ['stop']),
])
def test_standby_does_not_cut_power_on_blocker(state, code, commands):
    robot = StandbyRobot(5, **(dict(program=TARGET, playback='PLAYING', mode='RUNNING') | state))
    with dashboard(robot) as arm:
        assert power.stop_for_standby(arm)['code'] == code
    assert robot.commands == commands


def test_standby_leaves_an_already_off_local_arm_alone():
    robot = StandbyRobot(5, remote=False, mode='POWER_OFF')
    with dashboard(robot) as arm:
        assert power.stop_for_standby(arm)['code'] == 'standby'
        assert power.status(arm)['code'] == 'standby'
    assert robot.commands == []


def test_group_reports_each_arm_and_does_not_claim_partial_success(monkeypatch):
    from dataclasses import replace
    from contextlib import ExitStack

    with ExitStack() as stack:
        robots = [StandbyRobot(5, program=TARGET, playback='STOPPED', mode='RUNNING', remote=remote)
                  for remote in (True, False, True, True)]
        arms = [replace(stack.enter_context(dashboard(robot)), id=str(i)) for i, robot in enumerate(robots)]
        monkeypatch.setattr(power, 'operation_lock', nullcontext)
        messages = []
        assert not power.execute('standby', arms, lambda kind, **kw: messages.append((kind, kw)))
        results = [event['result']['code'] for kind,event in messages if kind=='arm']
        assert results == ['standby', 'local_control', 'standby', 'standby']
        assert [r.commands for r in robots] == [['power off'], [], ['power off'], ['power off']]

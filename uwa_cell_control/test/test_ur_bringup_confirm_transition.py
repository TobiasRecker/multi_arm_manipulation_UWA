"""Only successful program load may wait out a NORMAL confirmation transition.

Tests use a fake monotonic clock and in-process Dashboard replies. There are
no sockets, ROS nodes, host operations or physical controller commands.
"""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import sys

import pytest

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
import ur_bringup as bringup


ARM=bringup.Arm('right_front','in-process-test','2020101111',5,29999,
                '/programs/ros.urp',52001,52002)


class Clock:
    def __init__(self):
        self.value=100.
        self.sleeps=[]
    def now(self):return self.value
    def sleep(self,seconds):
        self.sleeps.append(seconds)
        self.value+=seconds


def state(mode='CONFIRM_SAFETY',**values):
    return replace(bringup.State(mode=mode,safety='NORMAL',remote=True,program=ARM.program,
        playback='STOPPED',playback_program='ros.urp',program_saved=True,version='5.15.8'),**values)


def wait(monkeypatch,states,*,step='load',seconds=1.):
    clock=Clock()
    report={'commands':[{'command':'load ros.urp','reply':'Loading program: ros.urp'}]}
    rows=list(states)
    reads=[]
    def inspect(_dash,_arm):
        assert _arm is ARM
        row=rows.pop(0) if len(rows)>1 else rows[0]
        reads.append(row)
        return row
    monkeypatch.setattr(bringup,'inspect',inspect)
    def run():
        return bringup.wait_for(object(),ARM,step,lambda _:(True,False),report,
                                seconds=seconds,clock=clock.now,sleep=clock.sleep)
    return run,clock,report,reads


def test_successful_load_waits_for_normal_confirm_mode_to_clear_before_returning(monkeypatch):
    run,clock,report,reads=wait(monkeypatch,[state(),state('POWER_OFF')])
    run()
    assert [row.mode for row in reads]==['CONFIRM_SAFETY','POWER_OFF']
    assert report['state']['mode']=='POWER_OFF'
    assert clock.value==100.25 and clock.sleeps==[.25]
    assert report['commands']==[{'command':'load ros.urp','reply':'Loading program: ros.urp'}]


def test_persistent_normal_confirmation_uses_existing_deadline_then_preserves_manual_block(monkeypatch):
    run,clock,report,reads=wait(monkeypatch,[state()],seconds=1.)
    with pytest.raises(bringup.Blocked) as error:
        run()
    assert error.value.code=='confirm_safety' and error.value.action
    assert 1. <= clock.value-100. < 1.25
    assert len(reads)>1 and report['state']['mode']=='CONFIRM_SAFETY'
    assert len(report['commands'])==1


def test_regular_successful_load_has_no_added_wait(monkeypatch):
    run,clock,report,reads=wait(monkeypatch,[state('POWER_OFF')])
    run()
    assert not clock.sleeps and len(reads)==1
    assert report['state']['mode']=='POWER_OFF'


@pytest.mark.parametrize('mode,safety,code',[
    ('POWER_OFF','PROTECTIVE_STOP','safety_blocked'),
    ('POWER_OFF','ROBOT_EMERGENCY_STOP','safety_blocked'),
    ('CONFIRM_SAFETY','PROTECTIVE_STOP','safety_blocked'),
    ('CONFIRM_SAFETY','REDUCED','confirm_safety'),
    ('CONFIRM_SAFETY','UNDEFINED_SAFETY_MODE','safety_blocked'),
])
def test_load_tolerance_does_not_delay_other_native_faults_or_non_normal_confirmation(monkeypatch,mode,safety,code):
    run,clock,_,reads=wait(monkeypatch,[state(mode,safety=safety)])
    with pytest.raises(bringup.Blocked) as error:
        run()
    assert error.value.code==code
    assert not clock.sleeps and len(reads)==1


def test_fault_appearing_during_load_validation_ends_wait_immediately(monkeypatch):
    run,clock,_,reads=wait(monkeypatch,[state(),state(safety='PROTECTIVE_STOP')],seconds=30.)
    with pytest.raises(bringup.Blocked) as error:
        run()
    assert error.value.code=='safety_blocked'
    assert clock.sleeps==[.25] and len(reads)==2


@pytest.mark.parametrize('step',['power on','brake release','play','wait_ros'])
def test_no_confirmation_tolerance_for_non_load_steps(monkeypatch,step):
    run,clock,_,reads=wait(monkeypatch,[state()],step=step)
    with pytest.raises(bringup.Blocked) as error:
        run()
    assert error.value.code=='confirm_safety'
    assert not clock.sleeps and len(reads)==1


@pytest.mark.parametrize('changes,code',[
    ({'remote':False},'local_control'),
    ({'playback':'PAUSED'},'program_in_use'),
    ({'program':'/programs/other.urp','playback':'PLAYING','playback_program':'other.urp'},'program_in_use'),
])
def test_confirmation_wait_still_observes_remote_and_program_changes(monkeypatch,changes,code):
    run,clock,_,reads=wait(monkeypatch,[state(**changes)])
    with pytest.raises(bringup.Blocked) as error:
        run()
    assert error.value.code==code
    assert not clock.sleeps and len(reads)==1


class DashboardRobot:
    """Raw native replies exercise real inspect/write/run_arm without TCP."""
    def __init__(self,load_modes=('CONFIRM_SAFETY','POWER_OFF')):
        self.mode='POWER_OFF'
        self.program=None
        self.playback='STOPPED'
        self.validation_modes=[]
        self.commands=[]
        self.observed_modes=[]
        self.load_modes=load_modes

    @contextmanager
    def connect(self):yield self

    def ask(self,command):
        if command=='get serial number':return ARM.serial
        if command=='PolyscopeVersion':return 'URSoftware 5.15.8'
        if command=='robotmode':
            if self.validation_modes:self.mode=self.validation_modes.pop(0)
            self.observed_modes.append(self.mode)
            return 'Robotmode: '+self.mode
        if command=='safetystatus':return 'Safetystatus: NORMAL'
        if command=='is in remote control':return 'true'
        if command=='programState':return self.playback+' '+('ros.urp' if self.program else 'null')
        if command=='get loaded program':return 'Loaded program: '+self.program if self.program else 'No program loaded'
        if command=='isProgramSaved':return 'true '+self.program
        self.commands.append(command)
        if command=='load ros.urp':
            self.program=ARM.program
            self.validation_modes=list(self.load_modes)
            return 'Loading program: ros.urp'
        if command=='power on':self.mode='IDLE';return 'Powering on'
        if command=='brake release':self.mode='RUNNING';return 'Brake releasing'
        if command=='play':self.playback='PLAYING';return 'Starting program'
        pytest.fail('Unexpected controller command: '+command)

    def transport(self,_arm):return True,self.playback=='PLAYING'


def test_entire_cold_start_survives_load_transition_without_repeating_load_power_or_play(monkeypatch):
    robot=DashboardRobot()
    clock=Clock()
    original=bringup.wait_for
    def with_clock(*args,**kwargs):
        return original(*args,**kwargs,clock=clock.now,sleep=clock.sleep)
    monkeypatch.setattr(bringup,'wait_for',with_clock)
    result=bringup.run_arm(ARM,True,dashboard=lambda _:robot,get_transport=robot.transport,
                           transition_timeout=1.)
    assert result['code']=='ready'
    assert robot.commands==['load ros.urp','power on','brake release','play']
    assert [row['command'] for row in result['commands']]==robot.commands
    assert 'CONFIRM_SAFETY' in robot.observed_modes
    assert clock.sleeps==[.25]
    assert result['ros_reverse_connected'] is True


def test_initial_confirmation_before_load_remains_blocked_without_any_write():
    robot=DashboardRobot()
    robot.mode='CONFIRM_SAFETY'
    result=bringup.run_arm(ARM,True,dashboard=lambda _:robot,get_transport=robot.transport,
                           transition_timeout=1.)
    assert result['code']=='confirm_safety' and result['manual_action']
    assert result['commands']==[] and robot.commands==[]


def test_persistent_load_confirmation_never_energizes_or_repeats_load_on_retry(monkeypatch):
    robot=DashboardRobot(load_modes=('CONFIRM_SAFETY',))
    clock=Clock()
    original=bringup.wait_for
    def with_clock(*args,**kwargs):
        return original(*args,**kwargs,clock=clock.now,sleep=clock.sleep)
    monkeypatch.setattr(bringup,'wait_for',with_clock)
    first=bringup.run_arm(ARM,True,dashboard=lambda _:robot,get_transport=robot.transport,
                          transition_timeout=1.)
    assert first['code']=='confirm_safety' and first['state']['mode']=='CONFIRM_SAFETY'
    assert robot.commands==['load ros.urp']
    second=bringup.run_arm(ARM,True,dashboard=lambda _:robot,get_transport=robot.transport,
                           transition_timeout=1.)
    assert second['code']=='confirm_safety' and second['commands']==[]
    assert robot.commands==['load ros.urp']

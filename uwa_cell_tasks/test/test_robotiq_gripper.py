"""Real command state machine against an in-process register emulator only."""
import pytest
from uwa_cell_tasks.robotiq_gripper import Robotiq


class Device(Robotiq):
    def __init__(self,enabled=True):
        super().__init__('not-a-device',enabled=enabled)
        self.regs=dict(ACT=0,STA=0,FLT=0,OBJ=0,POS=3,PRE=0,SPE=0,FOR=0,COU=0)
        self.writes=[]
    def _set(self,pairs):
        self.writes.append(dict(pairs));self.regs.update(pairs)
        if 'ACT' in dict(pairs):self.regs['STA']=3 if self.regs['ACT'] else 0
        if 'GTO' in dict(pairs):
            self.regs.update(PRE=self.regs['POS'],OBJ=2)
    def status(self):
        return dict(registers=self.regs.copy(),activated=self.regs['ACT']==1 and self.regs['STA']==3,
                    fault_free=self.regs['FLT']==0)


def test_startup_and_read_only_goals_never_activate_or_move():
    device=Device(False)
    assert not device.writes
    for operation in (1,2):
        with pytest.raises(ValueError,match='MONITOR ONLY'):device.command(operation,20,10,0,2.)
    assert not device.writes


def test_inactive_move_does_not_implicitly_activate():
    device=Device()
    with pytest.raises(RuntimeError,match='inactive'):device.command(1,128,10,0,2.)
    assert not device.writes


def test_explicit_activation_then_contact_move_retains_target(monkeypatch):
    monkeypatch.setattr('uwa_cell_tasks.robotiq_gripper.time.sleep',lambda value:None)
    device=Device();device.command(2,0,0,0,2.)
    assert device.writes==[{'ACT':0},{'ACT':1}]
    outcome=device.command(1,128,10,0,2.)
    assert outcome['registers']['OBJ']==2
    assert device.writes[2:]==[{'FOR':0},{'SPE':10},{'POS':128},{'GTO':1}]
    assert device.last_requested['position_raw']==128
    # No automatic open, force-zero, reset or GTO0 after completion.
    assert device.writes[-1]=={'GTO':1}


@pytest.mark.parametrize('values',[(1,128,33,0,2.),(1,128,10,1,2.),(1,256,10,0,2.),
                                  (1,128,10,0,float('nan')),(1,128,10,0,.01)])
def test_invalid_or_higher_force_command_never_reaches_device(values):
    device=Device()
    with pytest.raises(ValueError):device.command(*values)
    assert not device.writes


def test_fault_during_move_does_not_reset_open_or_retry():
    device=Device();device.regs.update(ACT=1,STA=3)
    original=device._set
    def fault(pairs):
        original(pairs)
        if 'GTO' in dict(pairs):device.regs['FLT']=9
    device._set=fault
    with pytest.raises(RuntimeError,match='fault 9'):device.command(1,128,10,0,2.)
    assert device.writes==[{'FOR':0},{'SPE':10},{'POS':128},{'GTO':1}]


def test_unconfirmed_speed_or_force_never_changes_position_or_starts_motion(monkeypatch):
    monkeypatch.setattr('uwa_cell_tasks.robotiq_gripper.time.sleep',lambda value:None)
    device=Device();device.regs.update(ACT=1,STA=3,FOR=255,GTO=1)
    def ignored(pairs):device.writes.append(dict(pairs))
    device._set=ignored
    # Bound the confirmation loop deterministically without a real delay.
    clock=iter([0.,0.,.1,2.1])
    monkeypatch.setattr('uwa_cell_tasks.robotiq_gripper.time.monotonic',lambda:next(clock))
    with pytest.raises(TimeoutError) as failure:device.command(1,128,10,0,2.)
    assert 'during force confirmation' in str(failure.value)
    assert 'expected ACT=1 STA=3 FOR=0' in str(failure.value)
    assert 'FOR=255' in str(failure.value)
    # Do not queue another parameter until the preceding force write is read
    # back; in particular never reach POS/GTO after an ACK-only outcome.
    assert device.writes==[{'FOR':0}]


def test_unconfirmed_speed_reports_readback_without_reaching_position(monkeypatch):
    device=Device();device.regs.update(ACT=1,STA=3,SPE=255)
    device._set=lambda pairs:device.writes.append(dict(pairs))
    clock=iter([0.,0.,.1,.2,.3,2.1])
    monkeypatch.setattr('uwa_cell_tasks.robotiq_gripper.time.monotonic',lambda:next(clock))
    monkeypatch.setattr('uwa_cell_tasks.robotiq_gripper.time.sleep',lambda _:None)
    with pytest.raises(TimeoutError) as failure:device.command(1,128,16,0,2.)
    assert 'during speed confirmation' in str(failure.value)
    assert 'expected ACT=1 STA=3 SPE=16 FOR=0' in str(failure.value)
    assert 'SPE=255' in str(failure.value)
    assert device.writes==[{'FOR':0},{'SPE':16}]

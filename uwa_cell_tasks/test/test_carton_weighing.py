"""Finite weighing arithmetic only: no ROS, device connection or safety tests."""
from copy import deepcopy
import numpy as np
import pytest
from uwa_cell_tasks.carton_weighing import ARMS, G, estimate, sample_arm


def window(loads, rotations=None):
    rotations = rotations or {a:np.eye(3) for a in ARMS}
    return dict(window_s=2., arms={arm:[dict(device_time_s=float(t),
        wrench_base=[*(rotations[arm].T@np.array(loads[arm])),0.,0.,0.],
        payload_kg=1.,payload_cog=[0.,0.,.1],tcp_offset=[0.]*6) for t in np.linspace(0,2,41)] for arm in ARMS})


def test_signed_world_load_cancels_opposing_internal_forces_and_keeps_unequal_shares():
    # RF base tilted90degrees; force is in base, not tool coordinates.
    rotations = {ARMS[0]:np.array([[0.,0.,1.],[0.,1.,0.],[-1.,0.,0.]]),ARMS[1]:np.eye(3)}
    baseline=window({a:[1.,2.,-3.] for a in ARMS},rotations)
    held=window({ARMS[0]:[31.,2.,-3.],ARMS[1]:[-29.,2.,-3.]},rotations)
    lifted=window({ARMS[0]:[31.,2.,-3.-.2*G],ARMS[1]:[-29.,2.,-3.-.6*G]},rotations)
    result=estimate(baseline,held,lifted,rotations)
    assert result['mass_kg']==pytest.approx(.8)
    assert result['arms'][ARMS[0]]['load_fraction']==pytest.approx(.25)
    assert result['supported_to_lift_transfer_n']==pytest.approx(.8*G)
    assert result['assessment']=='BOTH_ARMS_LOAD_PLAUSIBLE'
    assert not result['empirical_band_is_accuracy_interval']


def test_upward_or_only_one_arm_is_inconclusive_not_absolute_norm_mass():
    baseline=window({a:[0.,0.,0.] for a in ARMS})
    for loads in ({a:[0.,0.,G] for a in ARMS},{ARMS[0]:[0.,0.,-G],ARMS[1]:[0.,0.,0.]}):
        result=estimate(baseline,baseline,window(loads),{a:np.eye(3) for a in ARMS})
        assert result['assessment']=='INCONCLUSIVE'
        assert result['warnings']


def test_changed_payload_invalidates_differential_mass():
    zero=window({a:[0.,0.,0.] for a in ARMS}); lifted=deepcopy(zero)
    lifted['arms'][ARMS[0]][0]['payload_kg']=2.
    result=estimate(zero,zero,lifted,{a:np.eye(3) for a in ARMS})
    assert result['mass_kg'] is None and result['empirical_mass_band_kg'] is None
    assert 'settings changed' in result['warnings'][0]


@pytest.mark.parametrize('bad',['nonfinite','short','repeat','reflection'])
def test_invalid_measurements_are_rejected(bad):
    zero=window({a:[0.,0.,0.] for a in ARMS}); lifted=deepcopy(zero)
    rotations={a:np.eye(3) for a in ARMS}
    if bad=='nonfinite':lifted['arms'][ARMS[0]][4]['wrench_base'][0]=float('nan')
    if bad=='short':lifted['arms'][ARMS[0]]=lifted['arms'][ARMS[0]][:3]
    if bad=='repeat':lifted['arms'][ARMS[0]][4]['device_time_s']=0.
    if bad=='reflection':rotations[ARMS[0]]=np.diag([1.,1.,-1.])
    with pytest.raises(ValueError):estimate(zero,zero,lifted,rotations)


@pytest.mark.parametrize('seconds',[0.,-1.,11.,float('nan')])
def test_invalid_window_rejected_before_opening_socket(seconds):
    with pytest.raises(ValueError):sample_arm('must-not-connect',seconds)


def test_sampler_negotiates_output_only_and_decodes_full_recipe(monkeypatch):
    import struct
    from uwa_cell_control.capture_rtde import OutputReader
    from uwa_cell_tasks import carton_weighing as module
    calls=[]
    class Socket:
        closed=False
        def settimeout(self,*args):pass
        def close(self):self.closed=True
    sock=Socket()
    monkeypatch.setattr(module.socket,'create_connection',lambda *a,**kw:sock)
    def request(self,kind,payload=b''):
        calls.append((kind,payload))
        return bytes([7])+module.TYPES if kind==79 else b'\x01'
    frames=iter((85,bytes([7])+struct.pack('>35d',t,*range(1,35))) for t in (0.,.05,.1))
    monkeypatch.setattr(OutputReader,'request',request)
    monkeypatch.setattr(OutputReader,'receive',lambda self:next(frames))
    rows=module.sample_arm('fake',.1)
    assert [kind for kind,_ in calls]==[86,79,83]
    assert calls[1][1][8:].decode()==module.FIELDS
    assert len(rows)==3 and rows[0]['wrench_base']==list(range(19,25))
    assert rows[0]['tcp_offset']==list(range(25,31))
    assert rows[0]['payload_kg']==31 and rows[0]['payload_cog']==[32,33,34]
    assert sock.closed

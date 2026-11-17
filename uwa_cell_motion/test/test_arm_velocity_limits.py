"""Per-arm operating caps stay bound to guard checks, reserves and timing."""
import copy
from pathlib import Path
import numpy as np
import pytest
import yaml
from uwa_cell_motion.common import config,ROBOT_IDS,arm_velocity_limit,guard_signature
from uwa_cell_motion.guard_core import GuardState
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_motion.planning import Problem


@pytest.fixture
def cfg():
    data=config(Path(__file__).parents[1]/'config/hardware_commissioning.yaml')
    data['arm_velocity_limits_rad_s']={r:.003 for r in ROBOT_IDS}
    data['arm_velocity_limits_rad_s']['right_front']=.03
    return data


def test_default_caps_and_binding_are_preserved_without_mapping(cfg):
    default={k:v for k,v in cfg.items() if k!='arm_velocity_limits_rad_s'}
    assert all(arm_velocity_limit(default,r)==.003 for r in ROBOT_IDS)
    assert guard_signature(default)!=guard_signature(cfg)
    changed=copy.deepcopy(cfg);changed['arm_velocity_limits_rad_s']['right_front']=.02
    assert guard_signature(changed)!=guard_signature(cfg)


@pytest.mark.parametrize('change', ['missing','unknown','zero','negative','nan','boolean'])
def test_config_rejects_ambiguous_or_invalid_arm_caps(tmp_path,cfg,change):
    values=cfg['arm_velocity_limits_rad_s']
    if change=='missing':values.pop('left_front')
    elif change=='unknown':values['unknown_arm']=.003
    else:values['right_front']={'zero':0.,'negative':-.1,'nan':float('nan'),'boolean':True}[change]
    file=tmp_path/'caps.yaml';file.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):config(file)


def test_measured_speed_uses_that_arms_cap_without_weakening_stationary_arms(cfg):
    state=GuardState(cfg)
    for r in ROBOT_IDS:state.receive(r,[0.]*6,[.015]*6 if r=='right_front' else [0.]*6,0.,0.)
    assert not state.evaluate([],0.,0.)['faults']
    state.receive('left_front',[0.]*6,[.004]*6,.1,.1)
    faults=state.evaluate([],.1,.1)['faults']
    assert any(f['reason']=='SPEED LIMIT' and f['arms']==['left_front'] and f['configured_limit_rad_s']==.003 for f in faults)
    assert not any(f['arms']==['right_front'] for f in faults)


def test_complete_stopping_budget_uses_same_cap_and_actual_overspeed(cfg):
    model=SphereModel.__new__(SphereModel)
    model.motion_radii={r:np.ones((1,6)) for r in ROBOT_IDS}
    budget,speed=model.arm_budget('right_front',np.zeros(6),.2,cfg)
    expected=6*.03*(.1+.2+1.)+6*.03**2/(2*.2)
    assert budget==pytest.approx(expected) and speed==pytest.approx(6*.03)
    other,_=model.arm_budget('right_rear',np.zeros(6),.2,cfg)
    assert other<budget/9
    overspeed,_=model.arm_budget('right_front',np.ones(6)*.1,.2,cfg)
    assert overspeed>budget


def test_explicit_uniform_mapping_keeps_old_budgets_identical(cfg):
    default={k:v for k,v in cfg.items() if k!='arm_velocity_limits_rad_s'}
    cfg['arm_velocity_limits_rad_s']={r:default['velocity_limit_rad_s'] for r in ROBOT_IDS}
    model=SphereModel.__new__(SphereModel);model.motion_radii={r:np.array([[1.,2.,3.,4.,5.,6.]]) for r in ROBOT_IDS}
    for r in ROBOT_IDS:
        assert model.arm_budget(r,np.zeros(6),.2,cfg)==model.arm_budget(r,np.zeros(6),.2,default)


def test_shared_timing_obeys_lowest_selected_cap(cfg):
    model=Problem.__new__(Problem);model.cfg=dict(cfg,velocity_limit_rad_s=.05)
    model.check=lambda *a,**k:True;model.edge=lambda *a,**k:True
    names=['q'+str(i) for i in range(12)];end=[.03]*6+[.06]*6
    request=dict(selected=['right_front','right_rear'],start=dict.fromkeys(names,0.),joint_names=names,target=end)
    result=model.time_parameterize(request,[[0.]*12,end]);points=result['points']
    assert max(np.max(np.abs(p['velocities'])) for p in points)<=.003+1e-12
    assert result['duration_s']==pytest.approx(1.875*.06/.003)
    for p in points:np.testing.assert_allclose(np.array(p['positions'][:6])*2,p['positions'][6:],atol=1e-12)

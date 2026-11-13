from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.common import PAIRS,ROBOT_IDS,config,simulation_only
from uwa_cell_motion.geometry import box_spheres,SphereModel
from uwa_cell_motion.guard_core import GuardState
from uwa_cell_motion.interlock import Interlock,expired_pair_leases,SUPERVISOR_PERIOD_S


@pytest.fixture
def cfg():return config(Path(__file__).parents[1]/'config/motion.yaml')


def fresh(core,now,moving=(),stamp=None):
    for rid in ROBOT_IDS:
        core.receive(rid,np.zeros(7),np.ones(7)*(.01 if rid in moving else 0),now if stamp is None else stamp,now)


def pairs(clear=.5):return [dict(arms=list(p),clearance_m=clear,threshold_m=.1) for p in PAIRS]


def test_graph_has_only_four_neighbors():
    assert len(PAIRS)==4
    assert {b for p in PAIRS if 'left_front' in p for b in p}-{'left_front'}=={'right_front','left_rear'}
    assert all(len([p for p in PAIRS if r in p])==2 for r in ROBOT_IDS)


def test_spheres_enclose_volume_not_just_mesh_vertices():
    lo=np.array([-.4,-.09,-.07]);hi=-lo;c,r=box_spheres(lo,hi,.05)
    rng=np.random.default_rng(14);points=rng.uniform(lo,hi,(10000,3))
    assert np.max(np.min(np.linalg.norm(points[:,None,:]-c[None,:,:],axis=2)-r,axis=1))<=0
    assert len(c)==16


def test_nearest_markers_use_surface_points_with_the_reported_gap():
    from types import SimpleNamespace
    model=SimpleNamespace(radii={'a':np.array([.1]),'b':np.array([.2])},links={'a':['tool_a'],'b':['tool_b']})
    nearest=SphereModel.nearest(model,{'a':np.array([[0.,0.,0.]]),'b':np.array([[1.,0.,0.]])},'a','b')
    assert np.allclose(nearest['surface_points'],[[.1,0.,0.],[.8,0.,0.]])
    assert np.isclose(np.linalg.norm(np.diff(nearest['surface_points'],axis=0)),nearest['clearance_m'])


def test_guard_stops_only_violating_pair_and_latches(cfg):
    core=GuardState(cfg);fresh(core,1)
    p=pairs();p[0]['clearance_m']=.05
    status=core.evaluate(p,1,1)
    assert set(status['blocked_arms'])==set(PAIRS[0])
    fresh(core,1.05)
    assert set(core.evaluate(pairs(),1.05,1.05)['blocked_arms'])==set(PAIRS[0])


def test_multiple_faults_union_endpoints(cfg):
    core=GuardState(cfg);fresh(core,1);p=pairs();p[0]['clearance_m']=p[1]['clearance_m']=0
    assert set(core.evaluate(p,1,1)['blocked_arms'])=={'left_front','right_front','left_rear'}


def test_stale_one_arm_stops_it_and_two_neighbors(cfg):
    core=GuardState(cfg);fresh(core,1)
    for r in ROBOT_IDS:
        if r!='left_front':core.receive(r,np.zeros(7),np.zeros(7),1.2,1.2)
    status=core.evaluate(pairs(),1.2,1.2)
    assert status['state']=='STATE STALE'
    assert set(status['blocked_arms'])=={'left_front','right_front','left_rear'}


def test_cached_messages_do_not_prove_freshness(cfg):
    core=GuardState(cfg);fresh(core,1)
    fresh(core,1.3,stamp=1)
    assert core.evaluate(pairs(),1.3,1.3)['state']=='STATE STALE'


def test_future_source_stamp_refused(cfg):
    core=GuardState(cfg);fresh(core,1,stamp=100)
    assert core.evaluate(pairs(),1,1)['state']=='STATE STALE'


def test_rewound_arm_epoch_latches_its_neighbors_and_keeps_cause(cfg):
    core=GuardState(cfg);fresh(core,1)
    core.receive('left_front',np.zeros(7),np.zeros(7),.9,1.01)
    status=core.evaluate(pairs(),1.01,1.01)
    assert set(status['blocked_arms'])=={'left_front','right_front','left_rear'}
    assert any(c['reason']=='CLOCK RESET' for c in status['latched_causes'])


def test_reset_requires_stationary_history_and_hysteresis(cfg):
    core=GuardState(cfg);fresh(core,1);core.evaluate(pairs(.01),1,1)
    assert not core.reset(pairs(),1,1)[0]
    for t in np.linspace(1,1.4,9):fresh(core,float(t))
    assert not core.reset(pairs(.105),1.4,1.4)[0]
    assert core.reset(pairs(),1.4,1.4)[0]
    assert not core.latched and core.reset_sequence==1


def test_stop_not_confirmed_while_moving(cfg):
    core=GuardState(cfg)
    for t in np.linspace(1,1.4,9):fresh(core,float(t),moving=['left_front'])
    status=core.evaluate(pairs(.01),1.4,1.4)
    assert not status['standstill_confirmed'] and status['state']=='STOPPING'


def decision(sequence=1,instance='a',blocked=(),reset=0):
    return dict(instance=instance,sequence=sequence,blocked_arms=list(blocked),reset_sequence=reset,state='CLEAR')


def test_watchdog_startup_requires_explicit_reset():
    core=Interlock(.4);core.receive(decision(),1)
    assert core.tick(1)==set(ROBOT_IDS)
    assert core.request_reset(1)
    core.receive(decision(2,reset=1),1.1)
    assert not core.tick(1.1)


def test_close_pair_cannot_spend_the_whole_heartbeat_timeout(cfg):
    value=dict(evaluated_monotonic_s=1.,pairs=[dict(arms=list(PAIRS[0]),clearance_m=.10,threshold_m=.10,relative_speed_bound_m_s=.5)])
    assert not expired_pair_leases(value,1.07,cfg)
    assert expired_pair_leases(value,1.081,cfg)==set(PAIRS[0])
    # A supervisor tick plus switch latency remains within the guard's
    # check-interval + switch reserve even if no new decision arrives.
    assert .08+SUPERVISOR_PERIOD_S+cfg['stop_latency_s']<=1/cfg['rate_hz']+cfg['stop_latency_s']


def test_lease_includes_transport_age_and_excess_clearance(cfg):
    value=dict(evaluated_monotonic_s=1.,pairs=[dict(arms=list(PAIRS[1]),clearance_m=.20,threshold_m=.10,relative_speed_bound_m_s=.5)])
    assert not expired_pair_leases(value,1.27,cfg)
    assert expired_pair_leases(value,1.281,cfg)==set(PAIRS[1])
    value['pairs'][0]['clearance_m']=1.
    assert not expired_pair_leases(value,1.39,cfg)
    assert expired_pair_leases(value,1.41,cfg)==set(PAIRS[1])
    assert expired_pair_leases({},1.,cfg)==set(ROBOT_IDS)


def test_guard_death_stops_all_and_stays_latched_after_return():
    core=Interlock(.4);core.receive(decision(),1);core.request_reset(1);core.receive(decision(2,reset=1),1.1)
    assert core.tick(1.6)==set(ROBOT_IDS)
    core.receive(decision(3,reset=1),1.7)
    assert core.tick(1.7)==set(ROBOT_IDS)


def test_replayed_heartbeat_does_not_refresh_watchdog():
    core=Interlock(.4);core.receive(decision(),1)
    assert not core.receive(decision(),1.3)
    assert core.received==1


def test_guard_restart_cannot_clear_interlock():
    core=Interlock(.4);core.receive(decision(),1);core.request_reset(1)
    core.receive(decision(2,reset=1),1.1);assert not core.blocked
    core.receive(decision(instance='b'),1.2);assert core.blocked==set(ROBOT_IDS)


def test_invalid_state_does_not_replace_valid_record(cfg):
    core=GuardState(cfg);fresh(core,1)
    assert not core.receive('left_front',[float('nan')]*7,[0]*7,2,2)
    assert core.records['left_front']['received']==1


def test_overspeed_latches_moving_arm(cfg):
    core=GuardState(cfg);fresh(core,1)
    core.receive('left_front',np.zeros(7),np.ones(7)*.08,1,1)
    status=core.evaluate(pairs(),1,1)
    assert status['blocked_arms']==['left_front']
    assert status['faults'][0]['reason']=='SPEED LIMIT'


def test_fault_cause_remains_visible_until_explicit_reset(cfg):
    core=GuardState(cfg);fresh(core,1)
    core.evaluate(pairs(.01),1,1);fresh(core,1.05)
    status=core.evaluate(pairs(),1.05,1.05)
    assert not status['faults'] and status['latched_causes']
    assert all(c['reason']=='DISTANCE' for c in status['latched_causes'])


def test_unconfirmed_model_blocks_all_arms(cfg):
    core=GuardState(cfg);fresh(core,1)
    core.external_faults=[dict(arms=list(ROBOT_IDS),reason='MODEL MISMATCH')]
    assert set(core.evaluate(pairs(),1,1)['blocked_arms'])==set(ROBOT_IDS)


def test_missing_front_left_does_not_prevent_independent_rear_right_reset(cfg):
    core=GuardState(cfg)
    for t in np.linspace(1,1.4,9):
        for r in ROBOT_IDS:
            if r!='left_front':core.receive(r,np.zeros(7),np.zeros(7),float(t),float(t))
    available=[p for p in pairs() if 'left_front' not in p['arms']]
    assert core.reset(available,1.4,1.4)[0]
    assert core.reset_arms==['right_rear']
    assert core.latched=={'left_front','right_front','left_rear'}


def test_partial_reset_preserves_other_interlocks():
    core=Interlock(.4);core.receive(decision(),1);core.request_reset(1)
    value=decision(2,blocked=['left_front','right_front','left_rear'],reset=1);value['reset_arms']=['right_rear']
    core.receive(value,1.1)
    assert core.blocked=={'left_front','right_front','left_rear'}


def test_command_entrypoint_refuses_other_domains(monkeypatch):
    monkeypatch.setenv('ROS_DOMAIN_ID','66');monkeypatch.setenv('GZ_PARTITION','uwa_cell_sim')
    with pytest.raises(RuntimeError):simulation_only()


@pytest.mark.parametrize('spacing',[0,-1])
def test_invalid_sphere_configuration_rejected(spacing):
    with pytest.raises(ValueError):box_spheres([-1]*3,[1]*3,spacing)

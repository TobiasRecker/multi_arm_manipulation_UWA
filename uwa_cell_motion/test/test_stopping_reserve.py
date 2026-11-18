"""Independent arithmetic and failure cases for opt-in body/joint reserves."""
import copy
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import yaml
from uwa_cell_motion.common import (BODY_RESERVE_MODEL,ROBOT_IDS,config,
    guard_signature,joint_names,joint_velocity_limits)
from uwa_cell_motion.stopping_reserve import body_budgets,critical_pair
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_motion.guard_core import GuardState
from uwa_cell_motion.interlock import expired_pair_leases,SUPERVISOR_PERIOD_S
from uwa_cell_motion.planning import Problem


@pytest.fixture
def cfg():
    c=config(Path(__file__).parents[1]/'config/hardware_motion.yaml')
    c.update(stopping_reserve_model=BODY_RESERVE_MODEL,
        command_velocity_limit_rad_s=.05,
        joint_velocity_limits_rad_s={r:[.01]*6 for r in ROBOT_IDS})
    return c


@pytest.mark.parametrize('case',['missing_arm','extra_arm','short','zero','negative','nan','bool','ambiguous','unknown_policy','no_policy','no_caps'])
def test_invalid_contracts_fail_closed(tmp_path,cfg,case):
    caps=cfg['joint_velocity_limits_rad_s']
    if case=='missing_arm':caps.pop('left_front')
    elif case=='extra_arm':caps['unknown']=[.01]*6
    elif case=='short':caps['left_front'].pop()
    elif case in ('zero','negative','nan','bool'):caps['left_front'][0]={'zero':0,'negative':-.1,'nan':float('nan'),'bool':True}[case]
    elif case=='ambiguous':cfg['arm_velocity_limits_rad_s']={r:.01 for r in ROBOT_IDS}
    elif case=='unknown_policy':cfg['stopping_reserve_model']='unknown'
    elif case=='no_policy':cfg.pop('stopping_reserve_model')
    elif case=='no_caps':cfg.pop('joint_velocity_limits_rad_s')
    path=tmp_path/'config.yaml';path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):config(path)


def test_valid_contract_and_signatures(tmp_path,cfg):
    path=tmp_path/'config.yaml';path.write_text(yaml.safe_dump(cfg))
    assert config(path)==cfg
    other=copy.deepcopy(cfg);other['joint_velocity_limits_rad_s']['left_front'][1]=.02
    assert guard_signature(cfg)!=guard_signature(other)
    other=copy.deepcopy(cfg);other['command_velocity_limit_rad_s']=.04
    assert guard_signature(cfg)!=guard_signature(other)
    assert np.all(joint_velocity_limits(cfg,'right_rear')>0)


def test_body_distance_bound_and_actual_overspeed_are_explicit(cfg):
    radii=np.array([[1.,2.],[0.,0.]])
    result=body_budgets(radii,[.01,-.08],[.02,.03],.2,cfg)
    speed=.021+2*.08
    braking=(.021**2+2*.08**2)/(2*.2)
    assert result['speed_m_s'][0]==pytest.approx(speed)
    assert result['total_m'][0]==pytest.approx(speed*1.3+braking)
    assert result['total_m'][1]==0
    assert result['total_m'][0]==pytest.approx(sum(result[k][0] for k in
        ('data_age_m','sampling_m','reaction_m','braking_m')))


def test_explicit_geometric_policy_removes_only_dynamic_distance_budgets(cfg,tmp_path):
    before=guard_signature(cfg);cfg['stopping_reserve_policy']='geometric_only'
    assert before!=guard_signature(cfg)
    file=tmp_path/'policy.yaml';file.write_text(yaml.safe_dump(cfg));assert config(file)==cfg
    result=body_budgets(np.ones((2,6)),np.zeros(6),np.full(6,.1),.2,cfg)
    assert np.all(result['total_m']==0) and np.all(result['speed_m_s']>0)
    pair=make_pair([[1.,0,0]],[[0,0,0]],budgets([0],[1]),budgets([0],[1]),cfg)
    assert pair['threshold_m']==cfg['model_margin_m']
    assert pair['reserve_policy']=='geometric_only' and pair['maximum_evaluation_age_s']==cfg['heartbeat_timeout_s']
    pair['arms']=list(ROBOT_IDS[:2]);decision=dict(evaluated_monotonic_s=1.,pairs=[pair])
    assert not expired_pair_leases(decision,1.1,cfg)
    assert expired_pair_leases(decision,1.3,cfg)==set(pair['arms'])
    cfg.pop('stopping_reserve_policy')
    assert expired_pair_leases(decision,1.1,cfg)==set(ROBOT_IDS)


def test_geometric_policy_still_stops_for_distance_speed_and_stale_state(cfg):
    cfg['stopping_reserve_policy']='geometric_only'
    pair=make_pair([[.02,0,0]],[[0,0,0]],budgets([0],[1]),budgets([0],[1]),cfg)
    assert pair['remaining_clearance_m']<0 and pair['maximum_evaluation_age_s']==0
    pair['arms']=list(ROBOT_IDS[:2]);guard=GuardState(cfg)
    for rid in ROBOT_IDS:guard.receive(rid,np.zeros(6),np.zeros(6),1.,1.)
    guard.receive('left_front',np.zeros(6),np.full(6,.2),1.,1.)
    reasons={f['reason'] for f in guard.evaluate([pair],1.,1.)['faults']}
    assert {'DISTANCE','SPEED LIMIT'}<=reasons
    assert any(f['reason']=='STATE STALE' for f in guard.evaluate([],1.3,1.3)['faults'])


@pytest.mark.parametrize('r,v,caps,age',[
    ([[1.,-1.]],[0,0],[.1,.1],.1),([[1.,1.]],[0],[.1],.1),
    ([[1.,1.]],[float('nan'),0],[.1,.1],.1),([[1.,1.]],[0,0],[-.1,.1],.1),
    ([[1.,1.]],[0,0],[.1,.1],-.1)])
def test_invalid_budget_inputs_are_rejected(cfg,r,v,caps,age):
    with pytest.raises(ValueError):body_budgets(r,v,caps,age,cfg)


def budgets(total,speed):
    total,speed=np.array(total,float),np.array(speed,float)
    return dict(total_m=total,speed_m_s=speed,data_age_m=total*.1,
        sampling_m=total*.1,reaction_m=total*.7,braking_m=total*.1)


def make_pair(ca,cb,ba,bb,cfg):
    centres={'a':np.asarray(ca,float),'b':np.asarray(cb,float)}
    radii={r:np.zeros(len(c)) for r,c in centres.items()}
    links={r:[r+str(i) for i in range(len(c))] for r,c in centres.items()}
    return critical_pair('a','b',centres,radii,links,{'a':ba,'b':bb},cfg)


def test_farther_moving_body_can_be_more_critical_than_geometric_nearest(cfg):
    pair=make_pair([[.1,0,0],[.3,0,0]],[[0,0,0]],budgets([0,.28],[0,.1]),budgets([0],[0]),cfg)
    assert pair['sphere_indices']==[1,0]
    assert pair['geometric_min_clearance_m']==pytest.approx(.1)
    assert pair['clearance_m']==pytest.approx(.3)
    assert pair['remaining_clearance_m']<0
    assert pair['maximum_evaluation_age_s']==0
    assert sum(pair['reserve_components_m'].values())==pytest.approx(pair['threshold_m'])


def test_lease_uses_all_pairs_even_when_critical_pair_moves_slowly(cfg):
    pair=make_pair([[.05,0,0],[.3,0,0]],[[0,0,0]],budgets([0,.21],[.001,1.]),budgets([0],[0]),cfg)
    assert pair['sphere_indices']==[0,0]
    expected=.1-SUPERVISOR_PERIOD_S+.05
    assert pair['maximum_evaluation_age_s']==pytest.approx(expected)
    pair['arms']=list(ROBOT_IDS[:2])
    decision=dict(evaluated_monotonic_s=1.,pairs=[pair])
    assert not expired_pair_leases(decision,1.+expected-.0001,cfg)
    assert expired_pair_leases(decision,1.+expected+.0001,cfg)==set(pair['arms'])


def test_all_sphere_pairs_match_independent_scalar_oracle(cfg):
    rng=np.random.default_rng(17)
    for _ in range(60):
        ca=rng.normal(size=(7,3));cb=rng.normal(size=(5,3))
        ra=rng.uniform(.01,.05,7);rb=rng.uniform(.01,.05,5)
        ba=budgets(rng.uniform(.01,.2,7),rng.uniform(0,.3,7))
        bb=budgets(rng.uniform(.01,.2,5),rng.uniform(0,.3,5))
        result=critical_pair('a','b',dict(a=ca,b=cb),dict(a=ra,b=rb),
            dict(a=['a']*7,b=['b']*5),dict(a=ba,b=bb),cfg)
        slack=[];lease=[]
        for i in range(7):
            for j in range(5):
                gap=np.linalg.norm(ca[i]-cb[j])-ra[i]-rb[j]
                remaining=gap-cfg['model_margin_m']-ba['total_m'][i]-bb['total_m'][j]
                speed=ba['speed_m_s'][i]+bb['speed_m_s'][j]
                slack.append(remaining);lease.append(.1-SUPERVISOR_PERIOD_S+remaining/speed)
        assert result['remaining_clearance_m']==pytest.approx(min(slack))
        expected=0 if min(slack)<=0 else min(cfg['heartbeat_timeout_s'],max(0,min(lease)))
        assert result['maximum_evaluation_age_s']==pytest.approx(expected)


@pytest.mark.parametrize('change',['missing','negative','too_long','wrong_model'])
def test_malformed_or_missing_v2_lease_stops_all(cfg,change):
    pair=dict(arms=list(ROBOT_IDS[:2]),reserve_model=BODY_RESERVE_MODEL,maximum_evaluation_age_s=.1)
    if change=='missing':pair.pop('maximum_evaluation_age_s')
    elif change=='negative':pair['maximum_evaluation_age_s']=-1
    elif change=='too_long':pair['maximum_evaluation_age_s']=1
    else:pair['reserve_model']='other'
    assert expired_pair_leases(dict(evaluated_monotonic_s=1.,pairs=[pair]),1.,cfg)==set(ROBOT_IDS)


def test_stationary_axis_cap_is_checked_independently_of_faster_axes(cfg):
    cfg['joint_velocity_limits_rad_s']['left_front']=[.001,.1,.1,.1,.1,.1]
    core=GuardState(cfg)
    for rid in ROBOT_IDS:core.receive(rid,np.zeros(6),np.zeros(6),1.,1.)
    core.receive('left_front',np.zeros(6),[.002,.05,0,0,0,0],1.01,1.01)
    fault=next(f for f in core.evaluate([],1.01,1.01)['faults'] if f['reason']=='SPEED LIMIT')
    assert fault['joint_index']==0 and fault['configured_limit_rad_s']==.001


def test_complete_opening_sweep_requires_fixed_virtual_coordinate(cfg):
    model=SphereModel.__new__(SphereModel)
    model.motion_radii={'left_front':np.ones((1,7))}
    normal=model.body_budget('left_front',np.zeros(7),.2,cfg)
    model.enveloped_dofs={'left_front':(6,)}
    enclosed=model.body_budget('left_front',np.zeros(7),.2,cfg)
    assert enclosed['total_m'][0]<normal['total_m'][0]
    with pytest.raises(ValueError):model.body_budget('left_front',[0]*6+[.01],.2,cfg)


def test_joint_specific_timing_preserves_shared_progress_without_slowest_arm_cap(cfg):
    cfg.update(command_velocity_limit_rad_s=.04,acceleration_limit_rad_s2=1.)
    cfg['joint_velocity_limits_rad_s']['left_front']=[.05]*6
    cfg['joint_velocity_limits_rad_s']['right_front']=[.002]*6
    names=joint_names('left_front')+joint_names('right_front')
    delta=np.array([.1]*6+[.001]*6)
    request=dict(selected=['left_front','right_front'],joint_names=names,
        start=dict.fromkeys(names,0.),target=delta.tolist())
    model=Problem.__new__(Problem);model.cfg=cfg
    model.check=lambda *a,**k:True;model.edge=lambda *a,**k:True
    trajectory=model.time_parameterize(request,[np.zeros(12),delta])
    assert trajectory['duration_s']==pytest.approx(1.875*.1/.04)
    for point in trajectory['points']:
        assert np.max(abs(np.array(point['velocities'][:6])))<=.04+1e-12
        assert np.max(abs(np.array(point['velocities'][6:])))<=.002+1e-12
        np.testing.assert_allclose(np.array(point['positions'][:6])/100,point['positions'][6:],atol=1e-12)


def test_runtime_phase_uses_the_same_joint_caps_and_command_timing(cfg):
    from concurrent.futures import Future
    from action_msgs.msg import GoalStatus
    from control_msgs.action import FollowJointTrajectory
    from uwa_cell_motion.execution import MotionClient
    cfg.update(command_velocity_limit_rad_s=.04,acceleration_limit_rad_s2=1.)
    cfg['joint_velocity_limits_rad_s']['left_front']=[.05,.002,.05,.05,.05,.05]
    names=joint_names('left_front');target=np.array([.1,.001,0,0,0,0])
    client=SimpleNamespace(positions=dict.fromkeys(names,0.),guard={'blocked_arms':[]},
        supervisor={'blocked_arms':[]},spin_once=lambda **k:None)
    sent=[]
    def ready(value):
        f=Future();f.set_result(value);return f
    def send(goal):
        sent.append(goal)
        for name,value in zip(names,goal.trajectory.points[-1].positions):client.positions[name]=value
        response=SimpleNamespace(status=GoalStatus.STATUS_SUCCEEDED,
            result=SimpleNamespace(error_code=FollowJointTrajectory.Result.SUCCESSFUL))
        return ready(SimpleNamespace(accepted=True,get_result_async=lambda:ready(response)))
    client.actions={'left_front':SimpleNamespace(server_is_ready=lambda:True,send_goal_async=send)}
    client.health=lambda:None
    assert MotionClient.phase(client,{'left_front':target},cfg,set())==set()
    points=sent[0].trajectory.points
    duration=points[-1].time_from_start.sec+points[-1].time_from_start.nanosec/1e9
    assert duration==pytest.approx(1.875*.1/.04)
    assert max(abs(p.velocities[0]) for p in points)<=.04+1e-12
    assert max(abs(p.velocities[1]) for p in points)<=.002+1e-12


def test_runtime_phase_envelope_uses_least_reserve_not_nearest_pair_threshold(cfg):
    from uwa_cell_motion.execution import safe_targets
    names={r:joint_names(r) for r in ROBOT_IDS};state={j:0. for n in names.values() for j in n}
    spheres=SimpleNamespace(world=lambda state:{},motion_radii={r:np.ones((1,6)) for r in names},
        pairs=lambda *a,**k:({},[dict(arms=['left_front','right_front'],remaining_clearance_m=1e-7)]),
        nearest=lambda *a,**k:dict(clearance_m=10.))
    problem=SimpleNamespace(cfg=cfg,names=names,spheres=spheres,edge=lambda *a,**k:True)
    client=SimpleNamespace(positions=state,velocities=dict.fromkeys(state,0.),guard={'pairs':[]})
    desired={j:.1 for j in names['left_front']}
    targets,unsafe=safe_targets(problem,client,desired,['left_front'])
    assert targets is None and unsafe=={'left_front'}


def test_audit_covers_geometry_between_samples_and_keeps_source_profiles(cfg):
    import importlib.util
    from uwa_cell_motion.common import PAIRS
    path=Path(__file__).parents[2]/'tools/audit_stopping_reserve.py'
    spec=importlib.util.spec_from_file_location('reserve_audit_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    names={r:joint_names(r) for r in ROBOT_IDS}
    selected=names['left_front'];state={j:0. for n in names.values() for j in n}
    state[selected[0]]=-.3
    def world(q):
        angle=q[selected[0]]
        return dict(left_front=np.array([[np.cos(angle),np.sin(angle),0.]]),
            right_front=np.array([[2.,0,0]]),left_rear=np.array([[4.,0,0]]),right_rear=np.array([[6.,0,0]]))
    motion={r:np.zeros((1,6)) for r in names};motion['left_front'][0,0]=1.
    problem=SimpleNamespace(names=names,spheres=SimpleNamespace(world=world,
        radii={r:np.array([.1]) for r in names},motion_radii=motion))
    waypoints=[[-.3,0,0,0,0,0],[.4,0,0,0,0,0]]
    request=dict(start=state,joint_names=selected,selected=['left_front'])
    bounds=module.path_gap_bounds(problem,request,waypoints,.2)
    for angle in np.linspace(-.3,.4,1001):
        actual=world(dict(state,**{selected[0]:angle}))
        for a,b in PAIRS:
            gap=np.linalg.norm(actual[a][0]-actual[b][0])-.2
            assert bounds[a,b][0,0]<=gap+1e-12
    original=copy.deepcopy(cfg)
    proposed=module.profile(cfg,request,waypoints,.05,.001,.002,1.3)
    assert cfg==original
    assert proposed['joint_velocity_limits_rad_s']['left_front'][1:]==[.002]*5
    assert proposed['joint_velocity_limits_rad_s']['right_rear']==[.001]*6

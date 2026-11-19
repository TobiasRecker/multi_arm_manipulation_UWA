"""Geometry, schedule selection, and start/monitor invariants for reviewed cartons."""
import copy
from types import SimpleNamespace
import time

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from uwa_cell_motion.common import joint_names
from uwa_cell_tasks import reviewed_carton as reviewed
from uwa_cell_tasks import reviewed_carton_execution as execution


def trajectory(arm,a,b):
    points=[dict(time=t,positions=[q]*6,velocities=[0.]*6,accelerations=[0.]*6)
            for t,q in ((0.,a),(1.,b))]
    return dict(joint_names=joint_names(arm),points=points,waypoints=[p['positions'] for p in points],duration_s=1.)


def test_bernstein_boxes_include_between_knot_overshoot():
    p=trajectory('right_front',0.,0.)
    p['points'][0]['velocities']=[.2]*6
    p['points'][1]['velocities']=[-.2]*6
    boxes=list(reviewed._joint_boxes(p,.005))
    from scipy.interpolate import BPoly
    func=BPoly.from_derivatives([0.,1.],[
        [v['positions'],v['velocities'],v['accelerations']] for v in p['points']])
    for q in func(np.linspace(0,1,301)):
        assert any(np.all(lo-1e-12<=q) and np.all(q<=hi+1e-12) for _,lo,hi in boxes)
    assert max(hi[0] for _,_,hi in boxes)>.05


def test_directional_stop_box_encloses_curved_six_axis_braking():
    axes=np.array([[0,0,1],[0,1,0],[0,1,0],[1,0,0],[0,1,0],[1,0,0]])
    levers=np.array([[.2,.1,.04],[.3,-.04,0],[.17,.04,.01],[.09,.02,-.08],[.04,-.09,.02],[.12,0,.03]])
    def forward(q):
        t=np.zeros(3);r=np.eye(3);origins=[];directions=[]
        for axis,lever,angle in zip(axes,levers,q):
            origins.append(t.copy());directions.append(r@axis)
            r=r@Rotation.from_rotvec(axis*angle).as_matrix()
            t=t+r@lever
        return t,np.column_stack([np.cross(d,t-p) for d,p in zip(directions,origins)])
    radii=np.cumsum(np.linalg.norm(levers,axis=1)[::-1])[::-1][None,:]
    rng=np.random.default_rng(1701)
    q0=rng.uniform(-2.,2.,6);p,j=forward(q0)
    dq=np.array([.13,.1,.15,.14,.1,.05])
    enclosure=reviewed.cartesian_stop_box(j[None,:,:],radii,dq)[0]
    for q in q0+rng.uniform(-1,1,(200,6))*dq:
        other,_=forward(q)
        assert np.all(np.abs(other-p)<=enclosure)
    assert np.all(enclosure<=float((radii@dq)[0])+1e-11)


def test_independent_progress_rejects_crossing_at_different_times():
    def samples(values):
        return np.array([[[p],[p]] for p in values],float)
    forward=samples([[0,0,0],[1,0,0]])
    reverse=samples([[1,0,0],[0,0,0]])
    assert reviewed.independent_clearance(forward,reverse,np.zeros((1,1)),.04)<=.04
    separated=samples([[0,1,0],[1,1,0]])
    assert reviewed.independent_clearance(forward,separated,np.zeros((1,1)),.04)==pytest.approx(1.)


@pytest.mark.parametrize('mode,expected',[
    ('together', [['right_front','right_rear']]),
    ('only_align', [['right_front','right_rear'],['right_front'],['right_rear']]),
    ('serial', [['right_front'],['right_rear']])])
def test_scheduler_groups_whole_task_and_emits_actual_boundaries(monkeypatch,mode,expected):
    arms=['right_front','right_rear']
    parts={a:[trajectory(a,0.,1.),trajectory(a,1.,2.)] for a in arms}
    start={j:0. for a in arms for j in joint_names(a)}
    def prove(problem,start,group,limit,collision):
        for arm,t in group.items():
            assert [start[j] for j in joint_names(arm)]==t['points'][0]['positions']
        valid=len(group)==1 or mode=='together' or (mode=='only_align' and
                all(t['points'][-1]['positions'][0]==1. for t in group.values()))
        return ({'pairs':[]},None if valid else 'no common corridor')
    monkeypatch.setattr(reviewed,'prove_group',prove)
    groups,_=reviewed.compile_groups(None,start,parts,.1)
    assert [g['arms']for g in groups]==expected


def test_read_bundle_and_final_build_preserve_exact_reviewed_content(tmp_path,monkeypatch):
    source=tmp_path/'source';source.write_bytes(b'source')
    p=SimpleNamespace(signature='model',binding='hardware')
    preview=tmp_path/'preview';preview.write_bytes(b'xml')
    file=tmp_path/'bundle'
    arm='right_rear';t=trajectory(arm,0.,.01)
    reviewed.write_bundle(file,'entry',p,{},[{'arms':[arm],'trajectories':{arm:t}}],[],source,preview,{},.1,.08)
    digest=reviewed.file_hash(file)
    saved=reviewed.read_bundle(file,digest,'entry',p,source)
    goal=execution._build_goal(saved['groups'][0]['trajectories'][arm])
    for point,old in zip(goal.trajectory.points,t['points']):
        assert list(point.positions)==old['positions']
        assert list(point.velocities)==old['velocities']
        assert list(point.accelerations)==old['accelerations']
        assert point.time_from_start.sec+point.time_from_start.nanosec/1e9==old['time']
    with pytest.raises(ValueError,match='digest'):
        reviewed.read_bundle(file,'wrong','entry',p,source)
    source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='binding'):
        reviewed.read_bundle(file,digest,'entry',p,source)
    source.write_bytes(b'source')
    monkeypatch.setattr(reviewed,'checker_identity',lambda _:dict(sha256='updated_checker'))
    with pytest.raises(ValueError,match='interpolation changed'):
        reviewed.read_bundle(file,digest,'entry',p,source)


def test_drifted_first_point_and_changed_target_do_not_authorize_a_rebase():
    a='right_front';t=trajectory(a,0.,1.);s={j:0. for j in joint_names(a)};end={j:1. for j in s}
    group=dict(arms=[a],start=s,trajectories={a:t},duration_s=1.)
    plan=dict(start=s,groups=[group])
    reviewed.check_boundaries(plan,s,end,[a])
    with pytest.raises(ValueError,match='endpoint'):
        reviewed.check_boundaries(plan,s,s,[a])
    t['points'][0]['positions'][0]=.005
    with pytest.raises(ValueError,match='first point'):
        reviewed.check_boundaries(plan,s,end,[a])


def test_concatenation_rejects_different_velocity_at_shared_pose():
    a=trajectory('right_front',0.,1.);b=trajectory('right_front',1.,2.)
    b['points'][0]['velocities'][2]=.1
    with pytest.raises(ValueError,match='junction'):
        reviewed.concatenate([a,b])


def test_force_baseline_rejects_old_samples_and_gripper_changes():
    now=time.monotonic(); rows=[dict(received=now-(11-i)*.05,force=[0.]*6) for i in range(12)]
    ob=SimpleNamespace(snapshot=lambda:rows)
    assert np.all(execution._fresh_force_reference('right_front',ob,.2)==0)
    rows[0]['received']-=2.
    with pytest.raises(RuntimeError,match='force baseline'):
        execution._fresh_force_reference('right_front',ob,.2)
    opened={'observed':True,'busy':False,'registers':dict(ACT=1,STA=3,OBJ=3,FLT=0,PRE=0,POS=3)}
    client=SimpleNamespace(jaws={'right_front':(now,opened)})
    execution._check_jaws(client,now)
    client.jaws['right_front']=(now-3,opened)
    with pytest.raises(RuntimeError,match='open-jaw'):
        execution._check_jaws(client,now)
    closed=copy.deepcopy(opened);closed['registers']['POS']=120
    client.jaws['right_front']=(now,closed)
    with pytest.raises(RuntimeError,match='open-jaw'):
        execution._check_jaws(client,now)


@pytest.mark.parametrize('policy,accepted',[('geometric_only',True),('enforce',False)])
def test_parallel_proof_honors_active_reserve_policy(monkeypatch,policy,accepted):
    arms=['right_front','right_rear'];seen=[]
    cfg=dict(stopping_reserve_policy=policy,state_timeout_s=.2,rate_hz=20.,stop_latency_s=1.,
             braking_acceleration_rad_s2=.2,model_margin_m=.04,velocity_limit_rad_s=.1)
    geometry=SimpleNamespace(motion_radii={a:np.ones((1,6))for a in arms},
                             radii={a:np.array([.05])for a in arms})
    p=SimpleNamespace(names={a:joint_names(a)for a in arms},spheres=geometry,cfg=cfg)
    start={j:0. for a in arms for j in joint_names(a)}
    def sweep(problem,state,arm,path,extra,dq):
        seen.append(dq.copy());center=np.array([[0.,0.,0.]])if arm==arms[0]else np.array([[.6,0.,0.]])
        nominal=np.array([[center,center]])
        stopped=nominal.copy()
        if np.any(dq):stopped[:,0]-=.8;stopped[:,1]+=.8
        return nominal,stopped
    monkeypatch.setattr(reviewed,'swept_arm',sweep)
    before=copy.deepcopy(cfg)
    proof,error=reviewed.prove_group(p,start,{a:trajectory(a,0.,.1)for a in arms},.1)
    assert (error is None)==accepted
    assert cfg==before
    assert all(np.any(q) for q in seen) if policy=='enforce' else all(not np.any(q)for q in seen)
    if accepted:
        assert proof['min_clearance_m']==pytest.approx(.5)
        assert proof['stop_policy']=='geometric_only'
        assert proof['progress_policy']=='all_independent_positions'


def test_geometric_only_parallel_still_rejects_intersecting_sweeps(monkeypatch):
    arms=['right_front','right_rear']
    p=SimpleNamespace(names={a:joint_names(a)for a in arms},cfg=dict(stopping_reserve_policy='geometric_only',
        state_timeout_s=.2,rate_hz=20.,stop_latency_s=1.,braking_acceleration_rad_s2=.2,
        model_margin_m=.04,velocity_limit_rad_s=.1),
        spheres=SimpleNamespace(motion_radii={a:np.ones((1,6))for a in arms},radii={a:np.array([.05])for a in arms}))
    start={j:0. for a in arms for j in joint_names(a)}
    def crossing(*args):
        boxes=np.zeros((1,2,1,3));return boxes,boxes
    monkeypatch.setattr(reviewed,'swept_arm',crossing)
    proof,error=reviewed.prove_group(p,start,{a:trajectory(a,0.,.1)for a in arms},.1)
    assert error and proof['pairs'][0]['geometric_clearance_lower_bound_m']<.04

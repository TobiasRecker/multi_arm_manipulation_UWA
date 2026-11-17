from pathlib import Path
import json
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.common import config,nominal_state,joint_names,PAIRS,ROBOT_IDS,BODY_RESERVE_MODEL
from uwa_cell_motion.geometry import SphereModel,sphere_aabb,aabb_separated
from uwa_cell_motion.planning import Problem


@pytest.fixture(scope='module')
def problem(tmp_path_factory):return Problem(tmp_path_factory.mktemp('prefilter'),config())


def test_bounds_enclose_complete_sphere_volumes_not_just_centres():
    a=sphere_aabb(np.array([[0.,0.,0.]]),np.array([2.]));b=sphere_aabb(np.array([[3.,0.,0.]]),np.array([2.]))
    assert np.all(a[0]<-2) and np.all(a[1]>2)
    assert not aabb_separated(a,b,.1)


@pytest.mark.parametrize('offset',[-1e-10,-1e-14,0.,1e-14,1e-10])
def test_near_threshold_uses_the_original_fine_decision(offset):
    model=SphereModel.__new__(SphereModel);model.radii={'a':np.array([.5]),'b':np.array([.5])}
    model.links={'a':['a'],'b':['b']};model.planning_stats=dict(pair_queries=0,prefilter_clear=0,fine_queries=0)
    world={'a':np.array([[0.,0.,0.]]),'b':np.array([[1.2+offset,0.,0.]])};bounds={r:sphere_aabb(p,model.radii[r]) for r,p in world.items()}
    original=model.nearest(world,'a','b')['clearance_m']>.2
    assert model.pair_clear(world,bounds,'a','b',.2)==original
    if abs(offset)<1e-12:assert model.planning_stats['fine_queries']==1


def test_random_clouds_match_dense_decisions_including_overlapping_hulls():
    rng=np.random.default_rng(64);clear=0
    for trial in range(1000):
        a=rng.normal(0,.5,(1+trial%17,3));b=rng.normal(0,.5,(1+trial%23,3))+(4 if trial%2 else 0)
        ra=rng.uniform(.01,.5,len(a));rb=rng.uniform(.01,.5,len(b));threshold=rng.uniform(0,.4)
        coarse=aabb_separated(sphere_aabb(a,ra),sphere_aabb(b,rb),threshold)
        dense=np.min(np.linalg.norm(a[:,None]-b[None],axis=2)-ra[:,None]-rb[None])>threshold
        assert not coarse or dense;clear+=coarse
    assert clear>400


def test_planning_cache_tracks_arm_and_mimic_tool_changes_and_rejects_stale_inputs(problem):
    state=nominal_state(problem.layout);model=problem.spheres;model._planning_cache.clear()
    world,bounds=model.planning_world(state);exact=model.world(state)
    assert all(np.array_equal(world[r],exact[r]) for r in world)
    again,_=model.planning_world(state);assert all(again[r] is world[r] for r in world)
    with pytest.raises(ValueError):again['right_rear'][0,0]=99
    state[joint_names('right_rear')[-1]]+=.01
    moved,_=model.planning_world(state)
    assert moved['right_rear'] is not world['right_rear']
    assert all(moved[r] is world[r] for r in world if r!='right_rear')
    state[problem.names['left_front'][6]]=.8
    closed,_=model.planning_world(state);exact=model.world(state)
    assert closed['left_front'] is not moved['left_front']
    assert all(np.array_equal(closed[r],exact[r]) for r in closed)
    bad=dict(state);bad.pop(joint_names('left_rear')[0])
    with pytest.raises(ValueError):model.planning_world(bad)
    bad=dict(state);bad[joint_names('left_rear')[0]]=float('nan')
    with pytest.raises(ValueError):model.planning_world(bad)


def test_all_fixed_suite_intervals_match_original_full_cell_check(problem):
    suite=json.loads((Path(__file__).parents[1]/'config/benchmark_suite_20261113.json').read_text());comparisons=0
    for case in suite['cases']:
        r=problem.normalize(case['request']);q0=np.array([r['start'][j] for j in r['joint_names']]);goal=np.array(r['target'])
        for u in np.linspace(0,1,9):
            q=q0+u*(goal-q0);state=problem.state(r,q);expected=problem.collision.check(state)[0]
            if expected:
                world=problem.spheres.world(state)
                expected=all(problem.spheres.nearest(world,*p['arms'])['clearance_m']>p['threshold_m'] for p in problem.thresholds())
            assert problem.check(r,q)==expected,(case['id'],u)
            comparisons+=1
    assert comparisons==270


def test_hardware_opening_hulls_keep_identical_clearance_decisions(tmp_path):
    from uwa_cell_motion.hardware_model import HardwareProblem,inventory_path
    p=HardwareProblem(tmp_path,config(Path(__file__).parents[1]/'config/hardware_motion.yaml'),inventory_path())
    state=nominal_state(p.layout);rng=np.random.default_rng(66)
    for _ in range(25):
        for rid in p.names:
            for j in joint_names(rid):state[j]+=float(rng.uniform(-.01,.01))
        world,bounds=p.spheres.planning_world(state);exact=p.spheres.world(state)
        assert all(np.array_equal(world[r],exact[r]) for r in world)
        for pair in p.thresholds():
            a,b=pair['arms'];threshold=pair['threshold_m']
            assert p.spheres.pair_clear(world,bounds,a,b,threshold)==(p.spheres.nearest(exact,a,b)['clearance_m']>threshold)


def test_guard_nearest_queries_still_return_exact_surface_points(problem):
    state=nominal_state(problem.layout);world=problem.spheres.world(state)
    for a,b in PAIRS:
        before=problem.spheres.nearest(world,a,b)
        cached,bounds=problem.spheres.planning_world(state)
        problem.spheres.pair_clear(cached,bounds,a,b,.01)
        assert problem.spheres.nearest(world,a,b)==before


def body_cloud_model(world,radii,totals):
    model=SphereModel.__new__(SphereModel)
    model.names={r:joint_names(r) for r in world};model.radii=radii
    model.links={r:[r]*len(p) for r,p in world.items()}
    model.planning_world=lambda _: (world,{})
    def budget(r,*args):
        total=np.asarray(totals[r]);zero=np.zeros(len(total))
        return dict(total_m=total,speed_m_s=zero,data_age_m=zero,
            sampling_m=zero,reaction_m=total,braking_m=zero)
    model.body_budget=budget
    model.planning_stats=dict(pair_queries=0,prefilter_clear=0,fine_queries=0)
    return model


def dense_body_clear(model,world,cfg):
    from uwa_cell_motion.stopping_reserve import critical_pair
    budgets={r:model.body_budget(r,None,None,None) for r in world}
    return all(critical_pair(a,b,world,model.radii,model.links,budgets,cfg)['remaining_clearance_m']>0 for a,b in PAIRS)


def test_body_prefilter_matches_dense_variable_reserves_on_random_clouds():
    rng=np.random.default_rng(1706);coarse=0;valid=0
    cfg=dict(model_margin_m=.04,heartbeat_timeout_s=.25,rate_hz=10.,state_timeout_s=.2)
    for trial in range(600):
        world={r:rng.normal(0,.4,(1+(trial+i)%17,3))+np.array([4*i if trial%2 else 0,0,0]) for i,r in enumerate(ROBOT_IDS)}
        radii={r:rng.uniform(.01,.3,len(p)) for r,p in world.items()}
        totals={r:rng.uniform(0,.5,len(p)) for r,p in world.items()}
        model=body_cloud_model(world,radii,totals)
        expected=dense_body_clear(model,world,cfg)
        assert model.planning_body_clear({},cfg)==expected
        coarse+=model.planning_stats['prefilter_clear'];valid+=expected
    assert valid>=300 and coarse>=1000


@pytest.mark.parametrize('offset',[-1e-10,-1e-14,0.,1e-14,1e-10])
def test_body_prefilter_preserves_exact_near_threshold_decision(offset):
    world={r:np.array([[i*10.,0,0]]) for i,r in enumerate(ROBOT_IDS)}
    a,b=PAIRS[0];world[a]=np.array([[0.,0,0]]);world[b]=np.array([[1.54+offset,0,0]])
    radii={r:np.array([.5]) for r in world};totals={r:np.array([.25]) for r in world}
    cfg=dict(model_margin_m=.04,heartbeat_timeout_s=.25,rate_hz=10.,state_timeout_s=.2)
    model=body_cloud_model(world,radii,totals)
    assert model.planning_body_clear({},cfg)==dense_body_clear(model,world,cfg)
    if abs(offset)<1e-12:assert model.planning_stats['fine_queries']>=1


def test_body_bounds_are_recomputed_when_budget_changes_without_geometry_change():
    world={r:np.array([[i*10.,0,0]]) for i,r in enumerate(ROBOT_IDS)}
    radii={r:np.array([.5]) for r in world};totals={r:np.array([.1]) for r in world}
    cfg=dict(model_margin_m=.04,heartbeat_timeout_s=.25,rate_hz=10.,state_timeout_s=.2)
    model=body_cloud_model(world,radii,totals)
    assert model.planning_body_clear({},cfg)
    totals['left_front']=np.array([100.])
    assert not model.planning_body_clear({},cfg)
    totals['left_front']=np.array([np.nan])
    with pytest.raises(ValueError):model.planning_body_clear({},cfg)


def test_hardware_body_filter_matches_original_with_complete_opening_envelopes(tmp_path):
    from uwa_cell_motion.hardware_model import HardwareProblem,inventory_path
    cfg=config(Path(__file__).parents[1]/'config/hardware_right_front_stop_test.yaml')
    cfg['joint_velocity_limits_rad_s']={r:[.003]*6 for r in ROBOT_IDS}
    model=HardwareProblem(tmp_path,cfg,inventory_path());rng=np.random.default_rng(1707)
    state=nominal_state(model.layout);checked=0
    for trial in range(100):
        current=dict(state)
        for r in ROBOT_IDS:
            for i,j in enumerate(joint_names(r)):
                current[j]=[0.,-np.pi/2,0.,-np.pi/2,0.,0.][i]+float(rng.uniform(-.15,.15))
        request=model.normalize(dict(start=current,goals={'left_front':[current[j] for j in joint_names('left_front')]}))
        q=request['target'];expected=model.collision.check(current)[0]
        if expected:
            _,pairs=model.spheres.pairs(current,{r:np.zeros(len(n)) for r,n in model.names.items()},
                {r:cfg['state_timeout_s'] for r in ROBOT_IDS},cfg)
            expected=all(p['remaining_clearance_m']>0 for p in pairs);checked+=1
        assert model.check(request,q)==expected
    assert checked>10

from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.common import config,nominal_state,ROBOT_IDS,joint_names,gripper_joint
from uwa_cell_motion.planning import Problem


@pytest.fixture(scope='module')
def problem(tmp_path_factory):
    return Problem(tmp_path_factory.mktemp('cell-motion'),config(Path(__file__).parents[1]/'config/motion.yaml'))


def simple(problem):
    start=nominal_state(problem.layout);rid='left_front'
    q=[start[j] for j in joint_names(rid)];q[-1]+=.04
    return dict(start=start,goals={rid:q})


def test_all_68_collision_bodies_have_volume_cover(problem):
    assert len(problem.spheres.coverage)==68
    assert all(c['spheres']>0 for c in problem.spheres.coverage)
    for rid in ROBOT_IDS:
        assert any(c['arm']==rid and 'finger_tip' in c['link'] for c in problem.spheres.coverage)
        assert any(c['arm']==rid and 'wrist_camera' in c['link'] for c in problem.spheres.coverage)


def test_open_closed_fingers_change_sphere_positions(problem):
    start=nominal_state(problem.layout);rid='left_front';start[gripper_joint(rid)]=0
    opened=problem.spheres.world(start)[rid]
    start[gripper_joint(rid)]=.8;closed=problem.spheres.world(start)[rid]
    assert np.max(np.linalg.norm(opened-closed,axis=1))>.02


def test_analytic_control_point_jacobian_matches_finite_difference(problem):
    state=nominal_state(problem.layout);world,jac=problem.spheres.jacobians(state,['left_front'])
    for k,name in enumerate(joint_names('left_front')):
        moved=problem.spheres.world(dict(state,**{name:state[name]+1e-6}))
        assert np.allclose(jac['left_front'][:,:,k],(moved['left_front']-world['left_front'])/1e-6,atol=2e-6)


def test_default_simulation_pose_has_stop_reserve(problem):
    r=problem.normalize(simple(problem));assert problem.check(r,[r['start'][j] for j in r['joint_names']])


def test_missing_arm_geometry_preserves_independent_neighbor_pairs(problem):
    state=nominal_state(problem.layout)
    for j in problem.names['left_front']:state.pop(j)
    world=problem.spheres.world(state,partial=True)
    assert set(world)==set(ROBOT_IDS)-{'left_front'}
    v={r:np.zeros(len(problem.names[r])) for r in world};ages={r:0. for r in world}
    _,pairs=problem.spheres.pairs(state,v,ages,problem.cfg,partial=True)
    assert {tuple(p['arms']) for p in pairs}=={('right_front','right_rear'),('left_rear','right_rear')}


def test_incomplete_start_cannot_become_executable(problem):
    r=simple(problem);r['start'].pop(gripper_joint('left_front'))
    with pytest.raises(ValueError):problem.normalize(r)


def test_cartesian_requires_explicit_frame_and_link(problem):
    r=simple(problem);r['goals']['left_front']={'pose':{'position':[0,0,0],'orientation_xyzw':[0,0,0,1]}}
    with pytest.raises(ValueError):problem.normalize(r)


def test_cartesian_normalization_uses_a_common_valid_joint_goal(problem):
    from uwa_cell_gazebo.charuco_views import Chain
    from scipy.spatial.transform import Rotation
    r=simple(problem);pose=Chain(problem.description,'world','left_front_tool0').forward(r['start'])
    r['goals']['left_front']=dict(frame_id='world',target_link='left_front_tool0',pose=dict(
        position=pose[:3,3].tolist(),orientation_xyzw=Rotation.from_matrix(pose[:3,:3]).as_quat().tolist()))
    normalized=problem.normalize(r)
    assert problem.check(normalized,normalized['target'])


def test_expired_edge_budget_returns_no_success(problem):
    r=problem.normalize(simple(problem));a=[r['start'][j] for j in r['joint_names']]
    assert not problem.edge(r,a,r['target'],deadline=0.)


def test_waiting_coordinator_produces_checked_stationary_arm_phases(problem):
    import time
    r=simple(problem);rid='right_front'
    r['goals'][rid]=[r['start'][j]+(.03 if j.endswith('wrist_3_joint') else 0) for j in joint_names(rid)]
    r=problem.normalize(r);path=problem.serial_direct(r,time.monotonic()+2.)
    assert path and len(path)==3
    assert np.allclose(path[0][6:],path[1][6:])
    assert np.allclose(path[-1],r['target'])
    assert all(problem.edge(r,a,b) for a,b in zip(path,path[1:]))


def test_fixed_suite_has_30_balanced_bound_cases(problem):
    import json
    from collections import Counter
    suite=json.loads((Path(__file__).parents[1]/'config/benchmark_suite_20261113.json').read_text())
    assert suite['model_signature']==problem.signature
    assert len(suite['cases'])==30 and set(Counter(c['category'] for c in suite['cases']).values())=={5}


def test_fixed_neighbor_cases_really_intersect_sphere_paths(problem):
    import json
    suite=json.loads((Path(__file__).parents[1]/'config/benchmark_suite_20261113.json').read_text())
    for case in suite['cases']:
        if case['category']!='neighbor_crossing':continue
        request=problem.normalize(case['request']);a,b=request['selected']
        q0=np.asarray([request['start'][j] for j in request['joint_names']]);q1=np.asarray(request['target'])
        assert problem.check(request,q0) and problem.check(request,q1)
        assert any(problem.spheres.nearest(problem.spheres.world(problem.state(request,q0+u*(q1-q0))),a,b)['clearance_m']<=0
                   for u in np.linspace(.05,.95,19))


def test_shared_timing_respects_limits_and_full_cell(problem):
    request=problem.normalize(simple(problem));q0=[request['start'][j] for j in request['joint_names']]
    trajectory=problem.time_parameterize(request,[q0,request['target']]);points=trajectory['points']
    assert max(np.max(np.abs(p['velocities'])) for p in points)<=problem.cfg['velocity_limit_rad_s']+1e-9
    assert max(np.max(np.abs(p['accelerations'])) for p in points)<=problem.cfg['acceleration_limit_rad_s2']+1e-5
    assert all(problem.check(request,p['positions']) for p in points)
    assert np.allclose(points[-1]['positions'],request['target'])
    assert all(b['time']>a['time'] for a,b in zip(points,points[1:]))


def test_changed_endpoint_and_nonfinite_paths_rejected(problem):
    request=problem.normalize(simple(problem));q0=[request['start'][j] for j in request['joint_names']]
    with pytest.raises(ValueError):problem.time_parameterize(request,[q0,q0])
    with pytest.raises(ValueError):problem.time_parameterize(request,[q0,[np.nan]*6])


def test_invalid_goal_is_recorded_for_both_planners(problem):
    request=simple(problem);request['goals']['left_front'][0]=100
    for method in ('rrtconnect','circular'):
        result=problem.plan(request,method)
        assert not result['success'] and result['error']=='INVALID_GOAL'


def test_unknown_planner_cannot_silently_use_another(problem):
    with pytest.raises(ValueError):problem.plan(simple(problem),'unknown')


def test_native_rrt_and_circular_return_checked_same_goal(problem):
    request=simple(problem)
    for method in ('rrtconnect','circular'):
        result=problem.plan(request,method)
        assert result['success'],method+': '+str(result.get('error'))
        assert result['metrics']['full_cell_collision_checked']
        assert np.allclose(result['trajectory']['points'][-1]['positions'],request['goals']['left_front'])


def test_native_rrt_worker_runs_without_direct_shortcut(problem):
    request=problem.normalize(simple(problem))
    path,error=problem.rrt(request,0,10.)
    assert path is not None,error
    assert np.allclose(path[-1],request['target'])
    assert all(problem.edge(request,a,b) for a,b in zip(path,path[1:]))

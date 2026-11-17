from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).parents[1]))
from uwa_cell_motion.candidates import enumerate_candidates
from uwa_cell_motion.common import config, nominal_state, joint_names, ROBOT_IDS
from uwa_cell_motion.planning import Problem
from uwa_cell_gazebo.charuco_views import Chain

@pytest.fixture(scope='module')
def problem(tmp_path_factory):
    return Problem(tmp_path_factory.mktemp('candidate-model'), config(Path(__file__).parents[1]/'config/motion.yaml'))

def request(problem):
    start=nominal_state(problem.layout)
    return dict(start=start, goals={r:dict(positions=[start[j] for j in joint_names(r)]) for r in ROBOT_IDS})

def pose_goal(problem, rid, state):
    pose=Chain(problem.description,'world',rid+'_tool0').forward(state)
    return dict(frame_id='world',target_link=rid+'_tool0',pose=dict(position=pose[:3,3].tolist(),
                orientation_xyzw=Rotation.from_matrix(pose[:3,:3]).as_quat().tolist()))

def test_four_arm_endpoint_and_all_six_pairs(problem):
    result=enumerate_candidates(problem,request(problem))
    assert len(result['combinations']) == 1
    assert len(result['combinations'][0]['pair_clearances']) == 6
    assert result['executable'] is False
    assert result['search']['retained_product_exhausted']
    assert result['model_signature']==problem.signature

def test_alternatives_are_kept_and_duplicates_merge_sources(problem):
    r=request(problem);rid='left_front';q=r['goals'][rid]['positions'];other=q.copy();other[-1]+=.02
    r['goals'][rid]={'alternatives':[{'positions':q},{'positions':other},{'positions':q}]}
    result=enumerate_candidates(problem,r)
    assert len(result['candidates'][rid])==2
    assert result['candidates'][rid][0]['alternative_indices']==[0,2]
    assert len(result['combinations'])==2

def test_joint_limits_and_unreachable_pose_are_not_success(problem):
    r=request(problem);r['goals']['left_front']={'positions':[100]*6}
    result=enumerate_candidates(problem,r)
    assert not result['combinations'] and not result['candidates']['left_front']
    r=request(problem);g=pose_goal(problem,'left_front',r['start']);g['pose']['position']=[100,100,100]
    r['goals']={'left_front':g}
    result=enumerate_candidates(problem,r,seeds=1)
    assert result['status']=='NO_VALID_COMBINATION_FOUND'
    assert not result['search']['complete_ik']

def test_ik_alternatives_reconstruct_target(problem):
    r=request(problem);rid='right_rear';goal=pose_goal(problem,rid,r['start']);r['goals']={rid:goal}
    result=enumerate_candidates(problem,r,seeds=12,budget_s=35)
    assert len(result['candidates'][rid])>=2
    desired=np.asarray(goal['pose']['position'])
    for c in result['candidates'][rid]:
        state=dict(r['start'],**dict(zip(joint_names(rid),c['positions'])))
        actual=Chain(problem.description,'world',rid+'_tool0').forward(state)
        assert np.linalg.norm(actual[:3,3]-desired)<=1e-4
        assert c['position_error_m']<=1e-4 and c['orientation_error_rad']<=1e-4
    assert result['combinations']

@pytest.mark.parametrize('kind',['missing','nan','frame','quaternion','foreign','unknown'])
def test_invalid_requests_rejected_before_search(problem,kind):
    r=request(problem);g=pose_goal(problem,'left_front',r['start']);r['goals']={'left_front':g}
    if kind=='missing':r['start'].pop(next(iter(r['start'])))
    if kind=='nan':r['start'][next(iter(r['start']))]=float('nan')
    if kind=='frame':g['frame_id']='base'
    if kind=='quaternion':g['pose']['orientation_xyzw']=[0,0,0,0]
    if kind=='foreign':g['target_link']='right_front_tool0'
    if kind=='unknown':g['target_link']='left_front_nonexistent'
    with pytest.raises(ValueError):enumerate_candidates(problem,r)

def test_expired_search_is_reported_not_infeasible(problem):
    result=enumerate_candidates(problem,request(problem),budget_s=1e-12)
    assert result['search']['deadline_reached']
    assert result['status']=='NO_VALID_COMBINATION_FOUND'

def test_check_cap_reports_remaining_search(problem):
    r=request(problem);q=r['goals']['left_front']['positions'];q2=q.copy();q2[-1]+=.02
    r['goals']['left_front']={'alternatives':[q,q2]}
    result=enumerate_candidates(problem,r,max_checks=1)
    assert result['search']['combinations_checked']==1
    assert result['search']['combinations_pending']==1
    assert not result['search']['retained_product_exhausted']

def test_conflicting_candidates_are_retained_until_combined_check(problem,monkeypatch):
    r=request(problem)
    monkeypatch.setattr(problem,'check',lambda request,q:False)
    result=enumerate_candidates(problem,r)
    assert all(result['candidates'].values())
    assert not result['combinations']

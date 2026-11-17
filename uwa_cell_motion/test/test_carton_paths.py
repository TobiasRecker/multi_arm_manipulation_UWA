from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.carton_paths import (CartonProblem,cartesian_entry,corner_targets,evaluate,
                                        joint_segment,pose_goal,quintic,upright_start,validate_segment)
from uwa_cell_motion.common import ROBOT_IDS,config,joint_names


@pytest.fixture(scope='module')
def problem(tmp_path_factory):
    return CartonProblem(tmp_path_factory.mktemp('carton-path-model'),config(Path(__file__).parents[1]/'config/motion.yaml'))


def test_zero_start_rejected_upright_valid_and_carton_is_present(problem):
    start=upright_start(problem.layout)
    assert problem.collision.check(start)[0]
    zero=dict(start)
    for r in ROBOT_IDS:zero.update(dict.fromkeys(joint_names(r),0.))
    assert not problem.collision.check(zero)[0]
    assert 'offline_carton' in problem.collision.description
    assert 'carton.stl' in problem.collision.description


def test_fixed_nearest_corners_and_vertical_entry(problem):
    targets=corner_targets(problem)
    assert len({t['corner_index'] for t in targets.values()})==4
    for arm,t in targets.items():
        goal=np.asarray(t['tool0_target']);pre=np.asarray(t['tool0_pregrasp']);tcp=goal@t['tool0_to_tcp']
        assert np.allclose(tcp[:3,3],t['tcp_world_m'])
        assert np.allclose(tcp[:3,2],[0,0,-1])
        assert np.allclose(pre[:3,:3],goal[:3,:3])
        assert np.allclose(pre[:3,3]-goal[:3,3],[0,0,.12])
        assert np.allclose(np.asarray(t['corner_world_m'])-t['tcp_world_m'],[0,0,.015])
        assert pose_goal(arm,goal)['target_link']==arm+'_tool0'


def test_quintic_stops_and_joint_path_has_no_overshoot():
    a=np.array([0,-1,2,0,1,-2.]);b=np.array([1,1,-1,2,0,1.]);s=joint_segment(a,b)
    u=np.linspace(0,1,501);q=evaluate(s,u)
    assert np.allclose(q[0],a) and np.allclose(q[-1],b)
    assert np.all(q>=np.minimum(a,b)-1e-10) and np.all(q<=np.maximum(a,b)+1e-10)
    assert np.allclose(evaluate(s,[0,1],1),0)
    assert np.allclose(evaluate(s,[0,1],2),0)
    assert np.all(np.diff(quintic(u))>=0)


def test_static_checker_rejects_an_entire_segment_with_invalid_end(problem):
    start=upright_start(problem.layout);arm='left_front';q=[start[j] for j in joint_names(arm)]
    with pytest.raises(ValueError,match='collision'):
        validate_segment(problem,arm,start,joint_segment(q,[0]*6))


def test_safe_small_segment_and_sample_bound(problem):
    start=upright_start(problem.layout);arm='right_rear';q=np.array([start[j] for j in joint_names(arm)])
    other=q.copy();other[0]+=.03
    result=validate_segment(problem,arm,start,joint_segment(q,other))
    assert result['max_joint_step_rad']<=.005
    assert result['samples']>=257 and result['duration_s']>0


def test_sampling_checks_smoothed_between_knots(problem,monkeypatch):
    start=upright_start(problem.layout);arm='right_rear';q=np.array([start[j] for j in joint_names(arm)]);other=q.copy();other[0]=.1
    key=joint_names(arm)[0]
    # Endpoints clear, interior collision: knot-only validation would miss it.
    monkeypatch.setattr(problem.isolated[arm],'check',lambda state:(not .04<state[key]<.06,[]))
    with pytest.raises(ValueError,match='collision'):
        validate_segment(problem,arm,start,joint_segment(q,other))


def test_cartesian_spline_derivatives_and_wrong_line_rejected(problem):
    start=upright_start(problem.layout);arm='right_rear';q=[start[j] for j in joint_names(arm)]
    target=problem.chains[arm].forward(start);target[0,3]+=.2
    segment=dict(kind='CARTESIAN_LINE',knots=[0,.5,1],positions=[q,q,q],target=target.tolist(),pregrasp_m=.12)
    assert np.allclose(evaluate(segment,[0,1],1),0)
    assert np.allclose(evaluate(segment,[0,1],2),0)
    with pytest.raises(ValueError,match='pose tolerance'):
        validate_segment(problem,arm,start,segment)

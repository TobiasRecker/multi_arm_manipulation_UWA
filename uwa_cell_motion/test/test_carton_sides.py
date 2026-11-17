from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.carton_sides import nearest_free_assignment,side_targets
from uwa_cell_motion.carton_paths import CartonProblem
from uwa_cell_motion.common import config


def test_competing_preference_uses_next_free_side():
    assigned,distances=nearest_free_assignment([[.1,0],[.2,0],[1.9,0]],[[0,0],[1,0],[2,0]])
    assert assigned=={0:0,2:2,1:1}
    assert len(set(assigned.values()))==3
    assert np.argmin(distances[1])==0 and assigned[1]==1


def test_ties_are_deterministic():
    assigned,_=nearest_free_assignment([[0,0],[0,0]],[[-1,0],[1,0]])
    assert assigned=={0:0,1:1}


def test_impossible_nearest_two_assignment_rejected():
    # The globally closest pair would consume the only alternative of robot 1.
    bases=[[0,.1],[0,.2],[2,.1],[2,.2]]
    sites=[[0,0],[2,0],[1,1],[1,-2]]
    with pytest.raises(ValueError,match='nearest two'):nearest_free_assignment(bases,sites)


def test_too_few_sites_rejected():
    with pytest.raises(ValueError):nearest_free_assignment([[0,0],[1,0]],[[0,0]])


def test_four_unique_side_midpoints_and_wall_normal_closing(tmp_path):
    p=CartonProblem(tmp_path,config(Path(__file__).parents[1]/'config/motion.yaml'))
    targets=side_targets(p);dims=np.array(p.carton['manifest']['dimensions_m'])
    assert len({t['side_index'] for t in targets.values()})==4
    assert all(t['preference_rank']<=2 for t in targets.values())
    for t in targets.values():
        local=np.array(t['side_local_m']);assert local[2]==dims[2]
        assert sum(np.isclose(local[:2],dims[:2]/2))==1
        tcp=np.asarray(t['tool0_target'])@t['tool0_to_tcp']
        assert np.allclose(tcp[:3,3],t['tcp_world_m'])
        assert np.allclose(tcp[:3,2],[0,0,-1])
        assert np.allclose(tcp[:3,0],t['closing_axis_world'])
        assert np.allclose(np.asarray(t['tool0_pregrasp'])[:3,3]-np.asarray(t['tool0_target'])[:3,3],[0,0,.12])
        assert np.allclose(np.asarray(t['side_world_m'])-t['tcp_world_m'],[0,0,.015])
    # A tilted box must not silently inherit gravity-aligned wall-pinch targets.
    p.carton['T_world_object']=p.carton['T_world_object'].copy()
    p.carton['T_world_object'][0,2]=.1
    with pytest.raises(ValueError,match='upright'):side_targets(p)


def test_offline_static_policy_keeps_all_six_pair_margins(tmp_path):
    p=CartonProblem(tmp_path,config(Path(__file__).parents[1]/'config/motion.yaml'),endpoint_policy='static_margin')
    assert len(p.thresholds())==6
    assert all(t['threshold_m']==p.cfg['model_margin_m'] for t in p.thresholds())
    p.endpoint_policy='stop_reserve'
    assert len(p.thresholds())==4
    assert all(t['threshold_m']>p.cfg['model_margin_m'] for t in p.thresholds())

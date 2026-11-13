from pathlib import Path
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.single_execution import corridor_error


def test_time_lag_on_checked_path_is_safe_but_geometric_departure_is_detected():
    vertices=np.array([[0.,0.],[1.,1.],[1.,2.]])
    start=vertices[:-1];delta=np.diff(vertices,axis=0);squared=np.sum(delta*delta,axis=1)
    assert corridor_error(np.array([.2,.2]),start,delta,squared)<1e-12
    assert corridor_error(np.array([.8,.8]),start,delta,squared)<1e-12
    assert corridor_error(np.array([.5,.7]),start,delta,squared)>.05


def test_stationary_waypoint_has_finite_corridor_distance():
    start=np.array([[1.,2.]]);delta=np.zeros((1,2));squared=np.array([1e-20])
    assert corridor_error(np.array([1.,2.]),start,delta,squared)==0
    assert np.isclose(corridor_error(np.array([1.,2.01]),start,delta,squared),.01)

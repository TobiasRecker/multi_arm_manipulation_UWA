import numpy as np
import pytest
from uwa_cell_tasks.timing import interpolation_peak,limit_shared_jerk


def test_shared_retiming_bounds_quintic_jerk_and_preserves_geometry():
    trajectory=dict(duration_s=1.,points=[dict(time=t,positions=[q,2*q],
        velocities=[0.,0.],accelerations=[0.,0.]) for t,q in [(0.,0.),(1.,1.)]])
    assert interpolation_peak(trajectory,3)==pytest.approx(120.)
    result=limit_shared_jerk(trajectory,15.)
    assert result['duration_s']==pytest.approx(2.,rel=2e-6)
    assert interpolation_peak(result,3)<=15.
    assert result['points'][1]['positions']==[1.,2.]
    assert trajectory['duration_s']==1.


def test_extrema_inside_segments_are_included():
    # q(t)=t^4-t^5: jerk=24t-60t² has an internal extremum at0.2.
    trajectory=dict(duration_s=1.,points=[
        dict(time=0.,positions=[0.],velocities=[0.],accelerations=[0.]),
        dict(time=1.,positions=[0.],velocities=[-1.],accelerations=[-8.])])
    assert interpolation_peak(trajectory,3)==pytest.approx(36.)
    # Restrict to [0,.3], where the internal maximum exceeds both endpoints.
    t=.3
    trajectory['points'][1]=dict(time=t,positions=[t**4-t**5],
        velocities=[4*t**3-5*t**4],accelerations=[12*t**2-20*t**3])
    assert interpolation_peak(trajectory,3)==pytest.approx(2.4)
    for limit in (0.,-1.,np.inf):
        with pytest.raises(ValueError):limit_shared_jerk(trajectory,limit)

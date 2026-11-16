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


def test_local_object_timing_bounds_endpoint_curvature_without_global_slowdown():
    from scipy.interpolate import CubicSpline
    from uwa_cell_tasks.timing import object_law_duration
    # High curvature near rest must be paired with the near-zero object speed.
    x=np.r_[0.,.0001,.0002,.001,.01,.1,.5,1.]
    q=np.column_stack([x+.001*np.exp(-x/.0001),np.sin(2*x)])
    spline=CubicSpline(x,q,axis=0)
    duration=object_law_duration(spline,.04,.25)*1.02
    u=np.linspace(0,1,200001);s=10*u**3-15*u**4+6*u**5
    ds=30*u**2*(1-u)**2;dds=60*u-180*u**2+120*u**3
    assert np.max(abs(spline(s,1)*ds[:,None]))/duration<=.04
    assert np.max(abs(spline(s,2)*ds[:,None]**2+spline(s,1)*dds[:,None]))/duration**2<=.25
    gradient=spline(np.linspace(0,1,100001),1);curvature=spline(np.linspace(0,1,100001),2)
    old=max(1.875*np.max(abs(gradient))/.04,np.sqrt((np.max(abs(curvature))*1.875**2+np.max(abs(gradient))*5.774)/.25))
    assert duration<old/2

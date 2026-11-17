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


def test_fivefold_time_compression_preserves_geometry_and_controller_polynomial():
    from uwa_cell_tasks.core import seal
    from uwa_cell_tasks.timing import scale_object_time,interpolation_peak
    from scipy.interpolate import BPoly
    name='right_front_wrist_1_joint'
    source=seal(dict(kind='rigid_object',joint_names=[name],duration_s=10.,points=[
        dict(time=0.,positions=[0.],velocities=[0.],accelerations=[0.],object_pose=np.eye(4).tolist()),
        dict(time=10.,positions=[.01],velocities=[0.],accelerations=[0.],object_pose=np.eye(4).tolist())]))
    cfg=dict(carrying_speed_multiplier=5.,joint_velocity_rad_s=.04,joint_acceleration_rad_s2=.25)
    fast=scale_object_time(source,cfg)
    assert fast['duration_s']==2. and source['duration_s']==10.
    assert [p['positions'] for p in fast['points']]==[p['positions'] for p in source['points']]
    def polynomial(t):return BPoly.from_derivatives([p['time'] for p in t['points']],
        [[p['positions'],p['velocities'],p['accelerations']] for p in t['points']])
    old,new=polynomial(source),polynomial(fast);u=np.linspace(0,2,101)
    for derivative in range(4):
        np.testing.assert_allclose(new.derivative(derivative)(u),old.derivative(derivative)(u*5)*5**derivative,atol=1e-12)


def test_time_compression_rejects_an_envelope_violation():
    from uwa_cell_tasks.core import seal
    from uwa_cell_tasks.timing import scale_object_time
    source=seal(dict(kind='rigid_object',joint_names=['right_front_wrist_1_joint'],duration_s=1.,
        points=[dict(time=0.,positions=[0.],velocities=[.02],accelerations=[0.]),
                dict(time=1.,positions=[.02],velocities=[.02],accelerations=[0.])]))
    with pytest.raises(ValueError,match='per-joint velocity'):
        scale_object_time(source,dict(carrying_speed_multiplier=5,joint_velocity_rad_s=.04,joint_acceleration_rad_s2=.25))


def test_batched_extrema_match_monolithic_polynomials_across_boundaries():
    from scipy.interpolate import BPoly,PPoly
    from uwa_cell_tasks.timing import interpolation_peaks
    rng=np.random.default_rng(24)
    times=np.cumsum(rng.uniform(.05,.1,270))
    values=rng.normal(size=(270,3,2))*.01
    trajectory=dict(points=[dict(time=float(t),positions=v[0].tolist(),
        velocities=v[1].tolist(),accelerations=v[2].tolist()) for t,v in zip(times,values)])
    for derivative in (1,2,3):
        polynomial=PPoly.from_bernstein_basis(BPoly.from_derivatives(times,values)).derivative(derivative)
        expected=np.zeros(2)
        for i,width in enumerate(np.diff(times)):
            for j in range(2):
                c=polynomial.c[:,i,j];roots=np.roots(np.polyder(c))
                candidates=[0.,width]+[r.real for r in roots if abs(r.imag)<1e-9 and 0<r.real<width]
                expected[j]=max(expected[j],max(abs(np.polyval(c,candidates))))
        np.testing.assert_allclose(interpolation_peaks(trajectory,derivative),expected,rtol=1e-12)

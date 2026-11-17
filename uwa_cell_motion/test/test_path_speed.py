from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.interpolate import CubicSpline

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.carton_paths import joint_segment,path_at,evaluate,quintic
from uwa_cell_motion.path_speed import scale_path,velocity_at,primitive_bounds


def example():
    a=joint_segment(np.zeros(6),np.arange(1,7)*.1);a['check']=dict(duration_s=4.)
    b=joint_segment(np.arange(1,7)*.1,np.arange(1,7)*.2);b['check']=dict(duration_s=2.)
    return dict(duration_s=6.,segments=[a,b])


def test_uniform_scaling_preserves_all_positions_and_scales_velocity():
    path=example();fast=scale_path(path,10)
    assert path['duration_s']==6 and fast['duration_s']==.6
    for t in np.linspace(0,7,151):
        assert np.allclose(path_at(path,t),path_at(fast,t/10),atol=1e-12)
        assert np.allclose(velocity_at(fast,t/10),10*velocity_at(path,t),atol=1e-10)
    assert np.allclose(velocity_at(fast,1),0)


def test_quintic_bounds_cover_known_analytic_peaks():
    s=example()['segments'][0];b=primitive_bounds(s);delta=np.arange(1,7)*.1;T=4.
    exact=[delta*1.875/T,delta*(10*np.sqrt(3)/3)/T**2,delta*60/T**3]
    for key,wanted in zip(['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3'],exact):
        assert np.all(np.asarray(b[key])>=wanted-1e-11)
        assert np.allclose(b[key],wanted,rtol=1e-5)


def test_spline_bounds_cover_dense_analytic_derivatives_and_one_sided_knots():
    x=np.linspace(0,1,9);y=np.array([np.sin((i+1)*x)*.1 for i in range(6)]).T
    s=dict(knots=x.tolist(),positions=y.tolist(),check=dict(duration_s=2.))
    b=primitive_bounds(s);u=np.linspace(0,1,100001);h=quintic(u);sp=CubicSpline(x,y,bc_type='natural')
    hp=30*u*u*(1-u)**2;hpp=60*u-180*u*u+120*u**3;hppp=60-360*u+360*u*u
    values=[sp(h,1)*hp[:,None]/2,
            (sp(h,2)*hp[:,None]**2+sp(h,1)*hpp[:,None])/4,
            (sp(h,3)*hp[:,None]**3+3*sp(h,2)*(hp*hpp)[:,None]+sp(h,1)*hppp[:,None])/8]
    for key,v in zip(['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3'],values):
        assert np.all(np.max(abs(v),axis=0)<=np.asarray(b[key])+1e-10)


def test_derivative_bounds_obey_time_power_laws():
    path=example();fast=scale_path(path,10)
    a=primitive_bounds(path['segments'][0]);b=primitive_bounds(fast['segments'][0])
    for power,key in enumerate(['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3'],1):
        assert np.allclose(b[key],np.asarray(a[key])*10**power,rtol=1e-8)


@pytest.mark.parametrize('factor',[0,-1,float('nan'),float('inf')])
def test_bad_factors_rejected(factor):
    with pytest.raises(ValueError):scale_path(example(),factor)

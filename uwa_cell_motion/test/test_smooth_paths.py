from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.smooth_paths import (curve,curve_bounds,plan_segment,progress,ramp_profile,
                                         sample_segment,spatial_deviation)


def segment(kind='JOINT'):
    x=np.linspace(0,1,61) if kind!='JOINT' else np.array([0.,1.])
    y=np.array([a*x+.03*np.sin(x*2) if kind!='JOINT' else a*x for a in np.linspace(.1,5,6)]).T
    return dict(kind=kind,knots=x.tolist(),positions=y.tolist(),check=dict(duration_s=20.))


@pytest.mark.parametrize('caps',[(.1,.4,2.),(10.,.1,1.),(2.,5.,.01)])
def test_monotone_unit_progress_and_c3_joins(caps):
    law=ramp_profile(*caps);times=np.linspace(0,law['duration_s'],10001)
    s,v,a,j=progress(law,times)
    assert s[0]==0 and s[-1]==1 and np.min(np.diff(s))>=-1e-12
    assert max(v)<=caps[0]*(1+1e-9)
    assert max(abs(a))<=caps[1]*(1+1e-9)
    assert max(abs(j))<=caps[2]*(1+1e-9)
    for boundary in [0,law['ramp_s'],law['ramp_s']+law['cruise_s'],law['duration_s']]:
        left=progress(law,boundary-1e-8);right=progress(law,boundary+1e-8)
        assert np.allclose(left,right,atol=2e-6)


@pytest.mark.parametrize('kind',['JOINT','CARTESIAN_LINE'])
def test_joint_limits_and_fixed_geometry(kind):
    source=segment(kind);new=plan_segment(source)
    s=np.linspace(0,1,20001);t=np.linspace(0,new['time_law']['duration_s'],20001)
    assert np.max(abs(spatial_deviation(source,new,s)))<2e-6
    assert np.allclose(sample_segment(new,0),source['positions'][0])
    assert np.allclose(sample_segment(new,t[-1]),source['positions'][-1])
    for derivative,limit in [(1,.45),(2,.4),(3,2.)]:
        assert np.max(abs(sample_segment(new,t,derivative)))<=limit*(1+1e-6)
        assert np.allclose(sample_segment(new,[0,t[-1]],derivative),0,atol=1e-10)


def test_curve_bounds_cover_dense_derivatives():
    s=segment('CARTESIAN_LINE');sp=curve(s);bound=curve_bounds(s);x=np.linspace(0,1,100001)
    for i in range(1,4):assert np.all(np.max(abs(sp(x,nu=i)),axis=0)<=bound[i-1]+1e-8)


@pytest.mark.parametrize('caps',[(0,1,1),(1,-1,1),(1,1,float('nan'))])
def test_invalid_limits(caps):
    with pytest.raises(ValueError):ramp_profile(*caps)

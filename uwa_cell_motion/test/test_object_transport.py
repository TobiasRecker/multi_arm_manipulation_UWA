from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.object_transport import object_pose,skew,yaw_basis
from uwa_cell_motion.smooth_paths import curve_bounds,plan_segment,sample_segment


def test_yaw_is_bounded_and_end_orientation_fixed():
    x=np.linspace(0,1,5001);B=yaw_basis(x)
    assert B.shape==(len(x),6)
    assert np.min(B)>=0 and np.max(B.sum(axis=1))<=1+1e-14
    assert np.allclose(B[[0,-1]],0)
    controls=np.deg2rad([-15,15,-15,15,-15,15])
    assert np.max(abs(B@controls))<=np.deg2rad(15)


def test_lift_transfer_lower_rotates_about_centre():
    initial=np.eye(4);initial[:3,3]=[.03,.007,.985]
    initial[:3,:3]=Rotation.from_euler('z',90,degrees=True).as_matrix()
    for s,delta in [(0,[0,0,0]),(1/3,[0,0,.1]),(.5,[-.1,0,.1]),(2/3,[-.2,0,.1]),(1,[-.2,0,0])]:
        pose=object_pose(initial,[-.2,0,0],.1,s,.2)
        assert np.allclose(pose[:3,3],initial[:3,3]+delta)
        assert np.allclose(pose[:3,:3],Rotation.from_euler('z',.2).as_matrix()@initial[:3,:3])
    assert np.allclose(skew([1,2,3])@[4,5,6],np.cross([1,2,3],[4,5,6]))


@pytest.mark.parametrize('kind',['JOINT','OBJECT_DERIVED'])
def test_shared_timing_limits_include_the_twenty_fourth_joint(kind):
    x=np.linspace(0,1,101) if kind!='JOINT' else np.array([0.,1.])
    q=np.zeros((len(x),24));q[:,:23]=x[:,None]*.01
    q[:,23]=3*x+.15*np.sin(4*x) if kind!='JOINT' else 3*x
    segment=dict(kind=kind,knots=x.tolist(),positions=q.tolist(),check={})
    bounds=curve_bounds(segment);assert bounds.shape==(3,24) and bounds[0,-1]>2.9
    new=plan_segment(segment);T=new['time_law']['duration_s']
    for n,cap in [(1,.45),(2,.4),(3,2.)]:
        assert np.max(abs(sample_segment(new,np.linspace(0,T,20001),n)))<=cap+1e-7
        assert np.max(abs(sample_segment(new,[0,T],n)))<1e-10
    assert np.allclose(sample_segment(new,[0,T]),q[[0,-1]])

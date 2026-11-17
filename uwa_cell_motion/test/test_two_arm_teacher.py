from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.two_arm_teacher import left_jacobian,pose_at,specification,box_separation,point_box_distance
from uwa_cell_motion.object_transport import yaw_basis


@pytest.mark.parametrize('vector',[[0,0,0],[1e-8,-2e-8,3e-8],[.4,-.8,.3],[1.8,.2,-.1]])
def test_world_rotation_differential_matches_finite_difference(vector):
    v=np.array(vector);eps=1e-6;actual=np.empty((3,3));R=Rotation.from_rotvec(v).as_matrix()
    for k in range(3):
        step=np.zeros(3);step[k]=eps
        a=Rotation.from_rotvec(v+step).as_matrix();b=Rotation.from_rotvec(v-step).as_matrix()
        actual[:,k]=(Rotation.from_matrix(a@R.T).as_rotvec()-Rotation.from_matrix(b@R.T).as_rotvec())/(2*eps)
    assert np.allclose(left_jacobian(v),actual,atol=1e-8)


def test_corrections_preserve_start_and_goal_and_rotate_about_centre():
    initial=np.eye(4);initial[:3,3]=[.2,-.1,1.1];initial[:3,:3]=Rotation.from_euler('xyz',[.1,.2,.3]).as_matrix()
    task=specification('endpoint', [.1,.2,.05],[30,-40,80], [.2,-.05,.03],[20,10,30])
    controls=np.random.default_rng(0).normal(0,.1,(6,6))
    assert np.allclose(pose_at(initial,task,0,controls),initial)
    end=pose_at(initial,task,1,controls)
    assert np.allclose(end[:3,3],initial[:3,3]+task['goal_m'])
    assert np.allclose(end[:3,:3],Rotation.from_rotvec(np.deg2rad(task['goal_rotation_vector_deg'])).as_matrix()@initial[:3,:3])
    controls[:,:3]=0
    assert np.allclose(pose_at(initial,task,.4,controls)[:3,3],pose_at(initial,task,.4,np.zeros((6,6)))[:3,3])


def test_noncommuting_correction_parameter_jacobian():
    initial=np.eye(4);task=specification('test',rotation_deg=[40,-60,50])
    controls=np.random.default_rng(12).normal(0,.15,(6,6));s=.43;B=yaw_basis(s)
    base=pose_at(initial,task,s,controls);eps=1e-6
    for knot,axis in [(0,3),(2,4),(4,5),(5,0)]:
        plus=controls.copy();minus=controls.copy();plus[knot,axis]+=eps;minus[knot,axis]-=eps
        a=pose_at(initial,task,s,plus);b=pose_at(initial,task,s,minus)
        fd=np.r_[(a[:3,3]-b[:3,3])/(2*eps),
                  (Rotation.from_matrix(a[:3,:3]@base[:3,:3].T).as_rotvec()-Rotation.from_matrix(b[:3,:3]@base[:3,:3].T).as_rotvec())/(2*eps)]
        G=np.eye(6);G[3:,3:]=left_jacobian((B@controls)[3:])
        assert np.allclose(fd,B[knot]*G[:,axis],atol=1e-8)


def test_box_separation_overlap_and_rotated_corner():
    a=np.eye(4);b=np.eye(4);half=np.array([.2,.1,.05])
    b[0,3]=.5
    assert box_separation(a,half,b,half)==pytest.approx(.1)
    b[0,3]=.3
    assert box_separation(a,half,b,half)<0
    b[0,3]=.4
    assert box_separation(a,half,b,half)==pytest.approx(0)
    b[0,3]=.35;b[:3,:3]=Rotation.from_euler('z',90,degrees=True).as_matrix()
    assert box_separation(a,half,b,half)==pytest.approx(.05)


def test_bad_task_or_controls_rejected():
    with pytest.raises(ValueError):specification('bad',goal_m=[np.nan,0,0])
    with pytest.raises(ValueError):pose_at(np.eye(4),specification('test'),.5,np.zeros(6))


def test_signed_box_distance_gradient_inside_and_outside():
    points=np.array([[.5,.3,.2],[.08,.01,.01],[-.5,-.3,.2]])
    half=np.array([.2,.1,.05]);d,n=point_box_distance(points,half);eps=1e-6
    assert d[0]>0 and d[1]<0 and d[2]>0
    for axis in range(3):
        step=np.zeros(3);step[axis]=eps
        actual=(point_box_distance(points+step,half)[0]-point_box_distance(points-step,half)[0])/(2*eps)
        assert np.allclose(actual,n[:,axis],atol=1e-8)

"""Nontrivial pose directions, outliers, optical-flow tracking and invalidation."""
import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from uwa_cell_tracking.core import estimate,DynamicTracker

K=np.array([[650.,0,320],[0,650,240],[0,0,1]])
D=np.zeros(5)


def fixture():
    rng=np.random.default_rng(77)
    points=rng.uniform([-.17,-.13,-.05],[.17,.13,.05],(90,3))
    pose=np.eye(4);pose[:3,:3]=Rotation.from_euler('xyz',[.1,-.2,.04]).as_matrix();pose[:3,3]=[.03,-.01,.85]
    pixels=cv2.projectPoints(points,cv2.Rodrigues(pose[:3,:3])[0],pose[:3,3],K,D)[0].reshape(-1,2)
    return points,pose,pixels


def test_recover_metric_camera_object_with_noise_and_outliers():
    points,truth,pixels=fixture();rng=np.random.default_rng(9)
    pixels+=rng.normal(0,.15,pixels.shape);pixels[:15]=rng.uniform([0,0],[640,480],(15,2))
    result=estimate(points,pixels,K,D)
    assert result.status=='VALID';assert result.inliers>=65
    delta=np.linalg.inv(truth)@result.T_camera_object
    assert np.linalg.norm(delta[:3,3])<.001
    assert Rotation.from_matrix(delta[:3,:3]).magnitude()<np.deg2rad(.5)


def test_no_features_and_collinear_geometry_never_produce_a_pose():
    points,truth,pixels=fixture()
    assert estimate(points[:7],pixels[:7],K,D).T_camera_object is None
    line=np.c_[np.linspace(-.2,.2,30),np.zeros((30,2))]
    pix=cv2.projectPoints(line,np.zeros(3),np.array([0.,0.,1.]),K,D)[0].reshape(-1,2)
    result=estimate(line,pix,K,D);assert result.status!='VALID'


def draw(points,pose):
    pixels=cv2.projectPoints(points,cv2.Rodrigues(pose[:3,:3])[0],pose[:3,3],K,D)[0].reshape(-1,2)
    image=np.zeros((480,640,3),np.uint8)
    for i,(x,y) in enumerate(pixels):
        cv2.circle(image,(round(x),round(y)),3,(90+(i*43)%160,)*3,-1)
    return image,pixels


def test_dynamic_6d_small_motion_then_occlusion_and_time_reversal():
    cv2.setNumThreads(1);points,truth,_=fixture();image,pixels=draw(points,truth)
    initial=estimate(points,pixels,K,D);assert initial.status=='VALID'
    tracker=DynamicTracker();tracker.initialize(image,initial,K,D,1.)
    moved=truth.copy();moved[:3,3]+=[.002,-.001,.001]
    moved[:3,:3]=Rotation.from_rotvec([.003,-.002,.002]).as_matrix()@moved[:3,:3]
    next_image,_=draw(points,moved);tracked=tracker.update(next_image,K,D,1.04)
    assert tracked.status=='VALID';delta=np.linalg.inv(moved)@tracked.T_camera_object
    assert np.linalg.norm(delta[:3,3])<.005
    assert Rotation.from_matrix(delta[:3,:3]).magnitude()<np.deg2rad(2)
    missing=tracker.update(np.zeros_like(image),K,D,1.08)
    assert missing.status=='LOST' and missing.T_camera_object is None
    tracker.initialize(image,initial,K,D,2.)
    assert tracker.update(image,K,D,1.).status=='LOST'
    tracker.initialize(image,initial,K,D,2.)
    assert tracker.update(image,K,D,3.).status=='LOST'


def test_camera_model_change_invalidates_tracking():
    points,pose,_=fixture();image,pixels=draw(points,pose);result=estimate(points,pixels,K,D)
    tracker=DynamicTracker();tracker.initialize(image,result,K,D,1.)
    other=K.copy();other[0,0]+=10
    result=tracker.update(image,other,D,1.04)
    assert result.status=='LOST' and result.T_camera_object is None

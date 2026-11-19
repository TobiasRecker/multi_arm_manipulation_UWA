"""Reference pixels must be matched anew; an empty current image has no pose."""
import sys
from pathlib import Path
import cv2,numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from register_carton_from_oak import track_photo_points


def fixture():
    points=np.array([[x,y,0.]for y in np.linspace(-.12,.12,7)for x in np.linspace(-.16,.16,9)])
    K=np.array([[650.,0.,320.],[0.,650.,240.],[0.,0.,1.]]);D=np.zeros(5);R=Rotation.from_euler('xyz',[.35,-.2,.1]).as_rotvec();T=np.array([0.,0.,.8]);pix=cv2.projectPoints(points,R,T,K,D)[0].reshape(-1,2)
    image=np.zeros((480,640,3),np.uint8);rng=np.random.default_rng(74)
    for x,y in np.rint(pix).astype(int):image[y-5:y+6,x-5:x+6]=rng.integers(20,240,(11,11,3),dtype=np.uint8)
    return image,points,pix,K,D


def test_recomputed_pixels_follow_current_image_motion():
    image,points,pix,K,D=fixture();current=cv2.warpAffine(image,np.float32([[1,0,3],[0,1,-2]]),(640,480))
    r,detail=track_photo_points(image,current,points,pix,[0,0,640,480],640,K,D,25)
    assert r.status=='VALID' and r.inliers>=40
    old=cv2.projectPoints(r.points,Rotation.from_euler('xyz',[.35,-.2,.1]).as_rotvec(),np.array([0.,0.,.8]),K,D)[0].reshape(-1,2)
    np.testing.assert_allclose(np.median(r.pixels-old,axis=0),[3,-2],atol=.2)


def test_old_pose_is_not_returned_without_current_features():
    image,points,pix,K,D=fixture();r,_=track_photo_points(image,np.zeros_like(image),points,pix,[0,0,640,480],640,K,D,25)
    assert r.status!='VALID' and r.T_camera_object is None

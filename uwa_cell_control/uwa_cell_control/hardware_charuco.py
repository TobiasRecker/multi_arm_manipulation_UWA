"""First real ChArUco view planning and intrinsic-free image observations.

Nominal optical mounting is used only to design motion, never as a fitted
extrinsic or as ground truth for choosing an image pose solution.
"""
from itertools import product

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from uwa_cell_gazebo.configuration import joint_names
from uwa_cell_gazebo.charuco import make_board
from uwa_cell_gazebo.charuco_views import Chain,desired_camera_pose
from .parking import plan_parking


def first_view(model,layout,rid,start,velocity=.05,acceleration=.10):
    names=joint_names(rid);q0=np.array([start[j] for j in names])
    table=layout['robots'][rid]['table']
    world_table=Chain(model.description,'world',table+'_table_top').forward({})
    target=world_table@desired_camera_pose(layout,rid)
    camera=Chain(model.description,'world',rid+'_wrist_camera_optical_frame')
    bounds=np.array([model.bounds[j] for j in names]).T
    def residual(q):
        actual=camera.forward(dict(zip(names,q)))
        return np.r_[actual[:3,3]-target[:3,3],
            .2*Rotation.from_matrix(actual[:3,:3]@target[:3,:3].T).as_rotvec()]
    seeds=[q0,np.array(layout['robots'][rid]['initial_positions'])]
    for pan,elbow in product((q0[0],q0[0]+np.pi/2,q0[0]-np.pi/2),(1.7,-1.7)):
        seeds.append(np.array([pan,-1.4,elbow,-1.5,q0[4],q0[5]]))
    candidates=[]
    for seed in seeds:
        fit=least_squares(residual,np.clip(seed,bounds[0]+1e-6,bounds[1]-1e-6),bounds=bounds,
                          max_nfev=220,ftol=1e-10,xtol=1e-10,gtol=1e-10)
        if np.linalg.norm(residual(fit.x))>1e-5:continue
        # Keep the nearest equivalent within native limits; never normalize blindly.
        q=fit.x.copy()
        for i in range(6):
            variants=[q[i]+k*2*np.pi for k in (-1,0,1) if bounds[0,i]<=q[i]+k*2*np.pi<=bounds[1,i]]
            q[i]=min(variants,key=lambda value:abs(value-q0[i]))
        try:path=plan_parking(model,layout,rid,start,target=q,velocity=velocity,acceleration=acceleration)
        except ValueError:continue
        path.update(purpose='first ChArUco view',nominal_camera_target_world=target.tolist(),
                    nominal_optics_used_for='motion design only; no real intrinsic/extrinsic calibration assumed')
        candidates.append(path)
    if not candidates:raise ValueError('No full-cell checked direct path to the first board view')
    return min(candidates,key=lambda p:p['duration'])


def observe(image,config,table):
    """Detect metric corner correspondences without assuming any camera matrix."""
    board=make_board(config,table)
    params=cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod=cv2.aruco.CORNER_REFINE_SUBPIX
    detector=cv2.aruco.CharucoDetector(board,cv2.aruco.CharucoParameters(),params)
    corners,ids,marker_corners,marker_ids=detector.detectBoard(image)
    annotated=image.copy()
    if marker_ids is not None:cv2.aruco.drawDetectedMarkers(annotated,marker_corners,marker_ids)
    result={'marker_ids':[] if marker_ids is None else marker_ids.ravel().tolist(),
            'corners':0,'object_points':[],'image_points':[],'corner_ids':[],
            'image_size':[image.shape[1],image.shape[0]],'annotated':annotated}
    if ids is None:return result
    cv2.aruco.drawDetectedCornersCharuco(annotated,corners,ids)
    if board.checkCharucoCornersCollinear(ids):return result
    objects,pixels=board.matchImagePoints(corners,ids)
    result.update(corners=len(ids),object_points=objects.reshape(-1,3).astype(float).tolist(),
                  image_points=pixels.reshape(-1,2).astype(float).tolist(),corner_ids=ids.ravel().tolist())
    return result


def calibrate_intrinsics(records,*,focus,image_size):
    """Fit only pre-labelled training views; validation corners never fit K/D."""
    train=[r for r in records if r['role']=='fit'];validation=[r for r in records if r['role']=='validation']
    if len(train)<20 or len(validation)<6:raise ValueError('Need >=20 fitting and >=6 independent validation views')
    if len({r['pixel_sha256'] for r in records})!=len(records):raise ValueError('Repeated image payloads do not count as new views')
    for r in records:
        if r['camera_settings']['focusAuto'] or r['camera_settings']['focus']!=focus:
            raise ValueError('Focus changed; do not mix intrinsic profiles')
        if r['image_size']!=list(image_size) or r['corners']<12:
            raise ValueError('Image size changed or insufficient board corners')
        objects=np.asarray(r['object_points']);pixels=np.asarray(r['image_points'])
        if objects.shape!=(r['corners'],3) or pixels.shape!=(r['corners'],2) or not np.isfinite(objects).all() or not np.isfinite(pixels).all():
            raise ValueError('Invalid corner correspondence data')
    objects=[np.asarray(r['object_points'],np.float32) for r in train]
    pixels=[np.asarray(r['image_points'],np.float32) for r in train]
    rms,k,d,rvecs,tvecs,std_intrinsics,_,per_view=cv2.calibrateCameraExtended(
        objects,pixels,tuple(image_size),None,None)
    if not np.isfinite(k).all() or not np.isfinite(d).all() or not 0<rms<1:
        raise ValueError('Intrinsic fit is non-finite or exceeds 1px RMS')
    width,height=image_size
    if not (.2*width<k[0,0]<5*width and .2*height<k[1,1]<7*height and
            0<k[0,2]<width and 0<k[1,2]<height):
        raise ValueError('Intrinsic solution outside plausible sensor geometry')
    fx_std,fy_std=std_intrinsics.ravel()[:2]
    if not np.isfinite(std_intrinsics).all() or max(fx_std/k[0,0],fy_std/k[1,1])>.05:
        raise ValueError('Weak intrinsic observability: focal uncertainty exceeds 5%; capture more diverse views')
    normals=np.array([cv2.Rodrigues(v)[0][:,2] for v in rvecs])
    if np.max(np.arccos(np.clip(normals@normals.T,-1,1)))<np.radians(20):
        raise ValueError('Insufficient board tilt diversity for intrinsics')
    errors=[]
    for r in validation:
        o=np.asarray(r['object_points'],np.float32);p=np.asarray(r['image_points'],np.float32)
        ok,rv,tv=cv2.solvePnP(o,p,k,d)
        if not ok:raise ValueError('Validation board pose could not be estimated')
        projected=cv2.projectPoints(o,rv,tv,k,d)[0].reshape(-1,2)
        errors.append(float(np.sqrt(np.mean(np.sum((projected-p)**2,axis=1)))))
    if max(errors)>1.5 or np.median(errors)>1.:
        raise ValueError('Independent intrinsic validation exceeded error limits')
    return {'schema_version':1,'passed':True,'camera_matrix':k.tolist(),'distortion':d.ravel().tolist(),
            'image_size':list(image_size),'focus':focus,'focusAuto':False,'fit_count':len(train),
            'validation_count':len(validation),'fit_rms_px':float(rms),'std_intrinsics':std_intrinsics.ravel().tolist(),
            'validation_rms_px':errors,'source':'real ChArUco corner calibration; no nominal K/D used'}

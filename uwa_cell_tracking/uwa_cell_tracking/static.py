"""Slow stationary registration: independent frames, consensus, robust pixel fit."""
import hashlib
import time
import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from .core import PoseResult


def static_pose(estimator,frames,K,D,*,minimum_frames=3):
    started=time.perf_counter();frames=list(frames)
    if len(frames)<minimum_frames:return PoseResult('LOST',reason='Not enough static frames')
    hashes=[hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest() for image in frames]
    if len(set(hashes))<minimum_frames:return PoseResult('LOST',reason='Static burst contains repeated images')
    poses=[estimator.register(image,K,D) for image in frames]
    if any(p.status!='VALID' for p in poses):
        return PoseResult('LOST',reason='Static burst has failed/ambiguous registration')
    reference=poses[0].T_camera_object
    for pose in poses[1:]:
        delta=np.linalg.inv(reference)@pose.T_camera_object
        if (np.linalg.norm(delta[:3,3])>.02 or Rotation.from_matrix(delta[:3,:3]).magnitude()>np.deg2rad(3)):
            return PoseResult('UNSTABLE',reason='Camera/object pose inconsistent across static burst')
    points=np.concatenate([p.points for p in poses]);pixels=np.concatenate([p.pixels for p in poses])
    initial=np.r_[cv2.Rodrigues(reference[:3,:3])[0].ravel(),reference[:3,3]]
    def residual(value):
        return (cv2.projectPoints(points,value[:3],value[3:],K,D)[0].reshape(-1,2)-pixels).ravel()
    fit=least_squares(residual,initial,loss='soft_l1',f_scale=2.,max_nfev=80)
    if not fit.success:return PoseResult('LOST',reason='Static robust refinement failed')
    T=np.eye(4);T[:3,:3]=cv2.Rodrigues(fit.x[:3])[0];T[:3,3]=fit.x[3:]
    rms=float(np.sqrt(np.mean(residual(fit.x).reshape(-1,2)**2)*2))
    if rms>max(p.rms_px for p in poses)+2:
        return PoseResult('UNSTABLE',reason='Static residual increased excessively')
    return PoseResult('VALID',T,poses[-1].points,poses[-1].pixels, sum(p.inliers for p in poses),rms,
        (time.perf_counter()-started)*1000,'Static camera/object assumption; repeatability is not absolute accuracy')

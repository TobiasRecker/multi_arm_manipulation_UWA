"""CPU reference backend: global texture/PnP registration and LK/PnP tracking.

Not FoundationPose. No depth/world priors, hardware clients or command APIs.
"""
from dataclasses import dataclass
import time
import json
from pathlib import Path
from .model import file_sha
import cv2
import numpy as np


@dataclass
class PoseResult:
    status: str
    T_camera_object: object=None
    points: object=None
    pixels: object=None
    inliers: int=0
    rms_px: float=float('inf')
    processing_ms: float=0.
    reason: str=''
    source_stamp: float=0.


def optics(K,D):
    K=np.asarray(K,float);D=np.asarray(D,float)
    if (K.shape!=(3,3) or not np.isfinite(K).all() or not np.isfinite(D).all() or
            min(K[0,0],K[1,1])<=0 or not np.allclose(K[2],[0,0,1])):raise ValueError('Invalid camera intrinsics')
    return K,D


def estimate(points,pixels,K,D, *, threshold=4.,min_inliers=24):
    points=np.asarray(points,np.float64);pixels=np.asarray(pixels,np.float64)
    if len(points)<min_inliers:return PoseResult('LOST',reason='Too few model correspondences')
    if (points.shape!=(len(pixels),3) or pixels.shape!=(len(points),2) or
            not np.isfinite(points).all() or not np.isfinite(pixels).all()):
        return PoseResult('LOST',reason='Invalid correspondences')
    if np.linalg.matrix_rank(points-points.mean(axis=0))<2:
        return PoseResult('LOST',reason='Degenerate model features')
    cv2.setRNGSeed(1749)
    ok,rv,tv,index=cv2.solvePnPRansac(points,pixels,K,D,iterationsCount=1500,
        reprojectionError=threshold,confidence=.999,flags=cv2.SOLVEPNP_EPNP)
    if not ok or index is None or len(index)<min_inliers:return PoseResult('LOST',reason='PnP consensus insufficient')
    index=index.ravel();obj=points[index];pix=pixels[index]
    # Planar patches can produce two solutions: score both positive-depth IPPE
    # candidates, and reject unresolved ambiguities rather than choosing a prior.
    singular=np.linalg.svd(obj-obj.mean(axis=0),compute_uv=False)
    if singular[1]<.005:return PoseResult('LOST',reason='Insufficient spatial feature spread')
    planar=singular[2]<1e-5
    candidates=[(rv,tv)]
    if planar:
        plane=cv2.solvePnPGeneric(obj,pix,K,D,flags=cv2.SOLVEPNP_IPPE)
        if plane[0]:candidates=list(zip(plane[1],plane[2]))
    scored=[]
    for rv,tv in candidates:
        rv,tv=cv2.solvePnPRefineLM(obj,pix,K,D,rv,tv)
        R=cv2.Rodrigues(rv)[0];local=obj@R.T+tv.ravel()
        if np.min(local[:,2])<=.02:continue
        delta=cv2.projectPoints(obj,rv,tv,K,D)[0].reshape(-1,2)-pix
        rms=float(np.sqrt(np.mean(np.sum(delta**2,axis=1))))
        T=np.eye(4);T[:3,:3]=R;T[:3,3]=tv.ravel();scored.append((rms,T))
    if not scored:return PoseResult('LOST',reason='No positive-depth solution')
    scored.sort(key=lambda x:x[0]);rms,T=scored[0]
    if len(scored)>1 and scored[1][0]<rms*1.1+.15:
        second=scored[1][1]
        angle=np.arccos(np.clip((np.trace(T[:3,:3].T@second[:3,:3])-1)/2,-1,1))
        if angle>.08:return PoseResult('AMBIGUOUS',reason='Two similar planar pose hypotheses')
    if rms>threshold:return PoseResult('LOST',reason='Excessive reprojection error')
    return PoseResult('VALID',T,obj,pix,len(obj),rms,reason='Planar observations' if planar else 'Multi-plane observations')


class TexturePose:
    def __init__(self,reference,*,width=1600):
        reference=Path(reference);meta=json.loads(reference.with_suffix('.json').read_text())
        if file_sha(reference)!=meta['reference_sha256']:raise ValueError('Tracker reference hash mismatch')
        self.metadata=meta
        data=np.load(reference,allow_pickle=False);self.points=data['points'];self.descriptors=data['descriptors']
        self.surfaces=data['surfaces']
        self.width=width;self.detector=cv2.SIFT_create(nfeatures=4500)
        self.matcher=cv2.BFMatcher(cv2.NORM_L2)

    def register(self,image,K,D,stamp=0.):
        started=time.perf_counter();K,D=optics(K,D)
        scale=min(1.,self.width/image.shape[1]);small=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
        gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY) if small.ndim==3 else small
        kp,desc=self.detector.detectAndCompute(gray,None)
        if desc is None:result=PoseResult('LOST',reason='No image features')
        else:
            matches=self.matcher.knnMatch(desc,self.descriptors,k=2)
            chosen={}
            for pair in matches:
                if len(pair)!=2:continue
                a,b=pair
                if a.distance>=.73*b.distance:continue
                old=chosen.get(a.trainIdx)
                if old is None or a.distance<old.distance:chosen[a.trainIdx]=a
            matched=list(chosen.values())
            points=np.array([self.points[a.trainIdx] for a in matched])
            pixels=np.array([kp[a.queryIdx].pt for a in matched])/scale
            surfaces=np.array([self.surfaces[a.trainIdx] for a in matched])
            threshold=4./scale;candidates=[]
            # A few wrong matches on another panel can tilt a mostly planar
            # EPNP solution substantially despite a small residual. Generate
            # per-surface hypotheses as well, then use a robust global score.
            groups=[np.ones(len(points),bool)]+[surfaces==s for s in np.unique(surfaces)]
            for group in groups:
                candidate=estimate(points[group],pixels[group],K,D,threshold=threshold)
                if candidate.status!='VALID':continue
                pose=candidate.T_camera_object
                projected=cv2.projectPoints(points,cv2.Rodrigues(pose[:3,:3])[0],pose[:3,3],K,D)[0].reshape(-1,2)
                errors=np.linalg.norm(projected-pixels,axis=1)
                score=float(np.maximum(0,1-(errors/threshold)**2).sum())
                candidates.append((score,candidate))
            if not candidates:result=PoseResult('LOST',reason='No reliable global/panel pose hypothesis')
            else:
                candidates.sort(key=lambda x:x[0],reverse=True);score,result=candidates[0]
                for other_score,other in candidates[1:]:
                    if other_score<score*.90:continue
                    delta=np.linalg.inv(result.T_camera_object)@other.T_camera_object
                    angle=np.arccos(np.clip((np.trace(delta[:3,:3])-1)/2,-1,1))
                    if np.linalg.norm(delta[:3,3])>.02 or angle>.1:
                        result=PoseResult('AMBIGUOUS',reason='Similar scores for distinct object-pose hypotheses');break
        result.source_stamp=float(stamp);result.processing_ms=(time.perf_counter()-started)*1000
        return result


class DynamicTracker:
    """Tracks only consecutive, fresh images; loss never publishes an old pose."""
    def __init__(self,*,max_gap_s=.5,width=960):
        self.max_gap_s=max_gap_s;self.width=width;self.reset()

    def reset(self):
        self.gray=None;self.result=None;self.K=None;self.D=None;self.stamp=None

    def initialize(self,image,result,K,D,stamp):
        if result.status!='VALID':self.reset();return
        if not np.isfinite(stamp):raise ValueError('Nonfinite frame time')
        K,D=optics(K,D);scale=min(1.,self.width/image.shape[1])
        small=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
        self.gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY) if small.ndim==3 else small
        self.result=result;self.scale=scale;self.K=K.copy();self.D=D.copy();self.stamp=float(stamp)
        self.shape=image.shape

    def update(self,image,K,D,stamp):
        started=time.perf_counter();K,D=optics(K,D);stamp=float(stamp)
        if self.gray is None:return PoseResult('LOST',reason='Registration required',source_stamp=stamp)
        if (not np.isfinite(stamp) or stamp<=self.stamp or stamp-self.stamp>self.max_gap_s or
                image.shape!=self.shape or not np.array_equal(K,self.K) or not np.array_equal(D,self.D)):
            self.reset();return PoseResult('LOST',reason='Stale/reversed time or camera model changed',source_stamp=stamp)
        small=cv2.resize(image,None,fx=self.scale,fy=self.scale,interpolation=cv2.INTER_AREA)
        gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY) if small.ndim==3 else small
        old=(self.result.pixels*self.scale).astype(np.float32).reshape(-1,1,2)
        kwargs=dict(winSize=(25,25),maxLevel=3,criteria=(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,30,.01))
        new,good,_=cv2.calcOpticalFlowPyrLK(self.gray,gray,old,None,**kwargs)
        back,reverse,_=cv2.calcOpticalFlowPyrLK(gray,self.gray,new,None,**kwargs)
        error=np.linalg.norm(back.reshape(-1,2)-old.reshape(-1,2),axis=1)
        keep=(good.ravel()!=0)&(reverse.ravel()!=0)&(error<.8)
        result=estimate(self.result.points[keep],new.reshape(-1,2)[keep]/self.scale,K,D,threshold=3./self.scale,min_inliers=16)
        result.source_stamp=stamp;result.processing_ms=(time.perf_counter()-started)*1000
        if result.status=='VALID':self.result=result;self.gray=gray;self.stamp=stamp
        else:self.reset()
        return result

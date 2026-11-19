#!/usr/bin/env python3
"""Current photo -> supported carton pose in the fixed right-board reference.

Offline image registration only. Keeps adopted base bindings and global camera
profiles unchanged. Records the support prior and every accepted/rejected fit.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import argparse,hashlib,json,sys
from pathlib import Path
import cv2,numpy as np,yaml
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'uwa_cell_tasks'))
from uwa_cell_tracking.core import TexturePose,estimate,PoseResult
from uwa_cell_gazebo.charuco import make_board
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_tasks.hardware_registration import per_arm_camera_binding,validate_per_arm_binding
cv2.setNumThreads(2)


def validate_visible_board_projection(obj, uv, Tcb, K, D):
    """Validate an existing camera reference; never fit new extrinsics here."""
    obj=np.asarray(obj,float);uv=np.asarray(uv,float)
    if len(obj)<16 or len(obj)%4 or np.min(np.ptp(obj[:,:2],axis=0))<.04:
        raise ValueError('Reference check needs four spatially distributed visible markers')
    projected=cv2.projectPoints(obj,cv2.Rodrigues(Tcb[:3,:3])[0],Tcb[:3,3],K,D)[0].reshape(-1,2)
    error=np.linalg.norm(projected-uv,axis=1);rms=float(np.sqrt(np.mean(error**2)));maximum=float(error.max())
    if not np.isfinite(error).all() or rms>=2. or maximum>=4.:
        raise ValueError(f'Previous camera reference disagrees with visible board: RMS{rms:.3f}px/max{maximum:.3f}px')
    return dict(reference_projection_rms_px=rms,max_reference_projection_px=maximum,
                board_span_m=np.ptp(obj,axis=0).tolist())


def planar_texture_candidates(tracker,image,K,D,stretches):
    """Affine feature views; every pose is checked in the original pixels."""
    scale=min(1.,tracker.width/image.shape[1]);results=[]
    for stretch in stretches:
        small=cv2.resize(image,None,fx=scale,fy=scale*stretch,interpolation=cv2.INTER_LINEAR)
        keypoints,descriptors=tracker.detector.detectAndCompute(cv2.cvtColor(small,cv2.COLOR_BGR2GRAY),None)
        if descriptors is None:continue
        for surface in np.unique(tracker.surfaces):
            mask=tracker.surfaces==surface;model=tracker.points[mask];chosen={}
            for pair in tracker.matcher.knnMatch(descriptors,tracker.descriptors[mask],k=2):
                if len(pair)!=2:continue
                match,second=pair
                if match.distance>=.73*second.distance:continue
                if match.trainIdx not in chosen or match.distance<chosen[match.trainIdx].distance:chosen[match.trainIdx]=match
            matches=list(chosen.values())
            if len(matches)<24:continue
            points=np.asarray([model[m.trainIdx]for m in matches]);pixels=np.asarray([keypoints[m.queryIdx].pt for m in matches])/np.array([scale,scale*stretch])
            result=estimate(points,pixels,K,D,threshold=4./scale)
            results.append((result,dict(surface=int(surface),vertical_feature_stretch=stretch,feature_interpolation="linear")))
    return results or [(PoseResult('LOST',reason='No planar texture correspondences'),{})]


def register(a):
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);photo=json.loads(a.metadata.read_text());intr=json.loads(a.intrinsics.read_text());intr=intr.get('intrinsics',intr);K=np.array(intr['K']);D=np.array(intr['D']);image=cv2.imread(str(a.image));focus=photo['standard']['lens_position']
    if image is None:raise ValueError('Native image unavailable')
    if not photo.get('success') or photo.get('mode')!='standard' or focus!=intr['focus'] or list(image.shape[1::-1])!=intr['image_size']:raise ValueError('Native photo/calibration mode, focus or dimensions differ')
    board=make_board(yaml.safe_load((REPO/'uwa_cell_description/config/cell_layout.yaml').read_text())['charuco'],'right');known={int(i):np.array(p)for i,p in zip(board.getIds().ravel(),board.getObjPoints())};params=cv2.aruco.DetectorParameters();params.cornerRefinementMethod=cv2.aruco.CORNER_REFINE_SUBPIX;corners,ids,_=cv2.aruco.ArucoDetector(board.getDictionary(),params).detectMarkers(image);obj=[];uv=[]
    for pixels,mid in zip(corners,[]if ids is None else ids.ravel()):
        if int(mid)in known:obj.extend(known[int(mid)]);uv.extend(pixels.reshape(4,2))
    obj=np.array(obj,dtype=float);uv=np.array(uv,dtype=float)
    description=a.description.read_text();Twb=Chain(description,'world','right_charuco').forward({});Twt=Chain(description,'world','right_table_top').forward({})
    board_mode='current_full_board_fit';reference_check={}
    if len(obj)<48:
        reference_path=getattr(a,'camera_reference_pose',None)
        if reference_path is None:raise ValueError('Fixed right board has insufficient visible marker corners')
        reference=json.loads(reference_path.read_text());proof=json.loads((reference_path.parent/'registration.json').read_text())
        if (reference.get('focus')!=focus or not proof.get('success') or proof.get('board_corners',0)<48 or
            proof.get('board_camera_mode','current_full_board_fit')!='current_full_board_fit' or proof.get('board_rms_px',float('inf'))>=2.):
            raise ValueError('A complete successful same-focus board registration is required; reference chains are not accepted')
        validate_per_arm_binding(description,reference)
        Twc=Chain(description,'world','right_front_base_link').forward({})@np.asarray(reference['T_base_camera_by_arm']['right_front'])
        reference_check=validate_visible_board_projection(obj,uv,np.linalg.inv(Twc)@Twb,K,D)
        brms=reference_check['reference_projection_rms_px'];board_mode='reference_validated_against_visible_corners'
    else:
        ok,rv,tv=cv2.solvePnP(obj,uv,K,D);Tcb=np.eye(4);Tcb[:3,:3]=cv2.Rodrigues(rv)[0];Tcb[:3,3]=tv.ravel()
        res=cv2.projectPoints(obj,rv,tv,K,D)[0].reshape(-1,2)-uv;brms=float(np.sqrt(np.mean(np.sum(res**2,axis=1))))
        if not ok or brms>=2.:raise ValueError('Fixed right-board reprojection failed')
        Twc=Twb@np.linalg.inv(Tcb)
    Tcw=np.linalg.inv(Twc);attempts=[];fits=[]
    for roi,width in [(a.roi,1600),(a.face_roi,1200),(a.face_roi,1600)]:
        x0,y0,x1,y1=roi
        if not 0<=x0<x1<=image.shape[1] or not 0<=y0<y1<=image.shape[0]:raise ValueError('Search ROI outside native image')
        k=K.copy();k[0,2]-=x0;k[1,2]-=y0;tracker=TexturePose(a.reference,width=width)
        candidates=(planar_texture_candidates(tracker,image[y0:y1,x0:x1],k,D,[1.,1.4,1.5,1.6])
                    if getattr(a,'planar_texture',False)else [(tracker.register(image[y0:y1,x0:x1],k,D),{})])
        for r,method in candidates:
            item=dict(roi=list(roi),width=width,status=r.status,inliers=r.inliers,rms_px=None if not np.isfinite(r.rms_px)else r.rms_px,reason=r.reason,**method);attempts.append(item)
            if r.status!='VALID':continue
            raw=Twc@r.T_camera_object;initial=np.linalg.inv(Twt)@raw;v0=[initial[0,3],initial[1,3],np.arctan2(initial[1,0],initial[0,0])];points=r.points;pixels=r.pixels+[x0,y0]
            def world(v):
                T=np.eye(4);T[:3,:3]=Rotation.from_euler('z',v[2]).as_matrix();T[:3,3]=[v[0],v[1],0.];return Twt@T
            def fun(v):
                T=Tcw@world(v);return (cv2.projectPoints(points,cv2.Rodrigues(T[:3,:3])[0],T[:3,3],K,D)[0].reshape(-1,2)-pixels).ravel()
            fit=least_squares(fun,v0,loss='soft_l1',f_scale=3.,xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=200);rms=float(np.sqrt(np.mean(np.sum(fun(fit.x).reshape(-1,2)**2,axis=1))));threshold=4./min(1.,width/(x1-x0));item.update(support_fit_rms_px=rms,registration_threshold_px=threshold,support_fit_pass=rms<=threshold)
            if item['support_fit_pass']:fits.append(world(fit.x))
    report=dict(success=False,device_commands=[],board_corners=len(obj),board_rms_px=brms,board_camera_mode=board_mode,camera_reference_pose=str(getattr(a,'camera_reference_pose',None)),reference_check=reference_check,attempts=attempts,support_prior='Carton visibly upright/supported on fixed right table; bottom at table plane; x/y/yaw fitted to current image',absolute_accuracy_validated=False,manipulation_approved=False)
    if len(fits)<2:report['error']='Fewer than two valid supported image-pose hypotheses'
    else:
        T=fits[0];spread=max(np.linalg.norm(t[:3,3]-T[:3,3])for t in fits);angular=max(np.rad2deg(Rotation.from_matrix(t[:3,:3]@T[:3,:3].T).magnitude())for t in fits);report.update(position_spread_m=float(spread),angle_spread_deg=float(angular))
        if spread>=.01 or angular>=2.:report['error']='Supported image hypotheses disagree'
        else:
            registration=dict(transforms={arm:dict(parent_frame=arm+'_base_link',child_frame='oak4_rgb_optical_frame',T_parent_child=(np.linalg.inv(Chain(description,'world',arm+'_base_link').forward({}))@Twc).tolist())for arm in ['right_front','right_rear']});binding=per_arm_camera_binding(description,registration,Tcw@T);validate_per_arm_binding(description,binding);binding.update(source=('Current fixed right board + adopted base bindings'if board_mode=='current_full_board_fit'else 'Previous complete board camera registration validated on current visible markers; current carton image fit'),focus=focus,support_prior=report['support_prior'],source_inputs={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.image,a.metadata,a.intrinsics,a.description,a.reference,Path(__file__)]+([a.camera_reference_pose,a.camera_reference_pose.parent/'registration.json']if board_mode!='current_full_board_fit'else [])});(out/'object-pose.json').write_text(json.dumps(binding,indent=2)+'\n');report.update(success=True,T_world_object=T.tolist(),object_pose=str(out/'object-pose.json'))
            dims=json.loads((REPO/'uwa_cell_description/assets/carton_avocado_v1/asset.json').read_text())['dimensions_m'];L,W,H=dims;points=np.array([[x,y,z]for z in (0,H)for y in (0,W)for x in (0,L)]);co=Tcw@T;px=cv2.projectPoints(points,cv2.Rodrigues(co[:3,:3])[0],co[:3,3],K,D)[0].reshape(-1,2)
            for i,j in [(0,1),(0,2),(1,3),(2,3),(4,5),(4,6),(5,7),(6,7),(0,4),(1,5),(2,6),(3,7)]:cv2.line(image,tuple(np.rint(px[i]).astype(int)),tuple(np.rint(px[j]).astype(int)),(0,255,255),9)
            cv2.rectangle(image,(0,0),(image.shape[1],250),(0,0,0),-1);cv2.putText(image,'CURRENT SUPPORTED CARTON / IMAGE REGISTRATION ONLY',(80,165),cv2.FONT_HERSHEY_SIMPLEX,3,(255,255,255),7);cv2.imwrite(str(out/'pose-preview.jpg'),cv2.resize(image,(1600,1200)));report['preview']=str(out/'pose-preview.jpg')
    (out/'registration.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(report,indent=2));return 0 if report['success']else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['image','metadata','intrinsics','description','output']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--planar-texture',action='store_true',help='Affine feature views with per-panel planar consensus; unchanged inlier, residual and hypothesis-agreement limits')
    ap.add_argument('--camera-reference-pose',type=Path,help='Explicit complete earlier camera registration, validated against >=4 current visible markers; never reuse its object pose')
    ap.add_argument('--reference',type=Path,default=REPO.parents[1]/'setup/tracking/models/carton_avocado_v1/reference.npz');ap.add_argument('--roi',nargs=4,type=int,default=[2700,2100,4900,3700]);ap.add_argument('--face-roi',nargs=4,type=int,default=[2850,2750,4700,3520]);raise SystemExit(register(ap.parse_args()))

"""Offline CPU tracking tools; camera streams are separate opt-in ROS inputs."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from .core import TexturePose
from .model import surface_reference
from .static import static_pose


def record(result):
    return dict(status=result.status,T_camera_object=None if result.T_camera_object is None else result.T_camera_object.tolist(),
        inliers=result.inliers,reprojection_rms_px=result.rms_px if np.isfinite(result.rms_px) else None,
        processing_ms=result.processing_ms,reason=result.reason,source_stamp=result.source_stamp,
        absolute_accuracy_validated=False,manipulation_approved=False)


def annotate(image,result,K,D):
    output=image.copy()
    if result.T_camera_object is not None:
        pose=result.T_camera_object
        cv2.drawFrameAxes(output,K,D,cv2.Rodrigues(pose[:3,:3])[0],pose[:3,3],.1,3)
    width=1200;output=cv2.resize(output,(width,round(output.shape[0]*width/output.shape[1])))
    cv2.rectangle(output,(0,0),(width,90),(0,0,0),-1)
    cv2.putText(output,result.status+' / CPU TEXTURE POSE',(20,37),cv2.FONT_HERSHEY_SIMPLEX,.8,(255,255,255),2)
    cv2.putText(output,result.reason[:95],(20,73),cv2.FONT_HERSHEY_SIMPLEX,.52,(255,255,255),1)
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    build=sub.add_parser('prepare');build.add_argument('--asset',type=Path,required=True);build.add_argument('--output',type=Path,required=True)
    run=sub.add_parser('localize');run.add_argument('--reference',type=Path,required=True)
    run.add_argument('--camera',type=Path,required=True,help='JSON: K,D,image_size; native matching fixed-focus optics')
    run.add_argument('--images',type=Path,nargs='+',required=True);run.add_argument('--output',type=Path,required=True)
    run.add_argument('--single',action='store_true',help='Diagnostic single frame; static mode otherwise needs3+ fresh frames')
    args=p.parse_args();cv2.setNumThreads(2)
    if args.mode=='prepare':print(json.dumps(surface_reference(args.asset,args.output),indent=2));return
    camera=json.loads(args.camera.read_text());K=np.array(camera['K']);D=np.array(camera['D']);frames=[]
    for path in args.images:
        image=cv2.imread(str(path))
        if image is None or [image.shape[1],image.shape[0]]!=camera['image_size']:raise ValueError('Image/calibration size mismatch '+str(path))
        frames.append(image)
    estimator=TexturePose(args.reference)
    result=estimator.register(frames[0],K,D) if args.single else static_pose(estimator,frames,K,D)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'pose.json').write_text(json.dumps(record(result),indent=2)+'\n')
    cv2.imwrite(str(args.output/'pose.jpg'),annotate(frames[-1],result,K,D));print(json.dumps(record(result),indent=2))


if __name__=='__main__':main()

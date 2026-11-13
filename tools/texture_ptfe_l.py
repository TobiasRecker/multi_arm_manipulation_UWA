"""Rectify explicitly identified physical plate/profile faces for the L asset."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def textures(root):
    out=root/'reconstruction';r=json.loads((out/'assembly_result.json').read_text())
    cameras=json.loads((out/'camera_models.json').read_text());landmarks=json.loads((out/'landmarks.json').read_text())['observations']
    W,D,H=r['width_m'],r['base_plate_depth_m'],r['upright_plate_height_m']
    source=cameras['r1_right_rear'];o=landmarks['r1_right_rear']
    def points(ids):return [o['pixels'][o['ids'].index(i)] for i in ids]
    # Corners of observed planar apertures, not their occluding support edges.
    definitions={
      'base_top':dict(camera='r1_right_rear',extent=[W,D],pixels=points([0,1,2,3])),
      'upright_front':dict(camera='r1_right_rear',extent=[W,H],pixels=points([0,1,5,4])),
      'upright_back':dict(camera='r1_right_front',extent=[W-.04,H-.02],rotated=True,
          pixels=[[636,688],[756,770],[800,905],[682,813]]),
      'metal_front':dict(camera='r1_right_rear',extent=[W,.02],
          pixels=[[984,781],[482,666],[486,646],[989,762]]),
      'metal_back':dict(camera='r1_right_front',extent=[W,H+.03],rotated=True,
          pixels=[[657,866],[843,974],[781,746],[598,628]])}
    # Back aperture order X0lower, XWlower, XWupper, X0upper.
    definitions['upright_back']['pixels']=[[682,813],[800,905],[756,770],[636,688]]
    report={}
    for name,item in definitions.items():
        c=cameras[item['camera']];image=cv2.imread(c['image']);pixels=np.array(item['pixels'],float)
        if item.get('rotated'):pixels=np.array([1599,1199])-pixels
        pixels*=c['image_size'][0]/1600;K=np.array(c['K']);dist=np.array(c['D'])
        normalized=cv2.undistortPointsIter(pixels[:,None,:],K,dist,None,None,
            (cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,100,1e-10)).reshape(-1,2)
        homography=cv2.getPerspectiveTransform(np.array([[0,0],[1,0],[1,1],[0,1]],np.float32),normalized.astype(np.float32))
        nw=1600;nh=max(120,round(nw*item['extent'][1]/item['extent'][0]));uu,vv=np.meshgrid(np.linspace(0,1,nw),np.linspace(1,0,nh))
        uv=np.c_[uu.ravel(),vv.ravel(),np.ones(nw*nh)]@homography.T;xy=uv[:,:2]/uv[:,2,None]
        rays=np.c_[xy,np.ones(len(xy))]
        native=cv2.projectPoints(rays,np.zeros(3),np.zeros(3),K,dist)[0].reshape(nh,nw,2).astype(np.float32)
        texture=cv2.remap(image,native[:,:,0],native[:,:,1],cv2.INTER_LINEAR)
        cv2.imwrite(str(out/(name+'_texture.jpg')),texture)
        report[name]=dict(**item,source_image=c['image'],source_sha256=c['image_sha256'],
            raw_native_corners=pixels.tolist(),texture_size=[nw,nh],perspective_and_native_distortion_accounted=True)
    (out/'texture_sources.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    textures(p.parse_args().root.resolve())

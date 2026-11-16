#!/usr/bin/env python3
"""Offline photo assignment for a frozen visual hull; fit images only."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from uwa_cell_control.silhouette_mesh import project, sha


def texture(hull):
    hull=Path(hull);report=json.loads((hull/'reconstruction.json').read_text())
    if sha(report['source_models'])!=report['source_models_sha256']:raise ValueError('Prepared camera models changed')
    cameras=json.loads(Path(report['source_models']).read_text())
    data=np.load(hull/'mesh_board.npz');v,f=data['vertices'],data['faces']
    triangles=v[f];centres=triangles.mean(1)
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
    names=report['fit_views'];best=np.full(len(f),-1.,float);chosen=np.full(len(f),-1,int)
    uv_all=[]
    for index,name in enumerate(names):
        c=cameras[name];p,z=project(v,c,500);cp,cz=project(centres,c,500)
        h=round(c['image_size'][1]*500/c['image_size'][0]);depth=np.full((h,500),np.inf,np.float32)
        eye=np.linalg.inv(np.asarray(c['T_camera_board']))[:3,3];direction=eye-centres
        direction/=np.linalg.norm(direction,axis=1)[:,None];score=(normals*direction).sum(1)
        # Conservative depth buffer at triangle-centroid depths; tolerance is
        # explicitly a voxel discretization allowance, not physical accuracy.
        for fi in np.flatnonzero((score>0)&(z[f].min(1)>0)):
            pix=p[f[fi]];lo=np.maximum(np.floor(pix.min(0)).astype(int),[0,0]);hi=np.minimum(np.ceil(pix.max(0)).astype(int),[499,h-1])
            if np.any(hi<lo):continue
            mask=np.zeros((hi[1]-lo[1]+1,hi[0]-lo[0]+1),np.uint8)
            cv2.fillConvexPoly(mask,np.rint(pix-lo).astype(np.int32),1)
            roi=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1];np.minimum(roi,np.where(mask,cz[fi],np.inf),out=roi)
        xy=np.clip(np.rint(cp).astype(int),[0,0],[499,h-1])
        visible=(cz>0)&(cp[:,0]>=0)&(cp[:,0]<500)&(cp[:,1]>=0)&(cp[:,1]<h)
        visible&=cz<=depth[xy[:,1],xy[:,0]]+2*report['voxel_size_m']
        full_pixels,_=project(v,c,report['proxy_width'])
        native_h=round(c['image_size'][1]*report['proxy_width']/c['image_size'][0])
        inside=(full_pixels[:,0]>=0)&(full_pixels[:,0]<report['proxy_width'])&(full_pixels[:,1]>=0)&(full_pixels[:,1]<native_h)
        mask=cv2.imread(str(hull/(name+'_mask.png')),cv2.IMREAD_GRAYSCALE)
        mi=np.clip(np.rint(full_pixels).astype(int),[0,0],[report['proxy_width']-1,native_h-1])
        inside&=mask[mi[:,1],mi[:,0]]>0
        visible&=inside[f].all(1)
        take=visible&(score>best)&(score>.05)
        chosen[take]=index;best[take]=score[take]
        uv_all.append(np.c_[(full_pixels[:,0]+.5)/report['proxy_width'],1-(full_pixels[:,1]+.5)/native_h])
    np.savez_compressed(hull/'texture_assignment.npz',camera_index=chosen,uv=np.asarray(uv_all))
    (hull/'texture_report.json').write_text(json.dumps(dict(fit_views=names,
        mesh_sha256=sha(hull/'mesh_board.npz'),textured_triangles=int((chosen>=0).sum()),total_triangles=len(f),
        validation_images_used=False,unseen_surface='neutral grey',
        occlusion_method='500px depth buffer; triangle-centroid depth with two-voxel allowance',
        source_photos={n:sha(hull/(n+'_photo.jpg')) for n in names}),indent=2)+'\n')
    print('Textured triangles',int((chosen>=0).sum()),'/',len(f))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hull',type=Path,required=True)
    a=p.parse_args();texture(a.hull)

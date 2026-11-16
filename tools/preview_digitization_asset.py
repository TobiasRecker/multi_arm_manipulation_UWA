"""CPU-only textured preview without Qt/OpenGL/ROS; orthographic depth buffer."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import trimesh


def render(asset,output):
    manifest=json.loads((asset/'asset.json').read_text());scene=trimesh.load(asset/manifest['preview_mesh'],force='scene')
    entries=[]
    for node in scene.graph.nodes_geometry:
        T,name=scene.graph[node];mesh=scene.geometry[name]
        entries.append((mesh,mesh.vertices@T[:3,:3].T+T[:3,3]))
    all_points=np.concatenate([p for _,p in entries]);centre=(all_points.min(axis=0)+all_points.max(axis=0))/2
    canvas=np.full((1000,1600,3),240,np.uint8)
    for side,eye_direction in enumerate(([1.3,2.2,1.5],[1.3,-2.2,1.5])):
        forward=-np.array(eye_direction,float);forward/=np.linalg.norm(forward)
        right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right);up=np.cross(right,forward)
        basis=np.array([right,-up,forward]).T;projected=(all_points-centre)@basis
        scale=min(720/np.ptp(projected[:,0]),700/np.ptp(projected[:,1]));origin=np.array([side*800+400,455])
        zbuffer=np.full(canvas.shape[:2],np.inf)
        for mesh,points in entries:
            p=(points-centre)@basis;pixel=p[:,:2]*scale+origin
            textured=hasattr(mesh.visual,'uv') and mesh.visual.uv is not None
            texture=np.asarray(mesh.visual.material.baseColorTexture.convert('RGB')) if textured else None
            for face in mesh.faces:
                xyz=points[face];normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]);normal/=np.linalg.norm(normal)
                if normal@(-forward)<=0:continue
                triangle=pixel[face];lo=np.maximum(np.floor(triangle.min(axis=0)).astype(int),[side*800,85]);hi=np.minimum(np.ceil(triangle.max(axis=0)).astype(int),[side*800+799,830])
                if np.any(hi<lo):continue
                matrix=np.column_stack((triangle[1]-triangle[0],triangle[2]-triangle[0]))
                if abs(np.linalg.det(matrix))<1e-8:continue
                xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
                coordinates=np.c_[xx.ravel()+.5,yy.ravel()+.5];uv=(coordinates-triangle[0])@np.linalg.inv(matrix).T
                weights=np.c_[1-uv.sum(axis=1),uv];inside=(weights>=-1e-8).all(axis=1)
                depth=weights@p[face,2];cx=xx.ravel();cy=yy.ravel();keep=inside&(depth<zbuffer[cy,cx])
                if not keep.any():continue
                cx=cx[keep];cy=cy[keep];zbuffer[cy,cx]=depth[keep]
                if textured:
                    texuv=np.clip(weights[keep]@mesh.visual.uv[face],0,1)
                    tx=np.rint(texuv[:,0]*(texture.shape[1]-1)).astype(int);ty=np.rint((1-texuv[:,1])*(texture.shape[0]-1)).astype(int)
                    colors=texture[ty,tx].astype(float)
                else:colors=np.asarray(mesh.visual.vertex_colors[face,:3],float).mean(axis=0)
                shade=.78+.22*max(0.,float(normal@np.array([.2,-.3,.93])))
                canvas[cy,cx]=np.clip(colors*shade,0,255).astype(np.uint8)
    image=Image.fromarray(canvas);draw=ImageDraw.Draw(image)
    try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',23);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
    except OSError:font=small=ImageFont.load_default()
    quality='IMAGE CONSISTENCY PASSED' if manifest['quality'].get('image_consistency_passed') else 'GEOMETRY REVIEW REQUIRED'
    for side in (0,1):
        x=side*800+22;draw.text((x,24),manifest['asset_id']+(' / FRONT' if side==0 else ' / REAR'),font=font,fill=(5,15,25))
        dims=' x '.join(f'{v*1000:.0f}' for v in manifest['dimensions_m'])+' mm'
        method=('Silhouette envelope; grid/interior not measured' if manifest.get('geometry_method')=='visual_hull'
                else 'Recipe geometry; fine details not measured')
        draw.multiline_text((x,855),dims+'\n'+quality+'\n'+method+'\nAccuracy / manipulation NOT VALIDATED',font=small,fill=(5,15,25),spacing=5)
    image.save(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();render(a.asset.resolve(),a.output.resolve())

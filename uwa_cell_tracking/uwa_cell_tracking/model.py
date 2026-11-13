"""Create immutable 2D-descriptor/3D-surface references from textured assets."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np

NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}


def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def surface_reference(asset, output, max_features=1600):
    """Read only geometry, UV and texture; reference/world poses are not used."""
    asset=Path(asset).resolve();manifest=json.loads((asset/'asset.json').read_text())
    if manifest['units']!='m':raise ValueError('Tracker requires asset geometry in metres')
    for name,digest in manifest['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or file_sha(asset/name)!=digest:
            raise ValueError('Invalid asset resource/hash '+name)
    root=ET.parse(asset/manifest['visual_mesh']).getroot()
    images={im.get('id'):im.findtext('c:init_from',namespaces=NS) for im in root.findall('c:library_images/c:image',NS)}
    effects={e.get('id'):e for e in root.findall('c:library_effects/c:effect',NS)}
    materials={m.get('id'):m.find('c:instance_effect',NS).get('url')[1:] for m in root.findall('c:library_materials/c:material',NS)}
    mapping={}
    for node in root.findall('c:library_visual_scenes/c:visual_scene/c:node',NS):
        instance=node.find('c:instance_geometry',NS)
        if instance is not None:
            # The packaged asset bakes transforms. Reject unapplied transforms.
            if any(node.find('c:'+k,NS) is not None for k in ('matrix','translate','rotate','scale')):
                raise ValueError('Bake DAE transforms before creating tracker reference')
            mapping[instance.get('url')[1:]]=instance.find('.//c:instance_material',NS).get('target')[1:]
    objects=[];descriptors=[];surfaces=[];stats=[]
    detector=cv2.SIFT_create(nfeatures=max_features)
    for surface,geometry in enumerate(root.findall('c:library_geometries/c:geometry',NS)):
        effect=effects[materials[mapping[geometry.get('id')]]]
        diffuse=effect.find('.//c:diffuse/c:texture',NS)
        if diffuse is None:continue  # Unknown/plain hidden faces give no measured appearance.
        sampler=diffuse.get('texture')
        surface_id=effect.find(f".//c:newparam[@sid='{sampler}']/c:sampler2D/c:source",NS).text
        image_id=effect.find(f".//c:newparam[@sid='{surface_id}']/c:surface/c:init_from",NS).text
        texture=cv2.imread(str(asset/images[image_id]),cv2.IMREAD_GRAYSCALE)
        if texture is None:raise ValueError('Cannot read reference texture')
        h,w=texture.shape;mesh=geometry.find('c:mesh',NS)
        arrays={s.get('id'):np.fromstring(s.findtext('c:float_array',namespaces=NS),sep=' ').reshape(-1,int(s.find('c:technique_common/c:accessor',NS).get('stride'))) for s in mesh.findall('c:source',NS)}
        points=arrays[mesh.find('c:vertices/c:input',NS).get('source')[1:]]
        triangles=mesh.find('c:triangles',NS);inputs=triangles.findall('c:input',NS)
        tex_input=next(x for x in inputs if x.get('semantic')=='TEXCOORD')
        vertex_input=next(x for x in inputs if x.get('semantic')=='VERTEX')
        stride=max(int(x.get('offset')) for x in inputs)+1
        indices=np.fromstring(triangles.findtext('c:p',namespaces=NS),sep=' ',dtype=int).reshape(-1,3,stride)
        uv=arrays[tex_input.get('source')[1:]]
        uv_faces=uv[indices[:,:,int(tex_input.get('offset'))]]
        point_faces=points[indices[:,:,int(vertex_input.get('offset'))]]
        mask=np.zeros_like(texture)
        for tri in uv_faces:
            pixel=tri*np.array([w-1,-(h-1)])+np.array([0,h-1]);cv2.fillConvexPoly(mask,np.round(pixel).astype(np.int32),255)
        mask=cv2.erode(mask,np.ones((13,13),np.uint8))
        keypoints,desc=detector.detectAndCompute(texture,mask)
        if desc is None:continue
        kp=np.array([p.pt for p in keypoints]);normalized=kp/np.array([w-1,h-1]);normalized[:,1]=1-normalized[:,1]
        assigned=np.zeros(len(kp),bool);local_points=np.zeros((len(kp),3))
        for tri,xyz in zip(uv_faces,point_faces):
            matrix=np.column_stack((tri[1]-tri[0],tri[2]-tri[0]))
            if abs(np.linalg.det(matrix))<1e-10:continue
            bary=(normalized-tri[0])@np.linalg.inv(matrix).T
            valid=(bary.min(axis=1)>=-1e-6)&(bary.sum(axis=1)<=1+1e-6)&~assigned
            local_points[valid]=xyz[0]+bary[valid]@np.array([xyz[1]-xyz[0],xyz[2]-xyz[0]])
            assigned|=valid
        objects.extend(local_points[assigned]);descriptors.extend(desc[assigned]);surfaces.extend([surface]*int(assigned.sum()))
        stats.append(dict(surface=surface,texture=images[image_id],features=int(assigned.sum())))
    if len(objects)<30:raise ValueError('Insufficient textured surface features')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output,points=np.asarray(objects),descriptors=np.asarray(descriptors,np.float32),surfaces=np.asarray(surfaces,np.int32))
    meta=dict(schema=1,asset_id=manifest['asset_id'],asset_manifest_sha256=file_sha(asset/'asset.json'),
        reference_sha256=file_sha(output),features=len(objects),surface_stats=stats,
        dimensions_m=manifest['dimensions_m'],geometry_accuracy_validated=manifest['quality']['measured_accuracy_validated'],
        reference_pose_used=False,method='SIFT texture descriptors mapped barycentrically to metric surface triangles')
    output.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

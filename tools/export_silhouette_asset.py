#!/usr/bin/env python3
"""Export an explicitly unvalidated photo-textured outer-envelope candidate."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image
import trimesh


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def export(hull,output):
    hull,output=Path(hull),Path(output)
    report=json.loads((hull/'reconstruction.json').read_text());tex=json.loads((hull/'texture_report.json').read_text())
    if sha(hull/'mesh_board.npz')!=tex['mesh_sha256']:raise ValueError('Mesh changed after texture assignment')
    if sha(report['source_models'])!=report['source_models_sha256'] or sha(report['source_annotations'])!=report['source_annotations_sha256']:
        raise ValueError('Camera models or mask annotations changed after reconstruction')
    data=np.load(hull/'mesh_board.npz');board_v,f=data['vertices'],data['faces']
    T=np.diag([1.,-1.,-1.,1.]);T[:2,3]=(board_v[:,:2].min(0)+board_v[:,:2].max(0))/2
    T[2,3]=report.get('support_plane_board_z_m') or 0.
    # Proper 180deg rotation about X: object +Z points above the printed board.
    v=(board_v-T[:3,3])@T[:3,:3]
    assigned=np.load(hull/'texture_assignment.npz');ids=assigned['camera_index'];uv=assigned['uv']
    mesh=trimesh.Trimesh(v,f,process=False);scene=trimesh.Scene()
    for index in [-1,*range(len(tex['fit_views']))]:
        selected=f[ids==index]
        if not len(selected):continue
        part=trimesh.Trimesh(v[selected].reshape(-1,3),np.arange(len(selected)*3).reshape(-1,3),process=False)
        if index<0:
            part.visual=trimesh.visual.ColorVisuals(part,vertex_colors=np.tile([145,145,145,255],(len(part.vertices),1)))
            name='unobserved_neutral_surface'
        else:
            name=tex['fit_views'][index];photo=hull/(name+'_photo.jpg')
            if sha(photo)!=tex['source_photos'][name]:raise ValueError('Texture photo changed')
            part.visual=trimesh.visual.TextureVisuals(uv=np.clip(uv[index][selected].reshape(-1,2),0,1),
                material=trimesh.visual.material.PBRMaterial(name=name,baseColorTexture=Image.open(photo).convert('RGB'),metallicFactor=0,roughnessFactor=1))
        scene.add_geometry(part,node_name=name)
    output.mkdir(parents=True,exist_ok=False)
    scene.export(output/'model.glb');mesh.export(output/'outer_envelope.stl')
    loaded=trimesh.load(output/'model.glb',force='scene')
    np.testing.assert_allclose(loaded.bounds,mesh.bounds,atol=1e-6)
    for source,name in [(hull/'reconstruction.json','reconstruction.json'),
                        (hull/'texture_report.json','texture_report.json'),
                        (Path(report['source_models']),'camera_models_snapshot.json'),
                        (Path(report['source_annotations']),'silhouette_annotations.json')]:
        shutil.copyfile(source,output/name)
    (output/'README.txt').write_text('DRAFT outer-envelope candidate, metres.\n'
        'GLB contains photographic textures; grey faces are unobserved.\n'
        'Cage holes and hidden interior are not reconstructed.\n'
        'Watertight envelope does not mean measured material or mechanical CAD.\n'
        'Not approved for tracking, collisions, manipulation or manufacture.\n'
        'T_board_asset in asset.json registers this local +Z-up asset to the right board.\n')
    manifest=dict(schema=1,asset_id='student_robot_v1_visual_hull_candidate',preview_mesh='model.glb',
        geometry_method='visual_hull',status='DRAFT_REVIEW_REQUIRED',units='m',
        dimensions_m=mesh.extents.tolist(),T_board_asset=T.tolist(),reference_frame='right_table_board',
        triangles=len(f),watertight=bool(mesh.is_watertight),signed_envelope_volume_m3=float(mesh.volume),
        measured_material_volume=False,source_reconstruction_sha256=sha(hull/'reconstruction.json'),
        source_mask_annotations_sha256=report['source_annotations_sha256'],
        source_camera_models_sha256=report['source_models_sha256'],
        fit_views=report['fit_views'],validation_views=report['validation_views'],
        photo_textured_triangle_fraction=float((ids>=0).mean()),
        quality=dict(image_consistency_passed=False,geometry_validated=False,tracking_validated=False,manipulation_approved=False),
        limitations=report['limitations']+[
            'Photographic appearance includes background seen through the cage; it is not measured material albedo.',
            'Not an editable mechanical CAD model. STL represents the envelope, not actual material or a collision-approved body.'],
        files={p.name:sha(p) for p in output.iterdir()})
    (output/'asset.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(asset=str(output),dimensions_m=manifest['dimensions_m'],watertight=manifest['watertight'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hull',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();export(a.hull,a.output)

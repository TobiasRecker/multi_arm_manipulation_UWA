"""Recipe-driven candidate CAD/photo asset export; run in .venvs/oak-model.

Reads only a completed job's frozen fit/cameras. Never connects to ROS/hardware
or installs an asset in a live cell. Metres in meshes; STEP in millimetres.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
import trimesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.STEPControl import STEPControl_Writer,STEPControl_Reader,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.StlAPI import StlAPI_Writer
from OCP.gp import gp_Pnt,gp_Trsf
from export_scanned_carton import connected_components
from package_carton_asset import package


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export(job,output):
    spec=json.loads((job/'job.json').read_text())['spec'];model=json.loads((job/'fit/model.json').read_text())
    if output.exists():raise ValueError('Candidate directory already exists')
    work=job/'export_work'/output.name;work.mkdir(parents=True,exist_ok=False);cad=work/'cad';cad.mkdir()
    frozen=dict(model,measured_dimensions_source='user supplied thicknesses; overall dimensions fitted from images')
    thickness=model['known_dimensions_m'].get('plate_thickness_m',model['known_dimensions_m'].get('wall_thickness_m'))
    frozen['plate_thickness_m']=thickness
    (work/'model.json').write_text(json.dumps(frozen,indent=2)+'\n')
    (work/'provenance.json').write_text(json.dumps(dict(dataset_sha256=sha(job/'dataset.json')))+'\n')
    shape=None
    for body in model['parts']:
        origin=np.array(body['origin_m'],float);size=np.array(body['size_m'],float)
        if origin.shape!=(3,) or size.shape!=(3,) or not np.isfinite([origin,size]).all() or min(size)<=0:raise ValueError('Invalid recipe body')
        part=BRepPrimAPI_MakeBox(gp_Pnt(*(origin*1000)),*(size*1000)).Shape()
        shape=part if shape is None else BRepAlgoAPI_Fuse(shape,part).Shape()
    if shape is None or not BRepCheck_Analyzer(shape).IsValid():raise ValueError('Invalid solid')
    writer=STEPControl_Writer();writer.Transfer(shape,STEPControl_AsIs)
    if writer.Write(str(cad/'model.step'))!=IFSelect_RetDone:raise ValueError('STEP write failed')
    reader=STEPControl_Reader()
    if reader.ReadFile(str(cad/'model.step'))!=IFSelect_RetDone:raise ValueError('STEP readback failed')
    reader.TransferRoots();box=Bnd_Box();BRepBndLib.Add_s(reader.OneShape(),box)
    extent=np.array(box.CornerMax().Coord())-box.CornerMin().Coord()
    np.testing.assert_allclose(extent,np.array(model['dimensions_m'])*1000,atol=1e-4)
    transform=gp_Trsf();transform.SetScale(gp_Pnt(0,0,0),.001)
    metres=BRepBuilderAPI_Transform(shape,transform,True).Shape();BRepMesh_IncrementalMesh(metres,.0001,False,.3,False).Perform()
    writer=StlAPI_Writer();writer.ASCIIMode=False
    if not writer.Write(metres,str(cad/'model.stl')):raise ValueError('STL write failed')
    mesh=trimesh.load(cad/'model.stl',force='mesh')
    if not mesh.is_watertight or not mesh.is_winding_consistent or connected_components(mesh)!=1 or mesh.volume<=0:raise ValueError('Export must be one closed consistently wound body')
    np.testing.assert_allclose(mesh.extents,model['dimensions_m'],atol=1e-6)
    # Generic source-view texturing is intentionally explicit: the input gives
    # four physical coplanar points with original image/optics binding. Existing
    # rectified textures can be supplied per plane; absent faces stay plain.
    # Never bake unrelated background into a synthetic object appearance.
    scene=trimesh.Scene();texture_sources=[]
    state=json.loads((job/'state.json').read_text())
    definitions=(json.loads((job/'fit/textures.json').read_text())
        if state['stages'].get('texture',{}).get('status')=='DONE' else [])
    used=np.zeros(len(mesh.faces),bool)
    for number,item in enumerate(definitions):
        texture_path=Path(item['texture']);pixels_sha=sha(texture_path)
        if pixels_sha!=item['texture_sha256']:raise ValueError('Rectified texture changed')
        name=item['camera_view'];cameras=json.loads((job/'prepared/camera_models.json').read_text())
        if name not in cameras or item['source_image_sha256']!=cameras[name]['image_sha256']:raise ValueError('Texture source not bound to prepared photograph')
        origin=np.array(item['origin_m']);u=np.array(item['u_m']);v=np.array(item['v_m'])
        if origin.shape!=(3,) or u.shape!=(3,) or v.shape!=(3,) or not np.isfinite([origin,u,v]).all():raise ValueError('Invalid texture plane')
        normal=np.cross(u,v);area=np.linalg.norm(normal)
        if area<1e-8 or abs(np.dot(u,v))>1e-8:raise ValueError('Texture axes must be nondegenerate and orthogonal')
        normal/=area;normal*=item['normal_sign']
        mask=(np.abs((mesh.triangles_center-origin)@normal)<1e-6)&(mesh.face_normals@normal>.999)&~used
        uv=np.c_[((mesh.vertices-origin)@u)/(u@u),((mesh.vertices-origin)@v)/(v@v)]
        selected=np.flatnonzero(mask)
        if not len(selected):raise ValueError('Texture plane does not match exposed CAD faces')
        if np.any(uv[mesh.faces[selected]]<-.001) or np.any(uv[mesh.faces[selected]]>1.001):raise ValueError('Texture aperture fails to cover selected CAD faces')
        used|=mask;points=mesh.triangles[selected].reshape(-1,3)
        part=trimesh.Trimesh(vertices=points,faces=np.arange(len(points)).reshape(-1,3),vertex_normals=np.repeat(mesh.face_normals[selected],3,axis=0),process=False)
        local_uv=np.c_[((points-origin)@u)/(u@u),((points-origin)@v)/(v@v)]
        part.visual=trimesh.visual.TextureVisuals(uv=local_uv,material=trimesh.visual.material.PBRMaterial(
            baseColorTexture=Image.open(texture_path),roughnessFactor=.8,metallicFactor=0))
        scene.add_geometry(part,node_name='photo_'+str(number));texture_sources.append(item['source_image_sha256'])
    if (~used).any():
        selected=np.flatnonzero(~used);points=mesh.triangles[selected].reshape(-1,3)
        part=trimesh.Trimesh(vertices=points,faces=np.arange(len(points)).reshape(-1,3),vertex_normals=np.repeat(mesh.face_normals[selected],3,axis=0),process=False)
        color=[174,142,99,255] if model['family']=='box_shell' else [220,224,225,255]
        part.visual=trimesh.visual.ColorVisuals(part,vertex_colors=np.tile(color,(len(part.vertices),1)));scene.add_geometry(part,node_name='unobserved_plain_faces')
    scene.export(cad/'model.glb');np.testing.assert_allclose(trimesh.load(cad/'model.glb',force='scene').extents,model['dimensions_m'],atol=1e-6)
    report=dict(schema=1,source_sha256=sha(work/'model.json'),visual_glb='model.glb',solid_mesh='model.stl',cad_step='model.step',
        stl_watertight=True,stl_connected_solids=1,stl_triangles=len(mesh.faces),volume_m3=float(mesh.volume),step_extents_mm=extent.tolist(),
        units=dict(step='mm',meshes='m'),texture_source_image_sha256=sorted(set(texture_sources)),
        files={p.name:sha(p) for p in cad.iterdir()})
    (cad/'export.json').write_text(json.dumps(report,indent=2)+'\n')
    package(work,output,basename='model',title=spec['object_id']+' / '+model['family'],source_model='model.json')
    manifest=json.loads((output/'asset.json').read_text());manifest['quality'].update(
        image_consistency_passed=model['image_consistency_passed'],tracking_validated=False,
        manipulation_approved=False,known_dimensions_m=model['known_dimensions_m'],
        photographic_texture_planes=len(definitions),unobserved_faces='plain assumed colour',
        fine_details_measured=False)
    manifest['provenance'].update(texture_source_image_sha256=report['texture_source_image_sha256'],
        job_spec_sha256=sha(job/'job.json'),camera_models_sha256=sha(job/'prepared/camera_models.json'))
    shutil.copyfile(cad/'export.json',output/'export_checks.json')
    manifest['files']['export_checks.json']=sha(output/'export_checks.json')
    (output/'asset.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();export(a.job.resolve(),a.output.resolve())

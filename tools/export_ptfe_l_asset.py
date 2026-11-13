"""Create a valid simplified PTFE/aluminium assembly and textured asset.

OpenCascade solids are mm; STL/GLB/DAE are m. Profile slot internals and tiny
perforations remain appearance-only, not falsely measured CAD geometry.
"""
import argparse
import hashlib
import json
from pathlib import Path

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


def export(root,asset):
    source=root/'reconstruction';model_path=source/'assembly_result.json';result=json.loads(model_path.read_text())
    cad=source/'cad';cad.mkdir(exist_ok=True)
    W,D,H=[result[k] for k in ('width_m','base_plate_depth_m','upright_plate_height_m')]
    if min(W,D,H)<=.04:raise ValueError('Nonphysical assembly dimensions')
    bars=[('base_left',[0,0,0],[.02,D+.03,.02]),('base_right',[W-.02,0,0],[.02,D+.03,.02]),
        ('base_back',[.02,0,0],[W-.04,.02,.02]),('base_front',[.02,D+.01,0],[W-.04,.02,.02]),
        ('upright_left',[0,0,.02],[.02,.02,H+.01]),('upright_right',[W-.02,0,.02],[.02,.02,H+.01]),
        ('upright_top',[.02,0,H+.01],[W-.04,.02,.02])]
    # A hidden0.1mm clearance avoids a non-manifold line-only contact between
    # rear support and plate. Visible sizes and operator-specified thicknesses
    # remain unchanged; this is a CAD convention, not a measured detail.
    plates=[('base_ptfe',[0,.0201,.02],[W,D+.0099,.01]),('upright_ptfe',[0,.02,.03],[W,.01,H])]
    shape=None
    for name,origin,size in bars+plates:
        part=BRepPrimAPI_MakeBox(gp_Pnt(*[x*1000 for x in origin]),*[x*1000 for x in size]).Shape()
        shape=part if shape is None else BRepAlgoAPI_Fuse(shape,part).Shape()
    if not BRepCheck_Analyzer(shape).IsValid():raise ValueError('Invalid PTFE assembly solid')
    writer=STEPControl_Writer();writer.Transfer(shape,STEPControl_AsIs)
    if writer.Write(str(cad/'model.step'))!=IFSelect_RetDone:raise ValueError('STEP export failed')
    reader=STEPControl_Reader()
    if reader.ReadFile(str(cad/'model.step'))!=IFSelect_RetDone:raise ValueError('STEP readback failed')
    reader.TransferRoots();box=Bnd_Box();BRepBndLib.Add_s(reader.OneShape(),box)
    extent=np.array(box.CornerMax().Coord())-box.CornerMin().Coord()
    np.testing.assert_allclose(extent,np.array(result['dimensions_m'])*1000,atol=1e-4)
    transform=gp_Trsf();transform.SetScale(gp_Pnt(0,0,0),.001)
    metres=BRepBuilderAPI_Transform(shape,transform,True).Shape();BRepMesh_IncrementalMesh(metres,.0001,False,.3,False).Perform()
    stl=StlAPI_Writer();stl.ASCIIMode=False
    if not stl.Write(metres,str(cad/'model.stl')):raise ValueError('STL export failed')
    mesh=trimesh.load(cad/'model.stl',force='mesh');components=connected_components(mesh)
    if not mesh.is_watertight or components!=1 or mesh.volume<=0:raise ValueError('Assembly must be one closed solid')
    np.testing.assert_allclose(mesh.extents,result['dimensions_m'],atol=1e-6)
    centres=mesh.triangles_center;normals=mesh.face_normals;tol=1e-6
    masks={
        'base_top':(normals[:,2]>.99)&(abs(centres[:,2]-.03)<tol)&(centres[:,1]>.03-tol),
        'upright_front':(normals[:,1]>.99)&(abs(centres[:,1]-.03)<tol)&(centres[:,2]>.03-tol),
        'upright_back':(normals[:,1]<-.99)&(abs(centres[:,1]-.02)<tol)&(centres[:,2]>.03-tol),
        'metal_front':(normals[:,1]>.99)&(abs(centres[:,1]-(D+.03))<tol)&(centres[:,2]<.02+tol),
        'metal_back':(normals[:,1]<-.99)&(abs(centres[:,1])<tol)}
    scene=trimesh.Scene();assigned=np.zeros(len(mesh.faces),bool)
    def flat_part(mask):
        index=np.flatnonzero(mask);points=mesh.triangles[index].reshape(-1,3)
        return trimesh.Trimesh(vertices=points,faces=np.arange(len(points)).reshape(-1,3),
            vertex_normals=np.repeat(mesh.face_normals[index],3,axis=0),process=False)
    for name,mask in masks.items():
        if not mask.any():raise ValueError('Missing visible face '+name)
        assigned|=mask;part=flat_part(mask);p=part.vertices
        if name=='base_top':uv=np.c_[p[:,0]/W,(p[:,1]-.03)/D]
        elif name=='upright_front':uv=np.c_[p[:,0]/W,(p[:,2]-.03)/H]
        elif name=='upright_back':uv=np.c_[(p[:,0]-.02)/(W-.04),(p[:,2]-.03)/(H-.02)]
        elif name=='metal_front':uv=np.c_[p[:,0]/W,p[:,2]/.02]
        else:uv=np.c_[p[:,0]/W,p[:,2]/(H+.03)]
        material=trimesh.visual.material.PBRMaterial(name=name,
            baseColorTexture=Image.open(source/(name+'_texture.jpg')),roughnessFactor=.8,metallicFactor=0)
        part.visual=trimesh.visual.TextureVisuals(uv=uv,material=material);scene.add_geometry(part,node_name=name)
    white=((centres[:,1]>=.02-tol)&(centres[:,1]<=.03+tol)&(centres[:,2]>=.03-tol))|((centres[:,1]>=.02-tol)&(centres[:,2]>=.02-tol)&(centres[:,2]<=.03+tol))
    for name,mask,color in [('ptfe_edges',~assigned&white,[235,235,229,255]),('aluminium',~assigned&~white,[155,164,170,255])]:
        if not mask.any():continue
        part=flat_part(mask);part.visual=trimesh.visual.ColorVisuals(part,vertex_colors=np.tile(color,(len(part.vertices),1)))
        scene.add_geometry(part,node_name=name)
    scene.metadata.update(units='metres',up_axis='Z',measured_accuracy_validated=False)
    scene.export(cad/'model.glb');loaded=trimesh.load(cad/'model.glb',force='scene')
    np.testing.assert_allclose(loaded.extents,result['dimensions_m'],atol=1e-6)
    report=dict(schema=1,STEP_units='mm',STL_units='m',GLB_units='m',step_reimport_extents_mm=extent.tolist(),
        stl_watertight=True,stl_connected_solids=components,stl_winding_consistent=bool(mesh.is_winding_consistent),
        stl_triangles=len(mesh.faces),volume_m3=float(mesh.volume),visual_glb='model.glb',solid_mesh='model.stl',cad_step='model.step',
        source_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),parts=[dict(name=n,origin_m=o,size_m=s) for n,o,s in bars+plates],
        known_dimensions=dict(profile_mm=[20,20],plate_mm=10,source='user'),
        limitations='Simplified external profile bodies; internal slots/fasteners/perforations appearance only; underside inferred',
        hidden_cad_clearance_m=.0001,hidden_cad_clearance_measured=False,
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cad.iterdir() if p.suffix in ('.step','.stl','.glb')})
    (cad/'export.json').write_text(json.dumps(report,indent=2)+'\n')
    package(source,asset,basename='model',title='PTFE L assembly with20mm aluminium supports',source_model='assembly_result.json')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--asset',type=Path,required=True)
    a=p.parse_args();export(a.root.resolve(),a.asset.resolve())

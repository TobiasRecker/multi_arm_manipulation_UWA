"""Export and verify the image-derived polygon-panel carton (offline).

Isolated .venvs/oak-model: OpenCascade STEP/mm, watertight STL/m, textured
GLB/m and an editable OpenSCAD/mm. Thickness is an explicit assumption.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakePrism
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.STEPControl import STEPControl_Writer, STEPControl_Reader, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.StlAPI import StlAPI_Writer
from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf


def connected_components(mesh):
    """Count connected mesh components without an optional graph dependency."""
    parent=list(range(len(mesh.vertices)))
    def root(v):
        while parent[v]!=v:
            parent[v]=parent[parent[v]];v=parent[v]
        return v
    for face in mesh.faces:
        for b in face[1:]:parent[root(int(b))]=root(int(face[0]))
    return len({root(int(v)) for v in mesh.faces.ravel()})


def export(source,out):
    result=json.loads(source.read_text());out.mkdir(parents=True,exist_ok=True)
    L,W,H=[result[k]*1000 for k in ('length_m','width_m','height_m')]
    t=result['wall_thickness_m']*1000
    if not (0<t<min(L,W,H)/4):raise ValueError('Invalid thickness')
    shape=BRepPrimAPI_MakeBox(L,W,t).Shape();scad=[]
    for name,panel in result['panels'].items():
        profile=np.array(panel['top_profile_m'])*1000;extent=panel['extent_m']*1000
        outline=np.vstack([[0,0],[extent,0],profile[::-1]])
        points=[]
        for s,z in outline:
            if name=='front':points.append([s,0,z])
            elif name=='back':points.append([s,W-t,z])
            elif name=='left':points.append([0,s,z])
            else:points.append([L-t,s,z])
        polygon=BRepBuilderAPI_MakePolygon()
        for point in points:polygon.Add(gp_Pnt(*point))
        polygon.Close();face=BRepBuilderAPI_MakeFace(polygon.Wire()).Face()
        direction=gp_Vec(0,t,0) if name in ('front','back') else gp_Vec(t,0,0)
        wall=BRepPrimAPI_MakePrism(face,direction).Shape()
        if not BRepCheck_Analyzer(wall).IsValid():raise ValueError('Invalid wall '+name)
        fusion=BRepAlgoAPI_Fuse(shape,wall);fusion.Build()
        if not fusion.IsDone():raise ValueError('Wall union failed '+name)
        shape=fusion.Shape()
        # OpenSCAD polygon is in local XY, then turned into a vertical panel.
        if name in ('front','back'):
            matrix=[[1,0,0,0],[0,0,1,0 if name=='front' else 'W-wall'],[0,1,0,0],[0,0,0,1]]
        else:
            matrix=[[0,0,1,0 if name=='left' else 'L-wall'],[1,0,0,0],[0,1,0,0],[0,0,0,1]]
        def literal(value):
            return value if isinstance(value,str) else str(value)
        matrix_text='['+','.join('['+','.join(literal(v) for v in row)+']' for row in matrix)+']'
        scad.append(f'  // {name}: visible photo contour\n  multmatrix({matrix_text})\n    linear_extrude(height=wall) polygon(points={json.dumps(outline.tolist())});')
    if not BRepCheck_Analyzer(shape).IsValid():raise ValueError('Invalid merged CAD solid')
    writer=STEPControl_Writer();writer.Transfer(shape,STEPControl_AsIs)
    if writer.Write(str(out/'carton.step'))!=IFSelect_RetDone:raise ValueError('STEP export failed')
    reader=STEPControl_Reader()
    if reader.ReadFile(str(out/'carton.step'))!=IFSelect_RetDone:raise ValueError('STEP readback failed')
    reader.TransferRoots();bbox=Bnd_Box();BRepBndLib.Add_s(reader.OneShape(),bbox)
    extents=np.array(bbox.CornerMax().Coord())-bbox.CornerMin().Coord()
    if not np.allclose(extents,[L,W,H],atol=1e-4):raise ValueError('STEP unit/extent mismatch')
    tr=gp_Trsf();tr.SetScale(gp_Pnt(0,0,0),.001)
    metres=BRepBuilderAPI_Transform(shape,tr,True).Shape()
    BRepMesh_IncrementalMesh(metres,.0001,False,.3,False).Perform()
    stl=StlAPI_Writer();stl.ASCIIMode=False
    if not stl.Write(metres,str(out/'carton.stl')):raise ValueError('STL export failed')
    mesh=trimesh.load(out/'carton.stl',force='mesh')
    count=connected_components(mesh)
    if not mesh.is_watertight or count!=1 or mesh.volume<=0:
        raise ValueError('Mesh must be one watertight outward solid')
    if not np.allclose(mesh.extents,np.array([L,W,H])/1000,atol=1e-6):raise ValueError('STL unit mismatch')
    (out/'carton.scad').write_text('// Image estimate; mm. Wall and floor thickness ASSUMED.\n'
        f'L={L:.9f}; W={W:.9f}; H={H:.9f}; wall={t};\nunion() {{\n  cube([L,W,wall]);\n'+'\n'.join(scad)+'\n}\n')
    # Photos are visual appearance only. Inner faces and hidden underside are
    # deliberately plain, not invented photo texture.
    normals=mesh.face_normals;centres=mesh.triangles_center
    masks={'front':normals[:,1]<-.99,'back':normals[:,1]>.99,
           'left':normals[:,0]<-.99,'right':normals[:,0]>.99}
    masks['front'] &= centres[:,1]<1e-6
    masks['back'] &= centres[:,1]>W/1000-1e-6
    masks['left'] &= centres[:,0]<1e-6
    masks['right'] &= centres[:,0]>L/1000-1e-6
    scene=trimesh.Scene();assigned=np.zeros(len(mesh.faces),bool)
    for name,mask in masks.items():
        if not mask.any():raise ValueError('Missing outer face '+name)
        assigned|=mask;part=mesh.submesh([np.flatnonzero(mask)],append=True)
        axis=0 if name in ('front','back') else 1;extent=(L if axis==0 else W)/1000
        uv=np.c_[part.vertices[:,axis]/extent,part.vertices[:,2]/(H/1000)]
        material=trimesh.visual.material.PBRMaterial(name=name,baseColorTexture=Image.open(source.parent/(name+'_texture.jpg')),
            metallicFactor=0,roughnessFactor=1,doubleSided=True)
        part.visual=trimesh.visual.TextureVisuals(uv=uv,material=material)
        scene.add_geometry(part,node_name=name)
    inside=mesh.submesh([np.flatnonzero(~assigned)],append=True)
    inside.visual=trimesh.visual.ColorVisuals(inside,vertex_colors=np.tile([174,142,99,255],(len(inside.vertices),1)))
    scene.add_geometry(inside,node_name='plain_unobserved_and_inner_faces')
    # Compute normals directly; scipy is intentionally not a CAD dependency.
    for geometry in scene.geometry.values():
        normals=np.zeros_like(geometry.vertices)
        weighted=geometry.face_normals*geometry.area_faces[:,None]
        for column in range(3):np.add.at(normals,geometry.faces[:,column],weighted)
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
        geometry.vertex_normals=normals
    scene.metadata.update(units='metres',up_axis='Z',measured_accuracy_validated=False,wall_thickness_assumed_m=t/1000)
    scene.export(out/'carton_textured.glb')
    loaded=trimesh.load(out/'carton_textured.glb',force='scene')
    if not np.allclose(loaded.extents,mesh.extents,atol=1e-6):raise ValueError('GLB readback unit mismatch')
    report=dict(schema=1,STEP_units='mm',SCAD_units='mm',STL_units='m',GLB_units='m',up_axis='Z',
        step_reimport_extents_mm=extents.tolist(),stl_watertight=bool(mesh.is_watertight),
        stl_connected_solids=count,stl_winding_consistent=bool(mesh.is_winding_consistent),
        stl_triangles=len(mesh.faces),volume_m3=float(mesh.volume),
        T_right_board_object=result['T_board_object'],source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        measured_accuracy_validated=False,wall_thickness_m=t/1000,wall_thickness_measured=False,
        textures='Saved photographs projected onto idealized outside panels. Inner/hidden surfaces plain.',
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in ('.stl','.step','.scad','.glb')})
    (out/'export.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();export(args.model.resolve(),args.output.resolve())

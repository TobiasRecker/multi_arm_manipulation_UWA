"""Export a reconstructed tray to STEP (mm), STL (m), and editable SCAD.

Runs in the isolated CAD environment; it reads saved parameters, no cameras.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
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
import trimesh

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--result',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
result=json.loads(args.result.read_text());out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
shape=None
for name,origin,size in result['solid_parts']:
 part=BRepPrimAPI_MakeBox(gp_Pnt(*[v*1000 for v in origin]),*[v*1000 for v in size]).Shape()
 shape=part if shape is None else BRepAlgoAPI_Fuse(shape,part).Shape()
assert BRepCheck_Analyzer(shape).IsValid(),'Exported tray is not a valid solid'
writer=STEPControl_Writer();writer.Transfer(shape,STEPControl_AsIs);assert writer.Write(str(out/'carton.step'))==IFSelect_RetDone
# Confirm STEP reimport and its physical dimensions, independently of the mesh.
reader=STEPControl_Reader();assert reader.ReadFile(str(out/'carton.step'))==IFSelect_RetDone;reader.TransferRoots();box=Bnd_Box();BRepBndLib.Add_s(reader.OneShape(),box);lo=np.array(box.CornerMin().Coord());hi=np.array(box.CornerMax().Coord());extent=hi-lo
expected=np.array([result[k] for k in ('length_m','width_m','height_m')])*1000;assert np.allclose(extent,expected,atol=1e-4)
transform=gp_Trsf();transform.SetScale(gp_Pnt(0,0,0),.001);metres=BRepBuilderAPI_Transform(shape,transform,True).Shape();BRepMesh_IncrementalMesh(metres,.0002,False,.4,False).Perform();writer=StlAPI_Writer();writer.ASCIIMode=False;assert writer.Write(metres,str(out/'carton.stl'))
mesh=trimesh.load(out/'carton.stl',force='mesh')
assert mesh.is_watertight
assert np.allclose(mesh.extents,expected/1000,atol=1e-6)
l,w,h=expected;t=result['wall_thickness_m']*1000;fractions=result['divider_fractions']
(out/'carton.scad').write_text(f'''// Image-based estimate; dimensions mm; wall thickness assumed.
length = {l:.6f};
width = {w:.6f};
height = {h:.6f};
wall = {t:.6f};
dividers = {json.dumps(fractions)};
union() {{
  difference() {{
    cube([length,width,height]);
    translate([wall,wall,wall]) cube([length-2*wall,width-2*wall,height]);
  }}
  for (f=dividers)
    translate([f*length-wall/2,wall,wall])
      cube([wall,width-2*wall,height-wall]);
}}
''')
pose=np.asarray(result['T_board_object'],float)
assert np.isclose(np.linalg.det(pose[:3,:3]),1.)
report={'schema':1,'model':'open_rectangular_tray','source_result':str(args.result.resolve()),'STEP_units':'mm','STL_units':'m','SCAD_units':'mm','step_reimport_extents_mm':extent.tolist(),'stl_watertight':bool(mesh.is_watertight),'stl_triangles':len(mesh.faces),'T_right_board_object':pose.tolist(),'object_axes':'right-handed: X length,Y width,Z up; origin bottom corner3 of fitted board vertices','source_sha256':hashlib.sha256(args.result.read_bytes()).hexdigest(),'files':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('carton.step','carton.stl','carton.scad')}}
(out/'export.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

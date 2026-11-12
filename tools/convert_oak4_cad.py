"""Convert the supplied OAK4-Pro STEP assembly into metre-scale visual meshes.

Developer tool only: cadquery-ocp8.0.1.1.0 and vtk9.6.2. Normal ROS/Gazebo
operation loads the committed meshes and does not need these dependencies.
"""
import argparse
from pathlib import Path
import json,hashlib,struct,time,resource
resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000))
from OCP.TopoDS import TopoDS_Shape,TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
import vtk
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--step',type=Path,required=True)
parser.add_argument('--work-dir',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
p=args.work_dir.resolve();out=args.output.resolve();source=args.step.resolve()
p.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
reader=STEPControl_Reader()
if reader.ReadFile(str(source))!=IFSelect_RetDone:raise ValueError('STEP import failed')
reader.TransferRoots();shape=reader.OneShape();builder=BRep_Builder()
glass_faces=set();glass_parts=[];ex=TopExp_Explorer(shape,TopAbs_SOLID)
while ex.More():
 s=ex.Current();b=Bnd_Box();BRepBndLib.Add_s(s,b);lo=b.CornerMin().Coord();hi=b.CornerMax().Coord();extent=[hi[i]-lo[i] for i in range(3)]
 if extent[0]>130 and extent[1]>30 and lo[2]>28 and extent[2]<2:
  glass_parts.append({'bounds_mm':[*lo,*hi]});fe=TopExp_Explorer(s,TopAbs_FACE)
  while fe.More():glass_faces.add(hash(fe.Current()));fe.Next()
 ex.Next()
assert len(glass_parts)==2,glass_parts
body=TopoDS_Compound();glass=TopoDS_Compound();builder.MakeCompound(body);builder.MakeCompound(glass);ex=TopExp_Explorer(shape,TopAbs_FACE)
while ex.More():
 face=ex.Current();builder.Add(glass if hash(face) in glass_faces else body,face);ex.Next()
mesh=BRepMesh_IncrementalMesh(shape,.4,False,.45,False);mesh.Perform()
report={'source_archive':'oak4-pro-3d-model.zip','source_step':'oak4 enclosure-thermal 30.STEP','step_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_length_unit':'millimetre','mesh_length_unit':'metre','linear_deflection_mm':.4,'angular_deflection_rad':.45,'glass_parts':glass_parts,'cad_to_sensor_axes':{'x':'CAD +Z','y':'CAD -X','z':'CAD -Y'},'cad_visual_origin_mm':[0.,0.,32.5],'placement':'Illustrative RGB front-centre anchor; not a measured optical/CAD registration','assets':{}}
for name,s,target in [('oak4_pro',body,50000),('oak4_pro_glass',glass,4000)]:
 w=StlAPI_Writer();w.ASCIIMode=False;assert w.Write(s,str(p/(name+'-mm.stl')))
 reader=vtk.vtkSTLReader();reader.SetFileName(str(p/(name+'-mm.stl')));reader.Update();before=reader.GetOutput().GetNumberOfCells()
 dec=vtk.vtkQuadricDecimation();dec.SetInputConnection(reader.GetOutputPort());dec.SetTargetReduction(max(0.,1-target/before));dec.VolumePreservationOn();dec.Update()
 matrix=vtk.vtkMatrix4x4();matrix.Zero();matrix.SetElement(0,2,.001);matrix.SetElement(0,3,-.0325);matrix.SetElement(1,0,-.001);matrix.SetElement(2,1,-.001);matrix.SetElement(3,3,1.)
 transform=vtk.vtkTransform();transform.SetMatrix(matrix);tf=vtk.vtkTransformPolyDataFilter();tf.SetTransform(transform);tf.SetInputConnection(dec.GetOutputPort());tf.Update()
 normals=vtk.vtkPolyDataNormals();normals.SetInputConnection(tf.GetOutputPort());normals.ConsistencyOn();normals.AutoOrientNormalsOff();normals.ComputePointNormalsOff();normals.ComputeCellNormalsOn();normals.Update()
 destination=out/(name+'.stl');writer=vtk.vtkSTLWriter();writer.SetFileName(str(destination));writer.SetFileTypeToBinary();writer.SetInputConnection(normals.GetOutputPort());assert writer.Write()
 report['assets'][destination.name]={'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'triangles_before':before,'triangles_after':normals.GetOutput().GetNumberOfCells(),'bounds_m':normals.GetOutput().GetBounds(),'bytes':destination.stat().st_size};print(name,report['assets'][destination.name],flush=True)
(out/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')

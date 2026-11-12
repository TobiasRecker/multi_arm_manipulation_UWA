"""Offline CAD preview; no camera or robot access. Requires VTK."""
import argparse
from pathlib import Path
import json,vtk
parser=argparse.ArgumentParser(description='Render a saved reconstructed tray and its CAD mesh');parser.add_argument('--result-dir',type=Path,required=True);args=parser.parse_args();p=args.result_dir.resolve();r=json.loads((p/'reconstruction.json').read_text());L,W,H=[r[k] for k in ('length_m','width_m','height_m')]
reader=vtk.vtkSTLReader();reader.SetFileName(str(p/'cad/carton.stl'));reader.Update()
window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(1600,900)
for index in range(2):
 ren=vtk.vtkRenderer();ren.SetViewport(index*.5,0,(index+1)*.5,1);ren.SetBackground(.88,.91,.94);window.AddRenderer(ren)
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(reader.GetOutputPort());actor=vtk.vtkActor();actor.SetMapper(mapper);prop=actor.GetProperty();prop.SetColor(.69,.50,.29);prop.SetEdgeVisibility(False);prop.SetEdgeColor(.23,.15,.08);prop.SetLineWidth(1.2);prop.SetInterpolationToPhong();ren.AddActor(actor)
 edges=vtk.vtkFeatureEdges();edges.SetInputConnection(reader.GetOutputPort());edges.BoundaryEdgesOn();edges.FeatureEdgesOn();edges.SetFeatureAngle(30);edges.ManifoldEdgesOff();edges.NonManifoldEdgesOff()
 line_mapper=vtk.vtkPolyDataMapper();line_mapper.SetInputConnection(edges.GetOutputPort());line_mapper.ScalarVisibilityOff();lines=vtk.vtkActor();lines.SetMapper(line_mapper);lines.GetProperty().SetColor(.23,.15,.08);lines.GetProperty().SetLineWidth(1.2);ren.AddActor(lines)
 cam=ren.GetActiveCamera();cam.SetFocalPoint(L/2,W/2,H*.4);cam.SetViewUp(0,0,1)
 if index==0:cam.SetPosition(L*1.1,-W*2.8,H*3.3)
 else:cam.SetPosition(L/2,W/2,H+1);cam.SetViewUp(0,1,0);cam.ParallelProjectionOn()
 cam.ParallelProjectionOn();cam.SetParallelScale(L*.70);cam.SetClippingRange(.001,10)
 title=vtk.vtkTextActor();title.SetInput('IMAGE-BASED CAD ESTIMATE' if index==0 else 'TOP VIEW / THREE COMPARTMENTS');title.SetPosition(24,820);title.GetTextProperty().SetColor(.03,.08,.13);title.GetTextProperty().SetFontSize(24);ren.AddViewProp(title)
 info=vtk.vtkTextActor();info.SetInput(f'{L*1000:.0f} x {W*1000:.0f} x {H*1000:.0f} mm\nWall / bottom / dividers: 2.5 mm ASSUMED\nMetric: OAK + front wrist + 40 mm printed reference\nRear wrist: visual check, no depth data');info.SetPosition(24,24);info.GetTextProperty().SetColor(.03,.08,.13);info.GetTextProperty().SetFontSize(18);ren.AddViewProp(info)
window.Render();shot=vtk.vtkWindowToImageFilter();shot.SetInput(window);shot.Update();writer=vtk.vtkPNGWriter();writer.SetFileName(str(p/'cad-preview.png'));writer.SetInputConnection(shot.GetOutputPort());writer.Write();print(p/'cad-preview.png')

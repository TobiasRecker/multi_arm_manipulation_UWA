"""Render the saved carton mesh and photo-textured GLB; no devices/ROS."""
import argparse
import json
from pathlib import Path

import vtk


def render(directory):
    result=json.loads((directory/'carton_model.json').read_text())
    L,W,H=[result[k] for k in ('length_m','width_m','height_m')]
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(1800,1100)
    importer=vtk.vtkGLTFImporter();importer.SetFileName(str(directory/'cad/carton_textured.glb'))
    importer.SetRenderWindow(window);importer.Update()
    original=window.GetRenderers().GetFirstRenderer();actors=list(original.GetActors())
    if len(actors)<5:raise ValueError('Textured GLB import incomplete')
    window.RemoveRenderer(original)
    reader=vtk.vtkSTLReader();reader.SetFileName(str(directory/'cad/carton.stl'));reader.Update()
    for i in range(2):
        ren=vtk.vtkRenderer();ren.SetViewport(i/2,0,(i+1)/2,1);ren.SetBackground(.91,.93,.96);window.AddRenderer(ren)
        if i==0:
            for actor in actors:
                prop=actor.GetProperty();texture=prop.GetTexture('albedoTex')
                if texture:
                    # Explicitly preserve the photo when using simple lighting.
                    prop.RemoveTexture('albedoTex');actor.SetTexture(texture)
                prop.SetInterpolationToFlat();prop.SetAmbient(.72);prop.SetDiffuse(.28)
                ren.AddActor(actor)
        else:
            mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(reader.GetOutputPort())
            actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(.73,.55,.33);ren.AddActor(actor)
            edges=vtk.vtkFeatureEdges();edges.SetInputConnection(reader.GetOutputPort());edges.SetFeatureAngle(30)
            edges.BoundaryEdgesOn();edges.FeatureEdgesOn();edges.ManifoldEdgesOff();edges.NonManifoldEdgesOff()
            em=vtk.vtkPolyDataMapper();em.SetInputConnection(edges.GetOutputPort());em.ScalarVisibilityOff()
            ea=vtk.vtkActor();ea.SetMapper(em);ea.GetProperty().SetColor(.24,.16,.08);ren.AddActor(ea)
        camera=ren.GetActiveCamera();camera.SetFocalPoint(L/2,W/2,H*.45)
        camera.SetViewUp(0,0,1);camera.SetPosition(L*1.8,-W*1.8,H*3)
        camera.ParallelProjectionOn();camera.SetParallelScale(L*.94);camera.SetClippingRange(.001,10)
        title=vtk.vtkTextActor();title.SetInput('PHOTO-TEXTURED MODEL' if i==0 else 'CAD GEOMETRY / VISIBLE CUTOUTS')
        title.SetPosition(26,1010);title.GetTextProperty().SetColor(.03,.07,.12);title.GetTextProperty().SetFontSize(25);ren.AddViewProp(title)
        caption=vtk.vtkTextActor();caption.SetPosition(26,34);caption.GetTextProperty().SetFontSize(19);caption.GetTextProperty().SetColor(.03,.07,.12)
        caption.SetInput(f'{L*1000:.0f} x {W*1000:.0f} x {H*1000:.0f} mm (image estimate)\n'
            'Thickness 2.5 mm ASSUMED; hidden geometry simplified\n'
            '25 photos reviewed / 20 metric views / 10 held-out views\n'
            'Absolute accuracy NOT validated; no depth data')
        ren.AddViewProp(caption)
    window.Render();snapshot=vtk.vtkWindowToImageFilter();snapshot.SetInput(window);snapshot.Update()
    writer=vtk.vtkPNGWriter();writer.SetInputConnection(snapshot.GetOutputPort());writer.SetFileName(str(directory/'carton_preview.png'));writer.Write()
    print(directory/'carton_preview.png')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args();render(args.directory.resolve())

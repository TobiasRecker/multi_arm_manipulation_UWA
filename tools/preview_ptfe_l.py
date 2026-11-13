"""Offline two-sided visual inspection of the packaged PTFE L asset."""
import argparse
import json
from pathlib import Path
import vtk


def render(asset,output):
    data=json.loads((asset/'asset.json').read_text());W,D,H=data['dimensions_m']
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(1800,1100)
    importer=vtk.vtkGLTFImporter();importer.SetRenderWindow(window);importer.SetFileName(str(asset/data['preview_mesh']));importer.Update()
    original=window.GetRenderers().GetFirstRenderer();actors=list(original.GetActors())
    if not actors:raise ValueError('Asset GLB failed to load')
    window.RemoveRenderer(original)
    for i in range(2):
        renderer=vtk.vtkRenderer();renderer.SetViewport(i/2,0,(i+1)/2,1);renderer.SetBackground(.89,.92,.95);window.AddRenderer(renderer)
        for source in actors:
            actor=vtk.vtkActor();actor.ShallowCopy(source);prop=vtk.vtkProperty();prop.DeepCopy(source.GetProperty());actor.SetProperty(prop)
            texture=prop.GetTexture('albedoTex')
            if texture:prop.RemoveTexture('albedoTex');actor.SetTexture(texture)
            prop.SetInterpolationToFlat();prop.SetAmbient(.65);prop.SetDiffuse(.35);renderer.AddActor(actor)
        camera=renderer.GetActiveCamera();camera.SetFocalPoint(W/2,D*.45,H*.45);camera.SetViewUp(0,0,1)
        camera.SetPosition(W*1.9,D*3.6,H*3.3) if i==0 else camera.SetPosition(W*1.8,-D*2.8,H*3)
        camera.ParallelProjectionOn();camera.SetParallelScale(W*.86);camera.SetClippingRange(.001,10)
        title=vtk.vtkTextActor();title.SetPosition(28,1010);title.SetInput('PTFE L ASSEMBLY / FRONT' if i==0 else 'REAR FRAME / SIMPLIFIED PROFILES')
        title.GetTextProperty().SetColor(.02,.06,.1);title.GetTextProperty().SetFontSize(25);renderer.AddViewProp(title)
        caption=vtk.vtkTextActor();caption.SetPosition(28,35);caption.GetTextProperty().SetFontSize(19);caption.GetTextProperty().SetColor(.02,.06,.1)
        caption.SetInput(f'Approx. {W*1000:.0f} x {D*1000:.0f} x {H*1000:.0f} mm\n'
            'User dimensions: PTFE 10 mm / aluminium 20 x 20 mm\n'
            'Photo textures; profile slots / tiny holes not measured\n'
            'Image estimate, no absolute accuracy validation')
        renderer.AddViewProp(caption)
    window.Render();snapshot=vtk.vtkWindowToImageFilter();snapshot.SetInput(window);snapshot.Update()
    writer=vtk.vtkPNGWriter();writer.SetInputConnection(snapshot.GetOutputPort());writer.SetFileName(str(output));writer.Write()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();render(a.asset.resolve(),a.output.resolve())

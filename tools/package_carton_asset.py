"""Freeze the reconstructed carton into a portable ROS/Gazebo visual asset.

Run in .venvs/oak-model. COLLADA and external textures work in both renderers;
the original GLB, STL and STEP are retained with source and artifact hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
import trimesh


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def package(source,output,*,basename='carton',title='Open avocado carton',source_model='carton_model.json'):
    report=json.loads((source/'cad/export.json').read_text())
    for name,digest in report['files'].items():
        if sha(source/'cad'/name)!=digest:raise ValueError('Source export hash mismatch '+name)
    model=json.loads((source/source_model).read_text())
    if sha(source/source_model)!=report['source_sha256']:raise ValueError('Source model hash mismatch')
    output.mkdir(parents=True,exist_ok=True);(output/'textures').mkdir(exist_ok=True)
    glb=report.get('visual_glb','carton_textured.glb');stl=report.get('solid_mesh','carton.stl');step=report.get('cad_step','carton.step')
    for before,after in [(glb,basename+'.glb'),(stl,basename+'.stl'),(step,basename+'.step')]:
        shutil.copyfile(source/'cad'/before,output/after)
    scene=trimesh.load(source/'cad'/glb,force='scene')
    root=ET.Element('COLLADA',xmlns='http://www.collada.org/2005/11/COLLADASchema',version='1.4.1')
    asset=ET.SubElement(root,'asset')
    for key in ('created','modified'):ET.SubElement(asset,key).text='2026-11-13T00:00:00Z'
    ET.SubElement(asset,'unit',name='meter',meter='1');ET.SubElement(asset,'up_axis').text='Z_UP'
    images=ET.SubElement(root,'library_images');effects=ET.SubElement(root,'library_effects')
    materials=ET.SubElement(root,'library_materials');geometries=ET.SubElement(root,'library_geometries')
    visual_scene=ET.SubElement(ET.SubElement(root,'library_visual_scenes'),'visual_scene',id='scene')
    vertices_all=[];triangle_count=0
    for number,name in enumerate(scene.graph.nodes_geometry):
        pose,geometry_name=scene.graph[name];geometry=scene.geometry[geometry_name]
        # All current GLB nodes are identity, but do not silently discard transforms.
        points=geometry.vertices@pose[:3,:3].T+pose[:3,3]
        normals=geometry.vertex_normals@np.linalg.inv(pose[:3,:3]);normals/=np.linalg.norm(normals,axis=1)[:,None]
        vertices_all.extend(points.tolist());triangle_count+=len(geometry.faces)
        ident=f'part_{number}';effect=ET.SubElement(effects,'effect',id=ident+'_effect')
        common=ET.SubElement(effect,'profile_COMMON');textured=hasattr(geometry.visual,'uv') and geometry.visual.uv is not None
        if textured:
            texture=f'textures/{ident}.jpg';image=ET.SubElement(images,'image',id=ident+'_image')
            ET.SubElement(image,'init_from').text=texture
            geometry.visual.material.baseColorTexture.convert('RGB').save(output/texture,quality=95)
            surface=ET.SubElement(ET.SubElement(common,'newparam',sid=ident+'_surface'),'surface',type='2D')
            ET.SubElement(surface,'init_from').text=ident+'_image'
            sampler=ET.SubElement(ET.SubElement(common,'newparam',sid=ident+'_sampler'),'sampler2D')
            ET.SubElement(sampler,'source').text=ident+'_surface'
            for key in ('minfilter','magfilter'):ET.SubElement(sampler,key).text='LINEAR'
        lambert=ET.SubElement(ET.SubElement(common,'technique',sid='common'),'lambert')
        ET.SubElement(ET.SubElement(lambert,'emission'),'color').text='0 0 0 1'
        ET.SubElement(ET.SubElement(lambert,'ambient'),'color').text='1 1 1 1'
        diffuse=ET.SubElement(lambert,'diffuse')
        if textured:ET.SubElement(diffuse,'texture',texture=ident+'_sampler',texcoord='UVMap')
        else:
            # Preserve the source material for non-carton assets as well.
            material=getattr(geometry.visual,'material',None)
            color=getattr(material,'baseColorFactor',None)
            if color is None:color=np.asarray(geometry.visual.vertex_colors)[0]
            color=np.asarray(color,dtype=float)/255.0
            ET.SubElement(diffuse,'color').text=' '.join(f'{v:.9g}' for v in color)
        ET.SubElement(ET.SubElement(materials,'material',id=ident+'_material'),'instance_effect',url='#'+ident+'_effect')
        mesh=ET.SubElement(ET.SubElement(geometries,'geometry',id=ident),'mesh')
        def source_array(suffix,values,parameters):
            values=np.asarray(values);name=ident+'_'+suffix
            src=ET.SubElement(mesh,'source',id=name)
            ET.SubElement(src,'float_array',id=name+'_array',count=str(values.size)).text=' '.join(f'{v:.10g}' for v in values.ravel())
            accessor=ET.SubElement(ET.SubElement(src,'technique_common'),'accessor',source='#'+name+'_array',count=str(len(values)),stride=str(len(parameters)))
            for parameter in parameters:ET.SubElement(accessor,'param',name=parameter,type='float')
        source_array('positions',points,['X','Y','Z']);source_array('normals',normals,['X','Y','Z'])
        if textured:source_array('uv',geometry.visual.uv,['S','T'])
        ET.SubElement(ET.SubElement(mesh,'vertices',id=ident+'_vertices'),'input',semantic='POSITION',source='#'+ident+'_positions')
        triangles=ET.SubElement(mesh,'triangles',count=str(len(geometry.faces)),material='material')
        ET.SubElement(triangles,'input',semantic='VERTEX',source='#'+ident+'_vertices',offset='0')
        ET.SubElement(triangles,'input',semantic='NORMAL',source='#'+ident+'_normals',offset='1')
        if textured:ET.SubElement(triangles,'input',semantic='TEXCOORD',source='#'+ident+'_uv',offset='2',set='0')
        ET.SubElement(triangles,'p').text=' '.join(str(int(v)) for face in geometry.faces for v in face for _ in range(3 if textured else 2))
        node=ET.SubElement(visual_scene,'node',id=ident+'_node')
        instance=ET.SubElement(node,'instance_geometry',url='#'+ident)
        material=ET.SubElement(ET.SubElement(ET.SubElement(instance,'bind_material'),'technique_common'),'instance_material',symbol='material',target='#'+ident+'_material')
        if textured:ET.SubElement(material,'bind_vertex_input',semantic='UVMap',input_semantic='TEXCOORD',input_set='0')
    ET.SubElement(ET.SubElement(root,'scene'),'instance_visual_scene',url='#scene')
    ET.indent(root);ET.ElementTree(root).write(output/(basename+'.dae'),encoding='utf-8',xml_declaration=True)
    dimensions=np.array(model['dimensions_m'] if 'dimensions_m' in model else [model[k] for k in ('length_m','width_m','height_m')])
    if not np.allclose(np.ptp(vertices_all,axis=0),dimensions,atol=1e-7):raise ValueError('DAE extent/unit mismatch')
    manifest=dict(schema=1,asset_id=output.name,title=title,version=1,
        units='m',up_axis='Z',visual_mesh=basename+'.dae',preview_mesh=basename+'.glb',solid_mesh=basename+'.stl',cad_mm=basename+'.step',
        dimensions_m=dimensions.tolist(),triangle_count=triangle_count,
        reference_pose=dict(frame='right_charuco',T_frame_object=model['T_board_object']),
        quality=dict(status='image_based_estimate',measured_accuracy_validated=False,
            wall_thickness_m=model.get('plate_thickness_m',model.get('wall_thickness_m',.0025)),
            wall_thickness_measured=False,known_dimensions_source=model.get('measured_dimensions_source','thickness assumed')),
        use='visual_only; not automatically a planning or physics obstacle',
        provenance=dict(date='2026-11-13',source='UWA four-arm/OAK image-only scan',
            source_model_sha256=sha(source/source_model),source_export_sha256=sha(source/'cad/export.json'),
            dataset_sha256=json.loads((source/'provenance.json').read_text())['dataset_sha256']),
        files={p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='asset.json'})
    (output/'asset.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(asset=str(output),dimensions_m=dimensions.tolist(),triangles=triangle_count),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();package(args.source.resolve(),args.output.resolve())

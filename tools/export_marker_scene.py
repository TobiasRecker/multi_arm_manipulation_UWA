#!/usr/bin/env python3
"""Export the accepted marker STEP assembly to two portable visual scene assets."""
import hashlib
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

REPO = Path(__file__).resolve().parents[1]
CAD = REPO / 'hardware/marker_tool'
AST = REPO / 'uwa_cell_description/assets'
TIP_HEIGHT_MM = 10.5


def tint(parent, name, value):
    ET.SubElement(ET.SubElement(parent, name), 'color').text = value


def dae_mesh(parts, path):
    root = ET.Element('COLLADA', xmlns='http://www.collada.org/2005/11/COLLADASchema',
                      version='1.4.1')
    asset = ET.SubElement(root, 'asset')
    for prop in ('created', 'modified'):
        ET.SubElement(asset, prop).text = '2026-11-19T00:00:00Z'
    ET.SubElement(asset,'unit',name='meter',meter='1')
    ET.SubElement(asset,'up_axis').text = 'Z_UP'
    effects = ET.SubElement(root,'library_effects')
    materials = ET.SubElement(root,'library_materials')
    geometry = ET.SubElement(root,'library_geometries')
    scene = ET.SubElement(ET.SubElement(root,'library_visual_scenes'),'visual_scene',id='scene')
    for name, mesh, rgb in parts:
        effect = ET.SubElement(effects,'effect',id=name+'_effect')
        common = ET.SubElement(effect,'profile_COMMON')
        lambert = ET.SubElement(ET.SubElement(common,'technique',sid='common'),'lambert')
        tint(lambert, 'diffuse', rgb + ' 1')
        tint(lambert, 'ambient', '.45 .45 .45 1')
        material = ET.SubElement(materials,'material',id=name+'_material')
        ET.SubElement(material,'instance_effect',url='#'+name+'_effect')
        out = ET.SubElement(ET.SubElement(geometry,'geometry',id=name),'mesh')
        for role, data in [('positions',mesh.vertices),('normals',mesh.face_normals)]:
            ident = name + '_' + role
            src = ET.SubElement(out,'source',id=ident)
            ET.SubElement(src,'float_array',id=ident+'_array',count=str(data.size)).text = (
                ' '.join(f'{v:.8g}' for v in data.ravel()))
            accessor = ET.SubElement(ET.SubElement(src,'technique_common'),'accessor',
                                     source='#'+ident+'_array',count=str(len(data)),stride='3')
            for axis in 'XYZ':
                ET.SubElement(accessor,'param',name=axis,type='float')
        v = ET.SubElement(out,'vertices',id=name+'_vertices')
        ET.SubElement(v,'input',semantic='POSITION',source='#'+name+'_positions')
        faces = ET.SubElement(out,'triangles',count=str(len(mesh.faces)),material='surface')
        ET.SubElement(faces,'input',semantic='VERTEX',source='#'+name+'_vertices',offset='0')
        ET.SubElement(faces,'input',semantic='NORMAL',source='#'+name+'_normals',offset='1')
        ET.SubElement(faces,'p').text = ' '.join(f'{v} {i}' for i,face in enumerate(mesh.faces) for v in face)
        node = ET.SubElement(scene,'node',id=name+'_node')
        part = ET.SubElement(node,'instance_geometry',url='#'+name)
        binding = ET.SubElement(ET.SubElement(part,'bind_material'),'technique_common')
        ET.SubElement(binding,'instance_material',symbol='surface',target='#'+name+'_material')
    ET.SubElement(ET.SubElement(root,'scene'),'instance_visual_scene',url='#scene')
    ET.indent(root)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def export(asset_id, parts, z_m, source):
    directory = AST / asset_id
    directory.mkdir(exist_ok=True)
    path = directory / 'model.dae'
    dae_mesh(parts, path)
    pose = np.eye(4)
    pose[:3,3] = [-.27, -.40, z_m]
    manifest = dict(
        schema=1, asset_id=asset_id, units='m', up_axis='Z', visual_mesh=path.name,
        dimensions_m=np.ptp(np.vstack([m.vertices for _,m,_ in parts]),axis=0).tolist(),
        triangle_count=sum(len(m.faces) for _,m,_ in parts),
        reference_pose=dict(frame='left_table_top', T_frame_object=pose.tolist()),
        quality=dict(status='cad_with_provisional_tabletop_placement',
                     measured_accuracy_validated=False),
        use='visual_only',
        provenance=dict(source=str(source.relative_to(REPO)),
                        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                        marker_body='Approximate profile from 125 mm overall, 20/19 mm barrel measurements'),
        files={path.name:hashlib.sha256(path.read_bytes()).hexdigest()},
    )
    (directory/'asset.json').write_text(json.dumps(manifest,indent=2)+'\n')


def main():
    source = CAD / 'marker-werkzeug.step'
    reader = STEPControl_Reader()
    if reader.ReadFile(str(source)) != IFSelect_RetDone or not reader.TransferRoots():
        raise RuntimeError('Could not import the marker CAD assembly')
    solids = TopExp_Explorer(reader.OneShape(), TopAbs_SOLID)
    bodies = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'solid.stl'
        while solids.More():
            solid = solids.Current()
            bbox = Bnd_Box()
            BRepBndLib.AddOptimal_s(solid, bbox)
            mesher = BRepMesh_IncrementalMesh(solid, .12, False, .22, False)
            if not mesher.IsDone() or not StlAPI_Writer().Write(solid, str(path)):
                raise RuntimeError('Could not mesh the marker CAD assembly')
            mesh = trimesh.load_mesh(path)
            bodies.append((bbox.CornerMin().Z(), bbox.CornerMin().Y(), mesh))
            solids.Next()
    if len(bodies) != 3:
        raise ValueError('Expected the dock and two adapter halves')
    bodies.sort(key=lambda b:(b[0],b[1]))
    dock = bodies[0][2].apply_scale(.001)
    adapter = []
    for i, (_, _, mesh) in enumerate(bodies[1:]):
        mesh.apply_translation([0,0,-TIP_HEIGHT_MM]).apply_scale(.001)
        adapter.append((f'adapter_{i}', mesh, '.88 .48 .08'))
    # Profile starts at the nominal tip. This approximation is visual, not a tip calibration.
    barrel = trimesh.creation.revolve(np.asarray([(0,4), (3,4), (6.8,8), (9.4,15),
                                                   (9.5,90), (10,115), (10,125), (0,125)])*.001)
    tip = trimesh.creation.revolve(np.asarray([(0,0),(1.2,0),(2.2,1.5),(2.2,4.1),(0,4.1)])*.001)
    export('marker_station_v1',[('dock',dock,'.08 .38 .46')],0,source)
    export('cos_marker_docked_v1',adapter+[('barrel',barrel,'.92 .92 .88'),
                                          ('tip',tip,'.10 .10 .10')],TIP_HEIGHT_MM*.001,source)


if __name__ == '__main__':
    main()

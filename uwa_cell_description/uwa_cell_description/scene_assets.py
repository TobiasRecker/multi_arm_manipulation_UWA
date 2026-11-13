"""Portable visual assets and a single pose shared by Gazebo, TF and RViz."""
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation


def transform(xyz, rpy):
    result=np.eye(4);result[:3,:3]=Rotation.from_euler('xyz',rpy).as_matrix();result[:3,3]=xyz
    return result


def rigid(value):
    matrix=np.asarray(value,dtype=float)
    if (matrix.shape!=(4,4) or not np.isfinite(matrix).all() or
            not np.allclose(matrix[3],[0,0,0,1],atol=1e-9) or
            not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-8) or
            not np.isclose(np.linalg.det(matrix[:3,:3]),1,atol=1e-8)):
        raise ValueError('Asset pose must be a finite right-handed rigid transform')
    return matrix


def anchor_pose(layout,frame):
    if frame=='world':return np.eye(4)
    for table_id,table in layout['tables'].items():
        world_top=transform(table['xyz'],table['rpy'])@transform([0,0,table['height']],[0,0,0])
        if frame==table_id+'_table_top':return world_top
        if frame==table_id+'_charuco':
            config=layout['charuco'];board=config['boards'][table_id]
            if not config['enabled']:raise ValueError('Scene asset references disabled ChArUco frame')
            return (world_top@transform(board['center_xyz'],[0,0,board['yaw']])@
                transform([-config['squares_x']*config['square_length']/2,
                            config['squares_y']*config['square_length']/2,0],[np.pi,0,0]))
    raise ValueError('Unsupported scene asset anchor '+str(frame))


def instances(layout, share=None):
    if share is None:
        from ament_index_python.packages import get_package_share_directory
        share=Path(get_package_share_directory('uwa_cell_description'))
    share=Path(share).resolve();result=[];names=set()
    entries=layout.get('scene_objects',[])
    if not isinstance(entries,list):raise ValueError('scene_objects must be a list')
    for item in entries:
        if (not isinstance(item,dict) or set(item)-{'id','asset','enabled','anchor_frame','T_anchor_object'}):
            raise ValueError('Invalid scene object configuration')
        for key in ('id','asset'):
            if not re.fullmatch(r'[a-z][a-z0-9_]*',str(item.get(key,''))):raise ValueError('Invalid asset '+key)
        if item['id'] in names:raise ValueError('Duplicate scene object ID')
        names.add(item['id'])
        if not isinstance(item.get('enabled',True),bool):raise ValueError('Asset enabled must be boolean')
        if not item.get('enabled',True):continue
        directory=(share/'assets'/item['asset']).resolve();manifest=json.loads((directory/'asset.json').read_text())
        if manifest.get('units')!='m' or manifest.get('up_axis')!='Z' or manifest['asset_id']!=item['asset']:
            raise ValueError('Asset identity/units/axes mismatch')
        for name,digest in manifest['files'].items():
            relative=Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Asset file path must stay relative to its directory')
            # CMake --symlink-install uses real directories with symlinked
            # individual files. Their resolved target may be in src; integrity
            # is pinned by the manifest hash, not by a false realpath boundary.
            path=directory/relative
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError('Asset file integrity mismatch: '+name)
        reference=manifest['reference_pose'];frame=item.get('anchor_frame',reference['frame'])
        if frame!=reference['frame'] and 'T_anchor_object' not in item:
            raise ValueError('A different anchor requires an explicit T_anchor_object')
        relative=rigid(item.get('T_anchor_object',reference['T_frame_object']))
        pose=anchor_pose(layout,frame)@relative
        mesh_name=manifest['visual_mesh']
        if mesh_name not in manifest['files']:raise ValueError('Visual mesh is not hash-pinned')
        mesh=(directory/mesh_name).resolve()
        result.append(dict(id=item['id'],model_name='uwa_asset_'+item['id'],frame='asset/'+item['id'],
            anchor_frame=frame,T_anchor_object=relative,T_world_object=pose,
            manifest=manifest,mesh_file=mesh,mesh_resource=f"package://uwa_cell_description/assets/{item['asset']}/{manifest['visual_mesh']}"))
    return result


def model_sdf(instance):
    root=ET.Element('sdf',version='1.9');model=ET.SubElement(root,'model',name=instance['model_name'])
    ET.SubElement(model,'static').text='true';pose=instance['T_world_object']
    ET.SubElement(model,'pose').text=' '.join(map(str,[*pose[:3,3],*Rotation.from_matrix(pose[:3,:3]).as_euler('xyz')]))
    link=ET.SubElement(model,'link',name='visual');visual=ET.SubElement(link,'visual',name='textured_carton')
    mesh=ET.SubElement(ET.SubElement(visual,'geometry'),'mesh')
    ET.SubElement(mesh,'uri').text=instance['mesh_file'].as_uri();ET.SubElement(mesh,'scale').text='1 1 1'
    ET.SubElement(visual,'cast_shadows').text='true'
    # Embedded DAE materials; no SDF colour override, collision or physics mass.
    return ET.tostring(root,encoding='unicode')

"""Metric/texture integrity and the common board->world pose of visual assets."""
from copy import deepcopy
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from uwa_cell_description.configuration import load_layout
from uwa_cell_description.scene_assets import instances, anchor_pose, model_sdf, rigid, transform
from uwa_cell_gazebo.charuco import table_board_transform

SHARE=Path(__file__).resolve().parents[2]/'uwa_cell_description'
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}


def test_textured_asset_is_meter_scaled_and_has_all_relative_textures():
    item=instances(load_layout(),SHARE)[0];manifest=item['manifest']
    dae=ET.parse(item['mesh_file']);root=dae.getroot()
    assert root.find('c:asset/c:unit',NS).get('meter')=='1'
    assert root.findtext('c:asset/c:up_axis',namespaces=NS)=='Z_UP'
    images=root.findall('c:library_images/c:image/c:init_from',NS)
    assert len(images)==4
    for image in images:
        assert not Path(image.text).is_absolute()
        assert (item['mesh_file'].parent/image.text).is_file()
    positions=[];triangles=0
    for mesh in root.findall('c:library_geometries/c:geometry/c:mesh',NS):
        array=next(s.find('c:float_array',NS) for s in mesh.findall('c:source',NS) if s.get('id').endswith('_positions'))
        positions.extend(np.fromstring(array.text,sep=' ').reshape(-1,3))
        triangle=mesh.find('c:triangles',NS);count=int(triangle.get('count'));triangles+=count
        inputs=triangle.findall('c:input',NS);indices=np.fromstring(triangle.findtext('c:p',namespaces=NS),sep=' ',dtype=int)
        assert len(indices)==count*3*len(inputs)
        assert {i.get('semantic') for i in inputs}>={'VERTEX','NORMAL'}
    np.testing.assert_allclose(np.ptp(positions,axis=0),manifest['dimensions_m'],atol=1e-8)
    assert triangles==manifest['triangle_count']==292
    assert not manifest['quality']['measured_accuracy_validated']


def test_pose_follows_rotated_table_board_and_stays_upright_between_tables():
    layout=load_layout();item=instances(layout,SHARE)[0];table=layout['tables']['right']
    expected=(transform(table['xyz'],table['rpy'])@transform([0,0,table['height']],[0,0,0])@
              table_board_transform(layout['charuco'],'right')@item['T_anchor_object'])
    np.testing.assert_allclose(item['T_world_object'],expected,atol=1e-12)
    np.testing.assert_allclose(expected[:3,2],[0,0,1],atol=1e-12)
    dimensions=item['manifest']['dimensions_m'];centre=expected[:3,:3]@(np.array(dimensions)/2)+expected[:3,3]
    assert abs(centre[0])<.03 and abs(centre[1])<.03
    altered=deepcopy(layout);altered['tables']['right']['rpy'][2]=.7
    altered['charuco']['boards']['right']['yaw']=.4
    item2=instances(altered,SHARE)[0]
    np.testing.assert_allclose(np.linalg.inv(anchor_pose(altered,'right_charuco'))@item2['T_world_object'],item['T_anchor_object'],atol=1e-12)
    sdf=ET.fromstring(model_sdf(item));assert sdf.findtext('model/static')=='true'
    assert sdf.find('.//collision') is None
    assert sdf.find('.//plugin') is None
    values=np.fromstring(sdf.findtext('model/pose'),sep=' ')
    np.testing.assert_allclose(transform(values[:3],values[3:]),expected,atol=1e-12)


def test_symlink_install_resolves_asset_directory_before_integrity_checks(tmp_path):
    (tmp_path/'assets').symlink_to(SHARE/'assets',target_is_directory=True)
    assert instances(load_layout(),tmp_path)[0]['mesh_file']==(SHARE/'assets/carton_avocado_v1/carton.dae').resolve()


def test_cmake_install_with_individually_symlinked_asset_files(tmp_path):
    for source in (SHARE/'assets').rglob('*'):
        target=tmp_path/'assets'/source.relative_to(SHARE/'assets')
        if source.is_dir():target.mkdir(parents=True,exist_ok=True)
        else:target.symlink_to(source)
    assert instances(load_layout(),tmp_path)[0]['manifest']['asset_id']=='carton_avocado_v1'


def test_changed_asset_hash_invalid_pose_and_implicit_reanchor_are_rejected(tmp_path):
    folder=tmp_path/'assets';shutil.copytree(SHARE/'assets',folder)
    texture=next(folder.glob('carton_avocado_v1/textures/*.jpg'));texture.write_bytes(b'changed')
    with pytest.raises(ValueError,match='integrity'):instances(load_layout(),tmp_path)
    for bad in [np.diag([1,1,-1,1]),np.diag([2,1,1,1]),np.full((4,4),np.nan)]:
        with pytest.raises(ValueError,match='rigid'):rigid(bad)
    layout=load_layout();layout['scene_objects'][0]['anchor_frame']='world'
    with pytest.raises(ValueError,match='different anchor'):instances(layout,SHARE)


def test_ptfe_asset_uses_own_geometry_materials_and_board_pose():
    layout=deepcopy(load_layout())
    layout['scene_objects']=[dict(id='ptfe_l',asset='ptfe_l_assembly_v1')]
    item=instances(layout,SHARE)[0];manifest=item['manifest']
    root=ET.parse(item['mesh_file']).getroot()
    points=[]
    for source in root.findall('.//c:source',NS):
        if source.get('id','').endswith('_positions'):
            points.extend(np.fromstring(source.findtext('c:float_array',namespaces=NS),sep=' ').reshape(-1,3))
    np.testing.assert_allclose(np.ptp(points,axis=0),manifest['dimensions_m'],atol=1e-8)
    assert len(root.findall('c:library_images/c:image',NS))==5
    colors=[np.fromstring(c.text,sep=' ') for c in root.findall('.//c:diffuse/c:color',NS)]
    # White PTFE and grey aluminium must survive GLB -> ROS DAE export.
    assert len(colors)==2 and all(np.ptp(c[:3])<.1 for c in colors)
    np.testing.assert_allclose(item['T_world_object'][:3,2],[0,0,1],atol=1e-8)
    assert manifest['quality']['wall_thickness_m']==.01
    assert not manifest['quality']['measured_accuracy_validated']
    sdf=ET.fromstring(model_sdf(item))
    assert sdf.find('.//collision') is None

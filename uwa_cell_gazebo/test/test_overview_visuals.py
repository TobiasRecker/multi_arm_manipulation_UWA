"""CAD scale, shared mesh poses and a ground-supported vertical stand."""
import hashlib,json,struct
from pathlib import Path
from urllib.parse import unquote,urlparse
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
from ament_index_python.packages import get_package_share_directory
from visualization_msgs.msg import Marker
from uwa_cell_gazebo.configuration import load_layout
from uwa_cell_gazebo.overview import camera_config,model_sdf,transforms
from uwa_cell_gazebo.overview_visuals import MESH,camera_and_tripod,sdf_visual_markers


def matrix(text):
    values=np.fromstring(text or '0 0 0 0 0 0',sep=' ');pose=np.eye(4)
    pose[:3,3]=values[:3];pose[:3,:3]=Rotation.from_euler('xyz',values[3:]).as_matrix()
    return pose


def test_installed_native_cad_mesh_is_in_metres_and_behind_the_optical_origin():
    folder=Path(get_package_share_directory('uwa_cell_description'))/Path(MESH).parent
    provenance=json.loads((folder/'provenance.json').read_text())
    assert provenance['mesh_length_unit']=='metre'
    for name,meta in provenance['assets'].items():
        content=(folder/name).read_bytes();count=struct.unpack('<I',content[80:84])[0]
        assert len(content)==84+50*count and count==meta['triangles_after']
        assert hashlib.sha256(content).hexdigest()==meta['sha256']
        triangles=np.frombuffer(content[84:],dtype=np.dtype([('normal','<f4',(3,)),('points','<f4',(3,3)),('attr','<u2')]))['points']
        assert np.isfinite(triangles).all()
        vertices=triangles.reshape(-1,3)
        assert vertices[:,0].max()<0  # no camera housing in front of its sensor
        assert np.ptp(vertices,axis=0).max()<.25


def test_rviz_and_gazebo_share_every_visual_pose_and_geometry():
    cfg=camera_config(load_layout());optical=transforms(cfg)[1].copy();sdf=model_sdf(cfg)
    markers=sdf_visual_markers(sdf);visuals=camera_and_tripod(transforms(cfg)[0])
    assert len(markers)==len(visuals) and len({m.id for m in markers})==len(markers)
    assert sum(m.type==Marker.MESH_RESOURCE for m in markers)==2
    assert sum(m.type==Marker.CYLINDER for m in markers)>=18
    for marker,visual in zip(markers,visuals):
        np.testing.assert_allclose([marker.pose.position.x,marker.pose.position.y,marker.pose.position.z],visual.pose[:3,3],atol=1e-10)
        q=marker.pose.orientation
        np.testing.assert_allclose(Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix(),visual.pose[:3,:3],atol=1e-10)
        if marker.type==Marker.MESH_RESOURCE:
            assert Path(unquote(urlparse(marker.mesh_resource).path)).is_file()
            assert [marker.scale.x,marker.scale.y,marker.scale.z]==[1.,1.,1.]
    np.testing.assert_array_equal(transforms(cfg)[1],optical)
    root=ET.fromstring(sdf)
    assert not root.findall('.//collision') and not root.findall('.//plugin')
    np.testing.assert_allclose(matrix(root.findtext('model/link/pose')),transforms(cfg)[0],atol=1e-12)


def test_tripod_stays_on_ground_below_actual_registered_pose_not_legacy_xyz():
    cfg=camera_config(load_layout());optical=transforms(cfg)[1].copy();optical[:3,3]+=[.2,-.15,-.1]
    cfg['world_optical']=optical.tolist();cfg['xyz']=[10.,10.,10.]
    visuals=camera_and_tripod(transforms(cfg)[0]);feet=[v for v in visuals if v.name.endswith('rubber_foot')]
    assert len(feet)==3
    centre=np.mean([v.pose[:3,3] for v in feet],axis=0)
    assert np.linalg.norm(centre[:2]-optical[:2,3])<.12
    for foot in feet:
        assert abs(foot.pose[2,3]-foot.size[2]/2)<1e-10
        np.testing.assert_allclose(foot.pose[:3,2],[0,0,1.],atol=1e-12)

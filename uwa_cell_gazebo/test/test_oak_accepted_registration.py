"""The accepted preliminary pose has one frame convention and remains world-fixed."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from uwa_cell_description.calibration_profile import load_profile, apply_layout
from uwa_cell_description.overview_profile import R_SENSOR_OPTICAL
from uwa_cell_gazebo.configuration import load_layout, nominal_layout_path, render_description
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_gazebo.overview import camera_config, transforms, model_sdf, intrinsic, project


def source():
    return Path(__file__).resolve().parents[2]/'uwa_cell_description/config/calibration/hardware_20261112_v3'


def measured():
    profile = load_profile(source()/'profile.json')
    return apply_layout(load_layout(nominal_layout_path()),profile), profile


def test_fk_derivation_uses_measured_snapshot_and_correct_inverse(tmp_path):
    layout,profile = measured()
    overview = profile['overview_camera']
    state = json.loads((source()/'oak_reference_state.json').read_text())['snapshot']
    joints = dict(zip(state['joint_names'],state['positions']))
    description = render_description(layout,tmp_path)[0]
    fk = Chain(description,'world','right_front_wrist_camera_optical_frame').forward(joints)
    relative = np.asarray(overview['relative_result']['T_oak_optical_right_front_optical'])
    expected = fk @ np.linalg.inv(relative)
    actual = transforms(camera_config(layout))[1]
    np.testing.assert_allclose(actual,expected,atol=1e-10)
    assert actual[2,3] <= 2 and actual[0,3] > .8
    assert profile['robots']['right_front']['camera']['passed'] is False
    assert overview['relative_result']['passed'] is False
    assert overview['quality_status']=='operator_accepted_preliminary'


def test_table_changes_do_not_move_external_tripod_or_change_arm_initial_positions():
    nominal = load_layout(nominal_layout_path())
    original,profile = measured()
    moved = deepcopy(nominal)
    moved['tables']['right']['xyz']=[.9,-.2,.1]
    moved['tables']['right']['rpy'][2]=.3
    moved = apply_layout(moved,profile)
    np.testing.assert_array_equal(transforms(camera_config(moved))[1],transforms(camera_config(original))[1])
    for rid in nominal['robots']:
        assert original['robots'][rid]['initial_positions']==nominal['robots'][rid]['initial_positions']
        assert original['robots'][rid]['mount_xyz']==nominal['robots'][rid]['mount_xyz']
        assert original['robots'][rid]['mount_rpy']==nominal['robots'][rid]['mount_rpy']


def test_sdf_and_ros_optical_pose_intrinsics_and_projection_agree():
    layout,profile = measured();cfg=camera_config(layout)
    root=ET.fromstring(model_sdf(cfg));values=np.fromstring(root.findtext('model/link/pose'),sep=' ')
    sdf_pose=np.eye(4);sdf_pose[:3,3]=values[:3];sdf_pose[:3,:3]=Rotation.from_euler('xyz',values[3:]).as_matrix()
    sensor,optical=transforms(cfg)
    np.testing.assert_allclose(sdf_pose,sensor,atol=1e-12)
    np.testing.assert_allclose(sensor[:3,:3]@R_SENSOR_OPTICAL,optical[:3,:3],atol=1e-12)
    camera=root.find('model/link/sensor/camera');k=intrinsic(cfg)
    for key,value in [('fx',k[0,0]),('fy',k[1,1]),('cx',k[0,2]),('cy',k[1,2])]:
        assert float(camera.findtext('lens/intrinsics/'+key))==value
    assert cfg['real_frame_id']=='real_oak4_rgb_optical_frame'
    local=np.array([[0.,0.,1.],[.2,-.1,1.]])
    world=local@optical[:3,:3].T+optical[:3,3]
    actual,depth=project(world,cfg)
    expected=cv2.projectPoints(local,np.zeros(3),np.zeros(3),k,np.array(cfg['distortion']))[0].reshape(-1,2)
    np.testing.assert_allclose(actual,expected,atol=1e-10)
    np.testing.assert_allclose(depth,1.)
    assert cfg['simulation_approximation']['max_error_at_8000x6000_px']<8
    assert cfg['distortion']==[0.]*5 and camera.find('distortion') is None
    assert len(profile['overview_camera']['factory']['distortion'])==14


def test_preliminary_acceptance_is_sha_bound_and_cannot_hide_bad_geometry(tmp_path):
    p=tmp_path/'profile';shutil.copytree(source(),p)
    path=p/'profile.json';data=json.loads(path.read_text())
    del data['overview_camera']['operator_acceptance']
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='explicit'):load_profile(path)
    data=json.loads((source()/'profile.json').read_text())
    data['overview_camera']['operator_acceptance']['extrinsics']['source_sha256']='0'*64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='exact artifact'):load_profile(path)
    data=json.loads((source()/'profile.json').read_text())
    registration=p/'oak_registration.json';value=json.loads(registration.read_text())
    value['T_world_oak_optical'][0][3]+=.1
    registration.write_text(json.dumps(value));sha=hashlib.sha256(registration.read_bytes()).hexdigest()
    data['overview_camera']['extrinsics']['sha256']=sha
    data['overview_camera']['operator_acceptance']['extrinsics']['source_sha256']=sha
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='derivation'):load_profile(path)


def test_preexisting_robot_calibrations_remain_byte_identical():
    new=source();old=new.with_name('hardware_20261112_v2')
    profile=json.loads((new/'profile.json').read_text());previous=json.loads((old/'profile.json').read_text())
    assert profile['robots']==previous['robots']
    for rid,arm in previous['robots'].items():
        for part in ('kinematics','intrinsics','handeye'):
            assert (new/arm[part]['file']).read_bytes()==(old/arm[part]['file']).read_bytes()

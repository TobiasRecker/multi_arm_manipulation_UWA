"""Measured optics, nominal world anchors, and consistent consumer kinematics."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from uwa_cell_gazebo.calibration_profile import load_profile
from uwa_cell_gazebo.configuration import load_layout, nominal_layout_path, render_description
from uwa_cell_gazebo.charuco_views import Chain


def test_measured_model_preserves_world_anchors_and_housing(tmp_path):
    nominal = load_layout(nominal_layout_path())
    measured = load_layout()
    raw = render_description(nominal, tmp_path)[0]
    calibrated = render_description(measured, tmp_path)[0]
    assert nominal['tables'] == measured['tables']
    for rid in nominal['robots']:
        for key in ('mount_xyz', 'mount_rpy', 'initial_positions'):
            assert nominal['robots'][rid][key] == measured['robots'][rid][key]
        for suffix in ('base_link',):
            np.testing.assert_allclose(Chain(raw, 'world', rid+'_'+suffix).forward({}),
                                       Chain(calibrated, 'world', rid+'_'+suffix).forward({}))
        for suffix in ('wrist_camera_link', 'robotiq_85_base_link'):
            np.testing.assert_allclose(Chain(raw, rid+'_tool0', rid+'_'+suffix).forward({}),
                                       Chain(calibrated, rid+'_tool0', rid+'_'+suffix).forward({}))
    for rid in ('left_rear', 'right_rear', 'right_front'):
        arm = measured['calibration']['robots'][rid]
        np.testing.assert_allclose(Chain(calibrated, rid+'_tool0',
            rid+'_wrist_camera_optical_frame').forward({}), arm['fit']['T_tool0_camera'], atol=1e-12)
        np.testing.assert_allclose(Chain(calibrated, rid+'_base_link',
            rid+'_measured_board_frame').forward({}), arm['fit']['T_base_board'], atol=1e-12)
    front = measured['calibration']['robots']['right_front']
    assert front['quality_status']['handeye'] == 'operator_accepted_below_threshold'
    assert front['fit']['passed'] is False


def test_intrinsics_and_sensor_frame_match_measured_optical_frame(tmp_path):
    layout = load_layout()
    description = render_description(layout, tmp_path)[0]
    root = ET.fromstring(description)
    from scipy.spatial.transform import Rotation
    for rid in ('left_rear', 'right_front', 'right_rear'):
        arm = layout['calibration']['robots'][rid]
        sensor = root.find(f"gazebo[@reference='{rid}_wrist_camera_link']/sensor")
        camera = sensor.find('camera')
        k = np.asarray(arm['camera']['camera_matrix'])
        intrinsics = camera.find('lens/intrinsics')
        assert float(intrinsics.findtext('fx')) == k[0, 0]
        assert float(intrinsics.findtext('cy')) == k[1, 2]
        assert [float(camera.findtext('distortion/'+name)) for name in
                ('k1', 'k2', 'p1', 'p2', 'k3')] == arm['camera']['distortion']
        optical = Chain(description, rid+'_wrist_camera_link', rid+'_wrist_camera_optical_frame').forward({})
        pose = np.fromstring(sensor.findtext('pose'), sep=' ')
        gz_rotation = Rotation.from_euler('xyz', pose[3:]).as_matrix()
        np.testing.assert_allclose(pose[:3], optical[:3, 3], atol=1e-12)
        np.testing.assert_allclose(gz_rotation[:, 0], optical[:3, 2], atol=1e-12)
        np.testing.assert_allclose(gz_rotation[:, 1], -optical[:3, 0], atol=1e-12)


def test_corruption_and_failed_front_handeye_cannot_be_activated(tmp_path):
    layout = load_layout()
    source = Path(layout['calibration']['file']).parent
    shutil.copytree(source, tmp_path/'profile')
    path = tmp_path/'profile/profile.json'
    data = json.loads(path.read_text())
    data['robots']['right_front']['operator_acceptance'].pop('handeye')
    data['robots']['right_front']['handeye'] = data['robots']['right_front']['rejected_handeye']
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='failed independent validation'):
        load_profile(path)
    path.write_bytes((source/'profile.json').read_bytes())
    target = tmp_path/'profile/right_rear_kinematics.yaml'
    target.write_text(target.read_text()+'\n# changed\n')
    with pytest.raises(ValueError, match='checksum mismatch'):
        load_profile(path)


def test_model_snapshot_roundtrip_and_image_mode_mismatch(tmp_path):
    layout = load_layout()
    render_description(layout, tmp_path)
    again = load_layout(tmp_path/'layout.yaml')
    assert again['calibration']['sha256'] == layout['calibration']['sha256']
    assert again['robots'] == layout['robots']
    from uwa_cell_gazebo.calibration_profile import apply_layout
    changed = deepcopy(layout)
    changed['robots']['right_rear']['tools']['camera_width'] = 1280
    with pytest.raises(ValueError, match='image mode'):
        apply_layout(changed, layout['calibration'])

from copy import deepcopy
import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from uwa_cell_gazebo.configuration import load_layout
from uwa_cell_gazebo.overview import camera_config, coverage, model_sdf, project, transforms
from uwa_cell_gazebo.charuco import board_image, detect_pose


def test_world_optical_basis_target_and_default_table_coverage():
    layout = load_layout()
    cfg = camera_config(layout)
    assert cfg['xyz'][2] <= 2.0  # user's current tripod limit
    sensor, optical = transforms(cfg)
    direction = np.subtract(cfg['look_at'], cfg['xyz'])
    direction /= np.linalg.norm(direction)
    np.testing.assert_allclose(sensor[:3,0],direction,atol=1e-12)
    np.testing.assert_allclose(optical[:3,2],direction,atol=1e-12)
    np.testing.assert_allclose(optical[:3,0],-sensor[:3,1],atol=1e-12)
    pixels, depth = project([cfg['look_at']],cfg)
    np.testing.assert_allclose(pixels,[[cfg['width']/2,cfg['height']/2]])
    assert depth[0]>0
    report = coverage(layout)
    assert all(t['all_corners_in_frame'] for t in report['tables'].values())
    assert all(b['approximate_min_marker_edge_px']>=12 for b in report['boards'].values())
    assert not report['calibrated'] and not report['occlusion_checked']


def test_board_sampling_follows_moved_and_rotated_tables():
    layout = load_layout()
    original = coverage(layout)
    layout['tables']['left']['xyz'][0] -= .2
    layout['tables']['left']['rpy'][2] = .1
    moved = coverage(layout)
    assert moved['boards']['left'] != original['boards']['left']
    assert moved['boards']['right'] == original['boards']['right']


def test_sdf_stays_static_with_matching_optics_topics_and_no_controllers():
    cfg = camera_config(load_layout())
    root = ET.fromstring(model_sdf(cfg))
    assert root.findtext('model/static') == 'true'
    sensor = root.find('model/link/sensor')
    assert sensor.findtext('camera/image/width') == str(cfg['width'])
    assert sensor.findtext('frame_id') == 'oak_overview_rgb_optical_frame'
    assert sensor.findtext('topic') == '/uwa_cell/oak_overview/rgb/image_raw'
    assert root.findall('.//plugin') == []
    assert root.findall('.//collision') == []  # visual stand, not yet a planning obstacle


def test_overview_finds_small_markers_in_large_frame_without_world_pose_input():
    import cv2
    config = load_layout()['charuco']
    pattern = cv2.resize(board_image(config,'left'),(256,192),interpolation=cv2.INTER_AREA)
    image = np.full((3000,4000),255,dtype=np.uint8)
    image[1404:1596,1872:2128] = pattern
    K = np.array([[3000.,0,2000],[0,3000,1500],[0,0,1]])
    assert detect_pose(image,K,np.zeros(5),config,'left') is None
    result = detect_pose(image,K,np.zeros(5),config,'left',min_marker_perimeter_rate=.008)
    assert result is not None and result['corners']==24


@pytest.mark.parametrize('change', [dict(width=True),dict(height=0),dict(rate=100),
    dict(near=20),dict(horizontal_fov=math.pi),dict(roll=float('nan')),
    dict(xyz=[0,0,0]),dict(unknown=1)])
def test_invalid_camera_is_rejected_before_spawning(change):
    layout = load_layout()
    layout['overview_camera'].update(change)
    with pytest.raises(ValueError):
        camera_config(layout)


def test_camera_cannot_look_at_its_own_position():
    layout=load_layout()
    layout['overview_camera']['look_at']=list(layout['overview_camera']['xyz'])
    with pytest.raises(ValueError):
        camera_config(layout)

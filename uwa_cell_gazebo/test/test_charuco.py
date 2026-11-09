from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
import yaml

from uwa_cell_gazebo.charuco import (
    board_image, detect_pose, make_board, pose_error, table_board_transform, transform,
)
from uwa_cell_gazebo.charuco_views import Chain, desired_camera_pose
from uwa_cell_gazebo.configuration import ROBOT_IDS, joint_names, load_layout, render_description

LAYOUT = Path(__file__).resolve().parents[2] / 'uwa_cell_description/config/cell_layout.yaml'


@pytest.mark.parametrize('table', ['left', 'right'])
def test_rendered_perspective_recovers_pose_and_rejects_other_table(table):
    config = load_layout(LAYOUT)['charuco']
    source = board_image(config, table)
    k = np.array([[686., 0, 320], [0, 686., 240], [0, 0, 1.]])
    d = np.zeros(5)
    rvec = np.array([.2, -.12, .1])
    tvec = np.array([-.14, -.1, .65])
    w, h, margin = config['squares_x']*.04, config['squares_y']*.04, config['margin']
    objects = np.array([[-margin, -margin, 0], [w+margin, -margin, 0],
                        [w+margin, h+margin, 0], [-margin, h+margin, 0]], np.float32)
    target = cv2.projectPoints(objects, rvec, tvec, k, d)[0].reshape(-1, 2)
    original = np.array([[0, 0], [source.shape[1], 0],
                         [source.shape[1], source.shape[0]], [0, source.shape[0]]], np.float32)
    mapping = cv2.getPerspectiveTransform(original, target)
    image = cv2.warpPerspective(source, mapping, (640, 480), borderValue=180)
    detected = detect_pose(image, k, d, config, table)
    assert detected is not None
    assert detected['corners'] >= config['min_corners']
    truth = np.eye(4)
    truth[:3, :3], truth[:3, 3] = cv2.Rodrigues(rvec)[0], tvec
    error = pose_error(detected['T_camera_board'], truth)
    assert error['translation_m'] < .002
    assert error['rotation_deg'] < 1
    assert detected['reprojection_rms_px'] < .5
    other = 'right' if table == 'left' else 'left'
    assert detect_pose(image, k, d, config, other) is None
    assert detect_pose(np.full_like(image, 127), k, d, config, table) is None
    # Recover a nontrivial unknown base pose from the actual image estimate.
    table_base_truth = transform([.3, -.5, .1], [.1, -.2, .4])
    base_camera = np.linalg.inv(table_base_truth) @ table_board_transform(config, table) @ np.linalg.inv(truth)
    table_base = table_board_transform(config, table) @ np.linalg.inv(detected['T_camera_board']) @ np.linalg.inv(base_camera)
    assert pose_error(table_base, table_base_truth)['translation_m'] < .01


def test_board_frames_and_initial_camera_views_are_consistent(tmp_path):
    layout = load_layout(LAYOUT)
    text = render_description(layout, tmp_path)[0]
    root = ET.fromstring(text)
    for table in ('left', 'right'):
        actual = Chain(text, f'{table}_table_top', f'{table}_charuco').forward({})
        np.testing.assert_allclose(actual, table_board_transform(layout['charuco'], table), atol=1e-12)
        # OpenCV Z points into the paper, while the printed mesh faces tabletop +Z.
        np.testing.assert_allclose(actual[:3, 2], [0, 0, -1], atol=1e-12)
        mesh = root.find(f"link[@name='{table}_charuco_mount']/visual/geometry/mesh")
        assert Path(mesh.get('filename').removeprefix('file://')).is_file()
    for rid in ROBOT_IDS:
        robot = layout['robots'][rid]
        chain = Chain(text, f"{robot['table']}_table_top", f'{rid}_wrist_camera_optical_frame')
        actual = chain.forward(dict(zip(joint_names(rid), robot['initial_positions'])))
        np.testing.assert_allclose(actual, desired_camera_pose(layout, rid), atol=1e-8)
        camera_board = np.linalg.inv(actual) @ table_board_transform(layout['charuco'], robot['table'])
        corners = make_board(layout['charuco'], robot['table']).getChessboardCorners()
        points = corners @ camera_board[:3, :3].T + camera_board[:3, 3]
        assert np.all(points[:, 2] > 0)
        k = np.array([[686., 0, 320], [0, 686., 240], [0, 0, 1.]])
        image_points = points @ k.T
        image_points = image_points[:, :2] / image_points[:, 2:]
        assert np.all((image_points > [30, 30]) & (image_points < [610, 450]))


@pytest.mark.parametrize('change', ['overlap_ids', 'large_marker', 'outside', 'nan', 'typo'])
def test_invalid_board_settings_fail_before_launch(tmp_path, change):
    raw = yaml.safe_load(LAYOUT.read_text())
    c = raw['charuco']
    if change == 'overlap_ids':
        c['boards']['right']['marker_start'] = 0
    elif change == 'large_marker':
        c['marker_length'] = c['square_length']
    elif change == 'outside':
        c['boards']['left']['center_xyz'][0] = 3
    elif change == 'nan':
        c['boards']['left']['yaw'] = float('nan')
    else:
        c['square_lenght'] = .04
    path = tmp_path / 'bad.yaml'
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError):
        load_layout(path)


def test_boards_can_be_disabled_and_follow_table_repositioning(tmp_path):
    layout = load_layout(LAYOUT)
    layout['tables']['left']['xyz'] = [-.7, .4, .2]
    layout['tables']['left']['rpy'] = [.1, .2, .3]
    text = render_description(layout, tmp_path)[0]
    actual = Chain(text, 'world', 'left_charuco').forward({})
    table = layout['tables']['left']
    expected = (transform(table['xyz'], table['rpy']) @ transform([0,0,table['height']], [0,0,0]) @
                table_board_transform(layout['charuco'], 'left'))
    np.testing.assert_allclose(actual, expected)
    layout['charuco']['enabled'] = False
    root = ET.fromstring(render_description(layout, tmp_path)[0])
    assert root.find("link[@name='left_charuco']") is None

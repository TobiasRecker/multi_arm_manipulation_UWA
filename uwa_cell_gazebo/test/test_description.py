from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from uwa_cell_gazebo.configuration import (
    ROBOT_IDS, controller_parameters, load_layout, render_description,
)

LAYOUT = Path(__file__).resolve().parents[2] / 'uwa_cell_description/config/cell_layout.yaml'


def description(layout, directory):
    return ET.fromstring(render_description(layout, directory)[0])


def transform(root, link):
    parents = {joint.find('child').get('link'): joint for joint in root.findall('joint')}
    matrix = np.eye(4)
    while link != 'world':
        joint = parents[link]
        assert joint.get('type') == 'fixed'
        origin = joint.find('origin')
        local = np.eye(4)
        if origin is not None:
            local[:3, 3] = np.fromstring(origin.get('xyz', '0 0 0'), sep=' ')
            local[:3, :3] = Rotation.from_euler(
                'xyz', np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')).as_matrix()
        matrix = local @ matrix
        link = joint.find('parent').get('link')
    return matrix


def test_four_models_and_connected_unique_24_joint_description(tmp_path):
    layout = load_layout(LAYOUT)
    assert [layout['robots'][rid]['type'] for rid in ROBOT_IDS] == ['ur5', 'ur7e', 'ur5e', 'ur5e']
    root = description(layout, tmp_path)
    links, joints = root.findall('link'), root.findall('joint')
    assert len({link.get('name') for link in links}) == len(links)
    assert len({joint.get('name') for joint in joints}) == len(joints)
    assert len([joint for joint in joints if joint.get('type') in ('revolute', 'continuous')]) == 24
    children = {joint.find('child').get('link') for joint in joints}
    assert {link.get('name') for link in links} - children == {'world'}
    assert len(joints) == len(links) - 1
    assert len(root.findall('ros2_control/joint')) == 24
    for rid, x, y in [('left_front', -.45, -.675), ('left_rear', -.45, .675),
                      ('right_front', .45, -.675), ('right_rear', .45, .675)]:
        np.testing.assert_allclose(transform(root, f'{rid}_base_link')[:3, 3], [x, y, .9])
    assert layout['tables']['right']['xyz'][0] - layout['tables']['left']['xyz'][0] - .8 == pytest.approx(.1)
    control = controller_parameters(layout)
    controlled = [joint for key, item in control.items() if key != '/uwa_cell/controller_manager'
                  for joint in item['ros__parameters']['joints']]
    assert set(controlled) == {joint.get('name') for joint in root.findall('ros2_control/joint')}
    assert len(controlled) == len(set(controlled)) == 24


def test_both_arms_follow_repositioned_table(tmp_path):
    layout = load_layout(LAYOUT)
    original = description(layout, tmp_path)
    layout['tables']['left']['xyz'] = [-.8, .2, .1]
    layout['tables']['left']['rpy'] = [0, 0, np.pi / 4]
    moved = description(layout, tmp_path)
    rotation = Rotation.from_euler('z', np.pi / 4)
    for rid, y in [('left_front', -.675), ('left_rear', .675)]:
        expected = rotation.apply([0, y, .9]) + [-.8, .2, .1]
        np.testing.assert_allclose(transform(moved, f'{rid}_base_link')[:3, 3], expected)
    for rid in ('right_front', 'right_rear'):
        np.testing.assert_allclose(transform(original, f'{rid}_base_link'),
                                   transform(moved, f'{rid}_base_link'))


def test_description_has_no_dependency_on_scan_file(tmp_path):
    layout = load_layout(LAYOUT)
    layout['scan']['source'] = '/missing/offline/drive/never-read.ply'
    assert description(layout, tmp_path).get('name') == 'uwa_cell'


@pytest.mark.parametrize('change', ['height', 'duplicate_robot', 'nan', 'outside_mount'])
def test_invalid_layout_fails_before_gazebo(tmp_path, change):
    import yaml
    layout = deepcopy(load_layout(LAYOUT))
    if change == 'height':
        layout['tables']['left']['height'] = -.1
    elif change == 'duplicate_robot':
        layout['robots']['extra_arm'] = layout['robots']['left_front']
    elif change == 'nan':
        layout['robots']['left_front']['mount_rpy'][0] = float('nan')
    else:
        layout['robots']['left_front']['mount_xyz'][0] = 2.0
    path = tmp_path / 'layout.yaml'
    path.write_text(yaml.safe_dump(layout))
    with pytest.raises(ValueError):
        load_layout(path)

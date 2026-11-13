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


def test_image_rendering_can_be_disabled_without_changing_robot_or_controller_model(tmp_path):
    layout=load_layout(LAYOUT)
    normal=ET.fromstring(render_description(layout,tmp_path)[0])
    disabled=ET.fromstring(render_description(layout,tmp_path,image_sensors=False)[0])
    assert len(normal.findall('.//sensor[@type="camera"]'))==4
    assert disabled.findall('.//sensor[@type="camera"]')==[]
    for tag in ('link','joint','ros2_control'):
        assert [ET.tostring(e) for e in normal.findall(tag)]==[ET.tostring(e) for e in disabled.findall(tag)]
    assert [ET.tostring(e) for e in normal.findall('.//sensor') if e.get('type')!='camera']==[
        ET.tostring(e) for e in disabled.findall('.//sensor')]


def transform(root, link, ancestor='world'):
    parents = {joint.find('child').get('link'): joint for joint in root.findall('joint')}
    matrix = np.eye(4)
    while link != ancestor:
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


def test_four_models_and_connected_unique_arm_and_tool_description(tmp_path):
    layout = load_layout(LAYOUT)
    assert [layout['robots'][rid]['type'] for rid in ROBOT_IDS] == ['ur5', 'ur7e', 'ur5e', 'ur5e']
    root = description(layout, tmp_path)
    links, joints = root.findall('link'), root.findall('joint')
    assert len({link.get('name') for link in links}) == len(links)
    assert len({joint.get('name') for joint in joints}) == len(joints)
    assert len([joint for joint in joints if joint.get('type') in ('revolute', 'continuous')]) == 48
    children = {joint.find('child').get('link') for joint in joints}
    assert {link.get('name') for link in links} - children == {'world'}
    assert len(joints) == len(links) - 1
    assert len(root.findall('ros2_control/joint')) == 48
    for rid, x, y in [('left_front', -.45, -.675), ('left_rear', -.45, .675),
                      ('right_front', .45, -.675), ('right_rear', .45, .675)]:
        np.testing.assert_allclose(transform(root, f'{rid}_base_link')[:3, 3], [x, y, .9])
    assert layout['tables']['right']['xyz'][0] - layout['tables']['left']['xyz'][0] - .8 == pytest.approx(.1)
    control = controller_parameters(layout)
    controlled = [joint for key, item in control.items() if key != '/uwa_cell/controller_manager'
                  for joint in item['ros__parameters']['joints']]
    assert set(controlled) == {joint.get('name') for joint in root.findall('ros2_control/joint')
                              if joint.find('command_interface') is not None}
    assert len(controlled) == len(set(controlled)) == 28


def test_camera_frames_mounting_side_mimics_and_meshes(tmp_path):
    root = description(load_layout(LAYOUT), tmp_path)
    for rid in ROBOT_IDS:
        camera = transform(root, f'{rid}_wrist_camera_optical_frame', f'{rid}_tool0')
        # +Y points away from the UR tool I/O connector. The lens looks outward.
        np.testing.assert_allclose(camera[:3, 3], [0, .0357, -.0001])
        np.testing.assert_allclose(camera[:3, 2], [0, .5, np.sqrt(3)/2], atol=1e-12)
        base = transform(root, f'{rid}_robotiq_85_base_link', f'{rid}_tool0')
        assert base[2, 3] == pytest.approx(.0135)
        sensor = root.find(f"gazebo[@reference='{rid}_wrist_camera_link']/sensor")
        xyzrpy = np.fromstring(sensor.findtext('pose'), sep=' ')
        # Gazebo +X/+Y/+Z correspond to optical +Z/-X/-Y.
        sensor_rotation = Rotation.from_euler('xyz', xyzrpy[3:]).as_matrix()
        np.testing.assert_allclose(sensor_rotation[:, 0], camera[:3, 2], atol=1e-12)
        np.testing.assert_allclose(sensor_rotation[:, 1], -camera[:3, 0], atol=1e-12)
        np.testing.assert_allclose(sensor_rotation[:, 2], -camera[:3, 1], atol=1e-12)
        assert sensor.findtext('topic') == f'/uwa_cell/{rid}/wrist_camera/image_raw'
        mimics = [j for j in root.findall('joint') if j.get('name').startswith(rid)
                  and j.find('mimic') is not None]
        assert len(mimics) == 5
        for joint in mimics:
            assert joint.find('mimic').get('joint') == f'{rid}_robotiq_85_left_knuckle_joint'
            interface = root.find(f"ros2_control/joint[@name='{joint.get('name')}']")
            assert interface.find('command_interface') is None
    for mesh in root.findall('.//mesh'):
        filename = mesh.get('filename').removeprefix('file://')
        assert Path(filename).is_file(), filename


def test_optional_tools_and_per_robot_mounting_overrides(tmp_path):
    import yaml
    raw = yaml.safe_load(LAYOUT.read_text())
    raw['robots']['left_front']['tools'] = {'camera_yaw': np.pi}
    raw['robots']['left_rear']['tools'] = {'camera_enabled': False}
    raw['robots']['right_front']['tools'] = {'gripper': 'none'}
    raw['robots']['right_rear']['tools'] = {'gripper': 'none', 'camera_enabled': False}
    path = tmp_path / 'custom.yaml'
    path.write_text(yaml.safe_dump(raw))
    layout = load_layout(path)
    root = description(layout, tmp_path)
    camera = transform(root, 'left_front_wrist_camera_optical_frame', 'left_front_tool0')
    np.testing.assert_allclose(camera[:3, 3], [0, -.0357, -.0001], atol=1e-12)
    assert root.find("link[@name='left_rear_wrist_camera_link']") is None
    assert transform(root, 'left_rear_robotiq_85_base_link', 'left_rear_tool0')[2, 3] == .01
    assert root.find("link[@name='right_front_robotiq_85_base_link']") is None
    assert root.find("link[@name='right_front_wrist_camera_link']") is not None
    assert '/uwa_cell/right_front_gripper_controller' not in controller_parameters(layout)


@pytest.mark.parametrize('key,value', [('gripper', '2f_140'), ('camera_enabled', 'false'),
    ('gripper_initial_position', -.1), ('camera_width', 0), ('camera_height', True),
    ('camera_rate', 31), ('camera_yaw', float('nan')), ('camera_horizontal_fov', 4),
    ('camera_yaww', 0)])
def test_invalid_tool_settings_fail_before_gazebo(tmp_path, key, value):
    import yaml
    raw = yaml.safe_load(LAYOUT.read_text())
    raw['robots']['left_front']['tools'] = {key: value}
    path = tmp_path / 'invalid.yaml'
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError):
        load_layout(path)


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

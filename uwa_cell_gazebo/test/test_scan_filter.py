from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from uwa_cell_gazebo.configuration import load_layout
from uwa_cell_gazebo.scan_filter import filter_reference, robot_base_center

LAYOUT = Path(__file__).resolve().parents[2] / 'uwa_cell_description/config/cell_layout.yaml'


def layout():
    result = load_layout(LAYOUT)
    result['scan'].update(rpy=[0, 0, 0], xyz=[0, 0, 0], crop_radius=None,
                          crop_center=None, exclude_boxes=[])
    return result


def test_radius_uses_world_metres_and_keeps_boundary_and_colors():
    cfg = layout()
    cfg['scan'].update(rpy=[0, 0, np.pi / 2], xyz=[10, 0, .9], scale=2,
                       crop_radius=4)
    # Already-scaled scan coordinates: world positions are [0,0,.9], [0,4,.9]
    # and [0,4.001,.9]. Applying scale twice or ignoring the TF gives wrong results.
    xyz = np.array([[0, 10, 0], [4, 10, 0], [4.001, 10, 0]])
    rgb = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], dtype=np.uint8)
    kept, colors, stats = filter_reference(xyz, rgb, cfg)
    np.testing.assert_array_equal(kept, xyz[:2])
    np.testing.assert_array_equal(colors, rgb[:2])
    np.testing.assert_array_equal(xyz[2], [4.001, 10, 0])  # Input was not mutated.
    assert stats['outside_radius'] == 1


def test_base_center_follows_table_pose_and_height():
    cfg = layout()
    np.testing.assert_allclose(robot_base_center(cfg), [0, 0, .9], atol=1e-12)
    cfg['tables']['left'].update(xyz=[-.45, 2, .1], rpy=[0, 0, np.pi / 2])
    np.testing.assert_allclose(robot_base_center(cfg), [0, 1, .95], atol=1e-12)


def test_static_robot_masks_preserve_tabletops_and_do_not_follow_arm_pose():
    cfg = layout()
    cfg['scan']['exclude_boxes'] = [
        {'name': 'recorded_robot', 'min': [-.5, -.5, .95], 'max': [.5, .5, 1.7]}]
    xyz = np.array([[0, 0, .9], [-.5, 0, 1], [.5, 0, 1], [.6, 0, 1], [0, 0, 0]])
    rgb = np.arange(15).reshape(5, 3)
    kept, colors, stats = filter_reference(xyz, rgb, cfg)
    np.testing.assert_array_equal(kept, xyz[[0, 3, 4]])
    np.testing.assert_array_equal(colors, rgb[[0, 3, 4]])
    assert stats['excluded_by_box']['recorded_robot'] == 2
    for robot in cfg['robots'].values():
        robot['initial_positions'] = [1.0] * 6
    np.testing.assert_array_equal(filter_reference(xyz, rgb, cfg)[0], kept)


def test_overlapping_masks_are_counted_once_and_empty_output_is_valid():
    cfg = layout()
    box = {'name': 'one', 'min': [-1, -1, -1], 'max': [1, 1, 1]}
    cfg['scan']['exclude_boxes'] = [box, {**box, 'name': 'two'}]
    kept, colors, stats = filter_reference(np.zeros((2, 3)), np.zeros((2, 3)), cfg)
    assert kept.shape == colors.shape == (0, 3)
    assert stats['excluded_by_box'] == {'one': 2, 'two': 0}


@pytest.mark.parametrize('settings', [
    {'crop_radius': 0}, {'crop_radius': -4}, {'crop_radius': float('nan')},
    {'crop_center': [0, 0]}, {'exclude_boxes': None},
    {'exclude_boxes': [{'name': 'bad', 'min': [0, 0, 0], 'max': [0, 1, 1]}]},
    {'exclude_boxes': [{'name': 'bad', 'min': [0, 0, float('nan')], 'max': [1, 1, 1]}]},
])
def test_invalid_world_filter_settings_are_rejected(tmp_path, settings):
    cfg = deepcopy(load_layout(LAYOUT))
    cfg['scan'].update(settings)
    path = tmp_path / 'layout.yaml'
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):
        load_layout(path)

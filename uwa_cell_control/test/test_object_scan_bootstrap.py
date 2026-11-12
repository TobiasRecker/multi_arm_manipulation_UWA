"""Single-view coarse geometry is image-derived, with separate planning margins."""
from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
import yaml

from uwa_cell_control.object_scan_bootstrap import fit_overview_box, planning_design
from uwa_cell_control.object_digitization import vertices, project
from uwa_cell_control.object_scan_plan import target_geometry
from test_object_digitization import data


def test_single_overview_recovers_unknown_box_instead_of_copying_user_guess():
    expected, cameras, _ = data()
    camera = cameras['a']
    ids = [4, 5, 6, 7, 2, 3]
    landmarks = dict(ids=ids, pixels=project(vertices(expected)[ids], camera, 1600).tolist(),
                     proxy_width=1600, user_rough_size_m=[.4, .3, .2])
    result = fit_overview_box(camera, landmarks)
    np.testing.assert_allclose(result['dimensions_m'], expected[3:], atol=1e-6)
    assert result['absolute_accuracy_validated'] is False and result['final_cad'] is False
    layout = yaml.safe_load((Path(__file__).parents[2] / 'uwa_cell_description/config/cell_layout.yaml').read_text())
    config = planning_design(layout, result, landmarks, {})
    np.testing.assert_allclose(config['size_m'], np.maximum(expected[3:], [.4, .3, .2]) * 1.15 + .04)
    assert config['centre_m'][2] == config['size_m'][2] / 2 + .005
    assert config['reference_frame'] == 'right_table_top'


def test_overview_estimate_needs_ground_contact_edge_and_top_corners():
    _, cameras, _ = data()
    landmarks = dict(ids=[4, 5, 6, 7], pixels=[[1, 1]] * 4, proxy_width=1600)
    with pytest.raises(ValueError, match='four top corners'):
        fit_overview_box(cameras['a'], landmarks)
    landmarks.update(ids=[4, 5, 6, 7, 2, 3], pixels=[[1, 1]] * 6)
    with pytest.raises(ValueError, match='Degenerate support edge'):
        fit_overview_box(cameras['a'], landmarks)


def test_between_tables_reference_does_not_move_the_metric_board():
    layout = yaml.safe_load((Path(__file__).parents[2] / 'uwa_cell_description/config/cell_layout.yaml').read_text())
    description = '''<robot name="test"><link name="world"/><link name="left_table_top"/><link name="right_table_top"/>
      <joint name="left" type="fixed"><parent link="world"/><child link="left_table_top"/><origin xyz="-.45 0 .9"/></joint>
      <joint name="right" type="fixed"><parent link="world"/><child link="right_table_top"/><origin xyz=".45 0 .9"/></joint></robot>'''
    config = dict(reference_frame='table_pair_midpoint', centre_m=[.01, .02, .1], size_m=[.4, .3, .2], yaw_rad=.5)
    target = target_geometry(layout, description, config)
    np.testing.assert_allclose(target['centre'], [.01, .02, 1.])
    np.testing.assert_allclose(target['T_world_board'][:3, 3], [.31, .1, .903])
    np.testing.assert_allclose(target['T_world_object'][:3, 0], [np.cos(.5), np.sin(.5), 0])

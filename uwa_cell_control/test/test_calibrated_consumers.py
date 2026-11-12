"""Simulation, hardware collision checking, and measured overlay share FK."""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from match_ur_hardware.profiles import load_profiles
from uwa_cell_gazebo.configuration import load_layout, joint_names, render_description
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_control.parking import make_model
from uwa_cell_visualization.model import description


def test_rendered_collision_and_overlay_chains_match(tmp_path):
    layout = load_layout()
    inventory = load_profiles(Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml')
    simulation = render_description(layout, tmp_path)[0]
    model, hardware_layout = make_model(layout, inventory, tmp_path/'hardware')
    positions = {}
    for rid in layout['robots']:
        positions.update(zip(joint_names(rid), layout['robots'][rid]['initial_positions']))
    assert model.check(positions)[0], 'Applied factory calibration must preserve collision-free initial cell'
    for rid in ('left_rear', 'right_front', 'right_rear'):
        sim = Chain(simulation, rid+'_base_link', rid+'_tool0').forward(positions)
        planned = Chain(model.description, rid+'_base_link', rid+'_tool0').forward(positions)
        np.testing.assert_allclose(sim, planned, atol=1e-12)
        assert Path(inventory[rid]['kinematics_file']).read_bytes() == Path(layout['robots'][rid]['kinematics_file']).read_bytes()
        if rid.startswith('right'):
            visual = description(inventory[rid], layout)
            mapped = {'real_'+name: value for name, value in positions.items()}
            measured = Chain(visual, 'real_'+rid+'_base_link', 'real_'+rid+'_tool0').forward(mapped)
            np.testing.assert_allclose(sim, measured, atol=1e-12)
            if rid == 'right_rear':
                optical = Chain(visual, 'real_right_rear_tool0', 'real_right_rear_wrist_camera_optical_frame').forward({})
                np.testing.assert_allclose(optical, layout['calibration']['robots'][rid]['fit']['T_tool0_camera'], atol=1e-12)
    # Fixed camera collision primitives have not been moved by an optical fit.
    root = ET.fromstring(model.description)
    assert root.find("link[@name='right_rear_wrist_camera_link']/collision") is not None


def test_previous_simulator_profiles_are_not_loaded_as_measured_hardware(tmp_path):
    from uwa_cell_calibration.storage import profile_directory
    from uwa_cell_gazebo.configuration import nominal_layout_path
    assert profile_directory(tmp_path, load_layout(nominal_layout_path())) == tmp_path/'profiles'
    measured = profile_directory(tmp_path, load_layout())
    assert measured.parent == tmp_path/'profiles'
    assert measured.name.startswith('measured_')


def test_new_acquisition_planning_uses_measured_intrinsics_with_nominal_fallback():
    from uwa_cell_control.hardware_sequence import planning_camera
    from uwa_cell_gazebo.configuration import nominal_layout_path
    layout=load_layout()
    camera=planning_camera(layout,'right_front')
    assert camera['k']==layout['calibration']['robots']['right_front']['camera']['camera_matrix']
    assert camera['d']==layout['calibration']['robots']['right_front']['camera']['distortion']
    assert camera['required_focus']==435
    assert planning_camera(load_layout(nominal_layout_path()),'right_front')['source'].startswith('nominal')

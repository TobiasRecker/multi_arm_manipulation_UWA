"""Offline perception decisions and coordinate binding; no robot or Gazebo commands."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'tools'))
import carton_hydrogen as hydrogen
import carton_multiview as multi
import run_carton_program as runner


def pose(x=0., yaw=0.):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_euler('z', yaw, degrees=True).as_matrix()
    result[0, 3] = x
    return result


def test_mean_uses_rigid_rotation_and_wraps_yaw():
    result, decision = multi.select_pose([pose(.10, 179.5), pose(.106, -179.5)])
    assert result[0, 3] == pytest.approx(.103)
    assert abs(Rotation.from_matrix(result[:3, :3]).as_euler('xyz', degrees=True)[2]) == pytest.approx(180.)
    assert decision['position_difference_m'] == pytest.approx(.006)
    assert decision['mode'] == 'two_view_mean'


@pytest.mark.parametrize('second', [pose(.01), pose(0, 2.), pose(.02), pose(0, 180)])
def test_disagreement_is_never_averaged_or_silently_downgraded(second):
    with pytest.raises(ValueError, match='disagree'):
        multi.select_pose([pose(), second])


@pytest.mark.parametrize('status', ['confirmed', 'occluded', 'uncertain', 'unavailable'])
def test_weaker_view_never_moves_the_accepted_pose(status):
    original = pose(.1, 30)
    selected, decision = multi.select_pose([original], dict(status=status))
    np.testing.assert_array_equal(selected, original)
    assert decision['mode'] == ('single_confirmed' if status == 'confirmed' else 'single_view')


def test_absence_of_a_strict_fit_and_positive_contradiction_reject():
    with pytest.raises(ValueError, match='Neither'):
        multi.select_pose([])
    with pytest.raises(ValueError, match='contradicts'):
        multi.select_pose([pose()], dict(status='contradicted'))


def test_invalid_rotation_cannot_enter_fusion():
    invalid = pose()
    invalid[0, 0] = 2
    with pytest.raises(ValueError, match='rigid'):
        multi.select_pose([invalid])


def test_usb_guidance_uses_native_unrotated_pixel_coordinates():
    answer = dict(status='found', box_2d=[100, 200, 800, 900], front_box_2d=None,
                  front_quad_2d=[[100, 200], [100, 900], [800, 900], [800, 200]])
    quad = hydrogen.native_front_quad(answer, image_window=(0, 0, 4056, 3040))
    assert quad[:2] == (811.2, 304.)
    windows = hydrogen.search_windows(answer, native_size=(4056, 3040), image_window=(0, 0, 4056, 3040),
                                      window_sizes=((1800, 1600), (1800, 1400)))
    for x0, y0, x1, y1 in windows:
        assert 0 <= x0 < x1 <= 4056 and 0 <= y0 < y1 <= 3040


def test_combine_rebuilds_both_arm_chains_and_binds_both_sources(tmp_path, monkeypatch):
    # Real binding functions, minimal fixed URDF, two independently accepted synthetic fits.
    from uwa_cell_tasks.hardware_registration import per_arm_camera_binding, validate_per_arm_binding
    description = '<robot name="test"><link name="world"/>' + ''.join(
        f'<link name="{arm}_base_link"/><joint name="{arm}" type="fixed"><parent link="world"/>'
        f'<child link="{arm}_base_link"/><origin xyz="{x} 0 0"/></joint>'
        for arm, x in [('right_front', .5), ('right_rear', -.5)]) + '</robot>'
    model = tmp_path/'model.urdf'; model.write_text(description)
    views = {}
    for index, name in enumerate(('oak4', 'oak_usb')):
        directory = tmp_path/name; directory.mkdir()
        source = directory/'pixels'; source.write_bytes(name.encode())
        world_camera = pose(.3 + index)
        target = pose(.10 + index*.006, 179.5+index)
        registration = {'transforms': {arm: dict(parent_frame=arm+'_base_link',
            child_frame='oak4_rgb_optical_frame', T_parent_child=(pose(-x)@world_camera).tolist())
            for arm, x in [('right_front', .5), ('right_rear', -.5)]}}
        binding = per_arm_camera_binding(description, registration, np.linalg.inv(world_camera)@target)
        binding.update(source='Session ChArUco synthetic', source_inputs={str(source): multi.sha256(source)})
        file = directory/'object-pose.json'; file.write_text(json.dumps(binding))
        (directory/'registration.json').write_text(json.dumps(dict(success=True, object_pose=str(file))))
        views[name] = dict(pose=str(file))
    result = multi.combine(dict(description=str(model), views=views), tmp_path/'combined')
    selected = multi.read_json(Path(result['pose']))
    validate_per_arm_binding(description, selected)
    for arm in ('right_front', 'right_rear'):
        assert selected['world_object_by_arm'][arm][0][3] == pytest.approx(.103)
    assert all(str(tmp_path/name/'pixels') in selected['source_inputs'] for name in views)
    for source, digest in selected['source_inputs'].items():
        assert multi.sha256(Path(source)) == digest


def test_both_camera_fits_are_attempted_and_usb_can_be_the_only_pose(tmp_path, monkeypatch):
    out = tmp_path/'run'; out.mkdir()
    config = dict(intrinsics=tmp_path/'oak4.json', camera_session=tmp_path/'primary-session.json',
                  secondary_camera=dict(intrinsics=tmp_path/'usb.json', camera_session=tmp_path/'usb-session.json'))
    for file in (config['camera_session'], config['secondary_camera']['camera_session']):
        file.write_text('{}')
    monkeypatch.setattr(runner, 'validate_session', lambda *args, **kwargs: {})
    monkeypatch.setattr(runner, 'capture_usb', lambda *args: (tmp_path/'usb.png', tmp_path/'usb-meta.json'))
    attempts = []
    def fit(config, progress, *args, **kwargs):
        attempts.append(progress.output)
        if progress.output == out:
            raise runner.CartonFitRejected('OAK4 occluded', out/'registration')
        return progress.output/'object-pose.json'
    monkeypatch.setattr(runner, 'register_current_carton', fit)
    def combine(command, *args, **kwargs):
        manifest = runner.load_json(out/'multiview-input.json')
        assert 'pose' not in manifest['views']['oak4']
        assert manifest['views']['oak_usb']['pose']
        return json.dumps(dict(pose=str(out/'multiview/object-pose.json'), mode='single_view', primary_camera='oak_usb'))
    monkeypatch.setattr(runner, 'logged_command', combine)
    runner.register_multiview(config, runner.Progress(out), tmp_path, tmp_path/'oak4.png', tmp_path/'meta.json')
    assert attempts == [out, out/'oak-usb']

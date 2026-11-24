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


def test_preferred_pose_is_unchanged_when_second_view_agrees_across_yaw_wrap():
    primary=pose(.10,179.5)
    result, decision = multi.select_pose([primary, pose(.106, -179.5)])
    np.testing.assert_array_equal(result,primary)
    assert decision['position_difference_m'] == pytest.approx(.006)
    assert decision['mode'] == 'primary_checked'
    assert decision['weights']==[1.,0.]


@pytest.mark.parametrize('second', [pose(.030001), pose(0, 2.), pose(.04), pose(0, 180)])
def test_disagreement_is_never_averaged_or_silently_downgraded(second):
    with pytest.raises(ValueError, match='disagree'):
        multi.select_pose([pose(), second])


@pytest.mark.parametrize('yaw', [0., 37., 179.5, -179.5])
def test_opposite_corner_labels_represent_the_same_upright_carton(yaw):
    dimensions=[.404,.342,.163]
    first=pose(.123,yaw)
    first[1,3]=.245
    second=first@multi.half_turn(dimensions)
    selected,decision=multi.select_pose([first,second],dimensions=dimensions)
    np.testing.assert_allclose(selected,first,atol=1e-12)
    assert decision['second_pose_relabelled_deg']==180
    assert decision['position_difference_m']<1e-12
    assert decision['angle_difference_deg']<1e-10
    # A half turn exchanges rectangle corners, never changes its physical footprint.
    corners=np.array([[0,0,0,1],[.404,0,0,1],[0,.342,0,1],[.404,.342,0,1]])
    left=sorted(map(tuple,np.round((first@corners.T).T,12)))
    right=sorted(map(tuple,np.round((second@corners.T).T,12)))
    assert left==right


def test_half_turn_is_not_a_ninety_degree_average_or_a_translation_override():
    dimensions=[.404,.342,.163]
    first=pose()
    with pytest.raises(ValueError,match='disagree'):
        multi.select_pose([first,pose(0,180)],dimensions=dimensions)
    second=first@multi.half_turn(dimensions)
    second[0,3]+=.0301
    with pytest.raises(multi.PoseDisagreement,match='symmetry alignment'):
        multi.select_pose([first,second],dimensions=dimensions)
    quarter=pose(0,90)
    centre=np.array([.202,.171,0.])
    quarter[:3,3]=centre-quarter[:3,:3]@centre
    with pytest.raises(ValueError,match='90.000 deg'):
        multi.select_pose([first,quarter],dimensions=dimensions)


def test_symmetry_check_keeps_primary_centre_and_rotation_and_reports_residual():
    dimensions=[.404,.342,.163]
    first=pose()
    # Rotate the same carton by one degree about its centre, then relabel its corners.
    centre=np.array([.202,.171,0.])
    nearby=pose(0,1.)
    nearby[:3,3]=centre-nearby[:3,:3]@centre
    second=nearby@multi.half_turn(dimensions)
    result,decision=multi.select_pose([first,second],dimensions=dimensions)
    np.testing.assert_array_equal(result,first)
    np.testing.assert_allclose(result[:3,:3]@centre+result[:3,3],centre,atol=1e-12)
    assert decision['angle_difference_deg']==pytest.approx(1.)
    assert decision['position_reference']=='carton_base_centre'


@pytest.mark.parametrize('offset,accepted',[(.014392,True),(.03,True),(.030000001,False)])
def test_thirty_mm_centre_boundary_does_not_move_primary(offset,accepted):
    primary=pose()
    if not accepted:
        with pytest.raises(multi.PoseDisagreement,match='centre <=30 mm'):
            multi.select_pose([primary,pose(offset)])
    else:
        selected,decision=multi.select_pose([primary,pose(offset)])
        np.testing.assert_array_equal(selected,primary)
        assert decision['centre_limit_m']==.03


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


def test_combine_preserves_oak4_arm_chains_and_binds_both_sources_despite_manifest_order(tmp_path, monkeypatch):
    # Real binding functions, minimal fixed URDF, two independently accepted synthetic fits.
    from uwa_cell_tasks.hardware_registration import per_arm_camera_binding, validate_per_arm_binding
    description = '<robot name="test"><link name="world"/>' + ''.join(
        f'<link name="{arm}_base_link"/><joint name="{arm}" type="fixed"><parent link="world"/>'
        f'<child link="{arm}_base_link"/><origin xyz="{x} 0 0"/></joint>'
        for arm, x in [('right_front', .5), ('right_rear', -.5)]) + '</robot>'
    model = tmp_path/'model.urdf'; model.write_text(description)
    views = {}
    original_primary=None
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
        if name=='oak4':original_primary=json.loads(json.dumps(binding))
        file = directory/'object-pose.json'; file.write_text(json.dumps(binding))
        (directory/'registration.json').write_text(json.dumps(dict(success=True, object_pose=str(file))))
        views[name] = dict(pose=str(file))
    views=dict(reversed(list(views.items())))
    result = multi.combine(dict(description=str(model), views=views), tmp_path/'combined')
    selected = multi.read_json(Path(result['pose']))
    validate_per_arm_binding(description, selected)
    assert result['primary_camera']=='oak4'
    for field in ('T_camera_object','T_world_object_candidate','world_object_by_arm'):
        assert selected[field]==original_primary[field]
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

"""Known synthetic geometry checks for the offline diagnostic, no hardware."""
import hashlib
import json

import numpy as np
import pytest

from uwa_cell_control.board_photo_evaluation import (transform, project, relative_fit,
    check_relative, correspondences, load_rows)


def synthetic():
    optics = dict(right_front=dict(K=np.array([[1000., 0, 640], [0, 1010, 480], [0, 0, 1]]), D=np.zeros(5)),
                  oak4=dict(K=np.array([[1700., 0, 1000], [0, 1680, 750], [0, 0, 1]]), D=np.zeros(5)))
    objects = np.array([[x*.038, y*.038, 0.] for y in range(1, 5) for x in range(1, 7)])
    relative = transform([.1, -.2, .05], [.25, -.1, .12])
    rows = []
    for i in range(5):
        reference_board = transform([.1 + .07*i, -.2 + .08*i, .12*i], [-.12 + .025*i, -.08, .9 + .04*i])
        observations = {}
        for name, pose in [('right_front', reference_board), ('oak4', relative @ reference_board)]:
            observations[name] = dict(object_points=objects.tolist(), image_points=project(objects, pose, optics[name]).tolist())
        rows.append(dict(set_id=str(i), role='fit' if i < 3 else 'validation', observations=observations))
    return rows, optics, relative


def test_recovers_correct_transform_direction_and_predicts_held_out_camera_pixels():
    rows, optics, truth = synthetic()
    actual, details = relative_fit(rows[:3], optics)
    assert details['training_count'] == 3
    assert np.allclose(actual, truth, atol=1e-7)
    for row in rows[3:]:
        check = check_relative(row, actual, optics)
        assert check['relative_translation_difference_mm'] < .0001
        assert check['relative_rotation_difference_deg'] < .0001
        assert max(e['cross_camera_rms_px'] for e in check['errors'].values()) < .0001


def test_bad_held_out_image_is_exposed_by_cross_camera_error_not_refitted():
    rows, optics, _ = synthetic()
    actual, _ = relative_fit(rows[:3], optics)
    pixels = np.asarray(rows[-1]['observations']['oak4']['image_points'])
    rows[-1]['observations']['oak4']['image_points'] = (pixels + [15., -7.]).tolist()
    check = check_relative(rows[-1], actual, optics)
    assert check['errors']['oak4']['cross_camera_rms_px'] > 10
    again, _ = relative_fit(rows[:3], optics)
    assert np.array_equal(actual, again)


@pytest.mark.parametrize('objects,pixels', [([[0., 0., 0.]] * 4, [[1., 2.]] * 4),
    ([[float('nan'), 0., 0.]] * 4, [[1., 2.]] * 4)])
def test_invalid_board_geometry_is_rejected(objects, pixels):
    with pytest.raises(ValueError):
        correspondences(dict(object_points=objects, image_points=pixels))


def test_modified_original_cannot_be_silently_used(tmp_path):
    p = tmp_path / 'session/set_001'
    (p / 'oak4').mkdir(parents=True)
    image = p / 'oak4/image.png'
    image.write_bytes(b'changed photo')
    data = dict(all_captured=True, cameras=dict(oak4=dict(success=True, image='image.png',
        sha256=hashlib.sha256(b'original photo').hexdigest(), observation={})))
    (p / 'manifest.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='Image hash differs'):
        load_rows(tmp_path)

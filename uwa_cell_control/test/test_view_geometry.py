import numpy as np
from uwa_cell_control.view_geometry import segment_box_hits, project_points, VisibilityModel


def test_finite_segments_parallel_rays_and_transformed_box():
    box = np.eye(4)
    box[:3, 3] = [0, 0, 2]
    bounds = np.array([[-.5, -.5, -.5], [.5, .5, .5]])
    # A body beyond a target cannot occlude that target; parallel outside misses.
    result = segment_box_hits([0, 0, 0], [[0, 0, 4], [0, 0, 1], [2, 0, 4]], box, bounds)
    np.testing.assert_array_equal(result, [True, False, False])
    np.testing.assert_array_equal(segment_box_hits([2, 0, 0], [[2, 0, 4]], box, bounds), [False])
    transform = np.array([[0., -1, 0, 2], [1., 0, 0, 3], [0., 0, 1, 1], [0., 0, 0, 1]])
    targets = np.array([[0., 0, 4], [0., 0, 1], [2., 0, 4]])
    np.testing.assert_array_equal(segment_box_hits(transform[:3, 3],
        targets @ transform[:3, :3].T + transform[:3, 3], transform @ box, bounds), result)


def test_optical_projection_rejects_behind_camera_and_outside_image():
    k = np.array([[100., 0, 50], [0, 100., 40], [0, 0, 1]])
    _, inside = project_points([[0, 0, 1], [0, 0, -1], [2, 0, 1]], np.eye(4), k, np.zeros(5), [100, 80])
    np.testing.assert_array_equal(inside, [True, False, False])


def test_mount_near_clipping_does_not_hide_a_real_obstacle_further_away():
    bounds = np.array([[-.1, -.1, 0], [.1, .1, .001]])
    assert not segment_box_hits([0, 0, 0], [[0, 0, 1]], np.eye(4), bounds)[0]
    translated = np.eye(4)
    translated[2, 3] = .1
    assert segment_box_hits([0, 0, 0], [[0, 0, 1]], translated, bounds)[0]


def test_look_at_is_a_right_handed_optical_transform():
    from uwa_cell_control.oak_view_design import look_at
    eye, target = np.array([1., 0, 2]), np.array([0., 0, .9])
    camera = look_at(eye, target)
    np.testing.assert_allclose(camera[:3, :3].T @ camera[:3, :3], np.eye(3), atol=1e-12)
    assert np.isclose(np.linalg.det(camera[:3, :3]), 1.)
    np.testing.assert_allclose(camera[:3, 2], (target-eye)/np.linalg.norm(target-eye))


def test_moving_body_changes_occlusion_without_changing_target():
    urdf = '''<robot name="test"><link name="world"/><link name="arm_body">
    <collision><geometry><box size="1 1 1"/></geometry></collision></link>
    <joint name="slide" type="prismatic"><parent link="world"/><child link="arm_body"/>
    <origin xyz="0 0 2"/><axis xyz="1 0 0"/></joint></robot>'''
    model = VisibilityModel(urdf, ['arm'])
    assert model.blocked([0, 0, 0], [[0, 0, 4]], model.frames({'slide': 0}))[0]
    assert not model.blocked([0, 0, 0], [[0, 0, 4]], model.frames({'slide': 2}))[0]

"""Combine independently accepted carton fits; inspect weaker views without using their pose."""

import argparse
import asyncio
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

from carton_camera_session import read_json, sha256, validate_session, write_session
import carton_hydrogen


def transform(value):
    matrix = np.asarray(value, dtype=float)
    if (matrix.shape != (4, 4) or not np.isfinite(matrix).all()
            or not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-9, rtol=0)
            or not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-7, rtol=0)
            or not np.isclose(np.linalg.det(matrix[:3, :3]), 1, atol=1e-7, rtol=0)):
        raise ValueError('Invalid rigid camera/object transform.')
    return matrix


def select_pose(poses, verification=None):
    """All input poses already passed the unchanged single-camera fit criteria."""
    if not poses:
        raise ValueError('Neither camera produced an accepted current carton pose.')
    if len(poses) == 1:
        check = verification or {'status': 'unavailable'}
        if check['status'] == 'contradicted':
            raise ValueError('The second view visibly contradicts the accepted carton pose.')
        if check['status'] not in {'confirmed', 'occluded', 'uncertain', 'unavailable'}:
            raise ValueError('Invalid second-view verification status.')
        return transform(poses[0]), dict(mode='single_confirmed' if check['status'] == 'confirmed' else 'single_view',
                                         verification=check)
    if len(poses) != 2:
        raise ValueError('Expected one or two independent camera fits.')
    first, second = map(transform, poses)
    distance = float(np.linalg.norm(first[:3, 3] - second[:3, 3]))
    angle = float(np.rad2deg(Rotation.from_matrix(first[:3, :3].T @ second[:3, :3]).magnitude()))
    # Reuse the registration's existing agreement limits, with the same strict boundary.
    if distance >= .01 or angle >= 2.:
        raise ValueError(f'Camera poses disagree: {distance*1000:.3f} mm / {angle:.3f} deg (limits <10 mm / <2 deg).')
    result = np.eye(4)
    result[:3, 3] = (first[:3, 3] + second[:3, 3]) / 2
    result[:3, :3] = Slerp([0, 1], Rotation.from_matrix([first[:3, :3], second[:3, :3]]))(.5).as_matrix()
    return result, dict(mode='two_view_mean', position_difference_m=distance, angle_difference_deg=angle,
                        weights=[.5, .5], absolute_accuracy_validated=False)


def symmetry_diagnostic(first, second, dimensions):
    """Explain a possible rectangular 180-degree alias; never accept it as a fit."""
    symmetry = np.diag([-1., -1., 1., 1.])
    symmetry[:2, 3] = dimensions[:2]
    equivalent = transform(second) @ symmetry
    first = transform(first)
    return dict(interpretation='Diagnostic rectangular 180-degree alias only; original poses remain rejected',
        position_difference_m=float(np.linalg.norm(equivalent[:3, 3]-first[:3, 3])),
        angle_difference_deg=float(np.rad2deg(Rotation.from_matrix(
            first[:3, :3].T@equivalent[:3, :3]).magnitude())))


def accepted_binding(path, description):
    from uwa_cell_tasks.hardware_registration import validate_per_arm_binding

    proof = read_json(path.parent/'registration.json')
    binding = read_json(path)
    if proof.get('success') is not True or Path(proof['object_pose']).resolve() != path.resolve():
        raise ValueError('An independent successful image registration is required for each metric pose.')
    validate_per_arm_binding(description, binding)
    for source, digest in binding['source_inputs'].items():
        if sha256(Path(source)) != digest:
            raise ValueError('Carton fit source changed: '+source)
    return binding


def projected_verification(view, world_pose, description, output):
    import cv2
    from uwa_cell_gazebo.charuco_views import Chain

    session = validate_session(read_json(Path(view['session'])), Path(view['intrinsics']),
                               photo=read_json(Path(view['metadata'])))
    optics = session['optics']
    world_camera = Chain(description, 'world', 'right_charuco').forward({}) @ np.linalg.inv(
        transform(session['T_camera_board']))
    camera_object = np.linalg.inv(world_camera) @ transform(world_pose)
    dimensions = read_json(Path(__file__).resolve().parents[1]/'uwa_cell_description/assets/carton_avocado_v1/asset.json')['dimensions_m']
    length, width, height = dimensions
    points = np.array([[x, y, z] for z in (0, height) for y in (0, width) for x in (0, length)])
    if ((camera_object[:3, :3] @ points.T).T + camera_object[:3, 3])[:, 2].min() <= 0:
        return dict(status='unavailable', reason='Predicted carton is behind the second camera.')
    pixels = cv2.projectPoints(points, cv2.Rodrigues(camera_object[:3, :3])[0], camera_object[:3, 3],
                               np.asarray(optics['K']), np.asarray(optics['D']))[0].reshape(-1, 2)
    native_width, native_height = optics['image_size']
    low = np.floor(pixels.min(axis=0)-100).astype(int)
    high = np.ceil(pixels.max(axis=0)+100).astype(int)
    x0, y0 = np.maximum(low, [0, 0])
    x1, y1 = np.minimum(high, [native_width, native_height])
    if x1 <= x0 or y1 <= y0:
        return dict(status='unavailable', reason='Predicted carton is outside the second image.')
    image = cv2.imread(view['image'])
    if image is None or list(image.shape[1::-1]) != optics['image_size']:
        raise ValueError('Invalid second-view image.')
    viewport = tuple(map(int, (x0, y0, x1, y1)))
    # Import only here, within the normal ROS offline environment.
    from register_carton_from_oak import carton_overlay
    plain = carton_overlay(image, None, None, None, dimensions, viewport=viewport)
    overlay = carton_overlay(image, camera_object, np.asarray(optics['K']), np.asarray(optics['D']),
                              dimensions, viewport=viewport)
    cv2.imwrite(str(output/'verification-image.jpg'), plain)
    cv2.imwrite(str(output/'verification-overlay.jpg'), overlay)
    answer = asyncio.run(carton_hydrogen.inspect_projected_carton(
        cv2.imencode('.jpg', plain)[1].tobytes(), cv2.imencode('.jpg', overlay)[1].tobytes(), output))
    return dict(answer, viewport=list(viewport), model=carton_hydrogen.MODEL, effort=carton_hydrogen.EFFORT)


def combine(manifest, output):
    output.mkdir()
    description = Path(manifest['description']).read_text()
    views = manifest['views']
    for view in views.values():
        if view.get('pose') and view.get('session'):
            validate_session(read_json(Path(view['session'])), Path(view['intrinsics']),
                             photo=read_json(Path(view['metadata'])))
    accepted = [(name, accepted_binding(Path(view['pose']), description)) for name, view in views.items() if view.get('pose')]
    verification = None
    if len(accepted) == 1:
        world_pose = accepted[0][1]['T_world_object_candidate']
        for name, view in views.items():
            if name != accepted[0][0] and view.get('image') and view.get('session'):
                if manifest.get('gemini_enabled') is not True:
                    verification = dict(status='unavailable', reason='Additional Gemini image transfer awaits explicit authorization.')
                else:
                    try:
                        verification = projected_verification(view, world_pose, description, output)
                    except (ValueError, OSError, RuntimeError, TimeoutError) as error:
                        verification = dict(status='unavailable', reason=str(error))
    report = dict(views=views, verification=verification, success=False, absolute_accuracy_validated=False)
    try:
        pose, decision = select_pose([b['T_world_object_candidate'] for _, b in accepted], verification)
        primary_name, binding = accepted[0]
        # Keep the primary camera/base chain and express the selected object through it.
        primary_world = transform(binding['T_world_object_candidate'])
        world_camera = primary_world @ np.linalg.inv(transform(binding['T_camera_object']))
        camera_object = np.linalg.inv(world_camera) @ pose
        binding['T_camera_object'] = camera_object.tolist()
        binding['T_world_object_candidate'] = pose.tolist()
        binding['world_object_by_arm'] = {
            arm: (transform(binding['T_world_base_by_arm'][arm]) @ transform(base_camera) @ camera_object).tolist()
            for arm, base_camera in binding['T_base_camera_by_arm'].items()}
        for _, other in accepted:
            binding['source_inputs'].update(other['source_inputs'])
        # Bind failed-view pixels and the categorical decision as evidence too.
        for view in views.values():
            for key in ('image', 'metadata', 'intrinsics', 'session', 'pose'):
                if view.get(key):
                    path = Path(view[key]).resolve()
                    binding['source_inputs'][str(path)] = sha256(path)
        for path in [Path(__file__), Path(carton_hydrogen.__file__), *sorted(output.glob('verification-*jpg'))]:
            binding['source_inputs'][str(path.resolve())] = sha256(path)
        binding['multiview'] = dict(decision, primary_camera=primary_name, accepted_cameras=[n for n, _ in accepted])
        report.update(success=True, **binding['multiview'])
        write_session(output/'decision.json', report)
        binding['source_inputs'][str((output/'decision.json').resolve())] = sha256(output/'decision.json')
        from uwa_cell_tasks.hardware_registration import validate_per_arm_binding
        validate_per_arm_binding(description, binding)
        write_session(output/'object-pose.json', binding)
        write_session(output/'registration.json', dict(report, object_pose=str(output/'object-pose.json'),
                                                       T_world_object=pose.tolist()))
        return dict(pose=str(output/'object-pose.json'), primary_camera=primary_name, **decision)
    except ValueError as error:
        if len(accepted) == 2:
            dimensions = read_json(Path(__file__).resolve().parents[1]/'uwa_cell_description/assets/carton_avocado_v1/asset.json')['dimensions_m']
            report['rectangle_symmetry_diagnostic'] = symmetry_diagnostic(
                accepted[0][1]['T_world_object_candidate'], accepted[1][1]['T_world_object_candidate'], dimensions)
        write_session(output/'decision.json', dict(report, error=str(error)))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(combine(read_json(args.manifest), args.output.resolve())))

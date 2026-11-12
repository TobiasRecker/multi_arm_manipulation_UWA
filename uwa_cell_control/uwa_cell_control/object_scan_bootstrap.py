"""Assisted coarse box estimate from one OAK RGB photo, for view planning only.

The visible metric board establishes scale. Explicit object landmarks are
reviewed annotations, not automatic segmentation or a final CAD measurement.
No robot command clients; no depth or learned model is used.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
import yaml

from uwa_cell_description.configuration import load_layout
from uwa_cell_gazebo.charuco import table_board_transform
from .board_photo_evaluation import pose_from_observation
from .hardware_charuco import observe
from .object_digitization import vertices, project, plane_point, object_pose


def fit_overview_box(camera, landmarks):
    ids = landmarks['ids']
    pixels = np.asarray(landmarks['pixels'], float)
    width = landmarks['proxy_width']
    if (len(set(ids)) != len(ids) or set(ids) - set(range(8)) or len(ids) < 6 or
            pixels.shape != (len(ids), 2) or not np.isfinite(pixels).all() or
            type(width) is not int or width <= 0 or
            not {2, 3, 4, 5, 6, 7} <= set(ids)):
        raise ValueError('Need four top corners (4..7) and two front support corners (2,3)')
    p2, p3 = [plane_point(pixels[ids.index(i)], camera, width) for i in (2, 3)]
    length = np.linalg.norm(p2[:2] - p3[:2])
    if length < .05:
        raise ValueError('Degenerate support edge')
    yaw = np.arctan2(*(p2 - p3)[[1, 0]])
    rough = np.asarray(landmarks.get('user_rough_size_m', [length, .3, .2]), float)
    if rough.shape != (3,) or not np.isfinite(rough).all() or min(rough) <= 0:
        raise ValueError('Rough seed dimensions must be positive finite metres')
    origin = p3[:2] - rough[1] * np.array([-np.sin(yaw), np.cos(yaw)])
    initial = np.r_[origin, yaw, length, rough[1:]]
    def residual(parameters):
        return (project(vertices(parameters)[ids], camera, width) - pixels).ravel()
    result = least_squares(residual, initial, bounds=([-5, -5, -8, .05, .05, .03], [5, 5, 8, 2., 2., 1.5]),
                           loss='soft_l1', f_scale=3., max_nfev=250)
    singular = np.linalg.svd(result.jac, compute_uv=False)
    if not result.success or singular[-1] / singular[0] < 1e-8:
        raise ValueError('Coarse box fit failed or is geometrically degenerate')
    error = residual(result.x).reshape(-1, 2)
    rms = float(np.sqrt(np.mean(np.sum(error ** 2, axis=1))))
    if rms > 15:
        raise ValueError('Landmark/model disagreement exceeds 15 proxy pixels; review the estimate')
    return dict(parameters_board_m_rad=result.x.tolist(), dimensions_m=result.x[3:].tolist(),
                point_rms_proxy_px=rms, point_errors_proxy_px=np.linalg.norm(error, axis=1).tolist(),
                absolute_accuracy_validated=False, final_cad=False, depth_used=False,
                assumptions=['Rectangular footprint, vertical walls, horizontal common support plane.',
                             'Image landmarks explicitly selected/reviewed; no automatic object segmentation.',
                             'Board print scale and fixed focus intrinsics assumed correct.'])


def planning_design(layout, estimate, landmarks, template, *, reference_table='right'):
    """Map image estimate to provisional model; enlarge with explicit design margins."""
    table_board = table_board_transform(layout['charuco'], reference_table)
    points = vertices(estimate['parameters_board_m_rad'])
    centre_board = points.mean(axis=0)
    centre_table = (table_board @ np.r_[centre_board, 1])[:3]
    size = np.asarray(estimate['dimensions_m'])
    rough = np.asarray(landmarks.get('user_rough_size_m', size))
    # Design allowance, NOT a statistical accuracy bound or a validated guarantee.
    padded = np.maximum(size, rough) * 1.15 + .04
    centre_table[2] = padded[2] / 2 + .005
    rotation_table = table_board[:3, :3] @ object_pose(estimate['parameters_board_m_rad'])[:3, :3]
    config = dict(template, reference_frame=reference_table + '_table_top',
                  centre_m=centre_table.tolist(), size_m=padded.tolist(),
                  yaw_rad=float(np.arctan2(rotation_table[1, 0], rotation_table[0, 0])),
                  geometry_source='assisted single-OAK box estimate; provisional board-to-table model anchor',
                  coarse_dimensions_m=size.tolist(), user_rough_dimensions_m=rough.tolist(),
                  design_margin='max(image estimate, user rough dimensions) * 1.15 + 0.04 m per dimension')
    return config


def prepare(oak_result, landmarks_path, output, template):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result = json.loads(Path(oak_result).read_text())
    image_path = Path(result['images']['standard']).resolve()
    metadata = json.loads(Path(result['metadata']).read_text())
    landmarks = json.loads(Path(landmarks_path).read_text())
    image = cv2.imread(str(image_path))
    if image is None or list(image.shape[1::-1]) != [8000, 6000]:
        raise ValueError('Native 8000x6000 OAK standard photograph required')
    layout = load_layout()
    profile = layout['calibration']
    factory = profile['overview_camera']['factory']
    if metadata['standard']['lens_position'] != factory['factory_calibration_lens_position']:
        raise ValueError('OAK photo focus does not match factory intrinsic reference')
    if landmarks.get('image_sha256') != hashlib.sha256(image_path.read_bytes()).hexdigest():
        raise ValueError('Landmarks are not bound to this original photograph')
    reference = landmarks.get('reference_table', 'right')
    if reference not in ('left', 'right'):
        raise ValueError('Reference table must be left or right')
    observation = observe(image, layout['charuco'], reference)
    observation.pop('annotated')
    intrinsic = dict(K=np.asarray(factory['camera_matrix_8000x6000']), D=np.asarray(factory['distortion']))
    pose, rms = pose_from_observation(observation, intrinsic)
    camera = dict(K=intrinsic['K'].tolist(), D=intrinsic['D'].tolist(), T_camera_board=pose.tolist(), observation=observation)
    estimate = fit_overview_box(camera, landmarks)
    config = planning_design(layout, estimate, landmarks, template, reference_table=reference)
    estimate.update(source_image=str(image_path), image_sha256=landmarks['image_sha256'],
                    camera=camera, reference_table=reference, board_rms_native_px=rms,
                    calibration_profile_id=profile['profile_id'], calibration_profile_sha256=profile['sha256'],
                    annotation=landmarks, planning_design=config,
                    planning_not_execution_authority=True)
    (output / 'estimate.json').write_text(json.dumps(estimate, indent=2, allow_nan=False) + '\n')
    (output / 'scan_geometry.yaml').write_text(yaml.safe_dump(config, sort_keys=False))
    width = landmarks['proxy_width']
    review = cv2.resize(image, (width, round(image.shape[0] * width / image.shape[1])))
    projected = project(vertices(estimate['parameters_board_m_rad']), camera, width)
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        cv2.line(review, tuple(np.rint(projected[a]).astype(int)), tuple(np.rint(projected[b]).astype(int)), (0, 255, 0), 2)
    for index, pixel in zip(landmarks['ids'], landmarks['pixels']):
        pt = tuple(np.rint(pixel).astype(int))
        cv2.circle(review, pt, 5, (0, 0, 255), -1)
        cv2.putText(review, str(index), pt, cv2.FONT_HERSHEY_SIMPLEX, .75, (0, 0, 255), 2)
    caption = 'COARSE OAK ESTIMATE / PLANNING ONLY / reviewed landmarks'
    cv2.putText(review, caption, (20, 36), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 5)
    cv2.putText(review, caption, (20, 36), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
    cv2.imwrite(str(output / 'overview_estimate.jpg'), review)
    return estimate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.home() / 'UWA_ws')
    parser.add_argument('--oak-result', type=Path, help='Saved result JSON from the existing OAK standard photo service')
    parser.add_argument('--capture-oak', action='store_true', help='Take one RGB photo; does not move any arm')
    parser.add_argument('--landmarks', type=Path, help='Reviewed, image-hash-bound coarse corner annotation')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.capture_oak:
        if args.oak_result:
            parser.error('Choose a saved photo or --capture-oak')
        source = args.workspace / 'src/oak_camera_calibration/tools/oak4_photo_service.py'
        spec = importlib.util.spec_from_file_location('uwa_scan_oak_photo', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.PhotoCapture(args.workspace).capture('standard', focus=116)
        args.oak_result = args.output / 'oak_result.json'
        args.oak_result.write_text(json.dumps(result, indent=2) + '\n')
    if not args.oak_result:
        parser.error('--oak-result or --capture-oak required')
    if args.landmarks is None:
        result = json.loads(args.oak_result.read_text())
        source = Path(result['images']['standard'])
        image = cv2.imread(str(source))
        cv2.imwrite(str(args.output / 'overview_review.jpg'), cv2.resize(image, (1600, 1200)))
        annotation = dict(image_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), reference_table='right',
                          proxy_width=1600, ids=[4, 5, 6, 7, 2, 3], pixels=None,
                          user_rough_size_m=None, annotation_source='REQUIRES reviewed object corner selection')
        template = args.output / 'landmarks_template.json'
        if template.exists():
            raise ValueError('Existing annotation template preserved; use a new session directory')
        template.write_text(json.dumps(annotation, indent=2) + '\n')
        print(json.dumps(dict(status='NEEDS_REVIEWED_LANDMARKS', template=str(template), hardware_motion=False)))
        return
    template = yaml.safe_load((args.workspace / 'src/multi_arm_manipulation_UWA/config/digitization/object_scan.yaml').read_text())
    estimate = prepare(args.oak_result, args.landmarks, args.output, template)
    print(json.dumps(dict(status='COARSE_ESTIMATE', dimensions_m=estimate['dimensions_m'],
                         board_rms_px=estimate['board_rms_native_px'], planning_geometry=str(args.output / 'scan_geometry.yaml'),
                         absolute_accuracy_validated=False, hardware_motion=False)))


if __name__ == '__main__':
    main()

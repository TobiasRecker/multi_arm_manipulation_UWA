"""Image-only eye-in-hand fit. No layout, camera mount, world TF or truth input.

M_i X C_i = Y; M=base<-tool0, X=tool0<-camera, C=camera<-board,
Y=base<-board. Validation observations never participate in fitting.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from uwa_cell_gazebo.charuco import pose_error


def mean_pose(poses):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_matrix(np.array([p[:3, :3] for p in poses])).mean().as_matrix()
    result[:3, 3] = np.mean([p[:3, 3] for p in poses], axis=0)
    return result


def pack(matrix):
    return np.r_[Rotation.from_matrix(matrix[:3, :3]).as_rotvec(), matrix[:3, 3]]


def unpack(vector):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_rotvec(vector[:3]).as_matrix()
    result[:3, 3] = vector[3:6]
    return result


def diverse(records):
    if len(records) < 12:
        raise ValueError('At least twelve distinct fitting poses are required')
    matrices = [np.asarray(r['T_base_tool0'], float) for r in records]
    angles = np.array([Rotation.from_matrix(matrices[0][:3, :3].T @ m[:3, :3]).as_rotvec()
                       for m in matrices[1:]])
    singular = np.linalg.svd(angles, compute_uv=False)
    if singular[1] < np.radians(10) or singular[1] / max(singular[0], 1e-12) < .1:
        raise ValueError('Insufficient rotations about two non-parallel axes')
    unique = []
    for m in matrices:
        if not any(pose_error(m, other)['translation_m'] < .001 and
                   pose_error(m, other)['rotation_deg'] < .5 for other in unique):
            unique.append(m)
    if len(unique) < .9 * len(matrices):
        raise ValueError('Repeated robot poses do not count as independent observations')
    return singular.tolist()


def park(records):
    matrices = [np.asarray(r['T_base_tool0'], float) for r in records]
    cameras = [np.asarray(r['T_camera_board'], float) for r in records]
    rotation, translation = cv2.calibrateHandEye(
        [m[:3, :3] for m in matrices], [m[:3, 3] for m in matrices],
        [c[:3, :3] for c in cameras], [c[:3, 3] for c in cameras], method=cv2.CALIB_HAND_EYE_PARK)
    x = np.eye(4)
    x[:3, :3], x[:3, 3] = rotation, translation.reshape(3)
    if not np.isfinite(x).all() or np.linalg.det(rotation) < .99:
        raise ValueError('Hand-eye initialization is singular')
    y = mean_pose([m @ x @ c for m, c in zip(matrices, cameras)])
    return x, y


def errors(records, x, y):
    residuals, summaries = [], []
    for record in records:
        m = np.asarray(record['T_base_tool0'], float)
        observed = np.asarray(record['T_camera_board'], float)
        predicted = np.linalg.inv(m @ x) @ y
        objects = np.asarray(record['object_points'], float).reshape(-1, 3)
        pixels = np.asarray(record['image_points'], float).reshape(-1, 2)
        k, d = np.asarray(record['camera_matrix'], float), np.asarray(record['distortion'], float)
        projected = cv2.projectPoints(objects, cv2.Rodrigues(predicted[:3, :3])[0],
                                     predicted[:3, 3], k, d)[0].reshape(-1, 2)
        delta = projected - pixels
        depths = (objects @ predicted[:3, :3].T + predicted[:3, 3])[:, 2]
        if np.any(depths <= 0):
            delta = delta + 10000
        residuals.extend(delta.ravel())
        summaries.append({'sample_id': record['sample_id'],
                          'reprojection_rms_px': float(np.sqrt(np.mean(np.sum(delta**2, axis=1)))),
                          **pose_error(m @ x @ observed, y)})
    return np.asarray(residuals), summaries


def refine(records, x, y):
    fit = least_squares(lambda p: errors(records, unpack(p[:6]), unpack(p[6:]))[0],
                        np.r_[pack(x), pack(y)], loss='soft_l1', f_scale=1.,
                        max_nfev=100, xtol=1e-10, ftol=1e-10, gtol=1e-9)
    if not fit.success or not np.isfinite(fit.x).all():
        raise ValueError(f'Joint image refinement did not converge: {fit.message}')
    return unpack(fit.x[:6]), unpack(fit.x[6:])


def solve_robot(records, bootstrap_count=100):
    training = [r for r in records if r['role'] == 'fit']
    validation = [r for r in records if r['role'] == 'validation']
    if len(validation) < 6:
        raise ValueError('At least six held-out validation poses are required')
    singular = diverse(training)
    x, y = refine(training, *park(training))
    summaries = errors(training, x, y)[1]
    rms = np.array([s['reprojection_rms_px'] for s in summaries])
    median = np.median(rms)
    limit = max(1., median + 4 * 1.4826 * np.median(abs(rms-median)))
    kept = [r for r, e in zip(training, rms) if e <= limit]
    if len(kept) < .8 * len(training):
        raise ValueError('More than 20% of fitting observations are outliers')
    excluded = [r['sample_id'] for r, e in zip(training, rms) if e > limit]
    if excluded:
        diverse(kept)
        x, y = refine(kept, x, y)
    held_out = errors(validation, x, y)[1]
    metrics = {
        'median_reprojection_rms_px': float(np.median([s['reprojection_rms_px'] for s in held_out])),
        'board_translation_rms_m': float(np.sqrt(np.mean([s['translation_m']**2 for s in held_out]))),
        'board_rotation_rms_deg': float(np.sqrt(np.mean([s['rotation_deg']**2 for s in held_out]))),
    }
    passed = (metrics['median_reprojection_rms_px'] <= 1. and
              metrics['board_translation_rms_m'] <= .005 and metrics['board_rotation_rms_deg'] <= .5)
    rng, draws = np.random.default_rng(4264), []
    for _ in range(bootstrap_count):
        sampled = [kept[i] for i in rng.integers(0, len(kept), len(kept))]
        try:
            bx, by = park(sampled)
            if np.isfinite(by).all():
                draws.append(by.tolist())
        except (ValueError, cv2.error):
            pass
    return {'passed': passed, 'T_tool0_camera': x.tolist(), 'T_base_board': y.tolist(),
            'fit_count': len(kept), 'validation_count': len(validation), 'excluded_samples': excluded,
            'rotation_singular_values': singular, 'validation': metrics, 'validation_samples': held_out,
            'bootstrap_base_board': draws, 'uncertainty_label': 'bootstrap repeatability; not absolute accuracy'}


def solve_session(records_by_robot, bootstrap_count=100):
    robots = {rid: solve_robot(records, bootstrap_count) for rid, records in records_by_robot.items()}
    pairs = {}
    for table in ('left', 'right'):
        front, rear = f'{table}_front', f'{table}_rear'
        if front not in robots or rear not in robots:
            continue
        relative = np.asarray(robots[front]['T_base_board']) @ np.linalg.inv(robots[rear]['T_base_board'])
        distances = [1000*np.linalg.norm((np.asarray(a) @ np.linalg.inv(b))[:3, 3])
                     for a, b in zip(robots[front]['bootstrap_base_board'], robots[rear]['bootstrap_base_board'])]
        pairs[table] = {'T_front_rear': relative.tolist(),
                        'distance_mm': float(1000*np.linalg.norm(relative[:3, 3])),
                        'distance_bootstrap_interval_mm': np.percentile(distances, [2.5,97.5]).tolist() if distances else None}
    return {'schema_version': 1, 'passed': all(r['passed'] for r in robots.values()),
            'robots': robots, 'relative_bases': pairs,
            'method': 'Park initialization + robust joint image refinement; fixed intrinsics',
            'ground_truth_used_for_fit': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    args = parser.parse_args()
    records = {}
    for path in sorted(args.session.glob('*/sample_*.json')):
        record = json.loads(path.read_text())
        records.setdefault(path.parent.name, []).append(record)
    if not records:
        parser.error('No saved observations found')
    result = solve_session(records)
    output = args.session/'result.json'
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(output, 'PASS' if result['passed'] else 'FAIL')
    return 0 if result['passed'] else 1

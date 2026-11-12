"""Offline diagnostic of saved mobile-board photographs; never activates a fit."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def transform(rvec, tvec):
    result = np.eye(4)
    result[:3, :3] = cv2.Rodrigues(np.asarray(rvec, dtype=float))[0]
    result[:3, 3] = np.asarray(tvec).ravel()
    return result


def vector(matrix):
    return np.r_[Rotation.from_matrix(matrix[:3, :3]).as_rotvec(), matrix[:3, 3]]


def from_vector(value):
    return transform(value[:3], value[3:])


def correspondences(observation):
    objects = np.asarray(observation['object_points'], np.float64)
    pixels = np.asarray(observation['image_points'], np.float64)
    if (objects.shape != (len(pixels), 3) or pixels.ndim != 2 or pixels.shape[1] != 2
            or len(pixels) < 4 or not np.isfinite(objects).all() or not np.isfinite(pixels).all()
            or np.linalg.matrix_rank(objects - objects.mean(axis=0)) < 2):
        raise ValueError('Invalid or collinear board correspondences')
    return objects, pixels


def project(objects, pose, optics):
    return cv2.projectPoints(objects, cv2.Rodrigues(pose[:3, :3])[0], pose[:3, 3],
                            optics['K'], optics['D'])[0].reshape(-1, 2)


def pose_from_observation(observation, optics):
    objects, pixels = correspondences(observation)
    result = cv2.solvePnPGeneric(objects, pixels, optics['K'], optics['D'], flags=cv2.SOLVEPNP_IPPE)
    if not result[0]:
        raise ValueError('Planar PnP failed')
    candidates = []
    for rv, tv in zip(result[1], result[2]):
        rv, tv = cv2.solvePnPRefineLM(objects, pixels, optics['K'], optics['D'], rv, tv)
        pose = transform(rv, tv)
        if np.min((objects @ pose[:3, :3].T + pose[:3, 3])[:, 2]) <= 0:
            continue
        rms = float(np.sqrt(np.mean(np.sum((project(objects, pose, optics) - pixels)**2, axis=1))))
        candidates.append((rms, pose))
    if not candidates:
        raise ValueError('No positive-depth planar pose')
    rms, pose = min(candidates, key=lambda pair: pair[0])
    # Selection uses only this image's reprojection, never nominal robot poses.
    return pose, rms


def mean_pose(poses):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_matrix(np.asarray([p[:3, :3] for p in poses])).mean().as_matrix()
    result[:3, 3] = np.mean([p[:3, 3] for p in poses], axis=0)
    return result


def relative_fit(rows, optics, reference='right_front', target='oak4'):
    """Estimate T_target_reference, fixed intrinsics, training observations only."""
    independent = []
    for row in rows:
        ref, _ = pose_from_observation(row['observations'][reference], optics[reference])
        dst, _ = pose_from_observation(row['observations'][target], optics[target])
        independent.append((dst @ np.linalg.inv(ref), ref))
    initial = np.r_[vector(mean_pose([p[0] for p in independent])),
                    np.concatenate([vector(p[1]) for p in independent])]

    def residual(value):
        relative = from_vector(value[:6])
        errors = []
        for i, row in enumerate(rows):
            ref = from_vector(value[6 + 6*i:12 + 6*i])
            for camera, pose in ((reference, ref), (target, relative @ ref)):
                objects, pixels = correspondences(row['observations'][camera])
                # Comparable angular image residuals despite different resolutions.
                focal = np.mean([optics[camera]['K'][0, 0], optics[camera]['K'][1, 1]])
                errors.extend(((project(objects, pose, optics[camera]) - pixels) / focal).ravel())
        return np.asarray(errors)
    fit = least_squares(residual, initial, loss='soft_l1', f_scale=.0005,
                        max_nfev=180, xtol=1e-11, ftol=1e-11, gtol=1e-11)
    if not fit.success or not np.isfinite(fit.x).all():
        raise ValueError('Relative pose optimizer failed: ' + fit.message)
    return from_vector(fit.x[:6]), dict(training_count=len(rows),
        normalization='pixel residual / mean focal length; soft_l1 scale0.0005',
        optimizer_message=fit.message, optimizer_evaluations=fit.nfev,
        angular_residual_rms_mrad=float(np.sqrt(np.mean(residual(fit.x)**2)) * 1000))


def check_relative(row, relative, optics):
    poses, local_errors = {}, {}
    for name in ('right_front', 'oak4'):
        poses[name], local_errors[name] = pose_from_observation(row['observations'][name], optics[name])
    measured = poses['oak4'] @ np.linalg.inv(poses['right_front'])
    errors = {}
    for name, prediction in [('oak4', relative @ poses['right_front']),
                             ('right_front', np.linalg.inv(relative) @ poses['oak4'])]:
        objects, pixels = correspondences(row['observations'][name])
        residual = project(objects, prediction, optics[name]) - pixels
        rms = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
        focal = np.mean([optics[name]['K'][0, 0], optics[name]['K'][1, 1]])
        errors[name] = dict(cross_camera_rms_px=rms, cross_camera_rms_mrad=1000*rms/focal,
                            local_pnp_rms_px=local_errors[name])
    normal = poses['oak4'][:3, 2]
    center = poses['oak4'][:3, :3] @ np.mean(row['observations']['oak4']['object_points'], axis=0) + poses['oak4'][:3, 3]
    return dict(set_id=row['set_id'], role=row['role'], errors=errors,
        independent_T_oak_front=measured.tolist(),
        relative_translation_difference_mm=float(np.linalg.norm(measured[:3, 3] - relative[:3, 3])*1000),
        relative_rotation_difference_deg=float(np.degrees(Rotation.from_matrix(
            measured[:3, :3] @ relative[:3, :3].T).magnitude())),
        board_normal_in_oak=normal.tolist(), board_center_in_oak_m=center.tolist())


def load_rows(root):
    rows = []
    for manifest in sorted(Path(root).glob('*/set_*/manifest.json')):
        original = manifest.read_bytes()
        data = json.loads(original)
        row = dict(set_id=manifest.parent.name, manifest=str(manifest.resolve()),
            manifest_sha256=hashlib.sha256(original).hexdigest(), observations={}, cameras={},
            all_captured=data.get('all_captured', False), endpoint_joint_delta_rad=data.get('endpoint_joint_delta_rad', {}))
        for name, camera in data['cameras'].items():
            observation = camera.get('observation', {})
            row['observations'][name] = observation
            meta = camera.get('camera_metadata', {})
            row['cameras'][name] = dict(success=camera['success'], corners=observation.get('corners', 0),
                size=observation.get('image_size'), focus=camera.get('settings_before', {}).get('focus',
                    meta.get('standard', {}).get('lens_position')),
                manual_focus=camera.get('manual_focus', meta.get('requested_manual_focus') is not None),
                camera_id=camera.get('camera_identity', {}).get('uniqueCamId', meta.get('device_id')),
                source=camera.get('source'), started_at=camera.get('started_at'), finished_at=camera.get('finished_at'))
            if camera['success']:
                image = manifest.parent / name / camera['image']
                if hashlib.sha256(image.read_bytes()).hexdigest() != camera['sha256']:
                    raise ValueError('Image hash differs: ' + str(image))
        rows.append(row)
    return rows


def image_audit(rows, board_config):
    """Use saved raw images/bursts, never request another hardware image."""
    from .board_capture import MobileBoard
    detector = MobileBoard(board_config)
    audit = []
    for row in rows:
        directory = Path(row['manifest']).parent
        result = dict(set_id=row['set_id'], cameras={})
        for name, observation in row['observations'].items():
            record = json.loads((directory / name / 'record.json').read_text())
            pixels = np.asarray(observation['image_points'])
            ids = observation['corner_ids']
            point_map = dict(zip(ids, pixels))
            edges = []
            columns = board_config['squares_x'] - 1
            for i, point in point_map.items():
                for j in ([i + 1] if i % columns != columns - 1 else []) + [i + columns]:
                    if j in point_map:
                        edges.append(float(np.linalg.norm(point - point_map[j])))
            image = cv2.imread(str(directory / name / record['image']))
            if image is None or [image.shape[1], image.shape[0]] != observation['image_size']:
                raise ValueError('Recorded dimensions do not match decoded original')
            lo = np.maximum(0, np.floor(pixels.min(axis=0) - 5)).astype(int)
            hi = np.minimum(np.array(image.shape[1::-1]), np.ceil(pixels.max(axis=0) + 6)).astype(int)
            gray = cv2.cvtColor(image[lo[1]:hi[1], lo[0]:hi[0]], cv2.COLOR_BGR2GRAY)
            hull = cv2.convexHull(pixels.astype(np.float32))
            info = dict(square_spacing_px_median=float(np.median(edges)),
                detected_corner_hull_fraction_of_image=float(cv2.contourArea(hull)/(image.shape[0]*image.shape[1])),
                board_roi_fraction_gray_ge250=float(np.mean(gray >= 250)),
                board_roi_fraction_gray_le5=float(np.mean(gray <= 5)))
            del image, gray
            if name != 'oak4':
                burst = record['native_burst']
                directory_burst = Path(burst['directory'])
                frame_observations = []
                for frame in ('frame_000.jpg', 'frame_002.jpg'):
                    current = cv2.imread(str(directory_burst / frame))
                    observed, _ = detector.observe(current)
                    frame_observations.append(dict(zip(observed['corner_ids'], np.asarray(observed['image_points']))))
                common = set(frame_observations[0]) & set(frame_observations[1])
                distances = [float(np.linalg.norm(frame_observations[0][i] - frame_observations[1][i])) for i in common]
                info['within_native_burst'] = dict(common_corners=len(common),
                    median_corner_shift_px=float(np.median(distances)) if distances else None,
                    max_corner_shift_px=max(distances) if distances else None,
                    interpretation='image motion plus detector variability between first/last frame; not full three-camera synchronization')
            result['cameras'][name] = info
        audit.append(result)
    return audit


def coverage_figure(rows, output):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    colors = plt.get_cmap('tab10')
    for index, row in enumerate(rows):
        for axis, name in zip(axes, ('right_front', 'right_rear', 'oak4')):
            o = row['observations'][name]
            points = np.asarray(o['image_points']) / np.asarray(o['image_size'])
            axis.scatter(points[:, 0], points[:, 1], s=10, color=colors(index),
                marker='x' if row['role'] == 'validation' else '.',
                label=row['set_id'][4:10] + ' ' + row['role'])
            axis.set(xlim=(0, 1), ylim=(1, 0), title=name.replace('_', ' '),
                xlabel='Image width fraction', ylabel='Image height fraction')
            axis.set_aspect('equal')
            axis.grid(alpha=.2)
    axes[-1].legend(loc='upper left', fontsize=7)
    fig.suptitle('Six saved mobile-board views: detected corner coverage (not complete board outlines)')
    fig.tight_layout()
    fig.savefig(output, dpi=170)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, default=Path.home() / 'UWA_ws')
    p.add_argument('--input', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    ws = args.workspace
    args.output.mkdir(parents=True, exist_ok=False)
    root = args.input or ws / 'setup/calibration/three_camera_mobile'
    rows = load_rows(root)
    eligible = [r for r in rows if r['all_captured'] and all(
        r['cameras'].get(n, {}).get('corners', 0) >= 12 for n in ('right_front', 'right_rear', 'oak4'))]
    if len(eligible) < 5:
        raise ValueError('Need at least five complete >=12-corner sets for this diagnostic protocol')
    # Freeze chronological roles BEFORE computing any pose or choosing a model.
    train_ids = {r['set_id'] for r in eligible[:-2]}
    test_ids = {r['set_id'] for r in eligible[-2:]}
    for row in rows:
        row['role'] = 'fit' if row['set_id'] in train_ids else 'validation' if row['set_id'] in test_ids else 'low_corner_diagnostic'
    profile = ws / 'src/multi_arm_manipulation_UWA/uwa_cell_description/config/calibration/hardware_20261112_v2/right_front_hd_intrinsics.json'
    factory = ws / 'setup/calibration/oak_pose_20261112/oak_rgb_intrinsics.json'
    front, oak = json.loads(profile.read_text()), json.loads(factory.read_text())
    optics = dict(right_front=dict(K=np.asarray(front['camera_matrix']), D=np.asarray(front['distortion'])),
                  oak4=dict(K=np.asarray(oak['camera_matrix_8000x6000']), D=np.asarray(oak['distortion'])))
    for row in rows:
        for name, size, focus, identity in [('right_front', [2592, 1944], 435, '01D10E1900090912'),
                                          ('oak4', [8000, 6000], 116, oak['device_id'])]:
            c = row['cameras'][name]
            if c['size'] != size or c['focus'] != focus or not c['manual_focus'] or c['camera_id'] != identity:
                raise ValueError('Incompatible optical profile/identity in ' + row['set_id'] + ':' + name)
    protocol = dict(schema=1, created_at=datetime.now().astimezone().isoformat(),
        input_root=str(root), rows=rows, training=sorted(train_ids), validation=sorted(test_ids),
        protocol='Chronological first eligible sets train; last two reserved before pose fitting. No image removal by residual.',
        inputs=[dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in (profile, factory)],
        intrinsics_policy='Fixed front operator-accepted below-threshold HD435 and OAK EEPROM scaled8K at matching lens116; no rear VGA scaling',
        diagnostic_only=True, calibration_applied=False)
    save(args.output / 'protocol.json', protocol)
    relative, details = relative_fit([r for r in rows if r['role'] == 'fit'], optics)
    checks = [check_relative(row, relative, optics) for row in rows]
    eligible_checks = [r for r in checks if r['role'] != 'low_corner_diagnostic']
    normals = np.asarray([r['board_normal_in_oak'] for r in eligible_checks])
    centers = np.asarray([r['board_center_in_oak_m'] for r in eligible_checks])
    result = dict(schema=1, diagnostic_only=True, passed=False, calibration_applied=False,
        status='exploratory_relative_pose_not_validated_calibration', transform_convention='T_A_B maps points from B into A',
        T_oak_optical_right_front_optical=relative.tolist(), optimizer=details, per_view=checks,
        diversity=dict(board_normal_max_separation_deg=float(np.degrees(np.max(np.arccos(np.clip(normals @ normals.T, -1, 1))))),
            board_center_extent_in_oak_m=np.ptp(centers, axis=0).tolist()),
        limitations=['Only three training and two held-out views', 'Front intrinsics explicitly adopted below automatic quality threshold',
            'OAK factory intrinsics are not independent validation of this image pipeline',
            'Right-rear native-HD388 intrinsics missing: no rear extrinsic fit attempted',
            'Wrist native sensor focus/exposure readback unavailable during burst',
            'Photos not exposure synchronized; within-set board motion not excluded',
            'No absolute world/table/base mounting calibration, no hardware accuracy claim'])
    save(args.output / 'result.json', result)
    board_config = json.loads(Path(rows[0]['manifest']).read_text())['board']
    save(args.output / 'image-audit.json', image_audit(rows, board_config))
    coverage_figure(rows, args.output / 'coverage.png')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

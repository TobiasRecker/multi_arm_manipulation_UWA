#!/usr/bin/env python3
"""Offline static-board OAK registration candidate; never activates calibration.

Uses matching native optics, disjoint fitting/check corners, and a named
historical base-to-board fit. A repeated static view measures repeatability,
not independent absolute accuracy or a new intrinsic calibration.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'uwa_cell_tasks'))
from uwa_cell_tasks.hardware_registration import board_camera_candidate, board_relative_bases
from uwa_cell_control.board_photo_evaluation import pose_from_observation, project, mean_pose
from uwa_cell_gazebo.charuco import make_board
from uwa_cell_gazebo.configuration import load_layout
from uwa_cell_gazebo.charuco_views import Chain


def source(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def observe(image, optics, config, side):
    board = make_board(config, side)
    parameters = cv2.aruco.DetectorParameters()
    parameters.minMarkerPerimeterRate = .001
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.CharucoDetector(board, cv2.aruco.CharucoParameters(), parameters)
    corners, ids, _, _ = detector.detectBoard(image)
    result = dict(corners=0 if ids is None else len(ids), image_limit_passed=False)
    if ids is None or len(ids) < config['min_corners'] or board.checkCharucoCornersCollinear(ids):
        return dict(result, reason='Insufficient noncollinear board corners')
    objects, pixels = board.matchImagePoints(corners, ids)
    objects, pixels = objects.reshape(-1, 3), pixels.reshape(-1, 2)
    fit = ids.ravel() % 3 != 0
    if fit.sum() < 6 or (~fit).sum() < 4:
        return dict(result, reason='Insufficient disjoint fit/check corners')
    pose, rms = pose_from_observation(dict(object_points=objects[fit], image_points=pixels[fit]), optics)
    check = float(np.sqrt(np.mean(np.sum((project(objects[~fit], pose, optics)-pixels[~fit])**2, axis=1))))
    return dict(result, T_camera_board=pose.tolist(), fit_rms_px=rms,
                held_out_rms_px=check, fit_count=int(fit.sum()), check_count=int((~fit).sum()),
                image_limit_px=config['max_reprojection_error_px'],
                image_limit_passed=check <= config['max_reprojection_error_px'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', type=Path, nargs='+', required=True)
    parser.add_argument('--camera', type=Path, required=True, help='Native matching JSON K,D,image_size,focus')
    parser.add_argument('--model', type=Path, required=True, help='Frozen current hardware-model URDF')
    parser.add_argument('--profile', type=Path, default=REPO/'uwa_cell_description/config/calibration/hardware_20261112_v3')
    parser.add_argument('--anchor-arm', choices=['right_front', 'right_rear'], default='right_rear')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    camera = json.loads(args.camera.read_text())
    optics = {k: np.asarray(camera[k], float) for k in ('K', 'D')}
    layout = load_layout()
    description = args.model.read_text()
    paths = {a: args.profile / (a+('_hd_handeye_result.json' if a == 'right_front' else '_handeye_result.json'))
             for a in ('right_front', 'right_rear')}
    fits = {a: json.loads(p.read_text())['robots'][a] for a, p in paths.items()}
    arm = args.anchor_arm
    anchor = Chain(description, 'world', arm+'_base_link').forward({})
    frames = []
    for path in args.images:
        metadata_path = path.parent/'metadata.json'
        metadata = json.loads(metadata_path.read_text())
        samples = metadata.get('hq_frames') if path.name == 'hq.png' else [metadata.get('standard', metadata.get('hq_single', {}))]
        if not samples or any(s.get('lens_position') != camera['focus'] for s in samples):
            raise ValueError('Image focus metadata does not match optics: '+str(path))
        image = cv2.imread(str(path))
        if image is None or [image.shape[1], image.shape[0]] != camera['image_size']:
            raise ValueError('Image dimensions do not match native optics: '+str(path))
        observation = observe(image, optics, layout['charuco'], 'right')
        row = dict(image=source(path), metadata=source(metadata_path), observation=observation)
        if 'T_camera_board' in observation:
            row['T_world_camera_candidate'] = board_camera_candidate(anchor, fits[arm]['T_base_board'], observation['T_camera_board']).tolist()
        frames.append(row)
    poses = [np.asarray(f['T_world_camera_candidate']) for f in frames if 'T_world_camera_candidate' in f]
    result = dict(created_at=datetime.now(timezone.utc).isoformat(),
        status='DIAGNOSTIC_ONLY_NOT_APPLIED', executable=False, applied=False,
        absolute_accuracy_validated=False, hardware_manipulation_ready=False,
        anchor_frame=arm+'_base_link', T_world_anchor_current=anchor.tolist(),
        inputs=dict(camera=source(args.camera), model=source(args.model),
                    handeye={a: source(p) for a, p in paths.items()}),
        handeye_source_passed={a: bool(f['passed']) for a, f in fits.items()},
        frames=frames,
        assumptions=['Right table board has not moved relative to bases since historical fits',
                     'World/base anchor remains provisional; no world accuracy established'],
        independent_validation_required=True,
        T_right_front_base_right_rear_base_candidate=board_relative_bases(fits['right_front']['T_base_board'], fits['right_rear']['T_base_board']).tolist())
    if poses:
        mean = mean_pose(poses)
        result.update(T_world_camera_candidate=mean.tolist(),
            T_anchor_camera_candidate=(np.linalg.inv(anchor)@mean).tolist(),
            static_view_repeatability_only=dict(count=len(poses),
                max_position_deviation_m=max(float(np.linalg.norm(p[:3,3]-mean[:3,3])) for p in poses),
                max_rotation_deviation_deg=max(float(np.rad2deg(Rotation.from_matrix(p[:3,:3]@mean[:3,:3].T).magnitude())) for p in poses)))
    result['image_and_anchor_checks_passed'] = bool(poses and len(poses)==len(frames)
        and fits[arm]['passed'] and all(f['observation']['image_limit_passed'] for f in frames))
    (args.output/'registration-candidate.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'anchor_frame', 'image_and_anchor_checks_passed', 'hardware_manipulation_ready')}, indent=2))


if __name__ == '__main__':
    main()

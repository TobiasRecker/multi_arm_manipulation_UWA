"""Finite, camera-local carton landmark measurement. No ROS or device clients.

The landmarks are the four upper ends of the vertical OUTER corner seams,
not the contour of one printed wall. The nominal heights come from the
existing mesh, including its unequal corner heights. No print matching.
"""
import hashlib
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np


# Retain the task's 10 mm / 2 degree single-view consistency scale.
POSITION_LIMIT_M = .01
ANGLE_LIMIT_DEG = 2.


def mesh_landmarks(asset_path):
    asset_path = Path(asset_path)
    asset = json.loads(asset_path.read_text())
    path = asset_path.parent / asset['visual_mesh']
    if hashlib.sha256(path.read_bytes()).hexdigest() != asset['files'][asset['visual_mesh']]:
        raise ValueError('Carton mesh differs from its asset manifest')
    root = ET.parse(path).getroot()
    ns = {'c': root.tag.split('}')[0][1:]}
    source = root.find('.//c:geometry/c:mesh/c:source/c:float_array', ns)
    vertices = np.fromstring(source.text, sep=' ').reshape(-1, 3)
    length, width, _ = asset['dimensions_m']
    points = []
    for x, y in [(0, 0), (length, 0), (length, width), (0, width)]:
        seam = vertices[np.isclose(vertices[:, 0], x, atol=1e-7)
                        & np.isclose(vertices[:, 1], y, atol=1e-7)]
        if len(seam) < 2:
            raise ValueError('The mesh does not define all four vertical corner seams')
        points.append([x, y, float(seam[:, 2].max())])
    return np.asarray(points)


def checked_corners(value):
    if (not isinstance(value, list) or len(value) != 4
            or any(not isinstance(p, list) or len(p) != 2 for p in value)):
        raise ValueError('Four visible outer rim seam points [y,x] are required')
    if any(type(v) is not int or not 0 <= v <= 1000 for p in value for v in p):
        raise ValueError('Landmark coordinates must be integers from 0 to 1000')
    points = np.asarray(value, dtype=np.float64)[:, ::-1]
    if not cv2.isContourConvex(points.astype(np.float32)) or abs(cv2.contourArea(points.astype(np.float32))) < 100:
        raise ValueError('The four outer corner seams must form a convex cyclic polygon')
    return points


def native_pixels(context, corners):
    xy = checked_corners(corners)
    x0, y0, x1, y1 = context['image_window']
    return xy / 1000 * [x1-x0, y1-y0] + [x0, y0]


def rigid_xy(model, observed):
    p, q = model.mean(axis=0), observed.mean(axis=0)
    u, _, vt = np.linalg.svd((model-p).T @ (observed-q))
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1] *= -1
        rotation = vt.T @ u.T
    return rotation, q - rotation @ p


def angle_delta(a, b):
    return abs(float(np.arctan2(np.sin(a-b), np.cos(a-b))))


def evaluate(context, corners):
    """Return a local measurement, including rejected per-corner residuals.

    All corner proposals are used. An outlier is never silently dropped.
    Leave-one-out fits assess point consistency, not independent observations.
    """
    pixels = native_pixels(context, corners)
    K, D = np.asarray(context['K'], float), np.asarray(context['D'], float)
    model = np.asarray(context['model_corners_m'], float)
    Tct = np.asarray(context['T_camera_table'], float)
    if (K.shape != (3, 3) or model.shape != (4, 3) or Tct.shape != (4, 4)
            or not all(np.isfinite(v).all() for v in [K, D, model, Tct])):
        raise ValueError('Invalid frozen geometry context')
    Ttc = np.linalg.inv(Tct)
    rays = cv2.undistortPoints(pixels[:, None, :], K, D).reshape(-1, 2)
    rays = np.column_stack([rays, np.ones(4)]) @ Ttc[:3, :3].T
    if np.min(abs(rays[:, 2])) < 1e-5:
        raise ValueError('Viewing rays are parallel to the landmark height plane')
    candidates = []
    # Only proper rigid rotations are fitted. Trying both cyclic orders does
    # not declare 90 degree poses equivalent or permit reflected geometry.
    for reverse, shift in itertools.product([False, True], range(4)):
        order = np.roll(np.arange(4)[::-1] if reverse else np.arange(4), shift)
        p = model[order]
        distances = (p[:, 2]-Ttc[2, 3]) / rays[:, 2]
        if np.any(distances <= 0):
            continue
        observed = Ttc[:3, 3] + distances[:, None]*rays
        R, t = rigid_xy(p[:, :2], observed[:, :2])
        predicted_xy = p[:, :2] @ R.T + t
        errors = np.linalg.norm(predicted_xy-observed[:, :2], axis=1)
        candidates.append((float(np.mean(errors**2)), order, observed, R, t, errors))
    if not candidates:
        raise ValueError('Landmark proposals lie behind the calibrated camera')
    _, order, observed, R, t, errors = min(candidates, key=lambda c: c[0])
    p = model[order]
    yaw = np.arctan2(R[1, 0], R[0, 0])
    centre_model = model[:, :2].mean(axis=0)
    centre = R @ centre_model + t
    spreads, angles = [], []
    for omitted in range(4):
        keep = np.arange(4) != omitted
        r, v = rigid_xy(p[keep, :2], observed[keep, :2])
        spreads.append(float(np.linalg.norm(r @ centre_model + v-centre)))
        angles.append(float(np.rad2deg(angle_delta(np.arctan2(r[1, 0], r[0, 0]), yaw))))
    Tto = np.eye(4)
    Tto[:2, :2], Tto[:2, 3] = R, t
    Tco = Tct @ Tto
    projected = cv2.projectPoints(p, cv2.Rodrigues(Tco[:3, :3])[0], Tco[:3, 3], K, D)[0].reshape(-1, 2)
    residual_pixels = np.linalg.norm(projected-pixels, axis=1)
    success = (max(errors) <= POSITION_LIMIT_M and max(spreads) <= POSITION_LIMIT_M
               and max(angles) <= ANGLE_LIMIT_DEG)
    return dict(success=bool(success), method='outer_rim_seams_mesh_and_calibrated_table',
                error=None if success else 'Landmarks disagree with the existing carton geometry',
                T_table_object=Tto.tolist(), corner_model_indices=order.tolist(),
                observed_native_xy=pixels.tolist(), projected_native_xy=projected.tolist(),
                corner_error_mm=(errors*1000).tolist(), corner_pixel_residual=residual_pixels.tolist(),
                max_corner_error_mm=float(max(errors)*1000),
                leave_one_out_centre_spread_mm=max(spreads)*1000,
                leave_one_out_angle_spread_deg=max(angles),
                limits=dict(corner_error_mm=1000*POSITION_LIMIT_M,
                            centre_spread_mm=1000*POSITION_LIMIT_M, angle_spread_deg=ANGLE_LIMIT_DEG),
                absolute_accuracy_validated=False,
                limitations=['Mesh and its rim heights are image-based estimates, not precise metrology.',
                             'Observed deformations remain in the residuals; no print or perfect rim contour is matched.',
                             'Leave-one-out consistency is not an independent physical accuracy measurement.'])


def model_feedback(context, result):
    """Only image locations and residuals leave the local geometry tool."""
    x0, y0, x1, y1 = context['image_window']
    points = (np.asarray(result['projected_native_xy'])-[x0, y0])/[x1-x0, y1-y0]*1000
    return {key: result[key] for key in ['success', 'error', 'corner_error_mm', 'corner_pixel_residual',
            'max_corner_error_mm', 'leave_one_out_centre_spread_mm', 'leave_one_out_angle_spread_deg', 'limits']} | {
                'projected_rim_corners_2d': points[:, ::-1].round(2).tolist(),
                'projection_is_estimate_not_ground_truth': True}


def overlay(image_path, context, corners, result=None):
    """A real raster evidence image; lines are pixels, independent of HTML CSS."""
    image = cv2.imread(str(image_path))
    x0, y0, x1, y1 = context['image_window']
    image = image[y0:y1, x0:x1].copy()
    scale = min(1120/image.shape[1], 1000/image.shape[0])
    image = cv2.resize(image, None, fx=scale, fy=scale)
    points = np.rint((native_pixels(context, corners)-[x0, y0])*scale).astype(int)
    cv2.polylines(image, [points], True, (0, 0, 0), 7, cv2.LINE_AA)
    cv2.polylines(image, [points], True, (255, 255, 255), 3, cv2.LINE_AA)
    for label, point in zip('ABCD', points):
        cv2.circle(image, tuple(point), 7, (0, 0, 0), -1, cv2.LINE_AA)
        where = (int(np.clip(point[0]+10, 5, image.shape[1]-35)), int(np.clip(point[1]-10, 30, image.shape[0]-5)))
        cv2.putText(image, label, where, cv2.FONT_HERSHEY_SIMPLEX, .85, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(image, label, where, cv2.FONT_HERSHEY_SIMPLEX, .85, (255, 255, 255), 2, cv2.LINE_AA)
    return image

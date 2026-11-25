"""Calibrated synthetic RGB and image-only tabletop timber registration."""

from dataclasses import dataclass
from hashlib import sha256
from itertools import product
from pathlib import Path
import math

import cv2
import numpy as np


BEAM = "crossbeam"
OBSERVATION_SOURCE = "synthetic_rgb_browser"


@dataclass(frozen=True)
class PinholeCamera:
    name: str
    image_size: tuple[int, int]
    K: np.ndarray
    T_world_camera: np.ndarray

    def project(self, world_points):
        points = np.asarray(world_points) - self.T_world_camera[:3, 3]
        optical = points @ self.T_world_camera[:3, :3]
        if np.any(optical[:, 2] <= 0):
            raise ValueError("The synthetic camera cannot render points behind it.")
        projected = optical @ self.K.T
        return projected[:, :2] / projected[:, 2, None]

    def intersect_plane(self, pixels, height_m):
        rays = np.column_stack((pixels, np.ones(len(pixels)))) @ np.linalg.inv(self.K).T
        rays = rays @ self.T_world_camera[:3, :3].T
        origin = self.T_world_camera[:3, 3]
        if np.any(np.abs(rays[:, 2]) < 1e-9):
            return None
        scale = (height_m - origin[2]) / rays[:, 2]
        if np.any(scale <= 0):
            return None
        return origin + rays * scale[:, None]

    def as_dict(self):
        return {"name": self.name, "image_size": list(self.image_size), "K": self.K.tolist(),
                "D": [0.0] * 5, "T_world_camera": self.T_world_camera.tolist()}


def overview_camera(table_z_m, *, opposite=False):
    """Fixed synthetic viewpoints of the right table with zero-distortion optics."""
    width, height = 960, 720
    base = (-.30, .10, 1.86) if opposite else (1.22, -.13, 1.68)
    position = np.array([base[0], base[1], table_z_m + base[2]])
    look_at = np.array([0.47, -0.03, table_z_m + 0.08])
    forward = look_at - position
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0., 0., 1.])
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    pose = np.eye(4)
    pose[:3, :3] = np.column_stack((right, down, forward))
    pose[:3, 3] = position
    intrinsics = np.array([[650., 0., (width - 1) / 2], [0., 650., (height - 1) / 2], [0., 0., 1.]])
    name = "Synthetic OAK Pro view" if opposite else "Synthetic OAK4 view"
    return PinholeCamera(name, (width, height), intrinsics, pose)


def horizontal_pose(center_xyz, yaw_rad):
    cosine, sine = math.cos(yaw_rad), math.sin(yaw_rad)
    pose = np.eye(4)
    pose[:2, :2] = [[cosine, -sine], [sine, cosine]]
    pose[:3, 3] = center_xyz
    return pose


def rectangle(dimensions):
    half_x, half_y = np.asarray(dimensions)[:2] / 2
    return np.array([[-half_x, -half_y], [half_x, -half_y], [half_x, half_y], [-half_x, half_y]])


def _world_points(points, pose):
    return np.asarray(points) @ pose[:3, :3].T + pose[:3, 3]


def _solid_polygon(image, points, color):
    cv2.fillConvexPoly(image, np.rint(points * 16).astype(np.int32), color, cv2.LINE_AA, shift=4)


def _visible_faces(pose, size_m, camera):
    half = np.asarray(size_m) / 2
    camera_local = pose[:3, :3].T @ (camera.T_world_camera[:3, 3] - pose[:3, 3])
    for axis in range(3):
        others = [index for index in range(3) if index != axis]
        for sign in (-1, 1):
            if sign * camera_local[axis] <= half[axis]:
                continue
            vertices = np.zeros((4, 3))
            vertices[:, axis] = sign * half[axis]
            vertices[:, others] = rectangle(2 * half[others])
            points = _world_points(vertices, pose)
            optical_rotation = camera.T_world_camera[:3, :3]
            normal = pose[:3, axis] @ optical_rotation
            optical_point = (points[0] - camera.T_world_camera[:3, 3]) @ optical_rotation
            yield camera.project(points), normal, float(normal @ optical_point), axis == 2 and sign > 0


def _paint_face(image, depth_buffer, camera, face):
    polygon, normal, offset, is_top = face
    height, width = depth_buffer.shape
    x0, y0 = np.maximum(0, np.floor(polygon.min(axis=0)).astype(int))
    x1, y1 = np.minimum([width, height], np.ceil(polygon.max(axis=0)).astype(int) + 2)
    if x1 <= x0 or y1 <= y0:
        return

    depth_roi = depth_buffer[y0:y1, x0:x1]
    pixel_rows, pixel_columns = np.ogrid[y0:y1, x0:x1]
    plane_in_pixels = np.linalg.solve(camera.K.T, normal)
    divisor = plane_in_pixels[0] * pixel_columns + plane_in_pixels[1] * pixel_rows + plane_in_pixels[2]
    depths = np.divide(offset, divisor, out=np.full(depth_roi.shape, np.inf), where=np.abs(divisor) > 1e-9)
    polygon = polygon - [x0, y0]
    mask = np.zeros(depth_roi.shape, dtype=np.uint8)
    _solid_polygon(mask, polygon, 255)
    visible = (mask >= 128) & (depths > 0) & (depths < depth_roi)
    depth_roi[visible] = depths[visible]

    color = (132, 178, 222) if is_top else (73, 109, 157)
    face_rgb = np.full((*depth_roi.shape, 3), color, dtype=np.uint8)
    if is_top:
        for fraction in (0.19, 0.36, 0.63, 0.79):
            start = (1. - fraction) * polygon[0] + fraction * polygon[3]
            end = (1. - fraction) * polygon[1] + fraction * polygon[2]
            # All grain colours remain within the top-face colour model.
            cv2.line(face_rgb, tuple(np.rint(start + 0.05 * (end - start)).astype(int)),
                     tuple(np.rint(end - 0.05 * (end - start)).astype(int)), (117, 163, 209), 1, cv2.LINE_AA)
    image[y0:y1, x0:x1][visible] = face_rgb[visible]


def render_scene(beam_pose, dimensions_m, posts, table_z_m, *, camera=None, occluded=False):
    """Render a synthetic BGR image. Geometry arguments are renderer inputs only."""
    camera = camera or overview_camera(table_z_m)
    width, height = camera.image_size
    image = np.full((height, width, 3), (41, 44, 47), dtype=np.uint8)
    tabletop = rectangle((0.80, 1.70)) + [0.4955, 0.]
    _solid_polygon(image, camera.project(np.column_stack((tabletop, np.full(4, table_z_m)))), (76, 85, 89))

    depth_buffer = np.full((height, width), np.inf)
    faces = list(_visible_faces(np.asarray(beam_pose), dimensions_m, camera))
    for post in posts:
        faces.extend(_visible_faces(np.asarray(post["pose"]), post["size_m"], camera))
    for face in faces:
        _paint_face(image, depth_buffer, camera, face)
    if occluded:
        end_x = float(dimensions_m[0]) / 2
        top_z = float(dimensions_m[2]) / 2
        ends = camera.project(_world_points([[-end_x, 0., top_z], [end_x, 0., top_z]], np.asarray(beam_pose)))
        direction = ends[1] - ends[0]
        length = np.linalg.norm(direction)
        along = direction / length * max(12., length * 0.14)
        across = np.array([-along[1], along[0]]) * 2.0
        center = ends.mean(axis=0)
        screen = np.array([center - along - across, center + along - across,
                           center + along + across, center - along + across])
        _solid_polygon(image, screen, (109, 96, 66))
    return image


def _observed_contours(image):
    blue, green, red = np.moveaxis(image.astype(np.int16), -1, 0)
    mask = (red >= 180) & (blue >= 95) & (red - green >= 20) & (green - blue >= 19)
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    observed = []
    for contour in contours:
        if cv2.contourArea(contour) < 35:
            continue
        pixels = contour[:, 0, :].astype(float)
        height, width = image.shape[:2]
        if np.any(pixels <= 0) or np.any(pixels >= [width - 1, height - 1]):
            continue
        observed.append(pixels)
    return observed


def _wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def _fit_contour(pixels, size_m, table_z_m, camera, yaw_reference_rad):
    template = rectangle(size_m)
    top_z = table_z_m + size_m[2]
    contour = camera.intersect_plane(pixels, top_z)
    if contour is None:
        return None
    planar = np.ascontiguousarray(contour[:, :2], dtype=np.float32)
    outline = cv2.minAreaRect(planar)
    if cv2.contourArea(planar) < 0.86 * size_m[0] * size_m[1]:
        return None
    measured = cv2.boxPoints(outline).astype(float)
    pixels = camera.project(np.column_stack((measured, np.full(4, top_z))))
    center_xy = measured.mean(axis=0)
    possibilities = []
    for winding in (np.arange(4), np.arange(3, -1, -1)):
        for shift in range(4):
            order = np.roll(winding, shift)
            points_xy = measured[order] - center_xy
            left, _, right = np.linalg.svd(template.T @ points_xy)
            rotation = right.T @ left.T
            if np.linalg.det(rotation) < 0:
                continue
            predicted = template @ rotation.T + center_xy
            world_error = np.linalg.norm(predicted - measured[order], axis=1)
            if float(np.max(world_error)) > max(0.0025, 0.14 * min(size_m[:2])):
                continue
            projection = camera.project(np.column_stack((predicted, np.full(4, top_z))))
            pixel_error = np.linalg.norm(projection - pixels[order], axis=1)
            rms_px = float(np.sqrt(np.mean(pixel_error ** 2)))
            if rms_px > 2.4:
                continue
            yaw = math.atan2(rotation[1, 0], rotation[0, 0])
            change = abs(_wrap(yaw - yaw_reference_rad))
            pose = horizontal_pose([*center_xy, table_z_m + size_m[2] / 2], yaw)
            possibilities.append((rms_px, change, {"pose": pose, "pixels": projection,
                                  "rms_px": rms_px, "max_corner_error_m": float(np.max(world_error))}))
    if not possibilities:
        return None
    best_error = min(entry[0] for entry in possibilities)
    equivalent = [entry for entry in possibilities if entry[0] <= best_error + 1e-7]
    return min(equivalent, key=lambda entry: entry[1])[2]


def measure_scene(image, dimensions_m, post_sizes, table_z_m, *, camera=None,
                  post_order_axis=(0., 1.), yaw_reference_rad=math.pi / 2, beam_roi=None):
    """Fit metric rectangles to image pixels. The estimator only sees fixture dimensions and order."""
    camera = camera or overview_camera(table_z_m)
    if tuple(image.shape) != (*camera.image_size[::-1], 3) or image.dtype != np.uint8:
        raise ValueError("Expected a BGR uint8 image matching the calibrated optics.")
    if BEAM in post_sizes:
        raise ValueError("The crossbeam identifier is reserved for pickup geometry.")
    ordered_sizes = {BEAM: dimensions_m, **post_sizes}
    for size in ordered_sizes.values():
        if len(size) != 3 or not np.isfinite(size).all() or min(size) <= 0:
            raise ValueError("Timber dimensions must be three positive finite values in metres.")
    axis = np.asarray(post_order_axis, dtype=float)
    if axis.shape != (2,) or not np.isfinite(axis).all() or np.linalg.norm(axis) < 1e-9:
        raise ValueError("Post order requires a nonzero horizontal fixture axis.")

    contours = _observed_contours(image)
    fits = {}
    for identifier, size in ordered_sizes.items():
        fits[identifier] = {}
        for index, pixels in enumerate(contours):
            if identifier == BEAM and beam_roi is not None:
                left, top, right, bottom = beam_roi
                if np.any(pixels < [left, top]) or np.any(pixels > [right, bottom]):
                    continue
            fit = _fit_contour(pixels, size, table_z_m, camera, yaw_reference_rad)
            if fit is not None:
                fits[identifier][index] = fit

    evidence = {"observed_components": len(contours),
                "candidate_counts": {key: len(value) for key, value in fits.items()}}
    if any(not fit for fit in fits.values()):
        missing = ", ".join(key for key, value in fits.items() if not value)
        evidence.update(status="NOT_LOCALIZED", reason=f"Complete rectangular face unavailable: {missing}.")
        return evidence

    identifiers = list(ordered_sizes)
    assignments = []
    for indices in product(*fits.values()):
        if len(set(indices)) != len(identifiers):
            continue
        fit_set = {key: fits[key][index] for key, index in zip(identifiers, indices)}
        positions = [float(fit_set[key]["pose"][:2, 3] @ axis) for key in post_sizes]
        if all(first < second for first, second in zip(positions, positions[1:])):
            assignments.append(fit_set)
            if len(assignments) > 1:
                break
    if len(assignments) != 1:
        status = "AMBIGUOUS" if assignments else "NOT_LOCALIZED"
        evidence.update(status=status, reason="No unique complete assignment of timber faces in fixture order.")
        return evidence

    evidence.update(status="VALID", reason="Calibrated rectangular top faces measured in synthetic RGB.")
    evidence["fits"] = assignments[0]
    return evidence


def _artifact_png(path, image):
    encoded, data = cv2.imencode(".png", image)
    if not encoded:
        raise RuntimeError("Could not encode the synthetic camera evidence.")
    path.write_bytes(data.tobytes())


def _overlay(image, fits):
    annotated = image.copy()
    for identifier, fit in fits.items():
        pixels = np.rint(fit["pixels"]).astype(np.int32)
        color = (225, 244, 127) if identifier == BEAM else (132, 237, 174)
        cv2.polylines(annotated, [pixels], True, color, 2, cv2.LINE_AA)
        center = tuple(np.rint(pixels.mean(axis=0)).astype(int))
        cv2.drawMarker(annotated, center, color, cv2.MARKER_CROSS, 12, 2, cv2.LINE_AA)
        origin = (max(2, center[0] - 30), max(16, center[1] - 13))
        cv2.putText(annotated, identifier, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.56, (31, 37, 37), 4, cv2.LINE_AA)
        cv2.putText(annotated, identifier, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.56, color, 1, cv2.LINE_AA)
    return annotated


def _pose_error(candidate, reference, dimensions):
    truth = np.asarray(reference)
    relative = np.linalg.inv(truth) @ candidate
    yaw = math.atan2(relative[1, 0], relative[0, 0])
    period = math.pi / 2 if abs(dimensions[0] - dimensions[1]) < 1e-9 else math.pi
    equivalent = (yaw + period / 2) % period - period / 2
    return {"center_error_m": float(np.linalg.norm(relative[:3, 3])),
            "yaw_error_deg": abs(math.degrees(equivalent))}


def _beam_region(box_2d, image_size):
    if not isinstance(box_2d, (list, tuple)) or len(box_2d) != 4 or any(
            type(value) is not int or not 0 <= value <= 1000 for value in box_2d):
        raise ValueError("Expected a normalized Hydrogen beam search rectangle.")
    top, left, bottom, right = np.asarray(box_2d) / 1000
    if top >= bottom or left >= right:
        raise ValueError("Hydrogen beam search rectangle has no area.")
    width, height = image_size
    margin = 0.02
    return (max(0., width * (left - margin)), max(0., height * (top - margin)),
            min(width - 1., width * (right + margin)), min(height - 1., height * (bottom + margin)))


def observe_scene(beam_pose, dimensions_m, posts, table_z_m, *, camera=None, occluded=False, output=None,
                  hydrogen=False, post_order_axis=(0., 1.), yaw_reference_rad=math.pi / 2):
    """Generate and measure a browser observation, then audit it against renderer geometry."""
    posts = list(posts)
    sizes = {post["id"]: tuple(post["size_m"]) for post in posts}
    if len(sizes) != len(posts):
        raise ValueError("Fixture posts need distinct identifiers.")
    cameras = (camera,) if camera is not None else (overview_camera(table_z_m), overview_camera(table_z_m, opposite=True))
    views = []
    for view_camera in cameras:
        frame = render_scene(beam_pose, dimensions_m, posts, table_z_m, camera=view_camera, occluded=occluded)
        result = measure_scene(frame, dimensions_m, sizes, table_z_m, camera=view_camera,
                               post_order_axis=post_order_axis, yaw_reference_rad=yaw_reference_rad)
        views.append((view_camera, frame, result))

    valid = [view for view in views if view[2]["status"] == "VALID"]
    camera, image, selected = valid[0] if valid else max(views, key=lambda view: view[2]["candidate_counts"][BEAM])
    evidence = dict(selected)
    evidence["views"] = {view[0].name: {"status": view[2]["status"], "reason": view[2]["reason"],
                                      "candidate_counts": view[2]["candidate_counts"]} for view in views}
    if len(valid) == 2:
        second_fits = valid[1][2]["fits"]
        comparison = {key: _pose_error(selected["fits"][key]["pose"], second_fits[key]["pose"], size)
                      for key, size in {BEAM: dimensions_m, **sizes}.items()}
        evidence["view_comparison"] = comparison
        if any(error["center_error_m"] > .005 or error["yaw_error_deg"] > 2. for error in comparison.values()):
            evidence.pop("fits")
            evidence.update(status="AMBIGUOUS", reason="The two calibrated synthetic fits disagree.")

    if hydrogen:
        if evidence["status"] == "VALID":
            evidence["hydrogen"] = {"status": "not_needed"}
        else:
            try:
                if callable(hydrogen):
                    suggest = hydrogen
                else:
                    from wood_frame_hydrogen import suggest_synthetic_beam
                    suggest = suggest_synthetic_beam
                hints = dict(suggest(image.copy()))
                if hints.get("status") == "found" and not valid:
                    region = _beam_region(hints.get("box_2d"), camera.image_size)
                    retry = measure_scene(image, dimensions_m, sizes, table_z_m, camera=camera, beam_roi=region,
                                          post_order_axis=post_order_axis, yaw_reference_rad=yaw_reference_rad)
                    hints["remeasurement"] = {"status": retry["status"], "reason": retry["reason"],
                                              "candidate_counts": retry["candidate_counts"], "beam_roi_px": list(region)}
                    if retry["status"] == "VALID":
                        evidence.update(retry)
                evidence["hydrogen"] = hints
            except (ImportError, OSError, RuntimeError, ValueError, TypeError, TimeoutError) as error:
                evidence["hydrogen"] = {"status": "unavailable", "reason": str(error)}

    fits = evidence.pop("fits", {})
    evidence.update(camera=camera.name, calibration=camera.as_dict(), source=OBSERVATION_SOURCE,
                    image_pixel_sha256=sha256(image.tobytes()).hexdigest(),
                    beam_pose=fits[BEAM]["pose"].tolist() if fits else None,
                    post_poses={key: fits[key]["pose"].tolist() for key in sizes if key in fits},
                    residuals={key: {field: value for field, value in fit.items() if field.endswith(("_px", "_m"))}
                               for key, fit in fits.items()})
    references = {BEAM: (beam_pose, dimensions_m), **{post["id"]: (post["pose"], sizes[post["id"]]) for post in posts}}
    evidence["audit"] = {"synthetic_occluder": bool(occluded),
                         "pose_errors": {key: _pose_error(fit["pose"], *references[key]) for key, fit in fits.items()}}
    if output is not None:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        evidence.update(image="localization.png", overlay="localization-overlay.png")
        _artifact_png(directory / evidence["image"], image)
        _artifact_png(directory / evidence["overlay"], _overlay(image, fits))
        for index, (view_camera, frame, result) in enumerate(views, 1):
            view = evidence["views"][view_camera.name]
            if view_camera is camera:
                view.update(image=evidence["image"], overlay=evidence["overlay"])
            else:
                view.update(image=f"localization-view-{index}.png", overlay=f"localization-view-{index}-overlay.png")
                _artifact_png(directory / view["image"], frame)
                _artifact_png(directory / view["overlay"], _overlay(frame, result.get("fits", {})))
    return evidence


def observe_pickup(center_xy_m, yaw_rad, dimensions_m, table_z_m, **kwargs):
    """Browser shortcut for a scene containing just the loose crossbeam."""
    pose = horizontal_pose([*center_xy_m, table_z_m + dimensions_m[2] / 2], yaw_rad)
    return observe_scene(pose, dimensions_m, (), table_z_m, **kwargs)

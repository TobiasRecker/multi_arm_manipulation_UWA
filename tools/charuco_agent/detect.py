#!/usr/bin/env python3
"""Offline, reproducible ChArUco evidence in native sensor coordinates."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
import yaml


def make_board(config):
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config['dictionary']))
    ids = config['marker_ids']
    if len(ids) != len(set(ids)) or any(i < 0 or i >= dictionary.bytesList.shape[0] for i in ids):
        raise ValueError('Invalid or duplicate marker IDs in board definition')
    board = cv2.aruco.CharucoBoard((config['squares_x'], config['squares_y']),
                                    config['square_length'], config['marker_length'],
                                    dictionary, np.array(ids, np.int32))
    board.setLegacyPattern(config.get('legacy_pattern', False))
    return board


def detect_quads(gray, board, config, method):
    height, width = gray.shape
    longest = {'native': max(gray.shape), 'overview': 1800, 'contrast': 3000}[method]
    factor = min(1., longest / max(gray.shape))
    reduced = cv2.resize(gray, (max(1, round(width * factor)), max(1, round(height * factor))),
                         interpolation=cv2.INTER_AREA) if factor < 1 else gray
    if method == 'contrast':
        reduced = cv2.createCLAHE(clipLimit=2., tileGridSize=(8, 8)).apply(reduced)
    params = cv2.aruco.DetectorParameters()
    params.adaptiveThreshWinSizeMax = 55
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.minMarkerPerimeterRate = .003
    params.markerBorderBits = config.get('marker_border_bits', 1)
    corners, ids, _ = cv2.aruco.ArucoDetector(board.getDictionary(), params).detectMarkers(reduced)
    marker_ids = [] if ids is None else ids.flatten().tolist()
    ratio = np.array([width / reduced.shape[1], height / reduced.shape[0]], np.float32)
    quads = []
    for quad in corners:
        points = ((quad.reshape(4, 2) + .5) * ratio - .5).astype(np.float32)
        if factor < 1 and np.all(points >= 4) and np.all(points <= [width - 5, height - 5]):
            points = refine_native(gray, points)
        quads.append(points)
    return marker_ids, quads, list(reduced.shape[::-1])


def refine_native(gray, points):
    # Very shallow views can make two distinct edges fall inside the same 7x7
    # window. Keep the measured quadrilateral if subpixel refinement drifts.
    trial = points.copy()
    cv2.cornerSubPix(gray, trial, (3, 3), (-1, -1),
                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, .02))
    long_side = max(np.linalg.norm(points - np.roll(points, 1, axis=0), axis=1))
    narrow_extent = cv2.contourArea(points) / max(float(long_side), 1.)
    if max(np.linalg.norm(trial - points, axis=1)) <= min(1.5, .12 * narrow_extent):
        return trial
    return points


def rectified_view(gray, quad, config):
    """Prepare a discovery view. Its four control points never count as detections."""
    corners = np.array(quad, np.float32).reshape(4, 2)
    height, width = gray.shape
    if (not np.isfinite(corners).all() or np.any(corners < 0) or
            np.any(corners > [width - 1, height - 1]) or not cv2.isContourConvex(corners)
            or cv2.contourArea(corners, oriented=True) < 64):
        raise ValueError('Expected four distinct convex clockwise corners inside the original image')
    edge = np.linalg.norm(corners - np.roll(corners, -1, axis=0), axis=1)
    if np.min(edge) < 8:
        raise ValueError('Board quadrilateral edge is too small')
    aspect = config['squares_x'] / config['squares_y']
    out_width = round(min(3000, max(256, edge[0], edge[2], aspect * edge[1], aspect * edge[3])))
    out_height = round(out_width / aspect)
    # Include a white margin around clipped board boundaries for ArUco.
    pad = 12
    dst = np.array([[pad, pad], [pad+out_width-1, pad], [pad+out_width-1, pad+out_height-1],
                    [pad, pad+out_height-1]], np.float32)
    transform = cv2.getPerspectiveTransform(corners, dst)
    inverse = cv2.getPerspectiveTransform(dst, corners)
    discovery = cv2.warpPerspective(gray, transform, (out_width + 2*pad, out_height + 2*pad),
                                    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    return discovery, inverse, dict(corners_px=corners.tolist(), native_to_discovery=transform.tolist(),
                                    discovery_to_native=inverse.tolist(), size=list(discovery.shape[::-1]))


def consistent_markers(board, quads):
    """Fit measured quadrilaterals to the ID-specific layout, in raw pixels."""
    ids = list(quads)
    if len(ids) < 2:
        return ids, None, None
    objects = dict(zip(board.getIds().flatten().tolist(), board.getObjPoints()))
    obj = np.array([objects[i][:, :2] for i in ids], np.float32)
    uv = np.array([quads[i] for i in ids])
    lengths = np.linalg.norm(np.roll(uv, 1, axis=1) - uv, axis=2)
    limit = max(2., .10 * float(np.median(lengths)))
    h, _ = cv2.findHomography(obj.reshape(-1, 2), uv.reshape(-1, 2), cv2.RANSAC, limit)
    if h is None or not np.isfinite(h).all():
        return [], None, None
    predicted = cv2.perspectiveTransform(obj.reshape(-1, 1, 2), h).reshape(uv.shape)
    errors = np.linalg.norm(uv - predicted, axis=2)
    keep = np.max(errors, axis=1) <= limit * 1.5
    if np.sum(keep) < 2:
        # A single quadrilateral can fit a projective transform exactly.
        return [], None, None
    return [i for i, valid in zip(ids, keep) if valid], h, limit


def spread_over_board(board, marker_ids):
    if len(marker_ids) < 3:
        return False
    objects = dict(zip(board.getIds().flatten().tolist(), board.getObjPoints()))
    centers = np.float32([objects[i][:, :2].mean(axis=0) for i in marker_ids])
    return cv2.contourArea(cv2.convexHull(centers)) >= .45 * board.getSquareLength()**2


def estimated_pattern_corners(gray, config, board, source, origin):
    if source['duplicate_ids'] or len(source['charuco']) == len(board.getChessboardCorners()):
        return None
    quads = {m['id']: np.float32(m['corners_px']) - np.float32(origin) for m in source['markers']}
    support, transform, _ = consistent_markers(board, quads)
    if transform is None or not spread_over_board(board, support):
        return None
    w, h = board.getChessboardSize()
    world = np.float32([[0, 0], [w, 0], [w, h], [0, h]]) * config['square_length']
    corners = cv2.perspectiveTransform(world.reshape(4, 1, 2), transform).reshape(4, 2)
    if (not np.isfinite(corners).all() or np.any(corners < 0) or
            np.any(corners > [gray.shape[1]-1, gray.shape[0]-1]) or not cv2.isContourConvex(corners)
            or cv2.contourArea(corners, oriented=True) < 64
            or np.min(np.linalg.norm(corners - np.roll(corners, 1, axis=0), axis=1)) < 8):
        return None
    return corners, support


def measure(gray, board, config, origin, method, discovery, inverse):
    ids, candidates, size = detect_quads(discovery, board, config, method)
    if inverse is not None:
        native = []
        for candidate in candidates:
            points = cv2.perspectiveTransform(candidate.reshape(4, 1, 2), inverse).reshape(4, 2)
            if np.all(points >= 4) and np.all(points <= [gray.shape[1] - 5, gray.shape[0] - 5]):
                points = refine_native(gray, points)
            native.append(points)
        candidates = native
    return interpolate_measurements(gray, board, config, origin, method, ids, candidates, size)


def interpolate_measurements(gray, board, config, origin, method, ids, candidates, size):
    valid = set(config['marker_ids'])
    counts = Counter(ids)
    duplicates = sorted(i for i in valid if counts[i] > 1)
    quads = {i: q for i, q in zip(ids, candidates) if i in valid and counts[i] == 1}
    accepted, h, limit = consistent_markers(board, quads)
    offset = np.array(origin, np.float32)
    markers = [dict(id=i, corners_px=(quads[i] + offset).tolist()) for i in sorted(accepted)]
    points = {}
    rejected_corners = []
    if len(accepted) >= 2:
        # Interpolate on native grayscale samples even for a contrast/overview discovery.
        selected = [quads[i].reshape(1, 4, 2) for i in accepted]
        coords, corner_ids, _, _ = cv2.aruco.CharucoDetector(board).detectBoard(
            gray, markerCorners=selected, markerIds=np.array(accepted, np.int32).reshape(-1, 1))
        if corner_ids is not None:
            for i, coord in zip(corner_ids.ravel().tolist(), coords.reshape(-1, 2)):
                model_xy = board.getChessboardCorners()[i:i+1, :2].reshape(1, 1, 2)
                pred = cv2.perspectiveTransform(model_xy, h).reshape(2)
                if not np.isfinite(coord).all() or np.linalg.norm(coord - pred) > 1.5 * limit:
                    rejected_corners.append(i)
                    continue
                points[i] = (coord + offset).tolist()
    charuco = [dict(id=i, point_px=points[i]) for i in sorted(points)]
    noncollinear = len(points) >= 3 and not board.checkCharucoCornersCollinear(np.array(sorted(points), np.int32))
    return dict(method=method, discovery_size=size, markers=markers, charuco=charuco,
                noncollinear=noncollinear, duplicate_ids=duplicates,
                outlier_ids=sorted(set(quads) - set(accepted)), foreign_ids=sorted(set(ids) - valid),
                candidate_target_ids=sorted(set(ids) & valid), rejected_charuco_ids=sorted(rejected_corners),
                homography_inlier_threshold_px=limit)


def board_report(gray, config, origin, methods, quad):
    board = make_board(config)
    discovery, inverse, warp = (gray, None, None) if quad is None else rectified_view(gray, quad, config)
    passes = [measure(gray, board, config, origin, name, discovery, inverse) for name in methods]
    def rank(p):
        return (len(p['charuco']), len(p['markers']), not p['duplicate_ids'], not p['outlier_ids'])
    first = max(passes, key=rank)
    estimate = estimated_pattern_corners(gray, config, board, first, origin) if quad is None and len(methods) > 1 else None
    transforms = {}
    if estimate is not None:
        corners, support = estimate
        discovery, inverse, derived = rectified_view(gray, corners, config)
        dx, dy = origin
        to_raw = np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]])
        derived.update(corners_px=(corners + [dx, dy]).tolist(),
                       discovery_to_native=(to_raw @ inverse).tolist(),
                       native_to_discovery=(np.array(derived['native_to_discovery']) @ np.linalg.inv(to_raw)).tolist(),
                       estimated_from_marker_ids=support)
        for method in ('native', 'contrast'):
            extra = measure(gray, board, config, origin, method, discovery, inverse)
            extra['method'] = 'board_rectified_' + method
            transforms[extra['method']] = derived
            passes.append(extra)
    selected = max(passes, key=rank)
    duplicates = sorted(set().union(*(p['duplicate_ids'] for p in passes)))
    # A repeated board ID in distant positions across discovery passes can mean
    # two physical boards or a false decode, even when each pass saw it only once.
    positions = {}
    conflicts = set()
    for item in passes:
        for marker in item['markers']:
            quad = np.array(marker['corners_px'])
            center = np.mean(quad, axis=0)
            side = float(np.median(np.linalg.norm(quad - np.roll(quad, 1, axis=0), axis=1)))
            previous = positions.setdefault(marker['id'], [])
            if any(np.linalg.norm(center - prior) > .5 * min(length, side) for prior, length in previous):
                conflicts.add(marker['id'])
            previous.append((center, side))
    markers, corners = selected['markers'], selected['charuco']
    targets = sorted(set().union(*(p['candidate_target_ids'] for p in passes)))
    ambiguous = bool(duplicates or conflicts or (targets and not markers))
    full = len(corners) == len(board.getChessboardCorners()) and not ambiguous
    usable = len(corners) >= 12 and selected['noncollinear'] and not ambiguous
    status = 'ambiguous' if ambiguous else 'full' if full else 'partial' if markers else 'not_detected'
    summaries = [{k: v for k, v in p.items() if k not in ('markers', 'charuco')} |
                 dict(marker_ids=[m['id'] for m in p['markers']], charuco_ids=[c['id'] for c in p['charuco']])
                 for p in passes]
    return dict(board_id=config['board_id'], status=status, selected_pass=selected['method'],
                rectification=transforms.get(selected['method'], warp),
                markers=markers, charuco=corners, full=full, usable=usable,
                review_required=bool(ambiguous or (targets and not usable) or selected['outlier_ids']
                                     or selected['rejected_charuco_ids']), duplicate_ids=duplicates,
                conflicting_ids=sorted(conflicts), outlier_ids=selected['outlier_ids'],
                foreign_ids=sorted(set().union(*(p['foreign_ids'] for p in passes))), passes=summaries)


def combine_board(gray, config, first, second):
    """Require independently located marker IDs and native geometry before combining."""
    strongest = max((first, second), key=lambda b: (len(b['charuco']), len(b['markers'])))
    if any(b['duplicate_ids'] or b['conflicting_ids'] or b['status'] == 'ambiguous' for b in (first, second)):
        return strongest, 'duplicate or ambiguous source evidence'
    maps = [{m['id']: np.array(m['corners_px'], np.float32) for m in b['markers']} for b in (first, second)]
    common = sorted(maps[0].keys() & maps[1].keys())
    if len(common) < 3:
        return strongest, 'fewer than three common marker IDs'
    board = make_board(config)
    if not spread_over_board(board, common):
        return strongest, 'common marker IDs are insufficiently spread over the board'
    scales = []
    for mid in common:
        a, b = maps[0][mid], maps[1][mid]
        sides = [cv2.contourArea(q) / max(1., np.linalg.norm(q - np.roll(q, 1, axis=0), axis=1).max()) for q in (a, b)]
        minor = min(sides)
        scales.append(minor)
        if (np.linalg.norm(a.mean(axis=0) - b.mean(axis=0)) > max(1.5, .10 * minor)
                or np.linalg.norm(a - b, axis=1).max() > max(3., .30 * minor)):
            return strongest, 'common marker positions or ordered corners disagree'
    exclusions = set(first['outlier_ids']) | set(second['outlier_ids'])
    best = None
    for base, additional in (maps, maps[::-1]):
        combined = {i: q for i, q in (additional | base).items() if i not in exclusions}
        if len(combined) <= max(map(len, maps)):
            return strongest, 'no complementary unambiguous marker coverage'
        ids = sorted(combined)
        trial = interpolate_measurements(gray, board, config, (0, 0), 'fusion', ids,
                                         [combined[i] for i in ids], list(gray.shape[::-1]))
        if trial['outlier_ids'] or trial['rejected_charuco_ids']:
            continue
        points = {c['id']: np.array(c['point_px']) for c in trial['charuco']}
        if len(points) < max(len(first['charuco']), len(second['charuco'])):
            continue
        original = first['charuco'] + second['charuco']
        tolerance = max(2., .16 * np.median(scales))
        if any(c['id'] not in points or np.linalg.norm(points[c['id']] - c['point_px']) > tolerance
               for c in original):
            continue
        if best is None or len(points) > len(best['charuco']):
            best = trial
    if best is None:
        return strongest, 'combined native measurements lack consistent support or lose supported corners'
    full = len(best['charuco']) == len(board.getChessboardCorners())
    usable = len(best['charuco']) >= 12 and best['noncollinear']
    result = dict(strongest, selected_pass='geometric_fusion', rectification=None, status='full' if full else 'partial',
                  markers=best['markers'], charuco=best['charuco'], full=full, usable=usable,
                  foreign_ids=sorted(set(first['foreign_ids']) | set(second['foreign_ids'])),
                  review_required=bool(exclusions or not usable), outlier_ids=sorted(exclusions), passes=[],
                  fusion_common_ids=common, homography_inlier_threshold_px=best['homography_inlier_threshold_px'])
    return result, 'accepted'


def inspect(image, config, camera, *, expected=None, roi=None, quad=None, method='auto', fuse=None):
    raw = Path(image).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if expected and sha != expected:
        raise ValueError('Image SHA256 differs from the source manifest')
    gray = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE | cv2.IMREAD_IGNORE_ORIENTATION)
    if gray is None:
        raise ValueError('Cannot decode original image')
    del raw
    height, width = gray.shape
    if roi is not None and quad is not None:
        raise ValueError('Choose a rectangular or perspective search region')
    x, y, w, h = roi or [0, 0, width, height]
    if min(x, y) < 0 or min(w, h) < 8 or x + w > width or y + h > height:
        raise ValueError('ROI outside original image or too small')
    methods = ['native', 'overview', 'contrast'] if method == 'auto' else [method]
    crop = gray[y:y+h, x:x+w]
    cv2.setNumThreads(1)
    cv2.setRNGSeed(23)
    definitions = [config, *config.get('alternate_boards', [])]
    result = dict(schema_version=1, opencv_version=cv2.__version__, camera=camera, image_sha256=sha,
                  image_size=[width, height], coordinate_system='unrotated original pixels; u right, v down',
                  board_sha256=hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                  roi=[x, y, w, h], quad=np.asarray(quad).tolist() if quad is not None else None, boards=[])
    if fuse is None:
        result['boards'] = [board_report(crop, item, (x, y), methods, quad) for item in definitions]
    else:
        if len(fuse) != 2 or roi is not None or quad is not None:
            raise ValueError('Fusion requires two detector reports and the full original image')
        inputs = []
        digests = []
        for path in fuse:
            data = Path(path).read_bytes()
            report = json.loads(data)
            if 'fusion' in report or any(report.get(k) != result[k] for k in (
                    'schema_version', 'camera', 'image_size', 'image_sha256', 'board_sha256', 'coordinate_system')):
                raise ValueError('Fusion evidence is unbound or from another image, board or coordinate system')
            inputs.append({b['board_id']: b for b in report['boards']})
            digests.append(hashlib.sha256(data).hexdigest())
        decisions = {}
        for definition in definitions:
            bid = definition['board_id']
            candidate, reason = combine_board(gray, definition, inputs[0][bid], inputs[1][bid])
            decisions[bid] = reason
            result['boards'].append(candidate)
        result['fusion'] = dict(accepted='accepted' in decisions.values(), boards=decisions,
                                source_reports_sha256=digests)
    return result, gray


def draw(gray, result):
    size = result['image_size']
    scale = min(1., 1500 / max(size))
    preview = cv2.resize(gray, (round(size[0]*scale), round(size[1]*scale)), interpolation=cv2.INTER_AREA)
    overlay = cv2.cvtColor(preview, cv2.COLOR_GRAY2BGR)
    for board in result['boards']:
        for marker in board['markers']:
            pixels = np.rint(np.array(marker['corners_px']) * scale).astype(np.int32)
            cv2.polylines(overlay, [pixels], True, (60, 255, 90), 2, cv2.LINE_AA)
            cv2.putText(overlay, str(marker['id']), tuple(pixels[0]), cv2.FONT_HERSHEY_SIMPLEX,
                        .5, (0, 210, 255), 2, cv2.LINE_AA)
        for corner in board['charuco']:
            pixel = tuple(np.rint(np.array(corner['point_px']) * scale).astype(int))
            cv2.drawMarker(overlay, pixel, (255, 80, 255), cv2.MARKER_CROSS, 6, 1)
    return overlay


def output_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        tmp_path = Path(temporary.name)
        try:
            temporary.write(data)
            temporary.flush()
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    source = args.add_mutually_exclusive_group(required=True)
    source.add_argument('--set', type=Path, help='Directory containing manifest.json')
    source.add_argument('--image', type=Path, help='Original sensor image')
    args.add_argument('--camera', required=True)
    args.add_argument('--board', type=Path, help='Frozen board definition, JSON or YAML')
    args.add_argument('--expect-sha256')
    region = args.add_mutually_exclusive_group()
    region.add_argument('--roi', type=int, nargs=4, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'))
    region.add_argument('--quad', type=float, nargs=8, metavar='PX',
                        help='Native pixel pairs in cyclic TL TR BR BL board order')
    region.add_argument('--fuse', type=Path, nargs=2, metavar=('FULL', 'REGIONAL'),
                        help='Test native geometric fusion of two reports for this exact photo')
    args.add_argument('--method', choices=['auto', 'native', 'overview', 'contrast'], default='auto')
    args.add_argument('--output', required=True, type=Path)
    args.add_argument('--overlay', type=Path, help='Downsampled inspection JPEG or PNG')
    opt = args.parse_args()
    if opt.set:
        if opt.board:
            args.error('--set already includes the board configuration')
        if Path(opt.camera).name != opt.camera:
            args.error('Expected a camera name')
        manifest = opt.set / 'manifest.json'
        document = json.loads(manifest.read_text())
        record = document['cameras'][opt.camera]
        filename = Path(record['image'])
        if filename.name != str(filename) or not record.get('sha256'):
            raise ValueError('Original image filename or SHA256 missing')
        if opt.expect_sha256 and opt.expect_sha256 != record['sha256']:
            raise ValueError('Expected hash disagrees with manifest')
        image, config, expected = opt.set / opt.camera / filename, document['board'], record['sha256']
        protected = [manifest, image, opt.set / opt.camera / 'record.json']
    else:
        if not opt.board:
            args.error('--image requires --board')
        image, config, expected = opt.image, yaml.safe_load(opt.board.read_bytes()), opt.expect_sha256
        protected = [image, opt.board]
    if opt.fuse:
        protected.extend(opt.fuse)
    destinations = [opt.output] + ([opt.overlay] if opt.overlay else [])
    if len({p.resolve() for p in destinations + protected}) != len(destinations + protected):
        args.error('Write each artifact separately from its source')
    result, gray = inspect(image, config, opt.camera, expected=expected, roi=opt.roi, quad=opt.quad,
                           method=opt.method, fuse=opt.fuse)
    if opt.overlay:
        suffix = opt.overlay.suffix.lower()
        if suffix not in ('.jpg', '.jpeg', '.png'):
            args.error('Overlay should use a JPEG or PNG extension')
        success, encoded = cv2.imencode(suffix, draw(gray, result))
        if not success:
            raise ValueError('Could not encode overlay')
        output_bytes(opt.overlay, encoded.tobytes())
    output_bytes(opt.output, (json.dumps(result, indent=2, allow_nan=False) + '\n').encode())


if __name__ == '__main__':
    main()

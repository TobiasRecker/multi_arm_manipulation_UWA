#!/usr/bin/env python3
"""Measure the known carton rim in two saved wrist images, for operator review.

The input manifest maps each right arm to an image path and an
expected_rim_pixel [x, y] projected at that image's measured arm pose. The
result is a 2D observation of a textured rim, without jaw or support evidence.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ARMS = ("right_front", "right_rear")


def read_json(path):
    return json.loads(path.read_text())


def fixture_inputs(directory):
    projection = read_json(directory / "wall-alignment.json")
    inputs = {}
    for arm in ARMS:
        record = read_json(directory / f"{arm}-result.json")
        if not isinstance(record, dict) or record.get("arm") != arm or record.get("success") is not True:
            raise ValueError(f"No successful saved image for {arm}")
        image = Path(record["image"])
        # Resolve the camera subdirectory next to the manifest after copying a fixture.
        relative_image = directory / arm / image.parent.name / image.name
        inputs[arm] = {
            "image": str(relative_image if relative_image.is_file() else image),
            "expected_rim_pixel": projection[arm]["original_rim_target_pixel"],
        }
    return inputs


def fit_rim(image):
    height, width = image.shape[:2]
    # The known short-wall print places a yellow rim in the lower central region.
    x0, x1 = round(.32 * width), round(.75 * width)
    y0, y1 = round(.53 * height), round(.98 * height)
    hsv = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (18, 95, 95), (43, 255, 255))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if count < 2:
        return None
    label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    component = labels == label
    stride = max(1, round(height / 240))
    step_width = max(2, round(width / 324))
    points = []
    for row in range(round(.58 * height) - y0, len(component), stride):
        columns = np.flatnonzero(component[row:row + max(1, stride // 2)].any(axis=0))
        if len(columns) >= step_width:
            points.append((float(np.median(columns) + x0), float(row + y0)))
    if len(points) < 8 or points[-1][1] - points[0][1] < .1 * height:
        return None
    pixels = np.asarray(points, dtype=np.float32)
    vx, vy, x, y = map(float, cv2.fitLine(pixels, cv2.DIST_HUBER, 0., .01, .01).ravel())
    if abs(vy) < .5:
        return None
    slope = vx / vy
    intercept = x - slope * y
    residual = pixels[:, 0] - slope * pixels[:, 1] - intercept
    return {
        "line_x_per_y": slope,
        "line_intercept_px": intercept,
        "line_rms_px": float(np.sqrt(np.mean(residual**2))),
        "line_rows_px": [points[0][1], points[-1][1]],
        "sample_count": len(points),
        "angle_from_image_vertical_deg": float(np.rad2deg(np.arctan(slope))),
    }


def check_arm(record, base, output):
    if not isinstance(record, dict) or not isinstance(record.get("image"), str) or not record["image"]:
        raise ValueError("Provide an image path and native expected_rim_pixel [x, y]")
    expected = np.asarray(record.get("expected_rim_pixel"), dtype=float)
    if expected.shape != (2,) or not np.isfinite(expected).all():
        raise ValueError("Expected rim pixel must be a finite [x, y] pair")
    path = (base / record["image"]).resolve()
    raw = path.read_bytes()
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR) if raw else None
    if image is None or min(image.shape[:2]) < 100:
        raise ValueError(f"No readable wrist image of at least 100 × 100 px at {path}")
    height, width = image.shape[:2]
    x, y = expected.tolist()
    visible = 0 <= x < width and 0 <= y < height
    line = fit_rim(image)
    result = {
        "image": str(path),
        "image_sha256": hashlib.sha256(raw).hexdigest(),
        "image_size_px": [width, height],
        "expected_rim_pixel": [x, y],
        "expected_rim_in_frame": visible,
        "observed_rim": line,
    }
    if not visible:
        result.update(status="EXPECTED_RIM_OUT_OF_FRAME", reason="Projected rim target is outside the image")
    elif line is None:
        result.update(status="RIM_NOT_FOUND", reason="No continuous yellow rim segment in the search region")
    elif not line["line_rows_px"][0] <= y <= line["line_rows_px"][1]:
        result.update(status="RIM_NOT_VISIBLE_AT_TARGET", reason="No rim samples cover the target row")
    elif line["line_rms_px"] > .008 * width:
        result.update(status="RIM_UNCERTAIN", reason="Rim points do not support a single line")
    else:
        slope = line["line_x_per_y"]
        offset = (x - slope * y - line["line_intercept_px"]) / np.hypot(1., slope)
        result.update(status="RIM_MEASURED", reason="Visible yellow rim line and projected target compared",
                      signed_image_offset_px=float(offset))

    scale = min(1., 1200 / width)
    preview = cv2.resize(image, (round(scale * width), round(scale * height)), interpolation=cv2.INTER_AREA)
    if line:
        endpoints = [tuple(round(scale * value) for value in (line["line_x_per_y"] * row
                     + line["line_intercept_px"], row)) for row in line["line_rows_px"]]
        cv2.line(preview, *endpoints, (80, 255, 80), 3)
    if visible:
        cv2.drawMarker(preview, (round(scale * x), round(scale * y)), (255, 0, 255), cv2.MARKER_CROSS, 18, 2)
    cv2.rectangle(preview, (0, 0), (preview.shape[1], 32), (0, 0, 0), -1)
    cv2.putText(preview, result["status"], (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2)
    if not cv2.imwrite(str(output), preview):
        raise OSError(f"Could not write {output}")
    result["overlay"] = output.name
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Manifest with image and expected_rim_pixel for both right arms")
    source.add_argument("--fixture-dir", type=Path, help="Saved November 18 native wrist captures and rim projection")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "REVIEW_REQUIRED",
        "reason": "Rim measurements leave the wall midpoint, both jaw clearances and table support unconfirmed",
        "arms": {},
    }
    base = args.fixture_dir.resolve() if args.fixture_dir else args.input.resolve().parent
    try:
        inputs = fixture_inputs(base) if args.fixture_dir else read_json(args.input)
        if not isinstance(inputs, dict) or set(inputs) != set(ARMS):
            raise ValueError("Provide image records for right_front and right_rear")
    except (OSError, KeyError, TypeError, ValueError) as error:
        report.update(status="INVALID_INPUT", reason=str(error))
    else:
        for arm in ARMS:
            try:
                report["arms"][arm] = check_arm(inputs[arm], base, args.output / f"{arm}-overlay.jpg")
            except (OSError, OverflowError, TypeError, ValueError, cv2.error) as error:
                report["arms"][arm] = {"status": "INVALID_INPUT", "reason": str(error)}
                report.update(status="INVALID_INPUT", reason="One or more wrist inputs are unusable")
    result = json.dumps(report, indent=2, allow_nan=False) + "\n"
    (args.output / "result.json").write_text(result)
    print(result, end="")
    return 2 if report["status"] == "INVALID_INPUT" else 0


if __name__ == "__main__":
    raise SystemExit(main())

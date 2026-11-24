#!/usr/bin/env python3
"""Independently inspect and decode the finished professional ChArUco PDFs.

Run from the workspace with .venvs/charuco-print/bin/python. This reads final
PDF vectors and Poppler renders, rather than trusting the generator manifest.
It performs no camera, ROS, or robot I/O.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream


REPO = Path(__file__).resolve().parents[1]
DPI = 300
PX_PER_MM = DPI / 25.4
MM_PER_PT = 25.4 / 72.0
TOLERANCE_MM = 0.2


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raster_resources(resources, seen=None):
    """Find image XObjects, including those nested in Form XObjects."""
    seen = set() if seen is None else seen
    if resources is None:
        return []
    resources = resources.get_object()
    images = []
    objects = resources["/XObject"].get_object() if "/XObject" in resources else {}
    for name, reference in objects.items():
        identity = (getattr(reference, "idnum", None), str(name))
        if identity in seen:
            continue
        seen.add(identity)
        obj = reference.get_object()
        if obj.get("/Subtype") == "/Image":
            images.append(str(name))
        elif obj.get("/Subtype") == "/Form":
            images.extend(raster_resources(obj.get("/Resources"), seen))
    return images


def reference_bars(gray, bounds_px):
    """Measure long rules only in the white exterior margins, independently."""
    x0, y0, x1, y1 = bounds_px
    mask = (gray < 128).astype(np.uint8) * 255
    mask[max(0, int(y0) - 3):min(mask.shape[0], int(y1) + 4),
         max(0, int(x0) - 3):min(mask.shape[1], int(x1) + 4)] = 0
    result = {}
    for name, kernel in (("horizontal", (round(90 * PX_PER_MM), 1)),
                         ("vertical", (1, round(90 * PX_PER_MM)))):
        rules = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_RECT, kernel))
        contours, _ = cv2.findContours(rules, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        lengths = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            length = (width if name == "horizontal" else height) / PX_PER_MM
            if abs(length - 100) <= TOLERANCE_MM:
                lengths.append(float(length))
        result[name + "_100mm_lengths_mm"] = lengths
    return result


def inspect_board(spec, config, pdf_dir, render_dir):
    pdf_path = pdf_dir / spec["filename"]
    reader = PdfReader(pdf_path)
    if len(reader.pages) != 1:
        raise ValueError(f"Expected one PDF page, got {len(reader.pages)}")
    page = reader.pages[0]
    width_mm, height_mm = map(float, spec["page_mm"])
    page_mm = [float(page.mediabox.width) * MM_PER_PT,
               float(page.mediabox.height) * MM_PER_PT]
    page_origin = [float(page.mediabox.left), float(page.mediabox.bottom)]
    if not np.allclose(page_mm, [width_mm, height_mm], atol=0.001, rtol=0):
        raise ValueError(f"Wrong MediaBox size: {page_mm}")
    if page_origin != [0.0, 0.0] or float(page.get("/UserUnit", 1)) != 1 or int(page.get("/Rotate", 0)) % 360:
        raise ValueError("Unexpected PDF origin, UserUnit, or page rotation")
    preferences = reader.trailer["/Root"].get("/ViewerPreferences")
    preferences = preferences.get_object() if preferences is not None else {}
    if str(preferences.get("/PrintScaling")) != "/None":
        raise ValueError("PDF does not disable print scaling")
    images = raster_resources(page.get("/Resources"))
    operations = ContentStream(page.get_contents(), reader).operations
    if images or any(operator == b"INLINE IMAGE" for _, operator in operations):
        raise ValueError(f"Embedded raster image found: {images}")

    render_dir.mkdir(parents=True, exist_ok=True)
    prefix = render_dir / pdf_path.stem
    subprocess.run(["pdftoppm", "-r", str(DPI), "-gray", "-png", "-singlefile",
                    str(pdf_path), str(prefix)], check=True, capture_output=True)
    render_path = prefix.with_suffix(".png")
    gray = cv2.imread(str(render_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("Could not read Poppler render")
    preview_path = render_dir / (pdf_path.stem + "_preview.png")
    preview = Image.fromarray(gray)
    preview.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    preview.save(preview_path)

    nx, ny = map(int, spec["squares"])
    square, marker, margin = (float(spec[key]) for key in ("square_mm", "marker_mm", "margin_mm"))
    pattern_mm = [nx * square, ny * square]
    if not np.allclose(np.asarray(pattern_mm) + 2 * margin, [width_mm, height_mm], atol=1e-8, rtol=0):
        raise ValueError("Config pattern and margins do not match page dimensions")
    ids = np.asarray(spec["marker_ids"], dtype=np.int32)
    if len(ids) != nx * ny // 2 or len(set(ids.tolist())) != len(ids):
        raise ValueError("Unexpected marker ID count or repeated IDs")
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config["dictionary"]))
    board = cv2.aruco.CharucoBoard((nx, ny), square, marker, dictionary, ids)
    board.setLegacyPattern(bool(config["legacy_pattern"]))
    detector_parameters = cv2.aruco.DetectorParameters()
    detector_parameters.markerBorderBits = int(config["marker_border_bits"])
    detector = cv2.aruco.CharucoDetector(board, cv2.aruco.CharucoParameters(), detector_parameters)
    corners, corner_ids, marker_corners, marker_ids = detector.detectBoard(gray)
    found_ids = [] if marker_ids is None else sorted(map(int, marker_ids.ravel()))
    expected_corners = (nx - 1) * (ny - 1)
    if found_ids != sorted(ids.tolist()):
        raise ValueError(f"Marker IDs differ: found {found_ids}")
    if corner_ids is None or sorted(map(int, corner_ids.ravel())) != list(range(expected_corners)):
        raise ValueError(f"Not all {expected_corners} ChArUco corners decoded")

    objects = dict(zip(ids.tolist(), board.getObjPoints()))
    edge_errors, marker_position_errors = [], []
    marker_measurements = []
    for decoded_id, decoded_corners in zip(marker_ids.ravel(), marker_corners):
        measured_mm = np.asarray(decoded_corners).reshape(4, 2) / PX_PER_MM
        expected_mm = np.asarray(objects[int(decoded_id)])[:, :2] + margin
        edges = np.linalg.norm(measured_mm - np.roll(measured_mm, -1, axis=0), axis=1)
        edge_errors.extend(abs(edges - marker).tolist())
        marker_position_errors.extend(np.linalg.norm(measured_mm - expected_mm, axis=1).tolist())
        marker_measurements.append({"id": int(decoded_id), "edge_lengths_mm": edges.tolist()})
    corner_objects = board.getChessboardCorners()[:, :2]
    measured_corner_mm = corners.reshape(-1, 2) / PX_PER_MM
    expected_corner_mm = corner_objects[corner_ids.ravel()] + margin
    corner_error_mm = float(np.max(np.linalg.norm(measured_corner_mm - expected_corner_mm, axis=1)))

    expected_bounds = np.asarray([margin, margin, margin + pattern_mm[0], margin + pattern_mm[1]])
    bounds_px = expected_bounds * PX_PER_MM
    left = max(0, int(np.floor(bounds_px[0] - PX_PER_MM)))
    top = max(0, int(np.floor(bounds_px[1] - PX_PER_MM)))
    right = min(gray.shape[1], int(np.ceil(bounds_px[2] + PX_PER_MM)))
    bottom = min(gray.shape[0], int(np.ceil(bounds_px[3] + PX_PER_MM)))
    ys, xs = np.nonzero(gray[top:bottom, left:right] < 128)
    if not len(xs):
        raise ValueError("No black pattern found")
    measured_bounds = np.asarray([left + xs.min(), top + ys.min(),
                                  left + xs.max() + 1, top + ys.max() + 1]) / PX_PER_MM
    bounds_error = float(np.max(abs(measured_bounds - expected_bounds)))
    max_edge_error = float(max(edge_errors))
    max_position_error = float(max(marker_position_errors))
    if max(max_edge_error, max_position_error, corner_error_mm, bounds_error) > TOLERANCE_MM:
        raise ValueError("Raster geometry exceeds tolerance: " + str({
            "marker_edge_mm": max_edge_error, "marker_position_mm": max_position_error,
            "corner_position_mm": corner_error_mm, "pattern_bounds_mm": bounds_error}))
    bars = reference_bars(gray, bounds_px)
    if not bars["horizontal_100mm_lengths_mm"] or not bars["vertical_100mm_lengths_mm"]:
        raise ValueError(f"Missing or wrongly sized 100mm reference rule: {bars}")
    return {"board_id": spec["board_id"], "passed": True, "pdf": str(pdf_path.resolve()),
            "sha256": sha256(pdf_path), "page_mm": page_mm, "vector_only": True,
            "print_scaling": "None", "marker_ids": found_ids,
            "charuco_corner_count": expected_corners, "render_dpi": DPI,
            "render": str(render_path.resolve()), "preview": str(preview_path.resolve()),
            "pattern_bounds_mm": measured_bounds.tolist(),
            "max_pattern_bounds_error_mm": bounds_error,
            "max_marker_edge_error_mm": max_edge_error,
            "max_marker_position_error_mm": max_position_error,
            "max_charuco_position_error_mm": corner_error_mm,
            "reference_bars": bars, "marker_measurements": marker_measurements}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO / "config/print_designs/charuco_professional_v1.json")
    parser.add_argument("--pdf-dir", type=Path, default=REPO / "output/pdf")
    parser.add_argument("--render-dir", type=Path, default=REPO / "tmp/pdfs/charuco_professional_v1")
    parser.add_argument("--output", type=Path, default=REPO / "output/pdf/uwa_charuco_professional_v1_validation.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    report = {"generation_id": config["generation_id"], "config_sha256": sha256(args.config),
              "created_utc": datetime.now(timezone.utc).isoformat(), "opencv_version": cv2.__version__,
              "tolerance_mm": TOLERANCE_MM, "boards": [], "errors": []}
    seen = set()
    for spec in config["boards"]:
        repeated = seen.intersection(spec["marker_ids"])
        if repeated:
            report["errors"].append(f"Repeated marker IDs between boards: {sorted(repeated)}")
        seen.update(spec["marker_ids"])
        try:
            result = inspect_board(spec, config, args.pdf_dir, args.render_dir)
        except Exception as exc:
            result = {"board_id": spec["board_id"], "passed": False,
                      "error": f"{type(exc).__name__}: {exc}"}
        report["boards"].append(result)
    report["passed"] = not report["errors"] and bool(report["boards"]) and all(b["passed"] for b in report["boards"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "report": str(args.output.resolve()),
                      "boards": [{key: value for key, value in board.items() if key in
                                  ("board_id", "passed", "error", "max_marker_edge_error_mm",
                                   "max_pattern_bounds_error_mm")} for board in report["boards"]]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

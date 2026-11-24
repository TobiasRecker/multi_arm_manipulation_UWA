#!/usr/bin/env python3
"""Generate the separate professional ChArUco v1 print set as exact vectors.

Run with .venvs/charuco-print/bin/python from the workspace. No ROS, camera,
robot or active calibration configuration is accessed or changed.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from print_mobile_charuco import black_rectangles


REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "config/print_designs/charuco_professional_v1.json"


def register_fonts():
    font_dir = Path("/usr/share/fonts/truetype/dejavu")
    for family, filename in (("UWA-Sans", "DejaVuSans.ttf"),
                             ("UWA-Sans-Bold", "DejaVuSans-Bold.ttf")):
        pdfmetrics.registerFont(TTFont(family, str(font_dir / filename)))


def draw_annotations(pdf, spec, dictionary_name):
    """Use only the outer rim; leave at least 10 mm clear beside the pattern."""
    width, height = spec["page_mm"]
    ids = spec["marker_ids"]
    pdf.setFillGray(0)
    pdf.setStrokeGray(0)
    pdf.setFont("UWA-Sans-Bold", 9)
    pdf.drawCentredString(width * mm / 2, (height - 8) * mm,
                         f"UWA - {spec['label']} - ChArUco PRO v1")
    pdf.setFont("UWA-Sans", 7)
    pdf.drawCentredString(width * mm / 2, (height - 12) * mm,
                         f"{dictionary_name} | IDs {ids[0]}-{ids[-1]} | "
                         f"{spec['squares'][0]} x {spec['squares'][1]} squares | "
                         f"square {spec['square_mm']:g} mm | marker {spec['marker_mm']:g} mm")
    # Horizontal and vertical controls are outside the clear inner white rim.
    pdf.setLineWidth(0.45)
    x0, x1, y = spec["margin_mm"], spec["margin_mm"] + 100, 8
    pdf.line(x0 * mm, y * mm, x1 * mm, y * mm)
    for x in (x0, x1):
        pdf.line(x * mm, (y - 1) * mm, x * mm, (y + 1) * mm)
    pdf.setFont("UWA-Sans", 7)
    pdf.drawCentredString((x0 + x1) * mm / 2, 11 * mm, "X reference: 100 mm")
    pdf.drawRightString((width - spec["margin_mm"]) * mm, 8 * mm,
                        f"PLATE {width:g} x {height:g} mm | PRINT 100% / ACTUAL SIZE")
    vx, vy0, vy1 = 8, height / 2 - 50, height / 2 + 50
    pdf.line(vx * mm, vy0 * mm, vx * mm, vy1 * mm)
    for yy in (vy0, vy1):
        pdf.line((vx - 1) * mm, yy * mm, (vx + 1) * mm, yy * mm)
    pdf.saveState()
    pdf.translate(5 * mm, height * mm / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, "Y reference: 100 mm")
    pdf.restoreState()


def create(config_path, output_dir):
    config = json.loads(config_path.read_text())
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config["dictionary"]))
    ppm = config["vector_source_pixels_per_mm"]
    border_bits = config["marker_border_bits"]
    modules = dictionary.markerSize + 2 * border_bits
    seen_ids = set()
    register_fonts()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generation_id": config["generation_id"],
        "definition": str(config_path.resolve()),
        "definition_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "dictionary": config["dictionary"],
        "marker_border_bits": border_bits,
        "legacy_pattern": config["legacy_pattern"],
        "opencv_version": cv2.__version__,
        "geometry": "Exact black vector rectangles; seven source pixels/mm; no embedded raster",
        "annotations": "Outer white rim only; inner 10 mm rim around pattern remains blank",
        "active_runtime_configuration_changed": False,
        "boards": [],
    }
    for spec in config["boards"]:
        nx, ny = spec["squares"]
        width, height = spec["page_mm"]
        square, marker, margin = spec["square_mm"], spec["marker_mm"], spec["margin_mm"]
        pattern_width, pattern_height = nx * square, ny * square
        ids = np.array(spec["marker_ids"], dtype=np.int32)
        expected_count = nx * ny // 2
        if (len(ids) != expected_count or len(set(ids.tolist())) != expected_count
                or seen_ids.intersection(ids.tolist()) or min(ids) < 0
                or max(ids) >= len(dictionary.bytesList)):
            raise ValueError(f"Invalid or overlapping marker IDs: {spec['board_id']}")
        seen_ids.update(ids.tolist())
        if not np.allclose([width, height], [pattern_width + 2 * margin,
                                            pattern_height + 2 * margin]):
            raise ValueError("Plate must have the specified uniform white margin")
        square_px, marker_px = square * ppm, marker * ppm
        if (square_px != int(square_px) or marker_px != int(marker_px)
                or int(marker_px) % modules or (int(square_px) - int(marker_px)) % 2):
            raise ValueError("Raster source would quantize a marker module or its centering")
        board = cv2.aruco.CharucoBoard((nx, ny), square / 1000, marker / 1000,
                                      dictionary, ids)
        board.setLegacyPattern(config["legacy_pattern"])
        source = board.generateImage((round(pattern_width * ppm), round(pattern_height * ppm)),
                                     marginSize=0, borderBits=border_bits)
        if source[0, 0] != 0:
            raise ValueError("Unexpected pattern orientation: top-left square must be black")
        rectangles = black_rectangles(source)
        output = output_dir / spec["filename"]
        size = (width * mm, height * mm)
        pdf = canvas.Canvas(str(output), pagesize=size, pageCompression=1, invariant=1,
                            initialFontName="UWA-Sans")
        pdf.setTitle(f"UWA {spec['label']} - ChArUco PRO v1 - {width:g} x {height:g} mm - 1:1")
        pdf.setAuthor("UWA Robot Cell")
        pdf.setSubject(f"{config['dictionary']}; IDs {ids[0]}-{ids[-1]}; "
                       f"squares {square:g} mm; markers {marker:g} mm; "
                       "unscaled professional print master")
        pdf.setViewerPreference("PrintScaling", "None")
        for box in ("crop", "trim", "bleed"):
            pdf.setCropBox(size, name=box)
        pdf.setFillGray(1)
        pdf.rect(0, 0, *size, fill=1, stroke=0)
        path = pdf.beginPath()
        for px, py, pw, ph in rectangles:
            path.rect((margin + px / ppm) * mm,
                      (height - margin - (py + ph) / ppm) * mm,
                      pw / ppm * mm, ph / ppm * mm)
        pdf.setFillGray(0)
        pdf.drawPath(path, fill=1, stroke=0)
        draw_annotations(pdf, spec, config["dictionary"])
        pdf.showPage()
        pdf.save()
        manifest["boards"].append({
            **spec,
            "pdf": str(output.resolve()),
            "pattern_mm": [pattern_width, pattern_height],
            "pattern_origin_on_plate_mm": [margin, margin],
            "expected_marker_count": expected_count,
            "expected_charuco_corners": (nx - 1) * (ny - 1),
            "source_pixels_per_mm": ppm,
            "marker_module_mm": marker / modules,
            "reference_bars_mm": {"x": 100, "y": 100},
            "vector_rectangle_count": len(rectangles),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        })
        print(f"Created {output}: {width:g} x {height:g} mm; "
              f"{expected_count} markers / {(nx - 1) * (ny - 1)} corners")
    manifest_path = output_dir / "uwa_charuco_professional_v1_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Manifest {manifest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=REPO / "output/pdf")
    args = parser.parse_args()
    create(args.config, args.output_dir)

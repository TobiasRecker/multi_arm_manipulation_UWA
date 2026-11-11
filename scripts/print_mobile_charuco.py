#!/usr/bin/env python3
"""Single-page, actual-size A4 target, separate from the fixed table boards.

Run with .venvs/charuco-print/bin/python from the workspace. No ROS or robot I/O.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import yaml
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


REPO = Path(__file__).resolve().parents[1]


def black_rectangles(image):
    """Exact binary pixel runs as vector rectangles; no image interpolation."""
    active = {}
    rectangles = []
    for row in range(image.shape[0] + 1):
        runs = set()
        if row < image.shape[0]:
            changes = np.diff(np.r_[False, image[row] == 0, False].astype(np.int8))
            runs = set(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))
        for run in list(active):
            if run not in runs:
                first = active.pop(run)
                rectangles.append((int(run[0]), first, int(run[1]-run[0]), row-first))
        for run in runs:
            active.setdefault(run, row)
    return rectangles


def create(config_path, output):
    config = yaml.safe_load(config_path.read_text())
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config['dictionary']))
    ids = np.asarray(config['marker_ids'], dtype=np.int32)
    assert len(ids) == config['squares_x']*config['squares_y']//2
    assert len(set(ids.tolist())) == len(ids) and 0 <= min(ids) and max(ids) < len(dictionary.bytesList)
    assert not set(ids.tolist()) & (set(range(17)) | set(range(50, 67))), 'Existing table IDs must remain distinct'
    board = cv2.aruco.CharucoBoard((config['squares_x'], config['squares_y']),
        config['square_length'], config['marker_length'], dictionary, ids)
    board.setLegacyPattern(config['legacy_pattern'])
    # Six pixels/mm makes38mm squares and28mm markers exact integer lengths;
    # each4x4 marker plus border has six modules, each28 source pixels wide.
    pixels_per_mm = 6
    width, height = config['print']['pattern_mm']
    square_mm = config['square_length']*1000
    marker_mm = config['marker_length']*1000
    shape = (round(width*pixels_per_mm), round(height*pixels_per_mm))
    image = board.generateImage(shape, marginSize=0, borderBits=config['marker_border_bits'])
    rectangles = black_rectangles(image)
    x, top = config['print']['pattern_origin_on_paper_mm']
    page_width, page_height = config['print']['page_mm']
    y = page_height-top-height
    assert np.allclose([page_width, page_height], np.array(landscape(A4))/mm)
    assert abs(width-config['squares_x']*config['square_length']*1000) < 1e-8
    assert abs(height-config['squares_y']*config['square_length']*1000) < 1e-8
    assert min(x, top, page_width-x-width, y) >= 10
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=landscape(A4), pageCompression=1)
    pdf.setTitle(f'UWA mobile ChArUco A4 -{square_mm:g}mm squares -100 percent')
    pdf.setAuthor('UWA multi_arm_manipulation')
    pdf.setSubject(f"Robot-mounted target; {config['dictionary']}; IDs{ids[0]}-{ids[-1]}; actual-size printing")
    pdf.setViewerPreference('PrintScaling', 'None')
    pdf.setFillColorRGB(0, 0, 0)
    path = pdf.beginPath()
    for px, py, pw, ph in rectangles:
        path.rect((x+px/pixels_per_mm)*mm,
                  (y+(image.shape[0]-py-ph)/pixels_per_mm)*mm,
                  pw/pixels_per_mm*mm, ph/pixels_per_mm*mm)
    pdf.drawPath(path, stroke=0, fill=1)
    # Labels live in the side margins, leaving the full190mm pattern height.
    pdf.saveState()
    pdf.translate(286.8*mm, 105*mm)
    pdf.rotate(90)
    pdf.setFont('Helvetica-Bold', 7.5)
    pdf.drawCentredString(0, 0, f"UWA MOBILE A4 | {config['dictionary']} | IDs {ids[0]}-{ids[-1]}")
    pdf.restoreState()
    pdf.saveState()
    pdf.translate(290.4*mm, 105*mm)
    pdf.rotate(90)
    pdf.setFont('Helvetica', 7)
    pdf.drawCentredString(0, 0, f"{config['squares_x']}x{config['squares_y']} | square {square_mm:g} mm | marker {marker_mm:g} mm | Print 100% / Actual size")
    pdf.restoreState()
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(.5)
    bar_x, start, end = 7.5, 55., 155.
    pdf.line(bar_x*mm, start*mm, bar_x*mm, end*mm)
    for yy in (start, end):
        pdf.line((bar_x-1.2)*mm, yy*mm, (bar_x+1.2)*mm, yy*mm)
    pdf.saveState()
    pdf.translate(12.5*mm, 105*mm)
    pdf.rotate(90)
    pdf.setFont('Helvetica', 7.5)
    pdf.drawCentredString(0, 0, '100 mm | Kontrollstrecke nach dem Druck nachmessen')
    pdf.restoreState()
    pdf.showPage()
    pdf.save()
    manifest = {'pdf': str(output.resolve()), 'config': str(config_path.resolve()),
        'page_mm': [page_width, page_height], 'pattern_mm': [width, height],
        'pattern_origin_on_paper_mm': [x, top], 'square_mm': config['square_length']*1000,
        'marker_mm': config['marker_length']*1000, 'marker_ids': ids.tolist(),
        'expected_charuco_corners': (config['squares_x']-1)*(config['squares_y']-1),
        'reference_bar_mm': end-start, 'vector_rectangle_count': len(rectangles),
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'opencv_version': cv2.__version__,
        'mount_calibrated': False}
    output.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path,
        default=REPO/'uwa_cell_description/config/mobile_charuco_a4.yaml')
    parser.add_argument('--output', type=Path,
        default=REPO/'output/pdf/uwa_mobile_charuco_A4_1to1.pdf')
    args = parser.parse_args()
    create(args.config, args.output)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Create the actual-size A4 pen marker sheet; no camera or robot I/O.

Run from the workspace with .venvs/charuco-print/bin/python.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

REPO = Path(__file__).resolve().parents[1]
DICTIONARY = "DICT_4X4_100"
# Each ID has exactly one physical size, including across spare copies.
ROWS = [(40, 4, 98, 99), (30, 5, 96, 97), (25, 5, 94, 95),
        (20, 6, 92, 93), (20, 6, 92, 93)]
WHITE_MM = 4


def create(output):
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICTIONARY))
    existing_ids = set(range(17)) | set(range(50, 67)) | set(range(75, 92))
    assert not existing_ids.intersection(range(92, 100))
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=A4, pageCompression=1)
    pdf.setTitle("UWA Stift und Halter - ArUco A4 - 100 Prozent")
    pdf.setAuthor("UWA Robot Cell")
    pdf.setSubject("DICT_4X4_100; IDs 92-99; 20/25/30/40 mm; borderBits=1")
    pdf.setViewerPreference("PrintScaling", "None")
    page_height = A4[1] / mm

    def label(x, top, text, size=8, bold=False):
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(x * mm, (page_height - top) * mm, text)

    label(10, 15, "STIFT + HALTER", 18, True)
    label(10, 22, "26 ArUco-Etiketten | DICT_4X4_100 | IDs 92-99", 10)
    label(10, 29, "A4 HOCHFORMAT | 100 % / Tatsächliche Größe | Keine Seitenanpassung", 8.5, True)
    label(10, 34, "Schwarze Außenkante = Markermaß. 4 mm Weißrand beim Ausschneiden erhalten.", 8)
    label(10, 39, "Kopien sind Ersatz: pro ID nur ein Etikett im Kamerabild. Plan und matt aufkleben.", 8)

    top = 46.0
    placements = []
    for side, count, pen_id, holder_id in ROWS:
        pitch = 192 / count
        cut = side + 2 * WHITE_MM
        for column in range(count):
            marker_id = pen_id if column % 2 == 0 else holder_id
            role = "Adapter" if column % 2 == 0 else "Halter"
            left = 9 + column * pitch + (pitch - cut) / 2
            assert left >= 9 and left + cut <= 201
            # Pale dashed cut guides lie outside the 4 mm white quiet zone.
            pdf.setStrokeColorRGB(0.65, 0.65, 0.65)
            pdf.setLineWidth(0.25)
            pdf.setDash(1.5, 2)
            pdf.rect(left * mm, (page_height - top - cut) * mm,
                     cut * mm, cut * mm, fill=0, stroke=1)
            pdf.setDash()
            # Six modules: four data bits + one black border module per side.
            pattern = cv2.aruco.generateImageMarker(dictionary, marker_id, 6, borderBits=1)
            pdf.setFillColorRGB(0, 0, 0)
            path = pdf.beginPath()
            for row in range(6):
                for col in range(6):
                    if pattern[row, col] == 0:
                        path.rect((left + WHITE_MM + col * side / 6) * mm,
                                  (page_height - top - WHITE_MM - (row + 1) * side / 6) * mm,
                                  side / 6 * mm, side / 6 * mm)
            pdf.drawPath(path, fill=1, stroke=0)
            label(left, top + cut + 3.7, f"ID {marker_id} | {side} mm | {role}", 6.8, True)
            placements.append(dict(id=marker_id, role=role, marker_mm=side,
                                   cut_mm=cut, cut_left_mm=left, cut_top_mm=top))
        top += cut + 9
    assert top == 266
    label(10, 274, "Startvorschlag: ID 92 / 20 mm am Adapter. Haltermarker ersetzt keine Stiftanwesenheitsprüfung.", 7.3)
    label(10, 279, "Greifflächen, Schrauben und Einführöffnung freihalten. Markerbezug zur Greifpose noch einmessen.", 7.3)
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.8)
    pdf.line(10 * mm, (page_height - 286) * mm, 60 * mm, (page_height - 286) * mm)
    for x in (10, 60):
        pdf.line(x * mm, (page_height - 284) * mm, x * mm, (page_height - 288) * mm)
    label(65, 287, "Kontrollstrecke 50 mm - nach dem Druck mit Lineal prüfen", 8, True)
    pdf.showPage()
    pdf.save()
    manifest = dict(dictionary=DICTIONARY, marker_border_bits=1, page_mm=[210, 297],
                    white_margin_mm=WHITE_MM, marker_size_definition="outer black square, including black border",
                    duplicate_policy="spares only; one visible copy per ID",
                    suggested_start=dict(id=92, marker_length_m=0.020, role="adapter"),
                    placements=placements, pdf_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Created {output}: {len(placements)} markers on one A4 page")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "output/pdf/uwa_pen_markers_A4_1to1.pdf")
    create(parser.parse_args().output)

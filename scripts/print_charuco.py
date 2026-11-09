#!/usr/bin/env python3
"""Print the simulation's exact ChArUco patterns as 1:1 vector PDFs.

Source scripts/env.bash first. Additional PDF dependency: python3-reportlab.
Uses the same OpenCV board_image() as Gazebo; does not modify the simulation.
"""
import argparse
from pathlib import Path

import numpy as np
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import yaml

from uwa_cell_gazebo.charuco import board_image, make_board


REPO = Path(__file__).resolve().parents[1]


def black_rectangles(image):
    """Losslessly merge identical black pixel runs into vector rectangles."""
    assert set(np.unique(image)) <= {0, 255}
    active, rectangles = {}, []
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


def crop_marks(pdf, x, y, width, height):
    pdf.setStrokeColorRGB(.25, .25, .25)
    pdf.setLineWidth(.2)
    for xx in (x, x+width):
        for yy in (y, y+height):
            direction_x = -1 if xx == x else 1
            direction_y = -1 if yy == y else 1
            pdf.line(xx+direction_x*1.5*mm, yy, xx+direction_x*4.5*mm, yy)
            pdf.line(xx, yy+direction_y*1.5*mm, xx, yy+direction_y*4.5*mm)


def draw_board(pdf, rectangles, shape, full_width, full_height, x, y, start=0, end=None):
    end = full_width if end is None else end
    pdf.saveState()
    clip = pdf.beginPath()
    clip.rect(x, y, (end-start)*mm, full_height*mm)
    pdf.clipPath(clip, stroke=0, fill=0)
    pdf.translate(x-start*mm, y)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(0, 0, full_width*mm, full_height*mm, stroke=0, fill=1)
    scale = full_width / shape[1]
    assert abs(scale-full_height/shape[0]) < 1e-10
    path = pdf.beginPath()
    for px, py, pw, ph in rectangles:
        path.rect(px*scale*mm, (shape[0]-py-ph)*scale*mm, pw*scale*mm, ph*scale*mm)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawPath(path, stroke=0, fill=1)
    pdf.restoreState()
    crop_marks(pdf, x, y, (end-start)*mm, full_height*mm)


def footer(pdf, left, bar_x, square_mm, tiled=False):
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont('Helvetica', 8)
    pdf.drawString(left, 17*mm, '100% / Tatsächliche Größe. Nicht an die Seite anpassen.')
    pdf.setFont('Helvetica', 7)
    pdf.drawString(left, 11*mm, f'Feldkante nachmessen: {square_mm:g} mm. Plan auf eine feste Unterlage kleben.')
    bar_y = 23*mm if tiled else 12*mm
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(.45)
    pdf.line(bar_x, bar_y, bar_x+100*mm, bar_y)
    for xx in (bar_x, bar_x+100*mm):
        pdf.line(xx, bar_y-1.5*mm, xx, bar_y+1.5*mm)
    pdf.setFont('Helvetica', 7)
    pdf.drawCentredString(bar_x+50*mm, bar_y+2.2*mm, 'Kontrollstrecke: exakt 100 mm')


def new_pdf(path, size, title):
    result = canvas.Canvas(str(path), pagesize=size, pageCompression=1)
    result.setTitle(title)
    result.setAuthor('UWA multi_arm_manipulation')
    result.setSubject('ChArUco original simulation patterns, actual-size 1:1 printing')
    result.setViewerPreference('PrintScaling', 'None')
    return result


def create_pdfs(config, directory):
    directory.mkdir(parents=True, exist_ok=True)
    width = 1000*(config['squares_x']*config['square_length']+2*config['margin'])
    height = 1000*(config['squares_y']*config['square_length']+2*config['margin'])
    if width > 380 or height > 240.00001:
        raise ValueError('This print layout supports boards up to 380 x 240 mm')
    a3_size, a4_size = landscape(A3), A4
    if height*mm > a4_size[1]-50*mm:
        raise ValueError('Board is too tall for two portrait A4 tiles')
    a3_path = directory / 'uwa_charuco_boards_A3_1to1.pdf'
    a4_path = directory / 'uwa_charuco_boards_A4_tiled_1to1.pdf'
    a3 = new_pdf(a3_path, a3_size, 'UWA ChArUco - beide Boards - A3 - Originalgröße 1:1')
    a4 = new_pdf(a4_path, a4_size, 'UWA ChArUco - beide Boards - A4 Kacheln - Originalgröße 1:1')
    overlap = 20.0
    split = width/2
    for table, label in [('left', 'LINKS'), ('right', 'RECHTS')]:
        image = board_image(config, table)
        rectangles = black_rectangles(image)
        ids = make_board(config, table).getIds().tolist()
        subtitle = (f"{config['dictionary']} | IDs {ids[0]}-{ids[-1]} | "
                    f"{config['squares_x']} x {config['squares_y']} Felder | "
                    f"Feld {config['square_length']*1000:g} mm | Marker {config['marker_length']*1000:g} mm")
        x, y = (a3_size[0]-width*mm)/2, (a3_size[1]-height*mm)/2
        a3.setFont('Helvetica-Bold', 13)
        a3.drawString(x, 282*mm, f'TISCH {label} - ChArUco - A3 quer - 1:1')
        a3.setFont('Helvetica', 8)
        a3.drawString(x, 275*mm, subtitle)
        draw_board(a3, rectangles, image.shape, width, height, x, y)
        footer(a3, x, x+200*mm, config['square_length']*1000)
        a3.showPage()
        for tile, (start, end) in enumerate([(0, split+overlap/2), (split-overlap/2, width)], 1):
            tile_width = end-start
            if tile_width*mm > a4_size[0]-30*mm:
                raise ValueError('Board tile exceeds A4 printer-safe area')
            x, y = (a4_size[0]-tile_width*mm)/2, (a4_size[1]-height*mm)/2
            a4.setFont('Helvetica-Bold', 10)
            a4.drawString(15*mm, 283*mm, f'TISCH {label} - A4 Teil {tile}/2 - 1:1')
            a4.setFont('Helvetica', 7)
            a4.drawString(15*mm, 277.5*mm, subtitle)
            a4.drawString(15*mm, 272.5*mm,
                          'Linke Hälfte. An Schnittmarken zuschneiden; 20 mm Überlappung.' if tile == 1
                          else 'Rechte Hälfte zuschneiden; 20 mm deckungsgleich unter die linke legen.')
            draw_board(a4, rectangles, image.shape, width, height, x, y, start, end)
            footer(a4, 15*mm, 55*mm, config['square_length']*1000, tiled=True)
            a4.showPage()
    a3.save()
    a4.save()
    return a3_path, a4_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', type=Path,
                        default=REPO/'uwa_cell_description/config/cell_layout.yaml')
    parser.add_argument('--output-dir', type=Path, default=REPO/'output/pdf')
    args = parser.parse_args()
    config = yaml.safe_load(args.layout.read_text())['charuco']
    for path in create_pdfs(config, args.output_dir):
        print(path.resolve())


if __name__ == '__main__':
    main()

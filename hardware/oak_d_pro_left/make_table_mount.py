#!/usr/bin/env python3
"""Generate the ribbed table mount and a short split-clamp fit sample (mm)."""
import argparse
from math import hypot
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCone
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
from OCP.IFSelect import IFSelect_RetDone
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

# Keep X equal to the reference STEP X, Y to its Z and Z to its -Y.
TUBE_Y = -80.45
BOLT_ROWS = (-13, 85)
BOLT_X = 49
BASE = 8
HEIGHT = 145
LOWER_SCREW = 22
UPPER_SCREW = 135
BAND_Y = -16.5
BAND_WIDTH = 32


def polygon(points):
    poly = BRepBuilderAPI_MakePolygon()
    for point in points:
        poly.Add(gp_Pnt(*point))
    poly.Close()
    return poly.Wire()


def prism(points, vector):
    face = BRepBuilderAPI_MakeFace(polygon(points)).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(*vector)).Shape()


def box(x, y, z, dx, dy, dz):
    return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape()


def cylinder(x, y, z, radius, height):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z), gp_Dir(0, 0, 1)),
                                   radius, height).Shape()


def combine(first, others, operation=BRepAlgoAPI_Fuse):
    for other in others:
        boolean = operation(first, other)
        if not boolean.IsDone():
            raise ValueError(f"{operation.__name__} failed")
        first = boolean.Shape()
    return first


def link(start, end, width):
    x1, y1 = start
    x2, y2 = end
    distance = hypot(x2 - x1, y2 - y1)
    dx = -(y2 - y1) * width / (2 * distance)
    dy = (x2 - x1) * width / (2 * distance)
    return prism([(x1 - dx, y1 - dy, 0), (x2 - dx, y2 - dy, 0),
                  (x2 + dx, y2 + dy, 0), (x1 + dx, y1 + dy, 0)], (0, 0, BASE))


def rib(start, end, width, height):
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    distance = hypot(dx, dy)
    nx = -dy / distance
    ny = dx / distance
    # A broad root continues just into the base, with a taper to the toe.
    profile = [(0, BASE - 1), (1, BASE - 1), (0.98, BASE + 2),
               (0.47, BASE + height * 0.38), (0.18, BASE + height * 0.66),
               (0, BASE + height)]
    points = [(x1 + fraction * dx - nx * width / 2,
               y1 + fraction * dy - ny * width / 2, z) for fraction, z in profile]
    return prism(points, (nx * width, ny * width, 0))


def tab(z, width, front, top):
    # Widen the lower edge of each clamp gradually when printed upright.
    loft = BRepOffsetAPI_ThruSections(True, True)
    for height, half_width, nose in [(z, width / 2, front),
                                     (z + 10, BAND_WIDTH / 2, -22.5),
                                     (top, BAND_WIDTH / 2, -22.5)]:
        loft.AddWire(polygon([
            (-half_width, TUBE_Y + nose, height), (half_width, TUBE_Y + nose, height),
            (half_width, TUBE_Y - 7, height), (-half_width, TUBE_Y - 7, height),
        ]))
    loft.Build()
    return loft.Shape()


def clamp_bolt(z):
    # Round M5 clearance with a self-supporting roof at the top of the hole.
    y = TUBE_Y + BAND_Y
    start = gp_Pnt(-20, y, z)
    bore = BRepPrimAPI_MakeCylinder(gp_Ax2(start, gp_Dir(1, 0, 0)), 2.75, 40).Shape()
    roof = prism([(-20, y - 1.945, z + 1.94), (-20, y + 1.945, z + 1.94),
                  (-20, y, z + 3.89)], (40, 0, 0))
    return combine(bore, [roof])


def entry(z, radius):
    axis = gp_Ax2(gp_Pnt(0, TUBE_Y, z - 1.2), gp_Dir(0, 0, 1))
    return BRepPrimAPI_MakeCone(axis, radius, radius + 1.3, 1.3).Shape()


def table_mount(radius):
    near, far = BOLT_ROWS
    nose = (0, TUBE_Y)
    junction = (0, 40)
    feet = [(x, y) for x in [-BOLT_X, BOLT_X] for y in BOLT_ROWS]
    pieces = [cylinder(x, y, 0, 13, BASE) for x, y in feet]
    pieces += [link(nose, (x, near), 21) for x in [-BOLT_X, BOLT_X]]
    pieces += [link(nose, junction, 20), cylinder(*junction, 0, 10, BASE)]
    pieces += [link(junction, (x, far), 20) for x in [-BOLT_X, BOLT_X]]
    pieces += [rib((x * 0.15, TUBE_Y + 7), (x * 0.73, near - 13), 6, 96)
               for x in [-BOLT_X, BOLT_X]]
    pieces += [rib((0, TUBE_Y + 12), (0, 49), 7, 108),
               cylinder(0, TUBE_Y, BASE - 1, 16.5, HEIGHT - BASE + 1),
               tab(BASE - 1, 24, -12.5, 32),
               tab(115, 23, -12.5, HEIGHT)]
    # The nose and pads are joined by their rails before adding the ribs.
    base = cylinder(0, TUBE_Y, 0, 19.5, BASE)
    solid = combine(base, pieces)
    cuts = [cylinder(x, y, -1, 4.5, BASE + 2) for x, y in feet]
    cuts += [cylinder(0, TUBE_Y, 4, radius, HEIGHT),
             cylinder(0, TUBE_Y, 33, radius + 1, 86),
             box(-1.25, TUBE_Y - 25, 5, 2.5, 26, HEIGHT),
             clamp_bolt(LOWER_SCREW), clamp_bolt(UPPER_SCREW),
             entry(HEIGHT, radius)]
    return combine(solid, cuts, BRepAlgoAPI_Cut)


def fit_sample(radius):
    height = 24
    sleeve = cylinder(0, TUBE_Y, 0, 16.5, height)
    ears = box(-BAND_WIDTH / 2, TUBE_Y - 22.5, 0, BAND_WIDTH, 15.5, height)
    solid = combine(sleeve, [ears])
    cuts = [cylinder(0, TUBE_Y, -1, radius, height + 2),
            box(-1.25, TUBE_Y - 25, -1, 2.5, 26, height + 2),
            clamp_bolt(12), entry(height, radius)]
    return combine(solid, cuts, BRepAlgoAPI_Cut)


def export(shape, path, step=True):
    solids = TopExp_Explorer(shape, TopAbs_SOLID)
    if not solids.More() or not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError(f"Invalid solid for {path}")
    solids.Next()
    if solids.More():
        raise ValueError(f"Disconnected bodies for {path}")
    unifier = ShapeUpgrade_UnifySameDomain(shape, True, True, False)
    unifier.Build()
    shape = unifier.Shape()
    if step:
        writer = STEPControl_Writer()
        if (writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone
                or writer.Write(str(path.with_suffix(".step"))) != IFSelect_RetDone):
            raise RuntimeError(f"STEP export failed for {path}")
    mesh = BRepMesh_IncrementalMesh(shape, 0.025, False, 0.15, False)
    if not mesh.IsDone():
        raise RuntimeError(f"Meshing failed for {path}")
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(path.with_suffix(".stl"))):
        raise RuntimeError(f"STL export failed for {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bore", type=float, default=19.4, help="Clamping bore diameter in mm")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if not 19 <= args.bore <= 21:
        parser.error("Choose a bore between 19 and 21 mm")
    args.output.mkdir(parents=True, exist_ok=True)
    export(table_mount(args.bore / 2), args.output / "rohrhalter-19mm")
    export(fit_sample(args.bore / 2), args.output / "passprobe-19mm", step=False)


if __name__ == "__main__":
    main()

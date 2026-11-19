#!/usr/bin/env python3
"""Generate the COS whiteboard marker adapter and its keyed docking stand in mm."""
import argparse
from math import cos, pi, sin, sqrt
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.IFSelect import IFSelect_RetDone
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS_Compound

REAR_STOP = 46
GRIP_START = 20
ADAPTER_TOP = 49
KEY_HALF = 14
KEY_CLIP = 6
KEY_GAP = 0.65
FUNNEL = 4
SPLIT_GAP = 0.8
FOOT_THICKNESS = 5.5
TIP_CLEARANCE = 5


def box(x, y, z, dx, dy, dz):
    return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape()


def cylinder(radius, length, x=0, y=0, z=0, direction=(0, 0, 1)):
    axis = gp_Ax2(gp_Pnt(x, y, z), gp_Dir(*direction))
    return BRepPrimAPI_MakeCylinder(axis, radius, length).Shape()


def wire(points):
    poly = BRepBuilderAPI_MakePolygon()
    for p in points:
        poly.Add(gp_Pnt(*p))
    poly.Close()
    return poly.Wire()


def prism(points, vector):
    face = BRepBuilderAPI_MakeFace(wire(points)).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(*vector)).Shape()


def loft(sections):
    builder = BRepOffsetAPI_ThruSections(True, True)
    for z, outline in sections:
        builder.AddWire(wire([(x, y, z) for x, y in outline]))
    builder.Build()
    return builder.Shape()


def boolean(initial, operands, operation=BRepAlgoAPI_Fuse):
    for operand in operands:
        result = operation(initial, operand)
        if not result.IsDone():
            raise RuntimeError(f"{operation.__name__} failed")
        initial = result.Shape()
    return initial


def clean(shape):
    merge = ShapeUpgrade_UnifySameDomain(shape, True, True, False)
    merge.Build()
    shape = merge.Shape()
    if not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError("Invalid CAD body")
    return shape


def key_outline(expand=0):
    h = KEY_HALF + expand
    c = KEY_CLIP + (2 - sqrt(2)) * expand
    return [(-h, -h), (h, -h), (h, h-c), (h-c, h), (-h, h)]


def revolve(profile):
    face = BRepBuilderAPI_MakeFace(wire([(radius, 0, z) for radius, z in profile])).Face()
    return BRepPrimAPI_MakeRevol(face, gp_Ax1(gp_Pnt(), gp_Dir(0, 0, 1))).Shape()


def marker_bore(d10, d35, max_diameter):
    # Two short tapered lands touch the barrel near the two measured stations.
    relief = (max_diameter + 1.2) / 2
    slope = (d10 - d35) / 50
    stations = [(-1, relief)]
    for z, diameter in [(REAR_STOP - 35, d35), (REAR_STOP - 10, d10)]:
        radius = (diameter + 0.16) / 2
        stations.extend([(z-5, relief), (z-3, radius-3*slope),
                         (z+3, radius+3*slope), (z+5, relief)])
    stations.append((REAR_STOP, relief))
    return revolve([(0, stations[0][0]), *((r, z) for z, r in stations), (0, REAR_STOP)])


def adapter(d10, d35, max_diameter, pad_width):
    # X is the jaw-closing direction; Y is the width of a finger pad.
    half_pad = (pad_width + 1.2) / 2
    half_y = half_pad + 3.9
    block = box(-17, -half_y, 17, 34, 2*half_y, ADAPTER_TOP-17)
    key = loft([(0, key_outline(-1.2)), (1.5, key_outline()), (17.1, key_outline())])
    rails = [box(x, y, GRIP_START, 1.65, 3.9, ADAPTER_TOP-GRIP_START)
             for x in (-18.6, 16.95) for y in (-half_y, half_pad)]
    blank = boolean(block, [key, *rails])
    cuts = [marker_bore(d10, d35, max_diameter),
            box(-20, -SPLIT_GAP/2, -1, 40, SPLIT_GAP, ADAPTER_TOP+2)]
    for x in (-13, 13):
        for z in (22.5, 39.5):
            cuts.append(cylinder(1.65, 2*half_y+2, x, -half_y-1, z, (0, 1, 0)))
            cuts.append(cylinder(2.95, 3.5, x, -half_y-0.1, z, (0, 1, 0)))
            # Positive-Y half retains a standard M3 nut (5.5 mm across flats).
            nut_r = 5.8 / sqrt(3)
            vertices = [(x+nut_r*cos(i*pi/3), half_y-2.7, z+nut_r*sin(i*pi/3))
                        for i in range(6)]
            cuts.append(prism(vertices, (0, 3, 0)))
    pair = clean(boolean(blank, cuts, BRepAlgoAPI_Cut))
    bodies = TopExp_Explorer(pair, TopAbs_SOLID)
    halves = []
    while bodies.More():
        halves.append(bodies.Current())
        bodies.Next()
    if len(halves) != 2:
        raise ValueError("The adapter must have two separate halves")
    return halves


def dock(length, diameter):
    seat = length - REAR_STOP + FOOT_THICKNESS + TIP_CLEARANCE
    top = seat + 13
    well = max(13.4, (diameter + 8.5)/2)
    # Turn the foot, open well and outward-sloping rim as one connected shell.
    stem_r = well + 3.2
    solid = revolve([(0, 0), (32, 0), (32, FOOT_THICKNESS),
                     (stem_r, FOOT_THICKNESS), (stem_r, seat-7),
                     (29.5, top), (well, top), (well, FOOT_THICKNESS),
                     (0, FOOT_THICKNESS)])
    pocket = loft([(seat, key_outline(KEY_GAP)), (seat+6, key_outline(KEY_GAP)),
                   (top+0.1, key_outline(KEY_GAP+FUNNEL))])
    cuts = [pocket]
    for x in (-25, 25):
        cuts.append(cylinder(2.25, FOOT_THICKNESS+2, x=x, z=-1))
    return clean(boolean(solid, cuts, BRepAlgoAPI_Cut)), seat


def move(shape, dz=0, rotate_x=0):
    transform = gp_Trsf()
    transform.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(1, 0, 0)), rotate_x)
    transform.SetTranslationPart(gp_Vec(0, 0, dz))
    return BRepBuilderAPI_Transform(shape, transform, True).Shape()


def stl(shape, path):
    mesher = BRepMesh_IncrementalMesh(shape, 0.025, False, 0.15, False)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not mesher.IsDone() or not writer.Write(shape, str(path)):
        raise RuntimeError(f"STL export failed: {path}")


def step(shapes, path):
    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    for shape in shapes:
        builder.Add(compound, shape)
    writer = STEPControl_Writer()
    if (writer.Transfer(compound, STEPControl_AsIs) != IFSelect_RetDone
            or writer.Write(str(path)) != IFSelect_RetDone):
        raise RuntimeError(f"STEP export failed: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d10", type=float, default=20, help="Barrel OD 10 mm from rear")
    parser.add_argument("--d35", type=float, default=19, help="Barrel OD 35 mm from rear")
    parser.add_argument("--length", type=float, default=125, help="Uncapped overall length")
    parser.add_argument("--max-od", type=float, default=21, help="Largest barrel OD below the cap")
    parser.add_argument("--pad-width", type=float, default=22, help="Actual Robotiq pad width")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if not (13 <= args.d10 <= args.max_od <= 21.5
            and 13 <= args.d35 <= args.max_od
            and 90 <= args.length <= 160 and 16 <= args.pad_width <= 26):
        parser.error("Check diameters (13–21.5), length (90–160), and pad width (16–26), all in mm")
    halves = adapter(args.d10, args.d35, args.max_od, args.pad_width)
    stand, seat = dock(args.length, args.max_od)
    args.output.mkdir(parents=True, exist_ok=True)
    # In print orientation the concave clamping bore faces upwards on each half.
    for half in halves:
        bounds = Bnd_Box()
        BRepBndLib.AddOptimal_s(half, bounds)
        positive = bounds.CornerMin().Y() > 0
        angle = -pi/2 if positive else pi/2
        name = "mutter" if positive else "schraube"
        bed_offset = bounds.CornerMax().Y() if positive else -bounds.CornerMin().Y()
        stl(move(half, bed_offset, angle), args.output / f"greifadapter-{name}.stl")
    stl(stand, args.output / "tischaufnahme.stl")
    step([stand, *(move(half, seat) for half in halves)], args.output / "marker-werkzeug.step")


if __name__ == "__main__":
    main()

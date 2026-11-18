#!/usr/bin/env python3
"""Export flat-printing, millimetre STL parts using VTK."""
import argparse
from math import cos, pi, sin
from pathlib import Path

from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkPolyDataNormals, vtkTriangleFilter
from vtkmodules.vtkFiltersGeneral import vtkContourTriangulator
from vtkmodules.vtkIOGeometry import vtkSTLWriter


def export_profile(path, outline, holes, thickness):
    points = vtkPoints()
    edges = vtkCellArray()
    loops = []
    for contour in (outline, *holes):
        loop = [points.InsertNextPoint(x, y, 0) for x, y in contour]
        loops.append(loop)
        for start, end in zip(loop, loop[1:] + loop[:1]):
            edges.InsertNextCell(2, (start, end))

    profile = vtkPolyData()
    profile.SetPoints(points)
    profile.SetLines(edges)
    triangulator = vtkContourTriangulator()
    triangulator.SetInputData(profile)
    triangulator.Update()
    if triangulator.GetTriangulationError():
        raise RuntimeError(f"Could not triangulate {path.name}")

    offset = points.GetNumberOfPoints()
    for index in range(offset):
        x, y, _ = points.GetPoint(index)
        points.InsertNextPoint(x, y, thickness)
    faces = vtkCellArray()
    cap = triangulator.GetOutput()
    for index in range(cap.GetNumberOfCells()):
        cell = cap.GetCell(index)
        a, b, c = (cell.GetPointId(i) for i in range(3))
        faces.InsertNextCell(3, (c, b, a))
        faces.InsertNextCell(3, (a + offset, b + offset, c + offset))
    for loop in loops:
        for start, end in zip(loop, loop[1:] + loop[:1]):
            faces.InsertNextCell(4, (start, end, end + offset, start + offset))

    solid = vtkPolyData()
    solid.SetPoints(points)
    solid.SetPolys(faces)
    triangles = vtkTriangleFilter()
    triangles.SetInputData(solid)
    normals = vtkPolyDataNormals()
    normals.SetInputConnection(triangles.GetOutputPort())
    normals.SplittingOff()
    normals.AutoOrientNormalsOn()
    writer = vtkSTLWriter()
    writer.SetInputConnection(normals.GetOutputPort())
    writer.SetFileName(str(path))
    writer.SetFileTypeToBinary()
    if not writer.Write():
        raise RuntimeError(f"Could not write {path}")


def circle_hole(x, diameter, vertices=64):
    radius = diameter / 2
    return [
        (x + radius * cos(2 * pi * i / vertices),
         -radius * sin(2 * pi * i / vertices))
        for i in range(vertices)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tube", type=float, default=40, help="Measured tube width in mm")
    parser.add_argument("--clearance", type=float, default=0.6, help="Total saddle play in mm")
    parser.add_argument("--cable", type=float, default=6, help="USB cable diameter in mm")
    parser.add_argument("--spacing", type=float, default=75, help="Rear M4 hole spacing in mm")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if not (10 <= args.tube <= 80 and 0.2 <= args.clearance <= 2
            and 3 <= args.cable <= 12 and 20 <= args.spacing <= 120):
        parser.error("Expected tube 10–80, clearance 0.2–2, cable 3–12 and spacing 20–120 mm")

    args.output.mkdir(parents=True, exist_ok=True)
    half_span = args.spacing / 2 + 8
    jig = [(-half_span, -9), (half_span, -9), (half_span, 9), (-half_span, 9)]
    holes = [circle_hole(x, 4.5) for x in (-args.spacing / 2, args.spacing / 2)]
    export_profile(args.output / "oak-rear-hole-template.stl", jig, holes, 4)

    half_tube = (args.tube + args.clearance) / 2
    outer = half_tube + 3
    groove = args.cable / 2 + 0.5
    saddle = [
        (-outer, -8), (-half_tube, -8), (-half_tube, 0),
        (half_tube, 0), (half_tube, -8), (outer, -8),
        (outer, 6), (groove, 6), (0, 3), (-groove, 6), (-outer, 6),
    ]
    export_profile(args.output / "usb-cable-saddle.stl", saddle, [], 24)


if __name__ == "__main__":
    main()

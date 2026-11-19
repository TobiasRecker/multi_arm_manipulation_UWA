"""Geometry references in workpiece coordinates, independent of process actuation."""

from dataclasses import dataclass
import math

import numpy as np


def vector(values, size, name):
    result = np.asarray(values, dtype=float)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f'{name} must contain {size} finite coordinates')
    return result


@dataclass(frozen=True)
class SurfaceFrame:
    """Origin, outward normal and direction of the u axis in the workpiece."""

    origin_m: tuple
    outward: tuple
    u_axis: tuple

    def __post_init__(self):
        origin = vector(self.origin_m, 3, 'Surface origin')
        normal = vector(self.outward, 3, 'Surface normal')
        tangent = vector(self.u_axis, 3, 'Surface u axis')
        if (abs(np.linalg.norm(normal) - 1.) > 1e-8 or
                abs(np.linalg.norm(tangent) - 1.) > 1e-8 or abs(normal @ tangent) > 1e-8):
            raise ValueError('Surface normal and u axis must be orthogonal unit vectors')
        for name, value in [('origin_m', origin), ('outward', normal), ('u_axis', tangent)]:
            object.__setattr__(self, name, tuple(value))

    def tool_pose(self, uv_m, clearance_m=0.):
        """Tip pose in the workpiece. Tool +Z points into the surface."""
        uv = vector(uv_m, 2, 'Surface point')
        if not math.isfinite(clearance_m):
            raise ValueError('Clearance must be finite')
        normal = np.asarray(self.outward)
        tangent = np.asarray(self.u_axis)
        transverse = np.cross(normal, tangent)
        pose = np.eye(4)
        pose[:3, :3] = np.column_stack((tangent, -transverse, -normal))
        pose[:3, 3] = self.origin_m + uv[0]*tangent + uv[1]*transverse + clearance_m*normal
        return pose


@dataclass(frozen=True)
class SurfacePolyline:
    """An uninterrupted surface stroke given by ordered (u, v) points in metres."""

    points_uv_m: tuple

    def __post_init__(self):
        points = tuple(tuple(vector(p, 2, 'Polyline point')) for p in self.points_uv_m)
        if len(points) < 2 or any(a == b for a, b in zip(points, points[1:])):
            raise ValueError('Polyline requires at least two points and nonzero consecutive edges')
        object.__setattr__(self, 'points_uv_m', points)

    def record(self):
        return dict(kind='surface_polyline', points_uv_m=[list(p) for p in self.points_uv_m])


@dataclass(frozen=True)
class AxialFeed:
    """Approach, inward feed and withdrawal reference with one fixed tool axis."""

    uv_m: tuple
    clearance_m: float
    depth_m: float

    def __post_init__(self):
        object.__setattr__(self, 'uv_m', tuple(vector(self.uv_m, 2, 'Feed point')))
        if not all(math.isfinite(value) and value > 0 for value in (self.clearance_m, self.depth_m)):
            raise ValueError('Axial clearance and depth must be positive and finite')

    def reference(self, frame):
        heights = (self.clearance_m, 0., -self.depth_m, self.clearance_m)
        return {name: frame.tool_pose(self.uv_m, height) for name, height in
                zip(('approach', 'surface', 'depth', 'withdrawn'), heights)}


def point_segment_distance(point, start, stop):
    edge = stop - start
    fraction = np.clip((point - start) @ edge / (edge @ edge), 0., 1.)
    return np.linalg.norm(point - (start + fraction*edge))

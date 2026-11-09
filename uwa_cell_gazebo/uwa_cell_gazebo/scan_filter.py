"""Non-destructive display masks in world metres, after scan scale and pose."""
import numpy as np
from scipy.spatial.transform import Rotation


def robot_base_center(layout):
    positions = []
    for robot in layout['robots'].values():
        table = layout['tables'][robot['table']]
        local = np.asarray(robot['mount_xyz']) + [0, 0, table['height']]
        positions.append(Rotation.from_euler('xyz', table['rpy']).apply(local) + table['xyz'])
    return np.mean(positions, axis=0)


def filter_reference(xyz, rgb, layout):
    """Return scaled scan-frame points/colors; use world positions only for masks.

    xyz is already scaled, as required by the published scan frame. Masks are
    fixed to the recorded scene, independent of the simulated arm joint states.
    The source arrays and raw import cache are never modified.
    """
    settings = layout['scan']
    xyz, rgb = np.asarray(xyz), np.asarray(rgb)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or rgb.shape != xyz.shape:
        raise ValueError('Reference positions and colors must have matching Nx3 shapes')
    if not np.isfinite(xyz).all():
        raise ValueError('Scaled scan coordinates are not finite; check scan.scale')
    world = Rotation.from_euler('xyz', settings['rpy']).apply(xyz) + settings['xyz']
    if not np.isfinite(world).all():
        raise ValueError('Transformed scan coordinates are not finite')
    keep = np.ones(len(xyz), dtype=bool)
    center = settings.get('crop_center')
    center = robot_base_center(layout) if center is None else np.asarray(center)
    radius = settings.get('crop_radius')
    outside = np.zeros(len(xyz), dtype=bool)
    if radius is not None:
        # Rigid-transform rounding must not discard a point exactly on the sphere.
        outside = np.linalg.norm(world - center, axis=1) > radius + 1e-9
        keep &= ~outside
    counts = {}
    for box in settings.get('exclude_boxes', []):
        inside = np.all((world >= box['min']) & (world <= box['max']), axis=1)
        counts[box['name']] = int(np.count_nonzero(keep & inside))
        keep &= ~inside
    stats = {'input_points': len(xyz), 'output_points': int(keep.sum()),
             'outside_radius': int(outside.sum()), 'excluded_by_box': counts,
             'crop_center_world': center.tolist(), 'crop_radius_m': radius}
    return xyz[keep], rgb[keep], stats

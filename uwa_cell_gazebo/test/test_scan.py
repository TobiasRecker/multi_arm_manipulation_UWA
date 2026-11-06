from pathlib import Path

import numpy as np
import pytest

from uwa_cell_gazebo.configuration import SCAN_DEFAULTS
from uwa_cell_gazebo.scan import convert_scan, prepare_scan, read_vertices


def ply(path, rows):
    # Deliberately reorder fields: the reader must use the header, not column numbers.
    names = ['opacity', 'z', 'x', 'f_dc_2', 'f_dc_0', 'y', 'f_dc_1',
             'scale_2', 'scale_0', 'scale_1']
    data = np.zeros(len(rows), dtype=[(name, '<f4') for name in names])
    for key in ('scale_0', 'scale_1', 'scale_2'):
        data[key] = -6.0
    for index, row in enumerate(rows):
        for key, value in row.items():
            data[key][index] = value
    header = 'ply\nformat binary_little_endian 1.0\nelement vertex ' + str(len(rows)) + '\n'
    header += ''.join(f'property float {name}\n' for name in names) + 'end_header\n'
    path.write_bytes(header.encode() + data.tobytes())
    return path


def test_gaussian_colors_invalid_values_opacity_and_scales(tmp_path):
    red = {'f_dc_0': .5 / .28209479177387814,
           'f_dc_1': -.5 / .28209479177387814, 'f_dc_2': -.5 / .28209479177387814}
    path = ply(tmp_path / 'scan with spaces.ply', [
        {'x': 0, 'opacity': float('inf'), **red}, {'x': 1},
        {'x': float('nan')}, {'x': 2, 'opacity': float('nan')},
        {'x': 3, 'opacity': -20}, {'x': 4, 'scale_1': 2},
        {'x': 5, 'scale_0': float('nan')}, {'x': 6, 'f_dc_1': float('inf')},
    ])
    xyz, rgb, metadata = convert_scan(path, SCAN_DEFAULTS)
    np.testing.assert_allclose(xyz, [[0, 0, 0], [1, 0, 0]])
    np.testing.assert_array_equal(rgb[0], [255, 0, 0])
    assert metadata['source_vertices'] == 8 and metadata['registered'] is False


def test_voxel_reduction_and_cap_are_deterministic(tmp_path):
    path = ply(tmp_path / 'points.ply', [{'x': i / 1000} for i in range(1000)])
    settings = {**SCAN_DEFAULTS, 'voxel_size': .01, 'max_points': 17}
    first = convert_scan(path, settings)[0]
    second = convert_scan(path, settings)[0]
    assert len(first) == 17
    np.testing.assert_array_equal(first, second)


def test_cache_reused_and_changes_with_filters(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path / 'cache'))
    source = ply(tmp_path / 'scan.ply', [{'x': 0}, {'x': 1}])
    cache = prepare_scan(source, SCAN_DEFAULTS)
    assert cache.exists()
    assert prepare_scan(source, SCAN_DEFAULTS) == cache
    assert prepare_scan(source, {**SCAN_DEFAULTS, 'voxel_size': .02}) != cache
    with np.load(cache, allow_pickle=False) as data:
        assert data['xyz'].shape == data['rgb'].shape == (2, 3)


def test_missing_truncated_and_unsupported_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_vertices(tmp_path / 'missing.ply')
    path = ply(tmp_path / 'short.ply', [{'x': 0}])
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(ValueError, match='Truncated'):
        read_vertices(path)
    path.write_text('ply\nformat ascii 1.0\nend_header\n')
    with pytest.raises(ValueError, match='binary_little_endian'):
        read_vertices(path)

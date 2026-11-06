"""Read Gaussian PLY data as data only; prepare a bounded point-reference cache."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

from .configuration import load_layout

PLY_TYPES = {'float': '<f4', 'float32': '<f4', 'double': '<f8', 'float64': '<f8',
             'uchar': 'u1', 'uint8': 'u1', 'int': '<i4', 'uint': '<u4'}
FILTER_KEYS = ('opacity_min', 'max_splat_scale', 'voxel_size', 'max_points')


def read_vertices(path):
    properties, count, vertex_active, saw_vertex, saw_format = [], None, False, False, False
    with Path(path).open('rb') as stream:
        if stream.readline().strip() != b'ply':
            raise ValueError('Input is not a PLY file')
        for _ in range(4096):
            line = stream.readline()
            if not line:
                raise ValueError('Truncated PLY header')
            words = line.decode('ascii').split()
            if not words:
                continue
            if words[0] == 'format':
                if words[1:] != ['binary_little_endian', '1.0']:
                    raise ValueError('This importer requires binary_little_endian PLY 1.0')
                saw_format = True
            if words[0] == 'element':
                if not saw_vertex and words[1] != 'vertex':
                    raise ValueError('Vertex data must be the first PLY element')
                vertex_active = words[1] == 'vertex'
                if vertex_active:
                    count, saw_vertex = int(words[2]), True
            if words[0] == 'property' and vertex_active:
                if len(words) != 3 or words[1] not in PLY_TYPES:
                    raise ValueError('Only supported scalar vertex properties can be imported')
                properties.append((words[2], PLY_TYPES[words[1]]))
            if words[0] == 'end_header':
                offset = stream.tell()
                break
        else:
            raise ValueError('PLY header is too long')
    if not saw_format:
        raise ValueError('Missing PLY format declaration')
    if count is None or count <= 0 or len({p[0] for p in properties}) != len(properties):
        raise ValueError('Invalid vertex count or duplicate vertex properties')
    if not {'x', 'y', 'z'} <= {p[0] for p in properties}:
        raise ValueError('PLY must contain x, y and z')
    dtype = np.dtype(properties)
    if Path(path).stat().st_size < offset + count * dtype.itemsize:
        raise ValueError('Truncated PLY vertex data')
    return np.memmap(path, dtype=dtype, mode='r', offset=offset, shape=(count,))


def convert_scan(path, settings):
    vertices = read_vertices(path)
    fields = vertices.dtype.names
    xyz = np.column_stack([vertices[key] for key in ('x', 'y', 'z')]).astype(np.float32)
    keep = np.isfinite(xyz).all(axis=1)
    if 'opacity' in fields:
        logits = np.asarray(vertices['opacity'], dtype=np.float64)
        # Saturate +/-inf logits, but reject NaN; avoid exp overflow.
        opacity = 1.0 / (1.0 + np.exp(-np.clip(logits, -80, 80)))
        keep &= ~np.isnan(logits) & (opacity >= settings['opacity_min'])
    if all(f'scale_{i}' in fields for i in range(3)):
        log_scale = np.column_stack([vertices[f'scale_{i}'] for i in range(3)])
        keep &= np.isfinite(log_scale).all(axis=1)
        keep &= (log_scale <= np.log(settings['max_splat_scale'])).all(axis=1)
    if all(f'f_dc_{i}' in fields for i in range(3)):
        dc = np.column_stack([vertices[f'f_dc_{i}'] for i in range(3)])
        keep &= np.isfinite(dc).all(axis=1)
        colors = np.clip(0.5 + 0.28209479177387814 * dc, 0, 1)
    elif all(key in fields for key in ('red', 'green', 'blue')):
        colors = np.column_stack([vertices[key] for key in ('red', 'green', 'blue')]) / 255.0
    else:
        colors = np.full_like(xyz, 0.65)
    keep &= np.isfinite(colors).all(axis=1)
    xyz, colors = xyz[keep], colors[keep]
    if not len(xyz):
        raise ValueError('No valid reference points remain after filtering')
    # Float64 avoids integer overflow for large finite outliers or tiny voxels.
    voxels = np.floor(xyz.astype(np.float64) / settings['voxel_size'])
    _, indices = np.unique(voxels, axis=0, return_index=True)
    indices.sort()
    if len(indices) > settings['max_points']:
        indices = np.random.default_rng(0).choice(indices, settings['max_points'], replace=False)
        indices.sort()
    xyz = xyz[indices]
    rgb = np.rint(colors[indices] * 255).astype(np.uint8)
    metadata = {'source_vertices': len(vertices), 'output_points': len(xyz),
                'registered': False, 'coordinate_units': 'original scan units'}
    return xyz, rgb, metadata


def cache_path(source, settings):
    source = Path(source).expanduser().resolve()
    stat = source.stat()
    identity = {'version': 1, 'source': str(source), 'size': stat.st_size,
                'mtime_ns': stat.st_mtime_ns,
                **{key: settings[key] for key in FILTER_KEYS}}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'uwa_cell/scans'
    return cache / f'{digest}.npz'


def prepare_scan(source, settings):
    target = cache_path(source, settings)
    if target.is_file():
        # Never unpickle a cached artifact.
        with np.load(target, allow_pickle=False) as cached:
            if cached['xyz'].ndim == 2 and cached['rgb'].shape == cached['xyz'].shape:
                return target
        raise ValueError(f'Invalid scan cache {target}; remove it and import again')
    xyz, rgb, metadata = convert_scan(source, settings)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.npz', delete=False) as stream:
            temporary = Path(stream.name)
            np.savez_compressed(stream, xyz=xyz, rgb=rgb, metadata=json.dumps(metadata))
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description='Prepare an unregistered point reference from PLY')
    parser.add_argument('--layout')
    parser.add_argument('--input', help='Override the source PLY; paths containing spaces are supported')
    args = parser.parse_args()
    settings = load_layout(args.layout)['scan']
    try:
        target = prepare_scan(args.input or settings['source'], settings)
        with np.load(target, allow_pickle=False) as data:
            print(data['metadata'].item())
        print(f'Local cache: {target}\nReference is UNREGISTERED; no collision mesh was generated.')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Scan import failed: {exc}\n')

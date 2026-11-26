#!/usr/bin/env python3
"""Export a dimensional cuboid candidate with only explicitly assigned textures."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image
import trimesh
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from OCP.IFSelect import IFSelect_RetDone
from OCP.Message import Message, Message_PrinterOStream
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer


# (file stem, normal, texture right, texture up) in the centred object frame.
FACES = {
    '+x': ('positive-x', (1, 0, 0), (0, 1, 0), (0, 0, 1)),
    '-x': ('negative-x', (-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    '+y': ('positive-y', (0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    '-y': ('negative-y', (0, -1, 0), (1, 0, 0), (0, 0, 1)),
    '+z': ('positive-z', (0, 0, 1), (1, 0, 0), (0, 1, 0)),
    '-z': ('negative-z', (0, 0, -1), (1, 0, 0), (0, -1, 0)),
}
UV = ((0, 0), (1, 0), (1, 1), (0, 1))
TRIANGLES = ((0, 1, 2), (0, 2, 3))
PLAIN = (183, 187, 191, 255)
TEXTURE_MAX_PX = 2048


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def texture_from_photo(entry, face_size, target):
    """The exterior corners correspond to UV corners in order, in source pixels."""
    corners = np.asarray(entry['corners_px'], dtype=float)
    if corners.shape != (4, 2) or not np.isfinite(corners).all():
        raise ValueError('Four finite image corners are required for each texture')
    edges = np.roll(corners, -1, axis=0) - corners
    next_edges = np.roll(edges, -1, axis=0)
    turns = edges[:, 0] * next_edges[:, 1] - edges[:, 1] * next_edges[:, 0]
    if not np.all(turns < -1e-6):
        raise ValueError('Texture corners must form a convex exterior face in UV order')
    lengths = np.linalg.norm(edges, axis=1)
    width, height = face_size
    density = min(lengths[[0, 2]].min() / width, lengths[[1, 3]].min() / height,
                  TEXTURE_MAX_PX / max(face_size))
    size = tuple(round(length * density) for length in face_size)
    if min(size) < 2:
        raise ValueError('Face has too few source pixels to rectify its texture')

    with Path(entry['image']).open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        if source_hash != entry['image_sha256']:
            raise ValueError('Texture photograph differs from the reviewed original')
        stream.seek(0)
        with Image.open(stream) as image:
            if (corners < 0).any() or (corners > np.asarray(image.size) - 1).any():
                raise ValueError('Texture corners must lie within the original photograph')
            x_max, y_max = np.asarray(size) - 1
            rectangle = ((0, y_max), (x_max, y_max), (x_max, 0), (0, 0))
            equations = []
            for (x, y), (u, v) in zip(rectangle, corners):
                equations.extend(((x, y, 1, 0, 0, 0, -u * x, -u * y),
                                  (0, 0, 0, x, y, 1, -v * x, -v * y)))
            coefficients = np.linalg.solve(equations, corners.ravel())
            texture = image.convert('RGB').transform(size, Image.Transform.PERSPECTIVE, coefficients,
                                                     Image.Resampling.BICUBIC)
    texture.save(target, quality=95, subsampling=0)
    return texture, {'image_sha256': source_hash, 'corners_px': corners.tolist(), 'size_px': list(size)}


def write_step(path, dimensions_mm):
    shape = BRepPrimAPI_MakeBox(gp_Pnt(*(-dimensions_mm / 2)), *dimensions_mm).Shape()
    if not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError('Invalid STEP cuboid')
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    if writer.Write(str(path)) != IFSelect_RetDone:
        raise ValueError('STEP write failed')
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone or not reader.TransferRoots():
        raise ValueError('STEP readback failed')
    bounds = Bnd_Box()
    BRepBndLib.Add_s(reader.OneShape(), bounds)
    extent = np.asarray(bounds.CornerMax().Coord()) - bounds.CornerMin().Coord()
    np.testing.assert_allclose(extent, dimensions_mm, rtol=1e-7, atol=1e-4)


def write_visual_models(directory, dimensions_m, face_textures):
    scene = trimesh.Scene()
    obj = ['# Object Scan cuboid candidate, metres', 'mtllib model.mtl']
    mtl = []
    sources = {}
    for index, (face, (name, normal, u, v)) in enumerate(FACES.items()):
        n, u, v = np.asarray((normal, u, v))
        points = np.asarray([dimensions_m / 2 * (n + (2 * a - 1) * u + (2 * b - 1) * v)
                             for a, b in UV])
        texture = None
        mtl.extend((f'newmtl {name}', 'Ka 0 0 0', 'Ks 0 0 0'))
        if face in face_textures:
            target = directory / 'textures' / f'{name}.jpg'
            target.parent.mkdir(exist_ok=True)
            face_size = tuple(np.abs(axis) @ dimensions_m for axis in (u, v))
            texture, source = texture_from_photo(face_textures[face], face_size, target)
            texture_path = target.relative_to(directory).as_posix()
            sources[face] = dict(source, path=texture_path)
            mtl.extend(('Kd 1 1 1', f'map_Kd {texture_path}'))
        else:
            mtl.append('Kd ' + ' '.join(f'{channel / 255:.5f}' for channel in PLAIN[:3]))
        material = trimesh.visual.material.PBRMaterial(
            name=name, baseColorFactor=PLAIN if texture is None else (255, 255, 255, 255),
            baseColorTexture=texture, roughnessFactor=.85, metallicFactor=0)
        part = trimesh.Trimesh(vertices=points, faces=TRIANGLES, process=False,
                               visual=trimesh.visual.TextureVisuals(uv=UV, material=material))
        scene.add_geometry(part, node_name=name, geom_name=name)
        obj.extend((f'g {name}', f'usemtl {name}'))
        obj.extend('v ' + ' '.join(f'{value:.12g}' for value in point) for point in points)
        obj.extend(f'vt {a} {b}' for a, b in UV)
        offset = 1 + len(UV) * index
        obj.extend('f ' + ' '.join(f'{offset + i}/{offset + i}' for i in triangle)
                   for triangle in TRIANGLES)
    (directory / 'model.obj').write_text('\n'.join(obj) + '\n', encoding='utf-8')
    (directory / 'model.mtl').write_text('\n'.join(mtl) + '\n', encoding='utf-8')
    path = directory / 'model.glb'
    scene.export(path)
    np.testing.assert_allclose(trimesh.load(path, force='scene').extents, dimensions_m, rtol=1e-6, atol=0)
    return sources


def export_box_candidate(output, dimensions_mm, face_textures=None):
    """Export verified files atomically. Dimension order is object X, Y, Z."""
    if (not isinstance(dimensions_mm, (list, tuple)) or len(dimensions_mm) != 3
            or any(type(value) not in (int, float) for value in dimensions_mm)):
        raise ValueError('Enter three positive cuboid dimensions in millimetres')
    dimensions = np.asarray(dimensions_mm, dtype=float)
    if not np.isfinite(dimensions).all() or (dimensions <= 0).any():
        raise ValueError('Enter three finite positive cuboid dimensions in millimetres')
    if face_textures is None:
        face_textures = {}
    if not isinstance(face_textures, dict) or set(face_textures) - FACES.keys():
        raise ValueError('Use known outward face identifiers for texture sources')
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix='.asset-') as temporary:
        candidate = Path(temporary) / 'candidate'
        candidate.mkdir()
        sources = write_visual_models(candidate, dimensions / 1000, face_textures)
        write_step(candidate / 'model.step', dimensions)
        models = {'model.glb': 'model/gltf-binary', 'model.obj': 'model/obj',
                  'model.mtl': 'text/plain', 'model.step': 'model/step'}
        models.update({source['path']: 'image/jpeg' for source in sources.values()})
        files = [dict(name=Path(path).name, path=path, media_type=media_type, sha256=sha256(candidate / path))
                 for path, media_type in models.items()]
        manifest = dict(schema_version=1, status='model_candidate', shape='cuboid', dimensions_mm=dimensions.tolist(),
                        frame='centred object XYZ', units={'glb': 'm', 'obj': 'm', 'step': 'mm'},
                        files=files, textured_faces=list(sources), missing_texture_faces=[face for face in FACES if face not in sources],
                        texture_sources=sources, fine_details_measured=False, manipulation_approved=False)
        (candidate / 'asset.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        candidate.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    request = json.load(sys.stdin)
    Message.DefaultMessenger_s().RemovePrinters(Message_PrinterOStream.get_type_descriptor_s())
    manifest = export_box_candidate(args.output, request['dimensions_mm'], request.get('face_textures'))
    print(json.dumps(manifest, allow_nan=False))


if __name__ == '__main__':
    main()

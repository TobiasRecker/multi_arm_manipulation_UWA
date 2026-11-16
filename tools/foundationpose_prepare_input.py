#!/usr/bin/env python3
"""Export an asset and saved aligned RGB-D capture, without a scene-pose prior.

Run with .venvs/oak-model/bin/python. No camera, ROS or network access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw
import trimesh


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_model(asset_path, output):
    asset = json.loads((asset_path / 'asset.json').read_text())
    if asset['units'] != 'm':
        raise ValueError('Need explicitly metre-based asset')
    for name, digest in asset['files'].items():
        if sha(asset_path / name) != digest:
            raise ValueError(f'Asset hash mismatch: {name}')
    scene = trimesh.load(asset_path / asset['preview_mesh'], force='scene')
    vertices, faces, materials, uvs = [], [], [], []
    offset = 0
    for node in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node]
        geometry = scene.geometry[geometry_name].copy()
        geometry.apply_transform(transform)
        vertices.append(geometry.vertices)
        faces.append(geometry.faces + offset)
        offset += len(geometry.vertices)
        if geometry.visual.kind == 'texture':
            material = geometry.visual.material
            if hasattr(material, 'to_simple'):
                material = material.to_simple()
            materials.append(material)
            uvs.append(geometry.visual.uv)
        else:
            colors = np.unique(geometry.visual.vertex_colors, axis=0)
            if len(colors) != 1:
                raise ValueError('Nonuniform vertex colors need a separate verified bake')
            materials.append(trimesh.visual.material.SimpleMaterial(
                image=Image.new('RGBA', (16, 16), tuple(colors[0]))))
            uvs.append(np.full((len(geometry.vertices), 2), .5))
    material, uv = trimesh.visual.material.pack(materials, uvs, padding=4,
                        max_tex_size_individual=1024, max_tex_size_fused=4096)
    material.image = material.image.convert('RGB')
    mesh = trimesh.Trimesh(vertices=np.vstack(vertices), faces=np.vstack(faces), process=False)
    mesh.visual = trimesh.visual.texture.TextureVisuals(uv=uv, material=material)
    expected = np.asarray(asset['dimensions_m'])
    if not np.allclose(mesh.extents, expected, atol=1e-7):
        raise ValueError('Asset unit/frame/extent mismatch')
    output.mkdir()
    path = output / 'textured_simple.obj'
    mesh.export(path)
    restored = trimesh.load(path, process=False, force='mesh')
    if len(restored.faces) != len(mesh.faces) or not np.allclose(restored.bounds, mesh.bounds, atol=1e-7):
        raise ValueError('OBJ roundtrip changed geometry or frame')
    if restored.visual.kind != 'texture' or restored.visual.material.image is None:
        raise ValueError('OBJ lost its texture atlas')
    return dict(asset_id=asset['asset_id'], dimensions_m=mesh.extents.tolist(),
        triangles=len(mesh.faces), bounds=mesh.bounds.tolist(), atlas_size=list(material.image.size),
        scene_pose_used=False, asset_quality=asset['quality'], asset_manifest_sha256=sha(asset_path / 'asset.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--mask-annotation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--downsample', type=int, choices=(1, 2), default=1,
                        help='Integer working-image reduction; keep source captures unchanged')
    args = parser.parse_args()
    capture = json.loads((args.capture / 'metadata.json').read_text())
    if not capture.get('success') or capture.get('kind') != 'rgbd':
        raise ValueError('Need a completed aligned RGB-D capture')
    k = np.asarray(capture['projection']['K'])
    if (not np.allclose(k, capture['projection']['depth_K'])
            or np.any(np.asarray(capture['projection']['D']) != 0)):
        raise ValueError('Projection is not a matching undistorted RGB-D pair')
    annotation = json.loads(args.mask_annotation.read_text())
    size = tuple(capture['projection']['size'])
    if any(s % args.downsample for s in size):
        raise ValueError('Source size must divide exactly by requested reduction')
    working_size = tuple(s // args.downsample for s in size)
    scale = 1. / args.downsample
    pixel_transform = np.array([[scale, 0, (scale - 1) / 2],
                                [0, scale, (scale - 1) / 2], [0, 0, 1.]])
    if tuple(annotation['image_size']) != size or annotation['source_frame'] != 0:
        raise ValueError('Mask annotation belongs to another image geometry/frame')
    if sha(args.capture / capture['pairs'][0]['rgb_path']) != annotation['source_rgb_sha256']:
        raise ValueError('Mask annotation does not match the first RGB payload')
    args.output.mkdir(parents=True, exist_ok=False)
    model = export_model(args.asset, args.output / 'mesh')
    for name in ('rgb', 'depth', 'masks'):
        (args.output / name).mkdir()
    for i, pair in enumerate(capture['pairs']):
        rgb = args.capture / pair['rgb_path']
        depth = args.capture / pair['depth_path']
        with Image.open(rgb) as image:
            if image.size != size:
                raise ValueError('RGB dimensions changed')
            if args.downsample != 1:
                image.resize(working_size, Image.Resampling.LANCZOS).save(args.output / 'rgb' / f'{i:06d}.png')
        with Image.open(depth) as image:
            array = np.asarray(image)
            if image.size != size or array.dtype != np.uint16:
                raise ValueError('Depth needs uint16 millimetres at RGB size')
            if args.downsample != 1:
                image.resize(working_size, Image.Resampling.NEAREST).save(args.output / 'depth' / f'{i:06d}.png')
        if pair['timestamp_difference_s'] > capture['max_timestamp_difference_s']:
            raise ValueError('Input timestamps exceed capture threshold')
        if args.downsample == 1:
            shutil.copyfile(rgb, args.output / 'rgb' / f'{i:06d}.png')
            shutil.copyfile(depth, args.output / 'depth' / f'{i:06d}.png')
    mask = Image.new('L', size, 0)
    painter = ImageDraw.Draw(mask)
    painter.polygon([tuple(p) for p in annotation['outer_polygon']], fill=255)
    for polygon in annotation.get('excluded_polygons', []):
        painter.polygon([tuple(p) for p in polygon], fill=0)
    if np.count_nonzero(np.asarray(mask)) < 100:
        raise ValueError('Empty or tiny object mask')
    if args.downsample != 1:
        mask = mask.resize(working_size, Image.Resampling.NEAREST)
    mask.save(args.output / 'masks/000000.png')
    np.savetxt(args.output / 'cam_K.txt', pixel_transform @ k)
    shutil.copyfile(args.mask_annotation, args.output / 'mask_annotation.json')
    report = dict(schema=1, kind='foundationpose_input', model=model,
        capture=str(args.capture.resolve()), capture_metadata_sha256=sha(args.capture / 'metadata.json'),
        source_mask_sha256=sha(args.mask_annotation), frames=len(capture['pairs']),
        preparation_source_sha256=sha(Path(__file__)),
        source_image_size=list(size), working_image_size=list(working_size),
        source_to_working_pixels=pixel_transform.tolist(),
        resampling='RGB Lanczos, depth/mask nearest, no depth filling' if args.downsample != 1 else 'none',
        units='mesh metres, depth PNG millimetres, OpenCV optical camera frame',
        initialization='visible first-frame object mask; no known object/board/world pose',
        absolute_accuracy_validated=False, manipulation_approved=False,
        files={p.relative_to(args.output).as_posix():sha(p) for p in args.output.rglob('*') if p.is_file()})
    (args.output / 'input.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    main()

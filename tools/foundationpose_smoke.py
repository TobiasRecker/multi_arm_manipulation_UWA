#!/usr/bin/env python3
"""Bounded, headless official RGB-D demo; no camera/robot/ROS access."""
import argparse
import json
import os
from pathlib import Path
import statistics
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frames', type=int, default=12)
    parser.add_argument('--stride', type=int, default=3)
    args = parser.parse_args()
    if not 2 <= args.frames <= 100 or not 1 <= args.stride <= 10:
        parser.error('frames must be 2..100 and stride 1..10')
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    import torch
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(0.45)
    import numpy as np
    import imageio.v2 as imageio
    import trimesh
    import nvdiffrast.torch as dr
    from estimater import FoundationPose, ScorePredictor, PoseRefinePredictor
    from datareader import YcbineoatReader
    from Utils import draw_xyz_axis, set_seed
    imports_s = time.perf_counter() - started
    set_seed(0)
    mesh = trimesh.load(args.scene / 'mesh/textured_simple.obj')
    reader = YcbineoatReader(str(args.scene), shorter_side=None, zfar=float('inf'))
    report = {
        'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__,
        'cuda_runtime': torch.version.cuda, 'input': str(args.scene),
        'method': 'official FoundationPose register then track_one',
        'pose_convention': 'T_camera_object; mesh and depth in metres',
        'ground_truth_used_for_estimation': False,
        'manipulation_approved': False, 'absolute_accuracy_validated': False,
        'imports_s': imports_s, 'frames': [],
    }
    init_start = time.perf_counter()
    est = FoundationPose(
        model_pts=mesh.vertices, model_normals=mesh.vertex_normals,
        mesh=mesh, scorer=ScorePredictor(), refiner=PoseRefinePredictor(),
        glctx=dr.RasterizeCudaContext(), debug=0,
        debug_dir=str(args.output / 'debug'),
    )
    torch.cuda.synchronize()
    report['model_init_s'] = time.perf_counter() - init_start
    indices = list(range(0, len(reader), args.stride))[:args.frames]
    if len(indices) < 2:
        raise RuntimeError('Need at least two distinct RGB-D frames')
    for number, index in enumerate(indices):
        rgb, depth = reader.get_color(index), reader.get_depth(index)
        if rgb.shape[:2] != depth.shape:
            raise RuntimeError('RGB/depth geometry mismatch')
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        if number == 0:
            pose = est.register(K=reader.K, rgb=rgb, depth=depth,
                                ob_mask=reader.get_mask(index).astype(bool), iteration=5)
        else:
            pose = est.track_one(rgb=rgb, depth=depth, K=reader.K, iteration=2)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0
        pose = np.asarray(pose, dtype=float).reshape(4, 4)
        if (not np.isfinite(pose).all() or pose[2, 3] <= 0
                or not np.allclose(pose[3], [0, 0, 0, 1], atol=1e-4)
                or not np.allclose(pose[:3, :3].T @ pose[:3, :3], np.eye(3), atol=2e-3)
                or not np.isclose(np.linalg.det(pose[:3, :3]), 1, atol=2e-3)):
            raise RuntimeError(f'Invalid pose on frame {index}')
        row = {'index': index, 'id': reader.id_strs[index],
               'mode': 'register' if number == 0 else 'track',
               'seconds': elapsed, 'T_camera_object': pose.tolist()}
        # Read annotations only AFTER estimation, solely for separate evaluation.
        gt = reader.get_gt_pose(index)
        if gt is not None:
            row['annotation_translation_error_mm'] = float(np.linalg.norm(pose[:3, 3] - gt[:3, 3]) * 1000)
            cosine = (np.trace(pose[:3, :3] @ gt[:3, :3].T) - 1) / 2
            row['annotation_rotation_error_deg'] = float(np.degrees(np.arccos(np.clip(cosine, -1, 1))))
        report['frames'].append(row)
        np.savetxt(args.output / f'pose_{number:03d}.txt', pose)
        overlay = draw_xyz_axis(rgb.copy(), ob_in_cam=pose, scale=0.1,
                                K=reader.K, thickness=3, transparency=0, is_input_rgb=True)
        imageio.imwrite(args.output / f'overlay_{number:03d}.png', overlay)
        print(json.dumps({'frame': index, 'mode': row['mode'], 'seconds': elapsed}), flush=True)
        (args.output / 'report.partial.json').write_text(json.dumps(report, indent=2))
    report['registration_s'] = report['frames'][0]['seconds']
    report['tracking_median_s'] = statistics.median(row['seconds'] for row in report['frames'][1:])
    report['peak_torch_allocated_mib'] = torch.cuda.max_memory_allocated() / 2**20
    report['peak_torch_reserved_mib'] = torch.cuda.max_memory_reserved() / 2**20
    report['total_s'] = time.perf_counter() - started
    report['status'] = 'PASS'
    (args.output / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'frames'}, indent=2))


if __name__ == '__main__':
    main()

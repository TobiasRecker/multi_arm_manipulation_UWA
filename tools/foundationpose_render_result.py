#!/usr/bin/env python3
"""Render an already estimated pose for visual review; no new pose fitting."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import torch
    import trimesh
    import imageio.v2 as imageio
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(.2)
    from Utils import nvdiffrast_render
    report = json.loads((args.result / 'report.json').read_text())
    mesh = trimesh.load(args.scene / 'mesh/textured_simple.obj')
    k = np.loadtxt(args.scene / 'cam_K.txt')
    frame = report['frames'][0]
    rgb = imageio.imread(args.scene / 'rgb' / f'{frame["index"]:06d}.png')[..., :3]
    color, depth, _ = nvdiffrast_render(K=k, H=rgb.shape[0], W=rgb.shape[1],
        ob_in_cams=torch.tensor(np.asarray(frame['T_camera_object']), device='cuda', dtype=torch.float32)[None],
        mesh=mesh)
    color = np.clip(color[0].cpu().numpy() * 255, 0, 255).astype(np.uint8)
    visible = depth[0].cpu().numpy() > 0
    overlay = rgb.copy()
    overlay[visible] = (.5 * rgb[visible] + .5 * color[visible]).astype(np.uint8)
    imageio.imwrite(args.output / 'render.png', color)
    imageio.imwrite(args.output / 'overlay.png', overlay)
    print(str(args.output))


if __name__ == '__main__':
    main()

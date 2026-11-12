"""Static design visualization from a checked scan report; no ROS/camera access."""
import argparse
from itertools import product
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from uwa_cell_control.view_geometry import VisibilityModel


def faces(corners):
    # itertools.product order: index = x*4 + y*2 + z
    return [corners[ids] for ids in [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1],
                                     [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    data = json.loads(args.report.read_text())
    if not data.get('common_view_found'):
        raise ValueError('No common view in this report')
    description = (args.report.parent / 'cell.urdf').read_text()
    arms = list(data['candidates'])
    geometry = VisibilityModel(description, arms)
    frames = geometry.frames(data['common_state'])
    color = dict(zip(arms, ['#2166ac', '#00806a', '#b96a00', '#8945ad']))
    fig = plt.figure(figsize=(16, 9), facecolor='white')
    for index, (elev, azim) in enumerate([(28, -65), (90, -90)]):
        ax = fig.add_subplot(1, 2, index + 1, projection='3d')
        for arm, name, fixed, bounds in geometry.boxes:
            corners = np.asarray(list(product(*zip(bounds[0], bounds[1]))))
            T = frames[name] @ fixed
            corners = corners @ T[:3, :3].T + T[:3, 3]
            ax.add_collection3d(Poly3DCollection(faces(corners), facecolor=color[arm], edgecolor=color[arm],
                                               linewidth=.25, alpha=.14))
        # Table outlines from actual model frames; dimensions from saved design model.
        layout_path = args.report.parent / 'model/layout.yaml'
        import yaml
        layout = yaml.safe_load(layout_path.read_text())
        for table, entry in layout['tables'].items():
            w, h = entry['width'] / 2, entry['length'] / 2
            points = np.array([[-w, -h, 0], [w, -h, 0], [w, h, 0], [-w, h, 0], [-w, -h, 0]])
            T = frames[table + '_table_top']
            points = points @ T[:3, :3].T + T[:3, 3]
            ax.plot(*points.T, color='#222222', linewidth=2)
        T = np.asarray(data['T_world_object'])
        size = np.asarray(data['design']['size_m'])
        points = np.asarray(list(product(*[[-v/2, v/2] for v in size]))) @ T[:3, :3].T + T[:3, 3]
        ax.add_collection3d(Poly3DCollection(faces(points), facecolor='#e5a047', edgecolor='#6b3a00', alpha=.7))
        board = np.asarray(data['T_world_board'])
        outline = np.array([[0, 0, 0], [.28, 0, 0], [.28, .2, 0], [0, .2, 0], [0, 0, 0]])
        outline = outline @ board[:3, :3].T + board[:3, 3]
        ax.plot(*outline.T, color='#087f23', linewidth=2)
        for rid in arms:
            C = frames[rid + '_wrist_camera_optical_frame']
            xyz = C[:3, 3]
            ax.scatter(*xyz, s=40, color=color[rid])
            ax.plot(*np.array([xyz, T[:3, 3]]).T, color=color[rid], linewidth=2)
            ax.text(*xyz, ' ' + rid, color=color[rid], fontsize=10, weight='bold')
        oak = layout['calibration']['overview_camera']['registration']['T_world_oak_optical']
        xyz = np.asarray(oak)[:3, 3]
        ax.scatter(*xyz, s=50, color='#d02020')
        ax.plot(*np.array([xyz, T[:3, 3]]).T, color='#d02020', linewidth=2)
        ax.text(*xyz, ' OAK', color='#d02020', weight='bold')
        ax.set(xlim=(-1.1, 1.6), ylim=(-1.1, 1.1), zlim=(.7, 2.1), xlabel='World X / m', ylabel='World Y / m', zlabel='Z / m')
        ax.set_box_aspect([2.7, 2.2, 1.4])
        ax.view_init(elev=elev, azim=azim)
        ax.set_title('Common object views' if index == 0 else 'Top view', weight='bold')
    fig.suptitle('FIVE-CAMERA SCAN DESIGN — NO HARDWARE MOTION', fontsize=19, weight='bold')
    fig.text(.03, .03, f"{data['unique_view_count']} planned viewpoints | conservative collision-body bounds shown | "
             'object envelope 160 x 550 x 120 mm\n'
             'Provisional world anchors / some nominal camera mounts. Visibility is a model prediction, not a real-image check.', fontsize=12)
    fig.tight_layout(rect=[0, .08, 1, .95])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=140)
    plt.close(fig)
    print(args.output)


if __name__ == '__main__':
    main()

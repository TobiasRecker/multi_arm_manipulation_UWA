"""Export metre-scale holder meshes from the supplied Inventor package."""
import argparse
import hashlib
import json
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parents[1] / 'uwa_cell_description/meshes/visual/oak_d_pro_mount'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('holder_directory', type=Path)
    args = parser.parse_args()
    sources = [
        ('shoe', args.holder_directory / 'Rod_shoe_19mm.stl', (0, 0, 0)),
        ('carrier', args.holder_directory / 'Camera_carrier_OAK_D_Pro.stl', (0, 0, 0)),
        ('foot', ROOT / 'rohrhalter-19mm.stl', (0, 80.45, 0)),
    ]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for part, source, offset in sources:
        mesh = trimesh.load_mesh(source)
        if not mesh.is_volume:
            raise ValueError(f'Invalid STL {source}')
        mesh.apply_translation(offset).apply_scale(.001)
        dest = OUTPUT / f'{part}.stl'
        mesh.export(dest)
        manifest[part] = dict(source=source.name, source_sha256=sha(source),
                              visual_sha256=sha(dest), bounds_m=mesh.bounds.tolist())
    (OUTPUT/'provenance.json').write_text(json.dumps(dict(
        units='m', sources=manifest,
        assembly_sha256=sha(args.holder_directory / 'OAK_D_Pro_Adjustable_Holder.step'),
        neutral_flip_rgb_mm=[0, 47.35, 15.236], shoe_socket_stop_mm=-27,
        table_foot_rod_stop_mm=4), indent=2)+'\n')


if __name__ == '__main__':
    main()

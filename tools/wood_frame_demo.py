#!/usr/bin/env python3
"""Plan the UWA wood frame offline and export its browser replay."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'uwa_cell_tasks'))

from uwa_cell_tasks.core import write_json
from uwa_cell_description.configuration import default_layout_path, load_layout
from uwa_cell_tasks.wood_frame import FIXTURE_CENTER_Y_M, FrameRecipe, compile_frame, fixture
from uwa_cell_tasks.wood_frame_observation import observe_scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--layout', type=Path)
    parser.add_argument('--recipe', type=Path, help='JSON with optional FrameRecipe overrides')
    parser.add_argument('--case', choices=('nominal', 'shifted', 'occluded'), default='nominal')
    parser.add_argument('--hydrogen', action='store_true', help='Ask Gemini about synthetic images only')
    args = parser.parse_args()
    try:
        overrides = json.loads(args.recipe.read_text()) if args.recipe else {}
        if not isinstance(overrides, dict) or overrides.pop('schema_version', 1) != 1:
            raise ValueError('Expected a version 1 frame recipe')
        recipe = FrameRecipe(**overrides)
        if args.case == 'occluded':
            args.output.mkdir(parents=True, exist_ok=False)
            table = load_layout(args.layout or default_layout_path())['tables']['right']
            table_z = table['xyz'][2] + table['height']
            beam, posts = fixture(recipe, table_z, FIXTURE_CENTER_Y_M, (0., 0., 0.))
            result = observe_scene(beam, recipe.beam_size_m, posts, table_z,
                                   output=args.output, occluded=True, hydrogen=args.hydrogen)
            write_json(args.output/'observation.json', result)
            print(json.dumps(dict(status=result['status'], output=str(args.output.resolve()))))
            return
        from uwa_cell_tasks.wood_frame_viewer import export_viewer

        shift = (-.008, .025, np.deg2rad(5.)) if args.case == 'shifted' else (0., 0., 0.)
        plan, description = compile_frame(args.output, observe_scene, recipe=recipe,
                                          layout_path=args.layout, shift=shift, hydrogen=args.hydrogen)
        viewer = args.output/'viewer.html'
        export_viewer(plan, description, viewer)
        print(json.dumps(dict(status=plan['status'], viewer=str(viewer.resolve()), audit=plan['audit']), indent=2))
    except (OSError, TypeError, ValueError) as error:
        parser.exit(1, f'wood-frame: {error}\n')


if __name__ == '__main__':
    main()

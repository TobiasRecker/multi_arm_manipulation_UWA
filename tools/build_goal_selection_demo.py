#!/usr/bin/env python3
"""Reproducible synthetic task alternatives in a frozen current cell model."""
import argparse
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation
import yaml

from uwa_cell_description.configuration import default_layout_path
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.candidates import enumerate_candidates
from uwa_cell_motion.common import ROBOT_IDS, config, dump, joint_names, nominal_state
from uwa_cell_motion.planning import Problem


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args(); out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    path = default_layout_path().resolve(); layout = yaml.safe_load(path.read_text())
    if 'base_layout' in layout:
        profile = layout.get('calibration_profile')
        layout = yaml.safe_load((path.parent/layout['base_layout']).read_text())
        if profile: layout['calibration_profile'] = str((path.parent/profile).resolve())
    elif layout.get('calibration_profile'):
        layout['calibration_profile'] = str((path.parent/layout['calibration_profile']).resolve())
    snapshot = out/'layout.yaml'; snapshot.write_text(yaml.safe_dump(layout, sort_keys=False))
    with tempfile.TemporaryDirectory(prefix='uwa-selection-demo-') as temporary:
        problem = Problem(temporary, config(), snapshot)
        (out/'model.urdf').write_text(problem.description)
        start = nominal_state(problem.layout); goals = {}
        offsets = np.asarray([[.10,-.15,.10,0,0,.05], [-.45,.2,.1,-.15,.1,-.05],
                              [.4,-.35,-.2,.2,-.15,.1], [-1.2,.4,.2,-.3,0,0]])
        for rid in ROBOT_IDS:
            names = joint_names(rid); q0 = np.asarray([start[j] for j in names])
            chain = Chain(problem.description, 'world', rid+'_tool0'); alternatives = []
            for offset in offsets:
                pose = chain.forward(dict(start, **dict(zip(names, q0+offset))))
                alternatives.append(dict(frame_id='world', target_link=rid+'_tool0',
                                         pose=dict(position=pose[:3,3].tolist(),
                                                   orientation_xyzw=Rotation.from_matrix(pose[:3,:3]).as_quat().tolist())))
            goals[rid] = dict(alternatives=alternatives)
        request = dict(schema_version=1, start=start, goals=goals,
                       note='Synthetic equally acceptable flange poses, not a measured task or real motion target')
        dump(out/'request.json', request)
        result = enumerate_candidates(problem, request, seeds=24, seed=64,
                                      max_per_arm=8, max_combinations=16, budget_s=60.)
        dump(out/'candidates.json', result)
        print(json.dumps(dict(candidates={r:len(cs) for r,cs in result['candidates'].items()},search=result['search'])))


if __name__ == '__main__': main()

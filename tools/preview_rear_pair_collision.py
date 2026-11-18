#!/usr/bin/env python3
"""Render the retained rear-pair yaw reference and its native FCL witnesses."""
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation
from uwa_cell_motion.common import ROBOT_IDS
from uwa_cell_motion.object_transport import ObjectTransport
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher

from mine_teacher_collisions import contact_witness


ARMS = ('left_rear', 'right_rear')


def contact_marker(model, world, pair):
    """Locate the closest proxy surfaces on the two FCL-confirmed links."""
    indices = [np.flatnonzero(np.array(model.links[arm]) == link)
               for arm, link in zip(ARMS, pair)]
    centres = [world[arm][subset] for arm, subset in zip(ARMS, indices)]
    radii = [model.radii[arm][subset] for arm, subset in zip(ARMS, indices)]
    delta = centres[1][None, :, :] - centres[0][:, None, :]
    distances = np.linalg.norm(delta, axis=2)
    gaps = distances - radii[0][:, None] - radii[1][None, :]
    left, right = np.unravel_index(np.argmin(gaps), gaps.shape)
    direction = delta[left, right] / max(distances[left, right], 1e-12)
    surfaces = [centres[0][left] + direction * radii[0][left],
                centres[1][right] - direction * radii[1][right]]
    return dict(marker=np.mean(surfaces, axis=0).tolist(),
                highlights={arm: subset.tolist() for arm, subset in zip(ARMS, indices)})


def load_reference(directory):
    screening_path = directory / 'result.json'
    witness_path = directory / 'summary.json'
    raw = screening_path.read_bytes()
    screening = json.loads(raw)
    saved = json.loads(witness_path.read_text())
    if hashlib.sha256(raw).hexdigest() != saved['source_hashes']['result.json']:
        raise ValueError('Screening report does not match the retained witness')
    reference = next(case for case in screening['cases'] if case['id'] == 'rear_y0.55')
    yaw = next(item for item in reference['references'] if item['task']['name'] == 'axis2_1')
    source = Path(screening['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != screening['source_sha256']:
        raise ValueError('Source model does not match the screening report')
    return screening, saved, reference, yaw, source, hashlib.sha256(raw).hexdigest()


def build_teacher(directory, screening, reference, source):
    # Start directly from the archived rear-grasp seed on the bound model.
    teacher = TwoArmTeacher.__new__(TwoArmTeacher)
    ObjectTransport.__init__(teacher, directory, source, arms=ARMS)
    teacher.initial = np.array(reference['bank']['initial_pose'])
    teacher.start = reference['bank']['selected']['state']
    teacher.offsets = {arm: np.array(offset) for arm, offset in screening['rear_grasp_offsets'].items()}
    for offset in teacher.offsets.values():
        offset.setflags(write=False)
    teacher.environment_boxes = []
    model = teacher.problem.spheres
    fk = model.geometry.fk.frames(teacher.start)
    for body in model.environment:
        if body.link == 'offline_carton':
            continue
        lo = body.visual_vertices.min(axis=0)
        hi = body.visual_vertices.max(axis=0)
        transform = fk[body.link] @ body.fixed
        transform[:3, 3] += transform[:3, :3] @ ((lo + hi) / 2)
        teacher.environment_boxes.append((body.link, transform, (hi - lo) / 2))
    return teacher


def render_frames(teacher, rows, contacts, reference_rows=None):
    pair = [arm + '_forearm_link' for arm in ARMS]
    model = teacher.problem.spheres
    frames = []
    native_samples = []
    for index, row in enumerate(rows):
        pose = np.asarray(row['pose'])
        state = dict(teacher.start, **dict(zip(teacher.names, row['q'])))
        world = model.world(state)
        clear = teacher.full_check(pose, state)
        origin = teacher.object_origin(pose).tolist()
        rotation = Rotation.from_matrix(pose[:3, :3] @ teacher.initial[:3, :3].T)
        frame = dict(s=row['s'], object_origin=origin, reference_origin=origin,
                     centre=pose[:3, 3].tolist(), reference_centre=pose[:3, 3].tolist(),
                     rotation_vector_deg=rotation.as_rotvec(degrees=True).tolist(),
                     world={arm: positions.round(6).tolist() for arm, positions in world.items()},
                     fcl_clear=clear, object_box_gap_mm=1000 * min(row['environment_gaps_m']),
                     object_arm_gap_mm=1000 * min(row['object_arm_gaps_m']),
                     gaps=[dict(arms=entry['arms'], gap_mm=1000 * entry['clearance_m'])
                           for entry in row['pairs']])
        if reference_rows is not None:
            reference_pose = np.asarray(reference_rows[index]['pose'])
            frame['reference_origin'] = teacher.object_origin(reference_pose).tolist()
            frame['reference_centre'] = reference_pose[:3, 3].tolist()
        if not clear:
            native = contact_witness(teacher, pose, state, contacts / f'{index:02d}.log')
            if native['fcl_clear'] or not native['contact_pairs']:
                raise ValueError(f'Native contact labels missing for sample {index}')
            frame['contact_pairs'] = native['contact_pairs']
            if sorted(pair) in [sorted(links) for links in native['contact_pairs']]:
                frame.update(contact_marker(model, world, pair))
            native_samples.append(dict(index=index, s=row['s'], pairs=native['contact_pairs']))
        frames.append(frame)
    return frames, native_samples


def write_viewer(out, teacher, sets, *, reference_only=True, **settings):
    model = teacher.problem.spheres
    boxes = []
    for _, transform, half in teacher.environment_boxes:
        corners = np.array(list(product(*[[-h, h] for h in half])))
        boxes.append((corners @ transform[:3, :3].T + transform[:3, 3]).tolist())
    data = dict(reference_only=reference_only, view_centre=[0, .38, 1.24],
                arms=list(ROBOT_IDS), active_arms=list(ARMS), boxes=boxes,
                triangles=teacher.triangles.tolist(), radii={arm: r.tolist() for arm, r in model.radii.items()},
                sets=sets, summary=[], **settings)
    template = Path(__file__).with_name('preview_two_arm_teacher.html').read_text()
    (out / 'viewer.html').write_text(template.replace('__DATA__', json.dumps(data, allow_nan=False,
                                                 separators=(',', ':')).replace('</', '<\\/')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screening', type=Path, help='Folder containing result.json and summary.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    screening, saved, reference, yaw, source, screening_hash = load_reference(args.screening)
    count = yaw['inspection']['samples']
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'contacts').mkdir()
    with tempfile.TemporaryDirectory(prefix='uwa-rear-view-') as directory:
        teacher = build_teacher(directory, screening, reference, source)
        rows = teacher.path_rows(yaw['task'], count=count)
        frames, native_samples = render_frames(teacher, rows, out / 'contacts')
        expected = [item['s'] for item in yaw['inspection']['failures'] if not item['fcl_clear']]
        if not np.array_equal([item['s'] for item in native_samples], expected):
            raise ValueError('Recomputed collision samples differ from the retained screening')
        midpoint = len(frames) // 2
        mid_state = dict(teacher.start, **dict(zip(teacher.names, rows[midpoint]['q'])))
        if (saved['witness']['contact_pairs'] != frames[midpoint].get('contact_pairs')
                or not np.allclose(rows[midpoint]['pose'], saved['witness']['pose'], atol=1e-9, rtol=0)
                or any(abs(value - saved['witness']['state'][name]) > 1e-8 for name, value in mid_state.items())):
            raise ValueError('Viewer midpoint does not reproduce the retained contact witness')
        write_viewer(out, teacher, [dict(label='Rear pair / +60° world Z', frames=frames)],
                     initial_frame=midpoint)
        report = dict(executable=False, model_signature=teacher.problem.signature, sample_count=len(frames),
                      default_sample=midpoint, collision_samples=native_samples,
                      start_fcl_clear=frames[0]['fcl_clear'], end_fcl_clear=frames[-1]['fcl_clear'],
                      marker='Approximate region from the closest sphere surfaces on the FCL-confirmed links',
                      screening_sha256=screening_hash)
        (out / 'preview-check.json').write_text(json.dumps(report, indent=2) + '\n')
        print(f'{len(native_samples)}/{len(frames)} FCL samples. Viewer: {out / "viewer.html"}')


if __name__ == '__main__':
    main()

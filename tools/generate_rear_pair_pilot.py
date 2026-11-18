#!/usr/bin/env python3
"""Build a model-checked pilot from screened rear-arm start and goal families."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time

import numpy as np

from plan_two_arm_teacher import preview
from preview_rear_pair_collision import build_teacher, load_reference, write_viewer
from time_rear_pair_teacher import LIMITS, validate_model
from uwa_cell_motion.teacher_dataset import SCHEMA, atomic_json, set_initial, transitions, validate_export


def load_case(teacher, family, candidate):
    check = set_initial(teacher, family, teacher.initial, teacher.start)
    if (not check['passed'] or not np.array_equal(teacher.initial, family['initial_pose'])
            or not np.allclose(list(teacher.start.values()),
                               [family['initial_state'][name] for name in teacher.start], atol=1e-9, rtol=0)):
        raise ValueError('Start does not match the screened model')
    task = candidate['task']
    rows = teacher.path_rows(task, count=candidate['check']['samples'])
    replay = teacher.inspect(task, count=len(rows))
    if replay != candidate['check']:
        # Float values can vary at round-off between workers. Require the same
        # contact and failure samples and the same classification.
        def key(result):
            return (result['passed'], result['complete'],
                    [(row['s'], row['fcl_clear']) for row in result.get('failures', [])])
        if key(replay) != key(candidate['check']):
            raise ValueError('Reference classification changed')
    return rows


def generate_case(root, family, candidate, seeds, path):
    if path.exists():
        raise ValueError(f'Case output exists: {path}')
    path.mkdir()
    begun = time.monotonic()
    name = path.name
    kind = 'collision' if candidate['colliding_progress'] else 'free_control'
    result = dict(id=name, family=family['id'], group=family['anchor'], split='unassigned',
                  reference_class=kind, executable=False, status='RUNNING')
    task = candidate['task']
    result.update(task=task, reference=candidate['check'], colliding_progress=candidate['colliding_progress'])
    screening, _, _, _, source, source_hash = load_reference(root)
    anchor = next(case for case in screening['cases'] if case['id'] == family['anchor'])
    with tempfile.TemporaryDirectory(prefix='uwa-rear-pilot-') as directory:
        teacher = build_teacher(directory, screening, anchor, source)
        try:
            reference_rows = load_case(teacher, family, candidate)
            geometric = dict(initial_pose=teacher.initial.tolist(), goal_pose=reference_rows[-1]['pose'],
                             initial_state=teacher.start, goal_joint_positions_rad=reference_rows[-1]['q'])
            result.update(geometric, model_signature=teacher.problem.signature,
                          screening_sha256=source_hash, grasp_offsets=screening['rear_grasp_offsets'])
            if kind == 'free_control':
                controls = np.zeros((6, 6))
            else:
                initial = seeds.get(name)
                optimization = teacher.optimize(task, count=121, maxiter=26,
                                                initial_controls=None if initial is None else np.array(initial))
                result['optimization'] = optimization
                atomic_json(path / 'result.json', result)
                if not optimization.get('success', False):
                    raise ValueError(optimization['status'])
                controls = np.array(optimization['controls'])
            trajectory = teacher.trajectory(task, controls, **LIMITS)
            result['trajectory'] = trajectory
            result['validation'] = validate_model(teacher, trajectory, geometric)
            if not result['validation']['passed']:
                raise ValueError('Timed interpolation failed validation')
            records = transitions(teacher.initial, trajectory)
            result['export_validation'] = validate_export(teacher, records)
            if not result['export_validation']['passed']:
                raise ValueError('Export grid failed validation')
            last = max(candidate['colliding_progress'], default=None)
            if last is not None:
                from uwa_cell_motion.two_arm_teacher import pose_at
                pose = pose_at(teacher.initial, task, last, controls)
                result['carton_distance_to_goal_after_conflict_m'] = float(np.linalg.norm(
                    pose[:3, 3] - np.asarray(geometric['goal_pose'])[:3, 3]))
                if result['carton_distance_to_goal_after_conflict_m'] < .015:
                    raise ValueError('No appreciable continuation left after the conflict')
            np.savez_compressed(path / 'transitions.npz', **records)
            result['export_sha256'] = hashlib.sha256((path / 'transitions.npz').read_bytes()).hexdigest()
            result['status'] = 'VALIDATED'
            result['transitions'] = len(records['actions'])
            asset = dict(label=f"{name} / {'Avoidance' if kind == 'collision' else 'Free control'}",
                         variant='Teacher', duration_s=trajectory['duration_s'], validation=result['validation'],
                         frames=preview(teacher, trajectory))
            atomic_json(path / 'preview.json', asset)
        except (ValueError, np.linalg.LinAlgError) as error:
            result.update(status='REJECTED', reason=str(error))
    result['processing_s'] = time.monotonic() - begun
    atomic_json(path / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screening_root', type=Path)
    parser.add_argument('proposals', type=Path)
    parser.add_argument('selection', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = args.screening_root.resolve()
    screening, _, anchor, _, source, source_hash = load_reference(root)
    plan = json.loads(args.proposals.read_text())
    selection = json.loads(args.selection.read_text())
    if plan['screening_sha256'] != source_hash or plan['source_sha256'] != screening['source_sha256']:
        raise ValueError('Proposal binding differs from rear screening')
    families = {family['id']: family for family in plan['families']}
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    jobs = []
    for family_id, task_id in selection['cases']:
        family = families[family_id]
        candidate = next(item for item in family['attempts'] if item['task']['name'] == task_id)
        contacts = candidate['colliding_progress']
        if not candidate['eligible'] or not (candidate['check']['passed'] or contacts and max(contacts) <= .8):
            raise ValueError('Expected a free control or a collision with valid ends and remaining travel')
        jobs.append((family, candidate, out / f'{family_id}--{task_id}'))
    atomic_json(out / 'manifest.json', dict(executable=False, selection=selection,
                proposals_sha256=hashlib.sha256(args.proposals.read_bytes()).hexdigest(),
                screening_sha256=source_hash, timing_limits=LIMITS, bc_schema=SCHEMA,
                split='unassigned', arms=['left_rear', 'right_rear'],
                group_policy='Keep all cases associated with the same archived start anchor together.'))
    summary = []
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn')) as pool:
        futures = [pool.submit(generate_case, root, family, candidate, selection.get('seeds', {}), path)
                   for family, candidate, path in jobs]
        for future in as_completed(futures):
            result = future.result()
            summary.append({key: result[key] for key in ('id', 'family', 'group', 'status', 'reference_class',
                           'processing_s', 'reason', 'transitions') if key in result})
            atomic_json(out / 'summary.json', sorted(summary, key=lambda case: case['id']))
            print(result['id'], result['status'], result.get('reason', ''), flush=True)
    accepted = [path for _, _, path in jobs if (path / 'preview.json').is_file()]
    if accepted:
        with tempfile.TemporaryDirectory(prefix='uwa-rear-pilot-viewer-') as directory:
            teacher = build_teacher(directory, screening, anchor, source)
            sets = [json.loads((path / 'preview.json').read_text()) for path in accepted]
            write_viewer(out, teacher, sets, reference_only=False, distinct_goal=True, timed_rear=True,
                         gallery_title='Rear-arm teacher pilot')


if __name__ == '__main__':
    main()

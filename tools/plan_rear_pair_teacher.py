#!/usr/bin/env python3
"""Correct the archived rear-arm yaw reference in object space and compare both paths."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation

from preview_rear_pair_collision import build_teacher, load_reference, render_frames, write_viewer
from uwa_cell_motion.two_arm_teacher import pose_at


def check_geometry(teacher, task, controls):
    count = 1201  # Includes the original 61 evenly spaced reference samples.
    check = teacher.inspect(task, controls, count=count)
    if not check['complete']:
        return check
    rows = teacher.path_rows(task, controls, count=count)
    peak_translation = peak_orientation = closure_position = closure_angle = 0.0
    maximum_yaw = -np.inf
    bounds_ok = True
    for row in rows:
        pose = np.array(row['pose'])
        ideal = pose_at(teacher.initial, task, row['s'], np.zeros((6, 6)))
        delta = Rotation.from_matrix(pose[:3, :3] @ ideal[:3, :3].T)
        peak_translation = max(peak_translation, float(np.linalg.norm(pose[:3, 3] - ideal[:3, 3])))
        peak_orientation = max(peak_orientation, float(np.rad2deg(delta.magnitude())))
        relative = Rotation.from_matrix(pose[:3, :3] @ teacher.initial[:3, :3].T)
        maximum_yaw = max(maximum_yaw, float(relative.as_euler('zyx', degrees=True)[0]))
        state = dict(teacher.start, **dict(zip(teacher.names, row['q'])))
        bounds_ok &= all(teacher.collision.bounds[name][0] <= state[name] <= teacher.collision.bounds[name][1]
                         for name in teacher.names)
        for arm in teacher.arms:
            actual = teacher.problem.chains[arm].forward(state) @ teacher.tcp_offsets[arm]
            target = pose @ teacher.offsets[arm]
            closure_position = max(closure_position, float(np.linalg.norm(actual[:3, 3] - target[:3, 3])))
            error = Rotation.from_matrix(actual[:3, :3] @ target[:3, :3].T)
            closure_angle = max(closure_angle, float(error.magnitude()))
    endpoints = [rows[0], rows[-1]]
    endpoint_error = max(float(np.max(np.abs(np.array(row['pose']) -
                         pose_at(teacher.initial, task, row['s'], np.zeros((6, 6)))))) for row in endpoints)
    endpoint_joint_error = max(float(np.max(np.abs(np.array(row['q']) -
                               [teacher.start[name] for name in teacher.names]))) for row in endpoints)
    check.update(max_position_deviation_m=peak_translation, max_orientation_deviation_deg=peak_orientation,
                 max_world_z_yaw_deg=maximum_yaw, max_grasp_position_error_m=closure_position,
                 max_grasp_angle_error_rad=closure_angle, joint_bounds_ok=bool(bounds_ok),
                 endpoint_pose_matrix_max_error=endpoint_error, endpoint_joint_max_error_rad=endpoint_joint_error)
    check['passed'] = bool(check['passed'] and bounds_ok and closure_position <= 1e-6 and closure_angle <= 1e-5
                           and endpoint_error <= 1e-9 and endpoint_joint_error <= 1e-6)
    return check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screening', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, help='Recheck controls from an earlier optimizer JSON')
    args = parser.parse_args()
    screening, saved, reference, yaw, source, screening_hash = load_reference(args.screening)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    task = yaw['task']
    with tempfile.TemporaryDirectory(prefix='uwa-rear-teacher-') as directory:
        teacher = build_teacher(directory, screening, reference, source)
        if args.candidate:
            raw = args.candidate.read_bytes()
            optimization = json.loads(raw)
            candidate_sha256 = hashlib.sha256(raw).hexdigest()
        else:
            optimization = teacher.optimize(task, count=121, maxiter=35)
            candidate_sha256 = None
        controls = np.array(optimization['controls'], dtype=float)
        if (controls.shape != (6, 6) or not np.isfinite(controls).all()
                or np.max(np.abs(controls[:, :3])) > .12 + 1e-10
                or np.max(np.abs(controls[:, 3:])) > np.deg2rad(35) + 1e-10):
            raise ValueError('Candidate controls exceed the original teacher bounds')
        check = check_geometry(teacher, task, controls)
        report = dict(executable=False, stage='geometric_path', model_signature=teacher.problem.signature,
                      arms=list(teacher.arms), source_sha256=teacher.source_sha256, screening_sha256=screening_hash,
                      candidate_sha256=candidate_sha256, task=task, initial_pose=teacher.initial.tolist(),
                      initial_state=teacher.start, grasp_offsets=screening['rear_grasp_offsets'],
                      optimization=optimization, reference=yaw['inspection'], corrected=check)
        (out / 'result.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        if not check['passed']:
            raise RuntimeError('Candidate failed geometric checks; see result.json')

        count = yaw['inspection']['samples']
        reference_rows = teacher.path_rows(task, count=count)
        corrected_rows = teacher.path_rows(task, controls, count=count)
        contacts = out / 'contacts'
        contacts.mkdir()
        before, native = render_frames(teacher, reference_rows, contacts)
        after, corrected_contacts = render_frames(teacher, corrected_rows, contacts, reference_rows)
        expected = [row['s'] for row in yaw['inspection']['failures'] if not row['fcl_clear']]
        midpoint = count // 2
        if ([sample['s'] for sample in native] != expected or corrected_contacts
                or before[midpoint]['contact_pairs'] != saved['witness']['contact_pairs']):
            raise ValueError('Viewer samples do not reproduce the checked paths')
        write_viewer(out, teacher, [
            dict(label='Original reference', frames=before),
            dict(label='Teacher correction', frames=after, corrected=True, geometry=check),
        ], initial_frame=midpoint, initial_set=1)
        print(json.dumps({k: v for k, v in check.items() if k != 'failures'}, indent=2))


if __name__ == '__main__':
    main()

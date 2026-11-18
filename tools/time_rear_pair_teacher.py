#!/usr/bin/env python3
"""Time and verify the archived rear-arm correction as an offline model trajectory."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

from plan_two_arm_teacher import preview
from preview_rear_pair_collision import build_teacher, load_reference, write_viewer
from teacher_episode_core import sphere_table_gap
from uwa_cell_motion.common import ROBOT_IDS
from uwa_cell_motion.smooth_paths import sample_segment


LIMITS = dict(velocity=0.1, acceleration=0.4, jerk=2.0)
CHECK_STEP_S = 0.005


def arm_table_clearances(teacher, trajectory, times):
    """Check moving envelopes on the time grid and parked envelopes at the fixed pose."""
    model = teacher.problem.spheres
    tables = [box for box in teacher.environment_boxes if 'table' in box[0]]
    distal_links = ('upper_arm', 'forearm', 'wrist', 'robotiq')
    masks = {arm: np.array([any(part in link for part in distal_links) for link in model.links[arm]])
             for arm in ROBOT_IDS}
    if not tables or not all(mask.any() for mask in masks.values()):
        raise ValueError('Missing arm/table envelope geometry')
    def nearest(arm, world):
        mask = masks[arm]
        links = np.asarray(model.links[arm])[mask]
        candidates = []
        for name, table_pose, half in tables:
            gap, index, _ = sphere_table_gap(world[arm][mask], model.radii[arm][mask], table_pose, half)
            candidates.append(dict(gap_m=gap, table=name, link=str(links[index])))
        return min(candidates, key=lambda entry: entry['gap_m'])

    initial_world = model.world(teacher.start)
    parked = {arm: nearest(arm, initial_world) for arm in ROBOT_IDS if arm not in teacher.arms}
    moving = {arm: dict(gap_m=float('inf')) for arm in teacher.arms}
    joints = sample_segment(trajectory['segment'], times)
    for time_s, positions in zip(times, joints):
        state = dict(teacher.start, **dict(zip(teacher.names, positions)))
        world = model.world(state)
        for arm in teacher.arms:
            hit = nearest(arm, world)
            if hit['gap_m'] < moving[arm]['gap_m']:
                moving[arm] = dict(hit, time_s=float(time_s))
    return moving, parked


def endpoint_checks(teacher, trajectory, geometric):
    duration = trajectory['duration_s']
    start, initial_joints, start_progress = teacher.sample(trajectory, 0.0)
    goal, goal_joints, goal_progress = teacher.sample(trajectory, duration)
    errors = {
        'start_pose_matrix_max_error': float(np.max(np.abs(start - geometric['initial_pose']))),
        'goal_pose_matrix_max_error': float(np.max(np.abs(goal - geometric['goal_pose']))),
        'start_joint_max_error_rad': max(abs(initial_joints[name] - geometric['initial_state'][name])
                                         for name in teacher.names),
        'goal_joint_max_error_rad': max(abs(goal_joints[name] - expected) for name, expected in
                                        zip(teacher.names, geometric['goal_joint_positions_rad'])),
    }
    at_rest = [float(np.max(np.abs(sample_segment(trajectory['segment'], [0.0, duration], order))))
               for order in (1, 2, 3)]
    errors['endpoint_derivative_peaks'] = at_rest
    errors['passed'] = bool(start_progress == 0 and goal_progress == 1
                            and errors['start_pose_matrix_max_error'] <= 1e-9
                            and errors['goal_pose_matrix_max_error'] <= 1e-9
                            and errors['start_joint_max_error_rad'] <= 1e-6
                            and errors['goal_joint_max_error_rad'] <= 1e-6
                            and max(at_rest) <= 1e-8)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screening', type=Path)
    parser.add_argument('geometric_result', type=Path, help='Passed step 2 result.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    screening, _, reference, _, source, screening_hash = load_reference(args.screening)
    raw = args.geometric_result.read_bytes()
    geometric = json.loads(raw)
    if (geometric['stage'] != 'geometric_path' or geometric['executable'] is not False
            or not geometric['corrected']['passed'] or geometric['screening_sha256'] != screening_hash):
        raise ValueError('Expected a passed, bound offline geometry report')
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='uwa-rear-timing-') as directory:
        teacher = build_teacher(directory, screening, reference, source)
        if (geometric['model_signature'] != teacher.problem.signature
                or geometric['source_sha256'] != teacher.source_sha256
                or geometric['arms'] != list(teacher.arms) or geometric['joint_names'] != teacher.names
                or geometric['initial_state'] != teacher.start
                or geometric['grasp_offsets'] != screening['rear_grasp_offsets']
                or not np.array_equal(geometric['initial_pose'], teacher.initial)):
            raise ValueError('Geometric result differs from the bound model or start')
        controls = np.array(geometric['optimization']['controls'])
        trajectory = teacher.trajectory(geometric['task'], controls, **LIMITS)
        duration = trajectory['duration_s']
        print(f'Model duration {duration:.3f} s. Checking full interpolated motion.', flush=True)
        validation = teacher.validate(trajectory, dt=CHECK_STEP_S, **LIMITS)
        times = np.linspace(0, duration, validation['samples'])
        moving_table, parked_table = arm_table_clearances(teacher, trajectory, times)
        table_gap = min(entry['gap_m'] for entry in moving_table.values())
        endpoints = endpoint_checks(teacher, trajectory, geometric)
        dense_times = np.linspace(0, duration, 20001)
        dense_peaks = [float(np.max(np.abs(sample_segment(trajectory['segment'], dense_times, order))))
                       for order in (1, 2, 3)]
        derivatives_ok = all(peak <= limit + 1e-7 for peak, limit in zip(dense_peaks, LIMITS.values()))
        model_geometry_passed = validation['passed']
        # Same scope as the episode teacher. Fixed arms still participate in the
        # full FCL and all-pair tests at every sample in TwoArmTeacher.validate.
        validation.update(min_moving_arm_table_gap_m=table_gap, moving_arm_table=moving_table,
                          parked_arm_table_baseline=parked_table, endpoint_checks=endpoints,
                          dense_derivative_samples=len(dense_times), dense_derivative_peaks=dense_peaks,
                          passed=bool(model_geometry_passed and table_gap >= .003 - 1e-8
                                      and endpoints['passed'] and derivatives_ok))
        report = dict(stage='time_parameterized_model', executable=False, arms=list(teacher.arms),
                      parked_arms=[arm for arm in ROBOT_IDS if arm not in teacher.arms],
                      model_signature=teacher.problem.signature, source_sha256=teacher.source_sha256,
                      screening_sha256=screening_hash, geometry_sha256=hashlib.sha256(raw).hexdigest(),
                      timing_limits=LIMITS, initial_state=teacher.start,
                      initial_pose=geometric['initial_pose'], goal_pose=geometric['goal_pose'],
                      grasp_offsets=geometric['grasp_offsets'], trajectory=trajectory, validation=validation)
        (out / 'result.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        if not validation['passed']:
            raise RuntimeError('Timed model path failed verification; see result.json')
        write_viewer(out, teacher, [dict(label='Timed teacher correction', variant='Teacher',
                     duration_s=duration, validation=validation, frames=preview(teacher, trajectory))],
                     reference_only=False, distinct_goal=True, timed_rear=True)
        print(json.dumps({key: val for key, val in validation.items() if key != 'failures'}, indent=2))


if __name__ == '__main__':
    main()

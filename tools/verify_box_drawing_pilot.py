#!/usr/bin/env python3
"""Audit saved joint interpolants/episode links without the drawing-model API."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'uwa_cell_tasks'))
from uwa_cell_tasks.pilot_episode import Episode, write
from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.smooth_paths import sample_segment
from uwa_cell_gazebo.charuco_views import Chain


def audit(run):
    run = Path(run)
    report = json.loads((run/'result.json').read_text())
    episode = Episode(run/'episode')
    policy_hash = hashlib.sha256((run/'policy.py').read_bytes()).hexdigest()
    assert policy_hash == report['policy_sha256'] == episode.manifest['program_sha256']
    assert hashlib.sha256(Path(report['source_path']).read_bytes()).hexdigest() == report['source_sha256']
    urdf = (run/'model/carton-moveit/robot.urdf').read_text()
    assert hashlib.sha256(urdf.encode()).hexdigest() == report['model_urdf_sha256']
    for path, sha in report['mesh_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha, path
    chains = {a: Chain(urdf, 'world', a+'_tool0') for a in ROBOT_IDS}
    holders = report['program']['holding_arms']
    worker = report['program']['working_arm']
    names = [j for a in ROBOT_IDS for j in joint_names(a)]
    tcp = {a: np.array(report['holder_tcp_offsets'][a]) for a in holders}
    offsets = {a: np.array(report['grasp_offsets'][a]) for a in holders}
    initial = report['initial_state']
    last = np.array([initial[j] for j in names])
    closure = angle = tip_error = jump = 0.
    peaks = np.zeros(3)
    total = 0.
    samples = 0
    phase_names = []
    drawn = []
    face_geometry = {'y_max': (1, 1), 'z_min': (2, -1), 'y_min': (1, -1)}
    for phase in report['phases']:
        phase_names.append(phase['id'])
        segment = phase['segment']
        duration = phase['duration_s']
        ts = np.linspace(0, duration, 2001)
        for order in (1, 2, 3):
            peaks[order-1] = max(peaks[order-1], float(np.max(abs(sample_segment(segment, ts, order)))))
        positions = sample_segment(segment, np.linspace(0, duration, 151))
        jump = max(jump, float(np.max(abs(last-positions[0]))))
        angles = []
        for q in positions:
            state = dict(initial, **dict(zip(names, q)))
            poses = {a: chains[a].forward(state)@tcp[a]@np.linalg.inv(offsets[a]) for a in holders}
            base = poses[holders[0]]
            closure = max(closure, float(np.linalg.norm(base[:3, 3]-poses[holders[1]][:3, 3])))
            angle = max(angle, float(np.linalg.norm(Rotation.from_matrix(base[:3, :3]@poses[holders[1]][:3, :3].T).as_rotvec())))
            assert all(abs(state[j]-initial[j])<1e-10 for j in joint_names('left_rear'))
            if phase['drawing']:
                assert all(abs(state[j]-positions[0][names.index(j)])<1e-8 for a in holders for j in joint_names(a))
                tool = chains[worker].forward(state)
                tip = tool[:3, 3]+.30*tool[:3, 2]
                local = base[:3, :3].T@(tip-base[:3, 3])
                axis, sign = face_geometry[phase['face']]
                angles.append(np.arctan2(-local[2] * sign if axis == 1 else local[1] * sign,
                                         local[0]))
                tip_error = max(tip_error, abs(local[axis]-sign*report['dimensions_m'][axis]/2),
                                abs(np.linalg.norm(np.delete(local, axis))-.025))
            samples += 1
        if angles:
            sweep = np.unwrap(angles)
            assert abs(sweep[-1] - sweep[0] - 2*np.pi) < .001
            assert np.all(np.diff(sweep) > 0)
            drawn.append(phase['face'])
        last = positions[-1]
        total += duration
    assert closure<1e-6 and angle<1e-5 and jump<1e-7 and tip_error<.00025
    assert drawn == report['program']['surfaces']
    assert len(drawn) == len(set(drawn))
    assert np.max(abs(last - [initial[j] for j in names])) < 1e-7
    velocity = report['program'].get('velocity_rad_s', .35)
    if 'y_min' in drawn:
        assert velocity == .1
    assert np.all(peaks <= np.array([velocity, .4, 2.])+1e-6)
    rows = episode.records()
    starts = [r for r in rows if r['kind']=='phase_start']
    ends = [r for r in rows if r['kind']=='phase_end']
    assert [r['phase'] for r in starts] == [r['phase'] for r in ends] == phase_names
    assert len(starts)==len(report['phases'])
    elapsed = 0.
    for start, end, phase in zip(starts, ends, report['phases']):
        assert abs(start['model_time_s']-elapsed)<1e-8
        elapsed += phase['duration_s']
        assert abs(end['model_time_s']-elapsed)<1e-8
    summary = episode.summary()
    assert summary['status']=='MODEL_SEQUENCE_COMPLETE' and abs(total-summary['model_duration_s'])<1e-8
    assert not summary['force_channels'] and summary['detected_events']['object_lost'] is None
    return dict(passed=True, result_sha256=hashlib.sha256((run/'result.json').read_bytes()).hexdigest(),
                scope='independent FK/time/episode audit; not independent collision or physical validation',
                drawn_faces=drawn, phase_count=len(phase_names), kinematic_samples=samples, derivative_samples_per_phase=2001,
                derivative_peaks=peaks.tolist(), duration_model_s=total, max_phase_jump_rad=jump,
                max_holder_position_disagreement_m=closure, max_holder_orientation_disagreement_rad=angle,
                max_tool_reference_error_m=float(tip_error), feedback_count=len(summary['feedback']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a new audit output file')
    result=audit(args.run)
    write(args.output,result)
    print(json.dumps(result,indent=2))

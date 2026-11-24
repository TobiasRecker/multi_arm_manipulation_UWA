#!/usr/bin/env python3
"""Prepare two small four-arm paths from a saved native snapshot, offline only.

No ROS initialization, device readers, services or robot commands are used.
The unchanged 0.1 rad/s command cap and existing acceleration cap determine
quintic timing; there is no observation-time slowdown or serial fallback.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

import numpy as np

from uwa_cell_motion.common import ROBOT_IDS, config, dump, joint_names
from uwa_cell_motion.hardware_model import HardwareProblem, inventory_path
from uwa_cell_motion.minimal_execution import split_trajectory
from uwa_cell_tasks.reviewed_carton import prove_group
from prepare_minimal_protection import export_model


def start_from_snapshot(snapshot, names):
    """Accepted inputs are shared state packets or minimal_snapshot.observe()."""
    if snapshot.get('unit', 'rad') != 'rad':
        raise ValueError('Native joint positions must be radians')
    positions = snapshot.get('positions', snapshot.get('start', {}))
    result = {}
    for arm in ROBOT_IDS:
        joints = names[arm][:6]
        if all(joint in positions for joint in joints):
            q = [positions[joint] for joint in joints]
        else:
            record = snapshot.get('records', {}).get(arm)
            if record is not None:
                q = record['q']
            else:
                record = snapshot.get('arms', {}).get(arm, {})
                sample = (record.get('samples') or [{}])[-1]
                q = sample.get('actual_q', record.get('q'))
        q = np.asarray(q, dtype=float)
        if q.shape != (6,) or not np.isfinite(q).all():
            raise ValueError('Complete finite saved native positions required: '+arm)
        result.update(zip(joints, q.tolist()))
        result.update({joint: 0. for joint in names[arm][6:]})
    return result


def wrist_targets(problem, start, amplitude, signs=None):
    """Keep the arm configuration; roll each unloaded tool about its last axis."""
    if not np.isfinite(amplitude) or amplitude <= 0:
        raise ValueError('Positive finite wrist displacement required')
    if signs is not None and (len(signs) != 4 or any(value not in (-1, 1) for value in signs)):
        raise ValueError('Expected four signs, each -1 or 1, in ROBOT_IDS order')
    targets, deltas = {}, {}
    for index, arm in enumerate(ROBOT_IDS):
        names = joint_names(arm)
        q = np.array([start[joint] for joint in names])
        lo, hi = problem.collision.bounds[names[-1]]
        sign = signs[index] if signs is not None else (1 if q[-1] <= (lo+hi)/2 else -1)
        if not lo <= q[-1]+sign*amplitude <= hi:
            raise ValueError(arm+': requested wrist roll exceeds the offline joint bounds')
        q[-1] += sign*amplitude
        targets[arm], deltas[arm] = q.tolist(), sign*amplitude
    return targets, deltas


def prepare(args):
    for name in ('output', 'snapshot', 'inventory', 'config', 'cpp_replay'):
        setattr(args, name, getattr(args, name).expanduser().resolve())
    if args.layout is not None:args.layout = args.layout.expanduser().resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = json.loads(args.snapshot.read_text())
    cfg = config(args.config)
    if cfg.get('command_velocity_limit_rad_s', cfg['velocity_limit_rad_s']) != .1:
        raise ValueError('Functional test must retain the approved 0.1 rad/s command cap')
    if cfg.get('stopping_reserve_policy') != 'geometric_only':
        raise ValueError('Use the approved geometric-only hardware planning profile')
    problem = HardwareProblem(args.output/'model', cfg, args.inventory, args.layout)
    if snapshot.get('model_signature') and snapshot['model_signature'] != problem.signature:
        raise ValueError('Saved native snapshot and offline model signatures differ')
    start = start_from_snapshot(snapshot, problem.names)
    targets, deltas = wrist_targets(problem, start, args.amplitude, args.signs)
    state = dict(start)
    groups, native_states = [], []
    for name, goals in (('outward', targets),
                        ('return', {arm: [start[joint] for joint in joint_names(arm)] for arm in ROBOT_IDS})):
        request = problem.normalize(dict(start=state, goals=goals))
        q0 = [state[joint] for joint in request['joint_names']]
        # Only this simultaneous direct path is eligible; no detour, serial
        # fallback, smaller displacement or time stretch is substituted.
        trajectory = problem.time_parameterize(request, [q0, request['target']])
        trajectories = split_trajectory(trajectory, list(ROBOT_IDS))
        proof, error = prove_group(problem, state, trajectories, .1)
        if error:
            raise ValueError(name+': independent four-arm progress not proved: '+error)
        samples = [problem.state(request, point['positions']) for point in trajectory['points']]
        native_states.extend(samples)
        # Also replay every independent start/end combination through the new
        # C++ full-cell core, besides the existing swept-volume proof.
        for choices in itertools.product((0, 1), repeat=4):
            corner = dict(state)
            for arm, choice in zip(ROBOT_IDS, choices):
                if choice:
                    corner.update(zip(joint_names(arm), goals[arm]))
            native_states.append(corner)
        groups.append(dict(name=name, arms=list(ROBOT_IDS), start=dict(state),
                           trajectories=trajectories, trajectory=trajectory,
                           duration_s=trajectory['duration_s'], independent_progress_proof=proof))
        state.update(zip(request['joint_names'], request['target']))
    model_config = export_model(problem, args.output, mode='hardware')
    state_path = args.output/'cpp-replay-states.json'
    dump(state_path, dict(states=native_states))
    replay = subprocess.run([str(args.cpp_replay), str(model_config), str(state_path)],
                            capture_output=True, text=True, check=True)
    (args.output/'cpp-replay.log').write_text(replay.stderr)
    checked = json.loads(replay.stdout)
    dump(args.output/'cpp-replay-result.json', checked)
    if checked['model_signature'] != problem.signature or any(not row['clear'] for row in checked['states']):
        raise ValueError('New C++ collision core rejected the prepared functional-test states')
    result = dict(schema_version=1, kind='minimal_four_arm_functional_test', ready=True,
                  offline_only=True, commands_sent=[], model_signature=problem.signature,
                  source_snapshot=str(args.snapshot.resolve()),
                  source_snapshot_sha256=hashlib.sha256(args.snapshot.read_bytes()).hexdigest(),
                  inventory=str(args.inventory.resolve()), layout_path=str(args.layout.resolve()) if args.layout else None,
                  config=cfg, start=start, wrist_delta_rad=deltas, groups=groups,
                  command_joint_limit_rad_s=.1,
                  acceleration_limit_rad_s2=cfg['acceleration_limit_rad_s2'],
                  check_step_rad=cfg['joint_check_step_rad'],
                  cpp_replay_states=len(native_states),
                  sequence='two four-arm tasks; one explicit software pause/resume during outward task',
                  scope='Unloaded wrist rolls; no gripper changes, collisions or state-fault injections')
    dump(args.output/'functional-test.json', result)
    print(json.dumps(dict(ready=True, plan=str((args.output/'functional-test.json').resolve()),
                          model_signature=problem.signature, wrist_delta_rad=deltas,
                          duration_s=[group['duration_s'] for group in groups],
                          command_joint_limit_rad_s=.1, cpp_replay_states=len(native_states), commands_sent=[])))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cpp-replay', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, default=inventory_path())
    parser.add_argument('--layout', type=Path)
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1]/
                        'uwa_cell_motion/config/hardware_carton_supported_trend.yaml')
    parser.add_argument('--amplitude', type=float, default=.1, help='Wrist-3 displacement in radians, retained in both tasks')
    parser.add_argument('--signs', type=lambda value: [int(item) for item in value.split(',')],
                        help='Explicit LF, LR, RF, RR signs; otherwise choose toward each joint-range centre')
    args = parser.parse_args(argv)
    prepare(args)


if __name__ == '__main__':
    main()

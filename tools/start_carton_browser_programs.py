#!/usr/bin/env python3
"""Start only the required External Control programs under unloaded holds."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from run_carton_pregrasp import read_gripper_status, start_ros_programs_held, ApproachClient
from uwa_cell_motion.common import ROBOT_IDS, config
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_tasks.hardware_carton_approach import unloaded_open_status
from uwa_cell_tasks.motion_review import ReviewStore


REPO = Path(__file__).resolve().parents[1]
ARMS = ('right_front', 'right_rear')


def programs_needing_play(output):
    command = [sys.executable, str(REPO / 'scripts/ur_bringup.py'), '--status', '--json']
    for arm in ARMS:
        command.extend(['--arm', arm])
    result = subprocess.run(command, capture_output=True, text=True, timeout=12)
    (output / 'program-readiness.json').write_text(result.stdout)
    readiness = json.loads(result.stdout)
    arms = readiness.get('arms', {})
    if result.returncode not in (0, 1) or set(arms) != set(ARMS):
        raise ValueError(readiness.get('error') or 'Incomplete External Control status.')
    needs_play = []
    for arm in ARMS:
        status = arms[arm]
        if status['code'] == 'ready':
            continue
        if status['code'] == 'needs_preparation' and status.get('next_step') == 'play':
            needs_play.append(arm)
        else:
            raise ValueError(f"{arm}: {status['message']}")
    return needs_play


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--scene-session', required=True)
    args = parser.parse_args()
    require_domain('hardware')
    status = ReviewStore().status()
    if not status['area_released'] or status['session_id'] != args.scene_session or status['pending']:
        raise ValueError('The work area changed or another motion review is open.')
    arms = programs_needing_play(args.output)
    if not arms:
        print('External Control already playing on both carton arms.')
        return

    evidence = {'requested_arms': arms}

    def save():
        (args.output / 'browser-play.json').write_text(json.dumps(evidence, indent=2) + '\n')

    with TemporaryDirectory(prefix='carton-browser-play-') as models, motion_context():
        problem = HardwareProblem(models, config(args.config), REPO / 'config/hardware_inventory.yaml')
        # Monitor only. The startup client acquires no trajectory actions.
        client = ApproachClient(problem, [], {})
        try:
            for arm in ROBOT_IDS:
                if not unloaded_open_status(read_gripper_status(client, arm)):
                    raise ValueError(f'{arm}: open, unloaded gripper required for Play.')
            start_ros_programs_held(client, args.output, problem, evidence, save,
                                    browser_play=(args.scene_session, arms))
        finally:
            client.destroy_node()
    print('External Control playing on ' + ', '.join(arms) + '.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from error

#!/usr/bin/env python3
"""Start only the required External Control programs under unloaded holds."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

from std_srvs.srv import Trigger
from run_carton_pregrasp import read_gripper_status, start_ros_programs_held, ApproachClient
from uwa_cell_gripper_control.api import endpoint
from uwa_cell_motion.common import ROBOT_IDS, config
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_tasks.hardware_carton_approach import retained_holds, unloaded_guard_ready, unloaded_open_status
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


def check_unloaded_grippers(client):
    reads = {}
    for arm in ROBOT_IDS:
        name = endpoint(arm, 'hardware') + '/read'
        rpc = client.create_client(Trigger, name)
        client.rpc_clients[(Trigger, name)] = rpc
        reads[name] = rpc
    try:
        client.wait(lambda: all(rpc.service_is_ready() for rpc in reads.values()), timeout=10.)
    except TimeoutError as error:
        missing = [name for name, rpc in reads.items() if not rpc.service_is_ready()]
        if missing:
            raise RuntimeError('Gripper read service unavailable: ' + ', '.join(missing)) from error
    for arm in ROBOT_IDS:
        try:
            status = read_gripper_status(client, arm)
        except (RuntimeError, TimeoutError) as error:
            raise RuntimeError(f'{arm}: gripper status read failed: {error}') from error
        if not unloaded_open_status(status):
            raise ValueError(f'{arm}: carton setup requires an open, unloaded gripper.')


def check_scene(scene):
    status = ReviewStore().status()
    if not status['area_released'] or status['session_id'] != scene or status['pending']:
        raise ValueError('The work area changed or another motion review is open.')


def prepare_start_holds(client, scene, evidence):
    """Take only missing initial holds. A later phase must retain its own holds."""
    check_scene(scene)
    client.health()
    holds = retained_holds(client.supervisor, ROBOT_IDS)
    evidence['holds_before'] = holds
    if not holds['issues']:
        return
    if holds['verification_issues']:
        raise RuntimeError('Carton hold setup unavailable. ' + '. '.join(holds['verification_issues']))
    guard = client.guard
    if not unloaded_guard_ready(guard):
        unconfirmed = sorted(set(ROBOT_IDS) - set(guard.get('stationary_arms', [])))
        raise RuntimeError(f"Carton setup requires all arms stationary. Unconfirmed arms: {unconfirmed}. "
                           f"Guard faults: {guard.get('faults')}.")
    if (guard.get('armed') is not True or guard.get('stop_adapter_available') is not True
            or (guard.get('pilot') or {}).get('state') != 'ARMED_HOLD_OR_EXTERNAL_SOURCE'):
        raise RuntimeError('Carton hold setup requires an available armed guard and an idle motion executor.')
    if (not client.witness_peer.fresh(time.monotonic(), client.cfg['heartbeat_timeout_s'])
            or client.witness.get('tripped') is not False or client.witness.get('native_stop_pending') != []
            or client.supervisor.get('native_stop_pending') != []):
        raise RuntimeError('Carton hold setup blocked by the watchdog or a pending native stop. Check Safety log.')
    missing = holds['unlatched_arms']
    if missing:
        unavailable = [arm for arm in missing if not client.stop_clients[arm].service_is_ready()]
        if unavailable:
            raise RuntimeError('Supervisor hold service unavailable for ' + ', '.join(unavailable))
        before = {arm: record['status'] for arm, record in client.records.items()}
        evidence['hold_requests'] = list(missing)
        result = client.stop(missing)
        evidence['hold_result'] = result
        if not result['resource_holds_confirmed'] or not result['latches_confirmed']:
            detail = retained_holds(client.supervisor, missing)['issues'] + result['errors']
            raise RuntimeError('Initial arm hold failed. ' + '. '.join(detail) + '. Check Safety log.')
        client.health()
        changed = [arm for arm, status in before.items() if client.records[arm]['status'] != status]
        if changed:
            raise RuntimeError('Native arm state changed during hold setup. Check Safety log for ' + ', '.join(changed))
    # A stop RPC or an older cached status cannot confirm the handoff.
    client.health()
    after = retained_holds(client.supervisor, ROBOT_IDS)
    evidence['holds_after'] = after
    if after['issues']:
        raise RuntimeError('Initial arm holds incomplete. ' + '. '.join(after['issues']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--scene-session', required=True)
    args = parser.parse_args()
    require_domain('hardware')
    check_scene(args.scene_session)
    arms = programs_needing_play(args.output)

    evidence = {'requested_arms': arms}

    def save():
        (args.output / 'browser-play.json').write_text(json.dumps(evidence, indent=2) + '\n')

    save()
    with TemporaryDirectory(prefix='carton-browser-play-') as models, motion_context():
        problem = HardwareProblem(models, config(args.config), REPO / 'config/hardware_inventory.yaml')
        # Only supervisor holds and scoped Play are available to this client.
        client = ApproachClient(problem, [], {})
        try:
            client.connect()
            client.wait(lambda: client.witness is not None, timeout=3., health=True)
            evidence['holds_before'] = retained_holds(client.supervisor, ROBOT_IDS)
            if arms or evidence['holds_before']['issues']:
                check_unloaded_grippers(client)
                evidence['open_unloaded_grippers_confirmed'] = True
                prepare_start_holds(client, args.scene_session, evidence)
            if arms:
                check_scene(args.scene_session)
                start_ros_programs_held(client, args.output, problem, evidence, save,
                                        browser_play=(args.scene_session, arms))
        except Exception as error:
            evidence['error'] = str(error)
            raise
        finally:
            client.destroy_node()
            save()
    print('Initial holds confirmed. External Control ready on both carton arms.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from error

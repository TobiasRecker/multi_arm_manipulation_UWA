#!/usr/bin/env python3
"""Four-arm standby and startup CLI used by the local desktop app."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import asdict
import json
from pathlib import PurePosixPath
import sys
import time

from ur_bringup import (Blocked, Dashboard, INVENTORY, ROBOT_IDS, SAFE, inspect,
                        launch_driver, load_arms, operation_lock, run_arm, running_target, transport)


def stop_for_standby(arm, *, dashboard=Dashboard, timeout=18):
    result = {'arm': arm.id, 'state': None, 'commands': [], 'ros_reverse_connected': None}

    def read(dash):
        state = inspect(dash, arm)
        result['state'] = asdict(state)
        return state

    def validate(state):
        if state.remote is False:
            raise Blocked('local_control', 'Select Remote Control at the Teach Pendant.')
        if state.playback != 'STOPPED' and (
            state.program != arm.program or
            state.playback_program not in (arm.program, PurePosixPath(arm.program).name)
        ):
            raise Blocked('program_in_use', 'Another program is running or paused.')
        if state.mode not in ('POWER_OFF', 'IDLE', 'RUNNING'):
            raise Blocked('robot_mode_blocked', f'Robot is in {state.mode}.')

    def issue(dash, command, expected):
        entry = {'command': command}
        result['commands'].append(entry)
        try:
            reply = dash.ask(command)
        except OSError as error:
            entry['error'] = str(error)
            raise Blocked('command_outcome_unknown', f'No response to {command!r}.') from error
        entry['reply'] = reply
        if reply.lower() != expected.lower():
            code = 'local_control' if 'remote control' in reply.lower() else 'command_rejected'
            raise Blocked(code, f'{command}: {reply}')

    def wait(dash, condition, phase):
        deadline = time.monotonic() + timeout
        while True:
            state = read(dash)
            if condition(state):
                return state
            validate(state)
            if time.monotonic() >= deadline:
                raise Blocked('transition_timeout', f'{phase} was not confirmed.')
            time.sleep(.25)

    try:
        with dashboard(arm).connect() as dash:
            state = read(dash)
            if state.mode == 'POWER_OFF' and state.playback == 'STOPPED':
                return dict(result, code='standby')
            validate(state)
            if state.playback != 'STOPPED':
                issue(dash, 'stop', 'Stopped')
                wait(dash, lambda s: s.playback == 'STOPPED', 'Program stop')
            state = read(dash)
            if state.mode != 'POWER_OFF' or state.playback != 'STOPPED':
                validate(state)
                if state.playback != 'STOPPED':
                    raise Blocked('program_in_use', 'Program state changed after stop.')
                issue(dash, 'power off', 'Powering off')
                wait(dash, lambda s: s.mode == 'POWER_OFF' and s.playback == 'STOPPED', 'Arm power off')
        return dict(result, code='standby')
    except Blocked as error:
        # Expose actual command reply, but keep the English guidance separate.
        return dict(result, code=error.code, detail=str(error) if result['commands'] else None)
    except OSError:
        return dict(result, code='readback_lost' if result['commands'] else 'unreachable')


def status(arm, *, dashboard=Dashboard, get_transport=transport):
    result = {'arm': arm.id, 'state': None, 'commands': [], 'ros_reverse_connected': None}
    try:
        with dashboard(arm).connect() as dash:
            state = inspect(dash, arm)
        result['state'] = asdict(state)
        if state.mode == 'POWER_OFF' and state.playback == 'STOPPED':
            return dict(result, code='standby')
        if state.mode == 'CONFIRM_SAFETY':
            return dict(result, code='confirm_safety')
        if state.safety not in SAFE:
            return dict(result, code='safety_blocked')
        if state.mode == 'RUNNING' and running_target(arm, state):
            _, reverse = get_transport(arm)
            return dict(result, ros_reverse_connected=reverse, code='ready' if reverse else 'ros_not_connected')
        return dict(result, code='local_control' if state.remote is False else 'needs_preparation')
    except Blocked as error:
        return dict(result, code=error.code)
    except OSError:
        return dict(result, code='unreachable')


def execute(mode, arms, emit):
    with operation_lock() if mode != 'status' else nullcontext():
        if mode == 'status':
            with ThreadPoolExecutor(max_workers=len(arms)) as pool:
                results = list(pool.map(status, arms))
            for result in results:
                emit('arm', result=result)
            return True

        target = 'standby' if mode == 'standby' else 'ready'
        results = []
        for arm in arms:
            emit('progress', arm=arm.id)
            result = (stop_for_standby(arm) if mode == 'standby'
                      else run_arm(arm, True, start_driver=launch_driver))
            results.append(result)
            emit('arm', result=result)

        # The early arms may have changed while preparing later arms.
        verified = [arm for arm, result in zip(arms, results) if result['code'] == target]
        with ThreadPoolExecutor(max_workers=4) as pool:
            latest = {result['arm']: result for result in pool.map(status, verified)}
        for row in results:
            if row['arm'] in latest and latest[row['arm']]['code'] != target:
                row.update(latest[row['arm']], commands=row['commands'])
                emit('arm', result=row)
        return all(row['code'] == target for row in results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('status', 'standby', 'start'))
    args = parser.parse_args(argv)

    def emit(event, **payload):
        print(json.dumps({'event': event, **payload}, ensure_ascii=False), flush=True)

    try:
        inventory = load_arms(INVENTORY)
        ok = execute(args.mode, [inventory[rid] for rid in ROBOT_IDS], emit)
    except Exception as error:
        emit('error', message=str(error))
        return 2
    emit('done', success=ok)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

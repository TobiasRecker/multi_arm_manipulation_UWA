"""Reviewed trajectories using the shared collision-only protection service."""
import json
from pathlib import Path
import subprocess
import sys
import time

from uwa_cell_motion.common import dump, joint_names
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.minimal_execution import MinimalHardwareClient
from .motion_review import ReviewStore
from .reviewed_carton import START_TOLERANCE, speed_envelope


def start_programs(client, directory, arms, *, review=None, scene=None):
    """An explicitly requested Play operation, with no hold/watchdog ceremony."""
    if not arms:
        return {}
    repo = Path(__file__).resolve().parents[2]
    command = [sys.executable, str(repo/'scripts/ur_bringup.py'), '--apply', '--json']
    for arm in arms:
        command.extend(['--arm', arm])
    if review:
        command.extend(['--review-id', review[0], '--review-component', review[1],
                        '--review-stage', review[2]])
    elif scene:
        command.extend(['--play-only-for-scene', scene])
    else:
        raise ValueError('Program Play requires the existing explicit review or scene authorization')
    directory = Path(directory)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(subprocess.run, command, capture_output=True, text=True, timeout=30.)
        client.wait(future.done, timeout=35.)
        result = future.result()
    path = directory/'program-start.json'
    path.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError('External Control start failed: '+(result.stderr or result.stdout)[-1000:])
    return dict(returncode=result.returncode, report=str(path), arms=list(arms))


def run_bundle(problem, bundle, args, output, report, *, end_phase):
    groups = bundle['groups']
    arms = sorted({arm for group in groups for arm in group['arms']})
    review = getattr(args, 'review_id', None)
    store = ReviewStore() if review else None
    component = getattr(args, 'reviewed_sha256', None)
    if store:
        store.check_active(review, component, stage='motion')
    envelope = speed_envelope(problem, arms, bundle['joint_limit_rad_s'], bundle['tcp_limit_m_s'])
    for group in groups:
        if set(group['arms']) != set(group['trajectories']) or not group['arms']:
            raise ValueError('Malformed reviewed arm group')
        for arm, trajectory in group['trajectories'].items():
            if trajectory['joint_names'] != joint_names(arm):
                raise ValueError('Reviewed joint order changed')
            envelope.check_trajectory(arm, trajectory['points'])
    output = Path(output)
    began = time.monotonic()
    report.update(success=False, phase='REVIEWED_PREFLIGHT', protection_backend='minimal',
                  review_id=review, reviewed_sha256=component, arm_commands=[], finger_commands=[],
                  command_velocity_rad_s=bundle['joint_limit_rad_s'], tcp_limit_m_s=bundle['tcp_limit_m_s'],
                  segments=[])
    def save():
        dump(output/'result.json', report)
    save()
    with motion_context():
        client = MinimalHardwareClient(problem, 'hardware', arms)
        try:
            if store:
                store.begin_component(review, component, stage='motion')
            client.connect()
            if getattr(args, 'start_ros_programs', False):
                if store:
                    store.check_startup(review, 'motion')
                report['program_start'] = start_programs(client, output, arms,
                    review=(review, component, 'motion') if store else None,
                    scene=None if store else ReviewStore().status()['session_id'])
            for index, group in enumerate(groups):
                # Start matching is an input check for the approved path, never
                # a stationary-joint monitor during the subsequent execution.
                client.wait_unpaused()
                client.health()
                if not set(group['start']) <= client.positions.keys():
                    raise ValueError('Current joint inputs unavailable for the reviewed start')
                if any(abs(client.positions[j]-q) > START_TOLERANCE
                       for j, q in group['start'].items()):
                    raise ValueError('Current start differs from the reviewed trajectory; replan')
                segment = dict(arms=group['arms'], executed=False, group=index,
                               group_started_monotonic_s=time.monotonic())
                report['segments'].append(segment)
                report['phase'] = 'REVIEWED_'+bundle['phase'].upper()
                report['arm_commands'].append(dict(arms=group['arms'], group=index,
                                                   bundle_sha256=component))
                save()
                client.follow_group(group['trajectories'], duration_s=group['duration_s'], segment=segment)
                segment['end_monotonic_s'] = time.monotonic()
                save()
            report.update(success=True, phase=end_phase)
            return 0
        except KeyboardInterrupt as error:
            # An operator cancellation is an explicit software-stop request.
            report.update(error=str(error), phase='PAUSE_REQUESTED_BY_OPERATOR')
            try:
                report['stop_result'] = client.stop()
            except Exception as stop_error:
                report['stop_error'] = str(stop_error)
            return 1
        except Exception as error:
            report.update(error=str(error), phase='EXECUTION_FAILED',
                          protection_status=client.protection_status)
            # No new all-arm safety trigger for ordinary controller/RPC errors.
            return 1
        finally:
            report.update(reviewed_runner_s=time.monotonic()-began,
                          service_timings=client.service_timings,
                          final_positions=dict(client.positions))
            save()
            client.destroy_node()

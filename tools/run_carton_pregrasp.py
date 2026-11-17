#!/usr/bin/env python3
"""Explicit unloaded RF-then-RR approach; no entry, fingers or loaded motion.

Default: verify/model-check saved geometric evidence only. --execute plus
--reset-unloaded permits one stationary reset per arm, with all four grippers
confirmed open and all other arms re-held before each individual arm goal.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from std_srvs.srv import Trigger

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'uwa_cell_tasks'))
from uwa_cell_tasks.hardware_carton_approach import checked_problem
from uwa_cell_motion.common import ROBOT_IDS, joint_names, dump
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_execution import HardwareClient
from uwa_cell_motion.single_execution import follow
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_gripper_control.client import GripperClient


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--inventory', type=Path, default=REPO/'config/hardware_inventory.yaml')
    p.add_argument('--command-velocity', type=float, default=.0015)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--reset-unloaded', action='store_true')
    args = p.parse_args()
    if args.execute and not args.reset_unloaded: p.error('Explicit --reset-unloaded required for this unloaded commissioning sequence')
    root = args.output.resolve(); root.mkdir(parents=True, exist_ok=False)
    problem = checked_problem(root/'model', args.evidence, args.inventory, command_velocity=args.command_velocity)
    evidence = problem.pregrasp_evidence; path = evidence['path']; expected = dict(evidence['saved_start'])
    if path['kind'] != 'serial_direct' or len(path['waypoints']) != 3:
        raise ValueError('Expected the checked RF-then-RR serial path')
    # Only a high pregrasp, not contact insertion, is permitted by this runner.
    for goal in evidence['goals'].values():
        pre = np.asarray(goal['tool0_pregrasp']); entry = np.asarray(goal['theoretical_tool0_entry'])
        if not np.allclose(pre[:3, :3], entry[:3, :3]) or not np.allclose((pre-entry)[:2, 3], 0) or pre[2, 3]-entry[2, 3] < .149:
            raise ValueError('First unloaded physical approach requires >=150mm vertical pregrasp')
    report = dict(success=False, phase='OFFLINE_CHECK', arm_commands=[], finger_commands=[],
                  loaded_motion=False, command_velocity_rad_s=args.command_velocity,
                  monitored_velocity_rad_s=problem.cfg['velocity_limit_rad_s'], segments=[],
                  base_guard_signature=problem.signature, supplemental_object_signature=problem.supplemental_signature)
    record = root/'result.json'
    def save():dump(record, report)
    save()
    for index, arm in enumerate(['right_front','right_rear']):
        end = dict(zip(path['joint_names'], path['waypoints'][index+1]))
        if any(abs(end[j]-expected[j])>1e-8 for r in ROBOT_IDS if r!=arm for j in joint_names(r) if j in end):
            raise ValueError('Serial path changes a second arm')
        request = problem.normalize(dict(start=expected, goals={arm:[end[j] for j in joint_names(arm)]}))
        initial = [expected[j] for j in joint_names(arm)]
        if not problem.edge(request, initial, request['target']): raise ValueError('Fresh full-cell path verification failed')
        report['segments'].append(dict(arm=arm, request=request, geometric_path=[initial, request['target']], executed=False))
        expected.update(zip(joint_names(arm), request['target']))
    if not args.execute:
        report.update(success=True, phase='OFFLINE_CHECKED_NOT_EXECUTED'); save(); return 0
    require_domain('hardware')
    with motion_context():
        for index, segment in enumerate(report['segments']):
            arm = segment['arm']; client = HardwareClient(problem, 'hardware', [arm])
            try:
                report['phase'] = 'UNLOADED_CHECK_'+arm; save(); client.connect()
                for r in ROBOT_IDS:
                    with GripperClient(r) as gripper: status = gripper.status()
                    segment.setdefault('grippers_before', {})[r] = status
                    regs = status['registers']
                    if status.get('busy') is not False or not (regs['ACT']==1 and regs['STA']==3 and regs['FLT']==0 and regs['OBJ']==3 and regs['PRE']==0 and regs['POS']<=8):
                        raise ValueError(r+': not confirmed open/unloaded; no reset or goal sent')
                client.health()
                if any(abs(client.positions[j]-segment['request']['start'][j])>.0005 for n in problem.names.values() for j in n):
                    raise ValueError('Actual start changed; replan, no automatic reposition')
                if not client.guard.get('standstill_confirmed') or client.guard.get('faults'):
                    raise ValueError('Stationary clear guard required before explicit unloaded reset')
                # Preserve all old causes in the report; reset is a separate
                # explicit operation, never failure recovery or loaded resume.
                segment['guard_before_reset'] = client.guard; segment['supervisor_before_reset'] = client.supervisor; save()
                answer = client.service(Trigger, '/uwa_cell/collision_supervisor/reset', Trigger.Request())
                segment['reset_response'] = dict(success=answer.success, message=answer.message); save()
                if not answer.success: raise RuntimeError(answer.message)
                client.wait(lambda:not client.guard['blocked_arms'] and not client.supervisor['blocked_arms'], timeout=3., health=True)
                others = set(ROBOT_IDS)-{arm}
                segment['other_arm_holds'] = client.stop(others); save()
                if not all(segment['other_arm_holds'][key] for key in ('resource_holds_confirmed','latches_confirmed')):
                    raise RuntimeError('Other arm holds unconfirmed')
                client.health(); baseline = dict(client.positions)
                request = problem.normalize(dict(start=baseline, goals=segment['request']['goals']))
                # Revalidate the measured tiny start correction at unchanged
                # monitored reserves; timing uses the smaller command bound.
                trajectory = problem.time_parameterize(request, [[baseline[j] for j in joint_names(arm)], request['target']])
                plan = dict(request=request, trajectory=trajectory)
                execution = dict(stage='UNLOADED_PREGRASP_'+arm, record_path=str(root/(arm+'-execution.json')),
                                 phase_count=0, guard_stops=0)
                segment['nominal_duration_s'] = trajectory['duration_s']; report['phase'] = 'APPROACH_'+arm; save()
                report['arm_commands'].append(dict(arm=arm, goal=request['goals'][arm], requested_monotonic_s=time.monotonic())); save()
                follow(problem, client, plan, execution)
                segment['execution'] = execution
                if execution.get('stopped_arms'): raise RuntimeError(arm+': interlock stopped approach')
                segment['hold_after'] = client.stop([arm])
                segment['final_positions'] = dict(client.positions)
                segment['executed'] = True; dump(root/(arm+'-execution.json'), execution); save()
            except BaseException as error:
                report['error'] = str(error); report['phase'] = 'STOPPED_'+arm
                if client.owned: report['stop_result'] = client.stop(client.owned)
                save(); return 1
            finally:client.destroy_node()
        report.update(success=True, phase='AT_HIGH_PREGRASP_HELD_NO_CONTACT'); save()
    return 0


if __name__ == '__main__':raise SystemExit(main())

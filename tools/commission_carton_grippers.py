#!/usr/bin/env python3
"""Commission right ROS grippers at the saved unloaded arm posture.

Read-only by default. --execute-empty-stroke explicitly requests one partial
empty closing stroke (raw128) and a separate opening goal (raw0) per arm.
There are no arm, activation, power, controller or automatic recovery commands.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

import numpy as np
import rclpy
from rclpy.action import ActionClient
from std_srvs.srv import Trigger
from uwa_cell_gripper_interfaces.action import RobotiqCommand

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'uwa_cell_tasks'))
from uwa_cell_tasks.hardware_preparation import arm_observation, require_observation_domain
from uwa_cell_tasks.hardware_object_reference import MEMBERS
from match_ur_hardware.profiles import load_profiles


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True, help='Saved stationary native observations at unloaded handoff posture')
    p.add_argument('--inventory', type=Path, default=REPO/'config/hardware_inventory.yaml')
    p.add_argument('--execute-empty-stroke', action='store_true')
    args = p.parse_args(); require_observation_domain()
    args.output.mkdir(parents=True, exist_ok=False)
    reference = json.loads(args.reference.read_text()); profiles = load_profiles(args.inventory)
    report = dict(passed=False, mode='EMPTY_PARTIAL_STROKE' if args.execute_empty_stroke else 'READ_ONLY',
                  arm_commands=[], activation_commands=[], gripper_goals=[],
                  references_are_aperture_or_force_calibration=False)
    clients = []
    rclpy.init(); node = rclpy.create_node('uwa_carton_gripper_commissioning')
    def save():
        (args.output/'result.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    def wait(future, timeout):
        deadline = time.monotonic()+timeout
        while not future.done():
            rclpy.spin_once(node, timeout_sec=.03)
            if time.monotonic() >= deadline: raise TimeoutError('ROS outcome uncertain; no retry/open')
        result = future.result()
        if result is None: raise RuntimeError('Empty ROS response')
        return result
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {arm:pool.submit(arm_observation, profiles[arm]['ip']) for arm in MEMBERS}
            native = {arm:f.result() for arm,f in futures.items()}
        report['native_before'] = native; save()
        for arm, obs in native.items():
            old = reference['arms'][arm]['samples'][-1]
            if not obs['stationary_observed']:
                raise ValueError(arm+': arm is not observed stationary')
            for sample in obs['samples']:
                if (sample['robot_mode'] != 7 or sample['safety_mode'] != 1 or sample['runtime_state'] != 2 or
                    np.max(abs(np.array(sample['actual_q'])-old['actual_q'])) > .001):
                    raise ValueError(arm+': no longer at the saved unloaded handoff posture')
        adapters = {}
        for arm in MEMBERS:
            ns = '/uwa_hardware/'+arm+'/gripper'
            read = node.create_client(Trigger, ns+'/read')
            describe = node.create_client(Trigger, ns+'/capabilities')
            action = ActionClient(node, RobotiqCommand, ns+'/command'); clients.append(action)
            if not read.wait_for_service(timeout_sec=10.) or not describe.wait_for_service(timeout_sec=10.) or not action.wait_for_server(timeout_sec=10.):
                raise TimeoutError(arm+': shared ROS gripper interface unavailable')
            reply = wait(describe.call_async(Trigger.Request()), 5.)
            if not reply.success: raise RuntimeError(reply.message)
            info = json.loads(reply.message)
            report.setdefault('capabilities', {})[arm] = info; save()
            if args.execute_empty_stroke and not (info['actuation_enabled'] is True and info['max_force_raw']==0 and info['max_speed_raw']>=16):
                raise ValueError(arm+': explicit shared service command mode with force cap0 required')
            reply = wait(read.call_async(Trigger.Request()), 5.)
            if not reply.success: raise RuntimeError(reply.message)
            state = json.loads(reply.message); adapters[arm] = action
            report.setdefault('initial_grippers', {})[arm] = state; save()
            r = state['registers']
            if state.get('busy') is not False or not (r['ACT']==1 and r['STA']==3 and r['FLT']==0 and r['PRE']==0 and r['OBJ']==3 and r['POS']<=8):
                raise ValueError(arm+': expected already-activated open empty gripper; no reset/activation attempted')
        if args.execute_empty_stroke:
            for arm in MEMBERS:
                for position in (128, 0):
                    goal = RobotiqCommand.Goal(operation=1, position_raw=position, speed_raw=16, force_raw=0, timeout_s=20.)
                    record = dict(arm=arm, position_raw=position, speed_raw=16, force_raw=0,
                                  requested_monotonic_s=time.monotonic(), outcome_confirmed=False)
                    report['gripper_goals'].append(record); save()
                    handle = wait(adapters[arm].send_goal_async(goal), 5.)
                    record['accepted'] = handle.accepted; save()
                    if not handle.accepted: raise RuntimeError(arm+': explicit goal rejected')
                    wrapped = wait(handle.get_result_async(), 24.); result = wrapped.result
                    record.update(ros_status=wrapped.status, success=result.success, message=result.message,
                                  status=json.loads(result.status_json) if result.status_json else {})
                    save()
                    if not result.success or wrapped.status != 4: raise RuntimeError(arm+': goal failed; target retained')
                    r = record['status']['registers']
                    if r['OBJ'] != 3 or abs(r['POS']-position)>8 or r['PRE'] != position:
                        raise RuntimeError(arm+': unexpected contact/endpoint; no automatic opening or recovery')
                    record['outcome_confirmed'] = True; save()
        report.update(passed=True, interpretation='ROS command/status and unloaded partial travel only; no N/mm mapping, grasp or loaded stop proof')
    except Exception as error:
        report['error'] = str(error)
    finally:
        # Existing shared adapters/services remain running. Client cleanup never
        # releases a target or changes another process's command mode.
        for client in clients: client.destroy()
        node.destroy_node(); rclpy.shutdown(); save()
    print(json.dumps(dict(passed=report['passed'], mode=report['mode'],
                         gripper_goals=len(report['gripper_goals']), error=report.get('error'),
                         report=str(args.output/'result.json')), indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

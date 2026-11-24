#!/usr/bin/env python3
"""Prepare/review a geometric withdrawal, or execute its exact approved file.

Preparation consumes a saved complete start and explicit six-joint targets.
It cannot solve an actual mesh penetration or disable collision protection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

import numpy as np
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters
from std_srvs.srv import Trigger

from uwa_cell_motion.common import PAIRS, ROBOT_IDS, config, dump
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_model import HardwareProblem, inventory_path
from uwa_cell_motion.minimal_execution import MinimalHardwareClient, ROOT, split_trajectory


def digest(value):
    body = {key:item for key,item in value.items() if key != 'reviewed_sha256'}
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class WithdrawalProblem(HardwareProblem):
    def check(self, request, q, *, margin=True):
        state = self.state(request,q)
        if not self.collision.check(state)[0]:
            return False
        world = self.spheres.world(state)
        for pair in PAIRS:
            gap = self.spheres.nearest(world,*pair)['clearance_m']
            threshold = self.withdrawal_baselines.get(pair,.04)
            if gap < threshold-1e-9 or (pair not in self.withdrawal_baselines and gap <= .04):
                return False
        return True


def prepare(args):
    request = json.loads(args.request.read_text())
    with tempfile.TemporaryDirectory(prefix='uwa-withdrawal-') as directory:
        problem = WithdrawalProblem(directory,config(args.config),args.inventory,args.layout)
        start = request['start']
        if not problem.collision.check(start)[0]:
            raise ValueError('Actual model contact or invalid start; automatic withdrawal unavailable')
        world = problem.spheres.world(start)
        problem.withdrawal_baselines = {pair:problem.spheres.nearest(world,*pair)['clearance_m']
            for pair in PAIRS if problem.spheres.nearest(world,*pair)['clearance_m'] <= .04}
        if not problem.withdrawal_baselines:
            raise ValueError('No neighbor-margin violation; use an ordinary checked plan')
        normalized = problem.normalize(request)
        q0 = [start[j] for j in normalized['joint_names']]
        waypoints = request.get('waypoints',[q0,normalized['target']])
        trajectory = problem.time_parameterize(normalized,waypoints)
        previous = dict(problem.withdrawal_baselines)
        states = []
        for point in trajectory['points']:
            state = problem.state(normalized,point['positions'])
            world = problem.spheres.world(state)
            for pair in previous:
                gap = problem.spheres.nearest(world,*pair)['clearance_m']
                if gap < previous[pair]-1e-9:
                    raise ValueError('Withdrawal further approaches '+ '/'.join(pair))
                previous[pair] = gap
            states.append(state)
        if any(gap <= .04 for gap in previous.values()):
            raise ValueError('Withdrawal does not leave every violated 40 mm neighbor margin')
        result = dict(schema_version=1,kind='checked_neighbor_withdrawal',mode=args.mode,
                      model_signature=problem.signature,inventory=str(args.inventory.resolve()),
                      layout=str(args.layout.resolve()) if args.layout else None,
                      config=problem.cfg,start_tolerance_rad=.002,
                      states=states,trajectory=trajectory,
                      trajectories=split_trajectory(trajectory,normalized['selected']),
                      request=normalized,check_step_rad=problem.cfg['joint_check_step_rad'],
                      policy='FCL contact free; existing violated neighbor margins only improve')
        result['reviewed_sha256'] = digest(result)
        dump(args.output,result)
        print(json.dumps(dict(prepared=True,output=str(args.output.resolve()),
                              reviewed_sha256=result['reviewed_sha256'],commands_sent=[])))


def execute(args):
    plan = json.loads(args.plan.read_text())
    if (plan.get('kind') != 'checked_neighbor_withdrawal' or
            digest(plan) != plan.get('reviewed_sha256') or
            args.reviewed_sha256 != plan['reviewed_sha256']):
        raise ValueError('Exact reviewed withdrawal digest required')
    result = dict(success=False,protection_backend='minimal',reviewed_sha256=args.reviewed_sha256,
                  phase='ADMIT_CHECKED_WITHDRAWAL')
    with motion_context(), tempfile.TemporaryDirectory(prefix='uwa-withdrawal-execution-') as directory:
        problem = HardwareProblem(directory,plan['config'],plan['inventory'],plan.get('layout'))
        if problem.signature != plan['model_signature']:
            raise ValueError('Withdrawal model changed; prepare again')
        arms = list(plan['trajectories'])
        client = MinimalHardwareClient(problem,plan['mode'],arms)
        try:
            client.connect()
            parameter = Parameter(name='recovery_plan_path',value=ParameterValue(
                type=ParameterType.PARAMETER_STRING,string_value=str(args.plan.resolve())))
            changed = client.service(SetParameters,ROOT+'/set_parameters',SetParameters.Request(parameters=[parameter]))
            if not all(value.successful for value in changed.results):
                raise RuntimeError('Withdrawal file parameter rejected')
            admitted = client.service(Trigger,ROOT+'/begin_recovery',Trigger.Request())
            if not admitted.success:
                raise RuntimeError(admitted.message)
            # Match controllers' new authorization generation before sending
            # replacement goals. This is a one-shot response, no watchdog.
            status = json.loads(admitted.message)
            generation = status['generation']
            client.wait(lambda:all((client.protection_status or {}).get('arms',{}).get(arm,{}).get(
                'generation') == generation for arm in arms),timeout=3.)
            client.follow_group(plan['trajectories'],duration_s=plan['trajectory']['duration_s'],
                                recovery=True,recovery_sha256=args.reviewed_sha256)
            result.update(success=True,phase='WITHDRAWAL_COMPLETE',final_positions=client.positions)
        except KeyboardInterrupt:
            result['stop_result'] = client.stop()
        except Exception as error:
            result['error'] = str(error)
        finally:
            result['protection_status'] = client.protection_status
            dump(args.output,result)
            client.destroy_node()
    return 0 if result['success'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation',required=True)
    preparation = commands.add_parser('prepare')
    preparation.add_argument('--request',type=Path,required=True)
    preparation.add_argument('--inventory',type=Path,default=inventory_path())
    preparation.add_argument('--config',type=Path,default=Path(__file__).resolve().parents[1]/
                             'uwa_cell_motion/config/hardware_carton_supported_trend.yaml')
    preparation.add_argument('--layout',type=Path)
    preparation.add_argument('--mode',choices=('mock','hardware'),default='mock')
    execution = commands.add_parser('execute')
    execution.add_argument('--plan',type=Path,required=True)
    execution.add_argument('--reviewed-sha256',required=True)
    for command in (preparation,execution):
        command.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    return prepare(args) if args.operation == 'prepare' else execute(args)


if __name__ == '__main__':
    raise SystemExit(main())

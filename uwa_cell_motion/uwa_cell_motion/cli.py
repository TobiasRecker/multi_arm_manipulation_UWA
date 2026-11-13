"""Explicit plan / preview / execute, never implicit hardware actions."""
import argparse
import json
from pathlib import Path
import tempfile

from .common import config, dump, simulation_only


def main():
    parser=argparse.ArgumentParser(description='UWA simulation collision guard and PTP comparison')
    sub=parser.add_subparsers(dest='op',required=True)
    for name in ('guard','supervisor'):
        p=sub.add_parser(name);p.add_argument('--layout');p.add_argument('--config')
    p=sub.add_parser('snapshot');p.add_argument('--output',required=True)
    p=sub.add_parser('reset')
    p=sub.add_parser('stop')
    p=sub.add_parser('coverage');p.add_argument('--layout');p.add_argument('--config');p.add_argument('--output',required=True)
    p=sub.add_parser('plan');p.add_argument('request');p.add_argument('--method',choices=['rrtconnect','circular'],required=True)
    p.add_argument('--seed',type=int,default=0);p.add_argument('--layout');p.add_argument('--config');p.add_argument('--output',required=True)
    p=sub.add_parser('preview');p.add_argument('plan');p.add_argument('--output',required=True)
    p=sub.add_parser('execute');p.add_argument('plan');p.add_argument('--output',required=True)
    p=sub.add_parser('scenarios');p.add_argument('--layout');p.add_argument('--config');p.add_argument('--output',required=True)
    p=sub.add_parser('benchmark');p.add_argument('suite');p.add_argument('--layout');p.add_argument('--config')
    p.add_argument('--output',required=True);p.add_argument('--limit',type=int);p.add_argument('--seeds',type=int,default=5)
    p.add_argument('--execute',action='store_true',help='Execute successful plans in Gazebo; requires armed guard')
    p=sub.add_parser('replay-comparison');p.add_argument('directory');p.add_argument('--limit',type=int)
    p=sub.add_parser('report');p.add_argument('directory');p.add_argument('--output',required=True);p.add_argument('--guard-check')
    args,ros_args=parser.parse_known_args()
    if ros_args and ros_args[0]!='--ros-args':parser.error('Unrecognized arguments: '+' '.join(ros_args))
    cfg=config(getattr(args,'config',None))
    if args.op in ('guard','supervisor'):
        if args.op=='guard':from .guard_node import run
        else:from .supervisor import run
        run(cfg,args.layout);return
    if args.op in ('snapshot','reset','stop','execute'):
        from .execution import snapshot,reset,stop_all,execute
        simulation_only()
        if args.op=='snapshot':dump(args.output,snapshot());return
        if args.op=='reset':print(reset());return
        if args.op=='stop':print(stop_all());return
        result=execute(json.loads(Path(args.plan).read_text()),args.output);print(json.dumps(result))
        if not result['success']:raise SystemExit(1)
        return
    if args.op=='preview':
        from .preview import render
        render(json.loads(Path(args.plan).read_text()),args.output);print(args.output);return
    if args.op=='replay-comparison':
        from .benchmark import replay_comparison
        simulation_only();replay_comparison(args.directory,args.limit);return
    if args.op=='report':
        from .report import render
        render(args.directory,args.output,args.guard_check);return
    from .planning import Problem
    with tempfile.TemporaryDirectory(prefix='uwa-motion-') as directory:
        problem=Problem(directory,cfg,getattr(args,'layout',None))
        if args.op=='coverage':
            dump(args.output,dict(bodies=problem.spheres.coverage,mesh_sha256=problem.spheres.geometry.assets,
                                 model_signature=problem.signature,assumption='nominal collision shapes, not measured physical accuracy'))
        elif args.op=='plan':
            result=problem.plan(json.loads(Path(args.request).read_text()),args.method,args.seed)
            dump(args.output,result);print(json.dumps(dict(success=result['success'],error=result.get('error'),planning_time_s=result['planning_time_s'])))
            if not result['success']:raise SystemExit(1)
        elif args.op=='scenarios':
            from .benchmark import generate_suite
            dump(args.output,generate_suite(problem))
        elif args.op=='benchmark':
            from .benchmark import benchmark
            benchmark(problem,json.loads(Path(args.suite).read_text()),args.output,args.limit,args.seeds,args.execute)

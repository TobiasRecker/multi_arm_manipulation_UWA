"""Composable manipulation skills. All motion adapters are simulation-only."""
import argparse
import json
import os
from pathlib import Path
import sys
from .core import configuration,skills,RunStore,write_json,verify


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('skills')
    for command in ('prepare','plan'):
        p=sub.add_parser(command);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path);p.add_argument('--layout',type=Path)
        if command=='plan':p.add_argument('--scene',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--observation',type=Path,required=True)
    for command in ('status','stop','preview'):
        p=sub.add_parser(command);p.add_argument('run',type=Path)
    p=sub.add_parser('review');p.add_argument('run',type=Path);p.add_argument('--sha256',required=True)
    p.add_argument('--decision',choices=['continue','observe','replan','abort'],required=True);p.add_argument('--reason',required=True)
    p=sub.add_parser('run');p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--namespace',default='/uwa_grasp_validation');p.add_argument('--layout',type=Path)
    p.add_argument('--reference',type=Path,required=True)
    p=sub.add_parser('bridge');p.add_argument('--namespace',required=True);p.add_argument('--world',required=True)
    p=sub.add_parser('guard');p.add_argument('--scene',type=Path,required=True);p.add_argument('--layout',type=Path,required=True)
    p=sub.add_parser('supervisor');p.add_argument('--layout',type=Path,required=True)
    args,ros_args=parser.parse_known_args()
    if args.command=='skills':print(json.dumps(skills(),indent=2));return
    if args.command in ('prepare','plan'):
        from uwa_cell_description.configuration import load_layout
        from .scene import prepare_scene
        if args.command=='prepare':
            result=prepare_scene(load_layout(args.layout),configuration(args.config),args.output)
        else:
            from .planning import TaskProblem,grasp_candidates,plan_approach
            scene=verify(json.loads((args.scene/'scene.json').read_text()))
            observation=verify(json.loads(args.observation.read_text()))
            if observation['status']!='VALID' or observation.get('source')!='image_only_tracking':raise ValueError('A valid image-only observation is required')
            description=(args.scene/'robot.urdf').read_text();obj=observation['T_world_object']
            problem=TaskProblem(args.output/'model',description,load_layout(args.layout),scene,obj)
            candidates=grasp_candidates(description,scene,scene['cfg'],obj)
            start=json.loads(args.snapshot.read_text())['positions'];failures=[];result=None
            for candidate in candidates:
                try:result=plan_approach(problem,start,candidate);break
                except ValueError as error:failures.append(str(error))
            if result is None:raise ValueError('No feasible grasp: '+str(failures))
            write_json(args.output/'plan.json',result)
        print(json.dumps(dict(output=str(args.output.resolve()),sha256=result['sha256'])));return
    if args.command in ('status','preview'):
        store=RunStore(args.run)
        if args.command=='status':print(json.dumps(store.state,indent=2));return
        from .preview import preview
        print(preview(args.run));return
    if args.command=='review':
        RunStore(args.run).submit_review(args.sha256,args.decision,args.reason);print('REVIEW RECEIVED');return
    if args.command=='stop':
        # Runner observes this and latches holds. An unavailable runner is
        # independently stopped by its heartbeat watchdog.
        args.run.mkdir(parents=True,exist_ok=True);(args.run/'STOP').write_text('STOP REQUESTED\n')
        print('STOP REQUESTED; inspect status for confirmed standstill');return
    from uwa_cell_motion.common import simulation_only
    simulation_only()
    import rclpy
    from uwa_cell_description.configuration import default_layout_path
    layout=str(getattr(args,'layout',None) or default_layout_path())
    rclpy.init(args=ros_args)
    node=None
    try:
        if args.command=='run':
            from .runtime import run_task
            print(json.dumps(run_task(args.output,args.scene,layout,args.namespace,args.reference),indent=2,default=lambda v:v.tolist()))
        elif args.command=='bridge':
            from .bridge import TelemetryBridge
            node=TelemetryBridge(args.namespace,args.world);rclpy.spin(node)
        elif args.command=='guard':
            from .guard import TaskGuard
            node=TaskGuard(args.scene,layout);rclpy.spin(node)
        elif args.command=='supervisor':
            from uwa_cell_motion.supervisor import Supervisor
            from uwa_cell_motion.common import config
            from rclpy.executors import MultiThreadedExecutor
            node=Supervisor(config(),layout,prepare=False)
            executor=MultiThreadedExecutor(num_threads=4);executor.add_node(node)
            try:executor.spin()
            finally:executor.shutdown()
    except KeyboardInterrupt:pass
    finally:
        if node:
            if hasattr(node,'close'):node.close()
            node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()

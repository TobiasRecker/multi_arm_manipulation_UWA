"""Explicit hardware backend; monitor by default, motion only through execute."""
import argparse
import json
from pathlib import Path
import tempfile
import time
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
from std_srvs.srv import Trigger
from match_ur_hardware.profiles import load_profiles
from .common import config,dump,ROBOT_IDS
from .hardware_model import HardwareProblem,inventory_path
from .hardware_state import require_domain
from .hardware_state import dashboard_stop
from .hardware_ports import provision,StopPort
from .node import MotionNode
from .execution import motion_context
from .hardware_execution import HardwareClient


def stop_all(cfg,inventory,mode):
    require_domain(mode);native=native_stop_all(inventory,mode)
    profiles=load_profiles(inventory)
    with motion_context():
        node=MotionNode('hardware_collision_stop',namespace='/uwa_cell');executor=SingleThreadedExecutor();executor.add_node(node)
        state={};history={r:[] for r in profiles}
        def receive(msg):
            try:
                value=json.loads(msg.data);now=time.monotonic()
                if set(value['records'])!=set(profiles):return
                for rid,record in value['records'].items():
                    if max(now-record['received'],now-record['source_stamp'])>cfg['state_timeout_s']:return
                    history[rid].append((now,np.asarray(record['q']),np.asarray(record['v'])))
                state.update(value);state['received']=now
            except (ValueError,KeyError,TypeError):pass
        node.create_subscription(String,'/uwa_cell/hardware_state',receive,1)
        ports={r:StopPort(node,p,cfg,mode) for r,p in profiles.items()}
        clients=[node.create_client(Trigger,'/uwa_cell/collision_supervisor/'+r+'/stop') for r in profiles]
        sent=set();end=time.monotonic()+5.;result={}
        try:
            while time.monotonic()<end:
                executor.spin_once(timeout_sec=.01)
                for index,client in enumerate(clients):
                    if index not in sent and client.service_is_ready():client.call_async(Trigger.Request());sent.add(index)
                status={r:p.tick(True,True) for r,p in ports.items()};now=time.monotonic();quiet=True
                for rid,rows in history.items():
                    rows=[r for r in rows if r[0]>=now-cfg['standstill_window_s']-.05];history[rid]=rows
                    if len(rows)<3 or rows[-1][0]-rows[0][0]<cfg['standstill_window_s']*.8:quiet=False;continue
                    if np.max(abs(np.asarray([r[2] for r in rows])))>cfg['standstill_velocity_rad_s'] or np.max(np.ptp([r[1] for r in rows],axis=0))>cfg['standstill_velocity_rad_s']*cfg['standstill_window_s']:quiet=False
                result=dict(native_stop=native,resource_holds_confirmed=all(p['held'] for p in status.values()),
                    standstill_confirmed=quiet and now-state.get('received',-float('inf'))<cfg['state_timeout_s'],ports=status)
                if result['resource_holds_confirmed'] and result['standstill_confirmed']:return dict(success=True,**result)
            return dict(success=False,error='STOP UNCONFIRMED; requests retained, no automatic resume',**result)
        finally:executor.shutdown();node.destroy_node()


def native_stop_all(inventory,mode):
    from .native_stop import stop_all
    return stop_all(inventory,mode)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['mock','hardware'],default='mock')
    parser.add_argument('--inventory',type=Path);parser.add_argument('--layout');parser.add_argument('--config')
    commands=parser.add_subparsers(dest='op',required=True)
    for role in ('guard','supervisor','watchdog'):commands.add_parser(role).add_argument('--armed',action='store_true')
    commands.add_parser('provision');commands.add_parser('reset');commands.add_parser('stop')
    commands.add_parser('native-stop')
    p=commands.add_parser('snapshot');p.add_argument('--output',required=True)
    p=commands.add_parser('plan');p.add_argument('request');p.add_argument('--method',choices=['rrtconnect','circular'],required=True);p.add_argument('--seed',type=int,default=0);p.add_argument('--output',required=True)
    p=commands.add_parser('execute');p.add_argument('plan');p.add_argument('--output',required=True)
    p=commands.add_parser('preview');p.add_argument('plan');p.add_argument('--output',required=True)
    p=commands.add_parser('check-model');p.add_argument('--output',required=True)
    args,ros=parser.parse_known_args(argv)
    if ros and ros[0]!='--ros-args':parser.error('Unrecognized arguments: '+' '.join(ros))
    if args.op=='preview':
        from .preview import render
        plan=json.loads(Path(args.plan).read_text())
        if not plan.get('hardware_plan') or plan.get('execution_mode')!=args.mode:raise ValueError('Preview requires a plan for the selected hardware/mock backend')
        render(plan,args.output);print(args.output);return
    from ament_index_python.packages import get_package_share_directory
    cfg=config(args.config or Path(get_package_share_directory('uwa_cell_motion'))/'config/hardware_motion.yaml')
    inventory=args.inventory or inventory_path()
    if args.op=='native-stop':
        result=native_stop_all(inventory,args.mode);print(json.dumps(dict(native_stop=result,standstill_confirmed=False)))
        if args.mode=='hardware' and not all(v['acknowledged'] for v in result.values()):raise SystemExit(1)
        return
    if args.op in ('guard','supervisor','watchdog'):
        from .hardware_nodes import run
        return run(args.op,cfg,inventory,args.layout,args.mode,args.armed)
    if args.op=='provision':
        require_domain(args.mode)
        with motion_context():
            node=MotionNode('hardware_hold_provision')
            try:provision(node,load_profiles(inventory),cfg,args.mode)
            finally:node.destroy_node()
        print('Inactive six-joint holds provisioned; no arm/program activated');return
    if args.op=='stop':
        result=stop_all(cfg,inventory,args.mode);print(json.dumps(result))
        if not result['success']:raise SystemExit(1)
        return
    if args.op=='execute':
        from .hardware_execution import execute
        plan=json.loads(Path(args.plan).read_text())
        if args.inventory and args.inventory.resolve()!=Path(plan['inventory']).resolve():raise ValueError('CLI inventory differs from plan')
        if args.config and cfg!=plan['config']:raise ValueError('CLI operating bounds differ from plan')
        result=execute(plan,args.output,args.mode);print(json.dumps(result))
        if not result['success']:raise SystemExit(1)
        return
    with tempfile.TemporaryDirectory(prefix='uwa-hardware-cli-') as directory:
        problem=HardwareProblem(directory,cfg,inventory,args.layout)
        if args.op in ('snapshot','reset'):
            require_domain(args.mode)
            with motion_context():
                client=HardwareClient(problem,args.mode)
                try:
                    client.connect(guard=args.op=='snapshot')
                    if args.op=='reset':
                        answer=client.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request())
                        if not answer.success:raise RuntimeError(answer.message)
                        print(answer.message)
                    else:
                        client.health();dump(args.output,dict(schema_version=1,start=client.positions,goals={},hardware_binding=problem.binding,
                            source='output-only RTDE actual joints' if args.mode=='hardware' else 'MOCK states',source_records=client.records,
                            tool_policy='unobserved fingers: full opening envelope; zero is a model coordinate',execution_mode=args.mode))
                finally:client.destroy_node()
        elif args.op=='plan':
            request=json.loads(Path(args.request).read_text())
            if request.get('execution_mode',args.mode)!=args.mode or request.get('hardware_binding',problem.binding)!=problem.binding:raise ValueError('Request backend/model binding differs')
            result=problem.plan(request,args.method,args.seed);result['execution_mode']=args.mode;dump(args.output,result)
            print(json.dumps(dict(success=result['success'],error=result.get('error'),planning_time_s=result['planning_time_s'])))
            if not result['success']:raise SystemExit(1)
        elif args.op=='check-model':
            dump(args.output,dict(model_signature=problem.signature,hardware_binding=problem.binding,mesh_sha256=problem.spheres.geometry.assets,
                envelope=problem.envelope_audit,tool_internal_pairs='Coupled gripper opening hulls excluded internally only; external pairs retained',
                stop_budget_qualification='ENGINEERING ASSUMPTIONS - NOT MEASURED',inventory=str(inventory)))

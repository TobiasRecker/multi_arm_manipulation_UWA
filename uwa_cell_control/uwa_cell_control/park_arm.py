"""Plan, review or execute one explicit parking path. No implicit UR startup."""
import argparse
from datetime import datetime, timezone
import json
import os
import signal
from pathlib import Path
import tempfile
import time

import numpy as np

from match_ur_hardware.profiles import load_profiles
from uwa_cell_gazebo.configuration import ROBOT_IDS, load_layout, joint_names, default_layout_path
from .parking import (complete_state, digest, make_model, manual_states, plan_parking,
                      save_plan, validate_artifact)


class JointObserver:
    def __init__(self,node,profiles,ids,mode):
        from sensor_msgs.msg import JointState
        from std_msgs.msg import Bool
        from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
        from rclpy.qos import qos_profile_sensor_data
        self.node,self.profiles,self.mode=node,profiles,mode
        self.received={};self.program_running={};self.subscriptions=[]
        for rid in ids:
            self.subscriptions.append(node.create_subscription(JointState,
                profiles[rid]['namespace']+'/joint_states',
                lambda msg,rid=rid:self.receive(rid,msg),qos_profile_sensor_data))
            if mode=='hardware':
                qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
                self.subscriptions.append(node.create_subscription(Bool,
                    profiles[rid]['namespace']+'/io_and_status_controller/robot_program_running',
                    lambda msg,rid=rid:self.program_running.update({rid:msg.data}),qos))

    def receive(self,rid,msg):
        names=self.profiles[rid]['joint_names']
        if len(msg.name)!=len(msg.position) or len(set(msg.name))!=len(msg.name):return
        values=dict(zip(msg.name,msg.position))
        if not set(names)<=set(values):return
        q=np.array([values[j] for j in names])
        if not np.isfinite(q).all():return
        self.received[rid]={'positions':q.tolist(),'source':'mock_joint_states' if self.mode=='mock' else 'live_joint_states',
                            'received_monotonic':time.monotonic(),
                            'recorded_at':datetime.now(timezone.utc).isoformat()}

    def sample(self,timeout=4.):
        import rclpy
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            rclpy.spin_once(self.node,timeout_sec=.05)
        return {r:dict(record) for r,record in self.received.items()
                if time.monotonic()-record['received_monotonic']<.5}

    def guard(self,plan,*,require_program_link=False):
        moving=plan['arm'];now=time.monotonic()
        if require_program_link and self.mode=='hardware' and self.program_running.get(moving) is not True:
            raise RuntimeError(moving+': native External Control link not confirmed; no calibration trajectory')
        for rid in self.profiles:
            if plan['state_sources'][rid] in ('manual_pendant','user_nominal_home'):continue
            record=self.received.get(rid)
            if not record or now-record['received_monotonic']>.5:
                raise RuntimeError(rid+': joint telemetry stale or unavailable')
            if rid!=moving:
                expected=[plan['start'][j] for j in joint_names(rid)]
                if max(abs(np.array(record['positions'])-expected))>.015:
                    raise RuntimeError(rid+': stationary-arm pose changed; cancel parking')

    def close(self):
        for sub in self.subscriptions:self.node.destroy_subscription(sub)


def node_for(mode):
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    os.environ['ROS_DOMAIN_ID']='67' if mode=='mock' else '66'
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    # Keep the context alive while Python unwinds Ctrl+C into trajectory cleanup.
    # rclpy's default SIGINT handler shuts the context down before cancel/switch.
    rclpy.init(args=[],signal_handler_options=SignalHandlerOptions.NO)
    def interrupt_once(signum,frame):
        # A terminal Ctrl+C also reaches ros2 run, which forwards SIGINT again.
        # Ignore repeats while the trajectory's finally block cancels/deactivates.
        signal.signal(signal.SIGINT,signal.SIG_IGN)
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT,interrupt_once)
    signal.signal(signal.SIGTERM,interrupt_once)
    return rclpy.create_node('uwa_parking_'+str(os.getpid()))


def plan(args):
    profiles=load_profiles(args.inventory);layout=load_layout(args.layout)
    readings=manual_states(args.manual_states)
    if args.snapshot:
        snapshot=json.loads(Path(args.snapshot).read_text())
        if snapshot.get('mode')!=args.mode:raise ValueError('Snapshot mode mismatch')
        readings.update(snapshot['arms'])
    else:
        import rclpy
        node=node_for(args.mode)
        observer=JointObserver(node,profiles,[r for r,p in profiles.items() if p['ip']],args.mode)
        try:readings.update(observer.sample())
        finally:observer.close();node.destroy_node();rclpy.shutdown()
    start,sources,missing=complete_state(layout,readings)
    directory=Path(args.output).expanduser().resolve();directory.mkdir(parents=True,exist_ok=True)
    (directory/'states.json').write_text(json.dumps({'mode':args.mode,'arms':readings},indent=2)+'\n')
    model,layout=make_model(layout,profiles,directory)
    target=[float(v) for v in args.target_deg.split(',')] if args.target_deg else None
    if target is not None:target=np.radians(target).tolist()
    path=plan_parking(model,layout,args.arm,start,target=target,
                      velocity=args.velocity,acceleration=args.acceleration)
    path['layout_file']=str(Path(args.layout).expanduser().resolve())
    artifact=save_plan(directory,path,model,layout,profiles,sources,missing,args.mode)
    print(json.dumps({'plan':str(directory/'plan.json'),'preview':str(directory/'preview.png'),
        'arm':args.arm,'mode':args.mode,'executable':artifact['executable'],
        'unobserved_arms':missing,'target_deg':np.degrees(artifact['target']).tolist(),
        'duration_s':artifact['duration'],'collision_samples':artifact['collision_samples']},indent=2))


def execute(args):
    import rclpy
    from match_ur_hardware.trajectory import execute_trajectory
    artifact=json.loads(Path(args.plan).read_text());profiles=load_profiles(args.inventory)
    validate_artifact(artifact,profiles)
    rid=artifact['arm'];profile=profiles[rid]
    if not profile['ip']:raise ValueError('No configured target arm IP')
    node=node_for(artifact['mode'])
    ids=[r for r,s in artifact['state_sources'].items() if s not in ('manual_pendant','user_nominal_home')]
    observer=JointObserver(node,profiles,ids,artifact['mode'])
    try:
        readings=observer.sample()
        # Original manually recorded arms remain explicit fixed obstacles.
        for r,s in artifact['state_sources'].items():
            if s in ('manual_pendant','user_nominal_home'):
                readings[r]={'positions':[artifact['start'][j] for j in joint_names(r)],'source':s}
        start,sources,missing=complete_state(artifact['layout'],readings)
        if missing:raise ValueError('Current joint states missing: '+', '.join(missing))
        for r in ROBOT_IDS:
            error=max(abs(start[j]-artifact['start'][j]) for j in joint_names(r))
            if error>.01:raise ValueError(f'{r}: start changed by {error:.4f} rad; generate a new plan')
        with tempfile.TemporaryDirectory(prefix='uwa-parking-recheck-') as directory:
            model,layout=make_model(load_layout(artifact['layout_file']),profiles,directory)
            if digest(layout)!=digest(artifact['layout']):raise ValueError('Cell layout changed; regenerate plan')
            for point in artifact['points']:
                state=dict(start,**dict(zip(artifact['joint_names'],point['positions'])))
                if not model.check(state)[0]:raise ValueError('Current full-cell path recheck failed')
        observer.sample(.3)
        latest=observer.received.get(rid)
        if not latest:raise ValueError('Target arm must have live telemetry, not a manual-only state')
        if max(abs(np.array(latest['positions'])-[artifact['start'][j] for j in joint_names(rid)]))>.01:
            raise ValueError('Target moved during path recheck; regenerate plan')
        observer.guard(artifact)
        if args.check_only:
            print(json.dumps({'success':True,'check_only':True,'arm':rid,
                              'mode':artifact['mode'],'fingerprint':artifact['fingerprint']}))
            return
        result=execute_trajectory(node,profile,artifact['points'],mock=artifact['mode']=='mock',
                                  guard=lambda:observer.guard(artifact))
        observer.sample(.4)
        error=max(abs(np.array(observer.received[rid]['positions'])-artifact['target']))
        result.update(arm=rid,mode=artifact['mode'],final_error_rad=float(error))
        if error>.03:
            from match_ur_hardware.operations import switch
            switch(node,profile)
            raise RuntimeError(f'Final position error {error:.4f} rad')
        print(json.dumps(result,indent=2))
    finally:observer.close();node.destroy_node();rclpy.shutdown()


def main():
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('plan',help='Read state and save a command-free checked plan')
    p.add_argument('--inventory',default=str(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'))
    p.add_argument('--layout',default=str(default_layout_path()))
    p.add_argument('--arm',choices=ROBOT_IDS,required=True);p.add_argument('--mode',choices=['mock','hardware'],default='mock')
    p.add_argument('--manual-states',help='JSON pendant angles with explicit unit deg/rad')
    p.add_argument('--snapshot',help='Offline full state JSON, including mode and per-arm provenance')
    p.add_argument('--target-deg',help='Optional explicit six comma-separated joint angles; otherwise outward IK')
    p.add_argument('--velocity',type=float,default=.05);p.add_argument('--acceleration',type=float,default=.10)
    p.add_argument('--output',default=str(ws/'setup/calibration/parking'/datetime.now().strftime('%Y%m%d_%H%M%S')))
    p=sub.add_parser('execute',help='Execute exactly one checked plan on its recorded mode/domain')
    p.add_argument('plan');p.add_argument('--inventory',default=str(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'))
    p.add_argument('--check-only',action='store_true',help='Recheck current state and full path without controller or action commands')
    p=sub.add_parser('preview',help='Animate a plan in isolated RViz domain68; no hardware clients')
    p.add_argument('plan')
    args=parser.parse_args()
    try:
        if args.command=='plan':plan(args)
        elif args.command=='execute':execute(args)
        else:
            from .parking_preview import preview
            preview(args.plan)
        return 0
    except KeyboardInterrupt:
        print('Parking interrupted; owned trajectory cancellation requested.');return 130
    except Exception as error:
        print(json.dumps({'success':False,'error':str(error)}));return 1


if __name__=='__main__':raise SystemExit(main())

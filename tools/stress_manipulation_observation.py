#!/usr/bin/env python3
"""Guarded simulation observation stress; no arm/gripper trajectory goals."""
import argparse
import json
from pathlib import Path
import signal
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from uwa_cell_motion.common import simulation_only
from uwa_cell_tasks.core import resource_lease,write_json
from uwa_cell_tasks.observation import observe
from uwa_cell_tasks.runtime import Simulation


def execute(args):
    args.output.mkdir(parents=True,exist_ok=False)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    def interrupted(signum,frame):raise KeyboardInterrupt('Signal '+str(signum))
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
    report=dict(kind='observation_transport_stress',passed=False,completed_captures=0,
        arm_trajectory_commanded=False,gripper_goal_commanded=False,holding_proof=False,
        source_advance_samples={},maximum_source_advance_gap_wall_s={})
    sim=None;last={};started=time.monotonic()
    def sample(key,stamp):
        now=time.monotonic()
        if key in last and stamp<=last[key][0]:return
        if key in last:report['maximum_source_advance_gap_wall_s'][key]=max(
            report['maximum_source_advance_gap_wall_s'].get(key,0.),now-last[key][1])
        last[key]=(stamp,now)
        report['source_advance_samples'][key]=report['source_advance_samples'].get(key,0)+1
    try:
        sim=Simulation(args.namespace,args.scene);sim.stop_directory=args.output
        sim.create_subscription(JointState,args.namespace+'/joint_states',
            lambda m:sample('joints',m.header.stamp.sec+m.header.stamp.nanosec/1e9),qos_profile_sensor_data)
        for key,topic in [('object','tasks/object_truth'),('contacts','tasks/contacts')]:
            sim.create_subscription(String,args.namespace+'/'+topic,
                lambda m,k=key:sample(k,json.loads(m.data)['stamp']),qos_profile_sensor_data)
        sim.create_subscription(Clock,args.namespace+'/clock',
            lambda m:sample('clock',m.clock.sec+m.clock.nanosec/1e9),qos_profile_sensor_data)
        sim.connect();sim.reset()
        description=(args.scene/'robot.urdf').read_text()
        for index in range(args.captures):
            observation=observe(sim,description,args.reference,args.output/f'observation-{index:02d}')
            report['completed_captures']=index+1
            report['last_observation_sha256']=observation['sha256']
            report['elapsed_wall_s']=time.monotonic()-started
            write_json(args.output/'progress.json',report)
            print(json.dumps(dict(capture=index+1,status=observation['status'],
                maximum_source_advance_gap_wall_s=report['maximum_source_advance_gap_wall_s'])),flush=True)
        report['guard_faults']=sim.guard['latched_causes']
        report['passed']=(not report['guard_faults'] and set(last)=={'clock','object','contacts','joints'}
            and max(report['maximum_source_advance_gap_wall_s'].values())<=.15)
    except BaseException as error:
        report['error']=str(error)
        if sim is not None:report['guard_faults']=(sim.guard or {}).get('latched_causes')
    finally:
        if sim is not None:
            if sim.owned:
                report['stop']=sim.stop();report['passed']=report['passed'] and report['stop']['confirmed']
                sim.phase='done';sim.heartbeat();sim.owned=False
            sim.close()
        report['elapsed_wall_s']=time.monotonic()-started
        write_json(args.output/'report.json',report);print(json.dumps(report),flush=True)
        rclpy.shutdown()
    return 0 if report['passed'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--captures',type=int,default=12)
    parser.add_argument('--namespace',default='/uwa_grasp_validation')
    args=parser.parse_args();simulation_only()
    if not 1<=args.captures<=24:parser.error('Capture count must be between1 and24')
    with resource_lease(args.namespace):return execute(args)


if __name__=='__main__':raise SystemExit(main())

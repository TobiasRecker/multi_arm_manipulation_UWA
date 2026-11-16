#!/usr/bin/env python3
"""Read-only evaluation trace for an isolated uwa_cell_tasks simulation run."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from uwa_cell_motion.common import simulation_only
from uwa_cell_tasks.core import write_json,RunStore


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--namespace',default='/uwa_grasp_validation')
    parser.add_argument('--timeout',type=float,default=900.)
    parser.add_argument('--prepare',action='store_true',help='Create an unused CREATED run before ROS discovery; start recorder before runner')
    args=parser.parse_args();simulation_only()
    if args.prepare:
        if args.run.exists():parser.error('--prepare requires a new run directory')
        RunStore(args.run).event('CREATED','observe',recorder_prepared=True)
    if not args.namespace.startswith('/uwa_grasp_') or not (args.run/'state.json').is_file():
        parser.error('Existing isolated simulation task run required')
    path=args.run/'evaluation-trace.jsonl'
    rclpy.init();node=Node('task_evaluation_trace');data={};rows=0;last_saved=0.;origin=time.monotonic()
    def message(key):return lambda msg:data.update({key:json.loads(msg.data)})
    for key,topic in [('object','tasks/object_truth'),('contacts','tasks/contacts'),
                      ('guard','collision_guard/decision'),('supervisor','collision_supervisor/status')]:
        node.create_subscription(String,args.namespace+'/'+topic,message(key),
            qos_profile_sensor_data if key in ('object','contacts') else 10)
    node.create_subscription(String,args.namespace+'/tasks/group',message('group'),
        QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    def joints(msg):
        data['joints']=dict(stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9,
            positions={j:q for j,q in zip(msg.name,msg.position) if j.startswith(('right_front_','right_rear_'))},
            velocities={j:v for j,v in zip(msg.name,msg.velocity) if j.startswith(('right_front_','right_rear_'))})
    node.create_subscription(JointState,args.namespace+'/joint_states',joints,qos_profile_sensor_data)
    terminal=None
    try:
        with path.open('x') as output:
            while time.monotonic()-origin<args.timeout:
                rclpy.spin_once(node,timeout_sec=.02)
                now=time.monotonic()
                if now-last_saved<.05 or not all(k in data for k in ('object','contacts','joints','guard','supervisor')):continue
                state=json.loads((args.run/'state.json').read_text());terminal=state['state']
                row=dict(evaluation_only=True,elapsed_wall_s=now-origin,phase=state['phase'],
                    state=terminal,object=data['object'],contacts={k:data['contacts'][k] for k in ('stamp','pads','supported')},
                    joints=data['joints'],group=data.get('group'),
                    blocked_arms=data['supervisor']['blocked_arms'],held_arms=data['supervisor']['held_arms'],
                    faults=data['guard']['latched_causes'])
                output.write(json.dumps(row)+'\n');rows+=1;last_saved=now
                if rows%20==0:output.flush()
                if terminal in ('DONE','FAILED'):break
    finally:
        write_json(args.run/'evaluation-trace-summary.json',dict(evaluation_only=True,rows=rows,
            elapsed_wall_s=time.monotonic()-origin,terminal_state=terminal,source='own simulation telemetry; never a planning input'))
        node.destroy_node();rclpy.shutdown()
    print(str(path.resolve()))


if __name__=='__main__':main()

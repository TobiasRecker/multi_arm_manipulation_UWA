#!/usr/bin/env python3
"""Read-only bounded hardware protection trace: transitions plus1Hz snapshots."""
import argparse
import json
import os
from pathlib import Path
import time

import rclpy
from std_msgs.msg import String
from uwa_cell_motion.hardware_state import require_domain


def transition_key(value):
    ports={r:{k:p.get(k) for k in ('held','manager_fresh','hardware_mode_verified',
             'hold_config_verified','controller_error','native_stop_error','native_stop_events')}
           for r,p in value.get('ports',{}).items()}
    return json.dumps(dict(state=value.get('state'), instance=value.get('instance'),
        blocked=value.get('blocked_arms'),held=value.get('held_arms'),
        stationary_arms=value.get('stationary_arms'),
        stationarity={r:(e.get('confirmed'),e.get('reason')) for r,e in value.get('stationarity_evidence',{}).items()},
        faults=value.get('faults'),causes=value.get('latched_causes'),
        witness=value.get('witness_available'),tripped=value.get('tripped'),ports=ports),sort_keys=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=900.)
    args=p.parse_args();require_domain('hardware')
    if not 1<=args.seconds<=3600:p.error('Bounded1–3600s trace required')
    args.output.mkdir(parents=True,exist_ok=False)
    rclpy.init();node=rclpy.create_node('carton_interlock_trace_'+str(os.getpid()))
    old={};written={};counts={};latest={};maximum_age={};start=time.monotonic()
    with (args.output/'trace.jsonl').open('w') as stream:
        def receive(message,topic):
            now=time.monotonic()
            try:value=json.loads(message.data);key=transition_key(value)
            except (ValueError,TypeError):return
            latest[topic]=value;counts[topic]=counts.get(topic,0)+1
            stamp=value.get('evaluated_monotonic_s',now)
            maximum_age[topic]=max(maximum_age.get(topic,0),now-stamp)
            if old.get(topic)!=key or now-written.get(topic,-float('inf'))>=1.:
                stream.write(json.dumps(dict(received_monotonic_s=now,topic=topic,value=value),allow_nan=False)+'\n');stream.flush()
                old[topic]=key;written[topic]=now
        for topic in ['/uwa_cell/collision_guard/decision','/uwa_cell/collision_supervisor/status','/uwa_cell/hardware_watchdog/status']:
            node.create_subscription(String,topic,lambda m,t=topic:receive(m,t),1)
        try:
            while time.monotonic()-start<args.seconds:rclpy.spin_once(node,timeout_sec=.05)
        except KeyboardInterrupt:pass
        finally:
            report=dict(read_only=True,duration_s=time.monotonic()-start,counts=counts,
                        maximum_received_packet_age_s=maximum_age,latest=latest)
            (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
            node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()

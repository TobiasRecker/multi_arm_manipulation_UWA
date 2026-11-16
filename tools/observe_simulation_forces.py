#!/usr/bin/env python3
"""Read-only idle-world force observation; optionally check supported weight.

No services, actions, parameter writes or controller commands are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String
from uwa_cell_motion.common import simulation_only
from uwa_cell_tasks.scene import verify_scene
from uwa_cell_tasks.core import seal,write_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--namespace',default='/uwa_grasp_validation')
    p.add_argument('--seconds',type=float,default=8.);p.add_argument('--supported-mass',type=float)
    a=p.parse_args();simulation_only()
    if not a.namespace.startswith('/uwa_grasp_'):p.error('Private simulation namespace required')
    scene=verify_scene(a.scene);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    rclpy.init();node=rclpy.create_node('read_only_force_observer');rows=[];started=None;latest_rx=None
    path=out/'forces.jsonl';f=path.open('x');start=time.monotonic()
    def receive(msg):
        nonlocal started,latest_rx
        d=json.loads(msg.data)
        if len(d['joint_reactions'])!=len(d['requested_joints']):return
        if a.supported_mass is not None and not any(any('table_plate' in c for c in pair['collisions']) for pair in d['contact_loads']):return
        if started is None:started=time.monotonic()
        now=time.monotonic();d['observer_elapsed_wall_s']=now-start
        d['reception_gap_s']=None if latest_rx is None else now-latest_rx;latest_rx=now
        rows.append(d);f.write(json.dumps(d)+'\n')
    node.create_subscription(String,a.namespace+'/tasks/forces',receive,qos_profile_sensor_data)
    try:
        while time.monotonic()-start<80.:
            rclpy.spin_once(node,timeout_sec=.05)
            if started is not None and time.monotonic()-started>=a.seconds:break
    finally:f.close();node.destroy_node();rclpy.shutdown()
    assert rows and started is not None and time.monotonic()-started>=a.seconds,'Force observation did not complete'
    stable=[r for r in rows if r['observer_elapsed_wall_s']>=rows[0]['observer_elapsed_wall_s']+2.]
    normal=np.array([sum(p['mean_normal_load_n'] for p in r['contact_loads'] if any('table_plate' in c for c in p['collisions'])) for r in stable])
    checks=dict(data_present=len(stable)>100,valid_wrenches=all(r['missing_wrenches']==0 and r['invalid_wrenches']==0 for r in stable),
        physics_step_extrema=all(r['physics_samples']>=9 for r in stable),joint_reactions_present=all(len(r['joint_reactions'])==4 for r in stable))
    if a.supported_mass is not None:checks['supported_weight']=abs(float(normal.mean())-a.supported_mass*9.81)<a.supported_mass*9.81*.02
    result=seal(dict(kind='read_only_force_observation',passed=all(checks.values()),checks=checks,scene_sha256=scene['sha256'],
        samples=len(rows),stable_samples=len(stable),supported_mass_kg=a.supported_mass,
        mean_table_normal_n=float(normal.mean()),maximum_table_normal_n=float(normal.max()),
        maximum_reception_gap_s=max(r['reception_gap_s'] or 0. for r in rows),
        trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),observer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        interpretation='Idle supported scene only; not a loaded-grasp or dynamic capacity result.'))
    write_json(out/'force-observation.json',result);print(json.dumps(result));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only preparation: native states, RTDE cadence and checked q6 plan.

No ROS services/actions, controllers, reset, power, Play or gripper operations.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import numpy as np
from uwa_cell_motion.common import config,dump,joint_names
from uwa_cell_motion.hardware_model import HardwareProblem,inventory_path
from uwa_cell_motion.hardware_state import MotionOutputReader,require_domain


def read_stationary(host,hz,seconds=1.):
    reader=MotionOutputReader(host,frequency_hz=hz);rows=[]
    try:
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            stamp,q,v,status=reader.sample()
            rows.append(dict(device_stamp=stamp,received=time.monotonic(),q=q,v=v,status=status))
    finally:reader.close()
    if len(rows)<5:raise ValueError('Insufficient native state samples')
    dt=np.diff([r['device_stamp'] for r in rows]);wall=np.diff([r['received'] for r in rows])
    if np.any(dt<=0) or np.any(dt>.1) or np.any(wall>.1):raise ValueError('Native observer state gap')
    if max(abs(v) for r in rows for v in r['v'])>.0002:raise ValueError('Arm is moving; preparation rejected')
    if any(r['status']['robot_mode']!=7 or r['status']['safety_mode']!=1 for r in rows):
        raise ValueError('Native robot mode must be RUNNING/NORMAL; no startup performed')
    return dict(rows=rows,requested_hz=hz,device_interval_s=dict(median=float(np.median(dt)),maximum=float(max(dt))),
        receive_interval_s=dict(median=float(np.median(wall)),maximum=float(max(wall))),
        effective_device_hz=float(1/np.median(dt)))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--inventory',type=Path,default=inventory_path())
    p.add_argument('--delta-rad',type=float,default=.03);a=p.parse_args();a.output=a.output.resolve();require_domain('hardware')
    if not np.isfinite(a.delta_rad) or not 0<abs(a.delta_rad)<=.03:p.error('q6 displacement must be nonzero and at most0.03rad')
    a.output.mkdir(parents=True,exist_ok=False)
    cfg=config(a.config)
    if cfg['velocity_limit_rad_s']>.003 or cfg['acceleration_limit_rad_s2']>.006:
        raise ValueError('Use the unchanged slow commissioning profile')
    problem=HardwareProblem(a.output/'model',cfg,a.inventory)
    report=dict(kind='read_only_right_front_stop_preparation',robot='right_front',robot_ip=problem.profiles['right_front']['ip'],
        robot_commands_sent=0,actual_motion_executed=False,complete=False)
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures={r:pool.submit(read_stationary,profile['ip'],500. if r=='right_front' else 20.)
                for r,profile in problem.profiles.items()}
            results={r:f.result() for r,f in futures.items()}
        dump(a.output/'native-state.json',results)
        start={}
        for rid,names in problem.names.items():
            start.update(zip(names[:6],results[rid]['rows'][-1]['q']))
            start.update({n:0. for n in names[6:]})
        goal=[start[j] for j in joint_names('right_front')];goal[5]+=a.delta_rad
        request=dict(schema_version=1,start=start,goals=dict(right_front=goal),hardware_binding=problem.binding,
            execution_mode='hardware',source='independent output-only RTDE; offline start, recheck before execution')
        dump(a.output/'request.json',request)
        plan=problem.plan(request,'rrtconnect',seed=0);plan['execution_mode']='hardware';dump(a.output/'plan.json',plan)
        report.update(plan_success=plan['success'],plan_error=plan.get('error'),
            observer_cadence={r:{k:v for k,v in d.items() if k!='rows'} for r,d in results.items()},
            delta_q6_rad=a.delta_rad,velocity_limit_rad_s=cfg['velocity_limit_rad_s'],
            acceleration_limit_rad_s2=cfg['acceleration_limit_rad_s2'],complete=bool(plan['success']),
            interpretation='Model/observer preparation only; operator workspace and actual start must be rechecked; no braking measurement')
        if plan['success']:
            from uwa_cell_motion.preview import render
            render(plan,a.output/'preview.html')
    except Exception as e:
        report['error']=str(e);raise
    finally:dump(a.output/'preparation.json',report)
    print(json.dumps(report,indent=2))
    if not report['complete']:raise SystemExit(1)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Offline comparison of frozen paths under explicit per-axis speed contracts.

Retains model margin, data-age/check interval, assumed reaction and braking.
Never connects to a robot, changes a service or activates a generated profile.
"""
import argparse
import copy
import json
from pathlib import Path
import time
import numpy as np
import yaml
from match_ur_hardware.profiles import load_profiles
from uwa_cell_motion.common import (BODY_RESERVE_MODEL,ROBOT_IDS,PAIRS,
    dump,joint_names,sha,config)
from uwa_cell_motion.hardware_model import HardwareProblem


def path_gap_bounds(problem,request,waypoints,step):
    """Whole-path surface gaps with analytic coverage between sample states."""
    names=request['joint_names'];waypoints=np.asarray(waypoints,float)
    bounds={pair:np.full((len(problem.spheres.radii[pair[0]]),len(problem.spheres.radii[pair[1]])),np.inf) for pair in PAIRS}
    for start,end in zip(waypoints[:-1],waypoints[1:]):
        delta=end-start;count=max(1,int(np.ceil(np.max(abs(delta))/step)))
        local={pair:np.full_like(value,np.inf) for pair,value in bounds.items()}
        inflation={}
        for rid in ROBOT_IDS:
            dq=np.array([abs(delta[names.index(j)])/(2*count) if j in names else 0. for j in problem.names[rid]])
            inflation[rid]=problem.spheres.motion_radii[rid]@dq
        for u in np.linspace(0,1,count+1):
            state=dict(request['start'],**dict(zip(names,start+u*delta)))
            world=problem.spheres.world(state)
            for a,b in PAIRS:
                gap=np.linalg.norm(world[a][:,None,:]-world[b][None,:,:],axis=2)
                gap-=problem.spheres.radii[a][:,None]+problem.spheres.radii[b][None,:]
                local[a,b]=np.minimum(local[a,b],gap)
        for a,b in PAIRS:
            bounds[a,b]=np.minimum(bounds[a,b],local[a,b]-inflation[a][:,None]-inflation[b][None,:])
    if not all(np.isfinite(v).all() for v in bounds.values()):raise ValueError('No finite path segments')
    return bounds


def profile(base,request,waypoints,speed,stationary,tracking,factor):
    result=copy.deepcopy(base)
    result.pop('arm_velocity_limits_rad_s',None)
    result.update(stopping_reserve_model=BODY_RESERVE_MODEL,command_velocity_limit_rad_s=speed,
        joint_velocity_limits_rad_s={r:[stationary]*6 for r in ROBOT_IDS})
    names=request['joint_names'];ratios=np.zeros(len(names))
    for delta in np.diff(np.asarray(waypoints),axis=0):
        peak=np.max(abs(delta))
        if peak>0:ratios=np.maximum(ratios,abs(delta)/peak)
    for rid in request['selected']:
        result['joint_velocity_limits_rad_s'][rid]=[
            float(tracking+factor*speed*ratios[names.index(j)]) for j in joint_names(rid)]
    return result


def clearance_bound(problem,gaps,cfg):
    budgets={r:problem.spheres.body_budget(r,np.zeros(len(problem.names[r])),cfg['state_timeout_s'],cfg)['total_m'] for r in ROBOT_IDS}
    rows=[]
    for a,b in PAIRS:
        slack=gaps[a,b]-cfg['model_margin_m']-budgets[a][:,None]-budgets[b][None,:]
        i,j=np.unravel_index(np.argmin(slack),slack.shape)
        rows.append(dict(arms=[a,b],remaining_clearance_bound_m=float(slack[i,j]),
            sphere_indices=[int(i),int(j)],links=[problem.spheres.links[a][i],problem.spheres.links[b][j]]))
    return min(row['remaining_clearance_bound_m'] for row in rows),rows


def audit(source,out,args):
    old=json.loads(source.read_text())
    if not old.get('success') or not old.get('hardware_plan'):raise ValueError('Successful frozen hardware plan required')
    out.mkdir(parents=True,exist_ok=False)
    base=old['config'];request=old['request'];waypoints=old['trajectory']['waypoints']
    def cfg(speed):return profile(base,request,waypoints,speed,args.stationary_cap,args.tracking_allowance,args.speed_factor)
    problem=HardwareProblem(out/'model',cfg(args.command_speed),old['inventory'],old.get('layout_path'))
    if problem.signature!=old['model_signature'] or problem.spheres.geometry.assets!=old['mesh_sha256']:
        raise ValueError('Frozen path geometry/mesh binding changed')
    expected=sha(json.dumps(dict(inventory=load_profiles(old['inventory']),model=problem.signature,
        config=base,policy='all-tool-openings-v1'),sort_keys=True))
    if old['hardware_binding']!=expected:raise ValueError('Source inventory/config binding changed')
    gaps=path_gap_bounds(problem,request,waypoints,args.joint_step)
    if clearance_bound(problem,gaps,cfg(0.))[0]<base['reset_hysteresis_m']:
        raise ValueError('Even residual stationary/tracking contracts lack reserve; no candidate')
    low,high=0.,args.command_speed
    if clearance_bound(problem,gaps,cfg(high))[0]>=base['reset_hysteresis_m']:low=high
    else:
        for _ in range(35):
            mid=(low+high)/2
            if clearance_bound(problem,gaps,cfg(mid))[0]>=base['reset_hysteresis_m']:low=mid
            else:high=mid
        low*=.95
    if low<=0:raise ValueError('No positive speed candidate')
    chosen=cfg(low);(out/'config.yaml').write_text(yaml.safe_dump(chosen,sort_keys=False));config(out/'config.yaml')
    # Rebuild the final immutable config/model binding before writing a plan.
    problem=HardwareProblem(out/'final-model',chosen,old['inventory'],old.get('layout_path'))
    normalized=problem.normalize(request)
    trajectory=problem.time_parameterize(normalized,waypoints)
    plan=dict(old,request=normalized,config=chosen,hardware_binding=problem.binding,
        trajectory=trajectory,metrics=problem.metrics(normalized,trajectory),
        method='revalidated_frozen_geometry',stop_budget_qualification='ASSUMPTIONS UNCHANGED; NOT MEASURED ON HARDWARE')
    dump(out/'plan.json',plan)
    minimum,rows=clearance_bound(problem,gaps,chosen)
    report=dict(source_plan=str(source.resolve()),source_sha256=sha(source.read_text()),
        selected=normalized['selected'],old_duration_s=old['trajectory']['duration_s'],
        proposed_duration_s=trajectory['duration_s'],command_limit_rad_s=low,
        joint_caps_rad_s=chosen['joint_velocity_limits_rad_s'],
        retained_parameters={k:chosen[k] for k in ('model_margin_m','rate_hz','state_timeout_s',
            'heartbeat_timeout_s','stop_latency_s','braking_acceleration_rad_s2')},
        whole_path_remaining_clearance_bound_m=minimum,pairs=rows,
        analytic_between_sample_coverage=True,geometry_sample_step_rad=args.joint_step,
        activation_performed=False,physical_stop_qualification=False,
        limitations=['Frozen former actual start; obtain a fresh start before execution',
            'Enforce and monitor the exact positive per-joint caps; zero measured speed is not a contract',
            'Each serial phase has a different guard profile; no automatic live profile transition',
            'Physical stop latency/braking assumptions remain unqualified'])
    dump(out/'audit.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plans',type=Path,nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--command-speed',type=float,default=.05)
    p.add_argument('--stationary-cap',type=float,default=.001)
    p.add_argument('--tracking-allowance',type=float,default=.002)
    p.add_argument('--speed-factor',type=float,default=1.3)
    p.add_argument('--joint-step',type=float,default=.005)
    args=p.parse_args()
    args.output=args.output.expanduser().resolve()
    if any(not np.isfinite(v) or v<=0 for v in (args.command_speed,args.stationary_cap,args.tracking_allowance,args.speed_factor,args.joint_step)) or args.speed_factor<1:
        p.error('Positive finite bounds and speed-factor >=1 required')
    args.output.mkdir(parents=True,exist_ok=False);began=time.monotonic();rows=[]
    for index,source in enumerate(args.plans):
        print(json.dumps(dict(phase='AUDITING',source=str(source))),flush=True)
        row=audit(source,args.output/f'{index+1:02d}',args);rows.append(row)
        dump(args.output/'summary.json',dict(phases=rows,old_duration_s=sum(r['old_duration_s'] for r in rows),
            proposed_duration_s=sum(r['proposed_duration_s'] for r in rows),activation_performed=False,elapsed_s=time.monotonic()-began))
        print(json.dumps({k:row[k] for k in ('selected','old_duration_s','proposed_duration_s','command_limit_rad_s','whole_path_remaining_clearance_bound_m')}),flush=True)


if __name__=='__main__':main()

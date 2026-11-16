#!/usr/bin/env python3
"""Evaluate recorded contact lifts; never command robots or modify raw evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from match_cooperative_handling.rigid_object import pose_error
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_tasks.core import ARMS,digest,seal,verify,write_json,object_point_height
from uwa_cell_tasks.scene import verify_scene
from uwa_cell_tasks.operating import velocity_limits


def evaluate(run,scene_directory):
    scene=verify(json.loads((scene_directory/'scene.json').read_text()));cfg=scene['cfg']
    state=json.loads((run/'state.json').read_text());checks={};notes=[]
    checks['runner_completed']=state['state']=='DONE'
    checks['holds_confirmed']=bool(state.get('stop',{}).get('confirmed'))
    try:verify_scene(scene_directory);checks['current_implementation_bound']=True
    except (ValueError,OSError,KeyError) as error:checks['current_implementation_bound']=False;notes.append(str(error))
    try:
        plan=verify(json.loads((run/'plan.json').read_text()))
        checks['plan_scene_binding']=plan['scene_sha256']==scene['sha256']
        motion=verify(json.loads((run/'object-lift.json').read_text()))
        checks['one_object_trajectory']=(motion['kind']=='rigid_object' and len(motion['joint_names'])==12
            and tuple(motion['group']['members'])==ARMS and motion['scene_sha256']==scene['sha256'])
    except (OSError,KeyError,ValueError) as error:
        checks['one_object_trajectory']=False;notes.append('Missing or invalid compiled object motion: '+str(error))
    measured=state.get('measured_peak_speeds_rad_s',{});peak_source='state.json';diagnostic_sha=None
    if not measured and (run/'stop-diagnostic.json').exists():
        diagnostic=run/'stop-diagnostic.json';measured=json.loads(diagnostic.read_text()).get('measured_peak_speeds_rad_s',{})
        peak_source='stop-diagnostic.json';diagnostic_sha=hashlib.sha256(diagnostic.read_bytes()).hexdigest()
    peaks=[abs(v) for phase in measured.values() for v in phase.values()]
    checks['measured_speed_bound']=bool(peaks) and all(
        abs(speed)<=velocity_limits([joint],cfg)[0]+1e-8
        for phase in measured.values() for joint,speed in phase.items())
    arm_peaks=[abs(v) for phase in measured.values() for j,v in phase.items() if '_robotiq_' not in j]
    finger_peaks=[abs(v) for phase in measured.values() for j,v in phase.items() if '_robotiq_' in j]
    trace=run/'evaluation-trace.jsonl';loaded=[];released=[];moving=[]
    if trace.exists():
        for line in trace.open():
            row=json.loads(line);group=row.get('group')
            if row['phase'] in ('approach','grasp','move_object','set_down','release'):moving.append(row)
            if not group:continue
            if group.get('released'):released.append(row)
            elif not group.get('release_requested'):loaded.append(row)
    checks['loaded_trace_present']=bool(loaded)
    checks['guard_fault_free_during_motion']=bool(moving) and all(not row['faults'] for row in moving)
    checks['supported_release_observed']=any(r['contacts']['supported'] for r in released)
    checks['pads_retained_while_loaded']=bool(loaded) and all(
        all(all(r['contacts']['pads'][a].values()) for a in ARMS) for r in loaded)
    checks['offsets_immutable']=bool(loaded) and len({digest(r['group']['object_to_tcp']) for r in loaded})==1
    reference=scene.get('lift_reference_point_object_m',[0.,0.,0.])
    metrics=dict(loaded_samples=len(loaded),actual_hub_m=None,asset_origin_hub_m=None,max_rigidity_error_m=None,max_rigidity_error_rad=None,
                 near_target_unsupported_duration_s=0.,maximum_measured_joint_speed_rad_s=max(peaks) if peaks else None,
                 motion_trace_samples=len(moving))
    metrics.update(maximum_measured_arm_speed_rad_s=max(arm_peaks) if arm_peaks else None,
        maximum_measured_finger_speed_rad_s=max(finger_peaks) if finger_peaks else None)
    if loaded:
        description=(scene_directory/'robot.urdf').read_text()
        chains={a:Chain(description,'world',a+'_tool0') for a in ARMS}
        first=loaded[0];origin=np.array(first['object']['T_world_object']);baseline={
            a:np.linalg.inv(origin)@chains[a].forward(first['joints']['positions']) for a in ARMS}
        errors=[];heights=[];origin_heights=[];near_start=None;longest=0.
        for row in loaded:
            obj=np.array(row['object']['T_world_object'])
            height=object_point_height(obj,reference)-object_point_height(origin,reference);heights.append(height)
            origin_heights.append(float(obj[2,3]-origin[2,3]))
            for a in ARMS:errors.append(pose_error(chains[a].forward(row['joints']['positions']),obj@baseline[a]))
            near=(not row['contacts']['supported'] and abs(height-cfg['lift_m'])<=.002)
            stamp=row['object']['stamp']
            if near:
                if near_start is None:near_start=stamp
                longest=max(longest,stamp-near_start)
            else:near_start=None
        metrics.update(actual_hub_m=max(heights),asset_origin_hub_m=max(origin_heights),max_rigidity_error_m=max(e[0] for e in errors),
            max_rigidity_error_rad=max(e[1] for e in errors),near_target_unsupported_duration_s=longest)
    checks['physical_lift_observed']=metrics['actual_hub_m'] is not None and abs(metrics['actual_hub_m']-cfg['lift_m'])<=.002
    checks['unsupported_hold_observed']=metrics['near_target_unsupported_duration_s']>=cfg['dwell_s']-.05
    checks['rigidity_corridor_observed']=(metrics['max_rigidity_error_m'] is not None
        and metrics['max_rigidity_error_m']<=cfg['relative_position_tolerance_m']
        and metrics['max_rigidity_error_rad']<=cfg['relative_angle_tolerance_rad'])
    return seal(dict(run=str(run.resolve()),scene_sha256=scene['sha256'],passed=all(checks.values()),checks=checks,
        metrics=metrics,notes=notes,trace_sampling_allowance_s=.05,
        lift_reference_point_object_m=reference,lift_reference_kind=scene.get('lift_reference_kind','legacy_asset_origin'),
        validator_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        measured_peak_source=peak_source,stop_diagnostic_sha256=diagnostic_sha,
        interpretation='Simulation evaluation only; near-target interval includes settling, runner separately enforces dwell.',
        assumptions=cfg['simulation_assumptions']))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',required=True,type=Path);p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--report-name',default='validation-report.json',help='New report filename; raw evidence and previous reports are retained')
    args=p.parse_args();results=[]
    if Path(args.report_name).name!=args.report_name or not args.report_name.endswith('.json'):p.error('Use a JSON basename')
    if any((run/args.report_name).exists() for run in args.runs):p.error('Choose a new report name; previous reports must remain')
    for run in args.runs:
        report=evaluate(run,args.scene);write_json(run/args.report_name,report);results.append(report)
        print(run.name, 'PASS' if report['passed'] else 'INCOMPLETE / FAIL',report['metrics'])
    print('Completed contact runs:',sum(r['passed'] for r in results),'/',len(results))


if __name__=='__main__':main()

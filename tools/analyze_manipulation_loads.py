#!/usr/bin/env python3
"""Summarize recorded task-force windows per jaw and joint, without a damage claim."""
import argparse
import hashlib
import json
from pathlib import Path
from uwa_cell_tasks.core import verify,seal,write_json
from uwa_cell_tasks.force_metrics import pad_load_window


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    scene=verify(json.loads((a.scene/'scene.json').read_text()));reference=scene['cfg'].get('pad_load_reference_n')
    if reference is None:p.error('Scene must declare its per-jaw comparison reference')
    path=a.run/'force-trace.jsonl';full_rate=path.exists()
    if not full_rate:path=a.run/'evaluation-trace.jsonl'
    totals={};joints={};count=0;bad=0;phases={};previous_stamp=None;gaps=0
    for line in path.open():
        row=json.loads(line);force=row.get('forces')
        if force is None:bad+=1;continue
        stamp=force['stamp']
        if previous_stamp is not None and abs(stamp-previous_stamp-force['window_duration_s'])>1e-5:gaps+=1
        previous_stamp=stamp
        report=pad_load_window(force,reference);count+=1
        if not report['usable']:bad+=1
        phase=phases.setdefault(row['phase'],dict(samples=0,maximum_pad_mean_upper_bound_n=0.));phase['samples']+=1
        for pad,data in report['pads'].items():
            record=totals.setdefault(pad,dict(maximum_mean_load_upper_bound_n=0.,maximum_peak_load_upper_bound_n=0.))
            record['maximum_mean_load_upper_bound_n']=max(record['maximum_mean_load_upper_bound_n'],data['mean_load_upper_bound_n'])
            record['maximum_peak_load_upper_bound_n']=max(record['maximum_peak_load_upper_bound_n'],data['peak_load_upper_bound_n'])
            phase['maximum_pad_mean_upper_bound_n']=max(phase['maximum_pad_mean_upper_bound_n'],data['mean_load_upper_bound_n'])
        for name,data in force['joint_reactions'].items():
            record=joints.setdefault(name,dict(maximum_reaction_force_norm_n=0.,maximum_reaction_torque_norm_nm=0.))
            record['maximum_reaction_force_norm_n']=max(record['maximum_reaction_force_norm_n'],data['peak_force_norm_n'])
            record['maximum_reaction_torque_norm_nm']=max(record['maximum_reaction_torque_norm_nm'],data['peak_torque_norm_nm'])
    result=seal(dict(kind='recorded_manipulation_load_summary',observed_windows=count,missing_or_invalid_windows=bad,
        scene_sha256=scene['sha256'],trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),pad_load_reference_n=reference,
        full_rate_force_trace=full_rate,missing_force_windows=gaps,coverage_complete=full_rate and not gaps and not bad,
        reference_scope='User report per jaw/wall patch; not a measured break limit',pads=totals,joint_reactions=joints,phases=phases,
        damage_assessed=False,hardware_capacity_assessed=False,
        interpretation='Joint reactions include robot/tool gravity and inertia. Contact peaks depend on rigid-contact timestep.'))
    if a.output.exists():p.error('Choose a new output path; previous analysis must remain')
    write_json(a.output,result);print(json.dumps(result));return 0 if count and result['coverage_complete'] else 1

if __name__=='__main__':raise SystemExit(main())

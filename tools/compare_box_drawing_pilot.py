#!/usr/bin/env python3
"""Compare audited task variants with common initial/final joint states."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path

import numpy as np

from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.smooth_paths import sample_segment


def compare(runs, output):
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    names=[j for a in ROBOT_IDS for j in joint_names(a)]
    worker=[names.index(j) for j in joint_names('left_front')]
    holders=[names.index(j) for a in ('right_front','right_rear') for j in joint_names(a)]
    rows=[];first=last=None;reference=None
    for path in map(lambda x:Path(x).resolve(),runs):
        raw=(path/'result.json').read_bytes();d=json.loads(raw)
        audit=json.loads((path/'independent-audit.json').read_text())
        if not audit['passed'] or audit['result_sha256']!=hashlib.sha256(raw).hexdigest():
            raise ValueError('Matching independent audit required: '+str(path))
        if d['status']!='MODEL_SEQUENCE_COMPLETE' or d['backend']!='kinematic_model':
            raise ValueError('Expected completed model run')
        start=np.array([d['initial_state'][j] for j in names])
        end=np.array(d['phases'][-1]['segment']['positions'][-1])
        if reference is None:
            reference=d;first=start;last=end
        if d['model_signature']!=reference['model_signature'] or d['dimensions_m']!=reference['dimensions_m'] or d['program']['surfaces']!=reference['program']['surfaces'] or d['program']['circle_radius_m']!=reference['program']['circle_radius_m']:
            raise ValueError('Different scene or task')
        if max(np.max(abs(start-first)),np.max(abs(end-last)))>1e-6:
            raise ValueError('Different initial or final joint state')
        overlap=0.;outbound=[];duration=0.;per_phase=[]
        for phase in d['phases']:
            t=np.linspace(0,phase['duration_s'],2001)
            q=sample_segment(phase['segment'],t)
            v=sample_segment(phase['segment'],t,1)
            moving=(np.max(abs(v[:,worker]),axis=1)>1e-5)&(np.max(abs(v[:,holders]),axis=1)>1e-5)
            both=float(np.trapezoid(moving.astype(float),t))
            overlap+=both;duration+=phase['duration_s']
            per_phase.append(dict(id=phase['id'],duration_s=phase['duration_s'],sampled_model_overlap_s=both))
            if phase['id'] in ('present_bottom','transfer_to_z_min'):outbound.extend(q[:,worker])
        span=np.rad2deg(np.ptp(np.array(outbound),axis=0))
        rows.append(dict(run=str(path),label=path.name,variant=d['program'].get('variant','baseline'),
                         result_sha256=hashlib.sha256(raw).hexdigest(),duration_model_s=duration,
                         worker_transition_span_deg=span.tolist(),max_worker_transition_span_deg=float(span.max()),
                         sampled_model_overlap_s=overlap,phases=per_phase,
                         min_arm_gap_m=d['validation']['min_arm_gap_m'],
                         source_feedback=d.get('feedback_source'),
                         viewer=os.path.relpath(path/'viewer.html',output)))
    result=dict(schema_version=1,backend='kinematic_model',common_initial_final_states=True,
                circle_and_motion_limits_unchanged=True,rows=rows,
                note='All modeled task phases included, including closer/restore translations. No physical execution/contact proof.')
    (output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    labels={'baseline':'Original — sequential','overlap':'Same box position — overlapping motion',
            'closer_coordinated':'Box 8 cm closer — coordinated, smaller joint travel'}
    body=''
    for index,row in enumerate(rows):
        body+='<tr><td><button onclick="choose('+str(index)+')">'+html.escape(labels[row['variant']])+'</button></td><td>'+f"{row['duration_model_s']:.2f} s"+'</td><td>'+f"{row['max_worker_transition_span_deg']:.1f}°"+'</td><td>'+f"{row['sampled_model_overlap_s']:.2f} s"+'</td></tr>'
    payload=json.dumps([dict(viewer=r['viewer'],label=labels[r['variant']]) for r in rows]).replace('</','<\\/')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>UWA drawing — feedback comparison</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101a2b;color:white;font:16px system-ui}main{padding:20px}h1{color:#ffe2a1}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #809bb9;text-align:left}button{font:inherit;background:#f7faff;color:#10203a;padding:9px;border:2px solid white;cursor:pointer}#selected{padding:12px;border:3px solid #ffd17b;font-weight:bold}iframe{width:100%;height:1100px;border:2px solid #b9cde5}</style>
<main><h1>Drawing pilot — your feedback tested</h1><p>Same initial and final joint states, same circles and motion limits. Both the 8 cm relocation and its return are included. Kinematic model; no physical forces or contact validation.</p>
<table><tr><th>Variant / open preview</th><th>Total model time</th><th>Largest worker-joint span during transition</th><th>Estimated model movement overlap</th></tr>'''+body+'''</table><p id="selected"></p><iframe id="preview" title="Selected model preview"></iframe></main>
<script>const cases='''+payload+''';function choose(i){document.getElementById('preview').src=cases[i].viewer;document.getElementById('selected').textContent='SELECTED — '+cases[i].label}choose(1);</script></html>'''
    (output/'viewer.html').write_text(page)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs',type=Path,nargs='+')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.runs,args.output)
    print(json.dumps(result,indent=2))

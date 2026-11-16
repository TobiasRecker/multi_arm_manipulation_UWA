"""Local review report with strong contrast and explicit action states."""
import html
import json
from pathlib import Path


def preview(directory):
    directory=Path(directory);parts=[]
    escape=lambda value:html.escape(str(value))
    state=json.loads((directory/'state.json').read_text())
    parts.append('<h2>'+escape(state['state'])+' / '+escape(state['phase'])+'</h2>')
    if state.get('error'):parts.append('<p><strong>FAILED: '+escape(state['error'])+'</strong></p>')
    if 'stop' in state:
        parts.append('<p><strong>HOLDS '+('CONFIRMED' if state['stop'].get('confirmed') else 'NOT CONFIRMED')+'</strong></p>')
    review=directory/'review.json'
    if review.exists():
        packet=json.loads(review.read_text());evidence=packet['evidence']
        parts.append('<p>Review revision '+escape(packet['revision'])+' / '+escape(packet['stage'])+'</p>')
        if state['state']=='WAITING_REVIEW':parts.append('<p><strong>ACTION REQUIRED: inspect evidence, then submit the current hash before the 300s deadline.</strong></p><code>'+escape(packet['sha256'])+'</code>')
        if 'observation' in evidence:
            observation=evidence['observation']
            parts.append('<table><tr><th>Image source</th><th>Status</th><th>Inliers</th><th>RMS pixels</th></tr>')
            for view in observation['views']:
                parts.append('<tr>'+''.join('<td>'+escape(view.get(key,'—'))+'</td>' for key in ('arm','status','inliers','reprojection_rms_px'))+'</tr>')
            parts.append('</table><p>Image consensus; absolute accuracy remains unvalidated.</p>')
        if 'trajectory' in evidence:
            parts.append('<p>Candidate: '+escape(evidence['candidate']['id'])+'</p><table><tr><th>Stage</th><th>Duration (s)</th><th>Samples</th></tr>')
            for name in ('trajectory','entry','lift_witness'):
                motion=evidence[name];parts.append('<tr><td>'+escape(name)+'</td><td>'+escape(round(motion['points'][-1]['time'],3))+'</td><td>'+escape(len(motion['points']))+'</td></tr>')
            parts.append('</table><p>Lift witness is geometry only; physical holding is still to be proved.</p>')
        if 'delta_m_rad' in evidence:
            parts.append('<p>Object alignment delta (m, rad): '+escape(evidence['delta_m_rad'])+'</p>')
    for name in ('state.json','review.json','candidate_failures.json','group.json'):
        path=directory/name
        if path.exists():parts.append('<details><summary>'+escape(name)+' — complete evidence</summary><pre>'+escape(json.dumps(json.loads(path.read_text()),indent=2))+'</pre></details>')
    for image in sorted(directory.glob('**/*inspection.jpg')):
        parts.append('<figure><figcaption>'+html.escape(str(image.relative_to(directory)))+'</figcaption><img src="'+html.escape(str(image.relative_to(directory)),quote=True)+'"></figure>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>UWA task review</title><style>body{background:#101820;color:#fff;font:18px system-ui;max-width:1200px;margin:30px auto}pre,code{background:#000;padding:20px;white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%}h1,h2{color:#ffe76b}figure{border:3px solid #fff;padding:12px}td,th{border:2px solid #fff;padding:10px;text-align:left}table{border-collapse:collapse}summary{cursor:pointer;padding:15px;font-weight:bold}</style><h1>UWA task review — SIMULATION</h1>'+''.join(parts)+'</html>'
    path=directory/'review.html';path.write_text(page);return str(path.resolve())

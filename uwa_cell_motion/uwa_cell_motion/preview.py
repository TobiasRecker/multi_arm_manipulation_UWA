"""Standalone HTML preview, no ROS command clients."""
import html
from pathlib import Path
import numpy as np


def render(plan,output):
    if not plan.get('success'):raise ValueError('Only successful plans have a path preview')
    names=plan['trajectory']['joint_names'];points=plan['trajectory']['points']
    q=np.asarray([p['positions'] for p in points]);times=np.asarray([p['time'] for p in points])
    charts=[];colours=['#ffdd55','#55ddff','#ff88cc','#aaff66','#ccbbff','#ffffff']
    for arm in plan['request']['selected']:
        indices=[i for i,n in enumerate(names) if n.startswith(arm+'_')];lines=[];lo=float(q[:,indices].min())-.05;hi=float(q[:,indices].max())+.05
        for k,i in enumerate(indices):
            xy=' '.join(f'{60+850*t/max(times[-1],.01):.2f},{210-170*(v-lo)/(hi-lo):.2f}' for t,v in zip(times,q[:,i]))
            lines.append(f'<polyline points="{xy}" fill="none" stroke="{colours[k%6]}" stroke-width="2"/>')
        legend=' · '.join(f'<span style="color:{colours[k%6]}">{html.escape(names[i].removeprefix(arm+"_"))}</span>' for k,i in enumerate(indices))
        charts.append(f'<h2>{arm}</h2><div>{legend}</div><svg viewBox="0 0 950 240" role="img" aria-label="Joint trajectories in radians">{"".join(lines)}<text x="60" y="235" fill="white">0s</text><text x="840" y="235" fill="white">{times[-1]:.2f}s</text></svg>')
    text=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>UWA PTP preview</title>
<style>body{{background:#10141c;color:#fff;font:18px sans-serif;margin:32px;max-width:1100px}}svg{{width:100%;background:#202938}}h1{{color:#ffdd55}}.label{{border:3px solid white;padding:15px}}</style>
<h1>SIMULATION — PTP preview</h1><p class="label">PLANNED · {html.escape(plan['method'])} · {plan['trajectory']['duration_s']:.2f}s planned · no motion sent</p>
<p>Joint angles in radians. Stop-at-waypoint timing. Model geometry includes provisional cell anchors.</p>{''.join(charts)}</html>'''
    Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(text)

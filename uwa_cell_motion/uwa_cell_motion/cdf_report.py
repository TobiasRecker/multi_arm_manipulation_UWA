"""Standalone evidence page and scientific plots; no ROS or robot actions."""
import html
import json
from pathlib import Path
import numpy as np


def render_report(problem,summary,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from .cdf import ContactBank
    from .cdf_geometry import FrozenScene
    output=Path(output);successful=[r for r in summary['rows'] if r['method']=='cdf' and r['category']=='blocked_direct' and r['success']]
    figure=''
    if successful:
        row=successful[0];plan=json.loads((output/row['record']).read_text());request=plan['request'];scene=FrozenScene(problem,request)
        bank=ContactBank.load(output/f"contacts-{row['seed']}.npz",scene);q=np.asarray(plan['trajectory']['waypoints'])
        from .cdf_animation import render
        render(problem,plan,output/'animation.html')
        fig=plt.figure(figsize=(14,10),layout='constrained');ax=fig.add_subplot(221,projection='3d')
        frozen=problem.spheres.world(request['start'])
        for rid,points in frozen.items():
            if rid!=scene.arm:ax.scatter(*points.T,s=8,alpha=.3,label=rid+' (fixed)')
        centres=scene.forward(q)[0]
        for index,label in [(0,'start'),(len(q)//2,'middle'),(-1,'goal')]:
            ax.scatter(*centres[index].T,s=9,label='moving arm '+label)
        ax.plot(*centres[:,-1,:].T,color='black',lw=2,label='tool control-point path')
        ax.set(xlabel='world x [m]',ylabel='world y [m]',zlabel='world z [m]',title='Sphere centres / frozen full cell (not mesh rendering)');ax.legend(fontsize=7)
        ax=fig.add_subplot(222);lo=q[:,:2].min(axis=0)-.15;hi=q[:,:2].max(axis=0)+.15
        x,y=np.meshgrid(np.linspace(lo[0],hi[0],65),np.linspace(lo[1],hi[1],65));queries=np.tile(q[0],(x.size,1));queries[:,:2]=np.c_[x.ravel(),y.ravel()]
        distance=np.array([bank.query(p)[0] for p in queries]).reshape(x.shape)
        contour=ax.contourf(x,y,distance,20,cmap='viridis');fig.colorbar(contour,ax=ax,label='sampled CDF [rad]')
        ax.plot(q[:,0],q[:,1],'w.-',lw=1);ax.scatter(q[0,0],q[0,1],marker='o',c='red');ax.scatter(q[-1,0],q[-1,1],marker='*',c='red')
        ax.set(xlabel='joint1 [rad]',ylabel='joint2 [rad]',title='CDF slice: joints3–6 fixed at start\nWhite line: projection of actual six-dimensional path')
        ax=fig.add_subplot(223);trace=plan['cdf_trace'];ax.plot([t['cdf_rad'] for t in trace],label='sampled CDF');ax.axhline(1-plan['cdf_settings']['gamma'],color='red',ls='--',label='QP log-buffer threshold')
        ax.set(xlabel='QP step',ylabel='joint-space distance [rad]',title='CDF QP rollout');ax.legend()
        ax=fig.add_subplot(224);points=plan['trajectory']['points'];times=[p['time'] for p in points];positions=np.asarray([p['positions'] for p in points])
        for i in range(6):ax.plot(times,positions[:,i],label=f'joint{i+1}')
        ax.set(xlabel='planned time [s]',ylabel='angle [rad]',title='Validated time-parametrized trajectory');ax.legend(ncol=2)
        fig.savefig(output/'cdf-evidence.png',dpi=150);plt.close(fig);figure='<img src="cdf-evidence.png" alt="Frozen cell, CDF slice, QP trace and joint trajectories">'
    rows=[]
    for row in summary['rows']:
        metrics=row.get('metrics') or {};record=html.escape(row['record']);preview=record.removesuffix('.json')+'.html'
        status='PASS' if row['success'] else 'FAIL: '+str(row['error'])
        rows.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in (row['case_id'],row['seed'],row['method'],status,
            round(row['preparation_time_s'],3),round(row['planning_time_s'],3),round(row['total_offline_time_s'],3),
            metrics.get('planned_duration_s','—'),metrics.get('cdf_constrained_steps','—')))+
            f'<td><a href="{record}">JSON</a>'+ (f' · <a href="{preview}">preview</a>' if row['success'] else '')+'</td></tr>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Single-UR CDF evidence</title>
<style>body{font:17px sans-serif;margin:30px;background:#101722;color:white}a{color:#80dbff}table{border-collapse:collapse;font-size:14px}td,th{padding:9px;border:1px solid #8795aa}img{max-width:100%;background:white}.label{border:3px solid #ffe080;padding:15px}h1{color:#ffe080}</style>
<h1>Single-UR CDF — OFFLINE MODEL CHECK</h1><p class="label">One moving UR; three frozen arms. No Gazebo execution or real motion in this report.</p>
<p>Nonparametric scene-conditioned contact-template CDF + reactive logarithmic-barrier QP.
Full volume sphere/box steering model; full MoveIt/self/tool/table/camera and guard-reserve validation of the timed trajectory.
Finite exact templates can overestimate configuration distance; geometry/contact residuals may err either way. No collision-clearance or completeness guarantee from CDF itself.
No neural training, Franka weights, RRT guidance or fallback. Invalid goals/failures remain in this table.</p>
<p>Preparation is charged separately (and repeated in rows sharing a bank); online planning excludes final time-parameterization/validation.
Total offline includes that validation but excludes contact preparation. Tiny fixed suite is an implementation check, not a reproduction of paper success rates.</p>
<p><a href="https://arxiv.org/abs/2406.01137">Paper</a> · <a href="https://github.com/yimingli1998/cdf/tree/08a725718e748366c5b4da5cbc4c67e991961f0f">Reference code</a> · <a href="summary.json">Full summary</a></p>'''+('<p><a href="animation.html">PLAY / inspect the frozen-cell motion preview</a></p>' if successful else '')+figure+'''
<table><tr><th>Task</th><th>Seed</th><th>Method</th><th>Result</th><th>Bank prep [s]</th><th>Planning [s]</th><th>Total offline [s]</th><th>Planned travel [s]</th><th>CDF-constrained steps</th><th>Records</th></tr>'''+''.join(rows)+'</table></html>'
    (output/'report.html').write_text(page)

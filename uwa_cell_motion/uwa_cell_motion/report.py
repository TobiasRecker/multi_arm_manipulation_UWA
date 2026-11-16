"""Export transparent scientific comparison figures and an offline HTML report."""
import html
import json
from pathlib import Path
import statistics
import os

import numpy as np


def render(directory,output,guard_check=None):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(output.parent/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    directory=Path(directory)
    rows=[]
    for path in sorted(directory.glob('*.json')):
        value=json.loads(path.read_text())
        if isinstance(value,dict) and 'case_id' in value and 'method' in value:rows.append(value)
    summary=json.loads((directory/'summary.json').read_text())
    categories=['free','blocked_direct','neighbor_crossing','four_arm','tool_passage']
    methods=['rrtconnect','circular'];colors=['#2463a4','#d35e00'];labels=['RRTConnect','Circular fields (experimental)']
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for i,method in enumerate(methods):
        values=[sum(r['success'] for r in rows if r['method']==method and r['category']==c) for c in categories]
        bars=axes[0,0].bar(np.arange(5)+i*.35,values,width=.35,color=colors[i],label=labels[i])
        axes[0,0].bar_label(bars,padding=2,fontsize=8)
    axes[0,0].set_xticks(np.arange(5)+.175,[c.replace('_','\n') for c in categories])
    axes[0,0].set_ylabel('Successful plans /25 attempts');axes[0,0].set_ylim(0,27);axes[0,0].legend(fontsize=8)
    groups=[[r['planning_time_s'] for r in rows if r['method']==m and r['category'] in ('blocked_direct','neighbor_crossing')] for m in methods]
    axes[0,1].boxplot(groups,tick_labels=['RRTConnect','Circular fields']);axes[0,1].set_ylabel('Detour planning time [wall seconds]')
    axes[0,1].axhline(10,color='black',ls='--',lw=1,label='10s budget');axes[0,1].legend()
    executions={}
    for r in rows:
        e=r.get('execution')
        if e and e.get('success'):executions[e.get('record',r['case_id'])]=(r,e)
    if executions:
        x=[r['trajectory']['duration_s'] for r,e in executions.values()];y=[e['actual_simulation_s'] for r,e in executions.values()]
        axes[1,0].scatter(x,y,color='#2463a4',s=20)
        maximum=max(x+y);axes[1,0].plot([0,maximum],[0,maximum],'k--',lw=1)
        axes[1,0].set_xlabel('Planned duration [simulation seconds]');axes[1,0].set_ylabel('Measured duration [simulation seconds]')
        axes[1,0].set_title(f'{len(executions)} unique successful executions')
    else:axes[1,0].text(.1,.5,'Execution evidence pending',transform=axes[1,0].transAxes)
    if guard_check:
        guard=json.loads(Path(guard_check).read_text())
        values=[1000*guard['pair_fault_to_standstill_s'],1000*guard['guard_loss_hold_latency_s']]
        axes[1,1].bar(['Injected distance fault\nto arm speed threshold','Missing guard\nto resource hold'],values,color=['#2463a4','#d35e00'])
        axes[1,1].set_ylabel('Measured wall latency [ms]');axes[1,1].set_title('Different stop triggers — normal simulation rate')
    else:axes[1,1].axis('off')
    fig.suptitle('UWA four-arm simulation study — provisional cell geometry',fontsize=15)
    figure=output.with_suffix('.png');fig.savefig(figure,dpi=160);plt.close(fig)
    table=[]
    for category in categories+['unreachable']:
        cells=[]
        for method in methods:
            selected=[r for r in rows if r['method']==method and r['category']==category]
            successes=[r for r in selected if r['success']]
            timing=statistics.median(r['planning_time_s'] for r in selected) if selected else 0
            duration=statistics.median(r['trajectory']['duration_s'] for r in successes) if successes else None
            cells.append(f'<td>{len(successes)}/{len(selected)}</td><td>{timing:.3f}</td><td>{duration:.2f}</td>' if duration is not None else
                         f'<td>{len(successes)}/{len(selected)}</td><td>{timing:.3f}</td><td>—</td>')
        table.append('<tr><th>'+category+'</th>'+''.join(cells)+'</tr>')
    execution=summary.get('execution_summary',{})
    metric_rows=[]
    for method in methods:
        successful=[r for r in rows if r['method']==method and r['success']]
        length=f"{statistics.median(r['metrics']['joint_path_length_rad'] for r in successful):.4f}" if successful else '—'
        clearance=f"{1000*min(r['metrics']['minimum_sphere_clearance_m'] for r in successful):.1f}" if successful else '—'
        stops=sum(r.get('execution',{}).get('guard_stops',0) for r in rows if r['method']==method)
        metric_rows.append(f'<tr><th>{method}</th><td>{length}</td><td>{clearance}</td><td>{stops}</td></tr>')
    attempts=[]
    roots=[directory/'executions']+sorted(directory.glob('execution-history-*'))
    for path in sorted(path for root in roots for path in root.rglob('*.json')):
        value=json.loads(path.read_text())
        if 'phase_count' in value and 'guard_stops' in value:
            attempts.append(dict(record=str(path.relative_to(directory)),success=value['success'],
                stage=value.get('stage'),error=value.get('error'),stopped_arms=value.get('stopped_arms',[])))
    history=output.with_suffix('.attempts.json');history.write_text(json.dumps(attempts,indent=2)+'\n')
    failures=[a for a in attempts if not a['success']]
    failure_rows=''.join('<li>'+html.escape(a['record'])+': '+html.escape(str(a['stage']))+' — '+html.escape(str(a['error'] or a['stopped_arms']))+'</li>' for a in failures)
    canonical=[]
    for path in sorted((directory/'executions').glob('*.json')):
        value=json.loads(path.read_text())
        if not value.get('success',False):canonical.append(dict(record=path.name,stage=value.get('stage'),
            error=value.get('error') or value.get('post_review',{}).get('reason') or str(value.get('stopped_arms',[]))))
    final_failure_rows=''.join('<li>'+html.escape(a['record'])+': '+html.escape(str(a['stage']))+' — '+html.escape(str(a['error']))+'</li>' for a in canonical)
    badges=f"OFFLINE {'COMPLETE' if summary.get('complete') else 'INCOMPLETE'} · EXECUTION ATTEMPTS {'COMPLETE' if execution.get('complete') else 'INCOMPLETE'} · {execution.get('successes_unique',0)}/{execution.get('unique_trajectories',0)} UNIQUE ROUTES SUCCEEDED"
    document=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>UWA simulation study</title>
<style>body{{background:#10141c;color:white;font:17px system-ui;max-width:1200px;margin:32px auto;padding:20px}}h1,.status{{color:#ffdf55}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #aab7c8;padding:9px;text-align:left}}img{{width:100%;background:white}}a{{color:#8edaff}}.status{{border:3px solid white;padding:16px}}</style>
<h1>Four-arm collision guard and PTP comparison</h1><p class="status">{badges}</p>
<p>30 fixed tasks ×5 seeds ×2 methods.10s wall planning budget. Invalid targets and timeouts remain failures. Unreachable controls are intentionally outside joint limits.</p>
<p>Neighbor crossings are verified intersections of conservative sphere paths; mesh contact is recorded separately. RRTConnect and circular fields share direct-connection checks, a fixed-order waiting coordinator, operating bounds and final full-cell MoveIt/FCL validation. The circular baseline never invokes RRT. Native RRT process startup counts toward planning time.</p>
<img alt="Planning and execution comparison" src="{html.escape(figure.name)}">
<table><thead><tr><th>Task category</th><th>RRT success</th><th>Plan [s]</th><th>Duration [sim s]</th><th>CF success</th><th>Plan [s]</th><th>Duration [sim s]</th></tr></thead><tbody>{''.join(table)}</tbody></table>
<p>Duration medians use successful plans only; planning medians include failures. Start repositioning is checked separately and excluded from measured task duration. Identical timed trajectories share a linked execution record; physical executions and planning trials are counted separately.</p>
<table><thead><tr><th>Method</th><th>Median joint path length [rad]</th><th>Minimum checked neighbor sphere clearance [mm]</th><th>Guard-triggered arm stops in linked final trials</th></tr></thead><tbody>{''.join(metric_rows)}</tbody></table>
<p>Clearance is between conservative neighbor sphere surfaces, distinct from full-cell mesh validity. All individual metrics and diagnostics remain in the trial JSON files. Image rendering is disabled for the coherent Gazebo replay; camera collision bodies, inertias and TF are unchanged. Single-arm execution follows the complete checked trajectory; multiarm execution uses independent-progress phases and measured barriers, including their waiting time in measured duration.</p>
<p>Execution status: {html.escape(json.dumps(execution))}</p>
<p>Completion means that each unique route has an execution attempt, not that every execution succeeded. PREPARATION failures stopped before the target trajectory began. Final unsuccessful records: {len(canonical)}.</p><ul>{final_failure_rows}</ul>
<p>The gripper simulation can report open-stop velocity chatter. Tool rest uses a10µrad position-span test over300ms plus the unchanged operating velocity cap; arms retain3mrad/s. Actual excursions above0.05rad/s are execution failures and are stopped. No collision or source-freshness limit is relaxed for these failures. Runtime revisions and their evidence are recorded in <a href="runtime-manifest.json">the runtime manifest</a>.</p>
<p>The plotted distance-fault latency ends at the first measured arm-speed sample below the rest threshold. The production STOPPED state additionally requires the measured300ms history; resource ownership alone is insufficient. These observations do not establish a guaranteed worst-case stop time.</p>
<p>All retained execution attempts, including development versions, changed experimental conditions and operator interruptions: {len(attempts)} attempts, {len(failures)} unsuccessful. These are separate from the final unique-trajectory coverage. <a href="{html.escape(history.name)}">Complete attempt history</a>.</p><ul>{failure_rows}</ul>
<p>This is a simulation research comparison with provisional model anchors, approximated tool geometry and discrete mesh checks. It is not a hardware safety validation or evidence of a generally superior planner.</p></html>'''
    output.write_text(document)

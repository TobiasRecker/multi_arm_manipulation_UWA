#!/usr/bin/env python3
"""Compare matched contact-force windows of a recorded vertical lift, no commands."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from uwa_cell_tasks.core import verify,seal,write_json,object_point_height
from uwa_cell_tasks.force_metrics import pad_load_window


def read(path):return json.loads(path.read_text())


def extract(run,scene_dir):
    scene=verify(read(scene_dir/'scene.json'));motion=verify(read(run/'object-lift.json'))
    rows=[json.loads(line) for line in (run/'evaluation-trace.jsonl').open()]
    loaded=[r for r in rows if r.get('group') and not r['group'].get('released')]
    if not loaded:raise ValueError('No independently observed grasp group')
    reference=scene['lift_reference_point_object_m'];base=loaded[0]['object']['T_world_object']
    height0=object_point_height(base,reference)
    target=read(run/'object-targets.json')['lift_m']
    joint='right_front_wrist_1_joint';j=motion['joint_names'].index(joint)
    times=np.array([p['time'] for p in motion['points']]);q=np.array([p['positions'][j] for p in motion['points']])
    if not (np.all(np.diff(q)>=-1e-9) or np.all(np.diff(q)<=1e-9)):
        raise ValueError('Selected lift clock joint is not monotone')
    if q[-1]<q[0]:q=q[::-1];times=times[::-1]
    fit=[]
    for r in loaded:
        progress=(object_point_height(r['object']['T_world_object'],reference)-height0)/target
        if r['phase']=='move_object' and not r['faults'] and .1<progress<.9:
            fit.append(r['joints']['stamp']-np.interp(r['joints']['positions'][joint],q,times))
    if len(fit)<5:raise ValueError('Insufficient moving samples to align source clock')
    origin=float(np.median(fit));spread=float(np.quantile(fit,.95)-np.quantile(fit,.05))
    if spread>.005:raise ValueError('Source-clock fit inconsistent: possible native clipping or tracking error (>5ms)')
    end=origin+motion['duration_s']
    faults=[r['object']['stamp'] for r in rows if r['faults'] and r['object']['stamp']>=origin]
    if faults:end=min(end,min(faults))
    losses=[r['contacts']['stamp'] for r in rows if r.get('group') and
        r['contacts']['stamp']>=origin and not all(all(p.values()) for p in r['contacts']['pads'].values())]
    first_loss=min(losses) if losses else None
    if first_loss is not None:end=min(end,first_loss-.01)  # keep full10ms windows before first loss
    t=np.array([r['object']['stamp'] for r in rows]);progress=np.array([
        (object_point_height(r['object']['T_world_object'],reference)-height0)/target for r in rows])
    selected=[];previous=None;gaps=[]
    force_path=run/'force-trace.jsonl'
    for line in force_path.open():
        r=json.loads(line);f=r['forces'];stamp=f['stamp']
        if not origin<stamp<=end:continue
        if previous is not None and abs(stamp-previous-f['window_duration_s'])>1e-5:gaps.append([previous,stamp])
        previous=stamp
        pads=pad_load_window(f,scene['cfg']['pad_load_reference_n'])
        if not pads['usable']:raise ValueError('Invalid force window in moving interval')
        if any(v['contact_pairs']==0 for v in pads['pads'].values()):
            first_loss=stamp if first_loss is None else min(first_loss,stamp)
            end=min(end,stamp-f['window_duration_s']);break
        selected.append(dict(stamp=stamp,time_s=stamp-origin,progress=float(np.interp(stamp,t,progress)),pads=pads['pads']))
    selected=[r for r in selected if r['stamp']<=end]
    if not selected:raise ValueError('No native force windows in actual lift')
    return dict(run=str(run.resolve()),scene_sha256=scene['sha256'],cfg=scene['cfg'],scene=scene,
        motion_sha256=motion['sha256'],duration_commanded_s=motion['duration_s'],target_lift_m=target,
        source_start_s=origin,source_end_s=end,clock_fit_90pct_spread_s=spread,
        windows=len(selected),gap_intervals=gaps,force_trace_sha256=hashlib.sha256(force_path.read_bytes()).hexdigest(),
        maximum_lift_observed_m=float(max(progress)*target),
        first_contact_loss_sim_s=first_loss,
        lift_at_first_contact_loss_m=float(np.interp(first_loss,t,progress)*target) if first_loss is not None else None,
        motion_samples=[dict(progress=float(prog),velocities=r['joints']['velocities']) for r,prog in zip(rows,progress)
            if origin<=r['joints']['stamp']<=end and not r['faults']],rows=selected,measured_joint_velocity_peaks_rad_s={n:max(abs(r['joints']['velocities'][n]) for r in rows if origin<=r['joints']['stamp']<=end) for n in motion['joint_names']})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--fast',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Use a fresh output directory')
    a.output.mkdir(parents=True)
    data=[extract(run,run.parent/'scene') for run in (a.baseline,a.fast)]
    # These model/controller properties must be identical; guard envelopes may differ.
    keys=['mass_kg','friction','wall_thickness_m','finger_joint_damping_nm_s','gripper_gear_stiffness_nm_rad',
          'gripper_motor_stiffness_nm_rad','gripper_motor_torque_limit_nm','physics_step_s',
          'gripper_coarse_velocity_rad_s','gripper_fine_velocity_rad_s','gripper_fine_start_rad']
    same={k:data[0]['cfg'][k]==data[1]['cfg'][k] for k in keys}
    binaries={k:data[0]['scene'][k]==data[1]['scene'][k] for k in ['backend_sha256','physics_engine_sha256','force_backend_sha256']}
    from uwa_cell_control.parallel_scan import collision_signature
    signatures=[collision_signature((Path(d['run']).parent/'scene/robot.urdf').read_text()) for d in data]
    geometry_same=(signatures[0]==signatures[1] and
        data[0]['scene']['asset_manifest_sha256']==data[1]['scene']['asset_manifest_sha256'])
    extent=min(1.,*(max(r['progress'] for r in d['rows']) for d in data))
    pads={}
    for d in data:
        d['measured_joint_velocity_peaks_common_rad_s']={n:max(abs(r['velocities'][n]) for r in d['motion_samples'] if 0<=r['progress']<=extent) for n in d['measured_joint_velocity_peaks_rad_s']}
    for pad in data[0]['rows'][0]['pads']:
        metrics=[]
        for d in data:
            rows=[r for r in d['rows'] if 0<=r['progress']<=extent]
            means=np.array([r['pads'][pad]['mean_load_upper_bound_n'] for r in rows]);peaks=np.array([r['pads'][pad]['peak_load_upper_bound_n'] for r in rows])
            metrics.append(dict(max_10ms_mean_upper_n=float(means.max()),max_physics_peak_upper_n=float(peaks.max()),
                time_mean_upper_n=float(means.mean()),p95_10ms_mean_upper_n=float(np.quantile(means,.95)),windows=len(rows)))
        pads[pad]=dict(baseline=metrics[0],fivefold=metrics[1],
            mean_peak_ratio=metrics[1]['max_10ms_mean_upper_n']/metrics[0]['max_10ms_mean_upper_n'],
            physics_peak_ratio=metrics[1]['max_physics_peak_upper_n']/metrics[0]['max_physics_peak_upper_n'])
    clean=[{k:v for k,v in d.items() if k not in ('rows','scene','motion_samples')} for d in data]
    result=seal(dict(kind='matched_vertical_prefix_contact_force_comparison',
        scope='Vertical lift only, not the90degree rotation or the return descent',
        same_physics_properties=same,same_native_binaries=binaries,same_collision_kinematics=geometry_same,controlled_physics=all(same.values()) and all(binaries.values()) and geometry_same,
        commanded_speed_ratio=data[0]['duration_commanded_s']/data[1]['duration_commanded_s'],
        common_lift_progress_fraction=extent,force_coverage_complete=all(not d['gap_intervals'] for d in data),
        runs=clean,pads=pads,hardware_or_material_qualification=False,
        caveats=['Single historical1x lift versus new5x trial; no repeat statistics',
            'Per-jaw magnitudes and noncoincident peak upper bounds, not signed net object force',
            '10ms filter and physics-step peak resolution unchanged; rigid carton cannot crush'],
        comparison_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    write_json(a.output/'result.json',result)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
    for ax,pad in zip(axes.flat,pads):
        for d,label,color in zip(data,['1x recorded baseline','5x contact simulation'],['#185fa5','#c74a19']):
            rows=[r for r in d['rows'] if 0<=r['progress']<=extent]
            ax.plot([r['progress']*100 for r in rows],[r['pads'][pad]['mean_load_upper_bound_n'] for r in rows],label=label,color=color,lw=1)
        ax.set_title(pad);ax.grid(alpha=.3);ax.set_xlabel('Measured lift progress (%)');ax.set_ylabel('Per-jaw 10 ms load upper bound (N)')
    axes[0,0].legend();fig.suptitle('Same vertical lift:1x versus5x — measured contact loads, no rotation qualification')
    fig.tight_layout();fig.savefig(a.output/'forces.png',dpi=160);plt.close(fig)
    print(json.dumps(dict(commanded_speed_ratio=result['commanded_speed_ratio'],common_fraction=extent,pads=pads),indent=2))


if __name__=='__main__':main()

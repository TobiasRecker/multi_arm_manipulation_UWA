#!/usr/bin/env python3
"""Check goal handovers and render complete offline teacher episodes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import itertools
import hashlib
import shutil


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);args=parser.parse_args()
    out=args.directory.resolve();manifest=json.loads((out/'manifest.json').read_text());parent=Path(manifest['parent_path'])
    if os.environ.get('UWA_EPISODE_FROZEN')!='1':
        revision=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        reviewer=out/'review-code'/revision/Path(__file__).name
        reviewer.parent.mkdir(parents=True,exist_ok=True)
        if not reviewer.exists():shutil.copy2(__file__,reviewer)
        frozen=parent/'frozen-source';env=dict(os.environ,UWA_EPISODE_FROZEN='1',UWA_TEACHER_FROZEN='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        env['UWA_EPISODE_BASE_TOOLS']=str(frozen/'tools')
        env['PYTHONPATH']=os.pathsep.join([str(out/'code'),str(frozen/'tools')]+[str(frozen/p) for p in ['uwa_cell_motion','uwa_cell_calibration','uwa_cell_control','uwa_cell_description','uwa_cell_gazebo']]+[env.get('PYTHONPATH','')])
        return subprocess.call([sys.executable,str(reviewer),str(out)],env=env)
    import numpy as np
    from scipy.spatial.transform import Rotation
    from teacher_episode_core import EpisodeTeacher
    from generate_diverse_teacher_dataset import diverse_bindings
    from generate_teacher_dataset import sha
    from uwa_cell_motion.teacher_dataset import atomic_json,digest,transitions
    from uwa_cell_motion.common import ROBOT_IDS
    from uwa_cell_motion.two_arm_teacher import pose_at
    from uwa_cell_motion.smooth_paths import sample_segment
    for name,expected in manifest['code_sha256'].items():
        if sha(out/'code'/name)!=expected:raise ValueError('Generation source hash mismatch: '+name)
    reports=[json.loads(p.read_text()) for p in sorted((out/'episodes').glob('*.json'))]
    checks=[];sets=[]
    with tempfile.TemporaryDirectory(prefix='uwa-episode-review-') as directory:
        p=EpisodeTeacher(directory,Path(manifest['bindings']['source_path']))
        if diverse_bindings(p,p.source)!=manifest['bindings']:raise ValueError('Model binding mismatch')
        for r in reports:
            if r['manifest_sha256']!=digest(manifest):raise ValueError('Episode manifest mismatch')
            steps=r['steps'];errors=[];positions=[];angles=0.;handover=0.;duration=0.;previous=None
            if not steps:checks.append(dict(id=r['id'],passed=False,reason='No accepted goals'));continue
            for step in steps:
                if not step['validation']['passed']:errors.append('Invalid stored trajectory')
                if sha(out/step['records_path'])!=step['records_sha256']:errors.append('Export hash mismatch')
                initial=np.array(step['initial_pose']);records=transitions(initial,step['trajectory'])
                with np.load(out/step['records_path'],allow_pickle=False) as stored:
                    for key in records:
                        key_saved='goal_terminal' if key=='terminal' else key
                        if not np.allclose(stored[key_saved],records[key],atol=1e-12,rtol=0):errors.append('BC export mismatch')
                names=p.names
                if previous is not None:
                    jump=max(abs(previous['end_state'][n]-step['initial_state'][n]) for n in previous['end_state'])
                    jump=max(jump,float(np.max(abs(np.array(previous['end_pose'])-initial))));handover=max(handover,jump)
                    if jump>1e-10:errors.append('State reset at goal switch')
                p.initial=initial;p.start=dict(step['initial_state']);end,state,_=p.sample(step['trajectory'],step['duration_s'])
                if np.max(abs(end-np.array(step['end_pose'])))>1e-10:errors.append('Stored endpoint pose mismatch')
                if max(abs(state[n]-step['end_state'][n]) for n in state)>1e-10:errors.append('Stored endpoint state mismatch')
                for derivative in (1,2,3):
                    if np.max(abs(sample_segment(step['trajectory']['segment'],[0,step['duration_s']],derivative)))>1e-8:errors.append('Nonzero goal-switch derivative')
                poses=np.concatenate([records['object_pose'],records['object_pose_next'][-1:]])
                positions.extend(poses[:,:3,3].tolist())
                angles+=sum(Rotation.from_matrix(b[:3,:3]@a[:3,:3].T).magnitude() for a,b in zip(poses[:-1],poses[1:]))
                duration+=step['duration_s'];previous=step
            positions=np.array(positions);length=float(np.linalg.norm(np.diff(positions,axis=0),axis=1).sum())
            checks.append(dict(id=r['id'],passed=not errors,errors=sorted(set(errors)),goals=len(steps),duration_s=duration,
                object_path_length_m=length,angular_path_deg=float(np.rad2deg(angles)),handover_max_error=handover,
                workspace_span_xyz_m=np.ptp(positions,axis=0).tolist(),
                max_radius_from_original_anchor_m=float(np.linalg.norm(positions-np.array(manifest['anchor_pose'])[:3,3],axis=1).max()),
                min_arm_gap_m=min(s['validation']['min_pair_gap_m'] for s in steps),
                min_arm_table_gap_m=min(s['validation']['min_arm_table_gap_m'] for s in steps),
                fcl_reference_legs=sum(s['reference_screen']['fcl_collision_samples']>0 for s in steps),
                near_reference_legs=sum(s['reference_screen']['category']=='near' for s in steps),
                free_reference_legs=sum(s['reference_screen']['category']=='free' for s in steps)))
            ends=np.cumsum([s['duration_s'] for s in steps]);frames=[]
            for t in np.linspace(0,duration,241):
                index=min(int(np.searchsorted(ends,t,side='right')),len(steps)-1);step=steps[index]
                local=float(np.clip(t-(ends[index-1] if index else 0),0,step['duration_s']))
                p.initial=np.array(step['initial_pose']);p.start=dict(step['initial_state'])
                pose,state,s=p.sample(step['trajectory'],local);ref=pose_at(p.initial,step['task'],s,np.zeros((6,6)))
                goal=pose_at(p.initial,step['task'],1,np.zeros((6,6)))
                pairs=p.distances(pose,state)
                frames.append(dict(time_s=float(t),s=float(t/duration),goal_index=index+1,goal_count=len(steps),goal_centre=goal[:3,3].tolist(),
                    object_origin=p.object_origin(pose).tolist(),reference_origin=p.object_origin(ref).tolist(),centre=pose[:3,3].tolist(),reference_centre=ref[:3,3].tolist(),
                    rotation_vector_deg=np.rad2deg(Rotation.from_matrix(pose[:3,:3]@np.array(r['initial_pose'])[:3,:3].T).as_rotvec()).tolist(),
                    world={a:v.round(6).tolist() for a,v in p.problem.spheres.world(state).items()},fcl_clear=p.full_check(pose,state),
                    object_box_gap_mm=1000*float(p.environment_gaps(pose).min()),object_arm_gap_mm=1000*float(p.object_arm_gaps(pose,state).min()),
                    arm_table_gap_mm=1000*float(p.arm_table_gaps(pose,state).min()),gaps=[dict(arms=x['arms'],gap_mm=1000*x['clearance_m']) for x in pairs]))
            v=dict(steps[0]['validation']);v.update(passed=not errors and all(s['validation']['passed'] for s in steps),
                samples=sum(s['validation']['samples'] for s in steps),failures=[],max_time_step_s=max(s['validation']['max_time_step_s'] for s in steps),
                min_pair_gap_m=min(s['validation']['min_pair_gap_m'] for s in steps),min_scaled_sigma=min(s['validation']['min_scaled_sigma'] for s in steps),
                max_closure_position_m=max(s['validation']['max_closure_position_m'] for s in steps),
                max_position_deviation_m=max(s['validation']['max_position_deviation_m'] for s in steps),
                max_orientation_deviation_deg=max(s['validation']['max_orientation_deviation_deg'] for s in steps),
                bounds={k:max(s['validation']['bounds'][k] for s in steps) for k in v['bounds']})
            for key in ('min_object_box_gap_m','min_object_arm_gap_m','min_arm_table_gap_m'):
                v[key]=min(s['validation'][key] for s in steps)
            v['max_closure_angle_rad']=max(s['validation']['max_closure_angle_rad'] for s in steps)
            sets.append(dict(case_id=r['id'],label=f"{r['id']} — {len(steps)} goals / {length:.2f} m",variant='Teacher',duration_s=duration,validation=v,frames=frames))
        boxes=[]
        for _,T,half in p.environment_boxes:
            corners=np.array(list(itertools.product(*[[-h,h] for h in half])));boxes.append((corners@T[:3,:3].T+T[:3,3]).tolist())
        data=dict(arms=list(ROBOT_IDS),active_arms=list(p.arms),boxes=boxes,triangles=p.triangles.tolist(),radii={a:v.tolist() for a,v in p.problem.spheres.radii.items()},sets=sets,
            summary=[dict(name=r['id'],status=r['status'],accepted=bool(r['steps']),reason=None) for r in reports])
    audit=dict(passed=bool(checks) and all(c['passed'] for c in checks),episodes=checks,manifest_sha256=digest(manifest),reviewer_sha256=sha(Path(__file__)))
    atomic_json(out/'episode-audit.json',audit)
    if not sets:raise ValueError('No validated episode to render')
    template=(parent/'frozen-source/tools/preview_two_arm_teacher.html').read_text()
    template=template.replace('Two arms — One object-space teacher','Continuous-state episodes — A new goal after arrival')
    template=template.replace('Compare the requested reference with a corrected object path; all carrying joints share one clock.',
        'Each new goal starts from the previous checked endpoint. No pose resets or branch changes. Both carrying arms stop together at each goal.')
    template=template.replace('A red reference is an intentionally retained failed example.','Only accepted episode segments are shown. Rejected proposals are retained in the episode reports.')
    template=template.replace('World-axis rotation vector [deg]:','Rotation from episode start [deg]:')
    template=template.replace('Start and goal fixed.','Every segment start and goal fixed.')
    template=template.replace('path progress','episode time')
    template=template.replace('Two rotation examples return to their initial pose; the transfer example has a different target.',
        'Each episode chains six spatial goals with mixed translation and rotation; the current goal is shown above.')
    template=template.replace('clear=f.fcl_clear&&','clear=f.arm_table_gap_mm>=3-1e-5&&f.fcl_clear&&')
    template=template.replace('The initial carton centre is 8 cm above the previous tabletop configuration; establishing this pose is not a validated pickup.',
        'The initial configurations come from the offline start bank; establishing them is not a validated pickup. Distal arm/table sphere-box clearances are included in planning and dense validation (3 mm required).')
    script="\nconst oldRefresh=refresh;refresh=()=>{oldRefresh();const f=frame();$('clock').textContent+=' — GOAL '+f.goal_index+' / '+f.goal_count;$('state').textContent+=' Current goal centre [m]: '+f.goal_centre.map(x=>x.toFixed(3)).join(', ')+'. Arm/table gap: '+f.arm_table_gap_mm.toFixed(1)+' mm.';};window.onresize=refresh;refresh();\n"
    (out/'viewer.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')).replace('</script></html>',script+'</script></html>'))
    print('AUDIT',json.dumps(audit),flush=True);return 0 if audit['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

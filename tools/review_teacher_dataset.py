#!/usr/bin/env python3
"""Audit exported BC labels and render a self-contained accepted-path gallery."""
import argparse
import itertools
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation

from generate_teacher_dataset import bindings,load_completed,sha
from plan_two_arm_teacher import preview
from uwa_cell_motion.common import ROBOT_IDS
from uwa_cell_motion.smooth_paths import curve,sample_segment
from uwa_cell_motion.teacher_dataset import HORIZONS,atomic_json,digest
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher,pose_at


def audit_case(out,result):
    """Independently assemble observation/action expectations from raw poses."""
    initial=np.array(result['initial_pose']);trajectory=result['trajectory'];task=trajectory['task']
    with np.load(out/result['records_path'],allow_pickle=False) as loaded:
        records={k:loaded[k] for k in loaded.files}
    errors=[]
    def check(condition,label):
        if not condition:errors.append(label)
    check(all(np.isfinite(a).all() for a in records.values()),'finite arrays')
    check(records['observations'].shape==(100,52),'observation shape')
    check(records['actions'].shape==(100,6),'action shape')
    expected_progress=np.arange(100)/100
    check(np.allclose(records['progress'],expected_progress,atol=1e-14),'progress')
    check(np.allclose(records['next_progress'],expected_progress+.01,atol=1e-14),'next progress')
    check(np.array_equal(records['terminal'],np.arange(100)==99),'terminal')
    spline=curve(trajectory['segment']);goal=pose_at(initial,task,1,np.zeros((6,6)))
    max_label_error=0.
    for i,s in enumerate(expected_progress):
        current=records['object_pose'][i];nxt=records['object_pose_next'][i];action=records['actions'][i]
        expected=pose_at(initial,task,float(s),trajectory['controls'])
        expected_next=pose_at(initial,task,float(s+.01),trajectory['controls'])
        check(np.allclose(current,expected,atol=1e-12),'current pose')
        check(np.allclose(nxt,expected_next,atol=1e-12),'next pose')
        predicted=current.copy();predicted[:3,3]+=action[:3]
        predicted[:3,:3]=Rotation.from_rotvec(action[3:]).as_matrix()@current[:3,:3]
        label_error=float(np.max(abs(predicted-nxt)));max_label_error=max(max_label_error,label_error)
        check(label_error<1e-12,'action composition')
        check(np.allclose(records['q'][i],spline(s),atol=1e-12),'joint interpolation')
        check(np.allclose(records['q_next'][i],spline(s+.01),atol=1e-12),'next joint interpolation')
        def delta(target):
            return np.r_[target[:3,3]-current[:3,3],
                         Rotation.from_matrix(target[:3,:3]@current[:3,:3].T).as_rotvec()]
        lookahead=np.concatenate([delta(pose_at(initial,task,min(1,float(s+h)),np.zeros((6,6)))) for h in HORIZONS])
        obs=np.r_[spline(s),current[:3,3],current[:3,0],current[:3,1],delta(goal),s,lookahead]
        check(np.allclose(records['observations'][i],obs,atol=1e-12),'reference-only observation')
    times=np.linspace(0,trajectory['duration_s'],20001)
    peaks=[float(np.max(abs(sample_segment(trajectory['segment'],times,d)))) for d in (1,2,3)]
    check(np.all(np.array(peaks)<=np.array([.45,.4,2])+1e-7),'dense derivative caps')
    return dict(id=result['case']['id'],passed=not errors,errors=sorted(set(errors)),
        result_sha256=sha(out/'cases'/f"{result['case']['id']}.json"),
        records_sha256=result['records_sha256'],max_action_reconstruction_error=max_label_error,
        derivative_samples=20001,sampled_joint_derivative_peaks=peaks)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    args=parser.parse_args();out=args.directory.resolve();manifest=json.loads((out/'manifest.json').read_text())
    results=load_completed(out,manifest)
    if len(results)!=len(manifest['cases']):raise ValueError('Batch incomplete')
    family_splits={}
    for c in manifest['cases']:
        if c['family'] in family_splits and family_splits[c['family']]!=c['split']:
            raise ValueError('Family leakage')
        family_splits[c['family']]=c['split']
    accepted=[results[c['id']] for c in manifest['cases'] if results[c['id']]['status']=='VALIDATED']
    if not accepted:raise ValueError('No accepted trajectories to review')
    checks=[audit_case(out,r) for r in accepted]
    report=dict(passed=all(c['passed'] for c in checks),manifest_sha256=digest(manifest),
                review_code_sha256=sha(Path(__file__)),
                accepted=len(accepted),transitions=sum(r['transitions'] for r in accepted),
                families=len(family_splits),cases=checks,
                scope='Independent BC label assembly and dense derivative sampling; geometry acceptance from recorded teacher checks')
    report['metrics']=dict(
        time_validation_samples=sum(r['validation']['samples'] for r in accepted),
        progress_validation_samples=sum(r['export_validation']['samples'] for r in accepted),
        trajectory_duration_s=sum(r['trajectory']['duration_s'] for r in accepted),
        min_pair_gap_m=min(r['validation']['min_pair_gap_m'] for r in accepted),
        min_object_box_gap_m=min(r['validation']['min_object_box_gap_m'] for r in accepted),
        min_object_arm_gap_m=min(r['validation']['min_object_arm_gap_m'] for r in accepted),
        max_closure_position_m=max(r['validation']['max_closure_position_m'] for r in accepted),
        max_closure_angle_rad=max(r['validation']['max_closure_angle_rad'] for r in accepted))
    report['empty_accepted_groups']=[dict(category=category,split=split)
        for category in ('translation3d','rotation3d','mixed6d') for split in ('train','validation','test')
        if not any(r['case']['category']==category and r['case']['split']==split for r in accepted)]
    atomic_json(out/'export-audit.json',report)
    if not report['passed']:raise ValueError('BC export audit failed')
    sets=[]
    with tempfile.TemporaryDirectory(prefix='uwa-bc-gallery-') as directory:
        p=TwoArmTeacher(directory,Path(manifest['bindings']['source_path']))
        if bindings(p,Path(p.source))!=manifest['bindings']:raise ValueError('Current source/code/model differs from dataset')
        for result in accepted:
            p.initial=np.array(result['initial_pose']);p.start=dict(result['initial_state'])
            trajectory=result['trajectory'];case=result['case']
            sets.append(dict(case_id=case['id'],label=f"{case['id']} [{case['split']}]",variant='Teacher',
                duration_s=trajectory['duration_s'],validation=result['validation'],frames=preview(p,trajectory)))
            print('PREVIEW',case['id'],flush=True)
        boxes=[]
        for _,T,half in p.environment_boxes:
            corners=np.array(list(itertools.product(*[[-h,h] for h in half])))
            boxes.append((corners@T[:3,:3].T+T[:3,3]).tolist())
        data=dict(arms=list(ROBOT_IDS),active_arms=list(p.arms),boxes=boxes,triangles=p.triangles.tolist(),
            radii={a:v.tolist() for a,v in p.problem.spheres.radii.items()},sets=sets,
            summary=[dict(name=c['id'],status=results[c['id']]['status'],
                accepted=results[c['id']]['status']=='VALIDATED',
                reason=results[c['id']].get('reason') or results[c['id']].get('reference_check',{}).get('reason')) for c in manifest['cases']])
    template=Path(__file__).with_name('preview_two_arm_teacher.html').read_text()
    template=template.replace('Two arms — One object-space teacher','BC teacher — 3D and 6D trajectory families')
    template=template.replace('<table id="comparison"></table>',
        f'<p><strong>{len(accepted)} accepted / {len(results)} attempted trajectories. '
        f'{report["transitions"]} geometric BC transitions. Family-level train / validation / test split.</strong> '
        'Choose translation3d, rotation3d or mixed6d below. These labels describe the reference; corrections may use all six axes.</p>'
        '<details><summary>Show all trajectory checks</summary><table id="comparison"></table></details>')
    template=template.replace('A red reference is an intentionally retained failed example.',
        'The animation shows accepted teacher paths; dashed outlines show their requested references. Rejected tasks remain listed.')
    (out/'viewer.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
    print('AUDIT',report['passed'],'ACCEPTED',len(accepted),'VIEWER',out/'viewer.html',flush=True)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Audit a diverse-start dataset using its frozen Python environment."""
import argparse
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def annotate_starts(out):
    """Keep start orientation explicit even when playback begins at delta=0."""
    manifest=json.loads((out/'manifest.json').read_text());families={f['id']:f for f in manifest['families']}
    descriptions={}
    for case in manifest['cases']:
        result=json.loads((out/'cases'/f"{case['id']}.json").read_text())
        if result['status']!='VALIDATED':continue
        centre=[round(row[3],3) for row in result['initial_pose'][:3]]
        rotation=families[case['family']]['rotation_vector_deg']
        descriptions[case['id']]=f' Initial centre [m]: {centre}. Initial rotation from original anchor [deg]: {rotation}.'
    path=out/'viewer.html';html=path.read_text()
    html=html.replace('World-axis rotation vector [deg]:','Rotation from selected start, world-axis vector [deg]:')
    script='\nconst initialDescriptions='+json.dumps(descriptions)+';\n'
    factors={c['id']:c['rotation_excursion_factor'] for c in manifest['cases'] if 'rotation_excursion_factor' in c}
    script+='const challengeFactors='+json.dumps(factors)+';\n'
    script+="data.sets.forEach((s,i)=>{if(challengeFactors[s.case_id]){s.label+=' / rotation excursion ×'+challengeFactors[s.case_id];$('solution').options[i].textContent=s.label;$('comparison').rows[i+1].cells[0].textContent=s.label;}});\n"
    script+="const originalRefresh=refresh;refresh=()=>{originalRefresh();$('state').textContent+=initialDescriptions[set().case_id]||'';};window.onresize=refresh;refresh();\n"
    path.write_text(html.replace('</script></html>',script+'</script></html>'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    args=parser.parse_args();out=args.directory.resolve();frozen=out/'frozen-source'
    if os.environ.get('UWA_TEACHER_FROZEN')!='1':
        env=dict(os.environ,UWA_TEACHER_FROZEN='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        packages=['uwa_cell_motion','uwa_cell_calibration','uwa_cell_control','uwa_cell_description','uwa_cell_gazebo']
        env['PYTHONPATH']=os.pathsep.join([str(frozen/p) for p in packages]+[env.get('PYTHONPATH','')])
        code=subprocess.call([sys.executable,str(frozen/'tools'/Path(__file__).name),str(out)],env=env)
        if code==0:annotate_starts(out)
        return code
    import numpy as np
    from generate_diverse_teacher_dataset import diverse_bindings
    from generate_teacher_dataset import load_completed,sha
    from review_teacher_dataset import audit_case
    from plan_two_arm_teacher import preview
    from uwa_cell_motion.common import ROBOT_IDS
    from uwa_cell_motion.teacher_dataset import atomic_json,digest
    from uwa_cell_motion.teacher_starts import coverage,state_check
    from uwa_cell_motion.two_arm_teacher import TwoArmTeacher
    manifest=json.loads((out/'manifest.json').read_text());results=load_completed(out,manifest)
    if len(results)!=len(manifest['cases']):raise ValueError('Incomplete batch')
    accepted=[results[c['id']] for c in manifest['cases'] if results[c['id']]['status']=='VALIDATED']
    if not accepted:raise ValueError('No accepted trajectories')
    checks=[audit_case(out,r) for r in accepted];sets=[];start_checks=[]
    with tempfile.TemporaryDirectory(prefix='uwa-diverse-review-') as directory:
        p=TwoArmTeacher(directory,Path(manifest['bindings']['source_path']))
        if diverse_bindings(p,p.source)!=manifest['bindings']:raise ValueError('Model/configuration binding mismatch')
        for r in accepted:
            p.initial=np.array(r['initial_pose']);p.start=dict(r['initial_state']);c=r['case']
            start_checks.append(dict(id=c['id'],**state_check(p,p.initial,p.start)))
            sets.append(dict(case_id=c['id'],label=f"{c['family']} / {c['category']} [{c['split']}]",variant='Teacher',
                duration_s=r['trajectory']['duration_s'],validation=r['validation'],frames=preview(p,r['trajectory'])))
        boxes=[]
        for _,T,half in p.environment_boxes:
            corners=np.array(list(itertools.product(*[[-h,h] for h in half])))
            boxes.append((corners@T[:3,:3].T+T[:3,3]).tolist())
        data=dict(arms=list(ROBOT_IDS),active_arms=list(p.arms),boxes=boxes,triangles=p.triangles.tolist(),
            radii={a:v.tolist() for a,v in p.problem.spheres.radii.items()},sets=sets,
            summary=[dict(name=c['id'],status=results[c['id']]['status'],accepted=results[c['id']]['status']=='VALIDATED',
                 reason=results[c['id']].get('reason') or results[c['id']].get('reference_check',{}).get('reason')) for c in manifest['cases']])
    banks=[json.loads((out/'starts'/f"{f['id']}.json").read_text()) for f in manifest['families']]
    used={r['case']['family'] for r in accepted};used_banks=[r for r in banks if r['family']['id'] in used]
    report=dict(passed=all(c['passed'] for c in checks+start_checks),manifest_sha256=digest(manifest),
        cases=checks,start_checks=start_checks,accepted_start_coverage=coverage(used_banks,np.array(manifest['anchor_pose'])),
        transitions=100*len(accepted),accepted=len(accepted),
        min_reference_arm_gap_m=min(r['reference_check']['min_pair_gap_m'] for r in accepted),
        min_validated_arm_gap_m=min(r['validation']['min_pair_gap_m'] for r in accepted),
        time_validation_samples=sum(r['validation']['samples'] for r in accepted),
        corrected_arm_encounters=sum(not r['reference_check']['passed'] and r['reference_check']['min_pair_gap_m']<.02 for r in accepted),
        scope='Independent export labels/derivatives, repeated initial-state check; discrete model geometry only')
    atomic_json(out/'export-audit.json',report)
    if not report['passed']:raise ValueError('Audit failed')
    template=Path(__file__).with_name('preview_two_arm_teacher.html').read_text()
    template=template.replace('Two arms — One object-space teacher','Different starts — Two-arm BC teacher')
    template=template.replace('<table id="comparison"></table>',
        f'<p><strong>{len(used)} distinct checked starts; {len(accepted)} accepted / {len(results)} attempted trajectories.</strong> '
        'Each start is an independently initialized fixed grasp, not an executed approach. Select a different start family below.</p>'
        '<details><summary>All trajectory checks</summary><table id="comparison"></table></details>')
    template=template.replace('<p id="rejected"></p>','<details><summary>Rejected tasks</summary><p id="rejected"></p></details>')
    template=template.replace('A red reference is an intentionally retained failed example.','Dashed outlines show requested references; rejected tasks remain listed.')
    (out/'viewer.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
    print('AUDIT PASS',json.dumps({k:report[k] for k in ('accepted','transitions','min_reference_arm_gap_m','min_validated_arm_gap_m','corrected_arm_encounters')}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())

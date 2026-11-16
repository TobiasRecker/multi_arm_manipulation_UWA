#!/usr/bin/env python3
"""Evaluate known-load references, explicitly separating force magnitude/identity.

Analytic upper-plane geometry is allowed only in these reference worlds. It is
not a generic fix for the ambiguous collision1/body1 attribution in GazeboSim10.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from uwa_cell_tasks.core import verify,seal,write_json
from uwa_cell_tasks import force_metrics
from uwa_cell_tasks.force_metrics import contact_loads,analytic_upper_plane_force


def evaluate(case):
    directory=Path(case['path']);trace=directory/'trace.jsonl'
    rows=[json.loads(x) for x in trace.open()];mass=case['mass_kg'];dt=case['step_s'];weight=mass*9.81
    errors={k:[] for k in ('static_normal_n','contact_balance_n','free_balance_n','fixed_force_n','fixed_torque_nm','rotated_torque_nm')}
    duplicates=0;raw_identity_failures=0;static=[];dynamic=[];drop=[];acceleration_disagreement=[]
    previous=None
    for row in rows:
        t=row['stamp']
        if t<.02:previous=row;continue
        def body_contacts(name):
            return [c for c in row['contacts'] if any('::link::'+name+'::' in c[k] for k in ('collision1','collision2'))]
        load=contact_loads(body_contacts('load_body'));duplicates+=load['duplicate_points_removed']
        falling=contact_loads(body_contacts('drop_body'))
        # Link velocity itself can remain latched after a body stops. The
        # independent impact momentum check uses displacement-derived velocity.
        displacement_dt=t-previous['stamp']
        drop_velocity=(row['bodies']['drop_body']['position'][2]-previous['bodies']['drop_body']['position'][2])/displacement_dt if displacement_dt>0 else 0.
        drop.append((t,falling['normal_load_n'],drop_velocity))
        selected=any(a<=t<=b for a,b in ((.3,.8),(1.2,1.8),(2.2,2.45),(2.8,2.95)))
        if not selected:previous=row;continue
        down=row['completed_external_down_n'];push=row['completed_external_push_n'];gravity=np.array([0,0,-weight])
        force=analytic_upper_plane_force(load['points'])
        elapsed=t-previous['stamp']
        if elapsed<=0:previous=row;continue
        acceleration=(np.array(row['bodies']['load_body']['velocity'])-previous['bodies']['load_body']['velocity'])/elapsed
        measured=acceleration*mass
        acceleration_disagreement.append(float(np.linalg.norm(acceleration-np.array(row['bodies']['load_body']['acceleration']))))
        errors['contact_balance_n'].append(float(np.linalg.norm(force+np.array([push,0,-down])+gravity-measured)))
        free=np.array(row['bodies']['free_body']['acceleration'])*mass
        errors['free_balance_n'].append(float(np.linalg.norm(free-np.array([push,0,0]))))
        expected=np.array([0,0,weight+down]);moment=np.array([0,-.15*(weight+down),0])
        w=row['joints']['reference_fixed'];rot=row['joints']['reference_fixed_rotated']
        errors['fixed_force_n'].append(float(np.linalg.norm(np.array(w['force'])-expected)))
        errors['fixed_torque_nm'].append(float(np.linalg.norm(np.array(w['torque'])-moment)))
        errors['rotated_torque_nm'].append(float(np.linalg.norm(np.array(rot['torque'])-np.array([moment[1],0,0]))))
        if .3<=t<=.8 or 2.8<=t<=2.95:
            errors['static_normal_n'].append(abs(load['normal_load_n']-(weight+down)))
            static.append(load['normal_load_n'])
        if 1.2<=t<=1.8:dynamic.append(load['normal_load_n'])
        # This deliberately tests the naive collision1->body1 assumption. The
        # support-floor row should receive downward normal force but doesn't.
        for c in body_contacts('load_body'):
            if '::link::floor_body::' in c['collision1']:
                if sum(p['body1']['force'][2] for p in c['points'])>0:raw_identity_failures+=1
        previous=row
    assert rows[-1]['stamp']>=3.-3*dt and all(errors.values()),'Incomplete reference trace'
    drop=np.array(drop);hits=np.flatnonzero(drop[:,1]>weight*2)
    assert len(hits),'No observed drop impact'
    impact=drop[hits[0],0];window=drop[(drop[:,0]>=impact-.02)&(drop[:,0]<=impact+.05)]
    impulse=float(np.sum(window[1:,1])*dt)
    expected_impulse=float(mass*(window[-1,2]-window[0,2])+weight*(window[-1,0]-window[0,0]))
    moving=np.convolve(drop[:,1],np.ones(max(1,round(.01/dt)))/max(1,round(.01/dt)),mode='valid')
    max_errors={k:max(v) for k,v in errors.items()}
    limits=dict(static_normal_n=max(.01,.01*weight),contact_balance_n=max(.02,.01*weight),
        free_balance_n=.002,fixed_force_n=.002,fixed_torque_nm=.002,rotated_torque_nm=.002)
    checks={k:max_errors[k]<=limits[k] for k in max_errors}
    checks['drop_impulse_balance']=abs(impulse-expected_impulse)<=max(.005,.02*abs(expected_impulse))
    checks['duplicated_rows_observed_and_removed']=duplicates>0
    return seal(dict(case=case,passed=all(checks.values()),checks=checks,maximum_errors=max_errors,limits=limits,
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),duplicate_points_removed=duplicates,
        contact_body_identity_usable=raw_identity_failures==0,naive_identity_counterexamples=raw_identity_failures,
        native_link_acceleration_consistent=max(acceleration_disagreement)<.01,
        maximum_native_acceleration_disagreement_m_s2=max(acceleration_disagreement),
        force_balance_acceleration_source='Finite difference of consecutively logged velocity; native Link acceleration can remain latched at rest.',
        contact_force_magnitude_usable=all(checks.values()),joint_wrench_usable=all(checks[k] for k in ('fixed_force_n','fixed_torque_nm','rotated_torque_nm')),
        static_mean_n=float(np.mean(static)),dynamic_normal_mean_n=float(np.mean(dynamic)),
        drop_peak_n=float(drop[:,1].max()),drop_10ms_mean_peak_n=float(moving.max()),
        drop_impulse_ns=impulse,drop_expected_impulse_ns=expected_impulse,
        drop_momentum_velocity_source='Consecutive observed positions, not potentially latched native Link velocity.',
        analytic_contact_orientation='Reference-only: known horizontal plane; not generic body attribution.'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('experiment',type=Path);args=p.parse_args()
    manifest=verify(json.loads((args.experiment/'experiment.json').read_text()));cases=verify(json.loads((args.experiment/'cases.json').read_text()))
    reports=[]
    for case in cases['cases']:
        assert hashlib.sha256((Path(case['path'])/'world.sdf').read_bytes()).hexdigest()==case['world_sha256']
        report=evaluate(case);write_json(Path(case['path'])/'force-report.json',report);reports.append(report)
        print(Path(case['path']).name,report['passed'],report['maximum_errors'],'peak',round(report['drop_peak_n'],2),flush=True)
    convergence=[]
    for mass in manifest['masses']:
        same=[r for r in reports if r['case']['mass_kg']==mass]
        impulses=[r['drop_impulse_ns'] for r in same];means=[r['dynamic_normal_mean_n'] for r in same]
        spread=float(np.ptp(impulses)/np.mean(impulses));normal_spread=float(np.ptp(means)/np.mean(means))
        convergence.append(dict(mass_kg=mass,impulse_relative_spread=spread,normal_relative_spread=normal_spread,passed=spread<.03 and normal_spread<.01))
    result=seal(dict(kind='known_load_force_validation',passed=all(r['passed'] for r in reports) and all(c['passed'] for c in convergence),
        experiment_sha256=manifest['sha256'],cases=reports,convergence=convergence,
        analyzer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        force_metrics_source_sha256=hashlib.sha256(Path(force_metrics.__file__).read_bytes()).hexdigest(),
        interpretation='Reference magnitudes and joint reactions only. Raw contact-body attribution and rigid-impact peak forces are not qualified physical damage measurements.'))
    write_json(args.experiment/'force-validation.json',result);print('REFERENCE VALIDATION',result['passed']);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())

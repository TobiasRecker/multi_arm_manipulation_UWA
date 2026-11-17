#!/usr/bin/env python3
"""Compare the 10x corner approach with smoother, near-identical paths and timing."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation

from uwa_cell_motion.carton_paths import CartonProblem
from uwa_cell_motion.common import ROBOT_IDS,PAIRS,config,dump,joint_names
from uwa_cell_motion.smooth_paths import curve,plan_path,path_at,progress,sample_segment


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source')
    parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    source=Path(args.source).resolve();out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=False)
    raw=(source/'trajectory-10x.json').read_bytes();old=json.loads(raw);prior=json.loads((source/'comparison.json').read_text())
    root=Path(prior['source_path']).parent;baseline_raw=(root/'paths.json').read_bytes()
    assert hashlib.sha256(baseline_raw).hexdigest()==prior['source_sha256']==old['source_sha256']
    assert old['executable'] is False
    limits=dict(velocity=.45,acceleration=.4,jerk=2.)
    paths={arm:plan_path(path,**limits) for arm,path in old['paths'].items()}
    duration=max(p['duration_s'] for p in paths.values());start=old['task']['start']
    stats=dict(max_joint_geometry_difference_rad=0.,max_tcp_geometry_difference_m=0.,
               max_tcp_orientation_difference_rad=0.,max_cartesian_line_error_m=0.,
               max_cartesian_orientation_error_rad=0.,static_samples=0)
    sampled_peaks=np.zeros(3)
    with tempfile.TemporaryDirectory(prefix='uwa-carton-smooth-') as d:
        p=CartonProblem(d,config(root/'motion.yaml'),root/'layout.yaml')
        assert p.signature==old['model_signature']==prior['model_signature']
        assert p.spheres.geometry.assets==prior['mesh_sha256']
        mesh=p.carton['mesh_file'].parent/p.carton['manifest']['solid_mesh']
        assert hashlib.sha256(mesh.read_bytes()).hexdigest()==prior['object_mesh_sha256']
        for arm,path in paths.items():
            names=joint_names(arm);target=np.array(old['task']['targets'][arm]['tool0_target'])
            previous=np.array([start[j] for j in names])
            for original,segment in zip(old['paths'][arm]['segments'],path['segments']):
                s=np.linspace(0,1,4001);positions=curve(segment)(s)
                original_q=CubicSpline(original['knots'],original['positions'],bc_type='natural')(s)
                joint_error=float(np.max(abs(positions-original_q)))
                assert joint_error<=1e-4
                stats['max_joint_geometry_difference_rad']=max(stats['max_joint_geometry_difference_rad'],joint_error)
                assert np.allclose(previous,positions[0],atol=1e-10,rtol=0)
                for value,q,qold in zip(s,positions,original_q):
                    state=dict(start,**dict(zip(names,q)));assert p.isolated[arm].check(state)[0],arm+' single path collision'
                    actual=p.chains[arm].forward(state);before=p.chains[arm].forward(dict(start,**dict(zip(names,qold))))
                    tcp=actual@old['task']['targets'][arm]['tool0_to_tcp'];tcp_before=before@old['task']['targets'][arm]['tool0_to_tcp']
                    distance=float(np.linalg.norm(tcp[:3,3]-tcp_before[:3,3]));assert distance<=1e-5
                    angle=float(np.linalg.norm(Rotation.from_matrix(actual[:3,:3]@before[:3,:3].T).as_rotvec()));assert angle<=1e-4
                    stats['max_tcp_geometry_difference_m']=max(stats['max_tcp_geometry_difference_m'],distance)
                    stats['max_tcp_orientation_difference_rad']=max(stats['max_tcp_orientation_difference_rad'],angle)
                    if segment['kind']=='CARTESIAN_LINE':
                        wanted=target.copy();wanted[2,3]+=segment['pregrasp_m']*(1-value)
                        pe=float(np.linalg.norm(actual[:3,3]-wanted[:3,3]));re=float(np.linalg.norm(Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).as_rotvec()))
                        assert pe<=1e-4 and re<=1e-3
                        stats['max_cartesian_line_error_m']=max(stats['max_cartesian_line_error_m'],pe)
                        stats['max_cartesian_orientation_error_rad']=max(stats['max_cartesian_orientation_error_rad'],re)
                    stats['static_samples']+=1
                previous=positions[-1]
                T=segment['time_law']['duration_s'];t=np.linspace(0,T,20001)
                for n,cap in enumerate([limits['velocity'],limits['acceleration'],limits['jerk']],1):
                    peak=float(np.max(abs(sample_segment(segment,t,n))))
                    sampled_peaks[n-1]=max(sampled_peaks[n-1],peak);assert peak<=cap*(1+1e-7)
                    assert np.max(abs(sample_segment(segment,[0,T],n)))<=1e-9
                segment['check']['validation']='DENSE_STATIC_SELF_CARTON_CLEAR_NEW_CURVE'
                segment['check']['samples']=len(s);segment['check']['limits_kind']='Analytical curve/time-law bounds; no hardware dynamics qualification'
            final=p.chains[arm].forward(dict(start,**dict(zip(names,previous))))
            assert np.linalg.norm(final[:3,3]-target[:3,3])<=1e-4
            print(arm,'validated',path['duration_s'],flush=True)
        neighbours={frozenset(v) for v in PAIRS}
        def state_at(t):
            state=dict(start)
            for arm,path in paths.items():state.update(zip(joint_names(arm),path_at(path,t)))
            return state
        def pairs_at(world,t):
            from itertools import combinations
            budgets={}
            for arm in ROBOT_IDS:
                v=np.zeros(len(p.names[arm]));v[:6]=path_at(paths[arm],t,1)
                budgets[arm]=p.spheres.arm_budget(arm,v,p.cfg['state_timeout_s'],p.cfg)[0]
            return [dict(arms=[a,b],gap_m=float(p.spheres.nearest(world,a,b)['clearance_m']),
                         required_m=p.cfg['model_margin_m']+(budgets[a]+budgets[b] if frozenset((a,b)) in neighbours else 0.))
                    for a,b in combinations(ROBOT_IDS,2)]
        times=np.linspace(0,duration,int(np.ceil(duration/.01))+1);records=[];min_gap=float('inf');geometric=0;static_margin=0
        for t in times:
            state=state_at(float(t));world=p.spheres.world(state);pairs=pairs_at(world,float(t));fcl=p.collision.check(state)[0]
            geometric+=not fcl;gap=min(c['gap_m'] for c in pairs);min_gap=min(min_gap,gap);static_margin+=gap<p.cfg['model_margin_m']
            if not fcl or any(c['gap_m']<c['required_m'] for c in pairs):records.append(dict(time_s=float(t),fcl_clear=bool(fcl),pairs=pairs))
        # Preserve failures before stopping; a changed relative timing must never inherit old validity.
        diagnostic=dict(duration_s=duration,samples=len(times),conflict_samples=len(records),fcl_collision_samples=geometric,
                        static_margin_violation_samples=static_margin,min_pair_gap_m=min_gap,
                        max_sample_time_step_s=float(times[1]-times[0]),conflicts=records)
        peaks={key:max(s['smooth_bounds'][key] for path in paths.values() for s in path['segments'])
               for key in ['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3']}
        report=dict(schema_version=1,artifact_type='offline_smoothed_carton_paths',executable=False,
                    offline_endpoint_policy=json.loads(baseline_raw).get('offline_endpoint_policy','stop_reserve'),
                    source_sha256=hashlib.sha256(raw).hexdigest(),source_path=str(source/'trajectory-10x.json'),
                    model_signature=p.signature,mesh_sha256=prior['mesh_sha256'],object_mesh_sha256=prior['object_mesh_sha256'],
                    task=old['task'],paths=paths,limits=limits,geometry=stats,peaks=peaks,
                    dense_sampled_peaks=dict(zip(peaks,sampled_peaks.tolist())),parallel_diagnostic=diagnostic,
                    assumptions=['Comparison design caps, not measured physical UR limits',
                                 'Joint lines unchanged; Cartesian joint spline upgraded from cubic to quintic',
                                 'C3 time law includes complete stops at primitive joins',
                                 'Independent timing changed; full scene rechecked on a <=10ms grid',
                                 'Stopping reserves remain a separate unqualified diagnostic',
                                 'No contact dynamics, closing, lifting or hardware execution'])
        dump(out/'result.json',report)
        if geometric or static_margin:raise ValueError('Retimed combination failed geometric checks; negative result saved')
        # Reuse only frozen visual assets of the source viewer; replace every moving frame.
        html=(source/'viewer.html').read_text();data,_=json.JSONDecoder().raw_decode(html.split('<script>const data=',1)[1])
        assert data['task']==old['task'];baseline=data['sets'][1]
        baseline['label']=f'10x baseline — {baseline["diagnostic"]["duration_s"]:.2f} s';baseline['id']='10x baseline'
        baseline['derivative_series']=[]
        from uwa_cell_motion.carton_paths import evaluate
        for t in np.linspace(0,baseline['diagnostic']['duration_s'],241):
            maxima=np.zeros(3)
            for path in old['paths'].values():
                remaining=t
                for segment in path['segments']:
                    T=segment['check']['duration_s']
                    if remaining<=T:
                        u=remaining/T;h=10*u**3-15*u**4+6*u**5;hp=30*u*u*(1-u)**2;hpp=60*u-180*u*u+120*u**3;hppp=60-360*u+360*u*u
                        sp=CubicSpline(segment['knots'],segment['positions'],bc_type='natural')
                        vals=[sp(h,1)*hp/T,(sp(h,2)*hp**2+sp(h,1)*hpp)/T**2,
                              (sp(h,3)*hp**3+3*sp(h,2)*hp*hpp+sp(h,1)*hppp)/T**3]
                        maxima=np.maximum(maxima,[np.max(abs(v)) for v in vals]);break
                    remaining-=T
            baseline['derivative_series'].append(maxima.tolist())
        preview=[];traces={r:[] for r in ROBOT_IDS};series=[]
        for t in np.linspace(0,duration,241):
            state=state_at(float(t));world=p.spheres.world(state);pairs=pairs_at(world,float(t));stages={}
            for arm,path in paths.items():
                elapsed=0.;stage='AT FIXED GOAL'
                for segment in path['segments']:
                    elapsed+=segment['time_law']['duration_s']
                    if t<elapsed:stage='VERTICAL APPROACH' if segment['kind']=='CARTESIAN_LINE' else 'SMOOTH JOINT TRANSIT';break
                stages[arm]=stage;tcp=p.chains[arm].forward(state)@old['task']['targets'][arm]['tool0_to_tcp']
                traces[arm].append(tcp[:3,3].round(6).tolist())
            series.append([max(float(np.max(abs(path_at(path,float(t),n)))) for path in paths.values()) for n in [1,2,3]])
            preview.append(dict(time_s=float(t),world={r:w.round(5).tolist() for r,w in world.items()},fcl_clear=p.collision.check(state)[0],stages=stages,
                                gaps=[dict(arms=c['arms'],gap_mm=c['gap_m']*1000,required_mm=c['required_m']*1000,violation=c['gap_m']<c['required_m']) for c in pairs]))
        data['sets']=[baseline,dict(label=f'Smoothed — {duration:.2f} s',id='smoothed fixed-target paths',frames=preview,traces=traces,
                                   diagnostic=diagnostic,peaks=peaks,derivative_series=series)]
        data['comparison']=dict(old_duration_s=baseline['diagnostic']['duration_s'],new_duration_s=duration,
                                old_peaks=baseline['peaks'],new_peaks=peaks,geometry=stats)
        template=Path(__file__).with_name('preview_carton_smoothing.html').read_text()
        (out/'viewer.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
        print(json.dumps(dict(duration_s=duration,peaks=peaks,geometry=stats,diagnostic={k:v for k,v in diagnostic.items() if k!='conflicts'}),indent=2))


if __name__=='__main__':main()

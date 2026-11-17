#!/usr/bin/env python3
"""Evaluate the same four fixed-corner paths at 1x and 10x offline time scale."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

from uwa_cell_motion.carton_paths import CartonProblem,path_at
from uwa_cell_motion.common import ROBOT_IDS,config,dump,joint_names
from uwa_cell_motion.path_speed import path_bounds,scale_path,reserve_check


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source')
    parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    root=Path(args.source).resolve();out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=False)
    raw=(root/'paths.json').read_bytes();result=json.loads(raw)
    if result['artifact_type']!='offline_carton_primitive_paths' or result['executable'] is not False:
        raise ValueError('Expected non-executable offline path artifact')
    combination=next(c for c in result['combinations'] if c['id']==result['recommended_id'])
    paths={p['id']:p for values in result['paths'].values() for p in values}
    selected={arm:paths[pid] for arm,pid in zip(ROBOT_IDS,combination['path_ids'])}
    variants={factor:{r:scale_path(p,factor) for r,p in selected.items()} for factor in [1.,10.]}
    with tempfile.TemporaryDirectory(prefix='uwa-speed10-') as d:
        p=CartonProblem(d,config(root/'motion.yaml'),root/'layout.yaml')
        assert p.signature==result['model_signature'] and p.spheres.geometry.assets==result['mesh_sha256']
        mesh=p.carton['mesh_file'].parent/p.carton['manifest']['solid_mesh'];mesh_raw=mesh.read_bytes()
        assert hashlib.sha256(mesh_raw).hexdigest()==result['task']['object_mesh_sha256']
        urdf=ET.fromstring(p.description)
        limits={j.get('name'):float(j.find('limit').get('velocity')) for j in urdf.findall('joint') if j.find('limit') is not None}
        reports=[]
        for factor,group in variants.items():
            arms={}
            for arm,path in group.items():
                bounds=path_bounds(path);caps=np.array([limits[j] for j in joint_names(arm)])
                arms[arm]=dict(bounds,urdf_velocity_limits_rad_s=caps.tolist(),
                               urdf_velocity_limit_pass=bool(np.all(np.array(bounds['velocity_rad_s'])<=caps)),
                               original_velocity_profile_pass=max(bounds['velocity_rad_s'])<=p.cfg['velocity_limit_rad_s'],
                               original_acceleration_profile_pass=max(bounds['acceleration_rad_s2'])<=p.cfg['acceleration_limit_rad_s2'])
            reports.append(dict(factor=factor,duration_s=max(v['duration_s'] for v in group.values()),arms=arms,
                                peaks={key:max(max(a[key]) for a in arms.values()) for key in ['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3']},
                                samples=[],geometric_collision_samples=0,reserve_conflict_samples=0,
                                min_gap_m=float('inf'),max_required_gap_m=0.,worst_reserve_surplus_m=float('inf')))
        start=result['task']['start'];duration=max(v['duration_s'] for v in selected.values())
        times=np.linspace(0,duration,int(np.ceil(duration/.1))+1);max_position_error=0.
        for t in times:
            state=dict(start)
            for arm,path in selected.items():state.update(zip(joint_names(arm),path_at(path,float(t))))
            world=p.spheres.world(state);fcl=bool(p.collision.check(state)[0])
            for report in reports:
                factor=report['factor'];group=variants[factor];scaled_time=float(t/factor)
                for arm in ROBOT_IDS:
                    error=np.max(abs(path_at(selected[arm],float(t))-path_at(group[arm],scaled_time)))
                    max_position_error=max(max_position_error,float(error))
                pairs=reserve_check(p,world,group,scaled_time);conflict=any(c['violation'] for c in pairs)
                report['samples'].append(dict(time_s=scaled_time,fcl_clear=fcl,pairs=pairs))
                report['geometric_collision_samples']+=not fcl;report['reserve_conflict_samples']+=conflict
                report['min_gap_m']=min(report['min_gap_m'],*(c['gap_m'] for c in pairs))
                report['max_required_gap_m']=max(report['max_required_gap_m'],*(c['required_m'] for c in pairs))
                report['worst_reserve_surplus_m']=min(report['worst_reserve_surplus_m'],*(c['gap_m']-c['required_m'] for c in pairs))
        assert max_position_error<1e-10
        for report in reports:
            report['sample_count']=len(times);report['max_sample_time_step_s']=float(times[1]-times[0])/report['factor']
        summary=dict(schema_version=1,artifact_type='offline_carton_speed_comparison',executable=False,
                     source_path=str(root/'paths.json'),source_sha256=hashlib.sha256(raw).hexdigest(),
                     model_signature=p.signature,mesh_sha256=result['mesh_sha256'],configuration=p.cfg,
                     object_mesh_sha256=result['task']['object_mesh_sha256'],recommended_id=result['recommended_id'],
                     max_time_scaled_position_difference_rad=max_position_error,variants=reports,
                     scaling=dict(time='1/f',velocity='f',acceleration='f^2',jerk='f^3'),
                     scope=['Commanded path model only; no dynamics/contact simulation or hardware test',
                            'Local analytic derivative bounds, not measured peak actuator quantities',
                            'URDF velocity limits are distinct from the original slow profile',
                            'No qualified acceleration/jerk/torque/servo-tracking envelope supplied',
                            'Reserve model retains original operating-cap floor, latency, age and assumed braking',
                            'Identical normalized geometry does not imply identical physical tracking or stopping',
                            'No closing, load-bearing grasp or lift is performed'])
        dump(out/'comparison.json',summary)
        dump(out/'trajectory-10x.json',dict(artifact_type='offline_time_scaled_carton_paths',executable=False,
                                          source_sha256=summary['source_sha256'],model_signature=p.signature,
                                          task=result['task'],factor=10.,paths=variants[10.],
                                          profile_compliance='Original profile exceeded; evaluation only'))
        # Scene data for the existing viewer conventions; render the same geometry at both rates.
        triangles=np.array([[struct.unpack_from('<3f',mesh_raw,84+k*50+12+i*12) for i in range(3)] for k in range(struct.unpack_from('<I',mesh_raw,80)[0])])
        T=p.carton['T_world_object'];triangles=triangles@T[:3,:3].T+T[:3,3]
        frames=p.spheres.geometry.fk.frames(start);boxes=[]
        for body in p.spheres.environment:
            if body.link=='offline_carton':continue
            lo=body.visual_vertices.min(axis=0);hi=body.visual_vertices.max(axis=0)
            corners=np.array([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]])
            tf=frames[body.link]@body.fixed;boxes.append((corners@tf[:3,:3].T+tf[:3,3]).tolist())
        sets=[]
        for report in reports:
            factor=report['factor'];group=variants[factor];preview=[];traces={r:[] for r in ROBOT_IDS}
            for t in np.linspace(0,report['duration_s'],241):
                state=dict(start);stages={}
                for arm,path in group.items():
                    state.update(zip(joint_names(arm),path_at(path,float(t))))
                    elapsed=0.;stage='AT FIXED GOAL'
                    for segment in path['segments']:
                        elapsed+=segment['check']['duration_s']
                        if t<elapsed:stage='VERTICAL APPROACH' if segment['kind']=='CARTESIAN_LINE' else 'JOINT TRANSIT';break
                    stages[arm]=stage
                    tcp=p.chains[arm].forward(state)@result['task']['targets'][arm]['tool0_to_tcp']
                    traces[arm].append(tcp[:3,3].round(5).tolist())
                world=p.spheres.world(state);pairs=reserve_check(p,world,group,float(t))
                gaps=[dict(arms=c['arms'],gap_mm=1000*c['gap_m'],required_mm=1000*c['required_m'],violation=c['violation']) for c in pairs]
                preview.append(dict(time_s=float(t),world={r:w.round(5).tolist() for r,w in world.items()},gaps=gaps,fcl_clear=p.collision.check(state)[0],stages=stages))
            diagnostic=dict(duration_s=report['duration_s'],samples=report['sample_count'],conflict_samples=report['reserve_conflict_samples'],
                            fcl_collision_samples=report['geometric_collision_samples'],min_pair_gap_m=report['min_gap_m'],
                            max_sample_time_step_s=report['max_sample_time_step_s'],
                            conflicts=[dict(time_s=s['time_s']) for s in report['samples'] if any(c['violation'] for c in s['pairs'])])
            sets.append(dict(label=f'{factor:g}x trajectory — {report["duration_s"]:.2f} s',id=f'{factor:g}x same paths',
                             frames=preview,traces=traces,diagnostic=diagnostic,peaks=report['peaks']))
        zero=dict(start)
        for arm in ROBOT_IDS:zero.update(dict.fromkeys(joint_names(arm),0.))
        data=dict(arms=list(ROBOT_IDS),sets=sets,boxes=boxes,carton_triangles=triangles.round(5).tolist(),
                  targets=result['task']['targets'],radii={r:v.tolist() for r,v in p.spheres.radii.items()},
                  zero_world={r:v.round(5).tolist() for r,v in p.spheres.world(zero).items()},
                  task=result['task'],total_path_sets=2)
        template=Path(__file__).with_name('preview_carton_speed.html').read_text()
        (out/'viewer.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
        print(json.dumps({k:v for k,v in summary.items() if k not in ['variants','scope','mesh_sha256','configuration']},indent=2))
        for report in reports:print(json.dumps({k:v for k,v in report.items() if k not in ['samples','arms']},indent=2))


if __name__=='__main__':main()

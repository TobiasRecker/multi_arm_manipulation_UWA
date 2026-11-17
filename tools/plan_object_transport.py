#!/usr/bin/env python3
"""Offline four-arm carton transport, analytic yaw correction and shared timing."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from uwa_cell_motion.common import ROBOT_IDS, dump
from uwa_cell_motion.object_transport import (ObjectTransport, shared_trajectory,
    trajectory_at, validate_trajectory)
from uwa_cell_motion.smooth_paths import sample_segment


def preview(problem, trajectory, extra):
    frames=[]
    for t in np.linspace(0,trajectory['duration_s'],241):
        row=trajectory_at(problem,trajectory,float(t))
        state=dict(problem.start,**dict(zip(problem.names,row['q'])))
        pairs=problem.distances(row['pose'],state)
        frames.append(dict(time_s=float(t),s=row['s'],phase=row['phase'],yaw_deg=float(np.rad2deg(row['yaw_rad'])),
            object_origin=problem.object_origin(row['pose']).tolist(),centre=row['pose'][:3,3].tolist(),
            world={a:v.round(6).tolist() for a,v in problem.problem.spheres.world(state).items()},
            fcl_clear=problem.full_check(row['pose'],state),required_mm=1000*(.02+extra*np.sin(np.pi*row['s'])**2),
            gaps=[dict(arms=v['arms'],gap_mm=1000*v['clearance_m']) for v in pairs]))
    return frames


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Smoothed side-grasp result.json')
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--optimization-file',type=Path,help='Optional candidate controls; always revalidated')
    parser.add_argument('--dt',type=float,default=.005,help='Maximum validation step in seconds')
    args=parser.parse_args()
    if not 0<args.dt<=.01:parser.error('Validation dt must be in (0, .01]')
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='uwa-object-transport-') as directory:
        p=ObjectTransport(directory,args.source)
        screen=[]
        for direction,offset in [('world -X',[-.2,0,0]),('world +X',[.2,0,0]),('world +Y',[0,.2,0]),('world -Y',[0,-.2,0])]:
            try:
                rows=p.path(offset,.1,count=61);check=p.check_path(rows)
            except (ValueError,np.linalg.LinAlgError) as error:
                check=dict(passed=False,error=str(error))
            screen.append(dict(direction=direction,offset_m=offset,check=check))
        dump(out/'screen.json',screen)
        available=[v for v in screen if v['check']['passed']]
        if not available:raise ValueError('No continuous IK branch passed direction screening')
        chosen=max(available,key=lambda v:v['check']['min_pair_gap_m']);offset=chosen['offset_m']
        report=dict(schema_version=1,executable=False,artifact_type='offline_four_arm_object_transport',
            source_path=str(p.source),source_sha256=p.source_sha256,model_signature=p.problem.signature,
            mesh_sha256=p.problem.spheres.geometry.assets,object_mesh_sha256=p.saved['object_mesh_sha256'],
            direction=chosen['direction'],offset_m=offset,lift_m=.1,screen=screen,
            initial_object_centre=p.initial.tolist(),grasp_offsets={a:v.tolist() for a,v in p.offsets.items()},
            jacobian_convention='K = stack(inv(J_i) A_i), qdot = K [v_world; omega_world]; origin carton centre',
            sigma_convention='min singular value of diag(2,2,2,1,1,1) J_i; length scale 0.5 m; trial floor 0.05',
            assumptions=['Hypothetical fixed grasps with open fingers, fixed bases',
                'Nominal carton bottom 3 mm above tabletop; no contact-supported placement',
                'All six arm pairs; moving mesh, static scene and self collision via FCL',
                'Discrete checks, not a continuous collision certificate',
                'No mass, grip-force, actuator torque or internal-force validation',
                'Three shared C3 phases, full stops at lift/transfer/lower joins',
                'Yaw-only local optimization; translation corridor and branch changes not implemented'],variants=[])
        report['implementation_sha256']={str(f.relative_to(Path(__file__).parents[1])):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in [Path(__file__),Path(__file__).with_name('preview_object_transport.html'),
                      Path(__file__).parents[1]/'uwa_cell_motion/uwa_cell_motion/object_transport.py',
                      Path(__file__).parents[1]/'uwa_cell_motion/uwa_cell_motion/smooth_paths.py']}
        dump(out/'result.json',report)
        for label,extra in [('Ideal transport',0.),('Extra-clearance yaw experiment',.04)]:
            if extra and args.optimization_file:
                raw=args.optimization_file.read_bytes();candidate=json.loads(raw)['report']
                controls=np.array(candidate['controls']);rows=p.path(offset,.1,controls,241)
                optimization=dict(candidate,check=p.check_path(rows,extra_margin=extra),
                    candidate_source=str(args.optimization_file.resolve()),candidate_sha256=hashlib.sha256(raw).hexdigest())
            else:
                optimization,rows=p.optimize_yaw(offset,.1,extra_margin=extra)
                controls=np.array(optimization.get('controls',[0.]*6))
            variant=dict(label=label,extra_clearance_m=extra,optimization=optimization)
            report['variants'].append(variant);dump(out/'result.json',report)
            if not optimization['check']['passed']:raise ValueError(label+': optimizer failed acceptance check')
            if controls.shape!=(6,) or not np.isfinite(controls).all() or np.max(abs(controls))>np.deg2rad(15)+1e-10:
                raise ValueError('Candidate yaw controls violate the experiment envelope')
            trajectory=shared_trajectory(p,offset,.1,controls)
            variant['trajectory']=trajectory;dump(out/'result.json',report)
            print(label,'shared trajectory',trajectory['duration_s'],'s; validating',flush=True)
            validation=validate_trajectory(p,trajectory,dt=args.dt,extra_margin=extra)
            variant['validation']=validation
            variant['bounds']={k:max(seg['smooth_bounds'][k] for seg in trajectory['phases'])
                for k in ['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3']}
            peaks=np.zeros(3)
            for seg in trajectory['phases']:
                T=seg['time_law']['duration_s'];times=np.linspace(0,T,10001)
                for derivative,cap in [(1,.45),(2,.4),(3,2.)]:
                    peaks[derivative-1]=max(peaks[derivative-1],float(np.max(abs(sample_segment(seg,times,derivative)))))
                    if peaks[derivative-1]>cap+1e-7:raise ValueError('Joint derivative cap exceeded')
                    if np.max(abs(sample_segment(seg,[0,T],derivative)))>1e-8:raise ValueError('Nonzero join derivatives')
                seg['check']['validation']='PASS_DISCRETE_SHARED_INTERPOLANT' if validation['passed'] else 'FAIL_SHARED_INTERPOLANT'
            variant['sampled_derivative_peaks']=peaks.tolist();dump(out/'result.json',report)
            print(label,json.dumps(validation),flush=True)
            if not validation['passed']:raise ValueError(label+': negative result saved')
        frames=p.problem.spheres.geometry.fk.frames(p.start);boxes=[]
        for body in p.problem.spheres.environment:
            if body.link=='offline_carton':continue
            lo=body.visual_vertices.min(axis=0);hi=body.visual_vertices.max(axis=0)
            corners=np.array([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]])
            tf=frames[body.link]@body.fixed;boxes.append((corners@tf[:3,:3].T+tf[:3,3]).tolist())
        data=dict(arms=list(ROBOT_IDS),boxes=boxes,triangles=p.triangles.tolist(),direction=chosen['direction'],
            radii={a:v.tolist() for a,v in p.problem.spheres.radii.items()},sets=[])
        for variant in report['variants']:
            data['sets'].append(dict(label=variant['label'],duration_s=variant['trajectory']['duration_s'],
                validation=variant['validation'],bounds=variant['bounds'],
                frames=preview(p,variant['trajectory'],variant['extra_clearance_m'])))
        template=Path(__file__).with_name('preview_object_transport.html').read_text()
        (out/'viewer.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
        print('Viewer:',out/'viewer.html',flush=True)


if __name__=='__main__':main()

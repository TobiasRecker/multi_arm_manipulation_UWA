#!/usr/bin/env python3
"""File-only controller interpolation and task audit of a complete air-demo draft.

No execution endpoint. Even a passing file needs current-start binding,
coupled-motion commissioning and explicit Motion Review on the control host.
"""
import argparse
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
from scipy.interpolate import BPoly, make_interp_spline
from scipy.spatial.transform import Rotation

import prepare_carton_air_demo as demo
from uwa_cell_calibration.model import CollisionModel
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import joint_names
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_tasks.reviewed_carton import speed_envelope
from uwa_cell_tasks.timing import interpolation_peaks


def controller_points(spline, knots, duration):
    times=np.round(knots*duration*1e9)/1e9
    return [dict(time=float(t),positions=q.tolist(),velocities=v.tolist(),accelerations=a.tolist())
        for t,q,v,a in zip(times,spline(knots),spline(knots,1)/duration,spline(knots,2)/duration**2,strict=True)]


def source_phases(data):
    state=dict(data['reference_initial']);result={}
    for phase in data['phases']:
        result[phase['id']]=dict(start=dict(state),phase=phase)
        state.update(zip(phase['joint_names'],phase['points'][-1]['positions']))
    return result


def qualify(args):
    folder=args.bundle.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    data=demo.read(folder/'input.json');draft=demo.read(args.draft)
    if not draft.get('success') or draft.get('phase')!='COARSE_HARDWARE_DRAFT_PASSED':
        raise ValueError('A complete accepted draft is required')
    p=HardwareProblem.__new__(HardwareProblem);p.directory=out/'cell'
    p.cfg=data['config'];p.names=data['names'];p.description=(folder/'hardware.urdf').read_text()
    p.original_description=(folder/'original.urdf').read_text()
    p.collision=CollisionModel(p.description,p.directory/'moveit')
    shutil.copyfile(folder/'hardware.srdf',p.directory/'moveit/robot.srdf')
    for pair in ET.parse(folder/'hardware.srdf').findall('disable_collisions'):
        p.collision.scene.allowed_collision_matrix.set_entry(pair.get('link1'),pair.get('link2'),True)
    p.spheres=SphereModel(p.description,p.names,p.cfg['sphere_spacing_m'])
    p.chains={a:Chain(p.original_description,'world',a+'_tool0')for a in p.names}
    held=demo.moving_model(p,data,out)
    names=[j for arm in p.names for j in joint_names(arm)]
    envelope=speed_envelope(p,list(p.names),.1,1/12)
    offsets={a:np.asarray(v)for a,v in data['offsets'].items()}
    inverse=np.linalg.inv(offsets['right_front'])
    reference=(folder/'reference.urdf').read_text()
    refchains={a:Chain(reference,'world',a+'_tool0')for a in (*demo.HOLDERS,demo.WORKER)}
    references=source_phases(data)
    report=dict(success=False,executable=False,robot_commands_sent=False,physical_tool=False,
        phase='CONTROLLER_INTERPOLATION_AUDIT',start_kind=draft['start_kind'],
        limits=dict(joint_rad_s=.1,tcp_m_s=1/12,acceleration_rad_s2=p.cfg['acceleration_limit_rad_s2']),
        geometry_check_step_rad=.0025,phases=[],required_followup=
        'Current N100 binding, coupled-motion commissioning and explicit Motion Review',
        sources={str(path):demo.digest(path)for path in [folder/'input.json',args.draft,Path(demo.__file__),Path(__file__)]})
    demo.write(out/'proof.json',report)
    previous=dict(draft['start']);total=0.
    try:
        for phase in draft['phases']:
            print('Auditing controller phase',phase['id'],flush=True)
            rows=phase['samples'];u=np.array([row['source_index']for row in rows],float)
            u=(u-u[0])/(u[-1]-u[0])
            q=np.array([[row['positions'][j]for j in names]for row in rows])
            if max(abs(q[0]-[previous[j]for j in names]))>1e-7:
                raise ValueError(phase['id']+': phase junction changed')
            if phase['id']=='draw_y_min':
                columns=[names.index(j)for j in joint_names(demo.WORKER)]
                if np.ptp(q[:,columns],axis=0).max()>1e-5:
                    raise ValueError('Final circle does not keep the worker fixed')
                q[:,columns]=q[0,columns]
            zeros=np.zeros(len(names))
            spline=make_interp_spline(u,q,k=5,bc_type=([(1,zeros),(2,zeros)],[(1,zeros),(2,zeros)]))
            knots=np.unique(np.r_[0.,spline.t[(spline.t>0)&(spline.t<1)],1.])
            duration=1.
            for iteration in range(8):
                points=controller_points(spline,knots,duration)
                velocity=interpolation_peaks(dict(points=points),1)
                acceleration=interpolation_peaks(dict(points=points),2)
                scale=max(1.,float(velocity.max())/.1,
                    float(np.sqrt(acceleration.max()/p.cfg['acceleration_limit_rad_s2'])))
                trajectories={}
                for arm in p.names:
                    columns=[names.index(j)for j in joint_names(arm)]
                    if np.ptp(q[:,columns],axis=0).max()<1e-9:continue
                    subset=[dict(time=row['time'],**{key:np.asarray(row[key])[columns].tolist()
                        for key in ('positions','velocities','accelerations')})for row in points]
                    scale=max(scale,envelope.time_scale(arm,subset))
                    trajectories[arm]=dict(joint_names=joint_names(arm),points=subset)
                if scale<=1+1e-10:break
                duration*=scale
            else:raise ValueError('Unable to represent shared bounded controller timing')
            for arm,trajectory in trajectories.items():envelope.check_trajectory(arm,trajectory['points'])
            actual=BPoly.from_derivatives([r['time']for r in points],
                [[r[k]for k in ('positions','velocities','accelerations')]for r in points])
            count=max(257,int(np.ceil(float(velocity.max())*duration/.0025))+1)
            checks=np.unique(np.r_[np.linspace(0,duration,count),[r['time']for r in points]])
            source=references.get(phase['id']);reference_curve=None
            if source and (source['phase'].get('drawing')or source['phase'].get('operation')):
                rp=source['phase']['points']
                reference_curve=BPoly.from_derivatives([r['time']for r in rp],
                    [[r[k]for k in ('positions','velocities','accelerations')]for r in rp])
            closure=angle_error=tip_error=0.;gap=float('inf')
            for time in checks:
                state=dict(previous,**dict(zip(names,actual(time))))
                pose=p.chains['right_front'].forward(state)@inverse
                rear=p.chains['right_rear'].forward(state)
                wanted=pose@offsets['right_rear']
                closure=max(closure,float(np.linalg.norm(rear[:3,3]-wanted[:3,3])))
                angle_error=max(angle_error,float(Rotation.from_matrix(rear[:3,:3]@wanted[:3,:3].T).magnitude()))
                if closure>.0001 or angle_error>.001:
                    raise ValueError(f"{phase['id']}: interpolated fixed-grip error {closure}m/{angle_error}rad")
                gap=min(gap,demo.check_state(p,held,data,state,pose))
                if reference_curve is not None:
                    t=time/duration*source['phase']['points'][-1]['time']
                    rs=dict(source['start'],**dict(zip(source['phase']['joint_names'],reference_curve(t))))
                    refpose=refchains['right_front'].forward(rs)@np.linalg.inv(data['reference_group']['object_to_tcp']['right_front'])
                    reftool=refchains[demo.WORKER].forward(rs);tool=p.chains[demo.WORKER].forward(state)
                    ref_local=refpose[:3,:3].T@(reftool[:3,3]+.3*reftool[:3,2]-refpose[:3,3])
                    local=pose[:3,:3].T@(tool[:3,3]+.3*tool[:3,2]-pose[:3,3])
                    tip_error=max(tip_error,float(np.linalg.norm(local-ref_local)))
                    if tip_error>.00025:raise ValueError(f"{phase['id']}: virtual task-path error {tip_error}m")
            record=dict(id=phase['id'],duration_s=duration,trajectories=trajectories,
                checked_samples=len(checks),minimum_neighbor_gap_m=gap,fixed_grip_error_m=closure,
                fixed_grip_error_rad=angle_error,virtual_task_error_m=tip_error,
                start=dict(previous),end={j:float(v)for j,v in zip(names,actual(duration))})
            demo.write(out/(phase['id']+'.json'),record)
            report['phases'].append({k:v for k,v in record.items()if k not in ('trajectories','start','end')})
            previous.update(record['end']);total+=duration
            demo.write(out/'proof.json',report)
        report.update(success=True,phase='FINITE_CONTROLLER_INTERPOLATION_AUDIT_PASSED',
                      total_duration_s=total,end=previous)
    except Exception as error:
        report.update(error=str(error),phase='CONTROLLER_INTERPOLATION_AUDIT_REJECTED')
        print('REJECTED',error,flush=True)
    demo.write(out/'proof.json',report)
    return 0 if report['success'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('bundle','draft','output'):parser.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(qualify(parser.parse_args()))

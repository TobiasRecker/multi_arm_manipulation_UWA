#!/usr/bin/env python3
"""Supplement a frozen Return-to-Home plan with finite task-obstacle evidence.

No ROS context or hardware commands. Does not alter the active protection model.
The original plan retains its robot, object/support, speed and margin proof.
This supplementary audit checks the full-opening robots against extra obstacles
and conservatively bounds the released carton against those obstacles.
"""
import argparse
import itertools
from pathlib import Path
import shutil
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
from scipy.interpolate import BPoly
from prepare_carton_air_demo import read, write, digest
from task_obstacles import robot_model


def audit(bundle, plan_path, output):
    output.mkdir(parents=True, exist_ok=False)
    data=read(bundle/'input.json');plan=read(plan_path)
    if plan['model_identity']!=data['model_identity']:
        raise ValueError('Frozen carton scene and return plan model identities differ')
    problem=SimpleNamespace(description=(bundle/'hardware.urdf').read_text(),
        directory=output/'cell',names=data['names'])
    folder=problem.directory/'moveit';folder.mkdir(parents=True)
    shutil.copyfile(bundle/'hardware.srdf',folder/'robot.srdf')
    model=robot_model(problem,data['task_obstacles'],output/'obstacles')
    report=dict(success=False,executable=False,robot_commands_sent=False,
        plan_sha256=digest(plan_path),bundle_sha256=digest(bundle/'input.json'),
        task_obstacles=data['task_obstacles'],geometry_step_rad=.0025,groups=[])
    try:
        # Includes support/release endpoints and an enclosing vertical drop tube.
        tracks={item['link']:item for item in plan['object_tracks']}
        for item in plan['objects']:
            if item['loaded']:
                raise ValueError('Supplementary release audit is limited to the in-place unladen reset')
            track=tracks[item['link']]
            local=np.array([v for box in track['boxes'] for v in itertools.product(*zip(box['lo'],box['hi']))])
            cloud=np.concatenate([local@np.asarray(item[key])[:3,:3].T+np.asarray(item[key])[:3,3]
                for key in ('start_pose','release_pose','support_pose')])
            # Existing 5mm position and 3mm landing envelopes, conservatively isotropic.
            error=item['position_error_m']+.003
            lo,hi=cloud.min(0)-error,cloud.max(0)+error
            for obstacle in data['task_obstacles']:
                if np.all(hi>=obstacle['lo_m']) and np.all(lo<=obstacle['hi_m']):
                    raise ValueError(item['name']+': conservative release tube intersects '+obstacle['name'])
        groups=[g for item in plan['objects']for g in item['retreat']]+plan['home']
        for group in groups:
            curves={arm:BPoly.from_derivatives([p['time']for p in t['points']],
                [[p[k]for k in ('positions','velocities','accelerations')]for p in t['points']])
                for arm,t in group['trajectories'].items()}
            duration=group['duration_s'];count=max(257,int(np.ceil(duration*plan['joint_limit_rad_s']/.0025))+1)
            knots=[p['time']for t in group['trajectories'].values()for p in t['points']]
            checks=np.unique(np.r_[np.linspace(0,duration,count),knots])
            for time in checks:
                state=dict(group['start'])
                for arm,curve in curves.items():
                    state.update(zip(group['trajectories'][arm]['joint_names'],curve(time)))
                if not model.check(state)[0]:
                    model.check(state,contacts=True)
                    raise ValueError(group['phase']+': extra task obstacle collision')
            report['groups'].append(dict(phase=group['phase'],arms=group['arms'],samples=len(checks)))
        report['success']=True
    except Exception as error:
        report['error']=str(error)
    write(output/'proof.json',report)
    print({k:v for k,v in report.items()if k!='task_obstacles'},flush=True)
    return 0 if report['success'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('bundle','plan','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(audit(args.bundle,args.plan,args.output))

#!/usr/bin/env python3
"""Read-only, compact agent review packet; never approves or commands a task."""
import argparse
import json
from pathlib import Path
import time

from uwa_cell_tasks.core import verify


def candidate_summary(candidate):
    result={k:candidate.get(k) for k in ('id','strategy','assumptions','score','centre_of_mass_object_m',
        'gravity_projection_fraction','support_line_offset_m','estimated_vertical_load_n','load_estimate_kind','contacts')}
    for key in ('tcp_targets','pregrasp'):
        result[key+'_world_xyz_m']={arm:[pose[i][3] for i in range(3)] for arm,pose in candidate[key].items()}
    return result


def trajectory_summary(trajectory):
    points=trajectory['points']
    result=dict(kind=trajectory.get('kind'),duration_s=trajectory['duration_s'],
        joint_names=trajectory['joint_names'],samples=len(points),
        maximum_absolute_velocity_rad_s=max((abs(v) for p in points for v in p.get('velocities',[])),default=None),
        maximum_absolute_acceleration_rad_s2=max((abs(v) for p in points for v in p.get('accelerations',[])),default=None))
    if 'object_pose' in points[0]:
        result['object_displacement_world_m']=[points[-1]['object_pose'][i][3]-points[0]['object_pose'][i][3] for i in range(3)]
        result['object_motion_statement']=trajectory.get('statement')
        result['simulation_stop_reserve_mode']=trajectory.get('simulation_stop_reserve_mode','enforce')
        result['group']=trajectory.get('group')
    return result


def inspect(directory):
    directory=Path(directory).resolve()
    state=json.loads((directory/'state.json').read_text())
    packet=verify(json.loads((directory/'review.json').read_text()))
    evidence=packet['evidence'];verify(evidence)
    pending=state['state']=='WAITING_REVIEW' and state['phase']==packet['stage']
    waiting=next((h for h in reversed(state['history']) if h['state']=='WAITING_REVIEW' and h['phase']==packet['stage']),None)
    result=dict(run=str(directory),saved_state=state['state'],phase=state['phase'],
        pending=pending,stage=packet['stage'],revision=packet['revision'],sha256=packet['sha256'],
        evidence_sha256=evidence['sha256'],review_age_wall_s=time.time()-waiting['time_unix_s'] if waiting else None,
        notice='Saved review evidence only; inspect actual images and live task/guard state before deciding.')
    observation=evidence.get('observation')
    if observation is None and (directory/'strategy.json').is_file():
        observation=json.loads((directory/'strategy.json').read_text()).get('observation')
    if observation:
        verify(observation)
        result['observation']=dict(status=observation['status'],source=observation.get('source'),
            sha256=observation['sha256'],source_stamp=observation['source_stamp'],
            views=[{k:view.get(k) for k in ('arm','status','inliers','reprojection_rms_px','reason')} for view in observation['views']])
        matches=[]
        for path in directory.glob('*/result.json'):
            candidate=json.loads(path.read_text())
            if candidate.get('sha256')==observation['sha256']:
                matches.extend(str(p) for p in sorted(path.parent.glob('*-inspection.jpg')))
        result['inspection_images']=matches
    if 'candidate' in evidence:
        result['candidate']=candidate_summary(evidence['candidate'])
    elif 'candidates' in evidence:
        result['candidate_ranking']=[dict(id=c['id'],score=c['score']) for c in evidence['candidates']]
        result['first_three_candidates']=[candidate_summary(c) for c in evidence['candidates'][:3]]
    for key in ('trajectory','entry','lift_witness'):
        if key in evidence:result[key]=trajectory_summary(evidence[key])
    if 'delta_m_rad' in evidence:result['alignment_delta_m_rad']=evidence['delta_m_rad']
    for key in ('scene_sha256','model_signature','plan_sha256'):
        if key in evidence:result[key]=evidence[key]
    if 'mesh_sha256' in evidence:result['collision_meshes_bound']=len(evidence['mesh_sha256'])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    arguments=parser.parse_args()
    print(json.dumps(inspect(arguments.run),indent=2))

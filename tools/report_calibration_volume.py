#!/usr/bin/env python3
"""Verify and illustrate a frozen calibration endpoint proposal, offline only."""
import argparse
from itertools import combinations, product
import json
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from uwa_cell_calibration.model import CollisionModel
from uwa_cell_control.view_geometry import VisibilityModel
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_description.configuration import ROBOT_IDS, joint_names
from uwa_cell_motion.geometry import SphereModel


def report(root, search):
    source = root/'input'
    output = root/search/'output'
    proposal = json.loads((output/'proposal.json').read_text())
    proposal['source_proposal_sha256'] = hashlib.sha256((output/'proposal.json').read_bytes()).hexdigest()
    proposal['source_proposal_path'] = str((output/'proposal.json').resolve())
    # Preserve the explicitly adopted19Nov RF cable revolution. This changes
    # only the joint representation; the independent FK/FCL check below
    # verifies the same geometry. Raw container output remains untouched.
    rf = proposal['selected']['right_front']['joints_rad']
    offset = -2*np.pi*round(rf[0]/(2*np.pi))
    rf[0] += offset
    proposal['target_state']['right_front_shoulder_pan_joint'] += offset
    proposal['joint_winding_adjustment'] = dict(arm='right_front',joint='shoulder_pan_joint',
        added_rad=offset,reason='19Nov user cable-unwinding decision: preserve near-zero base revolution')
    proposal['limitations'] = [s for s in proposal['limitations'] if not s.startswith('No new hand-eye')]
    proposal['limitations'].append('Fixed-arm images register cameras to external anchors; independent motion-based hand-eye fitting/validation requires multiple arm poses.')
    description = (source/'original.urdf').read_text()
    collision_description = (source/'collision.urdf').read_text()
    for filename, key in [('original.urdf','original_urdf_sha256'), ('collision.urdf','collision_urdf_sha256')]:
        if hashlib.sha256((source/filename).read_bytes()).hexdigest() != proposal['source_binding'][key]:
            raise ValueError('Frozen geometry binding changed: '+filename)
    state = proposal['target_state']
    collision = CollisionModel(collision_description, root/'endpoint-verification-model')
    for pair in ET.parse(source/'local-model/moveit/robot.srdf').findall('disable_collisions'):
        collision.scene.allowed_collision_matrix.set_entry(pair.get('link1'), pair.get('link2'), True)
    clear, _ = collision.check(state)
    names = {r:list(joint_names(r))+[n for n in state if n.startswith(r+'_robotiq_')]
             for r in ROBOT_IDS}
    spheres = SphereModel(collision_description, names, .05)
    world, bounds = spheres.planning_world(state)
    gaps = {a+'__'+b:spheres.nearest(world, a, b) for a,b in combinations(ROBOT_IDS, 2)}
    if not clear or min(g['clearance_m'] for g in gaps.values()) <= .04:
        raise ValueError('Endpoint fails existing FCL /40mm interarm envelope criterion')
    points = np.array(proposal['common_board_centre_samples_world_m'])
    # Largest symmetric XY box around the table midpoint whose 5cm grid
    # nodes all belong to the retained mask; vertical extent may be asymmetric.
    occupied = {tuple(np.rint(p/.05).astype(int)) for p in points}
    best = (0., None)
    for x,y,lo,hi in product(range(1,12),range(1,12),range(20,27),range(27,34)):
        volume = 2*x*.05*2*y*.05*(hi-lo)*.05
        if volume <= best[0]:
            continue
        if all((i,j,k) in occupied for i,j,k in product(range(-x,x+1),range(-y,y+1),range(lo,hi+1))):
            best = volume, [[-x*.05,-y*.05,lo*.05],[x*.05,y*.05,hi*.05]]
    box = np.array(best[1])
    details = {}
    for r,e in proposal['selected'].items():
        T = np.array(e['camera_world'])
        optics = proposal['optics'][r]
        minimum_budget = .9*min(optics['camera_matrix'][0][0],optics['camera_matrix'][1][1])*.028*np.cos(np.pi/4)/np.linalg.norm(points-T[:3,3],axis=1).max()
        q = np.array(e['joints_rad'])
        reserves = [min(v-collision.bounds[n][0],collision.bounds[n][1]-v) for n,v in zip(joint_names(r),q)]
        chain = Chain(description,'world',r+'_wrist_camera_optical_frame')
        fk = chain.forward(state)
        details[r] = dict(camera_world_xyz_m=T[:3,3].tolist(), distance_m=e['distance_to_centre_m'],
            joints_deg=np.rad2deg(q).tolist(), minimum_joint_bound_reserve_deg=float(np.rad2deg(min(reserves))),
            minimum_marker_design_budget_px=float(minimum_budget),
            fk_matrix_max_error=float(np.max(abs(fk-T))))
    verification = dict(endpoint_fcl_clear=clear, interarm_hull_gaps=gaps,
        minimum_interarm_hull_gap_m=min(g['clearance_m'] for g in gaps.values()),
        sampled_box_world_bounds_m=box.tolist(), sampled_box_dimensions_m=(box[1]-box[0]).tolist(),
        sampled_box_volume_m3=best[0], cameras=details, executable=False,
        notes=['Box is a sampled design estimate; no analytic continuous-visibility proof.',
               'Marker budget is an optical estimate, not actual detection.',
               'No fresh four-arm start or approach path. No robot command sent.'])
    (root/'endpoint-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    (root/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
    geometry = VisibilityModel(description,ROBOT_IDS)
    frames = geometry.frames(state)
    colors = dict(left_front='#0072B2',left_rear='#009E73',right_front='#D55E00',right_rear='#8B40A3')
    fig = plt.figure(figsize=(15,7),layout='constrained')
    ax = fig.add_subplot(121,projection='3d');top = fig.add_subplot(122)
    for x in (-.4955,.4955):
        corners=np.array([[x+dx,dy,.9] for dx,dy in [(-.4,-.85),(.4,-.85),(.4,.85),(-.4,.85),(-.4,-.85)]])
        ax.plot(*corners.T,color='#606060');top.plot(corners[:,0],corners[:,1],color='#606060')
    for r,e in proposal['selected'].items():
        suffixes=['base_link','shoulder_link','upper_arm_link','forearm_link','wrist_1_link','wrist_2_link','wrist_3_link','tool0']
        skeleton=np.array([frames[r+'_'+s][:3,3] for s in suffixes])
        eye=np.array(e['camera_world'])[:3,3];c=np.array(proposal['target_centre_world_m'])
        ax.plot(*skeleton.T,'o-',color=colors[r],linewidth=4,markersize=4,label=r.replace('_',' '))
        ax.scatter(*eye,color=colors[r],s=80,marker='s');ax.plot(*np.array([eye,c]).T,'--',color=colors[r],alpha=.8)
        top.plot(skeleton[:,0],skeleton[:,1],'o-',color=colors[r],linewidth=4,markersize=4)
        top.scatter(*eye[:2],color=colors[r],s=80,marker='s');top.plot([eye[0],0],[eye[1],0],'--',color=colors[r])
    vertices=np.array(list(product(*zip(box[0],box[1]))))
    for a,b in combinations(vertices,2):
        if np.count_nonzero(abs(a-b)>1e-6)==1:ax.plot(*np.array([a,b]).T,color='#111111',linewidth=2)
    ax.scatter(*points[::4].T,c='#74c7eb',alpha=.18,s=5)
    top.scatter(points[::3,0],points[::3,1],c='#74c7eb',s=6,alpha=.3)
    top.plot([box[0,0],box[1,0],box[1,0],box[0,0],box[0,0]],
             [box[0,1],box[0,1],box[1,1],box[1,1],box[0,1]],color='black',linewidth=2)
    ax.set(xlim=(-1.15,1.15),ylim=(-1.35,1.35),zlim=(.8,2.),xlabel='world X [m]',ylabel='world Y [m]',zlabel='height [m]',title='Proposed arm / camera endpoints')
    ax.view_init(elev=26,azim=-59);ax.set_box_aspect((2.3,2.7,1.2));ax.legend(loc='upper left',fontsize=9)
    top.set(xlim=(-1.2,1.2),ylim=(-1.35,1.35),xlabel='world X [m]',ylabel='world Y [m]',title='Top view | camera squares, viewing directions dashed')
    top.set_aspect('equal');top.grid(alpha=.25)
    dims=box[1]-box[0]
    distances=[e['distance_to_centre_m'] for e in proposal['selected'].values()]
    fig.suptitle(f'CALIBRATION VIEW PROPOSAL — OFFLINE ONLY\nCamera distance {min(distances):.2f}–{max(distances):.2f} m | sampled central box {dims[0]:.2f} × {dims[1]:.2f} × {dims[2]:.2f} m',fontsize=15,fontweight='bold')
    fig.savefig(root/'proposal.png',dpi=160);plt.close(fig)
    print(json.dumps(verification,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    p.add_argument('--search',default='search-06')
    args=p.parse_args();report(args.root.resolve(),args.search)

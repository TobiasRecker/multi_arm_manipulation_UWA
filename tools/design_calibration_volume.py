#!/usr/bin/env python3
"""Offline four-wrist observation design from frozen geometry; no robot clients.

Run in the planning container with a frozen input folder. The result is an
endpoint proposal only. It cannot be executed and contains no start trajectory.
"""
import argparse
from itertools import combinations, product
import json
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from uwa_cell_calibration.model import CollisionModel
from uwa_cell_control.view_geometry import VisibilityModel, project_points
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_description.configuration import ROBOT_IDS, joint_names


def look_at(eye, centre, roll=0.):
    z = np.asarray(centre)-eye
    z /= np.linalg.norm(z)
    x = np.cross(z, [0., 0., 1.])
    x /= np.linalg.norm(x)
    T = np.eye(4)
    T[:3, :3] = np.column_stack((x, np.cross(z, x), z)) @ Rotation.from_euler('z', roll).as_matrix()
    T[:3, 3] = eye
    return T


def sphere_samples(radius):
    directions = np.array(list(product((-1., 0., 1.), repeat=3)))
    directions = directions[np.linalg.norm(directions, axis=1)>0]
    return radius*directions/np.linalg.norm(directions, axis=1)[:, None]


def fit_mask(points, T, optics, radius=.182):
    # A4 paper's half diagonal; 26 sampled support directions. This is a
    # sampled design envelope, explicitly not an analytic all-orientation proof.
    samples = points[:, None, :]+sphere_samples(radius)[None, :, :]
    _, inside = project_points(samples.reshape(-1, 3), T, optics['camera_matrix'],
                               optics['distortion'], optics['image_size'], margin=70)
    distance = np.linalg.norm(points-T[:3, 3], axis=1)
    # A design budget of >=28 native pixels / marker edge at45deg tilt
    # (~4.7px per 4x4-marker module including its border), with10% optical
    # allowance. Actual sharpness, exposure and recognition still need photos.
    marker_px = .9*min(optics['camera_matrix'][0][0], optics['camera_matrix'][1][1])*.028*np.cos(np.pi/4)/distance
    return inside.reshape(len(points), -1).all(axis=1) & (marker_px >= 28.)


def central_boxes(axes):
    boxes = []
    for x,y,lo,hi in product(range(1,10), range(1,10), range(20,27), range(27,34)):
        boxes.append((2*x*.05*2*y*.05*(hi-lo)*.05,
                      [11-x,11-y,lo-20], [11+x,11+y,hi-20]))
    boxes.sort(reverse=True)
    return boxes


def contained_boxes(mask, shape, boxes):
    prefix = np.pad(mask.reshape(shape).astype(int), ((1,0),)*3).cumsum(0).cumsum(1).cumsum(2)
    lo = np.array([b[1] for b in boxes]); hi = np.array([b[2] for b in boxes])+1
    count = np.zeros(len(boxes), int)
    for corner in product((0,1), repeat=3):
        idx = np.where(np.array(corner), hi, lo)
        count += (-1)**(3-sum(corner))*prefix[tuple(idx.T)]
    return count == np.prod(hi-lo, axis=1)


def solve(source, output):
    began = time.monotonic()
    output.mkdir(parents=True, exist_ok=True)
    data = json.loads((source/'design-input.json').read_text())
    description = (source/'original.urdf').read_text()
    collision = CollisionModel((source/'collision.urdf').read_text(), output/'model')
    # The frozen hardware model's coupled opening-envelope exclusions.
    import xml.etree.ElementTree as ET
    srdf = ET.parse(source/'robot.srdf')
    for pair in srdf.findall('disable_collisions'):
        collision.scene.allowed_collision_matrix.set_entry(pair.get('link1'), pair.get('link2'), True)
    visibility = VisibilityModel(description, ROBOT_IDS)
    neutral = dict(data['reference_state'])
    frames0 = visibility.frames(neutral)
    centre = np.array([0., 0., 1.28])
    axes = [np.arange(-.55, .551, .05), np.arange(-.55, .551, .05), np.arange(1.00, 1.651, .05)]
    points = np.array(list(product(*axes)))
    boxes = central_boxes(axes)
    shape = tuple(map(len, axes))
    sets = {}
    rng = np.random.default_rng(231123)
    for rid in ROBOT_IDS:
        names = joint_names(rid)
        chain = Chain(description, 'world', rid+'_wrist_camera_optical_frame')
        elbow_chain = Chain(description, 'world', rid+'_forearm_link')
        bounds = np.array([collision.bounds[n] for n in names]).T
        base = frames0[rid+'_base_link'][:3, 3]
        qref = np.array([neutral[n] for n in names])
        if rid == 'right_front':
            # User unwound this base cable to the near-zero revolution on
            # 19Nov. The17Nov seed must never reintroduce its old -360deg turn.
            qref[0] -= 2*np.pi*round(qref[0]/(2*np.pi))
        side = np.sign(base[:2])
        candidates = []
        attempted = converged = 0
        optics = data['optics'][rid]
        pixel_centre = (np.array(optics['image_size'],float)-1)/2
        normalized = cv2.undistortPoints(pixel_centre.reshape(1,1,2),
            np.array(optics['camera_matrix']), np.array(optics['distortion'])).reshape(2)
        centre_ray = np.r_[normalized,1.]
        centre_ray /= np.linalg.norm(centre_ray)
        centre_alignment = Rotation.align_vectors([[0.,0.,1.]], [centre_ray])[0].as_matrix()
        from moveit.core.collision_detection import AllowedCollisionMatrix, CollisionRequest, CollisionResult
        all_links = [l.get('name') for l in ET.fromstring(description).findall('link')]+['calibration_floor']
        local_acm = AllowedCollisionMatrix(all_links, False)
        for a, b in combinations(all_links, 2):
            found, value = collision.scene.allowed_collision_matrix.get_entry(a, b)
            if found and value == 'ALWAYS':
                local_acm.set_entry(a, b, True)
            if any(a.startswith(r+'_') or b.startswith(r+'_') for r in ROBOT_IDS if r != rid):
                local_acm.set_entry(a, b, True)
        # Cameras stay outside the centre. Elevated views leave it accessible.
        eyes = [np.array([side[0]*x, side[1]*y, z])
                for x, y, z in product((.65, .8, .95), (.85, 1.05, 1.25), (1.5, 1.7, 1.9))]
        eyes.sort(key=lambda e: -np.linalg.norm(e-centre))
        for eye in eyes:
            if np.linalg.norm(eye-base) > 1.03:
                continue
            for roll in (0., np.pi):
                desired = look_at(eye, centre, roll)
                # Frame the working centre at the image centre. Several
                # measured native principal points are far from image centre;
                # simply aiming the optical z-axis wastes usable overlap.
                desired[:3,:3] = desired[:3,:3] @ centre_alignment
                def residual(q):
                    actual = chain.forward(dict(zip(names, q)))
                    return np.r_[actual[:3, 3]-eye,
                                 .22*Rotation.from_matrix(actual[:3, :3] @ desired[:3, :3].T).as_rotvec()]
                seeds = [qref, np.array(data['historical_view_seeds'][rid])]
                seeds += [rng.uniform(np.maximum(bounds[0], -np.pi), np.minimum(bounds[1], np.pi)) for _ in range(3)]
                for seed in seeds:
                    attempted += 1
                    fit = least_squares(residual, np.clip(seed, bounds[0]+1e-5, bounds[1]-1e-5),
                                        bounds=bounds, max_nfev=65, ftol=1e-7, xtol=1e-7, gtol=1e-7)
                    if np.linalg.norm(residual(fit.x)) > 2e-4:
                        continue
                    converged += 1
                    q = fit.x.copy()
                    for k, name in enumerate(names):
                        options = [q[k]+2*np.pi*n for n in range(-2, 3)
                                   if bounds[0, k]+.08 < q[k]+2*np.pi*n < bounds[1, k]-.08]
                        if not options:
                            break
                        q[k] = min(options, key=lambda v: abs(v-qref[k]))
                    else:
                        state = dict(neutral, **dict(zip(names, q)))
                        # Check this arm against the static environment and itself;
                        # other arms' historical parked positions must not prune
                        # otherwise feasible joint endpoint combinations.
                        collision.state.joint_positions = {k:float(v) for k,v in state.items() if k in collision.bounds}
                        collision.state.update()
                        req, res = CollisionRequest(), CollisionResult()
                        collision.scene.check_collision(req, res, collision.state, local_acm)
                        if res.collision:
                            continue
                        elbow = elbow_chain.forward(dict(zip(names, q)))[:3, 3]
                        # Contextual preference: elbow above the table and outside
                        # the central board-handling space, wrist away from peers.
                        if elbow[2] < 1.08 or abs(elbow[0]) < .22:
                            continue
                        T = chain.forward(state)
                        mask = fit_mask(points, T, data['optics'][rid])
                        frames = visibility.frames(state)
                        own_blocked = visibility.blocked(T[:3, 3], points, frames, arms=[rid],
                                                        ignore_links=[rid+'_wrist_camera_link'])
                        mask &= ~own_blocked
                        if mask.sum() < 100:
                            continue
                        if any(np.linalg.norm(q-np.array(e['joints_rad'])) < .08 for e in candidates):
                            continue
                        candidates.append(dict(joints_rad=q.tolist(), camera_world=T.tolist(),
                            distance_to_centre_m=float(np.linalg.norm(eye-centre)), elbow_world=elbow.tolist(),
                            fit_count=int(mask.sum()), mask=mask))
        candidates.sort(key=lambda e: (-e['fit_count'], -e['distance_to_centre_m']))
        # Keep geometric variety and a bounded endpoint combination search.
        kept = []
        for entry in candidates:
            if all(np.linalg.norm(np.array(entry['camera_world'])[:3, 3]-np.array(e['camera_world'])[:3, 3])>.08
                   or np.linalg.norm(np.array(entry['joints_rad'])-e['joints_rad'])>.7 for e in kept):
                kept.append(entry)
            if len(kept) == 10:
                break
        for entry in kept:
            entry['boxes'] = contained_boxes(entry['mask'], shape, boxes)
        sets[rid] = kept
        print(json.dumps(dict(arm=rid, attempted=attempted, converged=converged, accepted=len(candidates), kept=len(kept),
                              elapsed_s=time.monotonic()-began)), flush=True)
        if not kept:
            raise ValueError(rid+': no candidate')
    combos = []
    for entries in product(*(sets[r] for r in ROBOT_IDS)):
        mask = np.logical_and.reduce([e['mask'] for e in entries])
        valid_boxes = np.logical_and.reduce([e['boxes'] for e in entries])
        indices = np.flatnonzero(valid_boxes)
        box_volume = boxes[indices[0]][0] if len(indices) else 0.
        combos.append((box_volume, int(mask.sum()), sum(e['distance_to_centre_m'] for e in entries), entries, mask))
    combos.sort(key=lambda e:(e[0], e[1], e[2]), reverse=True)
    checked = 0
    for _, _, _, entries, mask in combos:
        state = dict(neutral)
        for rid, entry in zip(ROBOT_IDS, entries):
            state.update(zip(joint_names(rid), entry['joints_rad']))
        checked += 1
        if not collision.check(state)[0]:
            continue
        frames = visibility.frames(state)
        visible = mask.copy()
        for rid, entry in zip(ROBOT_IDS, entries):
            visible &= ~visibility.blocked(np.array(entry['camera_world'])[:3, 3], points, frames,
                                           ignore_links=[rid+'_wrist_camera_link'])
        if visible.sum() < .85*mask.sum():
            continue
        selected = {r:{k:v for k,v in e.items() if k not in ('mask','boxes')} for r,e in zip(ROBOT_IDS,entries)}
        result = dict(schema_version=1, kind='four_wrist_calibration_endpoint_proposal', executable=False,
            target_centre_world_m=centre.tolist(), selected=selected, target_state=state,
            common_board_centre_samples_world_m=points[visible].round(5).tolist(), grid_step_m=.05,
            common_sampled_volume_m3=float(visible.sum()*.05**3), endpoint_fcl_clear=True,
            combinations_checked=checked, runtime_s=time.monotonic()-began,
            optics=data['optics'], source_binding=data['source_binding'],
            criteria=dict(native_size=[2592,1944], paper_size_m=[.297,.210], marker_edge_m=.028,
                image_margin_px=70, paper_half_diagonal_m=.182, board_sphere_directions=26,
                aiming='native image-centre ray, undistorted with matching K/D',
                design_minimum_marker_edge_px=28, design_board_tilt_deg=45, optical_budget_factor=.9,
                centre_grid_bounds_m=[[-.55,.55],[-.55,.55],[1.,1.65]],
                minimum_elbow_height_m=1.08, minimum_absolute_elbow_x_m=.22),
            limitations=['Sampled finite search, not a proof of global maximum.',
                'Visibility bounds and support-direction samples are design estimates, not detection guarantees.',
                'No current-start trajectory: left_front NO_CONTROLLER, other drives off at preparation.',
                'Full gripper-opening hulls checked. People, loose cables and unmodelled objects not included.',
                'Left-front optical mount is nominal. Fixed user-adopted base bindings retained.',
                'Common volume refers to four wrists only; external cameras need fresh measured extrinsics.',
                'Fixed-arm images register the camera rig to external anchors. Independent motion-based hand-eye fitting/validation needs multiple arm poses.'])
        (output/'proposal.json').write_text(json.dumps(result, indent=2)+'\n')
        np.savez_compressed(output/'candidates.npz', **{r:np.array([e['joints_rad'] for e in sets[r]]) for r in ROBOT_IDS})
        print(json.dumps({k:v for k,v in result.items() if k in ('endpoint_fcl_clear','common_sampled_volume_m3','runtime_s','combinations_checked')}), flush=True)
        return
    raise ValueError('No complete collision-free endpoint combination')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    solve(args.input.resolve(), args.output.resolve())

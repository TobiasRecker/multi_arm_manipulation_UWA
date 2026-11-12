"""Offline candidate search for shared wrist/OAK views. Never commands robots."""
import argparse
from itertools import product
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from uwa_cell_description.configuration import load_layout, joint_names, ROBOT_IDS
from uwa_cell_gazebo.charuco import table_board_transform
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_calibration.model import CollisionModel
from .view_geometry import VisibilityModel, project_points


def look_at(eye, target):
    z = np.asarray(target) - eye
    z /= np.linalg.norm(z)
    x = np.array([1., 0, 0])
    x -= z * np.dot(x, z)
    if np.linalg.norm(x) < .1:
        x = np.cross(z, [0, 0, 1])
    x /= np.linalg.norm(x)
    result = np.eye(4)
    result[:3, :3] = np.column_stack([x, np.cross(z, x), z])
    result[:3, 3] = eye
    return result


def design(source, output):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    layout = load_layout(source/'model/layout.yaml')
    description = (source/'cell.urdf').read_text()
    states = json.loads((source/'states.json').read_text())
    start = states['start']
    pose = json.loads((source/'pose_estimate.json').read_text())
    optics = json.loads((source/'oak_rgb_intrinsics.json').read_text())
    matrix = np.array(optics['camera_matrix_8000x6000'])
    distortion = np.array(optics['distortion'])
    model = CollisionModel(description, output/'moveit')
    geometry = VisibilityModel(description, ROBOT_IDS)
    initial_frames = geometry.frames(start)
    world_camera = initial_frames['right_table_top'] @ np.array(
        pose['boards']['right']['T_table_camera_assuming_nominal_board_placement'])
    world_boards, board_points, table_points = {}, {}, []
    c = layout['charuco']
    local_corners = np.array([[x*c['square_length'], y*c['square_length'], 0]
                             for y in range(1, c['squares_y']) for x in range(1, c['squares_x'])])
    for table in ['left', 'right']:
        world_boards[table] = world_camera @ np.array(pose['boards'][table]['T_camera_board'])
        board_points[table] = (local_corners @ world_boards[table][:3, :3].T + world_boards[table][:3, 3])
        t = layout['tables'][table]
        local = np.array([[x, y, .008] for x in np.linspace(-t['width']/2+.025, t['width']/2-.025, 17)
                          for y in np.linspace(-t['length']/2+.025, t['length']/2-.025, 33)])
        frame = initial_frames[table+'_table_top']
        table_points.append(local @ frame[:3, :3].T + frame[:3, 3])
    table_points = np.concatenate(table_points)
    all_boards = np.concatenate(list(board_points.values()))
    _, oak_table_inside = project_points(table_points, world_camera, matrix, distortion, [8000, 6000])
    _, oak_board_inside = project_points(all_boards, world_camera, matrix, distortion, [8000, 6000])
    eye = world_camera[:3, 3]
    baseline_blocked = geometry.blocked(eye, table_points, initial_frames)
    baseline_board_blocked = geometry.blocked(eye, all_boards, initial_frames)
    neutral = {j: q for rid in ROBOT_IDS for j, q in zip(joint_names(rid), [0, -np.pi/2, 0, -np.pi/2, 0, 0])}
    candidate_sets = {}
    for rid in ROBOT_IDS:
        table = layout['robots'][rid]['table']
        names = joint_names(rid)
        q0 = np.array([start[j] for j in names])
        chain = Chain(description, 'world', rid+'_wrist_camera_optical_frame')
        bounds = np.array([model.bounds[j] for j in names]).T
        camera = layout.get('calibration', {}).get('robots', {}).get(rid, {}).get('camera')
        if camera:
            wk, wd, size = np.array(camera['camera_matrix']), np.array(camera['distortion']), camera['image_size']
        else:
            size = [640, 480]
            focal = size[0]/(2*np.tan(layout['robots'][rid]['tools']['camera_horizontal_fov']/2))
            wk, wd = np.array([[focal, 0, size[0]/2], [0, focal, size[1]/2], [0, 0, 1.]]), np.zeros(5)
        centre = world_boards[table] @ np.array([c['squares_x']*c['square_length']/2,
                                               c['squares_y']*c['square_length']/2, 0, 1])
        candidates = []
        side = -1 if rid.endswith('front') else 1
        seeds = [q0, np.asarray(layout['robots'][rid]['initial_positions'])]
        base = initial_frames[rid+'_base_link'][:3, 3]
        count = 0
        for x, y, height, roll in product((-.18, 0, .18), (.38, .50, .62), (.45, .60), (0., np.pi)):
            desired = look_at(centre[:3]+[x, side*y, height], centre[:3])
            desired[:3, :3] = desired[:3, :3] @ Rotation.from_euler('z', roll).as_matrix()
            if np.linalg.norm(desired[:3, 3]-base) > .93:
                continue
            def residual(q):
                actual = chain.forward(dict(zip(names, q)))
                return np.r_[actual[:3, 3]-desired[:3, 3],
                             .2*Rotation.from_matrix(actual[:3, :3]@desired[:3, :3].T).as_rotvec()]
            for seed in seeds:
                fit = least_squares(residual, np.clip(seed, bounds[0]+1e-6, bounds[1]-1e-6),
                                    bounds=bounds, max_nfev=90, ftol=1e-8, xtol=1e-8, gtol=1e-8)
                if np.linalg.norm(residual(fit.x)) > 1e-4:
                    continue
                q = fit.x.copy()
                for i in range(6):
                    variants = [q[i]+2*np.pi*k for k in (-1, 0, 1)
                                if bounds[0, i] <= q[i]+2*np.pi*k <= bounds[1, i]]
                    q[i] = min(variants, key=lambda v: abs(v-q0[i]))
                # Design preference for the already cable-sensitive wrist:
                # no extra wrist2 turn and at most90deg wrist3 change here.
                if abs(q[4]) > np.pi or abs(q[5]-q0[5]) > np.pi/2:
                    continue
                state = dict(neutral, **dict(zip(names, q)))
                if not model.check(state)[0]:
                    continue
                frames = geometry.frames(state)
                actual = frames[rid+'_wrist_camera_optical_frame']
                _, inside = project_points(board_points[table], actual, wk, wd, size, margin=12)
                blocked = geometry.blocked(actual[:3, 3], board_points[table], frames,
                                           arms=[rid], ignore_links=[rid+'_wrist_camera_link'])
                wrist_visible = int((inside & ~blocked).sum())
                if wrist_visible < 24:
                    continue
                oak_blocked = geometry.blocked(eye, table_points, frames, arms=[rid])
                oak_board_blocked = geometry.blocked(eye, all_boards, frames, arms=[rid])
                _, wi = project_points(table_points, actual, wk, wd, size, margin=12)
                own = geometry.blocked(actual[:3, 3], table_points, frames,
                                       arms=[rid], ignore_links=[rid+'_wrist_camera_link'])
                overlap = wi & ~own & oak_table_inside & ~oak_blocked
                cost = (8*np.mean(oak_blocked & oak_table_inside) + 5*np.mean(oak_board_blocked) -
                        2*np.mean(overlap) + .03*np.linalg.norm(q-q0))
                count += 1
                candidates.append({'joints':q.tolist(), 'camera_world':actual.tolist(), 'score':float(cost),
                                   'own_wrist_board_corners':wrist_visible,
                                   'optics_source':('nominal' if camera is None else
                                       layout['calibration']['robots'][rid].get('quality_status',
                                           {'intrinsics':'passed','handeye':'passed'})),
                                   'wrist_matrix':wk.tolist(), 'wrist_distortion':wd.tolist(), 'wrist_size':size,
                                   '_table_blocked':oak_blocked, '_board_blocked':oak_board_blocked})
            print(json.dumps({'arm':rid,'accepted':count,'candidate_xyz':desired[:3,3].tolist()}), flush=True)
        candidates.sort(key=lambda v:v['score'])
        distinct = []
        for entry in candidates:
            if all(np.linalg.norm(np.array(entry['joints'])-other['joints'])>.25 for other in distinct):
                distinct.append(entry)
            if len(distinct) >= 6:
                break
        if not distinct:
            raise ValueError(rid+': no collision-free24-corner candidate')
        candidate_sets[rid] = distinct
        print(json.dumps({'arm_finished':rid,'feasible':len(candidates),'kept':len(distinct)}),flush=True)
    best = None
    for combo in product(*(candidate_sets[rid] for rid in ROBOT_IDS)):
        state = dict(start)
        for rid, entry in zip(ROBOT_IDS, combo):
            state.update(zip(joint_names(rid), entry['joints']))
        if not model.check(state)[0]:
            continue
        blocked = np.logical_or.reduce([e['_table_blocked'] for e in combo])
        board_blocked = np.logical_or.reduce([e['_board_blocked'] for e in combo])
        cost = np.mean(blocked & oak_table_inside)*8 + np.mean(board_blocked)*5 + .02*sum(e['score'] for e in combo)
        if best is None or cost < best[0]:
            frames = geometry.frames(state)
            shared = {}
            for rid, entry in zip(ROBOT_IDS, combo):
                camera = np.array(entry['camera_world'])
                _, inside = project_points(board_points[layout['robots'][rid]['table']], camera,
                                           entry['wrist_matrix'], entry['wrist_distortion'], entry['wrist_size'], margin=12)
                seen = ~geometry.blocked(camera[:3,3], board_points[layout['robots'][rid]['table']], frames,
                                        ignore_links=[rid+'_wrist_camera_link']) & inside
                shared[rid] = int(seen.sum())
            if min(shared.values()) < 24:
                continue
            best = cost, combo, state, blocked, board_blocked
    if best is None:
        raise ValueError('No four-arm combination with24 visible board corners per wrist')
    _, combo, state, blocked, board_blocked = best
    result = {'schema_version':1, 'purpose':'offline observation-pose proposal; no hardware motion',
              'camera_pose_status':'rough; assumes nominal right board/table relation',
              'layout_profile':layout['calibration']['profile_id'], 'source_states':states['sources'],
              'state':state,'start':start,'T_world_oak_optical':world_camera.tolist(),
              'world_boards':{t:v.tolist() for t,v in world_boards.items()},
              'occlusion_method':'conservative local bounding boxes of URDF collision meshes, not rendered pixels',
              'oak_table_in_frame_fraction':float(oak_table_inside.mean()),
              'baseline_oak_clear_table_fraction':float((oak_table_inside & ~baseline_blocked).mean()),
              'proposal_oak_clear_table_fraction':float((oak_table_inside & ~blocked).mean()),
              'baseline_oak_clear_board_corners':int((oak_board_inside & ~baseline_board_blocked).sum()),
              'proposal_oak_clear_board_corners':int((oak_board_inside & ~board_blocked).sum()),
              'collision_free_combination':True,'paths_checked':False,
              'limitations':['No hardware motion; targets need fresh path planning and operator review',
                             'Nominal base mounts and approximately placed table boards',
                             'Left-front current state is declared home, not measured',
                             'Nominal camera housings, mesh bounding boxes and5mm near clipping',
                             'No cables, people, loose objects or physical tripod collision model',
                             'Front optics include explicit operator acceptance below automatic quality thresholds'],
              'arms':{rid:{k:v for k,v in entry.items() if not k.startswith('_')}
                      for rid,entry in zip(ROBOT_IDS,combo)}}
    frames = geometry.frames(state)
    for rid, entry in result['arms'].items():
        camera = np.array(entry['camera_world'])
        _, inside = project_points(table_points, camera,entry['wrist_matrix'],entry['wrist_distortion'],entry['wrist_size'],margin=12)
        own = geometry.blocked(camera[:3,3],table_points,frames,ignore_links=[rid+'_wrist_camera_link'])
        mask = inside & ~own & oak_table_inside & ~blocked
        entry['shared_clear_table_fraction_total'] = float(mask.mean())
        entry['shared_clear_area_m2_approx'] = float(mask.mean()*sum(t['width']*t['length'] for t in layout['tables'].values()))
    (output/'proposal.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in result if k not in ('state','start','arms','world_boards')},indent=2),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();design(args.source,args.output)


if __name__=='__main__':main()

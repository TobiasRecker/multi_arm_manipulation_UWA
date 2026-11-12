"""Offline, full-cell checked common-object view search. No motion clients.

Snapshots describe measured states at their recorded time. Even successful
results are review artifacts, never executable hardware commands.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from itertools import permutations, product
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import yaml

from uwa_cell_description.configuration import ROBOT_IDS, joint_names, load_layout, default_layout_path
from uwa_cell_gazebo.charuco import table_board_transform, make_board
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_calibration.planner import timed_path
from .parking import complete_state, digest, make_model
from .view_geometry import VisibilityModel, project_points, segment_box_hits


def box_points(size):
    size = np.asarray(size, float)
    if size.shape != (3,) or not np.isfinite(size).all() or min(size) <= 0:
        raise ValueError('Object size requires three positive finite metres')
    return np.asarray(list(product(*[[-v / 2, v / 2] for v in size])))


def target_geometry(layout, description, config):
    reference = config['reference_frame']
    if reference not in ('left_table_top', 'right_table_top', 'table_pair_midpoint'):
        raise ValueError('Expected an explicit tabletop reference frame')
    if reference == 'table_pair_midpoint':
        table = config.get('reference_board_table', 'right')
        if table not in ('left', 'right'):
            raise ValueError('Reference board must be left or right')
        tables = [Chain(description, 'world', t + '_table_top').forward({}) for t in ('left', 'right')]
        if abs(tables[0][2, 3] - tables[1][2, 3]) > .02:
            raise ValueError('Tabletop heights differ; common support plane requires a measured reference')
        frame = tables[1].copy()
        frame[:3, 3] = (tables[0][:3, 3] + tables[1][:3, 3]) / 2
    else:
        table = reference.removesuffix('_table_top')
        frame = Chain(description, 'world', reference).forward({})
    centre = np.asarray(config['centre_m'], float)
    if centre.shape != (3,) or not np.isfinite(centre).all():
        raise ValueError('Object centre requires three finite metres')
    obj = frame.copy()
    obj[:3, 3] = (frame @ np.r_[centre, 1])[:3]
    yaw = float(config.get('yaw_rad', 0.))
    if not np.isfinite(yaw):
        raise ValueError('Object yaw must be finite radians')
    obj[:3, :3] = frame[:3, :3] @ Rotation.from_euler('z', yaw).as_matrix()
    size = np.asarray(config['size_m'], float)
    local = box_points(size)
    world = local @ obj[:3, :3].T + obj[:3, 3]
    board = layout['charuco']
    references = {}
    for name in ('left', 'right'):
        table_frame = Chain(description, 'world', name + '_table_top').forward({})
        B = table_frame @ table_board_transform(board, name)
        points = np.asarray([[x * board['square_length'], y * board['square_length'], 0]
                             for y in range(1, board['squares_y']) for x in range(1, board['squares_x'])])
        points = points @ B[:3, :3].T + B[:3, 3]
        markers = np.asarray(make_board(board, name).getObjPoints()).reshape(-1, 3)
        markers = markers @ B[:3, :3].T + B[:3, 3]
        references[name] = dict(T_world_board=B, board_points=points, marker_points=markers)
    return dict(T_world_object=obj, bounds=np.array([-size / 2, size / 2]),
                corners=world, centre=obj[:3, 3], references=references,
                **references[table], table=table)


def look_at(eye, target, x_hint=(1., 0., 0.)):
    eye, target = np.asarray(eye, float), np.asarray(target, float)
    z = target - eye
    if np.linalg.norm(z) < 1e-6:
        raise ValueError('Camera and target must differ')
    z /= np.linalg.norm(z)
    x = np.asarray(x_hint, float) - z * np.dot(x_hint, z)
    if np.linalg.norm(x) < .01:
        x = np.cross(z, [0., 0., 1.])
    if np.linalg.norm(x) < .01:
        x = np.cross(z, [0., 1., 0.])
    x /= np.linalg.norm(x)
    pose = np.eye(4)
    pose[:3, :3], pose[:3, 3] = np.column_stack([x, np.cross(z, x), z]), eye
    return pose


def solve_ik(chain, names, desired, seed, bounds, max_change=None):
    seed = np.asarray(seed)
    lo, hi = np.asarray(bounds).T
    if max_change is not None:
        lo, hi = np.maximum(lo, seed - max_change), np.minimum(hi, seed + max_change)
    def residual(q):
        actual = chain.forward(dict(zip(names, q)))
        return np.r_[actual[:3, 3] - desired[:3, 3],
                     .2 * Rotation.from_matrix(actual[:3, :3] @ desired[:3, :3].T).as_rotvec()]
    fit = least_squares(residual, np.clip(seed, lo + 1e-7, hi - 1e-7), bounds=(lo, hi), max_nfev=70)
    if np.linalg.norm(residual(fit.x)) > 1e-4:
        return None
    q = fit.x.copy()
    for i in range(len(q)):
        variants = [q[i] + 2 * np.pi * k for k in (-1, 0, 1)
                    if lo[i] <= q[i] + 2 * np.pi * k <= hi[i]]
        q[i] = min(variants, key=lambda v: abs(v - seed[i]))
    return q


def optics(layout, rid):
    camera = layout.get('calibration', {}).get('robots', {}).get(rid, {}).get('camera')
    if camera:
        return dict(K=camera['camera_matrix'], D=camera['distortion'], size=camera['image_size'],
                    status='active intrinsic profile; planning projection only',
                    quality=layout['calibration']['robots'][rid].get('quality_status'))
    tools = layout['robots'][rid]['tools']
    size = [tools['camera_width'], tools['camera_height']]
    f = size[0] / (2 * np.tan(tools['camera_horizontal_fov'] / 2))
    return dict(K=[[f, 0, size[0]/2], [0, f, size[1]/2], [0, 0, 1]], D=[0.] * 5, size=size,
                status='nominal projection; no matching calibration', quality=None)


def visibility(geometry, frames, camera, target, intrinsic, ignore=()):
    _, inside = project_points(target['corners'], camera, intrinsic['K'], intrinsic['D'],
                               intrinsic['size'], margin=12)
    # Full bounds inside image is separate from surface/board occlusion.
    blocked = geometry.blocked(camera[:3, 3], target['corners'], frames, ignore_links=ignore)
    references = {}
    for name, reference in target['references'].items():
        points, markers = reference['board_points'], reference['marker_points']
        _, board_inside = project_points(points, camera, intrinsic['K'], intrinsic['D'], intrinsic['size'], margin=12)
        board_blocked = geometry.blocked(camera[:3, 3], points, frames, ignore_links=ignore)
        board_blocked |= segment_box_hits(camera[:3, 3], points, target['T_world_object'], target['bounds'])
        _, marker_inside = project_points(markers, camera, intrinsic['K'], intrinsic['D'], intrinsic['size'], margin=12)
        marker_blocked = geometry.blocked(camera[:3, 3], markers, frames, ignore_links=ignore)
        marker_blocked |= segment_box_hits(camera[:3, 3], markers, target['T_world_object'], target['bounds'])
        complete_markers = int((marker_inside & ~marker_blocked).reshape(-1, 4).all(axis=1).sum())
        chess_visible = points[board_inside & ~board_blocked]
        rank = int(np.linalg.matrix_rank(chess_visible - chess_visible.mean(axis=0))) if len(chess_visible) else 0
        references[name] = dict(visible_reference_corners=int(len(chess_visible)), reference_chess_rank=rank,
                                visible_complete_reference_markers=complete_markers)
    best = max(references, key=lambda name: references[name]['visible_complete_reference_markers'])
    reference_ok = references[best]['visible_complete_reference_markers'] >= 2
    return dict(all_bounds_in_frame=bool(inside.all()), unblocked_box_corners=int((inside & ~blocked).sum()),
                reference_table=best, reference_views=references, **references[best],
                reference_pose_geometrically_supported=reference_ok,
                passes=bool(inside.all() and (inside & ~blocked).sum() >= 4 and reference_ok))


def add_object_collision(model, target, padding):
    from moveit_msgs.msg import CollisionObject
    from shape_msgs.msg import SolidPrimitive
    from geometry_msgs.msg import Pose
    if not np.isfinite(padding) or padding < 0:
        raise ValueError('Collision padding must be finite and nonnegative')
    obj = CollisionObject()
    obj.header.frame_id, obj.id = 'world', 'digitization_object_envelope'
    shape = SolidPrimitive(type=SolidPrimitive.BOX)
    # Leave the support-facing bottom unchanged: symmetric padding would
    # penetrate the tabletop and invalidate every state before any arm moved.
    shape.dimensions = (target['bounds'][1] - target['bounds'][0] + [2 * padding, 2 * padding, padding]).tolist()
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = (
        target['centre'] + target['T_world_object'][:3, :3] @ [0, 0, padding / 2]).tolist()
    q = Rotation.from_matrix(target['T_world_object'][:3, :3]).as_quat()
    pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w = q.tolist()
    obj.primitives, obj.primitive_poses, obj.operation = [shape], [pose], CollisionObject.ADD
    model.scene.apply_collision_object(obj)


def candidates_for_arm(model, layout, geometry, start, target, rid, config):
    names = joint_names(rid)
    q0 = np.array([start[j] for j in names])
    chain = Chain(model.description, 'world', rid + '_wrist_camera_optical_frame')
    base = Chain(model.description, 'world', rid + '_base_link').forward({})[:3, 3]
    azimuth = np.arctan2(*(base - target['centre'])[[1, 0]])
    intrinsic = optics(layout, rid)
    result, reasons = [], dict(ik=0, collision=0, visibility=0, bounds_outside_image=0,
                              object_occluded=0, reference_not_visible=0)
    for radius, height, angle, roll in product(config['horizontal_distances_m'], config['heights_above_centre_m'],
                                              config['azimuth_offsets_deg'], config['roll_deg']):
        a = azimuth + np.deg2rad(angle)
        eye = target['centre'] + [radius * np.cos(a), radius * np.sin(a), height]
        desired = look_at(eye, target['centre'])
        desired[:3, :3] = desired[:3, :3] @ Rotation.from_euler('z', roll, degrees=True).as_matrix()
        accepted = False
        seeds = [q0, np.asarray(layout['robots'][rid]['initial_positions'])]
        for seed in seeds:
            q = solve_ik(chain, names, desired, seed, [model.bounds[j] for j in names])
            if q is None:
                continue
            accepted = True
            if any(np.linalg.norm(q - c['joints']) < .15 for c in result):
                break
            state = dict(start, **dict(zip(names, q)))
            if not model.check(state)[0]:
                reasons['collision'] += 1
                continue
            frames = geometry.frames(state)
            actual = frames[rid + '_wrist_camera_optical_frame']
            view = visibility(geometry, frames, actual, target, intrinsic, [rid + '_wrist_camera_link'])
            if not view['passes']:
                reasons['visibility'] += 1
                reasons['bounds_outside_image'] += int(not view['all_bounds_in_frame'])
                reasons['object_occluded'] += int(view['unblocked_box_corners'] < 4)
                reasons['reference_not_visible'] += int(not view['reference_pose_geometrically_supported'])
                continue
            result.append(dict(joints=q.tolist(), camera_world=actual.tolist(), view=view,
                               score=float(np.linalg.norm(q - q0)), optics=intrinsic))
            break
        if not accepted:
            reasons['ik'] += 1
    result.sort(key=lambda c: c['score'])
    return result[:config['keep_per_arm']], reasons


def checked_schedule(model, start, candidates, final_check, *, velocity=.05, acceleration=.10):
    """Backtrack across serial arm orders and candidates; sweep every connection."""
    if not 0 < velocity <= .1 or not 0 < acceleration <= .2:
        raise ValueError('Motion limits exceed 0.10 rad/s or 0.20 rad/s²')
    if not model.check(start)[0]:
        raise ValueError('Full-cell start state is invalid')
    arms = tuple(candidates)
    if not arms or any(not candidates[rid] for rid in arms):
        return None
    for order in permutations(arms):
        def search(state, index, steps):
            if index == len(order):
                return (state, steps) if final_check(state) else None
            rid = order[index]
            for entry in candidates[rid]:
                try:
                    points = timed_path(model, rid, state, entry['joints'], velocity, acceleration)
                except ValueError:
                    continue
                end = dict(state, **dict(zip(joint_names(rid), entry['joints'])))
                step = dict(arm=rid, start=dict(state), target=entry['joints'], points=points,
                            camera_world=entry['camera_world'], purpose='common_object_initial_view')
                found = search(end, index + 1, steps + [step])
                if found is not None:
                    return found
            return None
        found = search(dict(start), 0, [])
        if found is not None:
            return found
    return None


def extra_views(model, layout, geometry, state, target, config):
    state = dict(state)
    steps, rejected = [], []
    for rid in ROBOT_IDS:
        names = joint_names(rid)
        chain = Chain(model.description, 'world', rid + '_wrist_camera_optical_frame')
        centre_pose = chain.forward(state)
        for dx, dy in config['extra_camera_xy_offsets_m']:
            desired = look_at(centre_pose[:3, 3] + centre_pose[:3, 0] * dx + centre_pose[:3, 1] * dy,
                              target['centre'], centre_pose[:3, 0])
            seed = [state[j] for j in names]
            q = solve_ik(chain, names, desired, seed, [model.bounds[j] for j in names],
                         max_change=config['extra_max_joint_change_rad'])
            if q is None:
                rejected.append(dict(arm=rid, offset=[dx, dy], reason='local IK unavailable'))
                continue
            endpoint = dict(state, **dict(zip(names, q)))
            frames = geometry.frames(endpoint)
            actual = frames[rid + '_wrist_camera_optical_frame']
            view = visibility(geometry, frames, actual, target, optics(layout, rid), [rid + '_wrist_camera_link'])
            if not view['passes']:
                rejected.append(dict(arm=rid, offset=[dx, dy], reason='object bounds/occlusion'))
                continue
            try:
                points = timed_path(model, rid, state, q, config['velocity_rad_s'], config['acceleration_rad_s2'])
            except ValueError:
                rejected.append(dict(arm=rid, offset=[dx, dy], reason='full-cell path collision'))
                continue
            steps.append(dict(arm=rid, start=dict(state), target=q.tolist(), points=points,
                              camera_world=actual.tolist(), purpose='additional_object_view', offset_camera_xy_m=[dx, dy]))
            state = endpoint
    return steps, rejected


def plan_scan(layout, model, start, sources, config):
    geometry = VisibilityModel(model.description, ROBOT_IDS)
    target = target_geometry(layout, model.description, config)
    add_object_collision(model, target, config['collision_padding_m'])
    result = dict(schema=1, purpose='object_scan_review_only', executable=False, hardware_commands=False,
                  created_at=datetime.now(timezone.utc).isoformat(), start=start, state_sources=sources,
                  layout_profile=layout.get('calibration', {}).get('profile_id', 'nominal'),
                  design=config, T_world_object=target['T_world_object'].tolist(),
                  T_world_board=target['T_world_board'].tolist(), candidates={}, steps=[],
                  common_view_found=False, paths_checked=False,
                  limitations=['Table/base world anchors and some optical mounts remain provisional.',
                               'Object envelope is a design assumption, not a new measurement.',
                               'No cable, person or physical tripod collision geometry.',
                               'Snapshot is not current execution authorization.',
                               'Active projection profiles may differ from native-HD acquisition optics.'])
    if not model.check(start)[0]:
        result['failure'] = 'Start collides with modeled cell/object envelope; no route searched'
        return result
    candidates = {}
    for rid in ROBOT_IDS:
        entries, reasons = candidates_for_arm(model, layout, geometry, start, target, rid, config)
        candidates[rid] = entries
        result['candidates'][rid] = dict(accepted=len(entries), rejected=reasons, entries=entries)
        print(json.dumps(dict(arm=rid, accepted=len(entries), rejected=reasons)), flush=True)
    oak = layout.get('calibration', {}).get('overview_camera')
    def all_visible(state):
        frames = geometry.frames(state)
        views = {rid: visibility(geometry, frames, frames[rid + '_wrist_camera_optical_frame'], target,
                                 optics(layout, rid), [rid + '_wrist_camera_link']) for rid in ROBOT_IDS}
        if oak:
            camera = np.asarray(oak['registration']['T_world_oak_optical'])
            factory = oak['factory']
            views['oak4'] = visibility(geometry, frames, camera, target,
                dict(K=factory['camera_matrix_8000x6000'], D=factory['distortion'], size=[8000, 6000]))
        else:
            views['oak4'] = dict(passes=False, reason='No registered OAK profile')
        result['last_combination_visibility'] = views
        return all(v['passes'] for v in views.values())
    schedule = checked_schedule(model, start, candidates, all_visible,
                                velocity=config['velocity_rad_s'], acceleration=config['acceleration_rad_s2'])
    if schedule is None:
        result['failure'] = 'No common five-camera view with fully checked serial connections found in this search'
        return result
    state, steps = schedule
    result.update(common_view_found=True, paths_checked=True, common_state=state, steps=steps,
                  common_visibility=deepcopy(result['last_combination_visibility']))
    additional, rejected = extra_views(model, layout, geometry, state, target, config)
    result['steps'].extend(additional)
    result['rejected_extra_views'] = rejected
    result['unique_view_count'] = 5 + len(additional)
    return result


def read_live_snapshot(inventory):
    """ROS subscriptions only; no driver startup, controllers or actions."""
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.signals import SignalHandlerOptions
    from match_ur_hardware.profiles import load_profiles
    from .park_arm import JointObserver
    profiles = load_profiles(inventory)
    context = Context()
    rclpy.init(args=[], context=context, domain_id=66, signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('uwa_object_scan_snapshot', context=context)
    observer = JointObserver(node, profiles, ROBOT_IDS, 'hardware')
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(node)
    try:
        deadline = time.monotonic() + 3.
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.05)
        readings = {rid: dict(record) for rid, record in observer.received.items()
                    if time.monotonic() - record['received_monotonic'] < .5}
        return dict(mode='hardware', arms=readings, source='read-only ROS JointState subscriptions',
                    recorded_at=datetime.now(timezone.utc).isoformat())
    finally:
        executor.shutdown()
        observer.close()
        node.destroy_node()
        context.try_shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='Read-only saved mode/arms JointState snapshot')
    parser.add_argument('--read-live-state', action='store_true', help='Read all four joint states; never start drivers')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--layout', type=Path, default=default_layout_path())
    parser.add_argument('--inventory', type=Path, default=Path(__file__).resolve().parents[2] / 'config/hardware_inventory.yaml')
    parser.add_argument('--preview-step', type=int, help='Only preview an existing report step on domain73')
    args = parser.parse_args()
    if args.preview_step is not None:
        from .parking_preview import preview
        preview(args.output / f'review_step_{args.preview_step:03d}.json', domain=73)
        return
    if (args.snapshot is None and not args.read_live_state) or args.config is None:
        parser.error('Provide --config and either --snapshot or --read-live-state')
    if args.snapshot is not None and args.read_live_state:
        parser.error('Choose a saved snapshot or --read-live-state')
    from match_ur_hardware.profiles import load_profiles
    config = yaml.safe_load(args.config.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    if args.read_live_state:
        snapshot = read_live_snapshot(args.inventory)
        args.snapshot = args.output / 'snapshot.json'
        args.snapshot.write_text(json.dumps(snapshot, indent=2) + '\n')
    else:
        snapshot = json.loads(args.snapshot.read_text())
    if snapshot.get('mode') not in ('hardware', 'mock'):
        raise ValueError('Snapshot requires explicit hardware/mock provenance')
    layout = load_layout(args.layout)
    start, sources, missing = complete_state(layout, snapshot['arms'])
    expected_source = 'live_joint_states' if snapshot['mode'] == 'hardware' else 'mock_joint_states'
    if missing or any(sources[rid] != expected_source for rid in ROBOT_IDS):
        raise ValueError('All four measured joint states are required; no home/layout substitution')
    profiles = load_profiles(args.inventory)
    model, layout = make_model(layout, profiles, args.output / 'model')
    result = plan_scan(layout, model, start, sources, config)
    result.update(snapshot=str(args.snapshot.resolve()), snapshot_sha256=digest(snapshot),
                  config_sha256=digest(config), description_sha256=digest(model.description),
                  snapshot_recorded_at={rid: snapshot['arms'][rid].get('recorded_at') for rid in ROBOT_IDS})
    (args.output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    (args.output / 'cell.urdf').write_text(model.description)
    for index, step in enumerate(result['steps']):
        chain = Chain(model.description, 'world', step['arm'] + '_tool0')
        preview = dict(step, description=model.description, layout=layout, joint_names=joint_names(step['arm']),
                       duration=step['points'][-1]['time'], state_sources=sources, unobserved_arms=[],
                       executable=False, mode=snapshot['mode'], purpose='OBJECT SCAN REVIEW ONLY',
                       tool_path_world=[chain.forward(dict(step['start'], **dict(zip(joint_names(step['arm']), p['positions']))))[:3, 3].tolist()
                                        for p in step['points']])
        (args.output / f'review_step_{index:03d}.json').write_text(json.dumps(preview, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ('common_view_found', 'paths_checked', 'executable')}
                     | dict(report=str(args.output / 'report.json'), steps=len(result['steps']))), flush=True)


if __name__ == '__main__':
    main()

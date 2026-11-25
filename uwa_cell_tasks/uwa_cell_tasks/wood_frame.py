"""Offline, object-led compilation for the three-arm wood frame recipe."""
from dataclasses import asdict, dataclass
import hashlib
from itertools import combinations, permutations, product
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import brentq
from scipy.spatial.transform import Rotation

from match_cooperative_handling.rigid_object import interpolate, pose_error
from uwa_cell_calibration.model import CollisionModel
from uwa_cell_description.configuration import ROBOT_IDS, default_layout_path, gripper_joint, joint_names, load_layout
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_gazebo.configuration import render_description
from uwa_cell_motion.carton_paths import solve_near
from uwa_cell_motion.common import PAIRS, all_names, nominal_state
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_motion.two_arm_teacher import box_separation, point_box_distance
from .contact_drawing import controller_spline
from .core import GraspGroup, configuration, digest, seal, write_json
from .pilot_episode import Episode
from .scene import fingertip_contact_primitives, inherit_pad_adjacency
from .workpiece_paths import AxialFeed, SurfaceFrame


HOLDERS = ('right_front', 'right_rear')
WORKERS = ('left_front', 'left_rear')
BEAM_ID = 'crossbar'
MODEL_STATUS = 'MODEL_SEQUENCE_COMPLETE'
FIXTURE_CENTER_Y_M = .135


@dataclass(frozen=True)
class FrameRecipe:
    beam_size_m: tuple = (.600, .038, .089)
    post_size_m: tuple = (.038, .038, .350)
    post_spacing_m: float = .340
    setback_m: float = .040
    site_vertical_m: float = .020
    mount_x_m: float = .298
    start_x_m: float = .155
    tool_length_m: float = .300

    def __post_init__(self):
        sizes = np.array([self.beam_size_m, self.post_size_m], float)
        if sizes.shape != (2, 3) or not np.isfinite(sizes).all() or np.min(sizes) <= 0:
            raise ValueError('Beam and post sizes must be finite positive xyz dimensions')
        offsets = (self.post_spacing_m, self.setback_m, self.site_vertical_m, self.tool_length_m)
        if not np.isfinite([*offsets, self.mount_x_m, self.start_x_m]).all() or min(offsets) <= 0:
            raise ValueError('Frame offsets must be finite and the sizes positive')
        length, width, height = sizes[0]
        post_span, thickness, post_height = sizes[1]
        if (length <= self.post_spacing_m + post_span or self.post_spacing_m <= post_span
                or 2*self.site_vertical_m >= height or self.setback_m + height >= post_height
                or width >= .080 or self.tool_length_m <= .239):
            raise ValueError('Stock dimensions do not fit the overlap, screw and gripper recipe')


def pose(position, yaw=np.pi/2):
    matrix = np.eye(4)
    matrix[:3, :3] = Rotation.from_rotvec([0., 0., yaw]).as_matrix()
    matrix[:3, 3] = position
    return matrix


def translate(matrix, delta):
    result = matrix.copy()
    result[:3, 3] += delta
    return result


def fixture(recipe, table_z, center_y, shift):
    beam = pose((recipe.start_x_m + shift[0], center_y + shift[1],
                 table_z + recipe.beam_size_m[2]/2), np.pi/2 + shift[2])
    posts = [
        dict(id=side, size_m=recipe.post_size_m, pose=pose((recipe.mount_x_m,
             center_y + sign*recipe.post_spacing_m/2, table_z + recipe.post_size_m[2]/2)))
        for side, sign in (('front_post', -1), ('rear_post', 1))
    ]
    return beam, posts


def assembly(recipe, beam, posts, worker):
    first, second = [item['pose'] for item in posts]
    u = second[:3, 3] - first[:3, 3]
    u[2] = 0.
    span = np.linalg.norm(u)
    if span <= recipe.post_size_m[0] or span + recipe.post_size_m[0] >= recipe.beam_size_m[0]:
        raise ValueError('Measured post spacing does not leave a usable overlap')
    u /= span
    up = np.array([0., 0., 1.])
    outward = np.cross(up, u)
    top = min(first[2, 3], second[2, 3]) + recipe.post_size_m[2]/2
    center = (first[:3, 3] + second[:3, 3])/2
    front_plane = max(outward @ matrix[:3, 3] + abs(matrix[:3, :3].T @ outward) @
                      (np.array(recipe.post_size_m)/2) for matrix in (first, second))
    center += outward * (front_plane - outward @ center + recipe.beam_size_m[1]/2 + .00005)
    center[2] = top - recipe.setback_m - recipe.beam_size_m[2]/2
    target = np.eye(4)
    target[:3, :3] = np.column_stack((u, outward, up))
    target[:3, 3] = center
    face = SurfaceFrame(tuple(center + outward*recipe.beam_size_m[1]/2), tuple(outward), tuple(u))
    sites = []
    for post in posts:
        horizontal = float(np.dot(post['pose'][:3, 3] - center, u))
        for label, vertical in (('upper', recipe.site_vertical_m), ('lower', -recipe.site_vertical_m)):
            uv = (horizontal, -vertical)
            sites.append(dict(id=f"{post['id']}_{label}", side=post['id'], uv_m=uv,
                              entry_m=face.tool_pose(uv)[:3, 3], direction=-outward))
    return dict(
        beam=dict(size_m=recipe.beam_size_m, start_pose=beam, target_pose=target),
        posts=posts, holders=HOLDERS, parked=next(arm for arm in WORKERS if arm != worker),
        tool=dict(arm=worker, tool0_to_tip=pose([0., 0., recipe.tool_length_m], 0.),
                  shaft_radius_m=.006, shaft_end_m=recipe.tool_length_m-.004,
                  body_radius_m=.024, body_start_m=.176,
                  body_end_m=recipe.tool_length_m-.063),
        screws=sites,
    ), face


def xyz(values):
    return ' '.join(map(str, values))


def with_tool(description, tool):
    root = ET.fromstring(description)
    arm = tool['arm']
    name = arm + '_wood_frame_driver'
    link = ET.SubElement(root, 'link', name=name)
    for radius, lo, hi in (
        (tool['body_radius_m'], tool['body_start_m'], tool['body_end_m']),
        (tool['shaft_radius_m'], tool['body_end_m'], tool['shaft_end_m']),
    ):
        collision = ET.SubElement(link, 'collision')
        ET.SubElement(collision, 'origin', xyz=xyz([0., 0., (hi+lo)/2]))
        ET.SubElement(ET.SubElement(collision, 'geometry'), 'cylinder',
                      radius=str(radius), length=str(hi-lo))
    joint = ET.SubElement(root, 'joint', name=name+'_mount', type='fixed')
    ET.SubElement(joint, 'parent', link=arm+'_tool0')
    ET.SubElement(joint, 'child', link=name)
    return ET.tostring(root, encoding='unicode')


def box_message(name, matrix, size, operation):
    from geometry_msgs.msg import Pose
    from moveit_msgs.msg import CollisionObject
    from shape_msgs.msg import SolidPrimitive

    message = CollisionObject()
    message.header.frame_id = 'world'
    message.id, message.operation = name, operation
    p = Pose()
    p.position.x, p.position.y, p.position.z = map(float, matrix[:3, 3])
    p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w = map(
        float, Rotation.from_matrix(matrix[:3, :3]).as_quat())
    message.primitive_poses = [p]
    if operation == CollisionObject.ADD:
        message.primitives = [SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(size))]
    return message


class WoodModel:
    def __init__(self, directory, description, layout, scene):
        from moveit_msgs.msg import CollisionObject

        self.scene = scene
        self.worker = scene['tool']['arm']
        self.fingers = {}
        self.chains = {arm: Chain(description, 'world', arm+'_tool0') for arm in ROBOT_IDS}
        self.description = with_tool(description, scene['tool'])
        self.collision = CollisionModel(self.description, directory)
        inherit_pad_adjacency(self.collision, directory/'robot.srdf')
        self.spheres = SphereModel(self.description, all_names(layout))
        self.layout = layout
        self.home = nominal_state(layout)
        self.names = tuple(j for arm in ROBOT_IDS for j in joint_names(arm))
        self.slices = {arm: [self.names.index(j) for j in joint_names(arm)] for arm in ROBOT_IDS}
        self.half_beam = np.array(scene['beam']['size_m'])/2
        self.table_z = layout['tables']['right']['height'] + layout['tables']['right']['xyz'][2]
        self.post_bounds = [(item['id'], item['pose'], np.array(item['size_m'])/2)
                            for item in scene['posts']]
        self.pads = {}
        root = ET.fromstring(description)
        for arm in HOLDERS:
            self.fingers[arm] = {
                joint.get('name'): float(joint.find('mimic').get('multiplier', 1.))
                for joint in root.findall('joint')
                if joint.get('name').startswith(arm+'_robotiq_85_') and joint.find('mimic') is not None
            }
            for side in ('left', 'right'):
                name = arm + '_robotiq_85_' + side + '_finger_tip_pad_link'
                geometry = root.find(f"link[@name='{name}']/collision")
                origin = np.fromstring(geometry.find('origin').get('xyz'), sep=' ')
                half = np.fromstring(geometry.find('geometry/box').get('size'), sep=' ')/2
                self.pads[arm, side] = (name, Chain(description, arm+'_tool0', name), origin, half)
        for name, matrix, half in self.post_bounds:
            self.collision.scene.apply_collision_object(box_message(name, matrix, half*2, CollisionObject.ADD))
            gap = matrix[2, 3] - abs(matrix[2, :3]) @ half - self.table_z
            if abs(gap) > .00025:
                raise ValueError(f'{name} is outside its tabletop mounting plane')
            self.collision.scene.allowed_collision_matrix.set_entry('right_table_plate', name, True)
        initial = scene['beam']['start_pose']
        self.collision.scene.apply_collision_object(box_message(BEAM_ID, initial, self.half_beam*2, CollisionObject.ADD))
        self.beam = initial.copy()
        self.tip = np.array(scene['tool']['tool0_to_tip'])
        self.allowed = None

    def angles(self, arm, angle):
        return {gripper_joint(arm): angle, **{j: angle*k for j, k in self.fingers[arm].items()}}

    def grip_geometry(self):
        _, chain, origin, half = self.pads[HOLDERS[0], 'left']
        def point(angle):
            transform = chain.forward(self.angles(HOLDERS[0], angle))
            return transform[:3, :3] @ (origin - [half[0], 0., 0.]) + transform[:3, 3]
        angle = brentq(lambda a: point(a)[0] - self.half_beam[1], 0., .8)
        return float(angle), float(point(angle)[2])

    def state(self, row, finger):
        state = dict(self.home, **dict(zip(self.names, row)))
        state.update({gripper_joint(arm): finger for arm in HOLDERS})
        return state

    def clear(self, beam, row, finger, *, gripping=False, seated=False, screw=None, margin=False):
        from moveit_msgs.msg import CollisionObject

        if not np.array_equal(beam, self.beam):
            self.collision.scene.apply_collision_object(box_message(BEAM_ID, beam, self.half_beam*2,
                                                                    CollisionObject.MOVE))
            self.beam = beam.copy()
        table_gap = float(beam[2, 3] - abs(beam[2, :3]) @ self.half_beam - self.table_z)
        if table_gap < -.0002:
            return f'beam penetrates tabletop ({table_gap:.5f} m)'
        for name, matrix, half in self.post_bounds:
            gap = box_separation(beam, self.half_beam, matrix, half)
            if gap < (-.0002 if seated else -1e-8):
                return f'beam penetrates {name} ({gap:.5f} m)'
        state = self.state(row, finger)
        for (arm, side), (name, chain, origin, _) in self.pads.items():
            if gripping:
                pad = (self.chains[arm].forward(state) @ chain.forward(self.angles(arm, finger)))[:3]
                center = beam[:3, :3].T @ (pad[:, :3] @ origin + pad[:, 3] - beam[:3, 3])
                if abs(center[0]) > self.half_beam[0]-.008 or abs(center[2]) > self.half_beam[2]+.025:
                    return f'{name} outside its grip region'
        allowed = gripping, table_gap <= .00025
        if allowed != self.allowed:
            matrix = self.collision.scene.allowed_collision_matrix
            for name, *_ in self.pads.values():
                matrix.set_entry(name, BEAM_ID, gripping)
            matrix.set_entry('right_table_plate', BEAM_ID, allowed[1])
            self.allowed = allowed
        if not self.collision.check(state)[0]:
            return 'full-cell FCL contact'
        worldtip = (self.chains[self.worker].forward(state) @ self.tip)[:3, 3]
        localtip = beam[:3, :3].T @ (worldtip - beam[:3, 3])
        if point_box_distance(localtip[None], self.half_beam)[0][0] < -1e-6:
            if screw is None:
                return 'virtual bit enters beam away from a screw phase'
            offset = worldtip - screw['entry_m']
            axial = float(offset @ screw['direction'])
            lateral = np.linalg.norm(offset - axial*screw['direction'])
            if lateral > .001 or axial > .0032:
                return 'virtual bit outside screw-site corridor'
        if margin:
            world, bounds = self.spheres.planning_world(state)
            for a, b in PAIRS:
                if not self.spheres.pair_clear(world, bounds, a, b, .040):
                    return f'40 mm model margin: {a} / {b}'
        return None

    def solve(self, arm, target, row):
        selection = self.slices[arm]
        q = solve_near(self, arm, self.state(row, 0.), target, row[selection])
        if np.max(np.abs(q-row[selection])) > .42:
            raise ValueError(f'{arm}: discontinuous Cartesian branch')
        row[selection] = q

    def branches(self, arm, target, row):
        selection = self.slices[arm]
        initial = row[selection]
        seeds = [initial]
        for elbow, wrist in product((1.7, -1.7), (1.6, -1.6)):
            for pan in (initial[0], initial[0]+np.pi, initial[0]-np.pi):
                seeds.append(np.array([pan, -1.55, elbow, -1.6, wrist, initial[5]]))
        found = []
        for seed in seeds:
            try:
                q = solve_near(self, arm, self.state(row, 0.), target, seed)
            except ValueError:
                continue
            q += 2*np.pi*np.round((initial-q)/(2*np.pi))
            if not all(lo <= x <= hi for (lo, hi), x in zip(
                       (self.collision.bounds[self.names[i]] for i in selection), q)):
                continue
            if all(np.linalg.norm(q-other) > 1e-3 for other in found):
                found.append(q)
        return sorted(found, key=lambda q: np.linalg.norm(q-initial))


def shifted_shape_tool(pose, roll):
    rotation = np.eye(4)
    rotation[:3, :3] = Rotation.from_rotvec([0., 0., roll]).as_matrix()
    return pose @ rotation


def holder_targets(beam, distance, grasp_z, flips, height):
    down = -beam[:3, 2]
    targets = {}
    for arm, sign, flip in zip(HOLDERS, (-1, 1), flips):
        closing = beam[:3, 1] * flip
        target = np.eye(4)
        target[:3, :3] = np.column_stack((closing, np.cross(down, closing), down))
        target[:3, 3] = beam[:3, 3] + sign*distance*beam[:3, 0] - down*(grasp_z + height)
        targets[arm] = target
    return targets


def cartesian(model, row, start, end, targets, *, samples=16):
    rows = [row.copy()]
    for progress in np.linspace(0, 1, samples+1)[1:]:
        following = rows[-1].copy()
        for arm, target in targets(interpolate(start, end, progress), progress).items():
            model.solve(arm, target, following)
        rows.append(following)
    return np.array(rows)


def assert_clear(model, rows, beam, finger, label, *, gripping=False, seated=False, screw=None):
    for idx, row in enumerate(rows):
        value = beam(idx, row) if callable(beam) else beam
        reason = model.clear(value, row, finger, gripping=gripping, seated=seated, screw=screw, margin=True)
        if reason:
            raise ValueError(f'{label} point {idx}/{len(rows)-1}: {reason}')


def free_path(model, start, end, arms, beam, label, *, seated=False):
    """Search unobstructed free connections before using Cartesian primitives."""
    def sample(points):
        return np.concatenate([np.linspace(a, b, 26, endpoint=False)
                               for a, b in zip(points, points[1:])] + [points[-1][None]])

    candidates = [[start, end]]
    for order in permutations(arms):
        path = [start]
        for arm in order:
            following = path[-1].copy()
            following[model.slices[arm]] = end[model.slices[arm]]
            path.append(following)
        candidates.append(path)
    for shoulder_delta in (-.25, .25, -.45, .45):
        control = (start+end)/2
        for arm in arms:
            control[model.slices[arm][1]] += shoulder_delta
        candidates.append([start, control, end])
    first_failure = None
    for candidate in candidates:
        try:
            assert_clear(model, sample(candidate), beam, 0., label, seated=seated)
            return candidate
        except ValueError as error:
            first_failure = first_failure or error
    raise first_failure


def pick(model, home, angle, grasp_z, distance, flips, height):
    beam = model.scene['beam']['start_pose']
    targets = holder_targets(beam, distance, grasp_z, flips, height)
    pre = {arm: translate(target, [0., 0., .090]) for arm, target in targets.items()}
    solutions = [model.branches(arm, pre[arm], home) for arm in HOLDERS]
    errors = []
    for combination in product(*(options[:4] for options in solutions)):
        goal = home.copy()
        for arm, q in zip(HOLDERS, combination):
            goal[model.slices[arm]] = q
        try:
            entry = cartesian(model, goal, beam, beam,
                lambda _, fraction: {arm: translate(target, [0., 0., .09*(1-fraction)])
                                     for arm, target in targets.items()})
            assert_clear(model, entry, beam, 0., 'open entry')
            for finger in np.linspace(0., angle, 12):
                if reason := model.clear(beam, entry[-1], finger, gripping=True, margin=True):
                    raise ValueError(f'grasp: {reason}')
            line = free_path(model, home, goal, HOLDERS, beam, 'high approach')
            return line, entry
        except ValueError as error:
            errors.append(str(error))
    raise ValueError(errors[0] if errors else 'high approach: no two-arm IK branches')


def worker_targets(model, face):
    for roll in (0., np.pi, np.pi/2, -np.pi/2):
        sites = []
        for screw in model.scene['screws']:
            feed = AxialFeed(screw['uv_m'], .043, .003)
            sites.append((screw, {key: shifted_shape_tool(value, roll) @ np.linalg.inv(model.tip)
                                  for key, value in feed.reference(face).items()}))
        yield sites


def build_waypoints(model, face, scope):
    initial, target = (model.scene['beam'][key] for key in ('start_pose', 'target_pose'))
    home = np.array([model.home[j] for j in model.names])
    angle, grasp_z = model.grip_geometry()
    errors = []
    for distance, flips, height in scope:
        try:
            high, entry = pick(model, home, angle, grasp_z, distance, flips, height)
            gripped = entry[-1]
            tcps = {a: model.chains[a].forward(model.state(gripped, angle)) for a in HOLDERS}
            group = GraspGroup(BEAM_ID, initial, tcps,
                               {arm: dict(left_pad=True, right_pad=True) for arm in HOLDERS}, {})
            lifted = translate(initial, [0., 0., .11])
            before_seat = translate(target, .048*target[:3, 1])
            def carry_targets(beam, _):
                return {arm: target for arm, (target, _) in group.targets(beam).items()}
            lift = cartesian(model, gripped, initial, lifted, carry_targets)
            carry = cartesian(model, lift[-1], lifted, before_seat, carry_targets, samples=24)
            seat = cartesian(model, carry[-1], before_seat, target, carry_targets)
            infer = lambda _, row: model.chains[HOLDERS[0]].forward(model.state(row, angle)) @ np.linalg.inv(group.offsets[HOLDERS[0]])
            assert_clear(model, lift, infer, angle, 'lift', gripping=True)
            assert_clear(model, carry, infer, angle, 'carry holders', gripping=True)
            assert_clear(model, seat, infer, angle, 'seat holders', gripping=True, seated=True)
            for sites in worker_targets(model, face):
                stand_off = translate(sites[0][1]['approach'], .085*target[:3, 1])
                for worker_goal in model.branches(model.worker, stand_off, carry[-1]):
                    try:
                        return finish_waypoints(model, home, high, entry, lift, carry, seat,
                                                group, angle, infer, worker_goal, sites)
                    except ValueError as error:
                        errors.append(f'grip={distance:.3f}/{flips}/{height:.3f}, tool: {error}')
            if not errors:
                errors.append('worker has no stand-off IK')
        except ValueError as error:
            errors.append(f'grip={distance:.3f}/{flips}/{height:.3f}: {error}')
    raise ValueError('; '.join(dict.fromkeys(errors))[:3200])


def finish_waypoints(model, home, high, entry, lift, carry, seat, group, angle, infer, worker_goal, sites):
    target = model.scene['beam']['target_pose']
    phases = []
    def add(name, rows, mode, finger, screw=None):
        phases.append((name, np.array(rows), mode, finger, screw))
    for index, pair in enumerate(zip(high, high[1:])):
        add('high_approach' if index == 0 else f'high_approach_{index+1}', pair, 'support', (0., 0.))
    add('open_entry', entry, 'support', (0., 0.))
    add('grasp', [entry[-1]]*2, 'close', (0., angle))
    add('lift', lift, 'carry', (angle, angle))
    worker_slice = model.slices[model.worker]
    carry = carry.copy()
    carry[:, worker_slice] = np.linspace(home[worker_slice], worker_goal, len(carry))
    seat = seat.copy()
    seat[:, worker_slice] = worker_goal
    assert_clear(model, carry, infer, angle, 'coordinated carry', gripping=True)
    assert_clear(model, seat, infer, angle, 'coordinated seating', gripping=True, seated=True)
    add('carry', carry, 'carry', (angle, angle))
    add('seat', seat, 'seating', (angle, angle))
    current = seat[-1]

    for screw, targets in sites:
        for kind, key, samples in (('axial_approach', 'approach', 22),
                                    ('axial_feed', 'depth', 18),
                                    ('axial_retract', 'withdrawn', 18)):
            start = model.chains[model.worker].forward(model.state(current, angle))
            rows = cartesian(model, current, start, targets[key], lambda tcp, _: {model.worker: tcp},
                             samples=samples)
            allowed = screw if kind in ('axial_feed', 'axial_retract') else None
            assert_clear(model, rows, target, angle, kind+' '+screw['id'], gripping=True,
                         seated=True, screw=allowed)
            add(kind, rows, 'seated', (angle, angle), screw)
            current = rows[-1]

    # First remove the tool from the shared assembly zone, then open both pads.
    worker_retracted = translate(sites[-1][1]['withdrawn'], .085*target[:3, 1])
    worker_tcp = model.chains[model.worker].forward(model.state(current, angle))
    clear_tool = cartesian(model, current, worker_tcp, worker_retracted,
                           lambda tcp, _: {model.worker: tcp})
    assert_clear(model, clear_tool, target, angle, 'tool retreat', gripping=True, seated=True)
    add('tool_retreat', clear_tool, 'seated', (angle, angle))
    add('fasten', [clear_tool[-1]]*2, 'seated', (angle, angle))
    for finger in np.linspace(angle, 0., 12):
        if reason := model.clear(target, clear_tool[-1], finger, gripping=True, seated=True, margin=True):
            raise ValueError(f'release: {reason}')
    add('release', [clear_tool[-1]]*2, 'open', (angle, 0.))
    tool0 = {arm: model.chains[arm].forward(model.state(clear_tool[-1], 0.)) for arm in HOLDERS}
    clear_holders = cartesian(model, clear_tool[-1], target, target,
        lambda _, u: {arm: translate(tcp, [0., 0., .115*u]) for arm, tcp in tool0.items()})
    assert_clear(model, clear_holders, target, 0., 'holder retreat', seated=True)
    return_path = free_path(model, clear_holders[-1], home, (*HOLDERS, model.worker),
                            target, 'return', seated=True)
    add('lift_clear', clear_holders, 'fixed', (0., 0.))
    for index, pair in enumerate(zip(return_path, return_path[1:])):
        phase_name = 'retreat' if index == len(return_path)-2 else f'retreat_{index+1}'
        add(phase_name, pair, 'fixed', (0., 0.))
    return phases, group


def compile_waypoints(model, scope, group, cfg):
    durations = []
    records = []
    maximum_error = np.zeros(2)
    sample_count = 0
    overlap_s = 0.
    seated_pose = None
    initial, target = (model.scene['beam'][key] for key in ('start_pose', 'target_pose'))
    inverse = {arm: np.linalg.inv(offset) for arm, offset in group.offsets.items()}
    limits = tuple(cfg[key] for key in ('joint_velocity_rad_s', 'joint_acceleration_rad_s2', 'joint_jerk_rad_s3'))
    for label, rows, mode, (start_finger, end_finger), screw in scope:
        duration = 0.15
        if mode in ('close', 'open'):
            duration = max(.15, 1.875*abs(end_finger-start_finger)/cfg['finger_velocity_limit_rad_s'])
        if np.max(np.abs(np.diff(rows, axis=0))) < 1e-10:
            times = np.array([0., duration])
            values = np.zeros((2, 3, len(model.names)))
            values[:, 0] = rows[0]
            def spline(t, nu=0):
                return rows[0] if nu==0 else np.zeros(len(rows[0]))
        else:
            times, values, spline, _ = controller_spline(rows.tolist(), np.linspace(0,1,len(rows)), limits, label)
        carrying = mode in ('carry', 'seating')
        gripping = carrying or mode in ('close', 'open', 'seated')
        seated = mode in ('seating', 'seated', 'open', 'fixed')
        active_site = screw if label in ('axial_feed', 'axial_retract') else None

        def at(t, row):
            u = t/times[-1]
            finger = start_finger + (end_finger-start_finger) * u**3*(10.+u*(-15.+6.*u))
            beam = target if seated else initial
            if carrying:
                state = model.state(row, finger)
                beam = model.chains[HOLDERS[0]].forward(state) @ inverse[HOLDERS[0]]
                other = model.chains[HOLDERS[1]].forward(state) @ inverse[HOLDERS[1]]
                np.maximum(maximum_error, pose_error(beam, other), out=maximum_error)
            return beam, finger

        checks = np.sort(np.r_[times, (times[1:] + times[:-1])/2])
        prev_t, active = 0., []
        for t in checks:
            row = spline(t)
            beam, finger = at(t, row)
            reason = model.clear(beam, row, finger, gripping=gripping, seated=seated,
                                 screw=active_site, margin=True)
            if reason:
                raise ValueError(f'controller interpolation {label} at {t:.3f}s: {reason}')
            sample_count += 1
            if label == 'carry':
                speed = spline(t, nu=1)
                simultaneous = all(np.max(np.abs(speed[model.slices[a]])) > 1e-4
                                   for a in (*HOLDERS, model.worker))
                if active and active[-1] and simultaneous:
                    overlap_s += t-prev_t
                active.append(simultaneous)
                prev_t = t
        poses, fingers = zip(*(at(t, row) for t, row in zip(times, values[:, 0])))
        if label == 'seat':
            seated_pose = poses[-1]
        record = dict(id=label if screw is None else label+'_'+screw['id'], kind=label,
                      time_s=times, positions=values[:,0], velocities=values[:,1], accelerations=values[:,2],
                      beam_poses=np.array(poses), gripper_positions=fingers)
        if screw is not None:
            record['screw_id'] = screw['id']
        records.append(record)
        durations.append(float(times[-1]))

    error_m, error_rad = pose_error(seated_pose, target)
    if maximum_error[0] > .002 or maximum_error[1] > np.deg2rad(1) or error_m > .002 or error_rad > np.deg2rad(1):
        raise ValueError('Independent FK exceeds rigid-grasp or final seating tolerance')
    if overlap_s <= .01:
        raise ValueError('All three active arms never move concurrently')
    return records, dict(status='PASS', samples=sample_count, arm_pairs_checked=len(tuple(combinations(ROBOT_IDS, 2))),
                         neighbor_margin_m=.04, model_duration_s=sum(durations), three_arm_overlap_s=overlap_s,
                         seating_error_m=error_m, seating_error_rad=error_rad,
                         max_grasp_position_error_m=maximum_error[0],
                         max_grasp_angle_error_rad=maximum_error[1],
                         screws_completed=[p['screw_id'] for p in records if p['kind']=='axial_retract'])


def compile_frame(output, observe, *, recipe=None, layout_path=None, shift=(0., 0., 0.), hydrogen=False):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    recipe = recipe or FrameRecipe()
    layout_path = Path(layout_path or default_layout_path()).resolve()
    layout = load_layout(layout_path)
    table_z = sum((layout['tables']['right']['height'], layout['tables']['right']['xyz'][2]))
    description, _ = render_description(layout, output/'model')
    root = ET.fromstring(description)
    fingertip_contact_primitives(root)
    description = ET.tostring(root, encoding='unicode')
    (output/'description.urdf').write_text(description)
    cfg_path = Path(__file__).resolve().parents[1]/'config/carton_drawing_fast.yaml'
    cfg = configuration(cfg_path)
    search = []
    for worker, center_y in (('left_rear', FIXTURE_CENTER_Y_M), ('left_front', -FIXTURE_CENTER_Y_M), ('left_rear', .180),
                             ('left_front', -.180), ('left_rear', .080), ('left_front', -.080)):
        attempt = output/f'attempt-{len(search)+1:02d}'
        attempt.mkdir()
        print(f'Wood frame planning: {worker}, fixture Y={center_y:+.3f}m', flush=True)
        reference_beam, reference_posts = fixture(recipe, table_z, center_y, shift)
        observation = observe(reference_beam, recipe.beam_size_m, reference_posts, table_z,
                              output=attempt, hydrogen=hydrogen)
        if observation['status'] != 'VALID':
            search.append(dict(worker=worker, fixture_center_y_m=center_y,
                               reason='image: '+str(observation.get('reason', observation['status']))))
            continue
        beam = np.asarray(observation['beam_pose'])
        posts = [dict(item, pose=np.asarray(observation['post_poses'][item['id']])) for item in reference_posts]
        scene, face = assembly(recipe, beam, posts, worker)
        model = WoodModel(attempt/'collision', description, layout, scene)
        scope = [(distance, flips, height)
                 for distance, height, flips in product((.263, .230, .12), (.023, .010),
                                                        ((1, 1), (-1, -1), (1, -1), (-1, 1)))]
        try:
            waypoints, group = build_waypoints(model, face, scope)
            print('  Waypoints found; checking timed controller interpolation.', flush=True)
            phases, audit = compile_waypoints(model, waypoints, group, cfg)
        except ValueError as error:
            print('  ' + str(error), flush=True)
            search.append(dict(worker=worker, fixture_center_y_m=center_y, reason=str(error)))
            continue
        search.append(dict(worker=worker, fixture_center_y_m=center_y, status='PASS'))
        for key in ('image', 'overlay'):
            if observation.get(key):
                local = Path(observation[key])
                if not local.is_absolute():
                    observation[key] = str(attempt.relative_to(output)/local)
        plan = seal(dict(schema_version=1, status=MODEL_STATUS, scene=scene, phases=phases,
                         recipe=dict(schema_version=1, **asdict(recipe)),
                         joint_names=model.names, layout_path=str(layout_path), layout_sha256=digest(layout),
                         description_sha256=hashlib.sha256(description.encode()).hexdigest(),
                         table_z_m=table_z, audit=audit, observation=observation, grasp=group.record(),
                         simulated_fixture=dict(beam_start_pose=reference_beam, posts=reference_posts),
                         planning_attempts=search))
        write_json(output/'plan.json', plan)
        episode = Episode.create(output/'episode', backend='kinematic_model', program_sha256=plan['sha256'])
        elapsed = 0.
        for phase in phases:
            episode.append('phase_start', phase=phase['id'], source='model', model_time_s=elapsed)
            elapsed += phase['time_s'][-1]
            episode.append('phase_end', phase=phase['id'], source='model', model_time_s=elapsed)
        episode.append('run_end', phase='retreat', source='model', model_time_s=elapsed,
                       details=dict(status=MODEL_STATUS))
        return plan, description
    write_json(output/'failure.json', dict(status='PLAN_REJECTED', attempts=search))
    raise ValueError('No fully checked wood-frame plan. See ' + str(output/'failure.json'))

#!/usr/bin/env python3
"""Compile Return to Home offline with the hardware cell and object geometry."""

import argparse
from hashlib import sha256
import itertools
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from scipy.interpolate import BPoly
from scipy.spatial.transform import Rotation

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
sys.path.insert(0, str(REPO / "uwa_cell_tasks"))

from prepare_carton_open_entry import shell_boxes
from prepare_carton_return import home_near
from return_home_model import model_identity
from return_home_request import ARMS, CARTON_ARMS, PLACEMENT_ROUTES, recorded_carton, validate_request
from uwa_cell_calibration.model import CollisionModel, set_origin
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.carton_paths import evaluate, joint_segment, quintic, solve_near
from uwa_cell_motion.common import config, dump, joint_names
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_tasks.motion_review import caps
from uwa_cell_tasks.reviewed_carton import (
    START_TOLERANCE, concatenate, file_hash, preview_model, prove_group, retime, speed_envelope,
)
from uwa_cell_tasks.timing import interpolation_peaks

INVENTORY = REPO / "config/hardware_inventory.yaml"
CONFIG = REPO / "uwa_cell_motion/config/hardware_carton_supported_trend.yaml"
HELD_DIR = WORKSPACE / "setup/skill_library/return-home-profiles"


def read(path):
    return json.loads(Path(path).read_bytes())


def coordinates(snapshot, problem):
    arms = snapshot.get("arms", {})
    identity = snapshot.get("model_identity")
    matching = identity == model_identity(problem) if identity else snapshot.get("model_signature") == problem.signature
    if not matching or set(arms) != set(ARMS):
        raise ValueError("The four-arm snapshot and active model must agree.")
    state = {joint: 0. for names in problem.names.values() for joint in names[6:]}
    for arm, entry in arms.items():
        q = np.asarray(entry["samples"][-1]["actual_q"], dtype=float)
        if entry.get("observed") is not True or q.shape != (6,) or not np.isfinite(q).all():
            raise ValueError(f"{arm}: measured four-arm start is incomplete.")
        state.update(zip(joint_names(arm), q.tolist(), strict=True))
    return state


def q_of(state, arm):
    return [state[joint] for joint in joint_names(arm)]


def xyz(values):
    return " ".join(map(str, values))


def corners(bounds):
    return np.array(list(itertools.product(*zip(bounds["lo"], bounds["hi"]))))


def world_points(boxes, pose):
    return np.concatenate([corners(box) for box in boxes]) @ pose[:3, :3].T + pose[:3, 3]


def tool_matrix(xyz_yaw):
    pose = np.eye(4)
    pose[:3, 3] = xyz_yaw[:3]
    pose[:3, :3] = Rotation.from_euler("z", xyz_yaw[3], degrees=True).as_matrix()
    return pose


def matching_input(evidence, key, directory):
    entry = evidence["inputs"][key]
    path = Path(entry["path"])
    if key == "object_pose":
        path = directory / "multiview/object-pose.json"
    if file_hash(path) != entry["sha256"]:
        raise ValueError(f"Recorded carton {key} changed.")
    return read(path)


def recorded_object(row, directory, problem, start):
    recorded_carton(directory)
    plan = directory / "plan"
    evidence = read(plan / "high-plan/evidence.json")
    binding = matching_input(evidence, "object_pose", directory)
    scene = matching_input(evidence, "contact_scene", directory)
    proof = read(plan / "weigh-plan/proof.json")
    reviewed = read(plan / "weigh-plan/review.json")
    if (proof["success"] is not True or reviewed["model_signature"] != problem.signature
            or reviewed["hardware_binding"] != problem.binding):
        raise ValueError("The archived lift and current planning model differ.")
    support = np.asarray(binding["T_world_object_candidate"])
    raised = support.copy()
    raised[2, 3] += proof["height_m"]
    estimates = []
    for arm in CARTON_ARMS:
        if max(abs(a - b) for a, b in zip(q_of(start, arm), q_of(proof["end"], arm), strict=True)) > START_TOLERANCE:
            raise ValueError(f"{arm}: current joints differ from the saved lift end. Enter a current measured object.")
        chain = problem.chains[arm]
        estimates.append(chain.forward(start) @ np.linalg.inv(chain.forward(proof["end"])) @ raised)
    if (np.linalg.norm(estimates[0][:3, 3] - estimates[1][:3, 3]) > .001
            or Rotation.from_matrix(estimates[0][:3, :3] @ estimates[1][:3, :3].T).magnitude() > .002):
        raise ValueError("The two wrist estimates disagree on the held carton pose.")
    boxes = shell_boxes(scene)
    raw_points = np.concatenate([np.asarray(shape["vertices"]) for shape in scene["shapes"]])
    return dict(name="Avocado carton", profile="avocado-carton", arms=list(CARTON_ARMS), action=row["action"],
                release=row["release"], pose=estimates[0], support=support, table="right", boxes=boxes,
                bottom_points=raw_points, tolerance=None,
                nominal_jaws=proof["nominal_contact_joints"], support_sides=["left", "right"],
                evidence_run=row["run_id"])


def manual_object(row):
    size = np.asarray(row["size_m"])
    box = dict(lo=[-size[0] / 2, -size[1] / 2, 0.], hi=[size[0] / 2, size[1] / 2, size[2]])
    pose = tool_matrix(row["pose_xyz_yaw_deg"])
    support = pose.copy()
    support[:2, 3] = row["target_xy_m"]
    return dict(name=row["name"], profile=row["profile"], arms=row["arms"], action=row["action"],
                release=row["release"], pose=pose, support=support, table=row["table"], boxes=[box],
                bottom_points=corners(box), tolerance=row["position_error_m"], nominal_jaws={},
                support_sides=[row["table"]])


def bottom(obj, pose):
    return float((obj["bottom_points"] @ pose[:3, :3].T + pose[:3, 3])[:, 2].min())


def load_profile(obj, problem):
    path = HELD_DIR / (obj["profile"] + ".json")
    if not obj["profile"] or not path.is_file():
        return {}
    data = read(path)
    geometry = json.dumps(obj["boxes"], sort_keys=True, allow_nan=False).encode()
    if (data.get("model_signature") != problem.signature or data.get("arms") != obj["arms"]
            or data.get("table") != obj["table"] or data.get("geometry_sha256") != sha256(geometry).hexdigest()):
        raise ValueError(f"{obj['name']}: profile does not match arm, object, table and model binding.")
    evidence = path.with_name(path.stem + "-evidence.json")
    if not evidence.is_file() or data.get("evidence_sha256") != file_hash(evidence):
        raise ValueError(f"{obj['name']}: object profile qualification evidence is missing or changed.")
    return dict(data, sha256=file_hash(path))


def support_check(problem, obj):
    side = obj["table"]
    pose = obj["support"]
    table = Chain(problem.original_description, "world", side + "_table_top").forward({})
    if not np.allclose(table[:3, 2], [0., 0., 1.], atol=1e-8):
        raise ValueError("Return to Home requires a horizontal modelled support.")
    pose[2, 3] += table[2, 3] - bottom(obj, pose)
    profile = obj["qualification"]
    if obj["tolerance"] is None:
        obj["tolerance"] = profile.get("position_error_m")
    footprint_error = obj["tolerance"] or 0.
    if type(footprint_error) not in (int, float) or not 0 <= footprint_error < 1:
        raise ValueError("Invalid profiled placement uncertainty.")
    drop = obj["release"] == "drop"
    drift = profile.get("landing_xy_error_m", 0.) if drop else 0.
    if type(drift) not in (int, float) or not 0 <= drift < 1:
        raise ValueError("Invalid profiled landing uncertainty.")
    points = world_points(obj["boxes"], pose)
    if drop:
        # Isotropic inflation allows the profiled horizontal and tilt envelope during the fall.
        radius = float(np.linalg.norm(points[:, :2] - pose[:2, 3], axis=1).max())
        if profile.get("upright_drop_qualified") is not True or drift <= 0 or radius <= 0:
            raise ValueError(f"{obj['name']}: a qualified upright short-drop envelope is required.")
    if len(obj["support_sides"]) == 1:
        local = (points - table[:3, 3]) @ table[:3, :3]
        table_data = problem.layout["tables"][side]
        if np.any(np.max(np.abs(local[:, :2]), axis=0) + footprint_error + drift >
                  np.array([table_data["width"], table_data["length"]]) / 2):
            raise ValueError(f"{obj['name']}: the complete placement footprint must fit inside the {side} table.")
    else:
        raw = obj["bottom_points"] @ pose[:3, :3].T + pose[:3, 3]
        on_plane = raw[raw[:, 2] <= table[2, 3] + 1e-6, :2]
        polygon = cv2.convexHull(on_plane.astype("float32"))
        patches = []
        for contact_side in obj["support_sides"]:
            plate = Chain(problem.original_description, "world", contact_side + "_table_top").forward({})
            if not np.allclose(plate[:3, 2], [0., 0., 1.]) or abs(plate[2, 3] - table[2, 3]) > 1e-8:
                raise ValueError("The original two-table placement needs coplanar horizontal supports.")
            dimensions = problem.layout["tables"][contact_side]
            widths = np.array([dimensions["width"], dimensions["length"]]) / 2
            outline = np.array(list(itertools.product(*zip(-widths, widths))))
            outline = outline @ plate[:2, :2].T + plate[:2, 3]
            area, patch = cv2.intersectConvexConvex(polygon, cv2.convexHull(outline.astype("float32")))
            if area <= 0:
                raise ValueError("The original carton position needs contact with both table plates.")
            patches.append(patch.reshape(-1, 2))
        hull = cv2.convexHull(np.concatenate(patches))
        centre = (raw[:, :2].min(axis=0) + raw[:, :2].max(axis=0)) / 2
        if cv2.pointPolygonTest(hull, tuple(centre), True) <= footprint_error + drift:
            raise ValueError("The known carton footprint has insufficient support across the table gap.")
    release = pose.copy()
    gap = 0.
    if drop:
        uncertainty = obj["tolerance"]
        maximum = profile.get("max_release_gap_m")
        if (type(maximum) not in (int, float) or not np.isfinite(maximum)
                or uncertainty is None or maximum <= 2 * uncertainty):
            raise ValueError(f"{obj['name']}: qualified drop gap cannot enclose the placement uncertainty.")
        gap = (2 * uncertainty + min(maximum - 2 * uncertainty, .001)) / 2
        release[2, 3] += gap
    return release, float(table[2, 3]), gap, drift


def scene_model(problem, objects, carried, directory, *, open_arms=(), inflate=None):
    """Use the full tool envelope except where an explicit jaw pose/transition is checked."""
    root = ET.fromstring(problem.description)
    original = ET.fromstring(problem.original_description)
    exact = set(open_arms).union(*(obj["arms"] for obj in carried))
    for link in root.findall("link"):
        if any(link.get("name").startswith(arm + "_robotiq_85_") for arm in exact):
            for geometry in link.findall("collision"):
                link.remove(geometry)
            for geometry in original.find(f"link[@name='{link.get('name')}']").findall("collision"):
                link.append(geometry)
    for obj in objects:
        name = obj["link"]
        parent = "world"
        for axis in range(3):
            child = name if axis == 2 else f"{name}_axis_{axis}"
            ET.SubElement(root, "link", name=child)
            joint = ET.SubElement(root, "joint", name=f"{name}_{axis}", type="prismatic")
            ET.SubElement(joint, "parent", link=parent)
            ET.SubElement(joint, "child", link=child)
            ET.SubElement(joint, "axis", xyz=xyz(np.eye(3)[axis]))
            ET.SubElement(joint, "limit", lower="-10", upper="10", effort="1", velocity="1")
            parent = child
        anchor = ET.SubElement(root, "joint", name=name + "_rotation", type="fixed")
        frame = np.eye(4)
        frame[:3, :3] = obj["pose"][:3, :3]
        set_origin(anchor, frame)
        ET.SubElement(anchor, "parent", link=name)
        body = ET.SubElement(root, "link", name=name + "_body")
        ET.SubElement(anchor, "child", link=body.get("name"))
        for box in obj["boxes"]:
            lo, hi = np.asarray(box["lo"]), np.asarray(box["hi"])
            padding = 0. if inflate is None else inflate.get(name, 0.)
            collision = ET.SubElement(body, "collision")
            ET.SubElement(collision, "origin", xyz=xyz((lo + hi) / 2))
            ET.SubElement(ET.SubElement(collision, "geometry"), "box",
                          size=xyz(hi - lo + 2 * padding))
    model = CollisionModel(ET.tostring(root, encoding="unicode"), directory)
    base_srdf = ET.parse(problem.directory / "moveit/robot.srdf")
    for pair in base_srdf.findall("disable_collisions"):
        model.scene.allowed_collision_matrix.set_entry(pair.get("link1"), pair.get("link2"), True)
    for obj in objects:
        model.bounds.update({f"{obj['link']}_{axis}": (-10., 10.) for axis in range(3)})
    return model


def allow_pads(model, obj, allow):
    for arm in obj["arms"]:
        for side in ("left", "right"):
            model.scene.allowed_collision_matrix.set_entry(
                obj["link"] + "_body", arm + f"_robotiq_85_{side}_finger_tip_link", allow)


def actual_scene(model, objects, state, *, moving=None, pose=None):
    combined = dict(state)
    for obj in objects:
        position = pose if obj is moving else obj["pose"]
        combined.update({f"{obj['link']}_{axis}": float(value)
                         for axis, value in enumerate(position[:3, 3])})
        top = obj.get("table_height")
        if top is not None:
            extension = max(0., bottom(obj, position) - world_points(obj["boxes"], position)[:, 2].min())
            model_bottom = bottom(obj, position)
            if model_bottom < top - .0001:
                raise ValueError(f"{obj['name']}: physical bottom is below the support plane.")
            on_support = obj.get("placed", False) or (obj is moving and model_bottom <= top + extension + 1e-7)
            for side in obj["support_sides"]:
                model.scene.allowed_collision_matrix.set_entry(
                    obj["link"] + "_body", side + "_table_plate", on_support)
    return combined


def determine_jaws(model, problem, objects, carried, state):
    """Resolve first nominal pad contact for manually registered objects."""
    for obj in carried:
        allow_pads(model, obj, True)
        state.update(obj["nominal_jaws"])
    for obj in carried:
        for arm in obj["arms"]:
            joint = problem.names[arm][6]
            if joint in obj["nominal_jaws"]:
                continue
            lo, hi = model.bounds[joint]
            for side in ("left", "right"):
                model.scene.allowed_collision_matrix.set_entry(
                    obj["link"] + "_body", arm + f"_robotiq_85_{side}_finger_tip_link", False)
            state[joint] = lo
            if not model.check(actual_scene(model, objects, state))[0]:
                raise ValueError(f"{arm}: the manually measured object obstructs the modelled open gripper.")
            previous = lo
            for value in np.linspace(lo, hi, 81)[1:]:
                state[joint] = float(value)
                if not model.check(actual_scene(model, objects, state))[0]:
                    lo, hi = previous, float(value)
                    break
                previous = float(value)
            else:
                raise ValueError(f"{arm}: modelled pads do not reach the object.")
            for _ in range(16):
                mid = (lo + hi) / 2
                state[joint] = mid
                if model.check(actual_scene(model, objects, state))[0]:
                    lo = mid
                else:
                    hi = mid
            state[joint] = hi
            obj["nominal_jaws"][joint] = hi
            allow_pads(model, obj, True)
    if not model.check(actual_scene(model, objects, state))[0]:
        model.check(actual_scene(model, objects, state), contacts=True)
        raise ValueError("Held objects intersect the cell outside their intended pad contacts.")
    return state


def pose_path(problem, state, arms, delta):
    count = max(1, int(np.ceil(np.linalg.norm(delta) / .002)))
    grid = np.linspace(0, 1, count + 1)
    output = {}
    for arm in arms:
        chain = problem.chains[arm]
        initial = chain.forward(state)
        q = q_of(state, arm)
        values = [q]
        for fraction in grid[1:]:
            target = initial.copy()
            target[:3, 3] += delta * fraction
            solution = solve_near(problem, arm, state, target, q)
            if np.max(np.abs(solution - q)) > .15:
                raise ValueError(f"{arm}: the Cartesian path changes IK branch.")
            q = solution
            values.append(q.tolist())
        output[arm] = dict(knots=grid.tolist(), positions=values)
    return output


def timed(problem, paths, speed, tcp):
    envelope = speed_envelope(problem, paths, speed, tcp)
    u = np.linspace(0., 1., 257)
    acc = problem.cfg["acceleration_limit_rad_s2"]
    samples = {arm: [evaluate(path, u, d) for d in range(3)] for arm, path in paths.items()}
    duration = max(.001, *(float(np.abs(v).max()) / speed for _, v, _ in samples.values()),
                   *(float(np.sqrt(np.abs(a).max() / acc)) for _, _, a in samples.values()))
    for _ in range(8):
        output = {}
        needed = duration
        for arm, (q, v, a) in samples.items():
            points = [dict(time=round(float(t * duration) * 1e9) / 1e9, positions=x.tolist(),
                           velocities=(y / duration).tolist(), accelerations=(z / duration**2).tolist())
                      for t, x, y, z in zip(u, q, v, a, strict=True)]
            trajectory = retime(dict(points=points, waypoints=paths[arm]["positions"]), arm, envelope)
            needed = max(needed, trajectory["duration_s"], trajectory["duration_s"] *
                         np.sqrt(float(interpolation_peaks(trajectory, 2).max()) / acc))
            output[arm] = trajectory
        if needed <= duration * (1. + 1e-10) and len({t["duration_s"] for t in output.values()}) == 1:
            return output
        duration = max(needed, duration * (1. + 1e-9))
    raise ValueError("Unable to retime the group within the approved joint/TCP limits.")


def endpoints(start, trajectories):
    end = dict(start)
    for arm, trajectory in trajectories.items():
        end.update(zip(joint_names(arm), trajectory["points"][-1]["positions"], strict=True))
    return end


def group_from_proof(start, trajectories, proof, label):
    return dict(phase=label, arms=list(trajectories), start=dict(start), trajectories=trajectories,
                duration_s=max(t["duration_s"] for t in trajectories.values()), proof=proof)


def check_start(problem, state):
    req = problem.normalize(dict(start=state, goals={ARMS[0]: q_of(state, ARMS[0])}))
    if not problem.check(req, q_of(state, ARMS[0])):
        raise ValueError("The current whole-cell geometry or neighbour margin rules out a Home plan.")


def coupled_qualification(obj, delta):
    if len(obj["arms"]) < 2:
        return None
    evidence = obj["qualification"].get("loaded_sync", {})
    skew = evidence.get("max_phase_skew_fraction")
    translation = evidence.get("allowable_relative_translation_m")
    rotation = evidence.get("allowable_relative_rotation_rad")
    if (any(type(v) not in (float, int) or not np.isfinite(v) for v in (skew, translation, rotation))
            or not 0 < skew <= 1 or translation <= 0 or rotation <= 0):
        return f"{obj['name']}: loaded synchronization has no qualification for these arms."
    # A bounded phase offset in the shared quintic produces an additional
    # translation of at most max(quintic') * phase_offset * displacement.
    differential = min(1., 1.875 * skew) * np.linalg.norm(delta) + .0002
    if differential > translation or .002 > rotation:
        return (f"{obj['name']}: profiled relative-motion allowance is smaller than the "
                f"{differential * 1000:.2f} mm / 2 mrad bound for this loaded segment.")
    return None


def check_cartesian(problem, model, objects, start, group, delta, *, active=None, nominal=None):
    duration = group["duration_s"]
    polynomials = {arm: BPoly.from_derivatives([p["time"] for p in t["points"]],
        [[p["positions"], p["velocities"], p["accelerations"]] for p in t["points"]])
        for arm, t in group["trajectories"].items()}
    initial = {arm: problem.chains[arm].forward(start) for arm in polynomials}
    held = dict(start, **(nominal or {}))
    for phase in np.linspace(0., 1., 257):
        state = dict(held)
        shift = delta * float(quintic(phase))
        for arm, polynomial in polynomials.items():
            state.update(zip(joint_names(arm), polynomial(phase * duration).tolist(), strict=True))
            transform = problem.chains[arm].forward(state)
            reference = initial[arm]
            if (np.linalg.norm(transform[:3, 3] - reference[:3, 3] - shift) > .0001
                    or Rotation.from_matrix(transform[:3, :3] @ reference[:3, :3].T).magnitude() > .001):
                raise ValueError(f"{arm}: interpolated Cartesian constraint failed.")
        pose = None
        if active is not None:
            pose = active["pose"].copy()
            pose[:3, 3] += shift
        if not model.check(actual_scene(model, objects, state, moving=active, pose=pose))[0]:
            model.check(actual_scene(model, objects, state, moving=active, pose=pose), contacts=True)
            raise ValueError(f"{group['phase']}: object or tool collision at progress {phase:.3f}.")


class StaticScene:
    def __init__(self, model, objects, jaws):
        self.model, self.objects, self.jaws = model, objects, dict(jaws)

    def check(self, state):
        return self.model.check(actual_scene(self.model, self.objects, dict(state, **self.jaws)))


def home_candidates(problem, start, arm, route, speed, tcp):
    q0 = q_of(start, arm)
    goal = home_near(q0, [problem.collision.bounds[j] for j in joint_names(arm)])
    if np.max(np.abs(np.subtract(q0, goal))) < START_TOLERANCE:
        return None
    if route == "direct":
        waypoints = [q0, goal]
    elif route == "upright_then_base":
        upright = list(goal)
        upright[0] = q0[0]
        waypoints = [q0, upright, goal]
    else:
        request = problem.normalize(dict(start=start, goals={arm: goal}))
        path, error = problem.rrt(request, seed=64, budget=problem.cfg["planning_budget_s"])
        if not path:
            raise ValueError(f"{arm}: {error}")
        waypoints = path
    parts = []
    for a, b in zip(waypoints, waypoints[1:]):
        if np.max(np.abs(np.subtract(a, b))) > 1e-9:
            parts.append(timed(problem, {arm: joint_segment(a, b)}, speed, tcp)[arm])
    return concatenate(parts)


def plan_home(problem, start, arms, routes, speed, tcp, extra):
    safe, used, failed = {}, {}, {}
    for arm in arms:
        failures = []
        for route in routes:
            try:
                path = home_candidates(problem, start, arm, route, speed, tcp)
                if path is None:
                    break
                proof, error = prove_group(problem, start, {arm: path}, speed, extra)
                if error:
                    raise ValueError(error)
                safe[arm], used[arm] = path, route
                break
            except ValueError as error:
                failures.append(f"{route}: {error}")
        else:
            failed[arm] = failures
    if safe and not failed:
        proof, error = prove_group(problem, start, safe, speed, extra)
        if error is None:
            return [group_from_proof(start, safe, proof, "Return to Home")], used
    # The stationary neighbours at the start of each serial alternative differ.
    for order in itertools.permutations(arms):
        state, groups, choices = dict(start), [], {}
        for arm in order:
            for route in routes:
                try:
                    path = home_candidates(problem, state, arm, route, speed, tcp)
                    if path is None:
                        break
                    proof, error = prove_group(problem, state, {arm: path}, speed, extra)
                    if error:
                        raise ValueError(error)
                    groups.append(group_from_proof(state, {arm: path}, proof, "Return to Home"))
                    choices[arm] = route
                    state = endpoints(state, {arm: path})
                    break
                except ValueError as error:
                    failed.setdefault(arm, []).append(f"{route}: {error}")
            else:
                break
        else:
            return groups, choices
    details = " | ".join(f"{arm}: {', '.join(dict.fromkeys(errors))}" for arm, errors in failed.items())
    raise ValueError("No checked Home schedule. " + details)


def plan_loaded(problem, model, objects, obj, start, jaws, ranking, speed, tcp):
    origin = obj["pose"].copy()
    offset = obj["release_pose"][:3, 3] - origin[:3, 3]
    horizontal = np.array([*offset[:2], 0.])
    in_place = np.linalg.norm(horizontal) < .00001
    failures = []
    offline = None
    for route in (("lower_in_place",) if in_place else ranking):
        if route == "raise_then_lower":
            lift = max(.05, float(offset[2]) + .05)
        else:
            lift = 0.
        if offset[2] - lift > .0001:
            failures.append(f"{route}: insufficient starting height for the selected release.")
            continue
        obj["pose"] = origin.copy()
        state, groups, blockers = start, [], []
        phases = [
            ("Raise for clearance", np.array([0., 0., lift])),
            ("Carry to the support", horizontal),
            ("Lower together", np.array([0., 0., offset[2] - lift])),
        ]
        try:
            for label, delta in phases:
                if np.linalg.norm(delta) < .00001:
                    continue
                if blocker := coupled_qualification(obj, delta):
                    blockers.append(blocker)
                paths = pose_path(problem, state, obj["arms"], delta)
                trajectories = timed(problem, paths, speed, tcp)
                proof, error = prove_group(problem, state, trajectories, speed)
                if error:
                    raise ValueError(f"{label}: {error}")
                group = group_from_proof(state, trajectories, proof, label)
                check_cartesian(problem, model, objects, state, group, delta, active=obj, nominal=jaws)
                group["object_delta_m"] = delta.tolist()
                groups.append(group)
                state = endpoints(state, trajectories)
                obj["pose"][:3, 3] += delta
        except ValueError as error:
            failures.append(f"{route}: {error}")
        else:
            result = (state, groups, blockers, route)
            if not blockers or not obj["qualification"].get("loaded_sync"):
                return result
            if offline is None:
                offline = (obj["pose"].copy(), result)
    if offline:
        obj["pose"], result = offline
        return result
    raise ValueError(f"{obj['name']}: no checked placement route. " + " | ".join(failures))


def assemble(args):
    request = validate_request(read(args.request))
    snapshot = read(args.snapshot)
    advice = read(args.advice)
    problem = HardwareProblem(args.output / "model", config(CONFIG), INVENTORY)
    problem.chains = {arm: Chain(problem.original_description, "world", arm + "_tool0") for arm in ARMS}
    start = coordinates(snapshot, problem)
    check_start(problem, start)
    caps_joint, tcp = caps(args.speed_percent)
    speed = min(caps_joint, .1)
    objects = []
    for index, row in enumerate(request["objects"]):
        obj = (recorded_object(row, args.runs / row["run_id"], problem, start)
               if row["source"] == "carton" else manual_object(row))
        obj["link"] = f"return_object_{index}"
        obj["qualification"] = load_profile(obj, problem)
        objects.append(obj)
    placed = [obj for obj in objects if obj["action"] == "place"]
    kept = [obj for obj in objects if obj["action"] == "keep"]
    live_blockers = []
    for obj in placed:
        release, table, gap, drift = support_check(problem, obj)
        obj.update(release_pose=release, table_height=table, gap=gap, landing_drift=drift)
        if obj["tolerance"] is None:
            live_blockers.append(f"{obj['name']}: placement uncertainty has no current measurement or qualified profile.")
    reports, state = [], dict(start)
    for index, obj in enumerate(placed):
        folder = args.output / f"object-{index}"
        carried = placed[index:] + kept
        model = scene_model(problem, objects, carried, folder / "carry")
        determine_jaws(model, problem, objects, carried, dict(state))
        jaws = {key: value for item in carried for key, value in item["nominal_jaws"].items()}
        first_pose = obj["pose"].copy()
        ranking = advice.get("placement_routes", PLACEMENT_ROUTES)
        state, groups, blockers, route = plan_loaded(problem, model, objects, obj, state, jaws, ranking, speed, tcp)
        live_blockers.extend(blocker for blocker in dict.fromkeys(blockers) if blocker not in live_blockers)
        release_model = scene_model(problem, objects, carried, folder / "release")
        for item in carried:
            allow_pads(release_model, item, True)
        for arm in obj["arms"]:
            joint = problem.names[arm][6]
            for jaw in np.linspace(jaws[joint], 0., 33):
                if not release_model.check(actual_scene(release_model, objects, dict(state, **dict(jaws, **{joint: jaw})),
                                                        moving=obj, pose=obj["pose"]))[0]:
                    raise ValueError(f"{arm}: gripper opening sweep intersects the object or cell.")
        carried = [item for item in carried if item is not obj]
        jaws = {key: value for item in carried for key, value in item["nominal_jaws"].items()}
        if obj["gap"]:
            fall = scene_model(problem, objects, carried, folder / "fall", open_arms=obj["arms"],
                               inflate={obj["link"]: obj["landing_drift"]})
            for item in carried:
                allow_pads(fall, item, True)
            for fraction in np.linspace(0., 1., 33):
                pose = obj["pose"].copy()
                pose[2, 3] -= fraction * obj["gap"]
                if not fall.check(actual_scene(fall, objects, dict(state, **jaws), moving=obj, pose=pose))[0]:
                    raise ValueError(f"{obj['name']}: the profiled fall envelope intersects the cell.")
                # Onset can precede the end of the open action. Check every
                # opening sweep against the falling body with only intended
                # pad faces exempted and all gripper structures still checked.
                allow_pads(fall, obj, True)
                for arm in obj["arms"]:
                    joint = problem.names[arm][6]
                    for jaw in np.linspace(obj["nominal_jaws"][joint], 0., 33):
                        sample = dict(state, **dict(jaws, **{joint: jaw}))
                        if not fall.check(actual_scene(fall, objects, sample, moving=obj, pose=pose))[0]:
                            raise ValueError(f"{arm}: a partial opening obstructs the profiled fall envelope.")
                allow_pads(fall, obj, False)
        obj["pose"] = obj["support"].copy()
        obj["placed"] = True
        retreat_model = scene_model(problem, objects, carried, folder / "retreat", open_arms=obj["arms"])
        for item in carried:
            allow_pads(retreat_model, item, True)
        extra = StaticScene(retreat_model, objects, jaws)
        height = max(.15, float(world_points(obj["boxes"], obj["pose"])[:, 2].max() + .025
                                - min(problem.chains[arm].forward(state)[2, 3] for arm in obj["arms"])))
        delta = np.array([0., 0., height])
        paths = pose_path(problem, state, obj["arms"], delta)
        trajectories = timed(problem, paths, speed, tcp)
        proof, error = prove_group(problem, state, trajectories, speed, extra)
        if error:
            raise ValueError(f"{obj['name']} · vertical withdrawal: {error}")
        retreat = group_from_proof(state, trajectories, proof, "Withdraw straight up")
        check_cartesian(problem, retreat_model, objects, state, retreat, delta, nominal=jaws)
        reports.append(dict(name=obj["name"], arms=obj["arms"], link=obj["link"], loaded=groups, retreat=[retreat],
                            placement_route=route,
                            start_pose=first_pose.tolist(), release_pose=obj["release_pose"].tolist(),
                            support_pose=obj["support"].tolist(), release=obj["release"],
                            gap_m=obj["gap"], position_error_m=obj["tolerance"],
                            qualification_sha256=obj["qualification"].get("sha256")))
        state = endpoints(state, trajectories)
    excluded = {arm for item in kept for arm in item["arms"]}
    extra = None
    if objects:
        # Preserve the exact-open model for released grippers while retaining
        # the primary all-opening arm collision proof.
        finished = [arm for item in placed for arm in item["arms"]]
        static = scene_model(problem, objects, kept, args.output / "home-scene", open_arms=finished)
        jaws = determine_jaws(static, problem, objects, kept, dict(state))
        jaws = {key: jaws[key] for obj in kept for key in obj["nominal_jaws"]}
        extra = StaticScene(static, objects, jaws)
    home, routes = plan_home(problem, state, [arm for arm in request["arms"] if arm not in excluded],
                             advice["home_routes"], speed, tcp, extra)
    end = state
    for group in home:
        end = endpoints(end, group["trajectories"])
    preview = preview_model(problem, args.output)
    object_tracks = [dict(link=obj["link"], name=obj["name"], boxes=obj["boxes"],
                          pose=next((report["start_pose"] for report in reports if report["link"] == obj["link"]),
                                    obj["pose"].tolist())) for obj in objects]
    document = dict(kind="return_to_home", version=1, model_signature=snapshot["model_signature"],
                    model_identity=model_identity(problem), start=start, end=end, objects=reports,
                    kept_arms=sorted(excluded), home=home, home_routes=routes, advice=advice,
                    joint_limit_rad_s=speed, tcp_limit_m_s=tcp, speed_percent=args.speed_percent,
                    robot_description=preview.read_text(), object_tracks=object_tracks,
                    live_blockers=live_blockers, snapshot_sha256=file_hash(args.snapshot),
                    request_sha256=file_hash(args.request))
    dump(args.output / "plan.json", document)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("request", "snapshot", "advice", "runs", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--speed-percent", type=float, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    plan = assemble(args)
    print(json.dumps(dict(objects=len(plan["objects"]), home_routes=plan["home_routes"],
                          live_blockers=plan["live_blockers"])))


if __name__ == "__main__":
    main()

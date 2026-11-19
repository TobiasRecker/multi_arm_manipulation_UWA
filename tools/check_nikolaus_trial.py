#!/usr/bin/env python3
"""Verify the Nikolaus trial from saved interpolants, without importing agent code."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.smooth_paths import sample_segment


VERTICES = np.array([(-20, -20), (20, -20), (20, 20), (-20, 20), (0, 40)]) / 1000
STROKE = "ABCEDCADB"
TOLERANCE = .0005
HOLDERS = ("right_front", "right_rear")
WORKER = "left_front"
FACES = ("y_max", "z_min", "y_min")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def house_edges(points, vertices=VERTICES):
    targets = vertices[[ord(name) - ord("A") for name in STROKE]]
    require(np.linalg.norm(points[0] - targets[0]) <= TOLERANCE, "House does not start at A")
    edge_records = []
    first = 0
    for index, (start, end) in enumerate(zip(targets, targets[1:])):
        name = STROKE[index:index + 2]
        hits = np.flatnonzero(np.linalg.norm(points[first + 1:] - end, axis=1) <= TOLERANCE)
        require(len(hits) > 0, f"Edge {name}: endpoint missing")
        last = first + 1 + int(hits[0])
        if index == len(STROKE) - 2:
            last = len(points) - 1
            require(np.linalg.norm(points[last] - end) <= TOLERANCE, "House does not end at B")
        part = points[first:last + 1]
        direction = (end - start) / np.linalg.norm(end - start)
        along = (part - start) @ direction
        closest = start + np.clip(along, 0, np.linalg.norm(end - start))[:, None] * direction
        error = np.linalg.norm(part - closest, axis=1).max()
        require(error <= TOLERANCE, f"Edge {name}: {error * 1000:.3f} mm away from segment")
        require(np.max(np.maximum.accumulate(along) - along) <= TOLERANCE, f"Edge {name}: double-back")
        edge_records.append(dict(edge=name, max_error_m=float(error), samples=len(part)))
        first = last
    return edge_records


def audit(run):
    file = run / "result.json"
    raw = file.read_bytes()
    report = json.loads(raw)
    require(report["status"] == "MODEL_SEQUENCE_COMPLETE" and report["executable"] is False,
            "Expected one completed offline run")
    program = report["program"]
    require(program["surfaces"] == list(FACES), "Unexpected task surface order")
    require(program["holding_arms"] == list(HOLDERS) and program["working_arm"] == WORKER,
            "Unexpected arm roles")
    require(program["velocity_rad_s"] == .1, "Expected the 0.1 rad/s profile")
    for named_file, expected in [
        (Path(report["source_path"]), report["source_sha256"]),
        (run / "policy.py", report["policy_sha256"]),
        (run / "model/carton-moveit/robot.urdf", report["model_urdf_sha256"]),
        *((Path(path), digest) for path, digest in report["mesh_sha256"].items()),
    ]:
        require(sha256(named_file.read_bytes()).hexdigest() == expected, f"Hash mismatch: {named_file}")
    declared_source = Path("/home/rosmatch/UWA_ws/setup/research/offline-carton-sides-20261117/standard/smoothed/result.json")
    require(report["source_sha256"] == sha256(declared_source.read_bytes()).hexdigest(), "Wrong fixture source")
    urdf = (run / "model/carton-moveit/robot.urdf").read_text()
    chains = {arm: Chain(urdf, "world", arm + "_tool0") for arm in (*HOLDERS, WORKER)}
    tool_to_box = {arm: np.array(report["holder_tcp_offsets"][arm]) @
                   np.linalg.inv(report["grasp_offsets"][arm]) for arm in HOLDERS}
    names = [joint for arm in ROBOT_IDS for joint in joint_names(arm)]
    parked = [names.index(joint) for joint in joint_names("left_rear")]
    holding = [names.index(joint) for arm in HOLDERS for joint in joint_names(arm)]
    initial = report["initial_state"]
    initial_q = np.array([initial[joint] for joint in names])
    previous = initial_q
    blocks = []
    active = None
    velocity = 0.
    duration_total = 0.
    for phase in report["phases"]:
        duration = float(phase["duration_s"])
        segment = phase["segment"]
        require(np.isfinite(duration) and duration > 0, "Invalid phase duration")
        require(abs(duration - segment["time_law"]["duration_s"]) < 1e-8, "Inconsistent phase time")
        ts = np.linspace(0, duration, max(2001, int(np.ceil(duration / .02)) + 1))
        q = sample_segment(segment, ts)
        speed = sample_segment(segment, ts, 1)
        require(np.isfinite(q).all() and np.isfinite(speed).all(), "Invalid joint interpolant")
        velocity = max(velocity, float(np.max(np.abs(speed))))
        require(np.max(np.abs(previous - q[0])) < 1e-7, f"Discontinuous join before {phase['id']}")
        require(np.max(np.abs(q[:, parked] - initial_q[parked])) < 1e-9, "Parked arm moved")
        previous = q[-1]
        duration_total += duration
        face = phase["face"] if phase["drawing"] else None
        if face is not None and face != active:
            require(face in FACES, "Unsupported drawing face")
            blocks.append((face, [], q[0, holding]))
        active = face
        if active is not None:
            require(np.max(np.abs(q[:, holding] - blocks[-1][2])) < 1e-7, "Holder moved during a stroke")
            indices = range(len(q))
        else:
            indices = np.linspace(0, len(q) - 1, 151, dtype=int)
        for index in indices:
            state = dict(initial, **dict(zip(names, q[index])))
            box, other = [chains[arm].forward(state) @ tool_to_box[arm] for arm in HOLDERS]
            require(np.linalg.norm(box[:3, 3] - other[:3, 3]) < 1e-6, "Holder position disagreement")
            require(Rotation.from_matrix(box[:3, :3] @ other[:3, :3].T).magnitude() < 1e-5,
                    "Holder rotation disagreement")
            if active is not None:
                tool = chains[WORKER].forward(state)
                tip = tool[:3, 3] + .30 * tool[:3, 2]
                blocks[-1][1].append(box[:3, :3].T @ (tip - box[:3, 3]))
    require(velocity <= .100001, "Joint speed exceeds 0.1 rad/s")
    require(np.max(np.abs(previous - initial_q)) < 1e-7, "Arms did not return to start")
    require([face for face, _, _ in blocks] == list(FACES), "Expected three uninterrupted drawing blocks")
    dims = np.array(report["dimensions_m"])
    edges = None
    for face, points, _ in blocks:
        coordinates = np.asarray(points)
        axis, sign = {"y_max": (1, 1), "z_min": (2, -1), "y_min": (1, -1)}[face]
        require(np.max(np.abs(coordinates[:, axis] - sign * dims[axis] / 2)) <= TOLERANCE,
                f"{face}: pen leaves the face plane")
        if face == "z_min":
            edges = house_edges(coordinates[:, :2])
        else:
            plane = coordinates[:, [0, 2]]
            radius = np.linalg.norm(plane, axis=1)
            require(np.max(np.abs(radius - .022)) <= TOLERANCE, f"{face}: wrong circle radius")
            turns = np.unwrap(np.arctan2(plane[:, 1], plane[:, 0]))
            require(abs(abs(turns[-1] - turns[0]) - 2 * np.pi) < .02 and
                    abs(np.sum(np.abs(np.diff(turns))) - 2 * np.pi) < .02, f"{face}: expected one full circle")
    return dict(passed=True, result_sha256=sha256(raw).hexdigest(), drawn_faces=list(FACES),
                house_edges=edges, max_speed_rad_s=velocity, duration_model_s=duration_total,
                scope="Operator FK and timing audit of the saved path; collision and contact are separate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.run), indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")

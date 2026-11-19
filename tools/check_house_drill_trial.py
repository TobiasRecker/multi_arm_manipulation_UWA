#!/usr/bin/env python3
"""Check the fourth trial from joint interpolants and the operator's task spec."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from check_nikolaus_trial import FACES, HOLDERS, TOLERANCE, VERTICES, WORKER, house_edges, require
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.smooth_paths import sample_segment


SPEC = Path(__file__).resolve().parents[1] / "docs/agent_trials/house_drill_spec.json"
AXIAL = ("axial_approach", "axial_feed", "axial_retract")


def axial_sites(pattern):
    angles = np.deg2rad(pattern["first_angle_deg"] + pattern["step_angle_deg"] * np.arange(pattern["count"]))
    return np.asarray(pattern["center_uv_m"]) + pattern["diameter_m"]/2 * np.column_stack((np.cos(angles), np.sin(angles)))


def check_axial_trace(points, axes, site, z_surface, endpoints):
    center_xy = site * [1., -1.]  # Underneath the carton, v points along object -Y.
    lateral = np.linalg.norm(points[:, :2] - center_xy, axis=1)
    require(lateral.max() <= TOLERANCE, "Axial motion strays from its designated site")
    require(np.min(axes[:, 2]) >= np.cos(np.deg2rad(1.)), "Axial tool points away from the inward normal")
    height = z_surface - points[:, 2]
    start, end = endpoints
    require(np.max(np.abs(height[[0, -1]] - [start, end])) <= .00025, "Wrong axial entry or target depth")
    require(min(height) >= min(start, end) - .00025 and max(height) <= max(start, end) + .00025,
            "Axial move exceeds the reference corridor")
    progress = height * np.sign(end - start)
    require(np.max(np.maximum.accumulate(progress) - progress) <= .0001, "Axial move reverses before its endpoint")
    return float(lateral.max()), [float(height[0]), float(height[-1])]


def check_circle(points, face, dims, radius):
    expected_y = dims[1]/2 if face == "y_max" else -dims[1]/2
    require(np.max(np.abs(points[:, 1] - expected_y)) <= TOLERANCE, f"{face}: leaves face")
    plane = points[:, [0, 2]]
    radial_error = np.max(np.abs(np.linalg.norm(plane, axis=1) - radius))
    require(radial_error <= TOLERANCE, f"{face}: wrong radius")
    angles = np.unwrap(np.arctan2(plane[:, 1], plane[:, 0]))
    require(abs(abs(angles[-1] - angles[0]) - 2*np.pi) < .02 and
            abs(np.sum(np.abs(np.diff(angles))) - 2*np.pi) < .02, f"{face}: expected a full circle")
    return float(radial_error)


def audit(run):
    spec = json.loads(SPEC.read_text())
    raw = (run / "result.json").read_bytes()
    report = json.loads(raw)
    program = report["program"]
    require(report["status"] == "MODEL_SEQUENCE_COMPLETE" and report["executable"] is False,
            "Expected complete, offline model result")
    require(program["surfaces"] == list(FACES) and program["holding_arms"] == list(HOLDERS)
            and program["working_arm"] == WORKER, "Unexpected surfaces or roles")
    require(program["velocity_rad_s"] == spec["joint_speed_rad_s"], "Unexpected joint-speed profile")
    fixture = Path("/home/rosmatch/UWA_ws/setup/research/offline-carton-sides-20261117/standard/smoothed/result.json")
    fixture_raw = fixture.read_bytes()
    require(sha256(fixture_raw).hexdigest() == report["source_sha256"], "Wrong fixture")
    require(report["dimensions_m"] == json.loads(fixture_raw)["task"]["dimensions_m"], "Wrong carton dimensions")
    model = run / "model/carton-moveit/robot.urdf"
    files = {Path(report["source_path"]): report["source_sha256"], model: report["model_urdf_sha256"],
             run / "policy.py": report["policy_sha256"],
             **{Path(path): digest for path, digest in report["mesh_sha256"].items()}}
    for file, digest in files.items():
        require(sha256(file.read_bytes()).hexdigest() == digest, f"Hash mismatch: {file}")

    urdf = model.read_text()
    chains = {arm: Chain(urdf, "world", arm + "_tool0") for arm in (*HOLDERS, WORKER)}
    tool_to_box = {arm: np.array(report["holder_tcp_offsets"][arm]) @
                   np.linalg.inv(report["grasp_offsets"][arm]) for arm in HOLDERS}
    names = [joint for arm in ROBOT_IDS for joint in joint_names(arm)]
    parked = [names.index(joint) for joint in joint_names("left_rear")]
    working = [names.index(joint) for joint in joint_names(WORKER)]
    holding = [names.index(joint) for arm in HOLDERS for joint in joint_names(arm)]
    initial = report["initial_state"]
    initial_q = np.array([initial[joint] for joint in names])
    previous = initial_q
    active = None
    blocks = []
    peak = 0.
    total = 0.
    for number, phase in enumerate(report["phases"]):
        segment = phase["segment"]
        duration = float(phase["duration_s"])
        require(np.isfinite(duration) and duration > 0, "Invalid phase duration")
        require(abs(duration - segment["time_law"]["duration_s"]) < 1e-8, "Phase time mismatch")
        times = np.linspace(0., duration, max(2001, int(np.ceil(duration/.02))+1))
        qs = sample_segment(segment, times)
        speed = sample_segment(segment, times, 1)
        require(np.isfinite(qs).all() and np.isfinite(speed).all(), "Invalid trajectory values")
        require(np.max(np.abs(qs[0] - previous)) < 1e-7, f"Discontinuity before {phase['id']}")
        require(np.max(np.abs(qs[:, parked] - initial_q[parked])) < 1e-9, "Parked arm moved")
        previous = qs[-1]
        peak = max(peak, float(np.max(np.abs(speed))))
        total += duration
        operation = phase.get("operation")
        if operation in AXIAL:
            require(not phase["drawing"] and phase["face"] == "z_min", "Unexpected axial phase metadata")
            require(type(phase.get("site")) is int, "Axial phase requires an integer site")
            key = (operation, phase["site"])
        else:
            key = ("trace", phase["face"]) if phase["drawing"] else None
        if key is not None and key != active:
            blocks.append(dict(key=key, points=[], axes=[], start_q=qs[0], first=number))
        active = key
        if key is not None:
            block = blocks[-1]
            block["last"] = number
            fixed = working if key == ("trace", "y_min") else holding
            require(np.max(np.abs(qs[:, fixed] - block["start_q"][fixed])) < 1e-7,
                    f"Expected {'working arm' if fixed == working else 'holders'} to stay fixed in {key}")
        indices = range(len(qs)) if key is not None else np.linspace(0, len(qs)-1, 151, dtype=int)
        for index in indices:
            state = dict(initial, **dict(zip(names, qs[index])))
            box, other = [chains[arm].forward(state) @ tool_to_box[arm] for arm in HOLDERS]
            require(np.linalg.norm(box[:3, 3] - other[:3, 3]) < 1e-6, "Rigid holder translation mismatch")
            require(Rotation.from_matrix(box[:3, :3] @ other[:3, :3].T).magnitude() < 1e-5,
                    "Rigid holder rotation mismatch")
            if active is not None:
                tool = chains[WORKER].forward(state)
                tip = tool[:3, 3] + .30 * tool[:3, 2]
                block["points"].append(box[:3, :3].T @ (tip - box[:3, 3]))
                block["axes"].append(box[:3, :3].T @ tool[:3, 2])

    require(peak <= .100001, "Joint-speed limit exceeded")
    require(np.max(np.abs(previous - initial_q)) < 1e-7, "Arms do not finish at start")
    pattern = spec["axial_pattern"]
    sites = axial_sites(pattern)
    expected = [("trace", "y_max"), ("trace", "z_min"),
                *((phase, site) for site in range(1, len(sites)+1) for phase in AXIAL),
                ("trace", "y_min")]
    require([b["key"] for b in blocks] == expected, "Expected house, six complete axial cycles and both circles")
    dims = np.asarray(report["dimensions_m"])
    z_surface = -dims[2]/2
    house = np.asarray(blocks[1]["points"])
    require(np.max(np.abs(house[:, 2] - z_surface)) <= TOLERANCE, "House leaves the bottom plane")
    edges = house_edges(house[:, :2], 2*VERTICES)
    require(np.min(np.asarray(blocks[-1]["axes"])[:, 1]) >= np.cos(np.deg2rad(1.)),
            "Opposite wall normal is not aligned with the fixed tool")
    clear, depth = pattern["clearance_m"], pattern["reference_depth_m"]
    axial = []
    for i, site in enumerate(sites):
        group = blocks[2+3*i:5+3*i]
        require(all(a["last"] + 1 == b["first"] for a, b in zip(group, group[1:])),
                "Each axial approach, feed and retract must be one continuous cycle")
        reference = group[0]["start_q"][holding]
        records = []
        for block, endpoints in zip(group, ((clear, 0.), (0., -depth), (-depth, clear))):
            require(np.max(np.abs(block["start_q"][holding] - reference)) < 1e-7,
                    "Workpiece moved between phases of one axial cycle")
            error, measured = check_axial_trace(np.asarray(block["points"]), np.asarray(block["axes"]),
                                                site, z_surface, endpoints)
            records.append(dict(operation=block["key"][0], max_lateral_error_m=error, height_endpoints_m=measured))
        axial.append(dict(site=i+1, target_uv_m=site.tolist(), phases=records))
    return dict(passed=True, result_sha256=sha256(raw).hexdigest(),
                entry_circle_error_m=check_circle(np.asarray(blocks[0]["points"]), "y_max", dims, .022),
                house_edges=edges, axial_sites=axial,
                final_circle_error_m=check_circle(np.asarray(blocks[-1]["points"]), "y_min", dims, .022),
                final_worker_fixed=True, max_speed_rad_s=peak, duration_model_s=total,
                scope="Independent offline geometry and timing audit; collision and process checks are separate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, help="Also save the audit as JSON")
    args = parser.parse_args()
    try:
        payload = json.dumps(audit(args.run), indent=2)
        if args.output:
            with args.output.open("x") as output:
                output.write(payload + "\n")
        print(payload)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")

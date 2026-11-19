"""Build the shared RViz/decision record from the two executable carton bundles."""
import base64
from datetime import datetime
from io import BytesIO
import json
import math
from pathlib import Path

from .motion_review import TASK, caps, digest


def read_json(path):
    return json.loads(Path(path).read_bytes())


def read_checked(path, expected):
    data = Path(path).read_bytes()
    if digest(data) != expected:
        raise ValueError("Review asset changed: " + str(path))
    return data


def motion_packet(paths, dimensions, speed, risk, reason, regular_start=False):
    groups, components, coordination = [], [], []
    start, description, carton, last = None, None, None, None
    for expected_phase, path in zip(("high", "entry"), paths, strict=True):
        data = Path(path).read_bytes()
        bundle = json.loads(data)
        if bundle["phase"] != expected_phase or not bundle["groups"]:
            raise ValueError("Both complete motion phases are required")
        joint_limit, tcp_limit = caps(speed)
        if not (math.isclose(bundle["joint_limit_rad_s"], joint_limit, rel_tol=1e-12)
                and math.isclose(bundle["tcp_limit_m_s"], tcp_limit, rel_tol=1e-12)):
            raise ValueError("Review speed does not match the executable point limits")
        components.append(digest(data))
        attempts = bundle.get("coordination_attempts", [])
        paired = any(len(part["arms"]) > 1 for part in bundle["groups"])
        if not paired and attempts:
            failure = attempts[0]
            detail = next((p for p in failure.get("details", {}).get("pairs", [])
                           if p["clearance_with_stop_lower_bound_m"] <= p["model_margin_m"]), None)
            if detail:
                coordination.append(f"{expected_phase}: sequential. {' / '.join(detail['arms'])}, "
                                    f"geometry bound {1000*detail['geometric_clearance_lower_bound_m']:.0f} mm, "
                                    f"bound including a stop {1000*detail['clearance_with_stop_lower_bound_m']:.0f} mm, "
                                    f"required {1000*detail['model_margin_m']:.0f} mm.")
            else:
                coordination.append(f"{expected_phase}: sequential. {failure['reason']}")
        xml = read_checked(bundle["preview_urdf"], bundle["preview_urdf_sha256"]).decode()
        if start is None:
            start = dict(bundle["start"])
            last = dict(start)
            description = xml
            carton = dict(size_m=dimensions, T_world_object=bundle["carton"]["world_pose"],
                          shell_boxes=bundle["carton"]["shell_boxes"])
        if (set(bundle["start"]) != set(last) or any(abs(q-last[j]) > 1e-6 for j,q in bundle["start"].items())
                or carton["T_world_object"] != bundle["carton"]["world_pose"]):
            raise ValueError("Carton phases do not share the planned boundary state/pose")
        for part in bundle["groups"]:
            if not part["arms"] or set(part["trajectories"]) != set(part["arms"]):
                raise ValueError("Incomplete timed group")
            group = dict(phase=expected_phase, arms=part["arms"], trajectories=part["trajectories"])
            for trajectory in group["trajectories"].values():
                names = trajectory["joint_names"]
                points = trajectory["points"]
                if (not points or len(names) != 6 or len(points[0]["positions"]) != len(names)
                        or not all(abs(last[j]-q) <= 1e-6 for j,q in zip(names,points[0]["positions"]))):
                    raise ValueError("Discontinuous review trajectory")
                last.update(zip(names, points[-1]["positions"], strict=True))
            groups.append(group)
    duration = sum(max(t["duration_s"] for t in g["trajectories"].values()) for g in groups)
    if not math.isfinite(duration):
        raise ValueError("Non-finite plan duration")
    preview = dict(start=start, groups=groups, robot_description=description, carton=carton, duration_s=duration)
    meta = dict(task=TASK, summary="High approach and open entry with both right grippers",
                risk=risk, reason="\n".join([reason, *coordination]), stage="motion", arms=["right_front","right_rear"],
                duration_s=duration, speed_percent=speed, components=components, requires_area=True,
                explicit_regular_start=regular_start)
    return meta, preview


def current_capture(image_path, metadata_path, earliest, now):
    path, metadata_path = Path(image_path).resolve(), Path(metadata_path).resolve()
    raw_meta = metadata_path.read_bytes()
    capture = json.loads(raw_meta)
    started, finished = (datetime.fromisoformat(capture[k]) for k in ("started_at", "finished_at"))
    if (not capture["success"] or not started.tzinfo or not finished.tzinfo
            or not earliest <= started.timestamp() <= finished.timestamp() <= now
            or not capture.get("device_id") or capture.get("camera_ip") != "192.168.8.238"
            or not capture.get("standard", {}).get("path")
            or path != (metadata_path.parent / capture["standard"]["path"]).resolve()):
        raise ValueError("An OAK4 standard image acquired after the current work-area or entry boundary is required")
    return path, raw_meta, capture


def entry_photo(image_path, metadata_path, entry_finished_at, now):
    from PIL import Image
    path, raw_meta, capture = current_capture(image_path, metadata_path, entry_finished_at, now)
    raw = path.read_bytes()
    with Image.open(BytesIO(raw)) as image:
        if image.size != (capture["standard"]["width"], capture["standard"]["height"]):
            raise ValueError("Image dimensions differ from capture metadata")
        image.thumbnail((1920, 1440))
        display = BytesIO()
        image.convert("RGB").save(display, format="JPEG", quality=91)
    return dict(mime_type="image/jpeg", data_base64=base64.b64encode(display.getvalue()).decode(),
                display_sha256=digest(display.getvalue()),
                original_sha256=digest(raw), metadata_sha256=digest(raw_meta), captured_at=capture["finished_at"])


def contact_component(state_hash, image_hash, regular_start):
    from .motion_review import encoded
    return digest(encoded(dict(state=state_hash, image=image_hash, arms=["right_front","right_rear"],
                               force_raw=0, speed_raw=16, regular_start=bool(regular_start))).encode())


def motion_timing(directory, phase_start, phase_end):
    """Estimate physical overlap only from consecutive samples on the same N100 clock."""
    events = []
    observed = {}
    first = None
    for arm in ("right_front", "right_rear"):
        file = Path(directory) / (arm + "-native.json")
        if not file.exists():
            return dict(available=False, reason="Independent arm record missing")
        rows = read_json(file)["records"]
        windows = []
        for left, right in zip(rows, rows[1:]):
            t0, t1 = left["received"], right["received"]
            if not phase_start <= t0 < t1 <= phase_end or t1-t0 > .15:
                continue
            if all(max(abs(v) for v in row["v"]) > .003 for row in (left, right)):
                windows.append((t0, t1))
        if len(rows) < 2:
            return dict(available=False, reason=arm + " has insufficient native samples")
        observed[arm] = sum(b-a for a,b in windows)
        if windows:
            first = min(first, windows[0][0]) if first is not None else windows[0][0]
        for a,b in windows:
            events.extend(((a,1),(b,-1)))
    previous, active, overlap = phase_start, 0, 0.
    for t, change in sorted(events):
        if active == 2:
            overlap += t-previous
        active += change
        previous = t
    return dict(available=True, speed_threshold_rad_s=.003, max_sample_gap_s=.15,
                observed_motion_s=observed, observed_overlap_s=overlap, first_motion_monotonic_s=first)

"""Inputs and bounded strategy advice for the Return to Home task."""

import asyncio
import json
import math
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from carton_hydrogen import ACP, AGY, EFFORT, MODEL

PROGRAM = "return-to-home-v1"
TASK = "return_to_home"
ARMS = ("left_front", "left_rear", "right_front", "right_rear")
CARTON_ARMS = ("right_front", "right_rear")
RUN_ID = re.compile(r"[a-f0-9]{32}")
PROFILE_ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
ROUTES = ("direct", "upright_then_base", "rrt_connect")
PLACEMENT_ROUTES = ("level_then_lower", "raise_then_lower")


def arm_ids(value, *, allow_empty=False):
    if (not isinstance(value, list) or (not value and not allow_empty)
            or any(type(arm) is not str or arm not in ARMS for arm in value)
            or len(value) != len(set(value))):
        raise ValueError("Choose distinct cell arm IDs.")
    return [arm for arm in ARMS if arm in value]


def vector(value, size, label):
    if (not isinstance(value, list) or len(value) != size
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)):
        raise ValueError(f"Enter {size} finite numbers for {label}.")
    return value


def validate_request(value):
    if not isinstance(value, dict) or set(value) != {"arms", "objects", "scene_confirmed"}:
        raise ValueError("Choose arms and identify the objects currently held in the cell.")
    if value["scene_confirmed"] is not True:
        raise ValueError("Confirm the participating arms and all held objects.")
    arms = arm_ids(value["arms"])
    objects = value["objects"]
    if not isinstance(objects, list) or len(objects) > len(ARMS):
        raise ValueError("Enter one record per object held in the cell.")
    used = set()
    for row in objects:
        if not isinstance(row, dict):
            raise ValueError("Invalid held object.")
        action = row.get("action")
        if action not in ("place", "keep"):
            raise ValueError("Choose Put down or Keep holding for every object.")
        members = arm_ids(row.get("arms"))
        if used.intersection(members):
            raise ValueError("An arm can belong to only one grip group.")
        used.update(members)
        if action == "place" and not set(members) <= set(arms):
            raise ValueError("Select every arm in a grip group before choosing Put down.")
        if row.get("source") == "carton":
            fields = {"source", "run_id", "arms", "action", "release"}
            if (set(row) != fields or members != list(CARTON_ARMS)
                    or not isinstance(row.get("run_id"), str) or not RUN_ID.fullmatch(row["run_id"])):
                raise ValueError("Choose a completed two-arm carton lift from the Library.")
        elif row.get("source") == "manual":
            required = {"source", "arms", "action", "release", "name", "size_m",
                        "pose_xyz_yaw_deg", "position_error_m", "table", "target_xy_m", "profile"}
            if set(row) != required:
                raise ValueError("Enter measured geometry, pose and support for the manual object.")
            name, profile = row["name"], row["profile"]
            if not isinstance(name, str) or not name.strip() or len(name) > 80:
                raise ValueError("Enter an object name (up to 80 characters).")
            if profile and (not isinstance(profile, str) or not PROFILE_ID.fullmatch(profile)):
                raise ValueError("Use a valid local object profile ID.")
            if type(profile) is not str:
                raise ValueError("Invalid local object profile ID.")
            if min(vector(row["size_m"], 3, "enclosing dimensions (m)")) <= 0:
                raise ValueError("Object dimensions must be positive.")
            vector(row["pose_xyz_yaw_deg"], 4, "world bottom-centre XYZ (m), yaw (degrees)")
            vector(row["target_xy_m"], 2, "world support centre XY (m)")
            if row["table"] not in ("left", "right"):
                raise ValueError("Select the destination table.")
            error = vector([row["position_error_m"]], 1, "pose/placement error (m)")[0]
            if error < 0:
                raise ValueError("Pose/placement error must be nonnegative.")
        else:
            raise ValueError("Choose an archived carton or enter a measured object.")
        if row.get("release") not in ("support", "drop"):
            raise ValueError("Choose supported release or the profiled short drop.")
    return dict(arms=arms, objects=objects, scene_confirmed=True)


def parse_advice(raw):
    fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", raw.strip(), re.DOTALL | re.IGNORECASE)
    result = json.loads(fenced[1] if fenced else raw)
    if not isinstance(result, dict) or set(result) != {"home_routes", "placement_routes", "reason", "assumptions"}:
        raise ValueError("Unexpected Hydrogen advice format.")
    for key, available in (("home_routes", ROUTES), ("placement_routes", PLACEMENT_ROUTES)):
        order = result[key]
        if (not isinstance(order, list) or len(order) != len(available)
                or any(type(x) is not str for x in order) or set(order) != set(available)):
            raise ValueError("Hydrogen must rank the locally defined routes.")
    reason, assumptions = result["reason"], result["assumptions"]
    if (not isinstance(reason, str) or not 0 < len(reason.strip()) <= 640
            or not isinstance(assumptions, list) or len(assumptions) > 6
            or any(not isinstance(x, str) or not 0 < len(x.strip()) <= 240 for x in assumptions)):
        raise ValueError("Invalid Hydrogen reason or assumptions.")
    return result


async def request_advice(summary):
    prompt = (
        "Rank the supplied placement and Home route IDs for this UWA cell recovery. "
        "Consider the ordered phases: for each selected load an upright common-object translation "
        "to the confirmed support, shared descent, stationary opening, then straight upward "
        "withdrawal before any Home route. A kept load remains stationary. "
        "In place, use vertical descent. For a different support centre, level_then_lower uses the "
        "starting height for the lateral leg. raise_then_lower makes a short vertical lift first. "
        "The operator selects supported vs profiled short-drop release. A local compiler owns geometry, "
        "trajectory, checks and permissions. Do not use tools or invent measurements, targets, actions, "
        "limits, or permissions. Reply only with JSON keys home_routes and placement_routes "
        "(each list contains all its available IDs in priority order), reason (one short paragraph), "
        "and assumptions (list of unresolved facts).\n"
        + json.dumps(summary, allow_nan=False)
    )
    with TemporaryDirectory(prefix="uwa-home-hydrogen-") as isolated:
        process = await asyncio.create_subprocess_exec(
            str(AGY), "acp", "--include-default-customizations=false", "--disable-telemetry",
            cwd=isolated, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        client = ACP(process)
        try:
            async with asyncio.timeout(12):
                await client.request("initialize", {
                    "protocolVersion": 1, "clientCapabilities": {},
                    "clientInfo": {"name": "uwa-return-home", "version": "1"},
                })
                session = await client.request("session/new", {"cwd": isolated, "mcpServers": []})
                client.session_id = session["sessionId"]
                params = {"sessionId": client.session_id}
                await client.request("session/set_config_option", {**params, "configId": "model", "value": MODEL})
                config = await client.request("session/set_config_option",
                    {**params, "configId": "thought_level", "value": EFFORT})
                selected = {item["id"]: item["currentValue"] for item in config["configOptions"]}
                if selected.get("model") != MODEL or selected.get("thought_level") != EFFORT:
                    raise ValueError("Antigravity did not select Hydrogen Low.")
            async with asyncio.timeout(20):
                response = await client.request("session/prompt",
                    {**params, "prompt": [{"type": "text", "text": prompt}]})
            if response.get("stopReason") != "end_turn" or client.used_tools:
                raise ValueError("Hydrogen must return one tool-free strategy.")
            return dict(parse_advice("".join(client.text)), source=MODEL, effort=EFFORT)
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.communicate(), 1.)
            except TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()


def advice(summary, *, use_model=True):
    if use_model:
        try:
            return asyncio.run(request_advice(summary))
        except (OSError, ValueError, RuntimeError, TimeoutError, KeyError, TypeError) as error:
            reason = f"Hydrogen unavailable: {type(error).__name__}: {error}"
    else:
        reason = "Deterministic regression fixture."
    return dict(home_routes=list(ROUTES), placement_routes=list(PLACEMENT_ROUTES),
                source="local", reason=reason, assumptions=[])


def recorded_carton(directory):
    """Use the completed weighing record, never a pending or incomplete grasp."""
    out = Path(directory)
    run = json.loads((out / "run.json").read_text())
    workflow = json.loads((out / "n100-contact-workflow.json").read_text())
    result = json.loads((out / "progress.json").read_text())
    if (run.get("program") != "carton-supported-v1" or result.get("phase") != "done"
            or workflow.get("success") is not True
            or workflow.get("phase") not in ("CARTON_LIFTED_AND_WEIGHED", "CARTON_LIFTED_WEIGHING_UNAVAILABLE")
            or workflow.get("closing_control_result_success") is not True):
        raise ValueError("Selected run has no completed two-arm carton lift.")
    return workflow

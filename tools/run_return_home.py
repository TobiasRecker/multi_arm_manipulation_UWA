#!/usr/bin/env python3
"""Program Library workflow for planning and reviewed Return to Home execution."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from return_home_request import ARMS, CARTON_ARMS, PLACEMENT_ROUTES, PROGRAM, ROUTES, RUN_ID, advice, recorded_carton, validate_request
from run_carton_program import (
    CELL, REPO, WORKSPACE, Progress, capture_oak, carton_camera, live_inputs, load_json,
    logged_command, n100, offline_tool, selected_runtime, upload,
)

PURPOSE = "return-to-home"
OBSERVE = """source "$1/scripts/control_env.bash"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -c '
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from uwa_cell_motion.common import config
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_tasks.minimal_snapshot import observe
from uwa_cell_tasks.motion_review import ReviewStore
binding = {}
exec(sys.argv[2], binding)
repo = Path(sys.argv[1]).resolve()
status = ReviewStore().status("return_to_home")
with TemporaryDirectory(prefix="return-home-model-") as folder:
    model = HardwareProblem(Path(folder), config(repo / "uwa_cell_motion/config/hardware_carton_supported_trend.yaml"),
                            repo / "config/hardware_inventory.yaml")
    snapshot = observe()
    if snapshot["model_signature"] != model.signature:
        raise ValueError("The active N100 collision model differs from its local planning model.")
    snapshot["model_identity"] = binding["model_identity"](model)
if sys.argv[3] == "live":
    from uwa_cell_motion.minimal_execution import protection_call
    protection = protection_call("status")["detail"]
    status["protection"] = {key: protection[key] for key in ("known_collisions", "unavailable_arms")}
print(json.dumps(dict(snapshot=snapshot, status=status), allow_nan=False))
' "$1" "$2" "$3"
"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def last_carton(runs):
    candidates = sorted((path for path in runs.glob("*/n100-contact-workflow.json")
                         if RUN_ID.fullmatch(path.parent.name)),
                        key=lambda path: path.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            result = recorded_carton(path.parent)
        except (OSError, ValueError, TypeError, KeyError):
            continue
        return dict(id=path.parent.name, date=result.get("updated_wall"), arms=list(CARTON_ARMS))
    return None


def catalog(runs, live):
    carton = last_carton(runs)
    return dict(id=PROGRAM, kind="return_to_home", title="Return to Home",
                description="Plan checked Home paths and put down held objects with up to four arms.",
                object="Held objects or unloaded arms", arms=[arm.replace("_", " ").title() for arm in ARMS],
                plan_available=live, live_available=live, demo_available=carton is not None,
                recorded_carton=carton,
                live_blocker=None if live else "Open the N100-enabled UWA Robot Power Library for current plans.",
                stages=[
                    dict(id="snapshot", title="Read the current scene", description="Use a fresh four-arm snapshot and confirm which arms hold each object."),
                    dict(id="planning", title="Check the complete return", description="Hydrogen ranks routes. The local planner checks carried objects, open withdrawal and the Home paths."),
                    dict(id="pilot_review", title="Independent first review", description="The first loaded revision is checked independently before the operator reviews motion."),
                    dict(id="lower", title="Carry and lower", description="Each grip group follows a common object path to the planned support."),
                    dict(id="open", title="Release the object", description="Approve the actual placement image in Motion Review before the grippers open."),
                    dict(id="withdraw", title="Withdraw straight up", description="Inspect the settled object and the open jaws before withdrawing."),
                    dict(id="home", title="Return to Home", description="Follow the reviewed paths with available arms. Kept loads stay in place."),
                ])


def recorded_fixture(out, runs):
    carton = last_carton(runs)
    if carton is None:
        raise ValueError("No completed recorded carton lift is available for the offline demo.")
    source = runs / carton["id"]
    proof = load_json(source / "plan/weigh-plan/proof.json")
    review = load_json(source / "plan/weigh-plan/review.json")
    snapshot = load_json(source / "observations.json")
    snapshot["model_signature"] = review["model_signature"]
    for arm in ARMS:
        names = review["groups"][0]["trajectories"].get(arm, {}).get("joint_names")
        if names:
            snapshot["arms"][arm]["samples"][-1]["actual_q"] = [proof["end"][joint] for joint in names]
    request = dict(arms=list(CARTON_ARMS), scene_confirmed=True, objects=[
        dict(source="carton", run_id=carton["id"], arms=list(CARTON_ARMS), action="place", release="support")])
    return request, snapshot


def observe(out, *, live=False):
    if selected_runtime() is None:
        raise ValueError("Open the Library from the active N100 minimal Robot Power instance.")
    module = (REPO / "tools/return_home_model.py").read_text()
    raw = logged_command(n100(OBSERVE, CELL, module, "live" if live else "plan"),
                         out / "n100-observation.log", 30, separate_stdout=True)
    data = json.loads(raw)
    if data["snapshot"].get("protection_backend") != "minimal":
        raise ValueError("The configured N100 did not provide minimal protection state.")
    return data["snapshot"], data["status"]


def strategy(request, *, use_model=True):
    # The recurring bounded prompt contains no real arm IDs, names, images,
    # positions, machine settings, or raw robot evidence.
    summary = dict(number_selected=len(request["arms"]), home_routes=list(ROUTES), placement_routes=list(PLACEMENT_ROUTES),
                   held_groups=[dict(members=len(row["arms"]), handling=row["action"], release=row["release"])
                                for row in request["objects"]])
    return advice(summary, use_model=use_model)


def phase_list(plan):
    for item in plan["objects"]:
        if item["loaded"]:
            yield "lower", True
        if item.get("commissioning"):
            continue
        yield "open", True
        yield "withdraw", True
    if plan["home"]:
        yield "home", False


def summarize(plan, path):
    phases = [group for obj in plan["objects"] for group in obj["loaded"] + obj["retreat"]] + plan["home"]
    steps = []
    for obj in plan["objects"]:
        steps.extend(group["phase"] for group in obj["loaded"])
        if not obj.get("commissioning"):
            steps.append("Open grippers")
            steps.extend(group["phase"] for group in obj["retreat"])
    steps.extend(group["phase"] for group in plan["home"])
    text = " → ".join(steps) or "Selected arms already Home or keeping their held loads."
    return dict(plan=text, motion=" ".join(plan["live_blockers"]) or "Whole-cell geometry checked.",
                kept_arms=", ".join(plan["kept_arms"]), strategy=plan["advice"]["reason"],
                strategy_source=plan["advice"]["source"], duration_s=sum(group["duration_s"] for group in phases),
                plan_sha256=sha(path))


def wait_for_first_review(out, path, first_marker, progress, result):
    if not any(item["loaded"] for item in load_json(path)["objects"]) or first_marker.is_file():
        return
    progress.update("pilot_review", "First loaded Return to Home revision awaits independent Codex review.", result=result)
    mark = out / "pilot-review.json"
    deadline = time.monotonic() + 900.
    while time.monotonic() < deadline:
        if mark.is_file():
            review = load_json(mark)
            if review.get("plan_sha256") != sha(path) or review.get("approved") is not True:
                raise ValueError("First-use review did not approve this frozen revision.")
            return
        time.sleep(.5)
    raise TimeoutError("The first-use Codex review expired before motion review.")


def record_carton_continuation(out):
    path = out / "planning/plan.json"
    plan = load_json(path)
    report_file = out / "phase-0.json"
    report = load_json(report_file)
    request = load_json(out / "request.json")
    item, = plan["objects"]
    probe, = item["loaded"]
    segment, = report["segments"]
    delta = probe["object_delta_m"]
    if (plan.get("commissioning") is not True or report["success"] is not True
            or report["plan_sha256"] != sha(path) or report.get("finger_commands")
            or segment.get("executed") is not True or delta[:2] != [0., 0.] or abs(delta[2] + .003) > 1e-9):
        raise ValueError("Carton continuation needs a confirmed 3 mm commissioning phase.")
    path = WORKSPACE / "setup/skill_library/return-home-profiles/avocado-carton-continuation.json"
    write(path, dict(grasp_run=request["objects"][0]["run_id"], profile_sha256=item["qualification_sha256"],
                     expected_end=plan["end"], measured_gap_m=item["reported_gap_m"],
                     model_identity=plan["model_identity"], phase_sha256=sha(report_file),
                     source_phase=str(report_file.relative_to(WORKSPACE))))


def remote_phase(remote, index, digest, status, out, phase, picture):
    files = []
    if picture:
        image, metadata = picture
        name = f"photo-{index}"
        logged_command(n100('mkdir -- "$1"', remote + "/" + name), out / f"remote-photo-{index}.log", 20)
        upload(remote + "/" + name + "/", image, out / f"upload-photo-{index}.log", metadata)
        files = [remote + "/" + name + "/standard.png", remote + "/" + name + "/metadata.json"]
    script = """folder=$1
cell=$2
revision=$3
session=$4
index=$5
executor_hash=$6
review_hash=$7
area_at=$8
model_hash=$9
shift 9
source "$cell/scripts/control_env.bash"
[[ $(sha256sum -- "$folder/execute_return_home.py" | cut -d ' ' -f 1) == "$executor_hash" ]]
[[ $(sha256sum -- "$folder/return_home_review_store.py" | cut -d ' ' -f 1) == "$review_hash" ]]
[[ $(sha256sum -- "$folder/return_home_model.py" | cut -d ' ' -f 1) == "$model_hash" ]]
if [[ $# -eq 2 ]]; then
    set -- --photo "$1" --metadata "$2"
fi
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -Bu "$folder/execute_return_home.py" \
  --plan "$folder/plan.json" --sha256 "$revision" --index "$index" --session "$session" --area-at "$area_at" "$@"
"""
    worker = REPO / "tools/execute_return_home.py"
    review = REPO / "uwa_cell_tasks/uwa_cell_tasks/motion_review.py"
    model = REPO / "tools/return_home_model.py"
    log = out / f"n100-{index}-{phase}.log"
    run = n100(script, remote, CELL, digest, status["session_id"], index, sha(worker), sha(review),
               status["area_released_at"], sha(model), *files)
    with log.open("w") as stream, subprocess.Popen(
            [str(arg) for arg in run], cwd=WORKSPACE, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as child:
        for line in child.stdout:
            stream.write(line)
            stream.flush()
            if line.strip() == "WAITING_FOR_OPERATOR_RESUME":
                yield "resume", None
            elif line.startswith("WAITING_FOR_"):
                yield "waiting", line.strip().rsplit(" ", 1)[-1]
            elif line.startswith("REVIEW_ACCEPTED_"):
                yield "accepted", line.strip().rsplit(" ", 1)[-1]
        code = child.wait()
    saved = logged_command(n100('cat -- "$1/phase-$2.json"', remote, index),
                           out / f"n100-{index}-result.log", 15, separate_stdout=True)
    result = json.loads(saved)
    write(out / f"phase-{index}.json", result)
    if code or not result["success"]:
        raise RuntimeError(result.get("error") or f"N100 phase {phase} did not complete. See Safety log.")
    yield "complete", result


def execute(plan, path, out, status, live_config, progress, result):
    first_marker = out.parent / ".return-home-first-loaded-reviewed.json"
    wait_for_first_review(out, path, first_marker, progress, result)
    remote = f"setup/tasks/{PURPOSE}/{out.name}"
    worker = REPO / "tools/execute_return_home.py"
    review = REPO / "uwa_cell_tasks/uwa_cell_tasks/motion_review.py"
    model = REPO / "tools/return_home_model.py"
    logged_command(n100('mkdir -p -- "$(dirname -- "$1")"; mkdir -- "$1"', remote),
                   out / "n100-handoff.log", 20)
    upload(remote + "/", path, out / "upload-execution.log", worker, model)
    upload(remote + "/return_home_review_store.py", review, out / "upload-review-store.log")
    camera = None
    try:
        if plan["objects"]:
            cam = live_inputs(live_config)
            camera = carton_camera(out, cam["focus"])
            camera.start()
        for index, (phase, contact) in enumerate(phase_list(plan)):
            photo = capture_oak(out, f"phase-{index}", camera) if contact else None
            for event, value in remote_phase(remote, index, sha(path), status, out, phase, photo):
                if event in ("waiting", "accepted"):
                    message = ("Review the current phase in UWA Robot Power." if event == "waiting"
                               else "Review accepted. Executing the frozen phase on the N100.")
                    progress.update(phase, message, result=dict(result, review_id=value))
                elif event == "resume":
                    progress.update(phase, "Review approved. Waiting for explicit operator RESUME in UWA Robot Power.",
                                    result=result)
    finally:
        if camera is not None:
            camera.stop()
    if plan["objects"] and not plan.get("commissioning") and not first_marker.exists():
        write(first_marker, dict(plan_sha256=sha(path), run=out.name))
    if plan.get("commissioning"):
        record_carton_continuation(out)
        return dict(result, commissioning=True, remote_run=remote,
                    motion="Commissioning descent complete. Both grippers keep holding the carton.")
    return dict(result, remote_run=remote, motion="All selected and released arms have completed the checked sequence.")


def run(args, progress):
    out = progress.output
    progress.update("snapshot", "Reading the four-arm start and the selected held-object records.")
    if args.mode == "demo":
        request, snapshot = recorded_fixture(out, args.runs)
        status = {"settings": {"speed_percent": 100 / 3}}
    else:
        request = validate_request(load_json(args.request))
        snapshot, status = observe(out, live=args.mode == "live")
        if args.mode == "live":
            if not status["area_released"]:
                raise ValueError("Release the work area in UWA Robot Power before preparing a live return.")
            if status["pending"]:
                raise ValueError("Finish the existing Motion Review before starting Return to Home.")
            if status["protection"]["known_collisions"]:
                conflict = status["protection"]["known_collisions"][0]
                links = " / ".join(conflict.get("links", []))
                raise ValueError(f"The N100 retains a geometry conflict ({links}). Inspect the UWA Robot Power Safety log.")
    write(out / "snapshot.json", snapshot)
    write(out / "request.json", request)
    progress.update("planning", "Requesting one bounded Hydrogen strategy, then checking every phase locally.")
    recommendation = (load_json(args.advice) if args.advice else strategy(request))
    write(out / "advice.json", recommendation)
    planning = out / "planning"
    progress.update("planning", "Checking the loaded path, stationary release, withdrawal and Home from the frozen inputs.")
    logged_command(offline_tool("prepare_return_home.py", "--request", out / "request.json",
        "--snapshot", out / "snapshot.json", "--advice", out / "advice.json", "--runs", args.runs,
        "--output", planning, "--speed-percent", status["settings"]["speed_percent"]),
        out / "compile.log", 420)
    path = planning / "plan.json"
    plan = load_json(path)
    result = summarize(plan, path)
    if args.mode == "live":
        if plan["live_blockers"]:
            raise ValueError(" ".join(plan["live_blockers"]))
        if recommendation["source"] == "local":
            raise ValueError("Hydrogen unavailable. The locally checked plan is saved. Use Plan only to inspect it.")
        if list(phase_list(plan)):
            result = execute(plan, path, out, status, args.live_config, progress, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("demo", "plan", "live"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--advice", type=Path)
    parser.add_argument("--live-config", type=Path)
    parser.add_argument("--accept-first-review", metavar="PLAN_SHA256")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.accept_first_review:
        path = args.output / "planning/plan.json"
        if sha(path) != args.accept_first_review or load_json(path)["live_blockers"]:
            parser.error("First-use review needs the exact qualified plan digest.")
        write(args.output / "pilot-review.json", dict(approved=True, plan_sha256=args.accept_first_review))
        return 0
    if args.mode is None or (args.mode != "demo" and args.request is None):
        parser.error("Select a program mode and supply the live request where required.")
    if args.advice and args.mode != "demo":
        parser.error("Replay advice is available only for the offline demo.")
    args.output.mkdir(parents=True, exist_ok=True)
    progress = Progress(args.output)
    try:
        result = run(args, progress)
    except Exception as error:
        path = args.output / "planning/plan.json"
        fields = {"result": summarize(load_json(path), path)} if path.is_file() else {}
        progress.update("failed", str(error), error=str(error), **fields)
        return 1
    if result.get("commissioning"):
        message = "Commissioning descent complete. Both grippers keep holding the carton."
    elif args.mode == "live":
        message = "Return to Home complete."
    else:
        message = "Offline Return to Home plan saved. No motion commands sent."
    progress.update("done", message, result=result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

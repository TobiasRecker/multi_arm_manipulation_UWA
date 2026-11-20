#!/usr/bin/env python3
"""Run the carton library program on recorded inputs or through N100 review."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

import carton_hydrogen
from carton_camera_session import create_session, validate_session, write_session

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
CELL = REPO.relative_to(WORKSPACE)
PROGRAM = "carton-supported-v1"
INTRINSICS = Path("setup/calibration/oak_capture_proposal_20261118/calibration_candidate_v1/oak_pose_candidate.json")
LIVE_PROFILE = CELL / "uwa_cell_motion/config/hardware_carton_supported_trend.yaml"
RECIPE_CACHE = WORKSPACE / "setup/skill_library/carton-recipes"
CHECKER_PREFIX = WORKSPACE / "setup/skill_library/n100-checker"
CHECKER_QUERY = """import json
from pathlib import Path
import sys
cell = Path(sys.argv[1]).resolve(strict=True)
sys.path.insert(0, str(cell / 'uwa_cell_tasks'))
from uwa_cell_tasks.reviewed_carton import checker_identity
print(json.dumps(checker_identity(cell / 'tools')))
"""
N100_HOST = "uwa-n100-robot-lan"
SSH_CONFIG = WORKSPACE / "setup/n100/ssh_config"
SSH_OPTIONS = [
    "-F", str(SSH_CONFIG), "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
    "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=3",
]
N100_WORKSPACE = """set -e
test "$(hostname)" = miniminiPC
cd "$HOME/uwa-ur-runtime"
"""
DEMO_PHOTO = WORKSPACE / "setup/oak4/photos/20261119-132416-standard-a0bac111"
DEMO_REFERENCE = WORKSPACE / "setup/tasks/carton_grasp_20261119/registration/object-pose.json"
DEMO_MODEL = WORKSPACE / "setup/tasks/carton_grasp_20261119/recipe/hardware.urdf"
DEMO_OBSERVATIONS = WORKSPACE / (
    "setup/tasks/carton_new_pose_20261119/n100-evidence/setup/tasks/"
    "carton_new_pose_20261119/cycle/snapshot/observations.json"
)
DEMO_WRISTS = WORKSPACE / "setup/tasks/carton_grasp_20261118_wrist01"
DEMO_ROI = (2400, 2850, 5000, 5050)


class Progress:
    def __init__(self, output):
        self.output = output
        self.path = output / "progress.json"
        self.events = []

    def update(self, phase, message, **fields):
        self.events.append({
            "phase": phase, "message": message,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({
            "phase": phase, "message": message, "events": self.events, **fields,
        }, indent=2, allow_nan=False) + "\n")
        temporary.replace(self.path)


def load_json(path):
    return json.loads(path.read_text())


def logged_command(command, log_path, timeout, *, separate_stdout=False):
    with log_path.open("w+") as log:
        try:
            completed = subprocess.run([str(arg) for arg in command], cwd=WORKSPACE,
                                       stdout=subprocess.PIPE if separate_stdout else log,
                                       stderr=log if separate_stdout else subprocess.STDOUT,
                                       text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"{log_path.stem} timed out after {timeout} s. See {log_path.name}.") from error
        if separate_stdout:
            log.write(completed.stdout)
        log.seek(0)
        output = log.read()
    if completed.returncode:
        lines = output.strip().splitlines()
        reason = lines[-1] if lines and lines[-1] not in {"{", "}"} else f"See {log_path.name}."
        raise RuntimeError(f"{log_path.stem} failed: {reason}")
    return completed.stdout if separate_stdout else output


def offline_command(*args, checker_prefix=None):
    environment = WORKSPACE / "setup/lyrical_env.bash"
    return [
        "/bin/bash", "-c",
        'source "$1" || exit $?; if [[ -n $2 ]]; then export AMENT_PREFIX_PATH="$2:$AMENT_PREFIX_PATH"; fi; '
        'shift 2; export ROS_DOMAIN_ID=74 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST '
        'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1; exec "$@"',
        "uwa-carton-program", environment, checker_prefix or "", *args,
    ]


def offline_tool(script, *args, checker_prefix=None):
    return offline_command(sys.executable, REPO / "tools" / script, *args, checker_prefix=checker_prefix)


def run_demo(program, progress):
    out = progress.output
    progress.update("oak_registration", "Fitting the carton pose from the recorded native OAK4 image.")
    registration = out / "registration"
    command = offline_tool(
        "register_carton_from_oak.py", "--image", DEMO_PHOTO / "standard.png",
        "--metadata", DEMO_PHOTO / "metadata.json", "--intrinsics", WORKSPACE / INTRINSICS,
        "--description", DEMO_MODEL, "--camera-reference-pose", DEMO_REFERENCE,
        "--roi", *DEMO_ROI, "--face-roi", *DEMO_ROI, "--planar-texture", "--output", registration,
    )
    logged_command(command, out / "oak-registration.log", 120)
    pose = load_json(registration / "registration.json")
    if pose.get("success") is not True:
        raise ValueError("OAK4 registration did not confirm the carton pose.")

    progress.update("offline_plan", "Preparing and checking the approach from recorded arm observations.")
    plan = out / "plan"
    command = offline_tool(
        "run_carton_cycle.py", "--plan-only", "--program", program,
        "--observations", DEMO_OBSERVATIONS, "--object-pose", registration / "object-pose.json",
        "--output", plan,
    )
    logged_command(command, out / "offline-plan.log", 240)
    workflow = load_json(plan / "workflow.json")
    if workflow.get("phase") != "OFFLINE_APPROACH_PREPARED":
        raise ValueError("The offline planner did not prepare a checked approach.")
    high = load_json(plan / "review-high.json")
    entry = load_json(plan / "review-entry.json")
    parallel = all(
        len(bundle["groups"]) == 1 and set(bundle["groups"][0]["arms"]) == {"right_front", "right_rear"}
        for bundle in (high, entry)
    )
    timing = sum(group["duration_s"] for bundle in (high, entry) for group in bundle["groups"])

    progress.update("wrist_diagnostic", "Checking the carton rim in separate recorded wrist-camera images.")
    wrist = out / "wrist"
    command = offline_tool("check_carton_wrist.py", "--fixture-dir", DEMO_WRISTS, "--output", wrist)
    logged_command(command, out / "wrist-diagnostic.log", 90)
    diagnostic = load_json(wrist / "result.json")
    position = ", ".join(f"{row[3]:.3f}" for row in pose["T_world_object"][:3])
    wrist_summary = ", ".join(f"{camera.replace('_', ' ').title()}: {value['status'].replace('_', ' ')}"
                              for camera, value in diagnostic["arms"].items())
    return {
        "pose": f"OAK4 fit at ({position}) m in world coordinates · {pose['board_corners']} board corners",
        "plan": f"{'Parallel approach' if parallel else 'Grouped approach'} · {timing:.1f} s nominal motion",
        "wrist": f"Separate recorded images · {wrist_summary} · operator review required",
        "artifacts": {
            "registration": "registration/registration.json",
            "oak_preview": "registration/pose-preview.jpg",
            "plan": "plan/workflow.json",
            "wrist": "wrist/result.json",
            **{f"{camera}_preview": f"wrist/{value['overlay']}" for camera, value in diagnostic["arms"].items()
               if value.get("overlay")},
        },
    }


def live_inputs(path):
    if path is None:
        raise ValueError("Live mode requires an explicit, locally enabled camera configuration.")
    config = load_json(path)
    if not isinstance(config, dict) or config.get("enabled") is not True:
        raise ValueError("Live mode is disabled in the local configuration.")
    fields = {"enabled", "intrinsics", "roi", "face_roi", "camera_reference_pose", "camera_session", "planar_texture"}
    if set(config) - fields:
        raise ValueError("Live config contains unknown fields.")
    if not isinstance(config.get("planar_texture", False), bool):
        raise ValueError("planar_texture must be true or false.")
    if "camera_session" in config:
        session = config["camera_session"]
        if not isinstance(session, str) or not session.strip() or config.get("camera_reference_pose"):
            raise ValueError("Configure a camera session file or a legacy camera reference.")
        config["camera_session"] = (path.parent / session).resolve()
    for key in ("intrinsics", "camera_reference_pose"):
        value = config.get(key)
        if value is None and key == "camera_reference_pose":
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Live config needs a file path for {key}.")
        file = (path.parent / value).resolve(strict=True)
        if not file.is_file():
            raise ValueError(f"{key} is not a file.")
        config[key] = file

    intrinsics = load_json(config["intrinsics"])
    intrinsics = intrinsics.get("intrinsics", intrinsics)
    if type(intrinsics.get("focus")) is not int or not 0 <= intrinsics["focus"] <= 255:
        raise ValueError("Live OAK intrinsics need a manual focus value from 0 to 255.")
    if intrinsics.get("image_size") != [8000, 6000]:
        raise ValueError("Live OAK intrinsics must match the native 8000 × 6000 Standard capture.")
    if not all(name in intrinsics for name in ("K", "D")):
        raise ValueError("Live OAK intrinsics need K and D calibration data.")
    for key in ("roi", "face_roi"):
        roi = config.get(key)
        if (not isinstance(roi, list) or len(roi) != 4 or any(type(value) is not int for value in roi)
                or not (0 <= roi[0] < roi[2] <= 8000 and 0 <= roi[1] < roi[3] <= 6000)):
            raise ValueError(f"Live config {key} needs a valid crop [x0, y0, x1, y1] in native pixels.")
    reference = config.get("camera_reference_pose")
    if reference and not reference.with_name("registration.json").is_file():
        raise ValueError("Camera reference needs its original sibling registration.json.")
    config["focus"] = intrinsics["focus"]
    return config


def n100(script, *args):
    command = shlex.join(["/bin/bash", "-c", N100_WORKSPACE + script, "uwa-carton-program",
                          *map(str, args)])
    return ["/usr/bin/ssh", *SSH_OPTIONS, "-T", N100_HOST, command]


def n100_preflight(out, program):
    files = [
        CELL / "tools/run_carton_cycle.py",
        CELL / "tools/register_carton_from_oak.py",
        CELL / "tools/carton_camera_session.py",
        CELL / "tools/start_carton_browser_programs.py",
        CELL / "scripts/ur_bringup.py",
        CELL / "config/carton_programs" / f"{program}.json",
        LIVE_PROFILE,
    ]
    arguments = []
    for file in files:
        with (WORKSPACE / file).open("rb") as source:
            arguments.extend([hashlib.file_digest(source, "sha256").hexdigest(), file])
    command = n100("""test -r install_lyrical/setup.bash
while [[ $# -gt 2 ]]; do
    actual=$(sha256sum -- "$2")
    if [[ ${actual%% *} != "$1" ]]; then
        printf 'N100 needs the matching qualified version of %s.\n' "$2" >&2
        exit 1
    fi
    shift 2
done
printf '%s\n' "$PWD"
./review.sh status
source "$1/scripts/control_env.bash"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -c "$2" "$1"
""", *arguments, CELL, CHECKER_QUERY)
    workspace_path, status_text, checker_text = logged_command(
        command, out / "n100-preflight.log", 25, separate_stdout=True,
    ).splitlines()
    target_workspace = Path(workspace_path)
    if not target_workspace.is_absolute() or target_workspace.name != "uwa-ur-runtime":
        raise ValueError("Unexpected N100 runtime workspace.")
    status = json.loads(status_text)
    if not status.get("area_released"):
        raise ValueError("Release the physical work area in UWA Robot Power before starting the live program.")
    if any(item.get("status") in {"pending", "approved", "running"} for item in status.get("pending", [])):
        raise ValueError("A motion review is already open. Finish it in UWA Robot Power before starting a new run.")
    prefix = CHECKER_PREFIX if CHECKER_PREFIX.is_dir() else None
    local = logged_command(offline_command(sys.executable, "-c", CHECKER_QUERY, REPO, checker_prefix=prefix),
                           out / "rosmini-checker.log", 25, separate_stdout=True)
    local_checker = json.loads(local)
    target_checker = json.loads(checker_text)
    if local_checker != target_checker:
        parts = local_checker["components"]
        target_parts = target_checker["components"]
        changed = sorted(key for key in parts.keys() | target_parts.keys() if parts.get(key) != target_parts.get(key))
        raise ValueError("ROSmini and N100 use different trajectory checker components: " + ", ".join(changed))
    return target_workspace, status, prefix


def capture_oak(out, name, focus):
    photo_tool = WORKSPACE / "src/oak_camera_calibration/tools/oak4_photo.sh"
    raw = logged_command(
        ["/bin/bash", photo_tool, "capture", "--mode", "standard", "--focus", focus],
        out / f"{name}-capture.log", 320,
    )
    data = json.loads(raw)
    directory = Path(data["directory"]).resolve(strict=True)
    image = Path(data["images"]["standard"]).resolve(strict=True)
    metadata = Path(data["metadata"]).resolve(strict=True)
    if data.get("mode") != "standard" or image != directory / "standard.png" or metadata != directory / "metadata.json":
        raise ValueError("Expected an original OAK Standard image and metadata pair.")
    return image, metadata


def calibrate_camera(progress, config_path):
    config = live_inputs(config_path)
    session_path = config.get("camera_session")
    if session_path is None:
        raise ValueError("Enable the local ChArUco camera session in the program configuration.")
    # Starting a calibration after moving the camera revokes the old reference
    # even if the new capture fails. Successful prior runs keep their copies.
    session_path.unlink(missing_ok=True)
    progress.update("oak_calibration", "Capturing and fitting the OAK4 right table reference with ChArUco.")
    requested = datetime.now(timezone.utc)
    photo_tool = WORKSPACE / "src/oak_camera_calibration/tools/oak4_photo.sh"
    raw = logged_command(["/bin/bash", photo_tool, "capture", "--mode", "charuco"],
                         progress.output / "charuco-capture.log", 320)
    result = json.loads(raw)
    directory = Path(result["directory"]).resolve(strict=True)
    if result.get("mode") != "charuco" or Path(result["metadata"]).resolve() != directory / "metadata.json":
        raise ValueError("Expected a native ChArUco capture and its metadata.")
    session = create_session(directory, config["intrinsics"], requested_at=requested)
    write_session(progress.output / "camera-session.json", session)
    write_session(session_path, session)
    return {"calibration": f"Right table · {session['right_marker_count']} markers · "
            f"{session['held_out_rms_px']:.2f} px held-out RMS", "valid_until": session["valid_until"]}


def upload(remote, local_file, log_path):
    command = [
        "/usr/bin/scp", *SSH_OPTIONS, str(local_file),
        f"{N100_HOST}:uwa-ur-runtime/{remote}",
    ]
    logged_command(command, log_path, 100)


def observe_start(remote, out, scene, progress):
    command = n100("""mkdir -- "$1"
mkdir -- "$1/entry"
source "$2/scripts/control_env.bash"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 "$2/tools/start_carton_browser_programs.py" --output "$1" \
  --config "$3" --scene-session "$4"
""", remote, CELL, LIVE_PROFILE, scene)
    progress.update("snapshot", "Checking External Control and starting the stopped carton programs on the N100 if needed.")
    logged_command(command, out / "n100-browser-play.log", 75)
    progress.update("snapshot", "Reading the four arms and grippers for planning.")
    command = n100("""source "$2/scripts/control_env.bash"
/usr/bin/python3 "$2/tools/prepare_carton_hardware.py" --observe \
  --stationarity-config "$3" --output "$1/observed" > "$1/observe.log"
exec cat -- "$1/observed/observations.json"
""", remote, CELL, LIVE_PROFILE)
    observations = out / "observations.json"
    observations.write_text(logged_command(command, out / "n100-snapshot.log", 25, separate_stdout=True))
    logged_command(offline_tool("prepare_carton_hardware.py", "--validate-planning-snapshot", observations),
                   out / "check-snapshot.log", 20)
    return observations


class CartonFitRejected(ValueError):
    """The camera inputs were valid, but the current carton fit was rejected."""


def register_attempt(config, out, recipe, image, metadata, windows, suffix=""):
    options = []
    if config.get("camera_session"):
        options.extend(["--camera-session", out / "camera-session.json"])
    elif reference := config.get("camera_reference_pose"):
        options.extend(["--camera-reference-pose", reference])
    if config.get("planar_texture"):
        options.append("--planar-texture")

    registration = out / f"registration{suffix}"
    roi, face_roi = windows
    command = offline_tool("register_carton_from_oak.py", "--image", image, "--metadata", metadata,
                           "--intrinsics", config["intrinsics"], "--description", recipe / "hardware.urdf",
                           "--roi", *roi, "--face-roi", *face_roi,
                           "--output", registration, *options)
    try:
        logged_command(command, out / f"oak-registration{suffix}.log", 120)
    except RuntimeError as error:
        result = registration / "registration.json"
        if result.is_file():
            report = load_json(result)
            reason = report.get("error")
            if report.get("success") is False and reason in (
                "Fewer than two valid supported image-pose hypotheses",
                "Supported image hypotheses disagree",
            ):
                raise CartonFitRejected(f"OAK4 registration failed. {reason}") from error
            if reason:
                raise ValueError(f"OAK4 registration failed. {reason}") from error
        raise
    pose = registration / "object-pose.json"
    if not pose.is_file():
        raise ValueError(f"OAK4 registration did not write {pose.relative_to(out)}.")
    return pose


def register_current_carton(config, progress, recipe, image, metadata, *, window_cache=None):
    out = progress.output
    progress.update("oak_registration", "Locating the carton in the current OAK4 image on ROSmini.")
    default_windows = config["roi"], config["face_roi"]
    if window_cache is None or not config.get("camera_session"):
        return register_attempt(config, out, recipe, image, metadata, default_windows)

    calibration_sha = hashlib.sha256((out / "camera-session.json").read_bytes()).hexdigest()
    preview = signature = None
    if window_cache.is_file():
        preview = carton_hydrogen.tabletop_preview(image)
        signature = carton_hydrogen.scene_signature(preview)
        if windows := carton_hydrogen.cached_windows(window_cache, calibration_sha, signature):
            progress.update("oak_registration", "Fitting the current OAK4 image in previously successful search windows.")
            try:
                return register_attempt(config, out, recipe, image, metadata, windows, "-reused")
            except CartonFitRejected:
                progress.update("oak_registration", "Trying the standard search windows on the current OAK4 image.")

    try:
        return register_attempt(config, out, recipe, image, metadata, default_windows)
    except CartonFitRejected as primary_error:
        progress.update("oak_registration", "The standard image fit was rejected. Asking Hydrogen Low for search windows.")
        try:
            if preview is None:
                preview = carton_hydrogen.tabletop_preview(image)
                signature = carton_hydrogen.scene_signature(preview)
            windows = carton_hydrogen.suggest_windows(preview, out)
        except (ValueError, OSError) as error:
            raise ValueError(f"{primary_error} {error}") from error
        progress.update("oak_registration", "Checking the suggested windows against the current OAK4 image.")
        pose = register_attempt(config, out, recipe, image, metadata, windows, "-hydrogen")
        try:
            carton_hydrogen.save_windows(window_cache, calibration_sha, signature, windows)
        except OSError as error:
            print(f"Could not save carton search windows: {error}", flush=True)
        return pose


def prepare_local_approach(program, progress, config, observations, status, checker_prefix, *, window_cache=None):
    out = progress.output
    progress.update("oak_capture", "Capturing a current native OAK4 photo for carton registration.")
    cache_command = offline_tool("prepare_carton_recipe.py", "--program", program, "--cache-dir", RECIPE_CACHE)
    with ThreadPoolExecutor(max_workers=1) as workers:
        recipe_ready = workers.submit(logged_command, cache_command, out / "static-recipe.log", 120,
                                      separate_stdout=True)
        image, metadata = capture_oak(out, "initial", config["focus"])
        recipe = Path(json.loads(recipe_ready.result())["recipe"])

    pose = register_current_carton(config, progress, recipe, image, metadata, window_cache=window_cache)

    progress.update("offline_plan", "Planning and checking both arm paths on ROSmini.")
    plan = out / "plan"
    command = offline_tool("run_carton_cycle.py", "--plan-only", "--recipe", recipe,
                           "--observations", observations, "--object-pose", pose,
                           "--speed-percent", status["settings"]["speed_percent"], "--output", plan,
                           checker_prefix=checker_prefix)
    try:
        logged_command(command, out / "offline-plan.log", 240)
    except RuntimeError as error:
        report = plan / "workflow.json"
        if report.is_file() and (reason := load_json(report).get("error")):
            raise ValueError(f"ROSmini planning failed. {reason}") from error
        raise
    return plan, image, metadata


def transfer_approach(remote, target_workspace, plan, image, metadata, config, out, checker_prefix):
    handoff = out / "handoff"
    handoff.mkdir()
    prepared = handoff / "prepared"
    command = offline_tool("stage_carton_plan.py", "--plan", plan, "--output", prepared,
                           "--target-root", target_workspace / remote / "prepared",
                           "--target-workspace", target_workspace, checker_prefix=checker_prefix)
    logged_command(command, out / "stage-approach.log", 60)

    inputs = handoff / "input"
    inputs.mkdir()
    for file, name in ((image, "standard.png"), (metadata, "metadata.json"),
                       (config["intrinsics"], "intrinsics.json")):
        shutil.copyfile(file, inputs / name)
    sources = [prepared, inputs]
    reference_dir = handoff / "camera-reference"
    reference_dir.mkdir()
    options = []
    if config.get("camera_session"):
        shutil.copyfile(out / "camera-session.json", reference_dir / "camera-session.json")
        options.extend(["--camera-session", f"{remote}/camera-reference/camera-session.json"])
    elif reference := config.get("camera_reference_pose"):
        shutil.copyfile(reference, reference_dir / "object-pose.json")
        shutil.copyfile(reference.with_name("registration.json"), reference_dir / "registration.json")
        options.extend(["--camera-reference-pose", f"{remote}/camera-reference/object-pose.json"])
    if options:
        sources.append(reference_dir)
    command = ["/usr/bin/scp", *SSH_OPTIONS, "-r", *sources, f"{N100_HOST}:uwa-ur-runtime/{remote}/"]
    logged_command(command, out / "upload-approach.log", 100)
    return options


def request_review(progress, remote_run, stage, *args):
    command = n100(f"""source {shlex.quote(str(CELL / 'scripts/control_env.bash'))}
exec /usr/bin/python3 -u {shlex.quote(str(CELL / 'tools/run_carton_cycle.py'))} "$@"
""", "--output", remote_run, "--execute", *args)
    waiting = f"WAITING_FOR_{stage.upper()}_REVIEW "
    log_path = progress.output / f"n100-{stage}.log"
    with log_path.open("w") as log, subprocess.Popen(
        command, cwd=WORKSPACE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    ) as process:
        for line in process.stdout:
            log.write(line)
            log.flush()
            if line.startswith(waiting):
                progress.update(f"{stage}_review", f"Review and approve this {stage} in UWA Robot Power.")
        code = process.wait()
    if code == 255:
        raise RuntimeError("N100 connection was interrupted. Check Motion review and Safety log for the run state.")
    report_command = n100('exec cat -- "$1"\n', f"{remote_run}/workflow.json")
    report = json.loads(logged_command(report_command, progress.output / f"n100-{stage}-workflow.json", 20))
    if code:
        raise RuntimeError(report.get("error") or report.get("last_image_error") or f"N100 {stage} failed. See {log_path.name}.")
    return report


def run_live(program, progress, config_path):
    out = progress.output
    progress.update("live_preflight", "Checking the configured optics, N100 runtime and work-area release.")
    config = live_inputs(config_path)
    window_cache = None
    if config_path.with_name("carton-hydrogen.enabled").is_file():
        window_cache = config_path.with_name("carton-hydrogen-windows.json")
    session = None
    if session_path := config.get("camera_session"):
        if not session_path.is_file():
            raise ValueError("Calibrate the OAK4 before starting the carton program.")
        session = validate_session(load_json(session_path), config["intrinsics"])
        write_session(out / "camera-session.json", session)
    target_workspace, status, checker_prefix = n100_preflight(out, program)
    remote = f"setup/tasks/skill-library-carton-{uuid.uuid4().hex}"
    (out / "n100-run.txt").write_text(remote + "\n")
    observations = observe_start(remote, out, status["session_id"], progress)
    plan, image, metadata = prepare_local_approach(
        program, progress, config, observations, status, checker_prefix, window_cache=window_cache,
    )
    progress.update("n100_approach", "Sending the checked trajectories to the N100 for motion review.")
    options = transfer_approach(remote, target_workspace, plan, image, metadata, config, out, checker_prefix)

    cycle = f"{remote}/cycle"
    report = request_review(progress, cycle, "motion", "--prepared-approach", target_workspace / remote / "prepared",
                            "--expected-scene-session", status["session_id"],
                            "--expected-observations", f"{remote}/observed/observations.json",
                            "--image", f"{remote}/input/standard.png",
                            "--metadata", f"{remote}/input/metadata.json",
                            "--intrinsics", f"{remote}/input/intrinsics.json", *options)
    if report.get("phase") != "WAITING_VISUAL_REVIEW":
        raise ValueError("The N100 did not confirm the completed open entry for this run.")

    progress.update("oak_entry_capture", "Capturing the actual open entry for the operator's contact review.")
    image, metadata = capture_oak(out, "entry", config["focus"])
    upload(f"{remote}/entry/standard.png", image, out / "upload-entry-image.log")
    upload(f"{remote}/entry/metadata.json", metadata, out / "upload-entry-metadata.log")
    progress.update("n100_contact", "Sending the current open-entry image to UWA Robot Power.")
    report = request_review(progress, cycle, "contact", "--close-after-review",
                            "--entry-image", f"{remote}/entry/standard.png",
                            "--entry-metadata", f"{remote}/entry/metadata.json")
    if report.get("phase") != "SUPPORTED_CONTACT_HELD" or report.get("success") is not True:
        raise ValueError("The N100 did not confirm the supported contact hold.")
    return {
        "remote_run": cycle,
        "contact": "N100 confirmed supported contact hold after operator review.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("demo", "live", "calibrate"), required=True)
    parser.add_argument("--program", choices=(PROGRAM,), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-config", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    marker = output / ".program-run"
    with marker.open("x"):
        pass
    progress = Progress(output)
    progress.update("setup", "Starting the selected carton program.")
    try:
        if args.mode == "demo":
            result = run_demo(args.program, progress)
            message = "Recorded carton pose, checked approach and wrist diagnostic completed."
        elif args.mode == "calibrate":
            result = calibrate_camera(progress, args.live_config)
            message = "Right table camera reference saved for 12 hours."
        else:
            result = run_live(args.program, progress, args.live_config)
            message = "Supported carton contact is held."
    except (ValueError, KeyError, OSError, RuntimeError, TypeError, KeyboardInterrupt) as error:
        message = str(error) or "Program interrupted."
        progress.update("failed", message, error=message)
        return 1
    progress.update("done", message, result=result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

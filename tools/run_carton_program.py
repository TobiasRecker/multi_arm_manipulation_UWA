#!/usr/bin/env python3
"""Run the carton library program on recorded inputs or through N100 review."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import sys
import uuid

import carton_hydrogen
from carton_camera_session import create_session, measure_fixed_reference, validate_session, write_session

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
CELL = REPO.relative_to(WORKSPACE)
PROGRAM = "carton-supported-v1"
CAMERA_PROGRAM = "oak4-camera-calibration-v1"
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
        'export PYTHONPATH="$3/uwa_cell_motion:${PYTHONPATH:-}"; '
        'shift 3; export ROS_DOMAIN_ID=74 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST '
        'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1; exec "$@"',
        "uwa-carton-program", environment, checker_prefix or "", REPO, *args,
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


def live_inputs(path, *, camera_id="oak4"):
    if path is None:
        raise ValueError("Live mode requires an explicit, locally enabled camera configuration.")
    config = load_json(path)
    if not isinstance(config, dict) or config.get("enabled") is not True:
        raise ValueError("Live mode is disabled in the local configuration.")
    fields = {"enabled", "intrinsics", "roi", "face_roi", "camera_reference_pose", "camera_session", "planar_texture"}
    if camera_id == "oak4":
        fields.add("secondary_camera")
    else:
        fields.add("gemini_enabled")
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
    size = [8000, 6000] if camera_id == "oak4" else [4056, 3040]
    device = "1479883285" if camera_id == "oak4" else "18443010314F3B1300"
    if intrinsics.get("image_size") != size or intrinsics.get("device_id") != device:
        raise ValueError(f"Live {camera_id} optics must match its physical device and native {size} image.")
    if not all(name in intrinsics for name in ("K", "D")):
        raise ValueError("Live OAK intrinsics need K and D calibration data.")
    for key in ("roi", "face_roi"):
        roi = config.get(key)
        if (not isinstance(roi, list) or len(roi) != 4 or any(type(value) is not int for value in roi)
                or not (0 <= roi[0] < roi[2] <= size[0] and 0 <= roi[1] < roi[3] <= size[1])):
            raise ValueError(f"Live config {key} needs a valid crop [x0, y0, x1, y1] in native pixels.")
    reference = config.get("camera_reference_pose")
    if reference and not reference.with_name("registration.json").is_file():
        raise ValueError("Camera reference needs its original sibling registration.json.")
    config["focus"] = intrinsics["focus"]
    if camera_id == "oak_usb":
        if not config.get("camera_session") or config.get("camera_reference_pose"):
            raise ValueError("OAK Pro requires its own time-limited camera session.")
        if not isinstance(config.get("gemini_enabled", False), bool):
            raise ValueError("gemini_enabled must be true or false.")
        config["hydrogen_geometry"] = dict(native_size=size, image_window=(0, 0, *size),
                                            window_sizes=((1800, 1600), (1800, 1400)))
    if "secondary_camera" in config:
        secondary = config["secondary_camera"]
        if not isinstance(secondary, str) or not secondary.strip():
            raise ValueError("secondary_camera must name a separate USB-OAK config file.")
        config["secondary_camera"] = live_inputs((path.parent / secondary).resolve(), camera_id="oak_usb")
    return config


def selected_runtime():
    backend = os.environ.get('UWA_PROTECTION_BACKEND', 'legacy')
    if backend not in ('legacy','minimal'):
        raise ValueError('Unknown protection backend')
    candidate = os.environ.get('UWA_MINIMAL_RUNTIME', '')
    if backend == 'minimal' and candidate:
        if not PurePosixPath(candidate).is_absolute():
            raise ValueError('UWA_MINIMAL_RUNTIME must be an absolute N100 runtime path')
        return Path(os.path.normpath(candidate))
    return None


def remote_location(relative):
    payload = PurePosixPath(str(relative))
    if payload.is_absolute() or '..' in payload.parts or not payload.parts:
        raise ValueError('Remote payload must be a nonempty relative path without traversal')
    suffix = payload.as_posix() + ('/' if str(relative).endswith('/') else '')
    return f'{N100_HOST}:{selected_runtime() or "uwa-ur-runtime"}/{suffix}'


def n100(script, *args):
    candidate = selected_runtime()
    backend = os.environ.get('UWA_PROTECTION_BACKEND', 'legacy')
    prefix = N100_WORKSPACE
    if backend == 'minimal':
        if candidate:
            prefix += 'cd -- '+shlex.quote(str(candidate))+'\n'
        prefix += 'export UWA_PROTECTION_BACKEND=minimal\n'
        prefix += 'export UWA_MINIMAL_RUNTIME="$PWD"\n'
        prefix += 'export UWA_MINIMAL_INSTALL="$PWD/install_lyrical"\n'
    command = shlex.join(["/bin/bash", "-c", prefix + script, "uwa-carton-program",
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
    expected_runtime = selected_runtime()
    if (not target_workspace.is_absolute() or
            (target_workspace != expected_runtime if expected_runtime is not None
             else target_workspace.name != "uwa-ur-runtime")):
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


def carton_camera(out, focus):
    import yaml
    live = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'uwa-oak4-live.service'],
                          capture_output=True, timeout=5)
    if live.returncode == 0:
        raise RuntimeError("OAK4 live view is active. Close it before starting the carton photo session.")
    # The library runner uses system Python without sourcing a ROS overlay.
    sys.path.insert(0, str(REPO / "uwa_cell_control"))
    try:
        from uwa_cell_control.oak4_capture_session import Oak4CaptureSession
    finally:
        sys.path.pop(0)
    inventory = yaml.safe_load((REPO / "config/hardware_inventory.yaml").read_text())
    return Oak4CaptureSession(WORKSPACE, inventory["cameras"]["oak4"], out / "oak4-stream",
                              focus, preview=False)


def capture_oak(out, name, camera):
    directory = out / f"{name}-photo"
    directory.mkdir()
    image, report = camera.capture(directory)
    metadata = directory / "metadata.json"
    if (report.get("mode") != "standard" or report.get("success") is not True
            or report["standard"]["lens_position"] != camera.focus or image != directory / "standard.png"
            or not image.is_file()):
        raise ValueError("Expected a fresh native fixed-focus OAK4 Standard image.")
    write_session(metadata, report)
    return image, metadata


def capture_usb(out, name, config):
    """Reuse the existing N100 camera-only transport and keep its raw evidence."""
    sys.path.insert(0, str(REPO / "uwa_cell_control"))
    try:
        from uwa_cell_control.n100_usb_camera import N100UsbCamera
    finally:
        sys.path.pop(0)
    directory = out / f"{name}-photo"
    directory.mkdir()
    started = datetime.now(timezone.utc).isoformat()
    image, raw = N100UsbCamera(WORKSPACE, directory / "transport", config["focus"]).capture(directory)
    # The transport checks device, native dimensions, focus, closure and lease.
    # started_at is a conservative request bound, not a hardware clock timestamp.
    standard = dict(raw["photo"], path="standard.png", width=4056, height=3040)
    report = dict(success=True, mode="standard", source="fixed_focus_single_capture",
                  camera_kind="oak_usb", device_id=raw["device_id"], standard=standard,
                  started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
                  timestamp_basis="ROSmini request/completion bounds; raw N100 acquisition evidence retained",
                  raw_metadata="native/metadata.json")
    target = directory / "standard.png"
    shutil.copyfile(image, target)
    write_session(directory / "metadata.json", report)
    return target, directory / "metadata.json"


def calibrate_secondary(progress, config):
    path = config["camera_session"]
    path.unlink(missing_ok=True)
    folder = progress.output / "oak-usb"
    folder.mkdir()
    requested = datetime.now(timezone.utc)
    progress.update("usb_calibration", "Capturing the OAK Pro right-board reference at its calibrated focus.")
    image, _ = capture_usb(folder, "reference", config)
    measured = measure_fixed_reference(image.parent, config["intrinsics"], WORKSPACE, folder)
    if measured is None:
        raise ValueError("The OAK Pro right-board reference could not be measured at focus 112.")
    session = create_session(measured, config["intrinsics"], requested_at=requested)
    write_session(folder / "camera-session.json", session)
    write_session(path, session)
    return dict(valid_from=session["valid_from"], valid_until=session["valid_until"],
                markers=session["right_marker_count"], held_out_rms_px=session["held_out_rms_px"])


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
    raw = logged_command(["/bin/bash", photo_tool, "capture", "--mode", "standard", "--focus", config["focus"]],
                         progress.output / "fixed-right-capture.log", 65)
    source = Path(json.loads(raw)["directory"]).resolve(strict=True)
    directory = measure_fixed_reference(source, config["intrinsics"], WORKSPACE, progress.output)
    if directory is None:
        progress.update("oak_calibration", "Fixed-focus right-board fit was insufficient. Searching focus and exposure.")
        raw = logged_command(["/bin/bash", photo_tool, "capture", "--mode", "charuco"],
                             progress.output / "charuco-capture.log", 320)
        result = json.loads(raw)
        directory = Path(result["directory"]).resolve(strict=True)
        if result.get("mode") != "charuco" or Path(result["metadata"]).resolve() != directory / "metadata.json":
            raise ValueError("Expected a native ChArUco capture and its metadata.")
    progress.update("camera_reference", "Determining the camera pose from the right table board and matching optics.")
    session = create_session(directory, config["intrinsics"], requested_at=requested)
    write_session(progress.output / "camera-session.json", session)
    import cv2
    image = cv2.imread(str(directory / 'right/pose/standard.png'))
    if image is None:
        raise ValueError('The saved camera calibration image cannot be decoded.')
    preview = cv2.resize(image, (1280, 960))
    cv2.rectangle(preview, (0, 0), (1280, 52), (255, 255, 255), -1)
    cv2.putText(preview, f"Right board: {session['right_marker_count']} markers | "
                f"check RMS {session['held_out_rms_px']:.2f}px", (15, 34),
                cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 2)
    if not cv2.imwrite(str(progress.output / 'camera-preview.jpg'), preview):
        raise ValueError('Could not save the camera calibration preview.')
    progress.update("camera_publish", "Publishing the checked camera reference for 12 hours from capture.")
    write_session(session_path, session)
    result = {"calibration": f"Right table · {session['right_marker_count']} markers · "
            f"{session['held_out_rms_px']:.2f} px held-out RMS", "valid_until": session["valid_until"],
            "valid_from": session["valid_from"], "artifacts": {"camera_preview": "camera-preview.jpg"}}
    if secondary := config.get("secondary_camera"):
        try:
            result["secondary_camera"] = calibrate_secondary(progress, secondary)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            result["secondary_camera"] = dict(available=False, reason=str(error))
            progress.update("usb_calibration_unavailable", f"OAK4 reference saved; OAK Pro unavailable: {error}")
    return result


def upload(remote, local_file, log_path, *additional_files):
    command = [
        "/usr/bin/scp", *SSH_OPTIONS, local_file, *additional_files,
        remote_location(remote),
    ]
    logged_command(command, log_path, 100)


def observe_start(remote, out, scene, progress):
    command = n100("""mkdir -p -- "$(dirname -- "$1")"
mkdir -- "$1"
mkdir -- "$1/entry"
source "$2/scripts/control_env.bash"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 "$2/tools/start_carton_browser_programs.py" --output "$1" \
  --config "$3" --scene-session "$4"
""", remote, CELL, LIVE_PROFILE, scene)
    minimal = os.environ.get('UWA_PROTECTION_BACKEND') == 'minimal'
    progress.update("snapshot", "Checking External Control on the two carton arms." if minimal else
                    "Preparing holds on the four idle arms and checking External Control on the two carton arms.")
    logged_command(command, out / "n100-browser-play.log", 75)
    progress.update("snapshot", "Reading the shared four-arm joint snapshot for planning." if minimal else
                    "Reading the four arms and grippers for planning.")
    command = n100("""source "$2/scripts/control_env.bash"
/usr/bin/python3 "$2/tools/prepare_carton_hardware.py" --observe \
  --stationarity-config "$3" --output "$1/observed" > "$1/observe.log"
exec cat -- "$1/observed/observations.json"
""", remote, CELL, LIVE_PROFILE)
    observations = out / "observations.json"
    observations.write_text(logged_command(command, out / "n100-snapshot.log", 25, separate_stdout=True))
    logged_command(offline_tool("prepare_carton_hardware.py", "--validate-planning-snapshot", observations),
                   out / "check-snapshot.log", 20)
    # Generic offline planning accepts a stopped program. This live snapshot
    # follows the explicit Play step and must describe the two arms that will run.
    observation = load_json(observations)
    if observation.get('protection_backend') == 'minimal':
        return observations
    states = observation["arms"]
    for arm in ("right_front", "right_rear"):
        runtime = states[arm]["samples"][-1]["runtime_state"]
        if runtime != 2:
            state = "STOPPED" if runtime == 1 else f"runtime_state={runtime}"
            raise RuntimeError(f"{arm}: ros.urp reported {state} after External Control setup. "
                               "Carton setup stopped before the photo and motion. Check UWA Robot Power → Safety log.")
    return observations


class CartonFitRejected(ValueError):
    """The camera inputs were valid, but the current carton fit was rejected."""

    def __init__(self, message, registration):
        super().__init__(message)
        self.registration = registration


def register_attempt(config, out, recipe, image, metadata, windows, suffix="", *, feedback=False, quad=None):
    options = []
    if config.get("camera_session"):
        options.extend(["--camera-session", config.get("session_copy", out / "camera-session.json")])
    elif reference := config.get("camera_reference_pose"):
        options.extend(["--camera-reference-pose", reference])
    if config.get("planar_texture"):
        options.append("--planar-texture")
    if feedback:
        options.extend(["--feedback-viewport", *config.get("hydrogen_geometry", {}).get("image_window", carton_hydrogen.IMAGE_WINDOW)])
    if quad is not None:
        options.extend(["--front-quad", *quad])

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
                raise CartonFitRejected(f"OAK4 registration failed. {reason}", registration) from error
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
    geometry = config.get("hydrogen_geometry")
    if geometry:
        # USB has separate optics, image orientation and search coordinates. No OAK4 window cache.
        try:
            return register_attempt(config, out, recipe, image, metadata, default_windows, feedback=True)
        except CartonFitRejected as rejected:
            if not config.get("gemini_enabled", False):
                raise
            def measure(number, windows, quad):
                try:
                    pose = register_attempt(config, out, recipe, image, metadata, windows,
                                            f"-hydrogen-{number}", feedback=True, quad=quad)
                    return pose, pose.parent
                except CartonFitRejected as error:
                    return None, error.registration
            preview = carton_hydrogen.tabletop_preview(image, native_size=geometry['native_size'],
                                                       image_window=geometry['image_window'])
            try:
                return carton_hydrogen.guide_measurements(preview, out, rejected.registration, measure,
                                                          geometry=geometry)[0]
            except ValueError as error:
                raise CartonFitRejected(str(error), rejected.registration) from error
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
        return register_attempt(config, out, recipe, image, metadata, default_windows, feedback=True)
    except CartonFitRejected as primary_error:
        progress.update("oak_registration", "The standard carton fit was rejected. Asking Hydrogen to locate the carton or its front wall.")

        def measure(number, windows, quad):
            progress.update("oak_registration", f"Measuring the current photo with Hydrogen guidance (pass {number}).")
            suffix = "-hydrogen" if number == 1 else f"-hydrogen-{number}"
            try:
                pose = register_attempt(config, out, recipe, image, metadata, windows, suffix,
                                        feedback=True, quad=quad)
            except CartonFitRejected as rejected:
                progress.update("oak_registration", "Sending Hydrogen the rejected fit and its overlay for targeted refinement.")
                return None, rejected.registration
            return pose, pose.parent

        try:
            if preview is None:
                preview = carton_hydrogen.tabletop_preview(image)
                signature = carton_hydrogen.scene_signature(preview)
            pose, windows, quad = carton_hydrogen.guide_measurements(preview, out, primary_error.registration, measure)
        except (ValueError, OSError) as error:
            raise CartonFitRejected(f"{primary_error} {error}", primary_error.registration) from error
        try:
            if quad is None:
                carton_hydrogen.save_windows(window_cache, calibration_sha, signature, windows)
        except OSError as error:
            print(f"Could not save carton search windows: {error}", flush=True)
        return pose


def refine_cross_view(config, progress, recipe, views):
    """Remeasure current native pixels; never waive the camera disagreement."""
    import carton_multiview as multi
    if not config['secondary_camera'].get('gemini_enabled') or not all(
            views.get(name, {}).get('pose') for name in ('oak4', 'oak_usb')):
        return
    dimensions = load_json(REPO/'uwa_cell_description/assets/carton_avocado_v1/asset.json')['dimensions_m']
    primary, other = [load_json(Path(views[name]['pose']))['T_world_object_candidate']
                      for name in ('oak4', 'oak_usb')]
    try:
        multi.select_pose([primary, other], dimensions=dimensions)
        return
    except multi.PoseDisagreement as error:
        initial_error = str(error)
    out = progress.output/'multiview-refinement'
    out.mkdir()
    comparisons = []
    view = views['oak4']

    def feedback(source, name, reason):
        target = out/name
        target.mkdir()
        report = load_json(source/'registration.json')
        report['error'] = ('Single-camera fit passed; cross-view comparison after 180-degree '
                           'symmetry alignment failed. Remeasure the visible printed wall, '
                           'without inventing a pose or changing thresholds: ' + reason)
        write_session(target/'registration.json', report)
        if (source/'fit-feedback.jpg').exists():
            shutil.copyfile(source/'fit-feedback.jpg', target/'fit-feedback.jpg')
        return target

    initial = feedback(Path(view['pose']).parent, 'initial-feedback', initial_error)
    fit_config = dict(config, session_copy=Path(view['session'])) if view.get('session') else config

    def measure(number, windows, quad):
        progress.update('multiview_refinement', f'Remeasuring the current OAK4 printed wall (pass {number}).')
        try:
            pose = register_attempt(fit_config, out, recipe, Path(view['image']), Path(view['metadata']),
                                    windows, f'-cross-view-{number}', feedback=True, quad=quad)
        except CartonFitRejected as error:
            return None, error.registration
        candidate = load_json(pose)['T_world_object_candidate']
        try:
            _, decision = multi.select_pose([candidate, other], dimensions=dimensions)
        except multi.PoseDisagreement as error:
            comparisons.append(dict(round=number, accepted=False, **error.comparison))
            return None, feedback(pose.parent, f'comparison-feedback-{number}', str(error))
        comparisons.append(dict(round=number, accepted=True, **decision))
        return pose, pose.parent

    try:
        result = carton_hydrogen.guide_measurements(
            carton_hydrogen.tabletop_preview(Path(view['image'])), out, initial, measure)
    except (ValueError, RuntimeError, OSError) as error:
        write_session(out/'result.json', dict(success=False, error=str(error), comparisons=comparisons))
        return  # Preserve original measurements; the normal comparison still rejects them.
    previous = view['pose']
    view['pose'] = str(result[0])
    write_session(out/'result.json', dict(success=True, original_pose=previous,
                                        pose=view['pose'], comparisons=comparisons))


def register_multiview(config, progress, recipe, image, metadata, *, window_cache=None):
    out = progress.output
    secondary = config["secondary_camera"]
    views = {"oak4": dict(image=str(image), metadata=str(metadata), intrinsics=str(config['intrinsics']))}
    if config.get('camera_session'):
        views['oak4']['session'] = str(out/'camera-session.json')
    usb_out = out/'oak-usb'
    usb_out.mkdir()
    usb_image = usb_metadata = None
    try:
        session = validate_session(load_json(secondary['camera_session']), secondary['intrinsics'])
        write_session(usb_out/'camera-session.json', session)
        secondary = dict(secondary, session_copy=usb_out/'camera-session.json')
        progress.update('usb_capture', 'Capturing a current native OAK Pro view of the stationary carton.')
        usb_image, usb_metadata = capture_usb(usb_out, 'initial', secondary)
        views['oak_usb'] = dict(image=str(usb_image), metadata=str(usb_metadata),
                                intrinsics=str(secondary['intrinsics']), session=str(secondary['session_copy']))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        views['oak_usb'] = dict(unavailable=str(error))
        progress.update('usb_unavailable', f'OAK Pro unavailable; retaining the existing strict OAK4 fit: {error}')
    for name, view_config, view_progress, photo, meta, cache in (
        ('oak4', config, progress, image, metadata, window_cache),
        ('oak_usb', secondary, Progress(usb_out), usb_image, usb_metadata, None),
    ):
        if photo is None:
            continue
        progress.update('multiview_registration', f'Measuring the carton independently in {name}.')
        try:
            views[name]['pose'] = str(register_current_carton(view_config, view_progress, recipe, photo, meta,
                                                             window_cache=cache))
        except CartonFitRejected as error:
            views[name]['fit_rejected'] = str(error)
    refine_cross_view(config, progress, recipe, views)
    manifest = out/'multiview-input.json'
    write_session(manifest, dict(description=str(recipe/'hardware.urdf'), views=views,
                                 gemini_enabled=secondary.get('gemini_enabled', False)))
    progress.update('multiview_decision', 'Comparing accepted poses, or checking the projected carton in the weaker view.')
    result = json.loads(logged_command(offline_tool('carton_multiview.py', '--manifest', manifest,
        '--output', out/'multiview'), out/'multiview.log', 90, separate_stdout=True))
    progress.update('multiview_decision', f"Carton pose: {result['mode']} · metric source: {result['primary_camera']}.")
    return Path(result['pose'])


def prepare_local_approach(program, progress, config, observations, status, checker_prefix, camera, *, window_cache=None):
    out = progress.output
    progress.update("oak_capture", "Capturing a current native OAK4 photo for carton registration.")
    cache_command = offline_tool("prepare_carton_recipe.py", "--program", program, "--cache-dir", RECIPE_CACHE)
    with ThreadPoolExecutor(max_workers=1) as workers:
        recipe_ready = workers.submit(logged_command, cache_command, out / "static-recipe.log", 120,
                                      separate_stdout=True)
        image, metadata = capture_oak(out, "initial", camera)
        recipe = Path(json.loads(recipe_ready.result())["recipe"])

    if config.get("secondary_camera"):
        pose = register_multiview(config, progress, recipe, image, metadata, window_cache=window_cache)
    else:
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
    destination = remote_location(remote+'/')
    handoff = out / "handoff"
    handoff.mkdir()
    prepared = handoff / "prepared"
    resources = []
    if os.environ.get('UWA_PROTECTION_BACKEND') == 'minimal':
        query = ("import json; from pathlib import Path; from ament_index_python.packages import get_package_share_directory; "
                 "p=Path(get_package_share_directory('uwa_cell_description')); "
                 "print(json.dumps(dict(share=str(p),source=str((p/'meshes/collision/2f_85/robotiq_base.stl').resolve(strict=True).parents[3]))))")
        locations = json.loads(logged_command(n100('source "$1/scripts/control_env.bash"\npython3 -c "$2"\n', CELL, query),
                                             out/'n100-description-share.log', 20, separate_stdout=True))
        for kind in ('share', 'source'):
            path = Path(locations[kind])
            if not path.is_absolute() or '..' in path.parts:
                raise ValueError('N100 description package returned an invalid path')
            resources.extend(['--description-'+kind, path])
    command = offline_tool("stage_carton_plan.py", "--plan", plan, "--output", prepared,
                           "--target-root", target_workspace / remote / "prepared",
                           "--target-workspace", target_workspace, *resources, checker_prefix=checker_prefix)
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
    command = ["/usr/bin/scp", *SSH_OPTIONS, "-r", *sources, destination]
    logged_command(command, out / "upload-approach.log", 100)
    return options


def request_review(progress, remote_run, stage, *args):
    command = n100(f"""source {shlex.quote(str(CELL / 'scripts/control_env.bash'))}
# Avoid competing with the controller-manager and guard callbacks on the N100.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
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
            elif line.startswith(f"REVIEW_ACCEPTED_{stage.upper()} "):
                progress.update(f"n100_{stage}", f"Review accepted. Executing the {stage} step on the N100.")
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
    camera = carton_camera(out, config["focus"])
    try:
        camera.start()
        observations = observe_start(remote, out, status["session_id"], progress)
        plan, image, metadata = prepare_local_approach(
            program, progress, config, observations, status, checker_prefix, camera, window_cache=window_cache,
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
        image, metadata = capture_oak(out, "entry", camera)
    finally:
        camera.stop()
    upload(f"{remote}/entry/", image, out / "upload-entry.log", metadata)
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
    parser.add_argument("--program", choices=(PROGRAM, CAMERA_PROGRAM), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-config", type=Path)
    args = parser.parse_args()
    if args.program == CAMERA_PROGRAM and args.mode != "calibrate":
        parser.error("The OAK4 camera calibration program uses --mode calibrate.")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    marker = output / ".program-run"
    with marker.open("x"):
        pass
    progress = Progress(output)
    progress.update("setup", "Starting OAK4 camera calibration." if args.program == CAMERA_PROGRAM
                    else "Starting the selected carton program.")
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

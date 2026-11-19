#!/usr/bin/env python3
"""Run the carton library program on recorded inputs or through N100 review."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
CELL = REPO.relative_to(WORKSPACE)
PROGRAM = "carton-supported-v1"
INTRINSICS = Path("setup/calibration/oak_capture_proposal_20261118/calibration_candidate_v1/oak_pose_candidate.json")
TEXTURE_MODEL = Path("setup/tracking/models/carton_avocado_v1/reference.npz")
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


def logged_command(command, log_path, timeout):
    with log_path.open("w+") as log:
        try:
            completed = subprocess.run([str(arg) for arg in command], cwd=WORKSPACE,
                                       stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"{log_path.stem} timed out after {timeout} s. See {log_path.name}.") from error
        log.seek(0)
        output = log.read()
    if completed.returncode:
        lines = output.strip().splitlines()
        reason = lines[-1] if lines and lines[-1] not in {"{", "}"} else f"See {log_path.name}."
        raise RuntimeError(f"{log_path.stem} failed: {reason}")
    return output


def offline_tool(script, *args):
    environment = WORKSPACE / "setup/lyrical_env.bash"
    return [
        "/bin/bash", "-c",
        'source "$1" || exit $?; shift; export ROS_DOMAIN_ID=74 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; exec "$@"',
        "uwa-carton-program", environment, sys.executable, REPO / "tools" / script, *args,
    ]


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
    fields = {"enabled", "intrinsics", "roi", "face_roi", "camera_reference_pose", "planar_texture"}
    if set(config) - fields:
        raise ValueError("Live config contains unknown fields.")
    if not isinstance(config.get("planar_texture", False), bool):
        raise ValueError("planar_texture must be true or false.")
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
        CELL / "tools/prepare_carton_recipe.py",
        CELL / "tools/register_carton_from_oak.py",
        CELL / "config/carton_programs" / f"{program}.json",
        CELL / "uwa_cell_motion/config/hardware_carton_supported_trend.yaml",
        TEXTURE_MODEL,
    ]
    arguments = []
    for file in files:
        with (WORKSPACE / file).open("rb") as source:
            arguments.extend([hashlib.file_digest(source, "sha256").hexdigest(), file])
    command = n100("""test -r install_lyrical/setup.bash
while [[ $# -gt 0 ]]; do
    actual=$(sha256sum -- "$2")
    if [[ ${actual%% *} != "$1" ]]; then
        printf 'N100 needs the matching qualified version of %s.\n' "$2" >&2
        exit 1
    fi
    shift 2
done
exec ./review.sh status
""", *arguments)
    status = json.loads(logged_command(command, out / "n100-preflight.log", 25))
    if not status.get("area_released"):
        raise ValueError("Release the physical work area in UWA Robot Power before starting the live program.")
    if any(item.get("status") in {"pending", "approved", "running"} for item in status.get("pending", [])):
        raise ValueError("A motion review is already open. Finish it in UWA Robot Power before starting a new run.")


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


def upload(remote, local_file, log_path):
    command = [
        "/usr/bin/scp", *SSH_OPTIONS, str(local_file),
        f"{N100_HOST}:uwa-ur-runtime/{remote}",
    ]
    logged_command(command, log_path, 100)


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
    n100_preflight(out, program)
    remote = f"setup/tasks/skill-library-carton-{uuid.uuid4().hex}"
    logged_command(
        n100('mkdir -- "$1"\nmkdir -- "$1/input" "$1/entry" "$1/camera-reference"\n', remote),
        out / "n100-run-directory.log", 20,
    )
    (out / "n100-run.txt").write_text(remote + "\n")
    progress.update("oak_capture", "Capturing a current native OAK4 photo for carton registration.")
    image, metadata = capture_oak(out, "initial", config["focus"])
    upload(f"{remote}/input/standard.png", image, out / "upload-initial-image.log")
    upload(f"{remote}/input/metadata.json", metadata, out / "upload-initial-metadata.log")
    upload(f"{remote}/input/intrinsics.json", config["intrinsics"], out / "upload-intrinsics.log")
    options = []
    if reference := config.get("camera_reference_pose"):
        upload(f"{remote}/camera-reference/object-pose.json", reference, out / "upload-camera-reference.log")
        upload(f"{remote}/camera-reference/registration.json", reference.with_name("registration.json"),
               out / "upload-camera-proof.log")
        options.extend(["--camera-reference-pose", f"{remote}/camera-reference/object-pose.json"])
    if config.get("planar_texture"):
        options.append("--planar-texture")

    cycle = f"{remote}/cycle"
    progress.update("n100_approach", "Registering the carton and preparing the approach on the N100.")
    report = request_review(progress, cycle, "motion", "--program", program,
                            "--image", f"{remote}/input/standard.png",
                            "--metadata", f"{remote}/input/metadata.json",
                            "--intrinsics", f"{remote}/input/intrinsics.json",
                            "--roi", *config["roi"], "--face-roi", *config["face_roi"], *options)
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
    parser.add_argument("--mode", choices=("demo", "live"), required=True)
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

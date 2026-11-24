#!/usr/bin/env python3
"""Run the supported carton program or prepare its approach from offline inputs."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "uwa_cell_tasks"))
from uwa_cell_tasks.carton_review import contact_component, current_capture, entry_photo, motion_packet, motion_timing, read_json
from uwa_cell_tasks.motion_review import ReviewStore, START_PERCENT, TASK, caps, digest, percent


class CaptureUnavailable(ValueError):
    """An operator can supply another actual image while the entered arms hold."""


def atomic_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def arguments():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--plan-only", action="store_true",
                      help="Prepare and check both approach phases from files without connecting to the cell")
    recipe = ap.add_mutually_exclusive_group()
    recipe.add_argument("--program", help="Saved carton program name from config/carton_programs")
    recipe.add_argument("--recipe", type=Path, help="Previously generated carton geometry/contact recipe")
    recipe.add_argument("--prepared-approach", type=Path, help="Executor-local staged, checked approach")
    ap.add_argument("--observations", type=Path, help="Saved arm observations for --plan-only")
    ap.add_argument("--object-pose", type=Path, help="Saved carton pose for --plan-only")
    ap.add_argument("--speed-percent", type=float, help="Active pilot speed to compile in --plan-only")
    ap.add_argument("--expected-scene-session", help="N100 work-area session bound to a prepared approach")
    ap.add_argument("--expected-observations", type=Path,
                    help="Original N100 snapshot used in a prepared approach")
    ap.add_argument("--close-after-review", action="store_true")
    ap.add_argument("--visual-confirmed", action="store_true",
                    help="Agent inspected this actual post-entry image")
    ap.add_argument("--start-ros-programs", action="store_true",
                    help="Include explicit unloaded regular startup under verified holds in this review")
    for name in ("image", "metadata", "intrinsics", "entry-image", "entry-metadata"):
        ap.add_argument("--" + name, type=Path)
    ap.add_argument("--registration-directory", type=Path, help="Reuse a successful registration only when every bound source and current capture is unchanged")
    ap.add_argument("--path-budget-s", type=float, help="Offline path-search time per candidate; no change to execution speed")
    camera = ap.add_mutually_exclusive_group()
    camera.add_argument("--camera-reference-pose", type=Path)
    camera.add_argument("--camera-session", type=Path)
    ap.add_argument("--photo-reference", type=Path)
    ap.add_argument("--verification-image", type=Path)
    ap.add_argument("--verification-metadata", type=Path)
    ap.add_argument("--planar-texture", action="store_true", help="Use validated affine/panel feature views for foreshortened carton faces")
    for roi in ("--roi", "--face-roi"):
        ap.add_argument(roi, nargs=4, type=int)
    ap.add_argument("--risk", choices=("low", "medium", "high"),
                    help="Planning agent's assessment; omission requests operator review")
    ap.add_argument("--reason", help="Specific justification for this plan or actual contact image")
    ap.add_argument("--config", type=Path, default=REPO/"uwa_cell_motion/config/hardware_carton_supported_trend.yaml")
    args = ap.parse_args()
    if bool(args.risk) != bool(args.reason and args.reason.strip()):
        ap.error("Provide --risk and a nonempty --reason together")
    if args.speed_percent is not None and not args.plan_only:
        ap.error("--speed-percent is for --plan-only; execution uses the active pilot setting")
    if args.prepared_approach:
        if not (args.execute and args.image and args.metadata and args.intrinsics and
                args.expected_scene_session and args.expected_observations):
            ap.error("Prepared approach needs --execute, current camera inputs, --expected-scene-session and --expected-observations")
        if any((args.close_after_review, args.visual_confirmed, args.registration_directory, args.path_budget_s,
                args.photo_reference, args.verification_image, args.verification_metadata,
                args.planar_texture, args.roi, args.face_roi)):
            ap.error("A prepared approach cannot change the completed registration or path search")
    elif args.expected_scene_session or args.expected_observations:
        ap.error("Expected session and observations require --prepared-approach")
    if args.plan_only:
        if not (args.observations and args.object_pose and (args.program or args.recipe)):
            ap.error("Offline planning needs --observations, --object-pose and --program or --recipe")
        if any((args.close_after_review, args.start_ros_programs, args.visual_confirmed, args.risk,
                args.image, args.metadata, args.intrinsics, args.entry_image, args.entry_metadata,
                args.registration_directory, args.camera_reference_pose, args.camera_session, args.photo_reference,
                args.verification_image, args.verification_metadata, args.planar_texture, args.roi, args.face_roi)):
            ap.error("Live capture, review and execution options are invalid with --plan-only")
    elif args.observations or args.object_pose:
        ap.error("--observations and --object-pose require --plan-only")
    elif args.close_after_review:
        if args.camera_session or not (args.execute and args.entry_image and args.entry_metadata):
            ap.error("Contact needs --execute, --entry-image and --entry-metadata")
    elif not all((args.image, args.metadata, args.intrinsics,
                  args.program or args.recipe or args.prepared_approach)):
        ap.error("Approach needs --image, --metadata, --intrinsics and a program, recipe or prepared approach")
    elif args.program and args.registration_directory:
        ap.error("Reusing a registration requires --recipe with the original hardware.urdf path")
    elif args.registration_directory and args.camera_session:
        ap.error("A camera session requires registering the current carton image.")
    if (args.execute and not (args.prepared_approach or args.close_after_review)
            and socket.gethostname().split(".", 1)[0].casefold() == "miniminipc"):
        ap.error("N100 execution requires a checked approach prepared on ROSmini.")
    return args


def reuse_registration(source, destination, required_inputs):
    """Reuse checked perception without replaying an old object after scene changes."""
    import shutil
    source=Path(source);proof=read_json(source/"registration.json")
    pose=source/"object-pose.json";binding=read_json(pose)
    if not proof.get("success") or Path(proof["object_pose"]).resolve()!=pose.resolve():
        raise ValueError("Successful original registration required")
    inputs=binding.get("source_inputs",{})
    if not inputs:raise ValueError("Registration has no bound sources")
    for path in required_inputs:
        path=Path(path).resolve()
        if str(path) not in inputs:raise ValueError("Current input missing from reused registration: "+str(path))
    for file,sha in inputs.items():
        if digest(Path(file).read_bytes())!=sha:raise ValueError("Reused registration input changed: "+file)
    shutil.copytree(source,destination)
    return dict(source=str(source.resolve()),object_pose_sha256=digest(pose.read_bytes()),
                registration_sha256=digest((source/"registration.json").read_bytes()),
                sources_verified=len(inputs))


class Workflow:
    def __init__(self, out, report):
        self.out, self.report = out, report

    def save(self):
        self.report["updated_wall"] = datetime.now().astimezone().isoformat()
        self.report["elapsed_s"] = time.monotonic() - self.report["started_monotonic_s"]
        atomic_json(self.out / "workflow.json", self.report)

    def phase(self, name, tool, *args):
        command = [sys.executable, str(REPO / "tools" / tool), *map(str, args)]
        start = time.monotonic()
        event = dict(phase=name, started_monotonic_s=start, command=command)
        self.report["events"].append(event)
        self.report["phase"] = name
        self.save()
        with (self.out / (name + ".log")).open("w") as log:
            proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                  env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"))
        end = time.monotonic()
        event.update(duration_s=end-start, returncode=proc.returncode)
        if name in {"high", "entry"}:
            try:
                event["native_motion"] = motion_timing(self.out/name, start, end)
            except (OSError, KeyError, ValueError, TypeError) as exc:
                event["native_motion"] = dict(available=False, reason=str(exc))
            first = event["native_motion"].get("first_motion_monotonic_s")
            if first is not None:
                self.report.setdefault("time_to_first_observed_motion_s", first-self.report["started_monotonic_s"])
        self.save()
        if proc.returncode:
            log_path = self.out / (name + ".log")
            detail = ""
            if "--output" in args:
                result_path = Path(args[args.index("--output")+1]) / "result.json"
                if result_path.is_file():
                    try:
                        detail = read_json(result_path).get("error", "")
                    except ValueError:
                        pass
            if not detail:
                with log_path.open("rb") as log:
                    log.seek(max(0, os.fstat(log.fileno()).st_size-3000))
                    lines = log.read().decode(errors="replace").strip().splitlines()
                detail = next((line.strip() for line in reversed(lines)
                               if "Error" in line or "error" in line), "")
            raise RuntimeError(f"{name} failed. {detail or log_path}")

    @contextmanager
    def approval(self, store, meta, preview):
        identifier = store.submit(str(self.out) + "/" + meta["stage"], meta, preview)
        self.report[meta["stage"] + "_review"] = identifier
        self.report["phase"] = "WAITING_FOR_" + meta["stage"].upper() + "_REVIEW"
        self.save()
        start = time.monotonic()
        claimed = False
        try:
            announced = False
            while not store.claim(identifier):
                if not announced:
                    print(f'{self.report["phase"]} {identifier}', flush=True)
                    announced = True
                time.sleep(.4)
            claimed = True
            print(f'REVIEW_ACCEPTED_{meta["stage"].upper()} {identifier}', flush=True)
            active = next(r for r in store.status()["pending"] if r["id"] == identifier)
            self.report["events"].append(dict(phase=self.report["phase"], duration_s=time.monotonic()-start,
                                             decided_by=active["decided_by"], review_id=identifier))
            if active["decided_by"] == "operator":
                self.report["operator_decisions"] = self.report.get("operator_decisions", 0)+1
            self.save()
            yield identifier
        except BaseException as exc:
            if claimed:
                store.finish(identifier, False, str(exc) or "Interrupted")
            else:
                store.withdraw(identifier)
            raise
        else:
            if store.finish(identifier, True) != "done":
                raise RuntimeError("Review revoked before completion")


def resolve_recipe(flow, args):
    program_name = getattr(args, "program", None)
    if program_name:
        recipe = flow.out / "recipe"
        flow.phase("prepare_recipe", "prepare_carton_recipe.py", "--program", program_name,
                   "--config", args.config, "--output", recipe)
    else:
        recipe = args.recipe
    program_file = (recipe / "program.json").resolve()
    if not program_name and not program_file.exists():
        return recipe, .15
    raw = program_file.read_bytes()
    program = json.loads(raw)
    identifier, pregrasp = program["program_id"], program["pregrasp_m"]
    if not isinstance(identifier, str) or not identifier or pregrasp != .15:
        raise ValueError("Expected a named supported carton program with a 150 mm pregrasp separation.")
    flow.report["program"] = dict(id=identifier, path=str(program_file), sha256=digest(raw))
    return recipe, pregrasp


def task_components(directory):
    runners = [("high", "run_carton_pregrasp.py", "--evidence", directory/"high-plan"),
               ("entry", "run_carton_open_entry.py", "--plan", directory/"entry-plan/result.json")]
    return runners, [directory/"review-high.json", directory/"review-entry.json"]


def prepare_approach(flow, args, joint, tcp, recipe, observations, object_pose, pregrasp_m):
    out = flow.out
    flow.phase("plan_high", "prepare_carton_pregrasp.py", "--observations", observations,
               "--object-pose", object_pose, "--contact-design", recipe/"contacts.json",
               "--contact-scene", recipe/"scene.json", "--config", args.config, "--pregrasp-m", pregrasp_m,
               "--output", out/"high-plan",
               *(["--path-budget-s", args.path_budget_s] if getattr(args, "path_budget_s", None) else []))
    evidence = read_json(out/"high-plan/evidence.json")
    if not evidence.get("path"):
        raise ValueError("High approach has no checked path: "+str(evidence.get("status"))+"; inspect high-plan/evidence.json")
    positions = dict(evidence["saved_start"])
    positions.update(zip(evidence["path"]["joint_names"], evidence["path"]["waypoints"][-1], strict=True))
    atomic_json(out/"planned-high.json", dict(planned_only=True,segments=[dict(final_positions=positions)]))
    flow.phase("plan_entry", "prepare_carton_open_entry.py", "--evidence", out/"high-plan",
               "--approach", out/"planned-high.json", "--planned-start", "--output", out/"entry-plan")
    runners, paths = task_components(out)
    for (name, tool, source, value), bundle in zip(runners, paths, strict=True):
        flow.phase("prepare_"+name, tool, source, value, "--prepare-reviewed", bundle, "--command-velocity",
                   joint, "--tcp-speed-m-s", tcp, "--output", out/("prepared-"+name))
    return runners, paths


def plan_offline(flow, args):
    speed = START_PERCENT if args.speed_percent is None else percent(args.speed_percent)
    joint, tcp = caps(speed)
    observations, object_pose = args.observations.resolve(), args.object_pose.resolve()
    flow.report["offline_inputs"] = {
        key: dict(path=str(path), sha256=digest(path.read_bytes()))
        for key, path in (("observations", observations), ("object_pose", object_pose))
    }
    recipe, pregrasp_m = resolve_recipe(flow, args)
    _, paths = prepare_approach(flow, args, joint, tcp, recipe, observations, object_pose, pregrasp_m)
    flow.report.update(success=True, phase="OFFLINE_APPROACH_PREPARED", speed_percent=speed,
                       review_bundles=[str(path) for path in paths])


def requested_program_starts(flow, requested, stage):
    """Use the same Dashboard and reverse-connection checks as the Play executor."""
    if not requested:
        return []
    result = subprocess.run([sys.executable, str(REPO/"scripts/ur_bringup.py"), "--status", "--json"],
                            capture_output=True, text=True, timeout=30)
    if result.returncode not in (0, 1):
        raise ValueError("Could not read External Control readiness: " + (result.stderr or result.stdout)[-400:])
    data = json.loads(result.stdout)
    arms = data.get("arms", {})
    if data.get("mode") != "status" or set(arms) != {"left_front","left_rear","right_front","right_rear"}:
        raise ValueError("Incomplete four-arm External Control status")
    flow.report.setdefault("program_readiness", {})[stage] = arms
    flow.save()
    starts = []
    from uwa_cell_motion.protection_backend import minimal_enabled
    selected = ('right_front','right_rear') if minimal_enabled() else tuple(arms)
    for arm in selected:
        row = arms[arm]
        if row["code"] == "ready":
            continue
        if row["code"] == "needs_preparation" and row.get("next_step") == "play":
            starts.append(arm)
        else:
            raise ValueError(f"{arm}: External Control unavailable · {row.get('message') or row['code']}")
    return sorted(starts)


def file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def staged_approach(flow, args, status, photo):
    from uwa_cell_tasks.reviewed_carton import checker_identity

    if args.expected_scene_session != status["session_id"]:
        raise ValueError("Work area changed during planning; acquire the scene again.")
    directory = args.prepared_approach.resolve(strict=True)
    receipt_path = directory/"stage-receipt.json"
    receipt = read_json(receipt_path)
    if receipt.get("schema_version") != 1 or receipt["speed_percent"] != status["settings"]["speed_percent"]:
        raise ValueError("Staged approach schema or active speed changed; prepare a new plan.")
    joint, tcp = caps(receipt["speed_percent"])
    if not {
        "high-plan/evidence.json", "high-plan/moveit/robot.urdf", "entry-plan/result.json",
        "review-high.json", "review-entry.json", "prepared-high/preview.urdf", "prepared-entry/preview.urdf",
        "inputs/observations.json", "inputs/object-pose.json", "recipe/scene.json", "recipe/contacts.json",
        "recipe/program.json", "planned-high.json",
    } <= receipt["files"].keys():
        raise ValueError("Staged approach is missing required proof files.")
    for name, sha256 in receipt["files"].items():
        path = (directory/name).resolve(strict=True)
        if Path(name).is_absolute() or not path.is_relative_to(directory) or file_sha256(path) != sha256:
            raise ValueError(f"Staged proof file changed: {name}")
    resource_roots = [REPO.parents[1], Path('/opt/ros/lyrical')]
    from uwa_cell_motion.protection_backend import minimal_enabled
    if minimal_enabled():
        from ament_index_python.packages import get_package_share_directory
        share = Path(get_package_share_directory('uwa_cell_description'))
        resource_roots.extend([share, (share/'meshes/collision/2f_85/robotiq_base.stl').resolve(strict=True).parents[3]])
    for name, sha256 in receipt["target_resources"].items():
        path = Path(name)
        if (not path.is_absolute() or ".." in path.parts
                or not any(path.is_relative_to(root) for root in resource_roots)
                or file_sha256(path) != sha256):
            raise ValueError(f"Staged model input changed: {name}")

    evidence = read_json(directory/"high-plan/evidence.json")
    expected = {
        "observations": directory/"inputs/observations.json",
        "object_pose": directory/"inputs/object-pose.json",
        "contact_scene": directory/"recipe/scene.json",
        "contact_design": directory/"recipe/contacts.json",
    }
    for name, path in expected.items():
        source = evidence["inputs"][name]
        if Path(source["path"]).resolve() != path or source["sha256"] != receipt["files"][str(path.relative_to(directory))]:
            raise ValueError(f"Staged evidence uses an unexpected {name} input.")
    if (file_sha256(args.expected_observations) != receipt["snapshot_sha256"] or
            receipt["snapshot_sha256"] != receipt["files"]["inputs/observations.json"]):
        raise ValueError("Staged approach uses a different N100 joint snapshot.")
    if receipt["object_pose_sha256"] != receipt["files"]["inputs/object-pose.json"]:
        raise ValueError("Staged approach uses a different carton registration.")
    for name, path in (("config", args.config), ("inventory", REPO/"config/hardware_inventory.yaml")):
        source = evidence["inputs"][name]
        if Path(source["path"]).resolve() != path.resolve() or source["sha256"] != file_sha256(path):
            raise ValueError(f"The active hardware {name} changed.")

    binding = read_json(expected["object_pose"])
    source_hashes = set(binding["source_inputs"].values())
    source_paths = [
        args.image, args.metadata, args.intrinsics,
        REPO/"tools/register_carton_from_oak.py",
        REPO.parents[1]/"setup/tracking/models/carton_avocado_v1/reference.npz",
    ]
    registration_source = binding["source"]
    if args.camera_session:
        from carton_camera_session import validate_session

        validate_session(read_json(args.camera_session), args.intrinsics, photo=photo)
        source_paths.append(args.camera_session)
    elif registration_source.startswith("Session ChArUco"):
        raise ValueError("The staged plan requires its original OAK4 camera session.")
    elif registration_source.startswith("Previous complete board camera registration"):
        if not args.camera_reference_pose:
            raise ValueError("The staged plan requires its original checked camera reference.")
        source_paths.extend((args.camera_reference_pose, args.camera_reference_pose.with_name("registration.json")))
    for path in source_paths:
        if file_sha256(path) not in source_hashes:
            raise ValueError(f"Staged carton pose differs from the current registration input {path.name}.")

    runners, paths = task_components(directory)
    entry = read_json(directory/"entry-plan/result.json")
    entry_sources = {
        str(directory/name): receipt["files"][name] for name in (
            "high-plan/evidence.json", "planned-high.json", "inputs/object-pose.json", "recipe/scene.json",
        )
    }
    entry_script = REPO/"tools/prepare_carton_open_entry.py"
    entry_sources[str(entry_script)] = file_sha256(entry_script)
    if entry.get("inputs") != entry_sources:
        raise ValueError("Staged open entry uses different input evidence.")
    checker = checker_identity(REPO/"tools")
    if receipt["checker_sha256"] != checker["sha256"]:
        raise ValueError("Staged trajectory checker differs from the N100 runtime.")
    phase_sources = (directory/"high-plan/evidence.json", directory/"entry-plan/result.json")
    for (phase, *_), path, source in zip(runners, paths, phase_sources, strict=True):
        bundle = read_json(path)
        preview_relative = Path(f"prepared-{phase}/preview.urdf")
        if (bundle.get("schema_version") != 2 or bundle.get("phase") != phase
                or bundle.get("checker") != checker or bundle.get("source_sha256") != file_sha256(source)
                or bundle.get("joint_limit_rad_s") != joint or bundle.get("tcp_limit_m_s") != tcp
                or Path(bundle["preview_urdf"]).resolve() != directory/preview_relative
                or bundle["preview_urdf_sha256"] != receipt["files"][str(preview_relative)]):
            raise ValueError("Staged trajectory no longer matches its checked source, active speed or N100 runtime.")
    program = read_json(directory/"recipe/program.json")
    flow.report["program"] = dict(id=program["program_id"], path=str(directory/"recipe/program.json"),
                                  sha256=receipt["files"]["recipe/program.json"])
    flow.report["staged_approach"] = dict(path=str(directory), receipt_sha256=file_sha256(receipt_path),
                                          speed_percent=receipt["speed_percent"])
    flow.save()
    return runners, paths


def prepare_live_approach(flow, args, joint, tcp):
    out = flow.out
    recipe, pregrasp_m = resolve_recipe(flow, args)
    flow.phase("snapshot", "prepare_carton_hardware.py", "--observe", "--stationarity-config", args.config, "--output", out/"snapshot")
    if getattr(args,"registration_directory",None):
        required=[args.image,args.metadata,args.intrinsics,recipe/"hardware.urdf",REPO/"tools/register_carton_from_oak.py"]
        if getattr(args,"verification_image",None):required.extend([args.verification_image,args.verification_metadata])
        flow.report["reused_registration"]=reuse_registration(args.registration_directory,out/"registration",required)
        flow.save()
    else:
        flow.phase("registration", "register_carton_from_oak.py", "--image", args.image,
                   "--metadata", args.metadata, "--intrinsics", args.intrinsics, "--description",
                   recipe/"hardware.urdf", "--output", out/"registration",
                   *(["--camera-reference-pose", args.camera_reference_pose] if args.camera_reference_pose else []),
                   *(["--camera-session", args.camera_session] if getattr(args,"camera_session",None) else []),
                   *(["--planar-texture"] if getattr(args,"planar_texture",False) else []),
                   *(["--photo-reference", args.photo_reference] if getattr(args,"photo_reference",None) else []),
                   *(["--verification-image",args.verification_image,"--verification-metadata",args.verification_metadata]if getattr(args,"verification_image",None)else []),
                   *(["--roi", *args.roi] if args.roi else []),
                   *(["--face-roi", *args.face_roi] if args.face_roi else []))
    return prepare_approach(flow, args, joint, tcp, recipe, out/"snapshot/observations.json",
                            out/"registration/object-pose.json", pregrasp_m)


def prior_library_decision(store, step, stage, speed):
    """Find the latest matching decision, including pre-familiarity Library runs."""
    with store.connection() as db:
        rows = db.execute("""
            SELECT id, operation, meta, status, actor FROM tickets
            WHERE json_extract(meta, '$.task')=? AND json_extract(meta, '$.stage')=?
              AND json_extract(meta, '$.speed_percent')=?
              AND (status IN ('rejected','replan') OR
                   (invalid=0 AND (status='done' OR
                    (actor='operator' AND status IN ('approved','running','failed','interrupted')))))
            ORDER BY created DESC
        """, (TASK, stage, speed))
        for row in rows:
            meta = json.loads(row["meta"])
            previous_step = meta.get("library_step")
            if previous_step is None:
                cycle = Path(row["operation"]).parent
                if cycle.name != "cycle" or not cycle.parent.name.startswith("skill-library-carton-"):
                    continue
                try:
                    report = read_json(cycle / "workflow.json")
                except (OSError, ValueError):
                    continue
                if (report.get(stage + "_review") != row["id"] or not report.get("staged_approach")
                        or report.get("program", {}).get("sha256") != step["program_sha256"]):
                    continue
                groups = db.execute("""
                    SELECT json_extract(g.value,'$.phase'), json_extract(g.value,'$.arms')
                    FROM tickets, json_each(preview,'$.groups') AS g WHERE tickets.id=?
                    ORDER BY g.key
                """, (row["id"],))
                previous_step = dict(program_sha256=step["program_sha256"],
                                     groups=[[phase, json.loads(arms)] for phase, arms in groups])
            if previous_step == step:
                if row["status"] in {"rejected", "replan"}:
                    return None
                return row["id"]
    return None


def assess_library_step(flow, store, meta, preview, *, visual_confirmed=False):
    if not flow.report.get("staged_approach") or flow.report["program"]["id"] != "carton-supported-v1":
        return
    step = dict(program_sha256=flow.report["program"]["sha256"],
                groups=[[group["phase"], group["arms"]] for group in preview["groups"]])
    meta["library_step"] = step
    previous = prior_library_decision(store, step, meta["stage"], meta["speed_percent"])
    if previous:
        meta["step_uncertainty"] = "medium"
        meta["prior_review"] = previous
        reason = "This program step was previously approved or completed."
        if meta["stage"] == "contact" and not visual_confirmed:
            reason += " Step uncertainty is medium. Inspect the current open-entry image before closing."
        else:
            meta["risk"] = "medium"
            reason += " Familiarity lowers the assessment from high to medium."
        # Preserve coordination details from the motion planner.
        meta["reason"] = "\n".join([reason, *meta["reason"].splitlines()[1:]])


def approach(flow, args, store):
    out = flow.out
    status = store.status()
    if not status["area_released"] or not status.get("area_released_at"):
        raise ValueError("Release the physical work area in UWA Robot Power before acquiring the scene")
    _, _, photo = current_capture(args.image, args.metadata, status["area_released_at"], time.time())
    if getattr(args,"verification_image",None):current_capture(args.verification_image,args.verification_metadata,status["area_released_at"],time.time())
    flow.report["scene_session"] = status["session_id"]
    speed = status["settings"]["speed_percent"]
    joint, tcp = caps(speed)
    if getattr(args, "prepared_approach", None):
        runners, paths = staged_approach(flow, args, status, photo)
    else:
        runners, paths = prepare_live_approach(flow, args, joint, tcp)
    asset = read_json(REPO/"uwa_cell_description/assets/carton_avocado_v1/asset.json")
    starts = requested_program_starts(flow, args.start_ros_programs, "motion")
    meta, preview = motion_packet(paths, asset["dimensions_m"], speed, args.risk or "high",
                                  args.reason or "Operator review requested for this approach.",
                                  bool(starts))
    meta["program_start_arms"] = starts
    meta["scene_session"] = status["session_id"]
    preparation = REPO / "tools/carton_gripper_phase.py"
    meta["gripper_preparation"] = dict(
        after="high", before="entry", arms=["right_front", "right_rear"],
        operations=["activate_if_inactive", "open"], force_raw=0, speed_raw=16,
        source_sha256=file_sha256(preparation))
    meta["reason"] += "\nAt the confirmed held high pose, activate and fully open both carton grippers (raw force 0, speed 16) before entry."
    if not args.risk:
        assess_library_step(flow, store, meta, preview)
    with flow.approval(store, meta, preview) as identifier:
        for (name, tool, source, value), bundle, sha in zip(runners, paths, meta["components"], strict=True):
            store.check_active(identifier, sha)
            if name == "entry":
                if file_sha256(preparation) != meta["gripper_preparation"]["source_sha256"]:
                    raise ValueError("Gripper preparation source changed since review")
                flow.phase("prepare_grippers", "carton_gripper_phase.py", "prepare",
                           "--state", out/"high/result.json", "--execute",
                           "--output", out/"prepare-grippers")
                prepared = read_json(out/"prepare-grippers/result.json")
                if not prepared.get("success") or prepared.get("phase") != "ACTIVE_OPEN_HELD":
                    raise ValueError("Active open grippers unconfirmed at high pose; no entry")
            # The entry client reads each active/open gripper and the four holds
            # immediately before releasing the group. A separate read-only process
            # here would check the same earlier state and rebuild the ROS graph.
            flow.phase(name, tool, source, value, "--reviewed", bundle, "--reviewed-sha256", sha,
                       "--review-id", identifier, "--execute", "--reset-unloaded", "--command-velocity", joint,
                       "--tcp-speed-m-s", tcp, "--output", out/name,
                       *(["--start-ros-programs"] if starts and name == "high" else []))
    flow.report.update(phase="WAITING_VISUAL_REVIEW", entry_finished_unix=time.time(),
                       entry_state_sha256=digest((out/"entry/result.json").read_bytes()))


def close_after_entry(flow, args, store):
    out = flow.out
    state_path = out/"entry/result.json"
    state_sha = digest(state_path.read_bytes())
    if state_sha != flow.report["entry_state_sha256"]:
        raise ValueError("Recorded entry state changed")
    if flow.report["scene_session"] != store.status()["session_id"]:
        raise ValueError("Work area changed since entry; reassess the scene before contact")
    preview = store.export(flow.report["motion_review"])["preview"]
    try:
        image = entry_photo(args.entry_image, args.entry_metadata, flow.report["entry_finished_unix"], time.time())
    except (ValueError, KeyError, OSError, TypeError) as exc:
        raise CaptureUnavailable(str(exc)) from exc
    preview = dict(preview, image=image, groups=[], duration_s=0, start=read_json(state_path)["segments"][-1]["final_positions"])
    starts = requested_program_starts(flow, args.start_ros_programs, "contact")
    component = contact_component(state_sha, image["original_sha256"], bool(starts))
    risk = args.risk or "high"
    if not args.visual_confirmed:
        risk = "high"
    elif risk == "low":
        risk = "medium"
    meta = dict(task=TASK, summary="Close both grippers on the table-supported carton, then hold",
                risk=risk, reason=args.reason or "Operator review of the actual open-entry image requested.",
                stage="contact", duration_s=0, speed_percent=store.status()["settings"]["speed_percent"],
                components=[component], entry_state_sha256=state_sha, capture_sha256=image["original_sha256"],
                explicit_regular_start=bool(starts), program_start_arms=starts, scene_session=flow.report["scene_session"],
                arms=["right_front","right_rear"], requires_area=True)
    if not args.risk:
        assess_library_step(flow, store, meta, preview, visual_confirmed=args.visual_confirmed)
    with flow.approval(store, meta, preview) as identifier:
        flow.phase("close", "carton_gripper_phase.py", "close", "--state", state_path, "--output", out/"grasp",
                   "--execute", "--visual-confirmed", "--review-id", identifier,
                   "--review-image-sha256", image["original_sha256"],
                   *(["--start-ros-programs"] if starts else []))
        contact = read_json(out/"grasp/result.json")
        from uwa_cell_motion.protection_backend import minimal_enabled
        verified = (contact.get('gripper_commands_completed') if minimal_enabled()
                    else contact.get('static_contact_hold_verified'))
        if not contact.get("success") or not verified:
            raise ValueError("Final static contact hold unconfirmed")
        flow.report.update(success=True, phase="SUPPORTED_CONTACT_HELD")


def main():
    args = arguments()
    out = args.output.resolve()
    if not (args.execute or args.plan_only):
        print(json.dumps(dict(executed=False, phases=[*(["prepare_recipe"] if args.program else []),
              "snapshot", "registration","plan_high","plan_entry",
              "prepare_high","prepare_entry","motion_review","high","entry",
              "actual_image_review","contact_review","close","hold"])))
        return 0
    if not args.close_after_review:
        out.mkdir(parents=True, exist_ok=False)
    with (out/".workflow.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.close_after_review:
            report = read_json(out/"workflow.json")
            if report["phase"] != "WAITING_VISUAL_REVIEW":
                raise ValueError("No completed open entry awaiting visual review")
            if not all(k in report for k in ("scene_session","motion_review","entry_state_sha256","entry_finished_unix")):
                print("This entry predates the reviewed pilot. Its existing workflow is preserved. "
                      "Use the original explicit supported-grasp contact procedure for this run.", file=sys.stderr)
                return 1
        else:
            report = dict(success=False, execute=args.execute, started_wall=datetime.now().astimezone().isoformat(),
                          started_monotonic_s=time.monotonic(), events=[], loaded_motion=False)
        flow = Workflow(out, report)
        store = None
        try:
            if args.plan_only:
                plan_offline(flow, args)
            else:
                store = ReviewStore()
                if args.close_after_review:
                    close_after_entry(flow, args, store)
                else:
                    approach(flow, args, store)
        except CaptureUnavailable as error:
            report.update(phase="WAITING_VISUAL_REVIEW", last_image_error=str(error))
            report["events"].append(dict(phase="IMAGE_REJECTED_BEFORE_CONTACT", error=str(error)))
            store.record_blocker(str(out), "Actual entry image required. " + str(error))
        except (Exception, KeyboardInterrupt) as error:
            stage = "contact" if args.close_after_review else "motion"
            if store is not None and not report.get(stage+"_review"):
                store.record_blocker(str(out), str(error) or "Interrupted")
            phase = "OFFLINE_APPROACH_REJECTED" if args.plan_only else "STOPPED_NO_AUTOMATIC_RECOVERY"
            report.update(success=False, phase=phase, error=str(error) or "Interrupted")
        finally:
            grasp = out/"grasp/result.json"
            if args.close_after_review and grasp.exists():
                contact = read_json(grasp)
                for key in ("confirmed_contact_members","static_contact_hold_verified"):
                    report[key] = contact.get(key)
                report["closing_control_result_success"] = contact.get("success", False)
            flow.save()
    print(json.dumps({k:v for k,v in report.items() if k != "events"}, indent=2))
    if args.plan_only:
        expected = "OFFLINE_APPROACH_PREPARED"
    else:
        expected = "SUPPORTED_CONTACT_HELD" if args.close_after_review else "WAITING_VISUAL_REVIEW"
    return 0 if report["phase"] == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())

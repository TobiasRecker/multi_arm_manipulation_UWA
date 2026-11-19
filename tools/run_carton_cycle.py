#!/usr/bin/env python3
"""Run the supported carton program or prepare its approach from offline inputs."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "uwa_cell_tasks"))
from uwa_cell_tasks.carton_review import contact_component, current_capture, entry_photo, motion_packet, motion_timing, read_json
from uwa_cell_tasks.motion_review import ReviewStore, START_PERCENT, TASK, caps, digest


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
    ap.add_argument("--observations", type=Path, help="Saved arm observations for --plan-only")
    ap.add_argument("--object-pose", type=Path, help="Saved carton pose for --plan-only")
    ap.add_argument("--close-after-review", action="store_true")
    ap.add_argument("--visual-confirmed", action="store_true",
                    help="Agent inspected this actual post-entry image")
    ap.add_argument("--start-ros-programs", action="store_true",
                    help="Include explicit unloaded regular startup under verified holds in this review")
    for name in ("image", "metadata", "intrinsics", "entry-image", "entry-metadata"):
        ap.add_argument("--" + name, type=Path)
    ap.add_argument("--registration-directory", type=Path, help="Reuse a successful registration only when every bound source and current capture is unchanged")
    ap.add_argument("--path-budget-s", type=float, help="Offline path-search time per candidate; no change to execution speed")
    ap.add_argument("--camera-reference-pose", type=Path)
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
    if args.plan_only:
        if not (args.observations and args.object_pose and (args.program or args.recipe)):
            ap.error("Offline planning needs --observations, --object-pose and --program or --recipe")
        if any((args.close_after_review, args.start_ros_programs, args.visual_confirmed, args.risk,
                args.image, args.metadata, args.intrinsics, args.entry_image, args.entry_metadata,
                args.registration_directory, args.camera_reference_pose, args.photo_reference,
                args.verification_image, args.verification_metadata, args.planar_texture, args.roi, args.face_roi)):
            ap.error("Live capture, review and execution options are invalid with --plan-only")
    elif args.observations or args.object_pose:
        ap.error("--observations and --object-pose require --plan-only")
    elif args.close_after_review:
        if not (args.execute and args.entry_image and args.entry_metadata):
            ap.error("Contact needs --execute, --entry-image and --entry-metadata")
    elif not all((args.image, args.metadata, args.intrinsics, args.program or args.recipe)):
        ap.error("Approach needs --image, --metadata, --intrinsics and --program or --recipe")
    elif args.program and args.registration_directory:
        ap.error("Reusing a registration requires --recipe with the original hardware.urdf path")
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
        print(f'{self.report["phase"]} {identifier}', flush=True)
        claimed = False
        try:
            while not store.claim(identifier):
                time.sleep(.4)
            claimed = True
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
    if not getattr(args, "program", None):
        return args.recipe, .15
    recipe = flow.out / "recipe"
    flow.phase("prepare_recipe", "prepare_carton_recipe.py", "--program", args.program,
               "--config", args.config, "--output", recipe)
    program_file = recipe / "program.json"
    raw = program_file.read_bytes()
    program = json.loads(raw)
    flow.report["program"] = dict(id=program["program_id"], path=str(program_file), sha256=digest(raw))
    return recipe, program["pregrasp_m"]


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
    runners = [("high", "run_carton_pregrasp.py", "--evidence", out/"high-plan"),
               ("entry", "run_carton_open_entry.py", "--plan", out/"entry-plan/result.json")]
    paths = [out/"review-high.json", out/"review-entry.json"]
    for (name, tool, source, value), bundle in zip(runners, paths, strict=True):
        flow.phase("prepare_"+name, tool, source, value, "--prepare-reviewed", bundle, "--command-velocity",
                   joint, "--tcp-speed-m-s", tcp, "--output", out/("prepared-"+name))
    return runners, paths


def plan_offline(flow, args):
    joint, tcp = caps(START_PERCENT)
    observations, object_pose = args.observations.resolve(), args.object_pose.resolve()
    flow.report["offline_inputs"] = {
        key: dict(path=str(path), sha256=digest(path.read_bytes()))
        for key, path in (("observations", observations), ("object_pose", object_pose))
    }
    recipe, pregrasp_m = resolve_recipe(flow, args)
    _, paths = prepare_approach(flow, args, joint, tcp, recipe, observations, object_pose, pregrasp_m)
    flow.report.update(success=True, phase="OFFLINE_APPROACH_PREPARED", speed_percent=START_PERCENT,
                       review_bundles=[str(path) for path in paths])


def approach(flow, args, store):
    out = flow.out
    status = store.status()
    if not status["area_released"] or not status.get("area_released_at"):
        raise ValueError("Release the physical work area in UWA Robot Power before acquiring the scene")
    current_capture(args.image, args.metadata, status["area_released_at"], time.time())
    if getattr(args,"verification_image",None):current_capture(args.verification_image,args.verification_metadata,status["area_released_at"],time.time())
    flow.report["scene_session"] = status["session_id"]
    speed = status["settings"]["speed_percent"]
    joint, tcp = caps(speed)
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
                   *(["--planar-texture"] if getattr(args,"planar_texture",False) else []),
                   *(["--photo-reference", args.photo_reference] if getattr(args,"photo_reference",None) else []),
                   *(["--verification-image",args.verification_image,"--verification-metadata",args.verification_metadata]if getattr(args,"verification_image",None)else []),
                   *(["--roi", *args.roi] if args.roi else []),
                   *(["--face-roi", *args.face_roi] if args.face_roi else []))
    runners, paths = prepare_approach(flow, args, joint, tcp, recipe, out/"snapshot/observations.json",
                                     out/"registration/object-pose.json", pregrasp_m)
    asset = read_json(REPO/"uwa_cell_description/assets/carton_avocado_v1/asset.json")
    meta, preview = motion_packet(paths, asset["dimensions_m"], speed, args.risk or "high",
                                  args.reason or "Operator review requested for this approach.",
                                  args.start_ros_programs)
    meta["scene_session"] = status["session_id"]
    with flow.approval(store, meta, preview) as identifier:
        for (name, tool, source, value), bundle, sha in zip(runners, paths, meta["components"], strict=True):
            store.check_active(identifier, sha)
            # The entry client reads each active/open gripper and the four holds
            # immediately before releasing the group. A separate read-only process
            # here would check the same earlier state and rebuild the ROS graph.
            flow.phase(name, tool, source, value, "--reviewed", bundle, "--reviewed-sha256", sha,
                       "--review-id", identifier, "--execute", "--reset-unloaded", "--command-velocity", joint,
                       "--tcp-speed-m-s", tcp, "--output", out/name,
                       *(["--start-ros-programs"] if args.start_ros_programs and name == "high" else []))
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
    component = contact_component(state_sha, image["original_sha256"], args.start_ros_programs)
    risk = args.risk or "high"
    if not args.visual_confirmed:
        risk = "high"
    elif risk == "low":
        risk = "medium"
    meta = dict(task=TASK, summary="Close both grippers on the table-supported carton, then hold",
                risk=risk, reason=args.reason or "Operator review of the actual open-entry image requested.",
                stage="contact", duration_s=0, speed_percent=store.status()["settings"]["speed_percent"],
                components=[component], entry_state_sha256=state_sha, capture_sha256=image["original_sha256"],
                explicit_regular_start=args.start_ros_programs, scene_session=flow.report["scene_session"],
                arms=["right_front","right_rear"], requires_area=True)
    with flow.approval(store, meta, preview) as identifier:
        flow.phase("close", "carton_gripper_phase.py", "close", "--state", state_path, "--output", out/"grasp",
                   "--execute", "--visual-confirmed", "--review-id", identifier,
                   "--review-image-sha256", image["original_sha256"],
                   *(["--start-ros-programs"] if args.start_ros_programs else []))
        contact = read_json(out/"grasp/result.json")
        if not contact.get("success") or not contact.get("static_contact_hold_verified"):
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

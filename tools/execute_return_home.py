#!/usr/bin/env python3
"""Run a single frozen Return to Home phase on the active N100 task host."""

import argparse
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import time

from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
import numpy as np
from return_home_model import model_identity

try:
    from return_home_review_store import ReviewStore, digest
except ModuleNotFoundError:
    from uwa_cell_tasks.motion_review import ReviewStore, digest

from uwa_cell_gripper_control.client import GripperClient
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import config, dump, joint_names
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.minimal_execution import MinimalHardwareClient, PauseAwareClock, build_goal
from uwa_cell_motion.protection_backend import minimal_enabled
from uwa_cell_tasks.carton_review import entry_photo
from uwa_cell_tasks.minimal_snapshot import observe
from uwa_cell_tasks.reviewed_carton import START_TOLERANCE, check_boundaries, speed_envelope


TASK = "return_to_home"
ARGS = Path("src/multi_arm_manipulation_UWA")


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def approval(store, operation, meta, preview):
    identifier = store.submit(operation, meta, preview)
    claimed = False
    deadline = time.monotonic() + 900.
    try:
        print(f"WAITING_FOR_{meta['stage'].upper()}_REVIEW {identifier}", flush=True)
        while not store.claim(identifier):
            if time.monotonic() >= deadline:
                raise TimeoutError("Motion review expired before approval.")
            time.sleep(.4)
        claimed = True
        print(f"REVIEW_ACCEPTED_{meta['stage'].upper()} {identifier}", flush=True)
        yield identifier
    except BaseException as error:
        if claimed:
            store.finish(identifier, False, str(error) or "Interrupted")
        else:
            store.withdraw(identifier)
        raise
    else:
        if store.finish(identifier, True) != "done":
            raise RuntimeError("Return to Home review was revoked.")


def resume_ready(status, arms):
    if status.get("paused") is not False:
        return False
    if status.get("reason") != "OPERATOR RESUME":
        return True
    channels = status.get("arms", {})
    return all(channels.get(arm, {}).get("confirmed") is True
               and channels[arm].get("generation") == status.get("generation")
               and channels[arm].get("factor", 0.) >= 1. - 1e-9 for arm in arms)


def wait_for_reviewed_resume(client, arms):
    status = client.protection_status or {}
    if status.get("known_collisions"):
        raise ValueError("A cell geometry pause is unresolved. Inspect the UWA Robot Power Safety log.")
    if resume_ready(status, arms):
        return
    print("WAITING_FOR_OPERATOR_RESUME", flush=True)
    deadline = time.monotonic() + 900.
    while not resume_ready(client.protection_status or {}, arms):
        if (client.protection_status or {}).get("known_collisions"):
            raise ValueError("A cell geometry pause is unresolved. Inspect the UWA Robot Power Safety log.")
        if time.monotonic() >= deadline:
            raise TimeoutError("Operator RESUME did not complete before the approved probe timed out.")
        client.spin_once(timeout_sec=.05)


def check_start(client, start, arms):
    client.health()
    now = time.monotonic()
    status = client.protection_status or {}
    if not resume_ready(status, arms):
        raise ValueError("Software PAUSE or RESUME transition is active. Use UWA Robot Power.")
    for arm in client.names:
        channel = status.get("arms", {}).get(arm) or {}
        if channel.get("action_active") or (arm in arms and channel.get("paused")):
            raise ValueError(f"{arm}: controller still owns an action or has not acknowledged the current state.")
    for arm, record in client.records.items():
        received = record.get("received_monotonic_s", record.get("received", 0.))
        if not 0 <= now - received <= .2:
            raise ValueError(f"{arm}: fresh planning state is missing.")
    if set(client.records) != set(client.names) or any(
            joint not in client.positions or abs(client.positions[joint] - value) > START_TOLERANCE
            for joint, value in start.items()):
        raise ValueError("Current four-arm state differs from the reviewed phase. Replan from the actual start.")


class DescentObservation:
    """Collect already subscribed samples for this commissioning move only."""

    def __init__(self, model, arms):
        self.chains = {arm: Chain(model.original_description, "world", arm + "_tool0") for arm in arms}
        self.samples = {arm: {} for arm in arms}

    def capture(self, client):
        status = (client.protection_status or {}).get("arms", {})
        for arm, samples in self.samples.items():
            data = client.records.get(arm, {})
            stamp = data.get("received_monotonic_s")
            q = data.get("q")
            if isinstance(stamp, (int, float)) and isinstance(q, list) and len(q) == 6 and stamp not in samples:
                samples[stamp] = dict(q=q, native_time_s=data.get("device_timestamp"),
                                      controller_time_s=status.get(arm, {}).get("phase_time_s"))

    def summary(self):
        records, arrays = {}, {}
        for arm, samples in self.samples.items():
            rows = []
            for stamp, evidence in sorted(samples.items()):
                q = dict(zip(joint_names(arm), evidence["q"], strict=True))
                rows.append(dict(received_monotonic_s=stamp, tcp_z_m=float(self.chains[arm].forward(q)[2, 3]),
                                 **evidence))
            records[arm] = rows
            if len(rows) >= 3:
                stamps = np.array([r["received_monotonic_s"] for r in rows])
                z = np.array([r["tcp_z_m"] for r in rows])
                arrays[arm] = (stamps, z[0] - z)
        detail = dict(records=records, source="Existing N100 joint and controller subscriptions")
        if len(arrays) == len(self.samples):
            first = max(t[0] for t, _ in arrays.values())
            last = min(t[-1] for t, _ in arrays.values())
            if last > first:
                axis = np.unique(np.concatenate([t[(t >= first) & (t <= last)] for t, _ in arrays.values()]))
                progress = np.stack([np.interp(axis, t, z) for t, z in arrays.values()])
                detail.update(overlap_s=float(last - first),
                              maximum_observed_relative_vertical_displacement_m=float(np.ptp(progress, axis=0).max()),
                              end_progress_m={arm: float(z[-1]) for arm, (_, z) in arrays.items()})
        return detail


def follow_loaded(client, group, segment, observation=None):
    """Coordinate ordinary provisional Action acceptance before the scheduled start."""
    trajectories = group["trajectories"]
    client.activate(trajectories)
    check_start(client, group["start"], trajectories)
    goals = {arm: build_goal(value) for arm, value in trajectories.items()}
    for arm in goals:
        client.wait(client.actions[arm].server_is_ready, timeout=3.)
    deadline_clock = client.get_clock().now().nanoseconds + 200_000_000
    accept_by = time.monotonic() + .1
    pending, handles = {}, {}
    try:
        for arm, goal in goals.items():
            stamp = goal.trajectory.header.stamp
            stamp.sec, stamp.nanosec = divmod(deadline_clock, 10**9)
            pending[arm] = client.actions[arm].send_goal_async(goal)
        while len(handles) != len(pending):
            for arm, future in pending.items():
                if arm not in handles and future.done():
                    handle = future.result()
                    handles[arm] = handle
                    if not handle.accepted:
                        raise RuntimeError(f"{arm}: coupled trajectory rejected.")
            if time.monotonic() >= accept_by or client.get_clock().now().nanoseconds >= deadline_clock:
                raise TimeoutError("Coupled trajectory acceptance missed its common start deadline.")
            if len(handles) < len(pending):
                client.spin_once(timeout_sec=.002)
    except BaseException:
        cancelled = {}

        def cancel(arm, future):
            try:
                handle = future.result()
                if handle.accepted:
                    cancelled[arm] = handle.cancel_goal_async()
            except Exception:
                return

        for arm, future in pending.items():
            if future.done():
                cancel(arm, future)
            else:
                future.add_done_callback(lambda item, arm=arm: cancel(arm, item))
        cutoff = time.monotonic() + .2
        while time.monotonic() < cutoff and (
                not all(f.done() for f in pending.values()) or not all(f.done() for f in cancelled.values())):
            client.spin_once(timeout_sec=.005)
        segment["accepted"] = [arm for arm, handle in handles.items() if handle.accepted]
        segment["cancel_confirmed"] = [arm for arm, future in cancelled.items()
                                       if future.done() and future.exception() is None
                                       and future.result().goals_canceling]
        raise
    segment["accepted"] = list(handles)
    results = {arm: handle.get_result_async() for arm, handle in handles.items()}
    timer = PauseAwareClock()
    if observation is not None:
        observation.capture(client)
    while not all(f.done() for f in results.values()):
        client.spin_once(timeout_sec=.01)
        if observation is not None:
            observation.capture(client)
        if timer.tick(client.paused) > group["duration_s"] * 5 + 8:
            raise TimeoutError("Coupled trajectory result is unconfirmed. Inspect UWA Robot Power.")
    for arm, future in results.items():
        result = future.result()
        if result.status != GoalStatus.STATUS_SUCCEEDED or result.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL:
            raise RuntimeError(f"{arm}: {result.result.error_string or 'coupled trajectory failed'}")
    segment["executed"] = True


def advance(group):
    end = dict(group["start"])
    for arm, trajectory in group["trajectories"].items():
        end.update(zip(trajectory["joint_names"], trajectory["points"][-1]["positions"], strict=True))
    return end


def stages(plan):
    state = plan["start"]
    result = []
    for item in plan["objects"]:
        for kind, key in (("lower", "loaded"), ("open", None), ("withdraw", "retreat")):
            if item.get("commissioning") and kind != "lower":
                break
            groups = item[key] if key else []
            if kind == "lower" and not groups:
                continue
            risk = item.get({"open": "release_risk", "withdraw": "withdraw_risk"}.get(kind), "high")
            result.append(dict(kind=kind, arms=item["arms"], item=item, groups=groups,
                               start=state, risk=risk))
            if groups:
                state = advance(groups[-1])
    if plan["home"]:
        arms = sorted({arm for group in plan["home"] for arm in group["arms"]})
        result.append(dict(kind="home", arms=arms, item=None, groups=plan["home"],
                           start=state, risk="high" if plan["kept_arms"] else "low"))
    return result


def preview_for(plan, current, photo):
    tracks = {obj["link"]: dict(obj, motions=[]) for obj in plan["object_tracks"]}
    groups = []
    elapsed = 0.
    for phase in stages(plan):
        item = phase["item"]
        if phase["kind"] == "open" and item["gap_m"]:
            tracks[item["link"]]["motions"].append(dict(start_s=elapsed, duration_s=0.,
                                                       delta_m=[0., 0., -item["gap_m"]]))
        for group in phase["groups"]:
            groups.append(group)
            if item is not None and "object_delta_m" in group:
                tracks[item["link"]]["motions"].append(dict(start_s=elapsed, duration_s=group["duration_s"],
                                                           delta_m=group["object_delta_m"]))
            elapsed += group["duration_s"]
    full = current["kind"] in ("lower", "home")
    if not full:
        tracks = {}
        for obj in plan["object_tracks"]:
            tracks[obj["link"]] = dict(obj)
        for phase in stages(plan):
            item = phase["item"]
            if item and phase["kind"] == "open":
                if phase is current or item["link"] == current["item"]["link"]:
                    tracks[item["link"]]["pose"] = (item["release_pose"] if current["kind"] == "open" else item["support_pose"])
                    break
                tracks[item["link"]]["pose"] = item["support_pose"]
    preview = dict(start=plan["start"] if full else current["start"],
                   groups=groups if full else current["groups"],
                   robot_description=plan["robot_description"],
                   object_tracks=list(tracks.values()),
                   duration_s=elapsed if full else sum(g["duration_s"] for g in current["groups"]))
    if photo is not None:
        preview["image"] = photo
    return preview


def open_grippers(arms, report, save):
    def opening(arm):
        with GripperClient(arm) as client:
            return client.open(force_raw=0, speed_raw=16)

    report["finger_commands"] = {arm: "submitted" for arm in arms}
    save()
    with ThreadPoolExecutor(max_workers=len(arms)) as pool:
        futures = {arm: pool.submit(opening, arm) for arm in arms}
        wait(futures.values())
        for arm, future in futures.items():
            try:
                response = future.result()
                registers = response.get("status", {}).get("registers", {})
                open_target = (registers.get("OBJ") == 3 and registers.get("PRE") == 0
                               and registers.get("FLT") == 0 and 0 <= registers.get("POS", 256) <= 8)
                if response.get("success") is not True or not open_target:
                    raise ValueError("Opening action did not confirm the open target.")
                report["finger_commands"][arm] = response
            except Exception as error:
                report["finger_commands"][arm] = dict(success=False, error=str(error))
    save()
    failed = [arm for arm in arms if report["finger_commands"][arm].get("success") is not True]
    if failed:
        raise RuntimeError("Opening unconfirmed for " + ", ".join(failed) + ". Observe the actual object before replanning.")


def run(args):
    if not minimal_enabled():
        raise ValueError("Return to Home requires the active N100 minimal runtime.")
    if sha(args.plan) != args.sha256:
        raise ValueError("Frozen Return to Home plan digest changed.")
    plan = read(args.plan)
    if plan.get("kind") != TASK or plan.get("version") != 1 or plan["live_blockers"]:
        raise ValueError("Return to Home plan is not qualified for this N100 operation.")
    workflow = stages(plan)
    if not 0 <= args.index < len(workflow):
        raise ValueError("Unknown Return to Home phase.")
    current = workflow[args.index]
    report_path = args.plan.parent / f"phase-{args.index}.json"
    if report_path.exists():
        raise ValueError("This phase has already been attempted. Prepare a new revision.")
    if args.index:
        previous = read(args.plan.parent / f"phase-{args.index - 1}.json")
        if previous.get("success") is not True or previous.get("plan_sha256") != args.sha256:
            raise ValueError("The preceding Return to Home phase did not confirm completion.")
        earliest = previous["completed_at"]
    else:
        earliest = args.area_at
    report = dict(success=False, plan_sha256=args.sha256, phase=current["kind"],
                  arms=current["arms"], segments=[], finger_commands={})
    def save():
        dump(report_path, report)
    save()
    try:
        store = ReviewStore()
        status = store.status(TASK)
        if not status["area_released"] or status["session_id"] != args.session or status["settings"]["speed_percent"] != plan["speed_percent"]:
            raise ValueError("Work area or speed changed after planning. Prepare a new revision.")
        problem = HardwareProblem(args.plan.parent / "model", config(ARGS / "uwa_cell_motion/config/hardware_carton_supported_trend.yaml"),
                                  ARGS / "config/hardware_inventory.yaml")
        if problem.signature != plan["model_signature"] or model_identity(problem) != plan["model_identity"]:
            raise ValueError("N100 and ROSmini hardware model bindings changed.")
        kind, item = current["kind"], current["item"]
        groups = current["groups"]
        envelope = speed_envelope(problem, current["arms"], plan["joint_limit_rad_s"], plan["tcp_limit_m_s"])
        if groups:
            selected = sorted({arm for group in groups for arm in group["arms"]})
            check_boundaries(dict(start=current["start"], groups=groups), current["start"],
                             advance(groups[-1]), selected)
            for group in groups:
                for arm, trajectory in group["trajectories"].items():
                    envelope.check_trajectory(arm, trajectory["points"])
        photo = None
        if item:
            if args.photo is None or args.metadata is None:
                raise ValueError("A fresh OAK4 image is required for this object phase.")
            photo = entry_photo(args.photo, args.metadata, earliest, time.time())
        preview = preview_for(plan, current, photo)
        summaries = dict(lower="Carry and lower", open="Open the grippers",
                         withdraw="Confirm landed object and withdraw", home="Return to Home")
        if kind == "open":
            gap = item.get("reported_gap_m", item["gap_m"])
            reason = (f"Confirm the clear fall and landing space. Planned gap {gap * 1000:.1f} mm "
                      f"± {item['position_error_m'] * 1000:.1f} mm." if gap
                      else "Confirm that the object is supported before opening the grippers.")
        elif kind == "withdraw":
            reason = "Confirm the object has settled at the shown location and is clear of the open pads."
        elif kind == "lower":
            reason = ("First joint descent probe. The 3 mm descent is separately reviewed and existing N100 data "
                      "are recorded for its duration." if item.get("commissioning") else
                      "Confirm the grip group, held object and placement against the current photograph.")
        else:
            reason = "Checked unloaded Home path, with the other arms and task objects in the cell model."
        stage = "contact" if kind == "open" else "motion"
        component = digest(f"{args.sha256}/{args.index}/{photo['original_sha256'] if photo else ''}".encode())
        meta = dict(task=TASK, summary=summaries[kind] + (f" · {item['name']}" if item else ""),
                    risk=current["risk"], reason=reason, stage=stage, arms=current["arms"],
                    duration_s=sum(g["duration_s"] for g in groups), components=[component],
                    speed_percent=plan["speed_percent"], joint_limit_rad_s=plan["joint_limit_rad_s"],
                    scene_session=args.session, requires_area=True)
        if photo:
            meta["capture_sha256"] = photo["original_sha256"]
        with approval(store, f"{args.plan.parent.name}/{args.index}/{args.sha256}", meta, preview) as ticket:
            with motion_context():
                client = MinimalHardwareClient(problem, "hardware", current["arms"])
                try:
                    client.connect()
                    if kind == "lower" and item.get("commissioning"):
                        wait_for_reviewed_resume(client, current["arms"])
                    check_start(client, current["start"], current["arms"])
                    store.begin_component(ticket, component, stage=stage)
                    if kind == "open":
                        open_grippers(current["arms"], report, save)
                    for group in groups:
                        store.check_active(ticket, component, stage)
                        check_start(client, group["start"], group["arms"])
                        segment = dict(arms=group["arms"], executed=False, phase=group["phase"])
                        report["segments"].append(segment)
                        save()
                        if kind == "lower" and len(group["arms"]) > 1:
                            observation = DescentObservation(problem, group["arms"]) if item.get("commissioning") else None
                            try:
                                follow_loaded(client, group, segment, observation)
                            finally:
                                if observation is not None:
                                    segment["descent_observation"] = observation.summary()
                                    save()
                        else:
                            client.follow_group(group["trajectories"], duration_s=group["duration_s"], segment=segment)
                        save()
                finally:
                    client.destroy_node()
        report.update(success=True, completed_at=time.time())
    except BaseException as error:
        report["error"] = str(error) or "Interrupted"
        raise
    finally:
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--session")
    parser.add_argument("--area-at", type=float)
    parser.add_argument("--index", type=int)
    parser.add_argument("--photo", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    if args.observe:
        print(json.dumps(dict(snapshot=observe(), status=ReviewStore().status(TASK)), allow_nan=False))
    else:
        args.plan = args.plan.resolve()
        print(json.dumps(run(args), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

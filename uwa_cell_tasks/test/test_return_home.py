"""Offline and isolated Action mocks for Return to Home."""

from concurrent.futures import Future
from contextlib import contextmanager
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / name) for name in ("tools", "uwa_cell_motion", "uwa_cell_tasks")]

import execute_return_home as executor
from prepare_return_home import coupled_qualification, support_check
from return_home_request import ARMS, PLACEMENT_ROUTES, ROUTES, parse_advice, validate_request
from uwa_cell_tasks.motion_review import ReviewStore, START_PERCENT


def object_request(arms, *, action="place"):
    return dict(source="manual", action=action, arms=list(arms), name="Test workpiece",
                size_m=[.1, .12, .04], pose_xyz_yaw_deg=[.2, .3, .47, 0.],
                position_error_m=.002, table="right", target_xy_m=[.25, .25],
                profile="", release="support")


@pytest.mark.parametrize("members", range(1, 5))
def test_request_and_frozen_stages_support_one_to_four_arms(members):
    arms = list(ARMS[:members])
    request = dict(arms=arms, objects=[object_request(arms)], scene_confirmed=True)
    assert validate_request(request) == request
    item = dict(arms=arms, loaded=[], retreat=[], name="A")
    stages = executor.stages(dict(start={"q": 0.}, objects=[item], home=[]))
    assert [stage["kind"] for stage in stages] == ["lower", "open", "withdraw"]
    assert all(stage["arms"] == arms and stage["risk"] == "high" for stage in stages)


def test_keep_holding_accepts_a_group_outside_selected_arms():
    request = dict(arms=[ARMS[0]], objects=[object_request(ARMS[1:3], action="keep")],
                   scene_confirmed=True)
    assert validate_request(request) == request
    request["objects"][0]["action"] = "place"
    with pytest.raises(ValueError, match="Select every arm"):
        validate_request(request)
    request["objects"] = [object_request([ARMS[0]], action="keep")] * 2
    with pytest.raises(ValueError, match="only one"):
        validate_request(request)


def test_hydrogen_cannot_invent_a_route_or_robot_command():
    good = dict(home_routes=list(ROUTES), placement_routes=list(PLACEMENT_ROUTES),
                reason="Prefer direct.", assumptions=[])
    assert parse_advice(json.dumps(good)) == good
    with pytest.raises(ValueError):
        parse_advice(json.dumps(dict(good, home_routes=["movej", *ROUTES[1:]])))
    with pytest.raises(ValueError):
        parse_advice(json.dumps(dict(good, speed=.5)))


def test_coupled_qualification_bounds_relative_displacement():
    obj = dict(name="Fixture", arms=list(ARMS), qualification={})
    assert "no qualification" in coupled_qualification(obj, [.02, 0., 0.])
    obj["qualification"]["loaded_sync"] = dict(max_phase_skew_fraction=.05,
        allowable_relative_translation_m=.003, allowable_relative_rotation_rad=.003)
    assert coupled_qualification(obj, [.02, 0., 0.]) is None
    assert "relative-motion" in coupled_qualification(obj, [.2, 0., 0.])
    obj["arms"] = list(ARMS[:1])
    assert coupled_qualification(obj, [.2, 0., 0.]) is None


def test_placement_retries_from_original_pose_after_blocked_lateral_route(monkeypatch):
    import prepare_return_home as compiler
    attempted = []
    arm = ARMS[0]
    obj = dict(name="Fixture", arms=[arm], qualification={}, pose=np.eye(4), release_pose=np.eye(4))
    obj["pose"][2, 3] = .1
    obj["release_pose"][0, 3] = .07

    def trajectory(_, start, arms, delta):
        attempted.append((obj["pose"][:3, 3].tolist(), delta.tolist()))
        return {arm: {"duration_s": 1., "delta": delta}}

    def proof(_, start, paths, speed):
        delta = paths[arm]["delta"]
        if delta[0] and obj["pose"][2, 3] <= .11:
            return None, "Fixture obstructs the lower horizontal path"
        return {"min_clearance_m": .1}, None

    monkeypatch.setattr(compiler, "pose_path", trajectory)
    monkeypatch.setattr(compiler, "timed", lambda _, paths, *_limits: paths)
    monkeypatch.setattr(compiler, "prove_group", proof)
    monkeypatch.setattr(compiler, "check_cartesian", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(compiler, "endpoints", lambda start, _paths: dict(start))
    _, groups, blockers, route = compiler.plan_loaded(None, None, [obj], obj, {"q": 0.}, {},
                                                       PLACEMENT_ROUTES, .1, .08)
    assert route == "raise_then_lower"
    assert [g["phase"] for g in groups] == ["Raise for clearance", "Carry to the support", "Lower together"]
    assert len(attempted) == 4 and attempted[0][0] == attempted[1][0]
    assert not blockers
    np.testing.assert_allclose(obj["pose"], obj["release_pose"], atol=1e-15)


def test_drop_gap_and_landing_inside_support(monkeypatch):
    import prepare_return_home as compiler
    monkeypatch.setattr(compiler, "Chain", lambda *_: SimpleNamespace(forward=lambda _: np.eye(4)))
    problem = SimpleNamespace(original_description="", layout={"tables": {"right": {"width": 1., "length": 1.}}})
    item = compiler.manual_object(dict(object_request([ARMS[0]]), release="drop"))
    item["qualification"] = dict(upright_drop_qualified=True, landing_xy_error_m=.002,
                                 max_release_gap_m=.004)
    with pytest.raises(ValueError, match="drop gap"):
        support_check(problem, item)
    item["qualification"]["max_release_gap_m"] = .006
    _, _, gap, _ = support_check(problem, item)
    assert item["tolerance"] < gap and gap + item["tolerance"] < .006
    item["support"][0, 3] = .49
    with pytest.raises(ValueError, match="fit inside"):
        support_check(problem, item)


def test_partial_open_reports_each_arm_and_prevents_continue(monkeypatch):
    reads = []

    def make_gripper(arm):
        @contextmanager
        def scope():
            def opening(**_):
                reads.append(arm)
                if arm == ARMS[1]:
                    raise TimeoutError("Controller result unknown")
                return dict(success=True, position_raw=3, status=dict(registers=dict(OBJ=3, PRE=0, FLT=0, POS=3)))
            yield SimpleNamespace(open=opening)
        return scope()

    monkeypatch.setattr(executor, "GripperClient", make_gripper)
    result = {}
    with pytest.raises(RuntimeError, match=ARMS[1]):
        executor.open_grippers(ARMS[:2], result, lambda: None)
    assert sorted(reads) == sorted(ARMS[:2])
    assert result["finger_commands"][ARMS[0]]["success"]
    assert not result["finger_commands"][ARMS[1]]["success"]


def test_home_trust_is_task_specific_and_never_auto_approves_high(tmp_path):
    store = ReviewStore(tmp_path)
    store.area("new", True)
    store.settings(task="carton_supported_grasp", trust=100)
    meta = dict(task="return_to_home", stage="motion", risk="low", reason="Checked",
                summary="Home", arms=[ARMS[0]], components=["frozen"], speed_percent=START_PERCENT)
    low = store.submit("low", meta, {})
    assert not store.claim(low)
    store.settings(task="return_to_home", trust=50)
    assert store.claim(low)
    store.begin_component(low, "frozen")
    with pytest.raises(ValueError, match="already dispatched"):
        store.begin_component(low, "frozen")
    store.finish(low, True)
    high = store.submit("high", dict(meta, risk="high"), {})
    store.settings(task="return_to_home", trust=100)
    assert not store.claim(high)


def test_changed_measured_start_blocks_before_dispatch():
    joint = "left_arm_joint"
    client = SimpleNamespace(health=lambda: None, positions={joint: .002},
        records={ARMS[0]: dict(received_monotonic_s=executor.time.monotonic())}, names=ARMS[:1],
        protection_status=dict(paused=False, generation=1,
                               arms={ARMS[0]: dict(confirmed=True, generation=1)}))
    with pytest.raises(ValueError, match="differs from the reviewed phase"):
        executor.check_start(client, {joint: 0.}, ARMS[:1])


def test_rejected_coupled_peer_cancels_only_accepted_own_goal(monkeypatch):
    cancelled, headers = [], []

    def completed(value):
        future = Future()
        future.set_result(value)
        return future

    def endpoint(arm):
        def send(goal):
            headers.append(goal.trajectory.header.stamp.nanosec)

            def cancel():
                cancelled.append(arm)
                return completed(SimpleNamespace(goals_canceling=[arm]))

            return completed(SimpleNamespace(accepted=arm == ARMS[0], cancel_goal_async=cancel))
        return SimpleNamespace(server_is_ready=lambda: True, send_goal_async=send)

    monkeypatch.setattr(executor, "check_start", lambda *_: None)
    monkeypatch.setattr(executor, "build_goal", lambda _: SimpleNamespace(trajectory=SimpleNamespace(
        header=SimpleNamespace(stamp=SimpleNamespace(sec=0, nanosec=0)))))
    client = SimpleNamespace(activate=lambda _: None, wait=lambda fn, timeout: fn(),
        actions={arm: endpoint(arm) for arm in ARMS[:2]},
        get_clock=lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=0)))
    evidence = {}
    with pytest.raises(RuntimeError, match=ARMS[1]):
        executor.follow_loaded(client, dict(start={}, trajectories=dict.fromkeys(ARMS[:2])), evidence)
    assert headers == [200_000_000, 200_000_000]
    assert cancelled == [ARMS[0]] and evidence["cancel_confirmed"] == [ARMS[0]]

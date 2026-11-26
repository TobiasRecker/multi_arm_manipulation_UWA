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
from prepare_return_home import coupled_qualification, support_check, vertical_placement_legs, footprint_inside_table
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
    trajectory = dict(joint_names=["q"], points=[{"positions": [0.]}])
    item = dict(arms=arms, loaded=[dict(start={"q": 0.}, trajectories={arms[0]:trajectory})], retreat=[], name="A")
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
    obj = dict(name="Fixture", arms=[arm], qualification={}, release="support", pose=np.eye(4), release_pose=np.eye(4))
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


def test_force_preview_uses_bounded_steps_in_the_contact_region():
    approach, *probe = vertical_placement_legs(-.019, force_preview=True)
    assert approach[1][2] == pytest.approx(-.009) and approach[2] is None
    assert len(probe) == 10
    assert all(delta[2] == pytest.approx(-.001) and speed == .005 for _, delta, speed in probe)


def test_home_tries_a_parallel_alternative_before_serial_fallback(monkeypatch):
    import prepare_return_home as compiler

    def proof(_problem, _start, trajectories, _speed, _extra):
        if len(trajectories) == 2 and any(t["route"] == "direct" for t in trajectories.values()):
            return None, "Independently progressed direct routes overlap"
        return {"min_clearance_m": .1}, None

    monkeypatch.setattr(compiler, "home_candidates",
                        lambda _p, _s, _a, route, *_: dict(route=route, duration_s=1.))
    monkeypatch.setattr(compiler, "prove_group", proof)
    groups, uses = compiler.plan_home(None, {}, ARMS[:2], list(ROUTES), .1, .08, None)
    assert [g["arms"] for g in groups] == [list(ARMS[:2])]
    assert set(uses.values()) == {"upright_then_base"}


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


def test_complete_single_table_support_does_not_require_old_second_table(monkeypatch):
    import prepare_return_home as compiler
    monkeypatch.setattr(compiler, "Chain", lambda *_: SimpleNamespace(forward=lambda _: np.eye(4)))
    problem=SimpleNamespace(original_description="",layout={"tables":{"right":{"width":1.,"length":1.}}})
    item=compiler.manual_object(object_request([ARMS[0]]))
    item['support_sides']=['left','right'];item['qualification']={}
    support_check(problem,item)
    assert item['support_sides']==['right']
    assert 'conservative footprint' in item['support_selection']


def test_support_requires_all_corners_plus_existing_uncertainty():
    table=np.eye(4);dimensions=dict(width=1.,length=1.)
    points=np.array([[.49,.1,0.],[.49,-.1,0.],[.3,.1,0.],[.3,-.1,0.]])
    assert footprint_inside_table(points,table,dimensions,.005)
    assert not footprint_inside_table(points,table,dimensions,.02)
    points[0,0]=.51
    assert not footprint_inside_table(points,table,dimensions,0.)


def test_thin_board_support_band_preserves_table_penetration_rejection():
    import prepare_return_home as compiler
    entries={}
    model=SimpleNamespace(scene=SimpleNamespace(allowed_collision_matrix=SimpleNamespace(
        set_entry=lambda a,b,allow:entries.update({(a,b):allow}))))
    obj=dict(link='carton',name='Test carton',pose=np.eye(4),bottom_points=np.array([[0.,0.,0.]]),
        boxes=[dict(lo=[-.1,-.1,-.005],hi=[.1,.1,.1])],table_height=0.,
        support_sides=['right'],thin_support_tops={'right_charuco_plate':.003},tolerance=.005)
    compiler.actual_scene(model,[obj],{})
    assert entries[('carton_body','right_charuco_plate')] is True
    raised=np.eye(4);raised[2,3]=.010
    compiler.actual_scene(model,[obj],{},moving=obj,pose=raised)
    assert entries[('carton_body','right_charuco_plate')] is False
    below=np.eye(4);below[2,3]=-.001
    with pytest.raises(ValueError,match='below the support plane'):
        compiler.actual_scene(model,[obj],{},moving=obj,pose=below)


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
            yield SimpleNamespace(open=opening, status=lambda: dict(
                registers=dict(ACT=1, STA=3, FLT=0), actuation_enabled=True, busy=False))
        return scope()

    monkeypatch.setattr(executor, "GripperClient", make_gripper)
    result = {}
    with pytest.raises(RuntimeError, match=ARMS[1]):
        executor.open_grippers(ARMS[:2], result, lambda: None)
    assert sorted(reads) == sorted(ARMS[:2])
    assert result["finger_commands"][ARMS[0]]["success"]
    assert not result["finger_commands"][ARMS[1]]["success"]


def test_inactive_gripper_prevents_opening_the_whole_group(monkeypatch):
    @contextmanager
    def make_gripper(arm):
        def status():
            active = arm == ARMS[0]
            return dict(registers=dict(ACT=int(active), STA=3 if active else 0, FLT=0),
                        actuation_enabled=True, busy=False)

        def opening(**_):
            pytest.fail(f"Unexpected opening command for {arm}")

        yield SimpleNamespace(status=status, open=opening)

    monkeypatch.setattr(executor, "GripperClient", make_gripper)
    result = dict(finger_commands={})
    with pytest.raises(RuntimeError, match=rf"No gripper commands sent.*{ARMS[1]}.*ACT=0, STA=0, FLT=0"):
        executor.open_grippers(ARMS[:2], result, lambda: None)
    assert not result["finger_commands"]
    assert result["gripper_readiness"][ARMS[0]]["ready"]
    assert not result["gripper_readiness"][ARMS[1]]["ready"]


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


def test_low_risk_return_home_open_can_use_task_trust_and_still_needs_a_photo(tmp_path):
    store = ReviewStore(tmp_path)
    store.area("new", True)
    store.settings(task="return_to_home", trust=50)
    meta = dict(task="return_to_home", stage="contact", risk="low", reason="Checked stable placement",
                summary="Open", arms=[ARMS[0]], components=["frozen"], speed_percent=START_PERCENT)
    with pytest.raises(ValueError, match="visual evidence"):
        store.submit("without capture", meta, {})
    ticket = store.submit("with capture", meta, {"image": {"original_sha256": "fixture"}})
    assert store.claim(ticket)


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


def test_unloaded_timeout_cancels_only_the_current_group():
    cancelled = []

    def accepted(arm):
        def cancel():
            cancelled.append(arm)
            response = Future()
            response.set_result(SimpleNamespace(goals_canceling=[arm]))
            return response

        goal = Future()
        goal.set_result(SimpleNamespace(accepted=True, cancel_goal_async=cancel))
        return goal

    client = SimpleNamespace(pending={ARMS[0]: accepted(ARMS[0])})

    def follow(*_, **__):
        assert client.pending == {}
        client.pending[ARMS[1]] = accepted(ARMS[1])
        raise TimeoutError("Controller did not complete.")

    client.follow_group = follow
    segment = dict(executed=False)
    with pytest.raises(TimeoutError, match="Controller did not complete"):
        executor.follow_unloaded(client, dict(trajectories={ARMS[1]: {}}, duration_s=1.), segment)
    assert cancelled == [ARMS[1]]
    assert segment == dict(executed=False, cancel_confirmed=[ARMS[1]])


def test_partial_home_continuation_retains_exact_remaining_path_and_rejects_unconfirmed_prefix():
    from copy import deepcopy
    groups=[dict(phase='Return to Home',arms=[arm],start={'joint':float(i)},
        trajectories={arm:dict(joint_names=['joint'],points=[dict(positions=[float(i+1)])])})
        for i,arm in enumerate(('right_front','right_rear'))]
    current=dict(kind='home',groups=groups,start={'joint':0.},arms=['right_front','right_rear'])
    result=dict(success=False,plan_sha256='bound',phase='home',finger_commands={},segments=[
        dict(phase='Return to Home',arms=['right_front'],executed=True,final_positions={'joint':1.},
             completion_source='FollowJointTrajectory result; no standstill test')])
    suffix=executor.remaining_home(current,result,'bound')
    assert suffix['groups'][0] is groups[1]
    assert suffix['start']=={'joint':1.} and suffix['arms']==['right_rear']
    bad=deepcopy(result);bad['segments'][0]['executed']=False
    with pytest.raises(ValueError,match='completion evidence'):executor.remaining_home(current,bad,'bound')
    bad=deepcopy(result);bad['segments'][0]['final_positions']['joint']+=.01
    with pytest.raises(ValueError,match='completion evidence'):executor.remaining_home(current,bad,'bound')
    with pytest.raises(ValueError,match='matching partial'):executor.remaining_home(current,result,'changed')


def test_partial_home_preview_contains_only_remaining_groups_and_supported_object():
    group=dict(duration_s=51.,arms=['right_rear'])
    current=dict(kind='home',remaining_only=True,start={'joint':1.},groups=[group])
    plan=dict(start={'joint':0.},robot_description='cell',
        object_tracks=[dict(link='carton',pose='old')],objects=[dict(link='carton',support_pose='landed')])
    preview=executor.preview_for(plan,current,None)
    assert preview['groups']==[group] and preview['start']==current['start']
    assert preview['duration_s']==51. and preview['object_tracks'][0]['pose']=='landed'

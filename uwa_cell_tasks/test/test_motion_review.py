from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uwa_cell_tasks.motion_review import ReviewStore, START_PERCENT, TASK, caps
from uwa_cell_tasks.carton_review import entry_photo, motion_timing


def packet(stage="motion", risk="low"):
    return dict(task=TASK, stage=stage, components=["high", "entry"] if stage=="motion" else ["close"],
                risk=risk, reason="Checked open entry", speed_percent=START_PERCENT, explicit_regular_start=False)


def test_decision_is_bound_once_and_reconnect_is_read_only(tmp_path):
    store = ReviewStore(tmp_path)
    meta = packet()
    identifier = store.submit("run/motion", meta, {})
    assert not store.claim(identifier)
    sha = store.export(identifier)["sha256"]
    with pytest.raises(ValueError):
        store.decide(identifier, sha, "approve")
    store.area("new", True)
    with pytest.raises(ValueError):
        store.decide(identifier, "earlier revision", "approve")
    def approve(_):
        try:
            ReviewStore(tmp_path).decide(identifier, sha, "approve")
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(approve, range(2))) == 1
    assert store.claim(identifier)
    with pytest.raises(ValueError):
        store.begin_component(identifier, "entry")
    store.begin_component(identifier, "high")
    with pytest.raises(ValueError):
        store.begin_component(identifier, "high")
    with pytest.raises(ValueError):
        store.check_startup(identifier, "motion")
    assert ReviewStore(tmp_path).status()["pending"][0]["status"] == "running"
    store.begin_component(identifier, "entry")
    assert store.finish(identifier, True) == "done"
    with pytest.raises(ValueError):
        store.claim(identifier)


def test_area_or_speed_change_invalidates_a_review(tmp_path):
    store = ReviewStore(tmp_path)
    store.area("new", True)
    store.settings(trust=50)
    review = store.submit("1", packet(), {})
    assert store.claim(review)
    session = store.status()["session_id"]
    store.area(session, False)
    store.area("new", True)
    with pytest.raises(ValueError):
        store.check_active(review, "high")
    assert store.finish(review, True) == "failed"
    pending = store.submit("2", packet(), {})
    store.settings(speed=25)
    with pytest.raises(ValueError):
        store.claim(pending)
    assert caps(START_PERCENT) == pytest.approx((.1, .25/3))


def test_contact_and_task_trust(tmp_path):
    store = ReviewStore(tmp_path)
    store.area("new", True)
    store.settings(trust=50)
    with pytest.raises(ValueError):
        store.submit("contact", packet("contact","low"), {"image":{}})
    identifier = store.submit("real/close", packet("contact","medium"), {"image":{"original_sha256":"photo"}})
    assert not store.claim(identifier)
    store.settings(trust=100)
    assert store.claim(identifier)
    store.check_active(identifier, "close", "contact")
    assert store.status()["pending"][0]["decided_by"] == "agent"
    store.finish(identifier, True)
    high = store.submit("unknown case", packet("contact","high"), {"image":{"original_sha256":"photo"}})
    assert not store.claim(high)
    store.decide(high, store.export(high)["sha256"], "replan")
    with pytest.raises(ValueError):
        store.claim(high)


def test_series_only_decreases_and_never_restores_speed(tmp_path):
    store=ReviewStore(tmp_path)
    store.area("new", True)
    store.settings(series_name="first carton placement", series_min=20)
    store.settings(speed=25, agent_series="first carton placement")
    for new, name in [(26,"first carton placement"),(19,"first carton placement"),(21,"other")]:
        with pytest.raises(ValueError):
            store.settings(speed=new, agent_series=name)
    store.settings(end_series=True)
    assert store.status()["settings"]["speed_percent"] == 25
    with pytest.raises(ValueError):
        store.settings(speed=20, agent_series="first carton placement")
    store.settings(speed=START_PERCENT)
    assert store.status()["settings"]["speed_percent"] == START_PERCENT


def test_another_task_begins_unsure_and_has_its_own_setting(tmp_path):
    store = ReviewStore(tmp_path)
    store.settings(trust=100)
    assert store.status("other_task")["settings"]["trust"] == 0
    store.settings(task="other_task", trust=50)
    assert ReviewStore(tmp_path).status("other_task")["settings"]["trust"] == 50
    assert store.status()["settings"]["trust"] == 100
    store.record_blocker("run", "Object pose unavailable. Acquire a new image.")
    assert store.status()["history"][0]["reason"].startswith("Object pose unavailable")
    assert store.status()["pending"] == []


def test_optional_program_start_needs_an_explicit_operator_decision(tmp_path):
    store = ReviewStore(tmp_path)
    store.area("new", True)
    store.settings(trust=100)
    identifier = store.submit("start and approach", dict(packet(), explicit_regular_start=True), {})
    assert not store.claim(identifier)
    store.decide(identifier, store.export(identifier)["sha256"], "approve")
    assert store.claim(identifier)
    store.check_startup(identifier, "motion")


def test_owner_restart_and_boot_invalidate_dispatch(tmp_path):
    store=ReviewStore(tmp_path)
    store.area("new", True)
    store.settings(trust=100)
    identifier=store.submit("test",packet(),{})
    assert store.claim(identifier)
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE tickets SET owner_start='expired'")
    with pytest.raises(ValueError):
        store.check_active(identifier,"high")
    new=ReviewStore(tmp_path)
    assert new.status()["history"][0]["status"]=="interrupted"
    active=new.submit("test2",packet(),{})
    assert new.claim(active)
    with sqlite3.connect(store.path) as db:
        state=json.loads(db.execute("SELECT data FROM control").fetchone()[0])
        state["boot"]="old"
        db.execute("UPDATE control SET data=?",(json.dumps(state),))
    assert not ReviewStore(tmp_path).status()["area_released"]


def test_photo_belongs_to_this_entry_and_source(tmp_path):
    path=tmp_path/"standard.png"
    Image.new("RGB",(32,32)).save(path)
    meta=dict(success=True,device_id="oak",camera_ip="192.168.8.238",standard=dict(path=path.name,width=32,height=32),
              started_at="2024-01-01T00:00:00+00:00",finished_at="2024-01-01T00:00:01+00:00")
    metadata=tmp_path/"metadata.json"
    metadata.write_text(json.dumps(meta))
    photo=entry_photo(path,metadata,1704067199,1704067202)
    assert photo["mime_type"]=="image/jpeg"
    with pytest.raises(ValueError):
        entry_photo(path,metadata,1704067201,1704067202)
    with pytest.raises(ValueError):
        entry_photo(tmp_path/"other.png",metadata,0,1704067202)


def test_motion_timing_skips_sample_gaps_and_counts_shared_intervals(tmp_path):
    for arm,times in (("right_front",[1.,1.1,1.2,3.]),("right_rear",[1.05,1.15,1.25])):
        rows=[dict(received=t,v=[.01]*6) for t in times]
        (tmp_path/(arm+"-native.json")).write_text(json.dumps(dict(records=rows)))
    summary=motion_timing(tmp_path,0,4)
    assert summary["observed_overlap_s"]==pytest.approx(.15)
    assert summary["observed_motion_s"]==pytest.approx(dict(right_front=.2,right_rear=.2))


def test_complete_workflow_with_mock_devices_uses_same_revisions(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from datetime import datetime, timezone
    import hashlib
    import time
    import importlib.util
    tool=Path(__file__).resolve().parents[2]/"tools/run_carton_cycle.py"
    spec=importlib.util.spec_from_file_location("review_cycle_test", tool)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store=ReviewStore(tmp_path/"store")
    store.area("new",True)
    store.settings(trust=100)
    history=[]
    run=tmp_path/"run"
    run.mkdir()
    def dump(path,data):
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(json.dumps(data))
    def photo(where):
        where.mkdir()
        image=where/"standard.png"
        Image.new("RGB",(20,20)).save(image)
        stamp=datetime.now(timezone.utc).isoformat()
        meta=where/"metadata.json"
        dump(meta, dict(success=True,device_id="oak",camera_ip="192.168.8.238",started_at=stamp,
                        finished_at=stamp,standard=dict(path=image.name,width=20,height=20)))
        return image,meta
    xml=tmp_path/"robot.urdf"
    xml.write_text('<robot name="fixture"/>')
    arms=["right_front","right_rear"]
    joints={a:[f"{a}_joint_{i}" for i in range(6)] for a in arms}
    def state(q):
        return {key:q for names in joints.values() for key in names}
    def phase(self,name,_,*args):
        args=list(args)
        history.append(name)
        if name=="plan_high":
            dump(run/"high-plan/evidence.json",dict(saved_start=state(0),
                 path=dict(joint_names=list(state(0)),waypoints=[list(state(.02).values())])))
        if name in {"prepare_high","prepare_entry"}:
            kind=name.split("_")[-1]
            a,b=(0,.02) if kind=="high" else (.02,.04)
            trajectories={arm:dict(joint_names=joints[arm],duration_s=1,points=[
                dict(time=t,positions=[q]*6,velocities=[0]*6,accelerations=[0]*6) for t,q in [(0,a),(1,b)]])
                for arm in arms}
            dump(run/f"review-{kind}.json",dict(phase=kind,groups=[dict(arms=arms,trajectories=trajectories)],
                 start=state(a),carton=dict(world_pose=[[1]],shell_boxes=[]),preview_urdf=str(xml),
                 preview_urdf_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),
                 joint_limit_rad_s=.1,tcp_limit_m_s=.25/3))
        if name in {"high","entry","close"}:
            identifier=args[args.index("--review-id")+1]
            if name=="close":
                sha=module.contact_component(hashlib.sha256((run/"entry/result.json").read_bytes()).hexdigest(),
                    args[args.index("--review-image-sha256")+1],False)
                store.begin_component(identifier,sha,"contact")
                dump(run/"grasp/result.json",dict(success=True,static_contact_hold_verified=True))
            else:
                sha=args[args.index("--reviewed-sha256")+1]
                store.begin_component(identifier,sha)
                assert sha==hashlib.sha256((run/f"review-{name}.json").read_bytes()).hexdigest()
                dump(run/name/"result.json",dict(segments=[dict(final_positions=state(.04))], review_id=identifier))
    monkeypatch.setattr(module.Workflow,"phase",phase)
    flow=module.Workflow(run,dict(events=[],started_monotonic_s=time.monotonic()))
    image,metadata=photo(tmp_path/"before")
    args=SimpleNamespace(image=image,metadata=metadata,intrinsics=tmp_path/"intrinsics",recipe=tmp_path,
        risk="low",reason="Review fixture",config=tmp_path/"config",camera_reference_pose=None,roi=None,
        face_roi=None,start_ros_programs=False)
    module.approach(flow,args,store)
    assert flow.report["phase"]=="WAITING_VISUAL_REVIEW"
    args.entry_image,args.entry_metadata=photo(tmp_path/"after")
    args.visual_confirmed=True
    module.close_after_entry(flow,args,store)
    assert flow.report["success"] and history[-3:]==["high","entry","close"]
    assert [row["status"] for row in store.status()["history"]]==["done","done"]

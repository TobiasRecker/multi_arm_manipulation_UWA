"""N100-local decisions for one supported carton cycle. No device or ROS calls."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

TASK = "carton_supported_grasp"
START_PERCENT = 100 / 3
RISKS = {"low": 1, "medium": 2, "high": 3}
TRUST = {0: 0, 50: 1, 100: 2}
TERMINAL = {"done", "failed", "rejected", "replan", "revoked", "interrupted"}


def encoded(value):
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def process_stamp(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] in {"Z", "X"} else fields[19]
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return None


def percent(value):
    value = float(value)
    if not math.isfinite(value) or not 0 < value <= 100:
        raise ValueError("Speed must be greater than 0 and at most 100 percent")
    return value


def caps(value):
    return .3 * (percent(value) / 100), .25 * (percent(value) / 100)


class ReviewStore:
    def __init__(self, directory=None):
        self.directory = Path(directory or Path.home() / ".local/state/uwa-motion-review")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.directory / "reviews.sqlite3"
        self.boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS control(id INTEGER PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tickets(
                    id TEXT PRIMARY KEY, operation TEXT UNIQUE NOT NULL, sha TEXT NOT NULL,
                    status TEXT NOT NULL, session TEXT, meta TEXT NOT NULL, preview TEXT NOT NULL,
                    reason TEXT, actor TEXT, created REAL NOT NULL, changed REAL NOT NULL,
                    pid INTEGER, owner_start TEXT, invalid INTEGER NOT NULL DEFAULT 0);
                CREATE UNIQUE INDEX IF NOT EXISTS one_running ON tickets(status) WHERE status='running';
                CREATE TABLE IF NOT EXISTS dispatch(id TEXT, component TEXT,
                    PRIMARY KEY(id, component));
            """)
        with self.write() as db:
            initial = dict(boot=self.boot, session_id=None, task_trust={}, speed_percent=START_PERCENT, series=None)
            db.execute("INSERT OR IGNORE INTO control VALUES(1,?)", (encoded(initial),))
            state = self._control(db)
            if "task_trust" not in state:
                state["task_trust"] = {TASK: state.pop("trust", 0)}
                self._save(db, state)
            if state["boot"] != self.boot:
                state.update(boot=self.boot, session_id=None, series=None, area_released_at=None)
                self._save(db, state)
                db.execute("UPDATE tickets SET status='interrupted',reason='N100 restarted' "
                           "WHERE status IN ('pending','approved','running')")
            for row in db.execute("SELECT * FROM tickets WHERE status='running'"):
                if process_stamp(row["pid"]) != row["owner_start"]:
                    db.execute("UPDATE tickets SET status='interrupted',reason='Executor exited' WHERE id=?", (row["id"],))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=2, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def write(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
            except BaseException:
                db.rollback()
                raise
            db.commit()

    @staticmethod
    def _control(db):
        return json.loads(db.execute("SELECT data FROM control WHERE id=1").fetchone()[0])

    @staticmethod
    def _save(db, value):
        db.execute("UPDATE control SET data=? WHERE id=1", (encoded(value),))

    @staticmethod
    def _invalidate(db, reason):
        db.execute("UPDATE tickets SET invalid=1, reason=?, changed=?, "
                   "status=CASE WHEN status='running' THEN 'running' ELSE 'revoked' END "
                   "WHERE status IN ('pending','approved','running')", (reason, time.time()))

    def area(self, session, release):
        with self.write() as db:
            state = self._control(db)
            current = state["session_id"]
            if release:
                if session != (current or "new") and not (current and session == "new"):
                    raise ValueError("Work session has changed")
                state["session_id"] = current or uuid.uuid4().hex
                if not current:
                    state["area_released_at"] = time.time()
                db.execute("UPDATE tickets SET session=? WHERE status='pending' AND session IS NULL",
                           (state["session_id"],))
            else:
                if not current or session != current:
                    raise ValueError("Work session has changed")
                self._invalidate(db, "Work area release revoked")
                state.update(session_id=None, series=None, area_released_at=None)
            self._save(db, state)

    def settings(self, *, task=TASK, trust=None, speed=None, series_name=None, series_min=None,
                 end_series=False, agent_series=None):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", task):
            raise ValueError("Invalid task name")
        with self.write() as db:
            state = self._control(db)
            old_speed = state["speed_percent"]
            old_trust = state["task_trust"].get(task, 0)
            if agent_series is not None:
                series = state["series"]
                if (not series or agent_series != series["name"] or not state["session_id"] or speed is None
                        or trust is not None or series_name is not None or end_series
                        or not series["min_percent"] <= percent(speed) <= state["speed_percent"]):
                    raise ValueError("Agent speed changes require a permitted decrease in the current test series")
            if trust is not None:
                if trust not in TRUST:
                    raise ValueError("Choose a configured task trust level")
                state["task_trust"][task] = trust
            if speed is not None:
                state["speed_percent"] = percent(speed)
            if (series_min is None) != (series_name is None):
                raise ValueError("Both series name and minimum speed are required")
            if series_name is not None:
                if (not state["session_id"] or not series_name.strip() or end_series
                        or percent(series_min) > state["speed_percent"]):
                    raise ValueError("Release the work area and choose a valid test range")
                state["series"] = dict(name=series_name.strip(), min_percent=percent(series_min))
            if end_series:
                state["series"] = None
            if state["speed_percent"] != old_speed:
                self._invalidate(db, "Speed or task trust changed; reassess the plan")
            elif trust is not None and trust < old_trust:
                db.execute("UPDATE tickets SET invalid=1,reason='Task trust reduced',changed=?, "
                           "status=CASE WHEN status='running' THEN 'running' ELSE 'revoked' END "
                           "WHERE status IN ('pending','approved','running') AND json_extract(meta,'$.task')=?",
                           (time.time(), task))
            self._save(db, state)

    def submit(self, operation, meta, preview):
        if meta["task"] != TASK or meta["stage"] not in {"motion", "contact"} or meta["risk"] not in RISKS:
            raise ValueError("Unsupported task, stage or risk")
        if not meta["reason"].strip() or not meta["components"]:
            raise ValueError("A reason and a bound action are required")
        if meta["stage"] == "contact" and (meta["risk"] == "low" or not preview.get("image")):
            raise ValueError("Contact requires current visual evidence and at least medium risk")
        content = encoded(preview)
        sha = digest(encoded([operation, meta, digest(content.encode())]).encode())
        with self.write() as db:
            state = self._control(db)
            if meta["speed_percent"] != state["speed_percent"]:
                raise ValueError("Speed changed since preparation; generate a new revision")
            if meta.get("scene_session") and state["session_id"] != meta["scene_session"]:
                raise ValueError("Work area changed since capture; refresh the scene and plan")
            old = db.execute("SELECT * FROM tickets WHERE operation=?", (operation,)).fetchone()
            if old:
                if old["sha"] == sha:
                    return old["id"]
                raise ValueError("Changed content requires a new operation")
            identifier = uuid.uuid4().hex
            now = time.time()
            db.execute("INSERT INTO tickets(id,operation,sha,status,session,meta,preview,created,changed) "
                       "VALUES(?,?,?,'pending',?,?,?,?,?)",
                       (identifier, operation, sha, state["session_id"], encoded(meta), content, now, now))
            return identifier

    @staticmethod
    def _row(db, identifier):
        row = db.execute("SELECT id,sha,status,session,meta,reason,actor,invalid,pid,owner_start "
                         "FROM tickets WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise ValueError("Unknown review")
        return row

    @staticmethod
    def _eligible(state, row, meta):
        return (state["session_id"] and state["session_id"] == row["session"] and not row["invalid"]
                and state["speed_percent"] == meta["speed_percent"])

    def decide(self, identifier, sha, decision):
        actions = {"approve": "approved", "reject": "rejected", "replan": "replan"}
        if decision not in actions:
            raise ValueError("Unknown decision")
        with self.write() as db:
            row = self._row(db, identifier)
            if row["sha"] != sha or row["status"] != "pending":
                raise ValueError("Decision no longer matches a pending revision")
            if decision == "approve" and not self._eligible(self._control(db), row, json.loads(row["meta"])):
                raise ValueError("Release the work area and verify the active speed first")
            db.execute("UPDATE tickets SET status=?, actor='operator',changed=? WHERE id=?",
                       (actions[decision], time.time(), identifier))

    def claim(self, identifier):
        """Only the workflow owner claims; a GUI approval never dispatches a goal."""
        with self.write() as db:
            row = self._row(db, identifier)
            state, meta = self._control(db), json.loads(row["meta"])
            if row["status"] not in {"pending", "approved"}:
                raise ValueError("Review already " + row["status"])
            if not self._eligible(state, row, meta):
                return False
            automatic = (RISKS[meta["risk"]] <= TRUST[state["task_trust"].get(meta["task"], 0)]
                         and not meta.get("explicit_regular_start"))
            if row["status"] == "pending" and not automatic:
                return False
            if db.execute("SELECT 1 FROM tickets WHERE status='running'").fetchone():
                raise ValueError("Another review is executing")
            pid = os.getpid()
            db.execute("UPDATE tickets SET status='running',actor=?,pid=?,owner_start=?,changed=? WHERE id=?",
                       (row["actor"] or "agent", pid, process_stamp(pid), time.time(), identifier))
            return True

    def check_active(self, identifier, bundle_sha256, stage="motion"):
        with self.connection() as db:
            row = self._row(db, identifier)
            meta = json.loads(row["meta"])
            if (row["status"] != "running" or not self._eligible(self._control(db), row, meta)
                    or meta["stage"] != stage or bundle_sha256 not in meta["components"]
                    or process_stamp(row["pid"]) != row["owner_start"]):
                raise ValueError("Motion review is inactive, changed or revoked")

    def begin_component(self, identifier, component, stage="motion"):
        self.check_active(identifier, component, stage)
        with self.write() as db:
            row = self._row(db, identifier)
            if row["status"] != "running" or row["invalid"]:
                raise ValueError("Review has ended")
            expected = json.loads(row["meta"])["components"]
            index = db.execute("SELECT COUNT(*) FROM dispatch WHERE id=?", (identifier,)).fetchone()[0]
            if index >= len(expected) or expected[index] != component:
                raise ValueError("Action already dispatched or out of sequence")
            db.execute("INSERT INTO dispatch VALUES(?,?)", (identifier, component))

    def check_startup(self, identifier, stage):
        with self.connection() as db:
            row = self._row(db, identifier)
            meta = json.loads(row["meta"])
            if (row["status"] != "running" or not self._eligible(self._control(db), row, meta)
                    or meta["stage"] != stage or not meta.get("explicit_regular_start")):
                raise ValueError("Regular program startup was not included in this release")

    def finish(self, identifier, success, reason=None):
        with self.write() as db:
            row = self._row(db, identifier)
            if row["status"] != "running" or row["pid"] != os.getpid() or row["owner_start"] != process_stamp(os.getpid()):
                raise ValueError("Only the running workflow can finish a review")
            status = "done" if success and not row["invalid"] else "failed"
            db.execute("UPDATE tickets SET status=?,reason=COALESCE(reason,?),changed=? WHERE id=?",
                       (status, reason, time.time(), identifier))
            return status

    def record_blocker(self, operation, reason):
        """Expose a preflight/observation problem even when no executable review exists."""
        identifier = uuid.uuid4().hex
        now = time.time()
        with self.write() as db:
            db.execute("INSERT INTO tickets(id,operation,sha,status,meta,preview,reason,created,changed) "
                       "VALUES(?,?,?,'blocked','{}','{}',?,?,?)",
                       (identifier, operation+"/issue/"+identifier, "", reason, now, now))

    def withdraw(self, identifier):
        with self.write() as db:
            db.execute("UPDATE tickets SET status='interrupted',reason='Workflow stopped before execution',"
                       "changed=? WHERE id=? AND status IN ('pending','approved')", (time.time(), identifier))

    def status(self, task=TASK):
        with self.connection() as db:
            state = self._control(db)
            rows = db.execute("SELECT id,sha,status,meta,reason,actor FROM tickets "
                              "WHERE status IN ('pending','approved','running') ORDER BY created")
            active = [dict(json.loads(r["meta"]), id=r["id"], sha256=r["sha"], status=r["status"],
                           decision_reason=r["reason"], decided_by=r["actor"]) for r in rows]
            history = [dict(r) for r in db.execute("SELECT id,status,reason,actor FROM tickets "
                       "WHERE status NOT IN ('pending','approved','running') ORDER BY changed DESC LIMIT 8")]
        return dict(settings=dict(task=task, trust=state["task_trust"].get(task, 0), speed_percent=state["speed_percent"],
                                  series=state["series"]), session_id=state["session_id"],
                    area_released=bool(state["session_id"]), area_released_at=state.get("area_released_at"),
                    pending=active, history=history)

    def export(self, identifier):
        with self.connection() as db:
            row = self._row(db, identifier)
            preview = db.execute("SELECT preview FROM tickets WHERE id=?", (identifier,)).fetchone()[0]
            return dict(id=identifier, sha256=row["sha"], preview=json.loads(preview))

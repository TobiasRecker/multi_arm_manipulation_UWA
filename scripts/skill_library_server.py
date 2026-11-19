#!/usr/bin/env python3
"""Serve the UWA program library on the workstation's loopback interface."""

import argparse
from datetime import datetime, timezone
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import sys
from threading import Thread
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
PROGRAM_ID = "carton-supported-v1"
RUN_ID = re.compile(r"[a-f0-9]{32}")
PREVIEWS = {"oak_preview", "right_front_preview", "right_rear_preview"}
STATIC = {
    "/": (ROOT / "scripts/skill_library/index.html", "text/html; charset=utf-8"),
    "/index.html": (ROOT / "scripts/skill_library/index.html", "text/html; charset=utf-8"),
    "/styles.css": (ROOT / "scripts/skill_library/styles.css", "text/css; charset=utf-8"),
    "/app.js": (ROOT / "scripts/skill_library/app.js", "text/javascript; charset=utf-8"),
    "/assets/carton.png": (ROOT / "output/images/carton_in_virtual_cell.png", "image/png"),
}
STAGES = [
    {"id": "capture", "title": "Capture the scene", "description": "Reference the carton in an OAK4 standard image."},
    {"id": "registration", "title": "Locate the carton", "description": "Fit its pose from the known carton texture and check the table reference."},
    {"id": "planning", "title": "Plan both arms", "description": "Compute and check the high approach and open entry from measured joints."},
    {"id": "motion_review", "title": "Review the approach", "description": "Review the current paths in UWA Robot Power before real motion."},
    {"id": "wrist", "title": "Inspect the grasp alignment", "description": "Measure the visible carton rim in archived wrist-camera images. Real contact uses a fresh OAK4 entry photo."},
    {"id": "contact_review", "title": "Close and hold", "description": "Review the actual entry before closing both grippers on the supported carton."},
]


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def now():
    return datetime.now(timezone.utc).isoformat()


def process_stamp(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return None
    return fields[19] if len(fields) > 19 and fields[0] not in {"Z", "X"} else None


class Runs:
    def __init__(self, directory, live_config=None):
        self.directory = directory
        self.live_config = live_config
        self.directory.mkdir(parents=True, exist_ok=True)

    def live_blocker(self):
        try:
            configured = self.live_config is not None and read_json(self.live_config).get("enabled") is True
        except (OSError, ValueError, AttributeError):
            return "The local live configuration could not be read."
        return None if configured else "The N100 and OAK live configuration has not been enabled on this workstation."

    def catalog(self):
        blocker = self.live_blocker()
        program = dict(id=PROGRAM_ID, title="Supported carton grasp",
                       description="Both right arms grasp the known Avocado carton at its measured pose and hold it on the table.",
                       object="Avocado carton", arms=["Right front", "Right rear"], stages=STAGES,
                       demo_available=True, live_available=blocker is None, live_blocker=blocker)
        latest = max((path for path in self.directory.glob("*/run.json") if RUN_ID.fullmatch(path.parent.name)),
                     key=lambda path: path.stat().st_mtime, default=None)
        return dict(programs=[program], active_run=self.get(latest.parent.name) if latest else None)

    def get(self, identifier):
        if RUN_ID.fullmatch(identifier) is None:
            return None
        output = self.directory / identifier
        metadata = read_json(output / "run.json")
        if not metadata:
            return None
        progress = read_json(output / "progress.json")
        exit_record = read_json(output / "exit.json")
        pid, stamp = metadata["pid"], metadata["stamp"]
        running = not exit_record and stamp is not None and process_stamp(pid) == stamp
        failure = progress.get("error")
        result = progress.get("result")
        if running:
            state = "running"
        elif exit_record.get("code") == 0 or (not exit_record and result is not None and not failure):
            state = "succeeded"
        else:
            state = "failed"
            failure = failure or "The program stopped before completing. Inspect run.log and the recorded phase."
        record = {key: metadata[key] for key in ("id", "program", "mode", "started_at")}
        record.update(state=state, phase=progress.get("phase", "starting"),
                      message=failure or progress.get("message", "Starting the program runner."),
                      events=progress.get("events", []))
        if exit_record:
            record["finished_at"] = exit_record["at"]
        if result is not None:
            record["result"] = result
        return record

    def preview(self, identifier, key):
        run = self.get(identifier)
        if not run or key not in PREVIEWS:
            return None
        artifact = run.get("result", {}).get("artifacts", {}).get(key)
        if artifact:
            directory = (self.directory / identifier).resolve()
            path = (directory / artifact).resolve()
            if path.is_relative_to(directory) and path.suffix == ".jpg" and path.is_file():
                return path.read_bytes()
        return None

    @staticmethod
    def record_exit(process, directory):
        code = process.wait()
        write_json(directory / "exit.json", dict(code=code, at=now()))

    def start(self, program, mode):
        if program != PROGRAM_ID or mode not in ("demo", "live"):
            raise ValueError("Choose a program and execution mode from the library.")
        if mode == "live" and (blocker := self.live_blocker()):
            raise ValueError(blocker)
        with (self.directory / ".run.lock").open("a") as lease:
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("Another library run is already active.") from error
            identifier = uuid4().hex
            output = self.directory / identifier
            output.mkdir()
            command = [sys.executable, str(ROOT / "tools/run_carton_program.py"),
                       "--program", program, "--mode", mode, "--output", str(output)]
            if mode == "live":
                command.extend(["--live-config", str(self.live_config)])
            started_at = now()
            with (output / "run.log").open("wb") as log:
                # The runner keeps the lease even if the browser or server closes.
                process = subprocess.Popen(command, cwd=WORKSPACE, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True, pass_fds=(lease.fileno(),))
            write_json(output / "run.json", dict(id=identifier, mode=mode, program=program, started_at=started_at,
                                                 pid=process.pid, stamp=process_stamp(process.pid)))
            Thread(target=self.record_exit, args=(process, output), daemon=True).start()
        return self.get(identifier)


class Handler(BaseHTTPRequestHandler):
    server_version = "UWAProgramLibrary"

    def response(self, code, body, media):
        self.send_response(code)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def json(self, code, payload):
        self.response(code, json.dumps(payload, allow_nan=False).encode(), "application/json; charset=utf-8")

    @property
    def host(self):
        return f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if self.headers.get("Host") != self.host:
            self.json(403, {"error": "Open the assigned loopback address."})
        elif self.path == "/api/catalog":
            self.json(200, self.server.runs.catalog())
        elif self.path.startswith("/api/runs/"):
            identifier, separator, key = self.path.removeprefix("/api/runs/").partition("/artifacts/")
            if separator:
                body = self.server.runs.preview(identifier, key)
                if body is None:
                    self.json(404, {"error": "Preview not found."})
                else:
                    self.response(200, body, "image/jpeg")
            else:
                run = self.server.runs.get(identifier)
                if run:
                    self.json(200, run)
                else:
                    self.json(404, {"error": "Run not found."})
        elif self.path in STATIC and STATIC[self.path][0].is_file():
            path, media = STATIC[self.path]
            self.response(200, path.read_bytes(), media)
        else:
            self.json(404, {"error": "Page not found."})

    def do_POST(self):
        if self.headers.get("Host") != self.host or self.headers.get("Origin") != f"http://{self.host}":
            self.json(403, {"error": "Start programs from the local library page."})
            return
        if self.path != "/api/runs":
            self.json(404, {"error": "Page not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 or self.headers.get_content_type() != "application/json":
                raise ValueError("Expected a JSON program and mode.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) != {"program", "mode"}:
                raise ValueError("Expected a program and execution mode.")
            run = self.server.runs.start(payload["program"], payload["mode"])
        except ValueError as error:
            self.json(400, {"error": str(error)})
        except RuntimeError as error:
            self.json(409, {"error": str(error)})
        except OSError as error:
            self.json(500, {"error": f"Could not start the program runner. {error.strerror}"})
        else:
            self.json(202, run)

    def log_request(self, code="-", size="-"):
        if str(code) not in {"200", "202"}:
            super().log_request(code, size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8780, help="Loopback port. 0 selects a free port.")
    parser.add_argument("--runs", type=Path, default=WORKSPACE / "setup/tasks/uwa_program_library")
    parser.add_argument("--live-config", type=Path)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        server.runs = Runs(args.runs.resolve(), args.live_config.resolve() if args.live_config else None)
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

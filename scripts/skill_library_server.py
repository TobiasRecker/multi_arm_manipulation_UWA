#!/usr/bin/env python3
"""Serve the UWA program library on the workstation's loopback interface."""

import argparse
from datetime import datetime, timezone
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from threading import Thread
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from carton_camera_session import validate_session
from run_carton_program import live_inputs, CAMERA_PROGRAM
from run_multi_camera_program import PROGRAM as MULTI_CAMERA_PROGRAM
from run_pen_program import PROGRAM as PEN_PROGRAM, availability as pen_availability
from run_return_home import PROGRAM as HOME_PROGRAM, catalog as home_catalog, validate_request as home_request
from object_scan_library import Scans, catalog as scan_catalog

WORKSPACE = ROOT.parents[1]
PROGRAM_ID = "carton-supported-v1"
RUN_ID = re.compile(r"[a-f0-9]{32}")
PREVIEWS = {"oak_preview", "right_front_preview", "right_rear_preview", "camera_preview",
            "usb_preview", "cross_view_preview", "pen_preview"}
STATIC = {
    "/": (ROOT / "scripts/skill_library/index.html", "text/html; charset=utf-8"),
    "/index.html": (ROOT / "scripts/skill_library/index.html", "text/html; charset=utf-8"),
    "/styles.css": (ROOT / "scripts/skill_library/styles.css", "text/css; charset=utf-8"),
    "/app.js": (ROOT / "scripts/skill_library/app.js", "text/javascript; charset=utf-8"),
    "/object-scan.js": (ROOT / "scripts/skill_library/object-scan.js", "text/javascript; charset=utf-8"),
    "/scan-textures.js": (ROOT / "scripts/skill_library/scan-textures.js", "text/javascript; charset=utf-8"),
    "/assets/carton.png": (ROOT / "output/images/carton_in_virtual_cell.png", "image/png"),
}
STAGES = [
    {"id": "snapshot", "title": "Read the robot state", "description": "Read the joints and grippers on the N100 and check readiness on ROSmini."},
    {"id": "capture", "title": "Capture the scene", "description": "Acquire current native OAK4 and OAK Pro images when both references are available. Keep the carton still."},
    {"id": "registration", "title": "Locate the carton", "description": "Average agreeing accepted camera poses, or use one strict fit with a second-view presence/occlusion check."},
    {"id": "planning", "title": "Plan both arms", "description": "Compute and check the high approach and open entry on ROSmini."},
    {"id": "motion_review", "title": "Review the approach", "description": "Review the current paths in UWA Robot Power before real motion."},
    {"id": "wrist", "title": "Inspect the grasp alignment", "description": "Measure the visible carton rim in archived wrist-camera images. Real contact uses a fresh OAK4 entry photo."},
    {"id": "contact_review", "title": "Close and hold", "description": "Review the actual entry before closing both grippers on the supported carton."},
]
CAMERA_STAGES = [
    {"id": "oak_calibration", "title": "Find and capture the boards",
     "description": "Search focus and exposure, then capture native OAK4 board images. Keep the camera and boards still."},
    {"id": "camera_reference", "title": "Determine the camera pose",
     "description": "Use the right table board and matching focus intrinsics to determine the camera reference."},
    {"id": "camera_publish", "title": "Share the reference for 12 hours",
     "description": "Save the checked reference for other programs. Recalibrate after moving the camera or board."},
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
        self.scans = Scans(self.directory / 'object-scans', self.directory)

    def camera_status(self):
        try:
            config = live_inputs(self.live_config)
        except (OSError, ValueError, KeyError, TypeError) as error:
            return {"calibrate_available": False, "live_blocker": str(error)}
        path = config.get("camera_session")
        if path is None:
            return {"calibrate_available": False, "live_blocker": None}
        if not path.is_file():
            return {"calibrate_available": True, "live_blocker": "Calibrate the OAK4 before starting the carton program."}
        try:
            session = validate_session(read_json(path), config["intrinsics"])
        except (OSError, ValueError, KeyError, TypeError):
            return {"calibrate_available": True, "live_blocker": "The OAK4 camera reference expired or is invalid. Recalibrate the camera."}
        result = {"calibrate_available": True, "live_blocker": None,
                  "camera_valid_from": session["valid_from"], "camera_valid_until": session["valid_until"]}
        if secondary := config.get('secondary_camera'):
            try:
                usb = validate_session(read_json(secondary['camera_session']), secondary['intrinsics'])
                result['secondary_camera'] = dict(status='valid', valid_until=usb['valid_until'])
            except (OSError, ValueError, KeyError, TypeError):
                result['secondary_camera'] = dict(status='unavailable',
                    reason='OAK Pro reference required. Start camera calibration to measure both cameras; strict OAK4 fallback remains available.')
        return result

    def catalog(self):
        camera = self.camera_status()
        try:
            selected_config=read_json(self.live_config)
            weigh = selected_config.get('weigh_after_grasp') is True
            air=selected_config.get('air_demo_after_grasp')is True
        except (OSError, ValueError, TypeError, AttributeError):
            weigh = False
            air = False
        stages = [dict(s) for s in STAGES]
        if weigh:
            stages[3]['description'] = 'Check the complete high approach, open entry and joint20mm lift before any motion. The weighing variant grasps20mm higher.'
            stages[-1].update(title='Reference, grasp and lift',description='Review the actual entry, save unloaded wrist forces, close both grippers and execute the reviewed joint20mm lift.')
            stages.append(dict(id='weigh',title='Estimate mass and load sharing',description='Compare finite force measurements before closing and after lifting. Show both arm shares and measurement limits; hold the lifted carton.'))
        program = dict(id=PROGRAM_ID, title="Supported carton grasp",
                       description=('Both right arms grasp the carton20mm higher, lift it20mm together and estimate its mass from wrist forces.' if weigh else
                           "Both right arms grasp the known Avocado carton at its measured pose and hold it on the table."),
                       object="Avocado carton", arms=["Right front", "Right rear"], stages=stages,
                       demo_available=True, live_available=camera["live_blocker"] is None, **camera)
        if air:
            program.update(title='Carton grasp and drawing air trial',
                description='Use the rehearsed grasp, weigh the empty carton, then carry out the house, circles and six virtual drilling cycles with an empty worker gripper.',
                arms=['Right front','Right rear','Left front','Left rear'])
            stages[3]['description']='Check the complete new acquisition and air trial before any approach. Reuse unchanged qualified paths.'
            stages.append(dict(id='air_demo',title='Drawing trial without a tool',
                description='Review the complete carry and turning sequence. Left front follows the virtual tool reference with an empty gripper; left rear parks. No pen pickup or material processing.'))
        program['camera_program'] = CAMERA_PROGRAM
        calibration = dict(id=CAMERA_PROGRAM, kind="camera_calibration", title="OAK camera calibration",
            description="Measure separate OAK4 and configured OAK Pro references from the right table board. Each reference lasts 12 hours from its own capture.",
            object="Right table ChArUco board", arms=[], device="Ethernet OAK4 · N100 OAK Pro", stages=CAMERA_STAGES,
            demo_available=False, live_available=False, **camera)
        latest = max((path for path in self.directory.glob("*/run.json") if RUN_ID.fullmatch(path.parent.name)),
                     key=lambda path: path.stat().st_mtime, default=None)
        multi_camera = dict(id=MULTI_CAMERA_PROGRAM, kind='multi_camera_capture', title='Multi-camera calibration capture',
            description='Prepare the four wrist-camera observation poses, then record the mobile ChArUco board with four wrists and both OAK cameras.',
            object='Mobile A4 ChArUco board', arms=['Left front', 'Left rear', 'Right front', 'Right rear'],
            device='Four wrists · Ethernet OAK4 · N100 USB OAK', setup_available=self.live_config is not None,
            gui_available=True, demo_available=False, live_available=False,
            stages=[dict(id='snapshot', title='Read the current start', description='Use fresh N100 joint states. Prepare unloaded arms and release the work area in UWA Robot Power first.'),
                dict(id='planning', title='Plan and check the approach', description='Plan new paths to the saved observation goals on ROSmini. Task command cap: 0.09 rad/s.'),
                dict(id='positioning', title='Position the four arms', description='Move left front, left rear, right front and right rear in sequence with the existing N100 protection.'),
                dict(id='capture_gui', title='Record six-camera board views', description='Open or reuse UWA Camera Capture. Hold the mobile board still for each CAPTURE ALL SIX; solve the calibration separately.')])
        pen = dict(id=PEN_PROGRAM, kind='pen_grasp', title='Pick pen from holder',
            description='Locate the two 30 mm markers with OAK Pro/OpenCV, use Gemini as a fallback, then plan the left rear arm to grasp and lift the pen.',
            object='COS pen and keyed holder', arms=['Left rear'], device='N100 OAK Pro',
            demo_available=False, camera_program=CAMERA_PROGRAM,
            stages=[dict(id='snapshot', title='Read the current start', description='Use the current N100 four-arm model and released work area.'),
                dict(id='capture', title='Capture the pen', description='Acquire a fresh native OAK Pro image; keep the pen fully seated.'),
                dict(id='registration', title='Locate both markers', description='Measure ID 97 on top and ID 96 on the side. Gemini may suggest a crop; OpenCV determines the metric pose.'),
                dict(id='planning', title='Plan the complete pickup', description='Check approach, vertical entry and carried-pen lift against the full cell, CAD adapter and holder.'),
                dict(id='motion_review', title='Review and enter', description='Review the new left-rear motion in UWA Robot Power. Open the gripper at the pregrasp pose, then enter vertically.'),
                dict(id='contact_review', title='Inspect, grasp and lift', description='Review a fresh open-entry photo, then close the left-rear gripper, lift vertically and hold.')],
            **pen_availability(self.live_config is not None))
        home = home_catalog(self.directory, self.live_config is not None)
        return dict(programs=[calibration, multi_camera, program, pen, home, scan_catalog()],
                    camera_reference=dict(status="valid" if camera.get('camera_valid_until') else "required",
                        valid_from=camera.get('camera_valid_from'), valid_until=camera.get('camera_valid_until'),
                        program=CAMERA_PROGRAM),
                    active_run=self.get(latest.parent.name) if latest else None)

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
        decision = read_json(output/'multiview/decision.json')
        if decision:
            record['perception'] = decision
            artifacts = record.setdefault('result', {}).setdefault('artifacts', {})
            for key, relative in (('usb_preview', 'oak-usb/initial-photo/native/preview.jpg'),
                                   ('cross_view_preview', 'multiview/verification-overlay.jpg')):
                if (output/relative).is_file():
                    artifacts[key] = relative
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

    def start(self, program, mode, options=None):
        allowed = {PROGRAM_ID: {"demo", "live", "calibrate"}, CAMERA_PROGRAM: {"calibrate"},
                   MULTI_CAMERA_PROGRAM: {'setup', 'gui'}, PEN_PROGRAM: {'inspect', 'plan', 'live'},
                   HOME_PROGRAM: {'demo', 'plan', 'live'}}
        if not isinstance(program, str) or not isinstance(mode, str) or program not in allowed or mode not in allowed[program]:
            raise ValueError("Choose a program and execution mode from the library.")
        if program == HOME_PROGRAM and mode != 'demo':
            if self.live_config is None:
                raise ValueError("Open the N100-enabled UWA Robot Power Library.")
            options = home_request(options)
        elif options is not None:
            raise ValueError("This program mode takes no scene options.")
        with (self.directory / ".run.lock").open("a") as lease:
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("Another library run is already active.") from error
            if program == MULTI_CAMERA_PROGRAM and mode == 'setup' and self.live_config is None:
                raise ValueError('Start the N100-enabled UWA Robot Power library to prepare the real arms.')
            if program == PEN_PROGRAM:
                status = pen_availability(self.live_config is not None)
                if not status[mode+'_available']:
                    raise ValueError(status['live_blocker'])
            if mode in {'live', 'calibrate'} and program not in (PEN_PROGRAM, HOME_PROGRAM):
                camera = self.camera_status()
                if mode == "live" and camera["live_blocker"]:
                    raise ValueError(camera["live_blocker"])
                if mode == "calibrate" and not camera["calibrate_available"]:
                    raise ValueError("The separate OAK4 calibration is not configured on this workstation.")
            identifier = uuid4().hex
            output = self.directory / identifier
            output.mkdir()
            if program == HOME_PROGRAM:
                command = [sys.executable, str(ROOT / 'tools/run_return_home.py'), '--mode', mode,
                           '--output', str(output), '--runs', str(self.directory)]
                if options is not None:
                    path = output / "operator-request.json"
                    write_json(path, options)
                    command.extend(['--request', str(path)])
            elif program == PEN_PROGRAM:
                command = [sys.executable, str(ROOT / 'tools/run_pen_program.py'),
                           '--mode', mode, '--output', str(output)]
            elif program == MULTI_CAMERA_PROGRAM:
                command = [sys.executable, str(ROOT / 'tools/run_multi_camera_program.py'),
                           '--mode', mode, '--output', str(output)]
            else:
                command = [sys.executable, str(ROOT / "tools/run_carton_program.py"),
                           "--program", program, "--mode", mode, "--output", str(output)]
            if mode in {'live', 'calibrate'} or (program == PEN_PROGRAM and mode == 'plan'):
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

    def headers_for(self, code, length, media):
        self.send_response(code)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()

    def response(self, code, body, media):
        self.headers_for(code, len(body), media)
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
        elif self.path == '/api/assets':
            self.json(200, {'assets': self.server.runs.scans.assets()})
        elif self.path == '/api/scans':
            self.json(200, {'scans': self.server.runs.scans.list()})
        elif self.path.startswith('/api/scans/'):
            self.scan_get()
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

    def scan_get(self):
        identifier, separator, key = self.path.removeprefix('/api/scans/').partition('/files/')
        scans = self.server.runs.scans
        try:
            if separator:
                path, media = scans.artifact(identifier, key)
                source = path.open('rb')
            else:
                self.json(200, scans.get(identifier))
                return
        except FileNotFoundError:
            self.json(404, {'error': 'Scan or scan file not found.'})
            return
        with source:
            self.headers_for(200, path.stat().st_size, media)
            shutil.copyfileobj(source, self.wfile, length=262144)

    def do_POST(self):
        if self.headers.get("Host") != self.host or self.headers.get("Origin") != f"http://{self.host}":
            self.json(403, {"error": "Start programs from the local library page."})
            return
        is_scan = self.path == '/api/scans' or self.path.startswith('/api/scans/')
        if self.path != "/api/runs" and not is_scan:
            self.json(404, {"error": "Page not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192 or self.headers.get_content_type() != "application/json":
                raise ValueError("Expected a JSON request of at most 8192 bytes.")
            payload = json.loads(self.rfile.read(length))
            if is_scan:
                self.scan_post(payload)
                return
            if (not isinstance(payload, dict) or set(payload) not in
                    ({"program", "mode"}, {"program", "mode", "options"})):
                raise ValueError("Expected a program and execution mode.")
            run = self.server.runs.start(payload["program"], payload["mode"], payload.get("options"))
        except ValueError as error:
            self.json(400, {"error": str(error)})
        except RuntimeError as error:
            self.json(409, {"error": str(error)})
        except OSError as error:
            self.json(500, {"error": f"Could not start the program runner. {error.strerror}"})
        else:
            self.json(202, run)

    def scan_post(self, payload):
        scans = self.server.runs.scans
        if self.path == '/api/scans':
            self.json(201, scans.create(payload))
            return
        identifier, separator, action = self.path.removeprefix('/api/scans/').partition('/')
        try:
            if not separator:
                raise FileNotFoundError
            asynchronous, scan = scans.action(identifier, action, payload)
        except FileNotFoundError:
            self.json(404, {'error': 'Scan or scan action not found.'})
        else:
            self.json(202 if asynchronous else 200, scan)

    def log_request(self, code="-", size="-"):
        if str(code) not in {"200", "201", "202"}:
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

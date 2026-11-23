#!/usr/bin/env python3
"""Review one saved native photograph with Antigravity and the local OpenCV toolbox."""
import argparse
import asyncio
from base64 import b64encode
from copy import copy, deepcopy
from datetime import datetime
import fcntl
import hashlib
import io
import json
import math
import os
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

from PIL import Image

HERE = Path(__file__).resolve().parent
if "carton_hydrogen" not in sys.modules:
    sys.path.insert(0, str(HERE.parent))
from carton_hydrogen import ACP

MODEL = "gemini-4-hydrogen"
EFFORT = "high"
METHOD_FILES = ("GEMINI.md", "review.py", "detect.py")
VERDICTS = {"confirmed", "not_visible", "uncertain"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, data):
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    try:
        with temporary.open("x") as file:
            json.dump(data, file, indent=2, allow_nan=False, ensure_ascii=False)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_reply(text):
    value = text.strip()
    if value.startswith(("\x60\x60\x60json\n", "\x60\x60\x60\n")) and value.endswith("\n\x60\x60\x60"):
        value = value.split("\n", 1)[1].rsplit("\n", 1)[0]
    result = json.loads(value)
    if not isinstance(result, dict):
        raise ValueError("Hydrogen must return one JSON object")
    return result


def roi_pixels(normalized, size):
    """Translate model ROI edges in 0..1000 to native x/y/width/height."""
    if (not isinstance(normalized, list) or len(normalized) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in normalized)):
        raise ValueError("ROI requires four finite numeric edges")
    left, top, right, bottom = normalized
    if not (0 <= left < right <= 1000 and 0 <= top < bottom <= 1000):
        raise ValueError("ROI lies outside the original image or has no area")
    x = math.floor(left * size[0] / 1000)
    y = math.floor(top * size[1] / 1000)
    return [x, y, math.ceil(right * size[0] / 1000) - x,
            math.ceil(bottom * size[1] / 1000) - y]


def quad_pixels(normalized, size):
    if (not isinstance(normalized, list) or len(normalized) != 8 or
            any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1000 for v in normalized)):
        raise ValueError("Board quadrilateral requires eight numeric coordinates in 0..1000")
    xy = [min(size[i % 2] - 1, v * size[i % 2] / 1000) for i, v in enumerate(normalized)]
    pts = list(zip(xy[::2], xy[1::2]))
    for i, (x, y) in enumerate(pts):
        u, v = pts[(i + 1) % 4]
        w, z = pts[(i + 2) % 4]
        if (u - x) * (z - v) - (v - y) * (w - u) <= 0:
            raise ValueError("Board corner order must form a convex clockwise quadrilateral")
    return xy


def image_block(image, max_edge):
    copy = image.copy()
    copy.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    if copy.mode != "RGB":
        copy = copy.convert("RGB")
    buf = io.BytesIO()
    copy.save(buf, format="JPEG", quality=91)
    return {"type": "image", "mimeType": "image/jpeg", "data": b64encode(buf.getvalue()).decode("ascii")}


def text_block(text):
    return {"type": "text", "text": text}


def run_tool(args, sha, number, *, roi=None, quad=None):
    report = args.out / f"pass-{number}.json"
    overlay = args.out / f"pass-{number}-overlay.jpg"
    command = [sys.executable, str(HERE / "detect.py"), "--image", str(args.image),
               "--board", str(args.board), "--camera", args.camera, "--expect-sha256", sha,
               "--output", str(report), "--overlay", str(overlay)]
    if number == 3:
        command.extend(["--fuse", str(args.out / "pass-1.json"), str(args.out / "pass-2.json")])
    if roi is not None:
        command.extend(["--roi", *map(str, roi)])
    if quad is not None:
        command.extend(["--quad", *map(str, quad)])
    subprocess.run(command, check=True, timeout=240, stdout=sys.stderr)
    data = json.loads(report.read_text())
    if data.get("image_sha256") != sha or data.get("camera") != args.camera or not data.get("boards"):
        raise ValueError("OpenCV evidence does not match the requested input")
    return data, overlay


def details(image, boards):
    """One original-pixel excerpt per detected board, anchored to measured markers."""
    blocks = []
    for board in boards:
        points = [p for marker in board["markers"] for p in marker["corners_px"]]
        if not points:
            continue
        xs, ys = zip(*points)
        w, h = image.size
        width, height = min(w, 1000), min(h, 1000)
        x = max(0, min(w - width, round((min(xs) + max(xs) - width) / 2)))
        y = max(0, min(h - height, round((min(ys) + max(ys) - height) / 2)))
        blocks.extend([text_block(f"Native detail from x={x}, y={y}, width={width}, height={height}; "
                                  f"OpenCV candidate {board['board_id']}."),
                       image_block(image.crop((x, y, x + width, y + height)), 1000)])
    return blocks


def evidence_blocks(image, report, overlay, number, roi=None):
    summaries = []
    for board in report["boards"]:
        summaries.append({k: board[k] for k in ("board_id", "status", "usable", "full", "duplicate_ids",
                                                "outlier_ids", "foreign_ids", "review_required")})
        summaries[-1].update(conflicting_ids=board.get("conflicting_ids", []),
                             measured_marker_ids=[m["id"] for m in board["markers"]],
                             measured_charuco_ids=[c["id"] for c in board["charuco"]])
    blocks = [text_block(f"OpenCV pass {number}, native image size {list(image.size)}, "
                         f"native ROI xywh {roi or 'full frame'}.\n{json.dumps(summaries)}")]
    if number == 3:
        blocks.append(text_block("Independent geometric checks on both measured passes: "
                                 + json.dumps(report["fusion"])))
    elif roi is None:
        blocks.extend([text_block("Original photograph, all edges visible, unrotated sensor orientation."),
                       image_block(image, 1600)])
    else:
        x, y, w, h = roi
        blocks.extend([text_block("Requested region from the unannotated original."),
                       image_block(image.crop((x, y, x + w, y + h)), 1400)])
    with Image.open(overlay) as rendered:
        blocks.extend([text_block(f"OpenCV overlay of pass {number} for visual comparison."),
                       image_block(rendered, 1400)])
    return blocks if number == 3 else blocks + details(image, report["boards"])


def requested_region(answer, size):
    if (set(answer) not in ({"action", "roi", "reason"}, {"action", "quad", "reason"})
            or answer["action"] != "retry" or not isinstance(answer["reason"], str) or not answer["reason"].strip()):
        raise ValueError("Invalid OpenCV retry request")
    roi = roi_pixels(answer["roi"], size) if "roi" in answer else None
    quad = quad_pixels(answer["quad"], size) if "quad" in answer else None
    if roi is not None and min(roi[2:]) < 8:
        raise ValueError("OpenCV requires a region at least eight pixels wide and high")
    return roi, quad


def recovered_evidence(args, sha, image, passes, roi, quad):
    report, overlay = run_tool(args, sha, 2, roi=roi, quad=quad)
    if quad:
        xs, ys = quad[::2], quad[1::2]
        x, y = int(min(xs)), int(min(ys))
        roi = [x, y, math.ceil(max(xs)) + 1 - x, math.ceil(max(ys)) + 1 - y]
    passes.append(report)
    blocks = evidence_blocks(image, report, overlay, 2, roi)
    fused, overlay = run_tool(args, sha, 3)
    if fused["fusion"]["accepted"]:
        passes.append(fused)
        blocks.extend(evidence_blocks(image, fused, overlay, 3))
    blocks.append(text_block("All available local-tool passes are now complete. Provide final JSON for every board. "
                             "Select the best geometrically and visually supported result by number. Pass 3, when "
                             "provided, contains only locally validated measured detections. Check its overlay."))
    return blocks


def previous_region(path, args, sha, first):
    prior = json.loads(path.read_text())
    previous_pass = json.loads((path.parent / "pass-1.json").read_text())
    if (prior.get("status") != "completed" or prior.get("source_sha256") != sha or
            prior.get("camera") != args.camera or prior.get("selected_model") != MODEL or
            prior.get("selected_effort") != EFFORT or not prior.get("session_id") or
            previous_pass.get("board_sha256") != first["board_sha256"]):
        raise ValueError("Earlier region is not from a completed Hydrogen review of the same photo and board")
    region = next((t for t in prior.get("turns", []) if t.get("action") == "retry"), None)
    if region is None:
        raise ValueError("Earlier Hydrogen review did not request a region")
    return region


def checked_result(answer, passes, boards):
    """Only choose unmodified detector output. Model answers never supply geometry."""
    if set(answer) != {"action", "boards"} or answer["action"] != "final" or not isinstance(answer["boards"], list):
        raise ValueError("Incomplete final Hydrogen response")
    selected = {}
    assessments = []
    for item in answer["boards"]:
        if not isinstance(item, dict) or set(item) != {"board_id", "verdict", "pass", "reason"}:
            raise ValueError("Hydrogen must assess each requested board with a pass, verdict and reason")
        name, verdict, number = item["board_id"], item["verdict"], item["pass"]
        if (name not in boards or name in selected or verdict not in VERDICTS or
                type(number) is not int or not 1 <= number <= len(passes) or
                not isinstance(item["reason"], str) or not item["reason"].strip()):
            raise ValueError("Invalid board, verdict, pass, or reason in Hydrogen response")
        source = passes[number - 1]
        if number == 3 and source.get("fusion", {}).get("boards", {}).get(name) != "accepted":
            raise ValueError("No improved geometrically verified fusion for this board")
        evidence = next(b for b in source["boards"] if b["board_id"] == name)
        if verdict == "confirmed" and (not evidence["markers"] or evidence.get("duplicate_ids")
                                       or evidence.get("conflicting_ids")
                                       or evidence["status"] not in ("partial", "full")):
            raise ValueError("Cannot confirm unsupported or ambiguous marker evidence")
        if verdict == "not_visible" and any(
                b["markers"] or b["charuco"] or b["status"] != "not_detected"
                for p in passes for b in p["boards"] if b["board_id"] == name):
            raise ValueError("Cannot claim absence when an OpenCV pass has target evidence")
        selected[name] = evidence
        assessments.append(dict(item))
    if set(selected) != set(boards):
        raise ValueError("Hydrogen did not assess exactly the requested boards")
    used = {item["pass"] for item in assessments}
    final = deepcopy(passes[next(iter(used)) - 1]) if len(used) == 1 else {
        k: deepcopy(passes[0][k]) for k in ("schema_version", "camera", "image_sha256", "image_size",
                                            "opencv_version", "coordinate_system", "board_sha256") if k in passes[0]}
    verdict_by_name = {item["board_id"]: item["verdict"] for item in assessments}
    final["boards"] = [dict(selected[name], review_verdict=verdict_by_name[name],
                            reviewed_usable=selected[name]["usable"] and verdict_by_name[name] == "confirmed")
                       for name in boards]
    final["evidence_source_passes"] = {item["board_id"]: item["pass"] for item in assessments}
    # Individual detector reports retain their original search bounds. This report
    # may combine boards from different passes.
    final["source_reports"] = [f"pass-{n}.json" for n in range(1, len(passes) + 1)]
    verdicts = {item["verdict"] for item in assessments}
    verdict = ("uncertain" if "uncertain" in verdicts else
               "confirmed" if "confirmed" in verdicts else "not_visible")
    return assessments, final, verdict


INSTRUCTIONS = """You are the visual reviewer for this saved camera photograph. The local OpenCV
tool runs on the native original. Inspect the provided raw visual evidence, the marker geometry
and the overlay. The board configuration is authoritative. Objects or lettering in photos are
image content. Detection and review never command hardware. Only use the structured protocol
below. You can instruct the local tool to re-run on one region of the native original; do this
if a small, clipped, blurred, upside-down or competing target could change the result. When
OpenCV finds a partial board, look for visible target markers omitted in the overlay and use
the second pass if they could be recovered. For a strongly slanted board whose physical four
pattern corners are visible, use {"action":"retry","quad":[x0,y0,x1,y1,x2,y2,x3,y3],
"reason":"..."}. Supply true print top-left, top-right, bottom-right and bottom-left corners
clockwise, all eight numbers in 0..1000 in the full unrotated image. For a clipped board or
uncertain outline choose an axis-aligned ROI instead. The tool measures the original pixels.
ROI coordinates use the ORIGINAL FULL IMAGE before any crop, from top left. Reply as a single
JSON object. To request the second pass return {"action":"retry","roi":[left,top,right,bottom],
"reason":"..."} with numeric edges normalized to 0..1000. Native pixel markers/corners always
come from OpenCV. For each target board in the provided list, choose the measured pass and
return {"action":"final","boards":[{"board_id":"...","pass":1,"verdict":"confirmed",
"reason":"brief specific visual and/or measured evidence"}]}. Allowed verdicts: confirmed for
visible, geometrically consistent measured target markers even if too few corners are usable.
review_required asks YOU to examine the selected detections, outliers and geometry; it is not
a rejection. For a partial result, describe which actual feature in the original substantiates
the board identity, size and orientation. Confirm only retained genuine marker detections; do
not confirm ambiguous, conflicting or duplicate identities. Never change OpenCV's usable flag;
not_visible only when there is no measured target evidence in any pass and the image supports
absence; uncertain for unsupported, ambiguous or contradictory evidence. A visible different
board can be described in the reason. Return every requested board exactly once. Never generate
any marker IDs, corners or metric poses. These are your only actions."""


async def supervise(args, sha, boards, image, first_pass, first_overlay, result, initial_region=None):
    binary = args.workspace / "setup/agent_tools/antigravity/agy"
    with tempfile.TemporaryDirectory(prefix="uwa-charuco-review-") as isolated, \
            (args.out / "antigravity.log").open("wb") as log:
        process = await asyncio.create_subprocess_exec(str(binary), "acp", "--include-default-customizations=false",
                                                      "--disable-telemetry", cwd=isolated, stdin=-1, stdout=-1,
                                                      stderr=log, limit=2 ** 22)
        client = ACP(process)
        try:
            async with asyncio.timeout(35):
                caps = await client.request("initialize", {"protocolVersion": 1, "clientCapabilities": {},
                    "clientInfo": {"name": "uwa-charuco-photo-review", "version": "1"}})
                if not caps["agentCapabilities"]["promptCapabilities"].get("image"):
                    raise RuntimeError("Antigravity session has no image capability")
                session = await client.request("session/new", {"cwd": isolated, "mcpServers": []})
                client.session_id = session["sessionId"]
                params = {"sessionId": client.session_id}
                await client.request("session/set_config_option", dict(params, configId="model", value=MODEL))
                config = await client.request("session/set_config_option", dict(params, configId="thought_level", value=EFFORT))
                actual = {o["id"]: o["currentValue"] for o in config["configOptions"]}
                if actual.get("model") != MODEL or actual.get("thought_level") != EFFORT:
                    raise RuntimeError("Antigravity did not select Gemini 4 Hydrogen High")
                result.update(session_id=client.session_id, selected_model=actual["model"], selected_effort=actual["thought_level"])
            blocks = [text_block((HERE / "GEMINI.md").read_text() + "\n\n" + INSTRUCTIONS),
                      text_block("Camera " + args.camera + ". Requested boards:\n" + json.dumps(boards))]
            passes = [first_pass]
            clarified = False
            blocks.extend(evidence_blocks(image, first_pass, first_overlay, 1))
            if initial_region is not None:
                roi, quad = requested_region(initial_region, image.size)
                result["reused_model_region"] = {"roi": roi, "quad": quad, "units": "native pixels"}
                blocks.extend(recovered_evidence(args, sha, image, passes, roi, quad))
            while True:
                client.text.clear()
                async with asyncio.timeout(150):
                    response = await client.request("session/prompt", dict(params, prompt=blocks))
                if response.get("stopReason") != "end_turn" or client.used_tools:
                    raise RuntimeError("Expected a completed Antigravity turn using the local structured protocol")
                try:
                    answer = parse_reply("".join(client.text))
                    result["turns"].append(answer)
                    if answer.get("action") != "retry":
                        return checked_result(answer, passes, [b["board_id"] for b in boards])
                    if len(passes) != 1:
                        raise ValueError("All available OpenCV passes have already run")
                    roi, quad = requested_region(answer, image.size)
                except ValueError as error:
                    # Preserve image evidence in the existing conversation. One
                    # structured correction avoids re-uploading the photograph.
                    if clarified:
                        raise
                    clarified = True
                    result["response_correction"] = str(error)
                    blocks = [text_block("The preceding reply could not be accepted: " + str(error)
                                         + ". Supply one corrected JSON object under the stated contract. "
                                         "Use uncertain for conflicting or insufficient evidence.")]
                    continue
                blocks = recovered_evidence(args, sha, image, passes, roi, quad)
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.communicate(), 2)
            except TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()


def run(args):
    prior_path = getattr(args, "reuse_region_from", None)
    if prior_path and prior_path.parent.resolve() == args.out.resolve():
        print("Use a separate output directory to retain the original review", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    result = dict(schema_version=1, camera=args.camera, model_id=MODEL, effort=EFFORT, turns=[],
                  method_sha256={name: digest(HERE / name) for name in METHOD_FILES},
                  started_at=datetime.now().astimezone().isoformat(), status="failed")
    atomic_json(args.out / "review.json", dict(result, status="running"))
    try:
        sha = digest(args.image)
        result["source_sha256"] = sha
        if args.expect_sha256 is not None and args.expect_sha256 != sha:
            raise ValueError("Original photograph SHA-256 differs from the capture record")
        board = json.loads(args.board.read_text())
        allowed = ("board_id", "dictionary", "squares_x", "squares_y", "square_length",
                   "marker_length", "marker_ids", "marker_border_bits", "legacy_pattern")
        boards = [{key: b[key] for key in allowed if key in b} for b in [board, *board.get("alternate_boards", [])]]
        first, overlay = run_tool(args, sha, 1)
        initial_region = previous_region(prior_path, args, sha, first) if prior_path else None
        with Image.open(args.image) as image:
            if image.size != tuple(first["image_size"]):
                raise ValueError("Native photo and detector dimensions differ")
            assessments, final, verdict = asyncio.run(supervise(args, sha, boards, image, first, overlay, result, initial_region))
        if digest(args.image) != sha:
            raise ValueError("Original photograph changed during the review")
        final["method_sha256"] = result["method_sha256"]
        atomic_json(args.out / "final-report.json", final)
        result.update(status="completed", verdict=verdict, boards=assessments, final_report="final-report.json")
    except Exception as error:
        result.update(error=f"{type(error).__name__}: {error}")
        print(result["error"], file=sys.stderr)
    finally:
        result["finished_at"] = datetime.now().astimezone().isoformat()
        atomic_json(args.out / "review.json", result)
    return 0 if result["status"] == "completed" else 1


def already_completed(args):
    receipt = args.out / "review.json"
    if not receipt.is_file():
        return False
    prior = json.loads(receipt.read_text())
    if prior.get("status") != "completed":
        return False
    sha = digest(args.image)
    board = json.loads(args.board.read_text())
    board_sha = hashlib.sha256(json.dumps(board, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report_name = prior.get("final_report")
    if (prior.get("model_id") == MODEL and prior.get("selected_model") == MODEL
            and prior.get("selected_effort") == EFFORT and isinstance(prior.get("session_id"), str)
            and prior["session_id"].strip()
            and prior.get("verdict") in VERDICTS and prior.get("source_sha256") == sha
            and prior.get("camera") == args.camera
            and isinstance(report_name, str) and report_name not in ("", ".", "..")
            and Path(report_name).name == report_name and args.expect_sha256 in (None, sha)):
        report_path = args.out / report_name
        if report_path.is_symlink() or not report_path.is_file():
            raise ValueError("Completed review requires a regular local detector report")
        report = json.loads(report_path.read_text())
        if (report.get("camera") == args.camera and report.get("image_sha256") == sha
                and report.get("board_sha256") == board_sha):
            return True
    raise ValueError("Output directory contains a completed review for a different input or an invalid receipt")


def run_frozen_job(args):
    # Decode and execute the exact review.py bytes hashed in this job. The child
    # detector and all later turns resolve their sources inside the same snapshot.
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / ".review.lock").open("ab") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if already_completed(args):
            return 0
        with tempfile.TemporaryDirectory(prefix="uwa-charuco-method-") as temp:
            frozen = Path(temp)
            for name in METHOD_FILES:
                (frozen / name).write_bytes((HERE / name).read_bytes())
            job = copy(args)
            job.board = frozen / "board.json"
            job.board.write_bytes(args.board.read_bytes())
            runner = runpy.run_path(str(frozen / "review.py"), run_name="uwa_frozen_charuco_review")
            return runner["run"](job)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--camera", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--expect-sha256")
    parser.add_argument("--reuse-region-from", type=Path, help="Use the same photo/board's previous Hydrogen region "
                        "for a fresh one-turn review. Write results to a separate --out directory.")
    args = parser.parse_args()
    args.workspace = args.workspace.resolve()
    return run_frozen_job(args)


if __name__ == "__main__":
    raise SystemExit(main())

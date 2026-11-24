"""Use Hydrogen Low to guide repeated, locally checked carton measurements."""

import asyncio
from base64 import b64decode, b64encode
from io import BytesIO
import json
from pathlib import Path
import re
from statistics import median
from tempfile import NamedTemporaryFile, TemporaryDirectory
import time


NATIVE_SIZE = (8000, 6000)
IMAGE_WINDOW = (775, 1750, 5350, 5260)
SIGNATURE_SIZE = (48, 36)
MAX_SCENE_DIFFERENCE = 3.0
MODEL = "gemini-4-hydrogen"
EFFORT = "low"
MAX_MEASUREMENTS = 3
REPO = Path(__file__).resolve().parents[1]
AGY = REPO.parents[1] / "setup/agent_tools/antigravity/agy"
PROMPT = REPO / "docs/agent_trials/PROMPT_CARTON_VISION.md"


def tabletop_preview(path, *, native_size=NATIVE_SIZE, image_window=IMAGE_WINDOW):
    from PIL import Image

    with Image.open(path) as image:
        if image.size != tuple(native_size):
            raise ValueError("Hydrogen image size differs from the camera's native optics.")
        preview = image.crop(image_window).convert("RGB")
    preview.thumbnail((1120, 1000))
    return preview


def scene_signature(preview):
    from PIL import Image

    return preview.convert("L").resize(SIGNATURE_SIZE, Image.Resampling.BOX).tobytes()


def cached_windows(path, calibration_sha, signature):
    try:
        entry = json.loads(path.read_text())
        if entry["version"] != 1 or entry["calibration_sha256"] != calibration_sha:
            return None
        previous = b64decode(entry["tabletop_signature"], validate=True)
        if len(previous) != len(signature):
            return None
        differences = [current - saved for current, saved in zip(signature, previous)]
        brightness_offset = median(differences)
        if sum(abs(value - brightness_offset) for value in differences) / len(differences) > MAX_SCENE_DIFFERENCE:
            return None
        windows = entry["roi"], entry["face_roi"]
        for window, size in zip(windows, ((2600, 2200), (2550, 1800))):
            x0, y0, x1, y1 = window
            if (any(type(value) is not int for value in window)
                    or not (0 <= x0 < x1 <= NATIVE_SIZE[0] and 0 <= y0 < y1 <= NATIVE_SIZE[1])
                    or (x1 - x0, y1 - y0) != size):
                return None
        return windows
    except (OSError, KeyError, TypeError, ValueError):
        return None


def save_windows(path, calibration_sha, signature, windows):
    # Another library instance may read the cache while this one publishes it.
    with NamedTemporaryFile(dir=path.parent, prefix=".carton-window-", delete=False, mode="w") as stream:
        temporary = Path(stream.name)
        try:
            json.dump({
                "version": 1,
                "calibration_sha256": calibration_sha,
                "tabletop_signature": b64encode(signature).decode("ascii"),
                "roi": windows[0],
                "face_roi": windows[1],
            }, stream)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def valid_box(box):
    return (isinstance(box, list) and len(box) == 4
            and all(type(value) is int and 0 <= value <= 1000 for value in box)
            and box[0] < box[2] and box[1] < box[3])


def parse_answer(raw):
    fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", raw.strip(), re.DOTALL | re.IGNORECASE)
    answer = json.loads(fenced[1] if fenced else raw)
    required = {"status", "box_2d", "front_box_2d"}
    if not isinstance(answer, dict) or not required <= answer.keys() <= required | {"front_quad_2d"}:
        raise ValueError("Unexpected Hydrogen response schema.")
    status, box, front = (answer[key] for key in ("status", "box_2d", "front_box_2d"))
    quad = answer.get("front_quad_2d")
    if status == "found" and valid_box(box) and (front is None or valid_box(front)) and valid_front_quad(quad, box):
        return answer
    if status in ("absent", "uncertain") and box is None and front is None and quad is None:
        return answer
    raise ValueError("Invalid Hydrogen status or image coordinates.")


def valid_front_quad(quad, box):
    if quad is None:
        return True
    if not isinstance(quad, list) or len(quad) != 4:
        return False
    top, left, bottom, right = box
    if not all(isinstance(point, list) and len(point) == 2
               and all(type(value) is int and 0 <= value <= 1000 for value in point)
               and top-20 <= point[0] <= bottom+20 and left-20 <= point[1] <= right+20 for point in quad):
        return False
    # The perspective warp expects four convex, clockwise points in x/y image order.
    points = [(x, y) for y, x in quad]
    edges = [(b[0]-a[0], b[1]-a[1]) for a, b in zip(points, points[1:]+points[:1])]
    return all(ax*by-ay*bx > 0 for (ax, ay), (bx, by) in zip(edges, edges[1:]+edges[:1]))


def native_front_quad(answer, *, image_window=IMAGE_WINDOW):
    quad = answer.get("front_quad_2d")
    if quad is None:
        return None
    x0, y0, x1, y1 = image_window
    return tuple(round(value, 3) for y, x in quad
                 for value in (x0 + (x1-x0)*x/1000, y0 + (y1-y0)*y/1000))


def search_windows(answer, *, native_size=NATIVE_SIZE, image_window=IMAGE_WINDOW,
                   window_sizes=((2600, 2200), (2550, 1800))):
    x0, y0, x1, y1 = image_window
    width, height = x1 - x0, y1 - y0

    def native_center(box):
        top, left, bottom, right = box
        return x0 + width * (left + right) / 2000, y0 + height * (top + bottom) / 2000

    def centered(center, w, h):
        left = min(native_size[0] - w, max(0, round(center[0] - w / 2)))
        top = min(native_size[1] - h, max(0, round(center[1] - h / 2)))
        return left, top, left + w, top + h

    box, front = answer["box_2d"], answer["front_box_2d"]
    center = native_center(box)
    face = native_center(front) if front else (center[0], center[1] + 0.2 * (box[2] - box[0]) * height / 1000)
    return centered(center, *window_sizes[0]), centered(face, *window_sizes[1])


class ACP:
    def __init__(self, process):
        self.process = process
        self.request_id = 0
        self.session_id = None
        self.text = []
        self.used_tools = False

    async def send(self, fields):
        self.process.stdin.write((json.dumps({"jsonrpc": "2.0", **fields}) + "\n").encode())
        await self.process.stdin.drain()

    async def request(self, method, params):
        self.request_id += 1
        await self.send({"id": self.request_id, "method": method, "params": params})
        while line := await self.process.stdout.readline():
            message = json.loads(line)
            incoming = message.get("method")
            if incoming == "session/update" and message["params"]["sessionId"] == self.session_id:
                update = message["params"]["update"]
                event = update["sessionUpdate"]
                if event == "agent_message_chunk" and update["content"]["type"] == "text":
                    self.text.append(update["content"]["text"])
                elif event in ("tool_call", "tool_call_update"):
                    self.used_tools = True
            elif incoming and "id" in message:
                self.used_tools = True
                if incoming == "session/request_permission":
                    await self.send({"id": message["id"], "result": {"outcome": {"outcome": "cancelled"}}})
                else:
                    await self.send({"id": message["id"], "error": {"code": -32601, "message": "Image only"}})
            elif message.get("id") == self.request_id:
                if "error" in message:
                    raise RuntimeError(f"Antigravity rejected {method}. See hydrogen-stderr.log.")
                return message["result"]
        raise RuntimeError(f"Antigravity exited during {method}. See hydrogen-stderr.log.")


def image_block(jpeg):
    return {"type": "image", "mimeType": "image/jpeg", "data": b64encode(jpeg).decode("ascii")}


def feedback_blocks(registration):
    report = json.loads((registration / "registration.json").read_text())
    valid = [attempt for attempt in report["attempts"] if "support_fit_rms_px" in attempt]
    best = sorted(valid, key=lambda attempt: attempt["support_fit_rms_px"] / attempt["registration_threshold_px"])[:3]
    fields = ("roi", "method", "inliers", "support_fit_rms_px", "registration_threshold_px")
    evidence = dict(error=report.get("error"), valid_supported_fits=sum(a['support_fit_pass'] for a in valid),
                    best=[{key: attempt[key] for key in fields if key in attempt} for attempt in best])
    text = ("Lokale Messung auf den nativen Pixeln: " + json.dumps(evidence) + "\n"
            "Die Bildansicht bleibt der gleiche Tischbildausschnitt. Türkis zeigt das rückprojizierte "
            "Kartonmodell des besten Fits, falls vorhanden. Wähle für die nächste Messung "
            "ein begründet korrigiertes Rechteck oder ein genaueres Viereck der bedruckten Vorderwand. "
            "Gib dieselbe JSON-Struktur zurück. Wiederhole keine unveränderte Messanfrage. "
            "Karton gefunden und genaue Pose bestimmt sind zwei verschiedene Befunde.")
    blocks = [{"type": "text", "text": text}]
    overlay = registration / "fit-feedback.jpg"
    if overlay.is_file():
        blocks.append(image_block(overlay.read_bytes()))
    return blocks, evidence


async def measure_with_hydrogen(jpeg, out, initial_registration, measure, evidence, *, geometry=None):
    started = time.monotonic()
    with TemporaryDirectory(prefix="uwa-carton-hydrogen-") as isolated, (out / "hydrogen-stderr.log").open("wb") as stderr:
        process = await asyncio.create_subprocess_exec(
            str(AGY), "acp", "--include-default-customizations=false", "--disable-telemetry",
            cwd=isolated, stdin=-1, stdout=-1, stderr=stderr,
        )
        client = ACP(process)
        try:
            async with asyncio.timeout(12):
                caps = await client.request("initialize", {"protocolVersion": 1, "clientCapabilities": {},
                    "clientInfo": {"name": "uwa-carton-library", "version": "1"}})
                if not caps["agentCapabilities"]["promptCapabilities"].get("image"):
                    raise RuntimeError("Antigravity ACP does not support image input.")
                session = await client.request("session/new", {"cwd": isolated, "mcpServers": []})
                client.session_id = session["sessionId"]
                params = {"sessionId": client.session_id}
                await client.request("session/set_config_option", {**params, "configId": "model", "value": MODEL})
                config = await client.request("session/set_config_option",
                                              {**params, "configId": "thought_level", "value": EFFORT})
                selected = {option["id"]: option["currentValue"] for option in config["configOptions"]}
                if selected.get("model") != MODEL or selected.get("thought_level") != EFFORT:
                    raise RuntimeError("Antigravity did not select Hydrogen Low.")
                evidence["setup_s"] = time.monotonic() - started
            blocks = [{"type": "text", "text": PROMPT.read_text()}, image_block(jpeg)]
            feedback, summary = feedback_blocks(initial_registration)
            blocks += feedback
            evidence["initial_fit"] = summary
            requests = set()
            for number in range(1, MAX_MEASUREMENTS + 1):
                item = {"round": number}
                evidence["rounds"].append(item)
                client.text.clear()
                started = time.monotonic()
                try:
                    async with asyncio.timeout(20):
                        result = await client.request("session/prompt", {**params, "prompt": blocks})
                finally:
                    item["prompt_s"] = time.monotonic() - started
                    item["tool_activity"] = client.used_tools
                item["stop_reason"] = result.get("stopReason")
                if item["stop_reason"] != "end_turn" or client.used_tools:
                    raise RuntimeError("Antigravity did not finish an image-only response.")
                answer = parse_answer("".join(client.text).strip())
                item["answer"] = answer
                if answer["status"] != "found":
                    raise ValueError(f"Hydrogen Low reported {answer['status']}.")
                windows = search_windows(answer, **(geometry or {}))
                quad = native_front_quad(answer, image_window=(geometry or {}).get('image_window', IMAGE_WINDOW))
                item["roi"], item["face_roi"], item["front_quad_native"] = *windows, quad
                if number == 1:
                    evidence.update(answer=answer, roi=windows[0], face_roi=windows[1])
                request = (*map(tuple, windows), quad)
                if request in requests:
                    raise ValueError("Hydrogen Low repeated the same carton measurement request.")
                requests.add(request)
                pose, registration = measure(number, windows, quad)
                item["registration"] = str(registration.relative_to(out))
                if pose is not None:
                    item["fit_accepted"] = True
                    return pose, windows, quad
                blocks, item["fit"] = feedback_blocks(registration)
            raise ValueError(f"No valid supported carton pose after {MAX_MEASUREMENTS} Hydrogen-guided measurements.")
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.communicate(), 1)
            except TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()


def guide_measurements(preview, out, initial_registration, measure, *, geometry=None):
    evidence = {"model": MODEL, "effort": EFFORT, "rounds": []}
    try:
        jpeg = BytesIO()
        preview.save(jpeg, format="JPEG", quality=89, optimize=True)
        return asyncio.run(measure_with_hydrogen(jpeg.getvalue(), out, initial_registration, measure, evidence,
                                               geometry=geometry))
    except TimeoutError as error:
        evidence["error"] = "Hydrogen Low timed out."
        raise ValueError(evidence["error"]) from error
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        evidence["error"] = str(error)
        raise ValueError(f"Hydrogen-guided carton fit ended. {error}") from error
    finally:
        (out / "hydrogen.json").write_text(json.dumps(evidence, indent=2) + "\n")


async def inspect_projected_carton(image, overlay, out):
    """Presence/occlusion evidence only; this response never supplies a metric pose."""
    prompt = (
        "Prüfe den bekannten offenen Avocado-Wellpappkarton in der zweiten Kameraansicht. "
        "Bild 1 ist das unveränderte Kamerabild, Bild 2 dieselbe Ansicht mit der aus der anderen "
        "Kamera projizierten Kartonhülle in Türkis. Die Hülle ist eine Hypothese, kein Bildbeweis. "
        "Prüfe anhand echter sichtbarer Wände, Kanten und Aufdrucke, ob der Karton dort steht. "
        "Eine vollständige Posemessung ist nicht erforderlich. Keine Koordinaten schätzen. "
        "confirmed: sichtbarer Karton passt zur projizierten Stelle; occluded: die Stelle ist "
        "durch einen sichtbaren Vordergrund verdeckt; contradicted: die Stelle ist klar sichtbar "
        "und leer oder der Karton eindeutig woanders; uncertain: Bildbefund reicht nicht. "
        'Antworte nur JSON mit genau {"status":"confirmed|occluded|contradicted|uncertain",'
        '"reason":"kurze sichtbare Begründung"}. Keine Werkzeuge verwenden.'
    )
    with TemporaryDirectory(prefix='uwa-carton-check-') as isolated, (out/'verification-stderr.log').open('wb') as stderr:
        process = await asyncio.create_subprocess_exec(
            str(AGY), 'acp', '--include-default-customizations=false', '--disable-telemetry',
            cwd=isolated, stdin=-1, stdout=-1, stderr=stderr)
        client = ACP(process)
        try:
            async with asyncio.timeout(45):
                caps = await client.request('initialize', {'protocolVersion': 1, 'clientCapabilities': {},
                    'clientInfo': {'name': 'uwa-carton-cross-view', 'version': '1'}})
                if not caps['agentCapabilities']['promptCapabilities'].get('image'):
                    raise ValueError('Hydrogen has no image input.')
                session = await client.request('session/new', {'cwd': isolated, 'mcpServers': []})
                client.session_id = session['sessionId']
                params = {'sessionId': client.session_id}
                await client.request('session/set_config_option', {**params, 'configId': 'model', 'value': MODEL})
                result = await client.request('session/set_config_option',
                    {**params, 'configId': 'thought_level', 'value': EFFORT})
                selected = {item['id']: item['currentValue'] for item in result['configOptions']}
                if selected.get('model') != MODEL or selected.get('thought_level') != EFFORT:
                    raise ValueError('Hydrogen Low selection was not confirmed.')
                result = await client.request('session/prompt', {**params, 'prompt': [
                    {'type': 'text', 'text': prompt}, image_block(image), image_block(overlay)]})
                if result.get('stopReason') != 'end_turn' or client.used_tools:
                    raise ValueError('Expected image-only Hydrogen response.')
                raw = ''.join(client.text).strip()
                fenced = re.fullmatch(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL | re.IGNORECASE)
                answer = json.loads(fenced[1] if fenced else raw)
                if (not isinstance(answer, dict) or set(answer) != {'status', 'reason'}
                        or answer['status'] not in {'confirmed', 'occluded', 'contradicted', 'uncertain'}
                        or not isinstance(answer['reason'], str) or not answer['reason'].strip()):
                    raise ValueError('Invalid cross-view response schema.')
                return answer
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.communicate(), 1)
            except TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()

"""Use Hydrogen Low to suggest search windows, never a robot-frame pose."""

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
REPO = Path(__file__).resolve().parents[1]
AGY = REPO.parents[1] / "setup/agent_tools/antigravity/agy"
PROMPT = REPO / "docs/agent_trials/PROMPT_CARTON_VISION.md"


def tabletop_preview(path):
    from PIL import Image

    with Image.open(path) as image:
        if image.size != NATIVE_SIZE:
            raise ValueError("Hydrogen expects the native 8000 × 6000 OAK4 image.")
        preview = image.crop(IMAGE_WINDOW).convert("RGB")
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
    if not isinstance(answer, dict) or set(answer) != {"status", "box_2d", "front_box_2d"}:
        raise ValueError("Unexpected Hydrogen response schema.")
    status, box, front = (answer[key] for key in ("status", "box_2d", "front_box_2d"))
    if status == "found" and valid_box(box) and (front is None or valid_box(front)):
        return answer
    if status in ("absent", "uncertain") and box is None and front is None:
        return answer
    raise ValueError("Invalid Hydrogen status or image coordinates.")


def search_windows(answer):
    x0, y0, x1, y1 = IMAGE_WINDOW
    width, height = x1 - x0, y1 - y0

    def native_center(box):
        top, left, bottom, right = box
        return x0 + width * (left + right) / 2000, y0 + height * (top + bottom) / 2000

    def centered(center, w, h):
        left = min(NATIVE_SIZE[0] - w, max(0, round(center[0] - w / 2)))
        top = min(NATIVE_SIZE[1] - h, max(0, round(center[1] - h / 2)))
        return left, top, left + w, top + h

    box, front = answer["box_2d"], answer["front_box_2d"]
    center = native_center(box)
    face = native_center(front) if front else (center[0], center[1] + 0.2 * (box[2] - box[0]) * height / 1000)
    return centered(center, 2600, 2200), centered(face, 2550, 1800)


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


async def request_answer(jpeg, stderr_path, evidence):
    started = time.monotonic()
    with TemporaryDirectory(prefix="uwa-carton-hydrogen-") as isolated, stderr_path.open("wb") as stderr:
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
            started = time.monotonic()
            try:
                async with asyncio.timeout(20):
                    result = await client.request("session/prompt", {**params, "prompt": [
                        {"type": "text", "text": PROMPT.read_text()},
                        {"type": "image", "mimeType": "image/jpeg", "data": b64encode(jpeg).decode("ascii")},
                    ]})
            finally:
                evidence["prompt_s"] = time.monotonic() - started
                evidence["tool_activity"] = client.used_tools
            evidence["stop_reason"] = result.get("stopReason")
            if result.get("stopReason") != "end_turn" or client.used_tools:
                raise RuntimeError("Antigravity did not finish an image-only response.")
            return "".join(client.text).strip()
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.communicate(), 1)
            except TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()


def suggest_windows(preview, out):
    evidence = {"model": MODEL, "effort": EFFORT}
    try:
        jpeg = BytesIO()
        preview.save(jpeg, format="JPEG", quality=89, optimize=True)
        raw = asyncio.run(request_answer(jpeg.getvalue(), out / "hydrogen-stderr.log", evidence))
        answer = parse_answer(raw)
        evidence["answer"] = answer
        if answer["status"] != "found":
            raise ValueError(f"Hydrogen Low reported {answer['status']}.")
        windows = search_windows(answer)
        evidence["roi"], evidence["face_roi"] = windows
        return windows
    except TimeoutError as error:
        evidence["error"] = "Hydrogen Low timed out."
        raise ValueError(evidence["error"]) from error
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        evidence["error"] = str(error)
        raise ValueError(f"Hydrogen Low could not supply a search window. {error}") from error
    finally:
        (out / "hydrogen.json").write_text(json.dumps(evidence, indent=2) + "\n")

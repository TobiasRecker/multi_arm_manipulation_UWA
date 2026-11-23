import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import carton_hydrogen


BOX = {"status": "found", "box_2d": [100, 200, 700, 800],
       "front_box_2d": [400, 200, 700, 800]}
QUAD = [[430, 240], [410, 770], [650, 760], [690, 250]]


def make_fit(directory):
    directory.mkdir()
    (directory / "registration.json").write_text(json.dumps({
        "error": "Rejected fit",
        "attempts": [{"support_fit_rms_px": 8., "registration_threshold_px": 6.5,
                      "support_fit_pass": False, "inliers": 30}],
    }))
    (directory / "fit-feedback.jpg").write_bytes(b"overlay")
    return directory


@pytest.mark.parametrize("accepted", [True, False])
def test_rejected_measurement_is_returned_to_the_same_hydrogen_session(tmp_path, monkeypatch, accepted):
    requests = []
    measurements = []
    replies = iter([BOX, dict(BOX, front_quad_2d=QUAD)] if accepted else [BOX] * 2)

    class Client:
        def __init__(self, process):
            self.text = []
            self.used_tools = False

        async def request(self, method, params):
            if method == "initialize":
                return {"agentCapabilities": {"promptCapabilities": {"image": True}}}
            if method == "session/new":
                return {"sessionId": "carton"}
            if method == "session/set_config_option":
                return {"configOptions": [{"id": "model", "currentValue": carton_hydrogen.MODEL},
                                          {"id": "thought_level", "currentValue": carton_hydrogen.EFFORT}]}
            requests.append(params)
            self.text.append(json.dumps(next(replies)))
            return {"stopReason": "end_turn"}

    async def spawn(*args, **kwargs):
        async def communicate():
            pass

        return SimpleNamespace(stdin=SimpleNamespace(close=lambda: None), communicate=communicate)

    monkeypatch.setattr(carton_hydrogen, "ACP", Client)
    monkeypatch.setattr(carton_hydrogen.asyncio, "create_subprocess_exec", spawn)
    rejected = make_fit(tmp_path / "rejected")
    pose = tmp_path / "accepted" / "object-pose.json"

    def measure(number, windows, quad):
        measurements.append(quad)
        return (None, rejected) if number == 1 else (pose, pose.parent)

    evidence = {"rounds": []}
    task = carton_hydrogen.measure_with_hydrogen(b"photo", tmp_path, rejected, measure, evidence)
    if accepted:
        result, _, quad = asyncio.run(task)
        assert result == pose
        assert measurements == [None, quad]
        assert quad == carton_hydrogen.native_front_quad(dict(BOX, front_quad_2d=QUAD))
    else:
        with pytest.raises(ValueError, match="repeated the same"):
            asyncio.run(task)
        assert measurements == [None]
    assert len(requests) == 2
    assert all(request["sessionId"] == "carton" for request in requests)
    assert "8.0" in requests[1]["prompt"][0]["text"]
    assert requests[1]["prompt"][1] == carton_hydrogen.image_block(b"overlay")


def test_hydrogen_reply_cannot_supply_a_metric_pose():
    with pytest.raises(ValueError, match="schema"):
        carton_hydrogen.parse_answer(json.dumps(dict(BOX, pose=[1, 2, 3])))
    with pytest.raises(ValueError, match="coordinates"):
        carton_hydrogen.parse_answer(json.dumps(dict(BOX, front_quad_2d=QUAD[::-1])))

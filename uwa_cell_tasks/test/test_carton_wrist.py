import json
from pathlib import Path
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from check_carton_wrist import ARMS, main


@pytest.mark.parametrize(("pixel", "line", "arm_status"), [
    ([190, 320], True, "RIM_MEASURED"),
    ([190, 430], True, "EXPECTED_RIM_OUT_OF_FRAME"),
    ([190, 200], True, "RIM_NOT_VISIBLE_AT_TARGET"),
    ([190, 320], False, "RIM_NOT_FOUND"),
])
def test_wrist_pixel_diagnostics_cannot_approve_contact(tmp_path, pixel, line, arm_status):
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    if line:
        cv2.line(image, (180, 235), (180, 380), (0, 255, 255), 7)
    assert cv2.imwrite(str(tmp_path / "wrist.png"), image)
    manifest = tmp_path / "input.json"
    manifest.write_text(json.dumps({arm: {"image": "wrist.png", "expected_rim_pixel": pixel} for arm in ARMS}))
    destination = tmp_path / "check"
    assert main(["--input", str(manifest), "--output", str(destination)]) == 0
    data = json.loads((destination / "result.json").read_text())
    assert data["status"] == "REVIEW_REQUIRED"
    for record in data["arms"].values():
        assert record["status"] == arm_status
        assert (destination / record["overlay"]).is_file()
        if arm_status == "RIM_MEASURED":
            assert record["signed_image_offset_px"] == pytest.approx(10., abs=0.1)
        else:
            assert "signed_image_offset_px" not in record


def test_wrist_reports_unusable_image(tmp_path):
    manifest = tmp_path / "input.json"
    manifest.write_text(json.dumps({arm: {"image": "missing.jpg", "expected_rim_pixel": [100, 200]} for arm in ARMS}))
    destination = tmp_path / "check"
    assert main(["--input", str(manifest), "--output", str(destination)]) == 2
    data = json.loads((destination / "result.json").read_text())
    assert data["status"] == "INVALID_INPUT"
    assert all(record["status"] == "INVALID_INPUT" for record in data["arms"].values())

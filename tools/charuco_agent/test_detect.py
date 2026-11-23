"""Regression cases for raw-coordinate recovery, identity and source binding."""
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml


TOOL = Path(__file__).with_name('detect.py')
spec = importlib.util.spec_from_file_location('uwa_agent_detector', TOOL)
detect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detect)
CONFIG = yaml.safe_load((TOOL.parents[2] / 'uwa_cell_description/config/mobile_charuco_a4.yaml').read_bytes())


def board_image():
    return detect.make_board(CONFIG).generateImage((700, 500), marginSize=0)


def save(path, img):
    assert cv2.imwrite(str(path), img)
    return path


def test_raw_and_crop_agree_on_corner_ids_and_native_pixels(tmp_path):
    img = cv2.copyMakeBorder(board_image(), 370, 90, 210, 110, cv2.BORDER_CONSTANT, value=255)
    p = save(tmp_path / 'source.png', img)
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    first, _ = detect.inspect(p, CONFIG, 'oak_usb', expected=expected)
    second, _ = detect.inspect(p, CONFIG, 'oak_usb', roi=[180, 340, 760, 550])
    a, b = first['boards'][0], second['boards'][0]
    assert a['full'] and a['usable'] and b['full'] and len(b['markers']) == 17
    assert [c['id'] for c in a['charuco']] == list(range(24))
    assert first['image_size'] == [img.shape[1], img.shape[0]]
    assert first['image_sha256'] == second['image_sha256'] == expected
    np.testing.assert_allclose([c['point_px'] for c in a['charuco']], [c['point_px'] for c in b['charuco']], atol=.3)
    with pytest.raises(ValueError, match='SHA256'):
        detect.inspect(p, CONFIG, 'oak_usb', expected='0' * 64)


def test_perspective_recovery_points_match_known_native_projection(tmp_path):
    img = board_image()
    source = np.float32([[0,0], [699,0], [699,499], [0,499]])
    corners = np.float32([[130,130],[995,220],[807,590],[396,460]])
    h = cv2.getPerspectiveTransform(source, corners)
    warped = cv2.warpPerspective(img, h, (1200,700),borderValue=255)
    p = save(tmp_path / 'warped.png', warped)
    report, _ = detect.inspect(p, CONFIG, 'wrist', quad=corners.flatten().tolist(), method='native')
    b = report['boards'][0]
    assert b['full'] and b['rectification'] and report['quad']
    grid = np.float32([[x*100-.5,y*100-.5] for y in range(1,5) for x in range(1,7)])
    expected = cv2.perspectiveTransform(grid.reshape(-1,1,2), h).reshape(-1,2)
    got = [v['point_px'] for v in b['charuco']]
    np.testing.assert_allclose(got, expected, atol=1.5)
    with pytest.raises(ValueError, match='clockwise'):
        detect.inspect(p, CONFIG, 'wrist', quad=corners[[0,2,1,3]].flatten(), method='native')


def test_duplicate_target_and_foreign_marker_are_distinguished(tmp_path):
    canvas = np.full((850, 1400), 255, np.uint8)
    canvas[35:535, 30:730] = board_image()
    dictionary = detect.make_board(CONFIG).getDictionary()
    for idx, x in [(75, 800), (50, 1020)]:
        canvas[590:720, x:x+130] = cv2.aruco.generateImageMarker(dictionary, idx, 130)
    report, _ = detect.inspect(save(tmp_path/'duplicates.png', canvas), CONFIG, 'wrist', method='native')
    b = report['boards'][0]
    assert b['duplicate_ids'] == [75] and b['status'] == 'ambiguous' and b['review_required']
    assert not b['usable'] and 50 in b['foreign_ids']
    assert 75 not in [m['id'] for m in b['markers']]
    assert all(i in CONFIG['marker_ids'] for i in [m['id'] for m in b['markers']])


def test_empty_frame_has_no_generated_correspondences(tmp_path):
    p = save(tmp_path/'white.png', np.full((300,400), 255, np.uint8))
    report, _ = detect.inspect(p, CONFIG, 'wrist')
    b = report['boards'][0]
    assert b['status'] == 'not_detected' and b['markers'] == b['charuco'] == []
    assert b['usable'] is False and not b['full']
    json.dumps(report, allow_nan=False)


def test_complementary_regions_fuse_on_native_data_and_conflicts_fail(tmp_path):
    canvas = cv2.copyMakeBorder(board_image(), 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    image = save(tmp_path/'sample.png', canvas)
    reports = []
    for region in ([0, 0, 575, 560], [185, 0, 575, 560]):
        item, _ = detect.inspect(image, CONFIG, 'usb', roi=region, method='native')
        path = tmp_path/f'pass-{len(reports)}.json'
        path.write_text(json.dumps(item))
        reports.append(path)
    combined, _ = detect.inspect(image, CONFIG, 'usb', fuse=reports)
    assert combined['fusion']['accepted'] and combined['boards'][0]['full']
    b = combined['boards'][0]
    assert len(b['markers']) == 17 and len(b['charuco']) == 24 and len(b['fusion_common_ids']) >= 3
    assert b['selected_pass'] == 'geometric_fusion'
    changed = json.loads(reports[1].read_bytes())
    marker = next(m for m in changed['boards'][0]['markers'] if m['id'] == b['fusion_common_ids'][0])
    marker['corners_px'] = (np.array(marker['corners_px']) + [110, 0]).tolist()
    reports[1].write_text(json.dumps(changed))
    rejected, _ = detect.inspect(image, CONFIG, 'usb', fuse=reports)
    assert not rejected['fusion']['accepted'] and 'disagree' in rejected['fusion']['boards'][CONFIG['board_id']]
    changed['image_sha256'] = '0'*64
    reports[1].write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='another image'):
        detect.inspect(image, CONFIG, 'usb', fuse=reports)


def test_marker_derived_rectification_uses_distributed_image_measurements(tmp_path):
    # A small occlusion leaves enough distributed markers to locate the entire pattern.
    gray = cv2.copyMakeBorder(board_image(), 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    gray[26:245, 29:247] = 255
    path = save(tmp_path/'partial.png', gray)
    report, _ = detect.inspect(path, CONFIG, 'wrist')
    b = report['boards'][0]
    assert any(p['method'] == 'board_rectified_native' for p in b['passes'])
    model = detect.make_board(CONFIG)
    src = dict(charuco=b['charuco'], markers=b['markers'], duplicate_ids=[])
    inferred, support = detect.estimated_pattern_corners(gray, CONFIG, model, src, [0,0])
    assert len(support) >= 3
    np.testing.assert_allclose(inferred, [[30,30], [730,30], [730,530], [30,530]], atol=2)
    src['markers'] = src['markers'][:2]
    assert detect.estimated_pattern_corners(gray, CONFIG, model, src, [0,0]) is None

"""Offline coverage evidence and aligned-depth checks for object scans."""

import json
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import object_scan_perception as scan


def test_capture_keeps_photo_when_second_camera_times_out(tmp_path, monkeypatch):
    def oak4_capture(workspace, directory, rgbd):
        image, meta = directory / 'image.png', directory / 'metadata.json'
        Image.new('RGB', (640, 480)).save(image)
        meta.write_text('{}')
        return image, meta, dict(source='fake_oak4', display_rotation_deg=0)

    def timeout(workspace, directory):
        raise subprocess.TimeoutExpired('camera transport', 1)

    monkeypatch.setattr(scan, 'oak4_capture', oak4_capture)
    monkeypatch.setattr(scan, 'oak_pro_capture', timeout)
    records = scan.capture(['oak4', 'oak_pro'], tmp_path)
    assert records[0]['image_sha256'] == scan.digest(records[0]['image'])
    assert records[0]['preview_sha256'] == scan.digest(records[0]['preview'])
    assert records[1]['camera'] == 'oak_pro' and 'timed out' in records[1]['error']


@pytest.mark.parametrize('mode', ['rgbd', 'rgbd_hdr', 'rgbd_hq'])
def test_rgbd_obb_preserves_beam_axis_and_table_height(tmp_path, mode):
    depth = np.full((480, 640), 1000, dtype=np.uint16)
    polygon = cv2.boxPoints(((310, 230), (220, 40), 17)).round().astype(np.int32)
    cv2.fillConvexPoly(depth, polygon, 962)
    k = [[500., 0, 320], [0, 500, 240], [0, 0, 1.]]
    rgb, depth_path = tmp_path / 'rgb.png', tmp_path / 'depth.png'
    Image.new('RGB', (640, 480)).save(rgb)
    assert cv2.imwrite(str(depth_path), depth)
    metadata = tmp_path / 'metadata.json'
    report = dict(success=True, kind='rgbd',
        projection=dict(K=k, depth_K=k, D=[0] * 5, size=[640, 480]),
        pairs=[dict(rgb_path=rgb.name, depth_path=depth_path.name)])
    if mode != 'rgbd':
        hdr_image = tmp_path / 'hdr.png'
        Image.new('RGB', (640, 480)).save(hdr_image)
        if mode == 'rgbd_hdr':
            report.update(mode=mode, hdr=dict(path=hdr_image.name, depth_path=depth_path.name,
                          reference_bracket='base', brackets=[dict(name='base')]))
        else:
            report.update(mode=mode, pairs=[], hq=dict(rgb_path=hdr_image.name, depth_path=depth_path.name,
                                                       sample_kind='static_rgb_stereo_hdr'))
    metadata.write_text(json.dumps(report))
    photo = dict(image=str(rgb), image_sha256=scan.digest(rgb), metadata=str(metadata),
                 rgbd=str(tmp_path), width=640, height=480, camera='oak4')
    if mode != 'rgbd':
        with pytest.raises(ValueError, match='does not belong'):
            scan.aligned_depth(photo)
        photo.update(image=str(hdr_image), image_sha256=scan.digest(hdr_image))
    box = dict(camera='oak4', status='found', box_2d=[358, 300, 602, 670])
    result = scan.estimate_geometry(photo, box)
    assert result['status'] == 'provisional'
    assert result['world_registration_validated'] is False
    obb = result['obb']
    assert obb['size_m'] == pytest.approx([.407, .075, .038], abs=.003)
    assert all(type(size) is float for size in obb['size_m'])
    assert obb['image_sha256'] == photo['image_sha256']
    rotation = np.asarray(obb['T_camera_object'])[:3, :3]
    assert np.linalg.det(rotation) == pytest.approx(1.)
    assert np.degrees(np.arctan2(rotation[1, 0], rotation[0, 0])) == pytest.approx(17., abs=1.)
    assert cv2.imwrite(str(depth_path), np.full_like(depth, 1000))
    assert scan.estimate_geometry(photo, box)['status'] == 'unavailable'


def test_gemini_proposals_reject_camera_or_point_outside_image_review(tmp_path):
    photo = dict(camera='oak_pro', image='present')
    def reviewer(prompt, images, output, workspace):
        assert 'Use two robots' in prompt
        assert images == [('oak_pro', photo)]
        return dict(observations=[dict(camera='oak_pro', status='found', box_2d=[50, 150, 500, 650],
            axis_2d=None, grasp_points=[dict(point_2d=[200, 800], reason='side')], reason='grain')], questions=[],
            approach='Concept', presentation_views=[])

    with pytest.raises(ValueError, match='grasp suggestions'):
        scan.investigate('Wooden beam', [photo], tmp_path, arm_count=2,
                         answer='Use two robots', reviewer=reviewer)


def test_cuboid_coverage_adds_missing_faces_and_rejects_unrelated_photo(tmp_path):
    record = dict(label='Same label', captures=[dict(camera='oak4', image='present', image_sha256='photo')])
    def report(view):
        return dict(status='candidate', faces=[dict(face='top', status='covered', views=[view],
            reason='Clear photo')], missing_views=[], repositioning=[], summary='Coverage estimate')

    result = scan.assess('Wooden beam', [record], tmp_path, family='cuboid',
                         reviewer=lambda *args: report('V1/oak4'))
    assert result['status'] == 'more_views'
    assert [face['face'] for face in result['faces']] == list(scan.CUBOID_FACES)
    assert len(result['missing_views']) == 6
    assert result['view_sources'][0]['image_sha256'] == 'photo'
    with pytest.raises(ValueError, match='photograph reference'):
        scan.assess('Wooden beam', [record], tmp_path, family='cuboid',
                    reviewer=lambda *args: report('V2/oak4'))

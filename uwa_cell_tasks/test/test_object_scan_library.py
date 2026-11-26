"""Exercise scan revisions, partial captures and asset publication offline."""

from contextlib import ExitStack
import hashlib
from pathlib import Path
import sys
from threading import Event
import time

from PIL import Image
import pytest


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
from object_scan_library import Scans, lease, read, write
import object_scan_perception as perception


class TestImages:
    def capture(self, cameras, output, *, workspace, rgbd):
        output.mkdir(parents=True)
        result = []
        for camera in cameras:
            if camera == 'oak_pro':
                result.append(dict(camera=camera, error='Test camera unavailable'))
                continue
            image = output / f'{camera}.jpg'
            Image.new('RGB', (160, 120), '#b27c4b').save(image)
            sha = hashlib.sha256(image.read_bytes()).hexdigest()
            result.append(dict(camera=camera, image=str(image), preview=str(image), image_sha256=sha,
                               preview_sha256=sha, width=160, height=120))
        return result

    def investigate(self, description, images, output, **kwargs):
        def review(prompt, photos, output, workspace):
            assert photos[0][1]['preview_sha256'] == photos[0][1]['image_sha256']
            return dict(approach=kwargs['answer'] or 'Use the top view.', presentation_views=['Both ends'],
                        questions=['How heavy is the beam?'], observations=[
                            dict(camera=camera, status='found', box_2d=[100, 100, 900, 900], axis_2d=None,
                                 grasp_points=[], reason='Synthetic test image') for camera, _ in photos])

        return perception.investigate(description, images, output, **kwargs, reviewer=review)

    def assess(self, description, views, output, **kwargs):
        def review(prompt, photos, output, workspace):
            return dict(status='more_views', faces=[dict(face='top', status='covered',
                        views=[photos[0][0]], reason='Synthetic test image')], missing_views=['Bottom view'],
                        repositioning=['Turn the beam over'], summary='Scan a second face.')

        return perception.assess(description, views, output, **kwargs, reviewer=review)


def wait(scans, identifier):
    for _ in range(400):
        result = scans.get(identifier)
        if result['status'] in {'ready', 'error'}:
            return result
        time.sleep(.025)
    pytest.fail('Object scan job did not finish')


def new_scan(scans):
    return scans.create(dict(name='Timber test', description='Synthetic rectangular beam',
                             camera_ids=['oak4', 'oak_pro'], robot_count=2, shape='box',
                             dimensions_mm=[600, 38, 89]))['id']


def test_existing_scan_upgrades_its_overview_before_using_hq_details(tmp_path):
    class CaptureProfiles(TestImages):
        def __init__(self):
            self.requests = []

        def capture(self, cameras, output, *, workspace, rgbd):
            self.requests.append(rgbd)
            images = super().capture(cameras, output, workspace=workspace, rgbd=rgbd)
            photo = images[0]
            if len(self.requests) == 1:
                photo.update(source='oak4_aligned_rgbd_hdr', rgbd=str(output))
            elif rgbd:
                photo.update(source='oak4_aligned_rgbd_hq', rgbd=str(output))
            else:
                photo.update(source='oak4_native_rgb_hdr_hq')
            return images

    provider = CaptureProfiles()
    scans = Scans(tmp_path / 'object-scans', tmp_path, perception=provider)
    identifier = new_scan(scans)
    for label in ('old overview', 'new overview', 'detail'):
        scans.action(identifier, 'capture', dict(label=label, camera_ids=['oak4']))
        assert wait(scans, identifier)['status'] == 'ready'
    assert provider.requests == [True, True, False]


def test_scan_revisions_partial_capture_and_publish(tmp_path):
    scans = Scans(tmp_path / 'object-scans', tmp_path, perception=TestImages())
    identifier = new_scan(scans)
    with pytest.raises(ValueError, match='Confirm sending'):
        scans.action(identifier, 'analyze', dict(allow_gemini=False))
    with pytest.raises(RuntimeError, match='Another library program'):
        with ExitStack() as stack:
            lease(stack, tmp_path / '.run.lock', 'Unexpected running program')
            scans.action(identifier, 'capture', dict(label='Top'))
    asynchronous, _ = scans.action(identifier, 'capture', dict(label='Top'))
    assert asynchronous
    scan = wait(scans, identifier)
    capture = scan['captures'][0]
    raw = capture['files'][0]['url'].partition('/files/')[2]
    image, media = scans.artifact(identifier, raw)
    assert image.is_file() and media == 'image/jpeg'
    assert capture['files'][1]['error'] == 'Test camera unavailable'
    assert 'artifacts' not in scan and 'image_path' not in capture['files'][0]
    with pytest.raises(FileNotFoundError):
        scans.artifact(identifier, '../../session.json')

    scans.action(identifier, 'analyze', dict(allow_gemini=True))
    old = wait(scans, identifier)['proposal']['revision']
    scans.action(identifier, 'approve', dict(revision=old))
    scans.action(identifier, 'analyze', dict(allow_gemini=True, answer='300 g on the table.'))
    scan = wait(scans, identifier)
    assert scan['proposal']['revision'] != old and scan['approval'] is None
    with pytest.raises(ValueError, match='current scan proposal'):
        scans.action(identifier, 'approve', dict(revision=old))
    scans.action(identifier, 'approve', dict(revision=scan['proposal']['revision']))
    assert scans.get(identifier)['approval']['scope'] == 'scan_sequence'
    with pytest.raises(FileNotFoundError):
        scans.action(identifier, 'execute', {})

    scans.action(identifier, 'assess', dict(allow_gemini=True))
    scan = wait(scans, identifier)
    assert scan['publish_available'] and scan['coverage']['status'] == 'more_views'
    assert scan['coverage']['texture_validated'] is False
    texture = dict(face='+z', camera='oak4', capture_id=capture['id'],
                   corners=[[.1, .8], [.9, .8], [.9, .2], [.1, .2]])
    with pytest.raises(ValueError, match='outward-face order'):
        scans.action(identifier, 'texture', dict(texture, corners=texture['corners'][::-1]))
    scans.action(identifier, 'texture', texture)

    if not (scans.workspace / '.venvs/oak-model/bin/python').is_file():
        pytest.skip('Workstation CAD exporter environment is unavailable')
    scans.action(identifier, 'publish', {})
    scan = wait(scans, identifier)
    assert scan['status'] == 'ready', scan['error']
    asset, = scans.assets()
    assert asset['id'] == identifier and asset['manipulation_approved'] is False
    assert asset['model']['textured_faces'] == ['+z'] and asset['model']['dimensions_mm'] == [600, 38, 89]
    model_path, media = scans.artifact(identifier, asset['model']['url'].partition('/files/')[2])
    assert model_path.read_bytes()[:4] == b'glTF' and media == 'model/gltf-binary'
    scans.action(identifier, 'capture', dict(label='Bottom', camera_ids=['oak4']))
    scan = wait(scans, identifier)
    assert scan['coverage'] is None and not scan['publish_available']
    assert scans.assets() == [asset]


def test_running_work_prevents_mutation_and_orphan_is_recoverable(tmp_path):
    started, finish = Event(), Event()

    class SlowCamera(TestImages):
        def capture(self, *args, **kwargs):
            started.set()
            if not finish.wait(4):
                raise RuntimeError('Did not release the test camera')
            return super().capture(*args, **kwargs)

    scans = Scans(tmp_path / 'object-scans', tmp_path, perception=SlowCamera())
    identifier = new_scan(scans)
    scans.action(identifier, 'capture', dict(label='Top'))
    try:
        assert started.wait(4) and scans.get(identifier)['status'] == 'capturing'
        with pytest.raises(RuntimeError, match='Another operation'):
            scans.action(identifier, 'dimensions', dict(dimensions_mm=[600, 39, 88]))
    finally:
        finish.set()
    assert wait(scans, identifier)['status'] == 'ready'
    path = scans.directory / identifier / 'session.json'
    write(path, dict(read(path), status='assessing'))
    scan = scans.get(identifier)
    assert scan['status'] == 'error' and 'interrupted' in scan['error']
    assert len(scan['captures']) == 1


def test_cuboid_coverage_rejects_single_visible_face():
    def review(prompt, photos, output, workspace):
        return dict(status='candidate', faces=[dict(face='top', status='covered',
                   views=[photos[0][0]], reason='Visible top')], missing_views=[],
                   repositioning=[], summary='One face is visible.')

    image = dict(camera='oak4', image='/fixture', image_sha256='a' * 64)
    coverage = perception.assess('Beam', [dict(captures=[image])], Path('/unused'),
                                 family='cuboid', reviewer=review)
    assert coverage['status'] == 'more_views'

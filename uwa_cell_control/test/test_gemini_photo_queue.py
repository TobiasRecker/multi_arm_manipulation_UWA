"""Discovery across an already running capture, restart and partial camera sets."""
from contextlib import closing
import hashlib
import json
from pathlib import Path

from uwa_cell_control import gemini_photo_queue as jobs


def test_register_and_discover_completed_camera_originals_once(tmp_path):
    session = tmp_path / 'custom-output/session'
    folder = session / 'set_123'
    wrist = folder / 'left_front'
    wrist.mkdir(parents=True)
    photo = wrist / 'image.jpg'
    photo.write_bytes(b'test-photo')
    board = {'board_id': 'uwa_mobile_a4', 'marker_ids': [75]}
    (session / 'board.json').write_text(json.dumps(board))
    (session / 'acquisition_profile.json').write_text('{}')
    camera = {'sha256': hashlib.sha256(photo.read_bytes()).hexdigest()}
    (wrist / 'record.json').write_text(json.dumps(camera))
    (wrist / 'annotated.jpg').write_bytes(b'overlay')
    # A capture elsewhere in the workspace must never be picked up.
    elsewhere = tmp_path / 'another/session/set_456'
    elsewhere.mkdir(parents=True)
    (elsewhere / 'manifest.json').write_text('{}')
    jobs.register_session(tmp_path, session)
    jobs.register_session(tmp_path, session)
    with closing(jobs.connect(tmp_path)) as db:
        jobs.discover(db)
        assert db.execute('SELECT count(*) FROM photos').fetchone()[0] == 1
        (folder / 'oak4').mkdir()
        (folder / 'oak4/image.png').write_bytes(b'native-full')
        (folder / 'right_front').mkdir()
        (folder / 'right_front/image.jpg').symlink_to(photo)
        records = {'left_front': camera, 'oak4': {'success': False}, 'right_front': {}}
        (folder / 'manifest.json').write_text(json.dumps(dict(board=board, cameras=records, all_captured=False)))
        jobs.discover(db)
    with closing(jobs.connect(tmp_path)) as db:
        jobs.discover(db)
        paths = {Path(row[0]) for row in db.execute('SELECT image FROM photos')}
        assert paths == {photo, folder / 'oak4/image.png'}
        status = json.loads((folder / 'gemini-charuco/status.json').read_text())
        assert set(status['cameras']) == {'left_front', 'oak4'}


def test_completed_requires_matching_model_and_original_evidence(tmp_path):
    import pytest
    job = dict(set_dir=str(tmp_path), camera='oak4', sha='a'*64)
    out = jobs.result_dir(job)
    out.mkdir(parents=True)
    result = dict(source_sha256=job['sha'], model_id=jobs.MODEL, verdict='uncertain',
                  status='completed', final_report='coordinates.json')
    jobs.atomic_json(out / 'review.json', result)
    jobs.atomic_json(out / 'coordinates.json', dict(image_sha256='wrong', camera='oak4'))
    with pytest.raises(ValueError, match='different photo'):
        jobs.checked_review(job)
    jobs.atomic_json(out / 'coordinates.json', dict(image_sha256=job['sha'], camera='oak4'))
    assert jobs.checked_review(job) == 'uncertain'

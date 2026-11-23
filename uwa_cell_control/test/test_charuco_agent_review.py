"""Validate the boundary between a model assessment and native OpenCV evidence."""
import argparse
import json
from pathlib import Path
import sys

import pytest

TOOL = Path(__file__).resolve().parents[2] / 'tools/charuco_agent'
sys.path.insert(0, str(TOOL))
import review


def board(name, usable=True):
    return dict(board_id=name, status='partial', usable=usable, full=False,
                markers=[dict(id=78, corners_px=[[1, 2], [3, 2], [3, 4], [1, 4]])],
                charuco=[], review_required=False)


def test_final_geometry_comes_only_from_each_selected_measured_pass():
    primary, second = board('mobile'), board('left')
    passes = [dict(boards=[primary, second], roi=[0, 0, 200, 200], schema_version=1),
              dict(boards=[dict(primary, markers=[]), dict(second, full=True)], roi=[4, 7, 80, 80])]
    response = dict(action='final', boards=[
        dict(board_id='mobile', verdict='confirmed', reason='marker shape matches', **{'pass': 1}),
        dict(board_id='left', verdict='uncertain', reason='partial overlap', **{'pass': 2})])
    assessments, final, verdict = review.checked_result(response, passes, ['mobile', 'left'])
    assert verdict == 'uncertain'
    assert final['boards'][0]['markers'] == primary['markers']
    assert final['boards'][1]['full'] and not final['boards'][1]['reviewed_usable']
    assert 'roi' not in final
    assert final['evidence_source_passes'] == {'mobile': 1, 'left': 2}
    assert len(assessments) == 2
    response['boards'][0]['points'] = [[800, 900]]
    with pytest.raises(ValueError):
        review.checked_result(response, passes, ['mobile', 'left'])


def test_valid_absence_requires_no_evidence_across_passes_and_no_ambiguity():
    target = board('test')
    empty = dict(target, status='not_detected', markers=[])
    answer = dict(action='final', boards=[dict(board_id='test', verdict='not_visible', reason='foreign target', **{'pass': 2})])
    with pytest.raises(ValueError, match='absence'):
        review.checked_result(answer, [dict(boards=[target]), dict(boards=[empty])], ['test'])
    answer['boards'][0].update(verdict='confirmed', **{'pass': 1})
    with pytest.raises(ValueError, match='ambiguous'):
        review.checked_result(answer, [dict(boards=[dict(target, status='ambiguous')])], ['test'])
    with pytest.raises(ValueError):
        review.checked_result(dict(action='final', boards=[]), [dict(boards=[target])], ['test'])


def test_model_regions_refer_to_original_sensor_coordinates():
    assert review.roi_pixels([100, 10, 200, 90], (8000, 6000)) == [800, 60, 800, 480]
    assert review.quad_pixels([0, 0, 1000, 0, 1000, 1000, 0, 1000], (8000, 6000)) == [
        0, 0, 7999, 0, 7999, 5999, 0, 5999]
    with pytest.raises(ValueError):
        review.quad_pixels([0, 0, 1000, 0, 0, 1000, 1000, 1000], (8000, 6000))
    with pytest.raises(ValueError):
        review.roi_pixels([-1, 0, 50, 50], (8000, 6000))


def test_input_hash_mismatch_does_not_contact_model(tmp_path, monkeypatch):
    def unexpected(*a, **kw):
        pytest.fail('Detector must not run without matching original identity')
    monkeypatch.setattr(review, 'run_tool', unexpected)
    image = tmp_path / 'photo'
    image.write_bytes(b'wrong original')
    args = argparse.Namespace(image=image, board=tmp_path/'unused', camera='oak4', out=tmp_path/'out',
                              workspace=tmp_path, expect_sha256='a'*64)
    assert review.run(args) == 1
    status = json.loads((args.out/'review.json').read_text())
    assert status['status'] == 'failed' and 'SHA-256' in status['error']
    assert not (args.out/'final-report.json').exists()


def test_incomplete_model_response_does_not_publish_geometry(tmp_path, monkeypatch):
    from PIL import Image
    image = tmp_path / 'photo.png'
    Image.new('RGB', (80, 64)).save(image)
    config = tmp_path/'board.json'
    config.write_text(json.dumps(dict(board_id='mobile')))
    args = argparse.Namespace(image=image, board=config, camera='oak4', out=tmp_path/'out',
                              workspace=tmp_path, expect_sha256=None)
    monkeypatch.setattr(review, 'run_tool', lambda *a, **kw: (dict(image_size=[80, 64]), None))
    async def incomplete(*a):
        raise ValueError('Incomplete final Hydrogen response')
    monkeypatch.setattr(review, 'supervise', incomplete)
    assert review.run(args) == 1
    assert json.loads((args.out/'review.json').read_text())['status'] == 'failed'
    assert not (args.out/'final-report.json').exists()


def test_real_wire_protocol_requests_native_recovery_and_selects_measured_points(tmp_path, monkeypatch):
    from PIL import Image

    image = tmp_path/'image.png'
    Image.new('RGB', (200, 100), 'white').save(image)
    cfg = tmp_path/'board.json'
    cfg.write_text(json.dumps(dict(board_id='mobile', marker_ids=[78])))
    args = argparse.Namespace(image=image, board=cfg, camera='left_front', out=tmp_path/'out',
                              workspace=tmp_path, expect_sha256=review.digest(image))
    calls = []

    def tool(args, sha, number, *, roi=None, quad=None):
        calls.append((number, roi, quad))
        evidence = board('mobile')
        evidence.update(duplicate_ids=[], outlier_ids=[], foreign_ids=[])
        if number == 2:
            evidence['markers'][0]['id'] = 80
        data = dict(image_size=[200, 100], boards=[evidence], camera=args.camera, image_sha256=sha,
                    roi=roi or [0, 0, 200, 100], board_sha256="fixture-board")
        if number == 3:
            data["fusion"] = dict(accepted=True, boards={"mobile": "Combines two genuine detections"})
        return data, image

    monkeypatch.setattr(review, 'run_tool', tool)
    agy = tmp_path/'setup/agent_tools/antigravity/agy'
    agy.parent.mkdir(parents=True)
    agy.write_text("""#!/usr/bin/env python3
import json,sys
def send(payload):
    print(json.dumps(dict(jsonrpc='2.0', **payload)), flush=True)
turns = 0
for line in sys.stdin:
    req = json.loads(line)
    method, params = req['method'], req['params']
    if method == 'initialize':
        value = {'agentCapabilities': {'promptCapabilities': {'image':True}}}
    elif method == 'session/new':
        assert params['mcpServers'] == []
        value = {'sessionId':'fixture-ACP-session'}
    elif method == 'session/set_config_option':
        assert params['value'] == ('gemini-4-hydrogen' if params['configId']=='model' else 'high')
        value = {'configOptions':[{'id':'model','currentValue':'gemini-4-hydrogen'},{'id':'thought_level','currentValue':'high'}]}
    elif method == 'session/prompt':
        assert any(b['type']=='image' and len(b['data'])>100 for b in params['prompt'])
        response = ({'action':'retry','roi':[100,200,800,800],'reason':'check the distant target'}
                    if turns == 0 else {'action':'final','boards':[{'board_id':'mobile','pass':2,
                        'verdict':'confirmed','reason':'decodes align on the printed board'}]})
        turns += 1
        send({'method':'session/update','params':{'sessionId':params['sessionId'],'update':{
            'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':json.dumps(response)}}}})
        value = {'stopReason':'end_turn'}
    else:
        raise ValueError(method)
    send({'id':req['id'],'result':value})
""")
    agy.chmod(0o700)
    assert review.run(args) == 0
    assert calls == [(1, None, None), (2, [20, 20, 140, 60], None), (3, None, None)]
    result = json.loads((args.out/'review.json').read_text())
    evidence = json.loads((args.out/result['final_report']).read_text())
    assert result['status'] == 'completed' and len(result['turns']) == 2
    assert result['selected_model'] == review.MODEL and result['selected_effort'] == review.EFFORT
    assert evidence['boards'][0]['markers'][0]['id'] == 80
    assert evidence['roi'] == [20, 20, 140, 60]


def test_confirmed_partial_evidence_keeps_the_original_usability_threshold():
    partial = dict(board('mobile', usable=False), review_required=True, charuco=[],
                   duplicate_ids=[], conflicting_ids=[], outlier_ids=[88])
    response = dict(action='final', boards=[dict(board_id='mobile', verdict='confirmed',
        reason='Retained marker lies squarely on the tilted checkerboard. Distractor 88 is excluded.',
        **{'pass': 1})])
    _, result, verdict = review.checked_result(response, [dict(boards=[partial])], ['mobile'])
    assert verdict == 'confirmed'
    assert result['boards'][0]['review_required']
    assert not result['boards'][0]['usable'] and not result['boards'][0]['reviewed_usable']
    for conflict in ('duplicate_ids', 'conflicting_ids'):
        partial[conflict] = [78]
        with pytest.raises(ValueError, match='ambiguous'):
            review.checked_result(response, [dict(boards=[partial])], ['mobile'])
        partial[conflict] = []


def test_model_can_select_only_a_verified_fusion_for_this_board():
    partial = dict(boards=[board('mobile')])
    fusion = dict(boards=[dict(board('mobile'), full=True, status='full')],
                  fusion=dict(accepted=True, boards=dict(mobile='accepted')))
    response = dict(action='final', boards=[dict(board_id='mobile', verdict='confirmed',
                                                 reason='complementary marker overlays agree', **{'pass': 3})])
    _, final, _ = review.checked_result(response, [partial, partial, fusion], ['mobile'])
    assert final['boards'][0]['status'] == 'full'
    fusion['fusion']['boards']['mobile'] = 'no_gain'
    with pytest.raises(ValueError, match='verified fusion'):
        review.checked_result(response, [partial, partial, fusion], ['mobile'])


def test_reusing_model_region_requires_same_board_photo_and_actual_completed_review(tmp_path):
    config_path = tmp_path/'review.json'
    atomic = review.atomic_json
    args = argparse.Namespace(camera='right_rear')
    prior = dict(status='completed', selected_model=review.MODEL, selected_effort='high',
                 source_sha256='original', camera='right_rear', session_id='real-acp',
                 turns=[dict(action='retry', roi=[0, 0, 500, 500], reason='visible print'),
                        dict(action='final', boards=[])])
    atomic(config_path, prior)
    atomic(tmp_path/'pass-1.json', {'board_sha256':'board'})
    assert review.previous_region(config_path, args, 'original', {'board_sha256':'board'}) == prior['turns'][0]
    with pytest.raises(ValueError):
        review.previous_region(config_path, args, 'different', {'board_sha256':'board'})
    with pytest.raises(ValueError):
        review.previous_region(config_path, args, 'original', {'board_sha256':'different'})


def test_frozen_runner_executes_the_same_method_bytes_after_source_changes(tmp_path, monkeypatch):
    source = tmp_path/'source'
    source.mkdir()
    (source/'GEMINI.md').write_text('old prompt')
    (source/'detect.py').write_text('old code')
    script = """
from pathlib import Path
import json, hashlib
def run(args):
    root = Path(__file__).parent
    names = ('review.py', 'detect.py', 'GEMINI.md')
    for n in names:
        (args.workspace/'source'/n).write_text('updated while in flight')
    sha = {n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}
    (args.out/'fixture-hashes.json').write_text(json.dumps(sha))
    return 0
"""
    (source/'review.py').write_text(script)
    monkeypatch.setattr(review, 'HERE', source)
    board_file = tmp_path/'board.json'
    board_file.write_text('{}')
    args = argparse.Namespace(workspace=tmp_path, out=tmp_path/'out', board=board_file)
    expected = {name: review.digest(source/name) for name in review.METHOD_FILES}
    assert review.run_frozen_job(args) == 0
    assert json.loads((args.out/'fixture-hashes.json').read_text()) == expected


def test_completed_review_is_retained_after_tool_update_without_model_request(tmp_path):
    import hashlib
    photo = tmp_path/'original.jpg'
    photo.write_bytes(b'original-image-for-idempotence')
    board_file = tmp_path/'board.json'
    board_file.write_text('{"board_id": "mobile"}')
    out = tmp_path/'out'
    out.mkdir()
    sha = review.digest(photo)
    receipt = dict(status='completed', camera='oak4', selected_effort='high', model_id=review.MODEL,
                   selected_model=review.MODEL, session_id='test-session', verdict='not_visible',
                   source_sha256=sha, final_report='final-report-revision-2.json')
    # Historical receipts can predate method hashing. Never assign today's code
    # hashes retrospectively or re-upload an already reviewed original.
    review.atomic_json(out/'review.json', receipt)
    review.atomic_json(out/receipt['final_report'], dict(image_sha256=sha, camera='oak4',
        board_sha256=hashlib.sha256(b'{"board_id":"mobile"}').hexdigest()))
    args = argparse.Namespace(workspace=tmp_path/'no-client', out=out, board=board_file, image=photo,
                              expect_sha256=sha, camera='oak4')
    assert review.run_frozen_job(args) == 0
    assert json.loads((out/'review.json').read_text()) == receipt
    board_file.write_text('{"board_id":"different"}')
    with pytest.raises(ValueError, match='different input'):
        review.run_frozen_job(args)
    assert json.loads((out/'review.json').read_text()) == receipt

    board_file.write_text('{"board_id":"mobile"}')
    for changes in (dict(final_report='../outside.json'), dict(final_report='..'), dict(session_id=' '),
                    dict(selected_model='unsupported')):
        review.atomic_json(out/'review.json', dict(receipt, **changes))
        with pytest.raises(ValueError, match='different input'):
            review.already_completed(args)

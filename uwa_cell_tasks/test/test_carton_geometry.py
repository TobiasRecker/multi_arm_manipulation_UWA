import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
import carton_geometry as geometry
import carton_geometry_agent as agent


def fixture():
    # Calibrated camera above the table, looking down. One unequal mesh corner.
    ctx = dict(K=[[1200, 0, 800], [0, 1200, 600], [0, 0, 1]], D=[0]*5,
               image_size=[1600, 1200], image_window=[0, 0, 1600, 1200],
               T_camera_table=[[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 2], [0, 0, 0, 1]],
               model_corners_m=[[0, 0, .163], [.404, 0, .163], [.404, .342, .159], [0, .342, .163]])
    angle = .47
    R = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    model = np.array(ctx['model_corners_m'])
    points = model.copy()
    points[:, :2] = model[:, :2] @ R.T + [-.25, -.2]
    T = np.array(ctx['T_camera_table'])
    camera = points @ T[:3, :3].T + T[:3, 3]
    pixels = camera[:, :2]/camera[:, 2, None]*1200 + [800, 600]
    yx = np.rint((pixels/[1600, 1200]*1000)[:, ::-1]).astype(int).tolist()
    return ctx, yx, points[:, :2].mean(0)


@pytest.mark.parametrize('reverse,shift', [(a, b) for a in [False, True] for b in range(4)])
def test_recovers_current_metric_centre_from_cyclic_landmarks(reverse, shift):
    ctx, corners, centre = fixture()
    corners = np.roll(np.asarray(corners)[::-1] if reverse else corners, shift, axis=0).tolist()
    result = geometry.evaluate(ctx, corners)
    assert result['success']
    T = np.array(result['T_table_object'])
    recovered = T[:2, :2] @ np.array(ctx['model_corners_m'])[:, :2].mean(0) + T[:2, 3]
    assert np.linalg.norm(recovered-centre) < .002
    assert max(result['corner_error_mm']) < 2
    assert not result['absolute_accuracy_validated']


def test_bad_B_is_rejected_without_silently_dropping_it():
    ctx, corners, _ = fixture()
    corners[1][1] += 55
    result = geometry.evaluate(ctx, corners)
    assert not result['success']
    assert len(result['corner_error_mm']) == 4
    assert result['max_corner_error_mm'] > 10


def test_landmarks_around_one_wall_are_not_accepted_as_the_whole_rim():
    ctx, corners, _ = fixture()
    corners[2] = [int(.8*corners[1][0]+.2*corners[2][0]), corners[2][1]]
    result = geometry.evaluate(ctx, corners)
    assert not result['success']


@pytest.mark.parametrize('corners', [None, [[0, 0]]*4,
    [[0, 0], [1000, 1000], [0, 1000], [1000, 0]],
    [[0, 0], [0, 1001], [1000, 1000], [1000, 0]],
    [[0., 0], [0, 1000], [1000, 1000], [1000, 0]]])
def test_rejects_invalid_image_coordinates(corners):
    with pytest.raises(ValueError):
        geometry.checked_corners(corners)


def test_feedback_contains_no_absolute_pose_or_robot_coordinates():
    ctx, corners, _ = fixture()
    feedback = geometry.model_feedback(ctx, geometry.evaluate(ctx, corners))
    assert feedback['success']
    assert 'T_table_object' not in feedback and 'T_camera_table' not in feedback
    assert len(feedback['projected_rim_corners_2d']) == 4


def test_mesh_landmarks_preserve_the_real_unequal_corner_height():
    p = Path(__file__).resolve().parents[2]/'uwa_cell_description/assets/carton_avocado_v1/asset.json'
    points = geometry.mesh_landmarks(p)
    assert points.shape == (4, 3)
    assert .003 < np.ptp(points[:, 2]) < .005


@pytest.mark.parametrize('answer', [dict(action='submit', measurement_id='x', path='/tmp/x'),
    dict(action='execute', command='move'), dict(action='check_geometry', rim_corners_2d=[[0, 0]]*4)])
def test_geometry_actions_cannot_request_files_or_commands(answer):
    with pytest.raises(ValueError):
        agent.parse_action(json.dumps(answer))


def test_model_must_call_checker_before_submitting(tmp_path, monkeypatch):
    ctx, corners, _ = fixture()
    image = tmp_path/'image.png'
    cv2.imwrite(str(image), np.zeros((1200, 1600, 3), np.uint8))
    replies = iter([dict(action='submit', measurement_id='geometry-1'),
                    dict(action='locate_box',box_2d=[0,0,1000,1000]),
                    dict(action='check_geometry', rim_corners_2d=corners),
                    dict(action='submit', measurement_id='geometry-1')])
    prompts = []

    class Client:
        def __init__(self, process): self.text=[]; self.used_tools=False
        async def request(self, method, params):
            if method=='initialize': return {'agentCapabilities': {'promptCapabilities': {'image': True}}}
            if method=='session/new':
                assert params['mcpServers']==[]
                return {'sessionId':'geometry'}
            if method=='session/set_config_option': return {'configOptions':[
                {'id':'model','currentValue':agent.MODEL},{'id':'thought_level','currentValue':agent.EFFORT}]}
            prompts.append(params['prompt'])
            self.text.append(json.dumps(next(replies)))
            return {'stopReason':'end_turn'}
    async def spawn(*args, **kwargs):
        async def communicate(): pass
        return SimpleNamespace(stdin=SimpleNamespace(close=lambda:None),communicate=communicate)
    monkeypatch.setattr(agent.asyncio,'create_subprocess_exec',spawn)
    result=asyncio.run(agent.observe(image,ctx,tmp_path,client_factory=Client))
    assert result['measurement_id']=='geometry-1'
    assert 'Submit must reference' in prompts[1][0]['text']
    assert 'check_geometry' in prompts[3][0]['text']
    assert len(prompts[2])==2
    audit=json.loads((tmp_path/'hydrogen-geometry.json').read_text())
    assert all('raw_response' in r for r in audit['rounds'])

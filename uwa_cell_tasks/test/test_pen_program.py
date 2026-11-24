"""Pen geometry, fallback contract and library/review isolation; no camera or robot calls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools'))
import pen_grasp_vision as vision
import run_pen_program as runner
from uwa_cell_tasks.motion_review import ReviewStore,TASK

spec=importlib.util.spec_from_file_location('pen_library',REPO/'scripts/skill_library_server.py')
library=importlib.util.module_from_spec(spec);spec.loader.exec_module(library)
DEFINITION=json.loads((REPO/'config/pen_programs/pen-left-rear-v1.json').read_text())


def synthetic():
    optics=dict(device_id='18443010314F3B1300',focus=112,image_size=[4056,3040],K=[[3000,0,2028],[0,3000,1520],[0,0,1]],D=[0]*5)
    # Camera looks down at the upright pen; the side is visible at an oblique angle.
    Twc=np.eye(4);Twc[:3,:3]=Rotation.from_euler('xyz',[150,0,15],degrees=True).as_matrix();Twc[:3,3]=[0,-.5,1.6]
    Two=np.eye(4);Two[:3,:3]=Rotation.from_euler('z',.4).as_matrix();Two[:3,3]=[0,0,.5]
    Tco=np.linalg.inv(Twc)@Two
    points=vision.marker_points(DEFINITION,1,3)
    pixels=cv2.projectPoints(points,cv2.Rodrigues(Tco[:3,:3])[0],Tco[:3,3],np.array(optics['K'],float),np.zeros(5))[0].reshape(-1,2)
    return optics,Twc,Two,pixels


def test_two_perpendicular_markers_recover_metric_pose_and_code_rotations(monkeypatch):
    optics,Twc,Two,pixels=synthetic()
    monkeypatch.setattr(vision,'detect',lambda *a:({97:pixels[:4],96:pixels[4:]},{'ids':[97,96]}))
    pose,_=vision.locate(np.zeros((3040,4056,3),np.uint8),optics,Twc,DEFINITION)
    assert np.allclose(pose['T_world_adapter'],Two,atol=1e-7)
    assert pose['quarter_turns']==[1,3] and pose['reprojection_rms_px']<1e-6


def test_no_pose_from_missing_marker_or_unconfirmed_mount(monkeypatch):
    optics,Twc,_,pixels=synthetic()
    monkeypatch.setattr(vision,'detect',lambda *a:({97:pixels[:4]},{}))
    with pytest.raises(ValueError,match='Both pen markers'):vision.locate(None,optics,Twc,DEFINITION)
    definition=copy.deepcopy(DEFINITION);definition['mount']['centered_confirmed']=False
    with pytest.raises(ValueError,match='mounting'):vision.locate(None,optics,Twc,definition)


def test_bad_two_marker_geometry_cannot_be_accepted(monkeypatch):
    optics,Twc,_,pixels=synthetic();pixels[4:]+=np.array([0,100])
    monkeypatch.setattr(vision,'detect',lambda *a:({97:pixels[:4],96:pixels[4:]},{}))
    with pytest.raises(ValueError):vision.locate(np.zeros((3040,4056,3),np.uint8),optics,Twc,DEFINITION)


def test_duplicate_ids_rejected_in_native_image(monkeypatch):
    detector=Mock();detector.detectMarkers.return_value=([np.zeros((1,4,2)),np.ones((1,4,2))],np.array([[97],[97]]),[])
    monkeypatch.setattr(cv2.aruco,'ArucoDetector',lambda *a:detector)
    with pytest.raises(ValueError,match='Duplicate'):vision.detect(np.zeros((3040,4056,3),np.uint8),DEFINITION)


@pytest.mark.parametrize('raw',[ '{"status":"found","box_2d":[800,100,400,200]}',
    '{"status":"found","box_2d":[100,100,200,200],"metric_pose":[1,2,3]}',
    '{"status":"absent","box_2d":null}' ])
def test_gemini_cannot_supply_robot_pose_or_invalid_box(raw):
    with pytest.raises(ValueError):vision.parse_roi(raw)


def test_gemini_roi_is_raw_sensor_orientation():
    assert vision.parse_roi('{"status":"found","box_2d":[100,200,300,400]}')==[751,244,1683,972]


def test_fallback_only_guides_native_opencv_remeasurement(tmp_path,monkeypatch):
    image=tmp_path/'native.png';image.write_bytes(b'original-image')
    monkeypatch.setattr(cv2,'imread',lambda _:np.zeros((3040,4056,3),np.uint8))
    monkeypatch.setattr(cv2,'imwrite',lambda *a:True)
    calls=[]
    def measure(im,optics,frame,definition,roi=None):
        calls.append(roi)
        if roi is None:raise ValueError('Occluded in full-frame pass')
        return dict(status='POSE_CANDIDATE'),im
    async def fallback(im,out,reason):return [10,20,100,200]
    monkeypatch.setattr(vision,'locate',measure)
    result=vision.perceive(image,{},np.eye(4),DEFINITION,tmp_path/'result',fallback=fallback)
    assert calls==[None,[10,20,100,200]]
    assert result['image_sha256']==hashlib.sha256(b'original-image').hexdigest()
    assert result['attempts'][-1]['method']=='gemini_roi_opencv_remeasurement'


def test_library_pen_uses_own_availability_not_carton_reference(tmp_path,monkeypatch):
    monkeypatch.setattr(library,'pen_availability',lambda enabled:dict(live_available=enabled,inspect_available=True,live_blocker=None))
    runs=library.Runs(tmp_path,live_config=tmp_path/'live.json')
    monkeypatch.setattr(runs,'camera_status',lambda:dict(calibrate_available=False,live_blocker='OAK4 expired'))
    card=next(p for p in runs.catalog()['programs'] if p['id']==runner.PROGRAM)
    assert card['live_available'] and card['arms']==['Left rear']
    popen=Mock(return_value=Mock(pid=123))
    monkeypatch.setattr(library.subprocess,'Popen',popen);monkeypatch.setattr(library,'Thread',Mock());monkeypatch.setattr(library,'process_stamp',lambda _: 'test')
    runs.start(runner.PROGRAM,'live')
    assert popen.call_args.args[0][1]==str(REPO/'tools/run_pen_program.py')


def test_mock_library_cannot_start_real_pen_movement(tmp_path,monkeypatch):
    monkeypatch.setattr(library,'pen_availability',lambda enabled:dict(live_available=enabled,inspect_available=True,live_blocker='N100 required'))
    with pytest.raises(ValueError,match='N100'):library.Runs(tmp_path).start(runner.PROGRAM,'live')


def test_pen_review_is_separate_from_carton_trust_and_explicit(tmp_path):
    store=ReviewStore(tmp_path);store.area('new',True);store.settings(task=TASK,trust=100)
    meta=dict(task='pen_holder_grasp',stage='motion',risk='high',reason='First pen task',components=['a'*64],
              speed_percent=store.status()['settings']['speed_percent'],arms=['left_rear'],duration_s=1,summary='Pen')
    identifier=store.submit('pen/motion',meta,dict(groups=[]))
    assert not store.claim(identifier)  # Carton trust never authorizes a new pen contact.
    row=store.status()['pending'][0];store.decide(identifier,row['sha256'],'approve')
    assert store.claim(identifier)
    store.begin_component(identifier,'a'*64)
    with pytest.raises(ValueError):store.begin_component(identifier,'a'*64)
    store.finish(identifier,True)
    assert store.status(task='pen_holder_grasp')['settings']['trust']==0

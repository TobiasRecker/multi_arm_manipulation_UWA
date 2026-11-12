from copy import deepcopy
import hashlib

import cv2
import numpy as np
import pytest

from uwa_cell_gazebo.configuration import load_layout,joint_names,ROBOT_IDS
from uwa_cell_gazebo.charuco import board_image,make_board
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_control.hardware_charuco import first_view,observe,calibrate_intrinsics
from uwa_cell_control.parking import make_model


@pytest.mark.parametrize('rid',ROBOT_IDS)
def test_hardware_cli_accepts_each_cell_arm_without_invoking_hardware(monkeypatch,tmp_path,rid):
    import sys
    import uwa_cell_control.handeye_hardware as command
    received=[]
    monkeypatch.setattr(command,'plan_view',lambda args:received.append(args.arm))
    monkeypatch.setattr(sys,'argv',['handeye_hardware','plan-view','--arm',rid,'--output',str(tmp_path)])
    assert command.main()==0
    assert received==[rid]


def test_board_corners_are_detected_without_nominal_intrinsics_and_wrong_board_is_not_accepted():
    config=load_layout()['charuco']
    picture=cv2.cvtColor(board_image(config,'right'),cv2.COLOR_GRAY2BGR)
    observation=observe(picture,config,'right')
    assert observation['corners']==24
    assert set(observation['marker_ids'])==set(range(50,67))
    assert len(observation['object_points'])==24
    assert observe(picture,config,'left')['corners']==0


@pytest.fixture(scope='module')
def intrinsic_observations():
    config=load_layout()['charuco'];objects=make_board(config,'right').getChessboardCorners()
    k=np.array([[650.,0,321.],[0,645.,239.],[0,0,1.]])
    d=np.array([-.08,.035,.001,-.001,0.])
    rng=np.random.default_rng(581);records=[]
    for i in range(40):
        rv=rng.uniform(-.45,.45,3);tv=np.array([-.12,-.08,rng.uniform(.48,.8)])
        tv[:2]+=rng.uniform(-.07,.07,2)
        pixels=cv2.projectPoints(objects,rv,tv,k,d)[0].reshape(-1,2)+rng.normal(0,.025,(len(objects),2))
        records.append({'sample_id':f'sample_{i:03d}','role':'validation' if i%5==4 else 'fit',
            'corners':len(objects),'image_size':[640,480],'object_points':objects.tolist(),
            'image_points':pixels.tolist(),'pixel_sha256':hashlib.sha256(str(i).encode()).hexdigest(),
            'camera_settings':{'focus':404,'focusAuto':False}})
    return records,k


def test_intrinsic_fit_recovers_k_and_held_out_views_never_fit_camera_matrix(intrinsic_observations):
    records,k=intrinsic_observations
    first=calibrate_intrinsics(records,focus=404,image_size=[640,480])
    np.testing.assert_allclose(first['camera_matrix'],k,atol=1.5)
    assert first['fit_count']==32 and first['validation_count']==8
    changed=deepcopy(records)
    for r in changed:
        if r['role']=='validation':r['image_points']=(np.array(r['image_points'])+[.2,.1]).tolist()
    second=calibrate_intrinsics(changed,focus=404,image_size=[640,480])
    np.testing.assert_allclose(first['camera_matrix'],second['camera_matrix'],atol=1e-12)


def test_changed_focus_duplicate_frames_and_bad_validation_do_not_produce_intrinsics(intrinsic_observations):
    records,_=intrinsic_observations
    changed=deepcopy(records);changed[-1]['camera_settings']['focus']=405
    with pytest.raises(ValueError,match='Focus changed'):calibrate_intrinsics(changed,focus=404,image_size=[640,480])
    changed=deepcopy(records);changed[-1]['pixel_sha256']=changed[0]['pixel_sha256']
    with pytest.raises(ValueError,match='Repeated'):calibrate_intrinsics(changed,focus=404,image_size=[640,480])
    changed=deepcopy(records)
    for r in changed:
        if r['role']=='validation':r['image_points']=(np.array(r['image_points'])+np.random.default_rng(24).normal(0,4,(24,2))).tolist()
    with pytest.raises(ValueError,match='validation'):calibrate_intrinsics(changed,focus=404,image_size=[640,480])


@pytest.mark.parametrize('rid',['right_rear','left_rear'])
def test_first_view_ik_and_full_moveit_sweep_keep_other_arms_fixed(tmp_path,rid):
    layout=load_layout();profiles={r:{'ur_type':a['type'],'kinematics_file':None} for r,a in layout['robots'].items()}
    model,layout=make_model(layout,profiles,tmp_path)
    start={j:q for rid,r in layout['robots'].items() for j,q in zip(joint_names(rid),r['initial_positions'])}
    # Starting nearby but different gives a real motion path, not only a no-op.
    start[rid+'_shoulder_pan_joint']-=.15
    plan=first_view(model,layout,rid,start)
    q=dict(start,**dict(zip(plan['joint_names'],plan['target'])))
    actual=Chain(model.description,'world',rid+'_wrist_camera_optical_frame').forward(q)
    np.testing.assert_allclose(actual,plan['nominal_camera_target_world'],atol=1e-5)
    for point in plan['points']:
        state=dict(start,**dict(zip(plan['joint_names'],point['positions'])))
        assert model.check(state)[0]
        assert all(state[j]==start[j] for r in ROBOT_IDS if r!=rid for j in joint_names(r))

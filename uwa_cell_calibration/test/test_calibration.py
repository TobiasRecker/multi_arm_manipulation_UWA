from copy import deepcopy
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from uwa_cell_gazebo.configuration import load_layout,render_description,joint_names,ROBOT_IDS
from uwa_cell_gazebo.charuco import make_board,transform,pose_error
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_calibration.model import CollisionModel,calibrated_description
from uwa_cell_calibration.planner import generate_plan,timed_path
from uwa_cell_calibration.solver import solve_session,solve_robot
from uwa_cell_calibration.storage import validate_result,fingerprint


@pytest.fixture(scope='module')
def data(tmp_path_factory):
    directory=tmp_path_factory.mktemp('calibration')
    layout=load_layout();description=render_description(layout,directory)[0]
    model=CollisionModel(description,directory)
    start={j:v for rid,r in layout['robots'].items() for j,v in zip(joint_names(rid),r['initial_positions'])}
    k=np.array([[686.242218,0,320],[0,686.242218,240],[0,0,1.]])
    matrices={r:{'k':k.tolist(),'width':640,'height':480} for r in ROBOT_IDS}
    plans=generate_plan(model,layout,start,matrices,list(ROBOT_IDS),40)
    records,truth={},{}
    rng=np.random.default_rng(55)
    for rid in ROBOT_IDS:
        chain=Chain(description,f'{rid}_base_link',f'{rid}_tool0')
        x=Chain(description,f'{rid}_tool0',f'{rid}_wrist_camera_optical_frame').forward({}) @ transform([.003,-.002,.002],[.025,-.015,.02])
        world_base=Chain(description,'world',f'{rid}_base_link').forward({})
        world_board=Chain(description,'world',layout['robots'][rid]['table']+'_charuco').forward({})
        y=np.linalg.inv(world_base)@world_board@transform([.008,-.006,.004],[.01,-.02,.015])
        truth[rid]={'x':x,'y':y}
        objects=make_board(layout['charuco'],layout['robots'][rid]['table']).getChessboardCorners().astype(float)
        records[rid]=[]
        for i,pose in enumerate(plans[rid]['poses']):
            m=chain.forward(dict(zip(joint_names(rid),pose['joints'])))
            camera=np.linalg.inv(m@x)@y
            pixels=cv2.projectPoints(objects,cv2.Rodrigues(camera[:3,:3])[0],camera[:3,3],k,np.zeros(5))[0].reshape(-1,2)
            pixels+=rng.normal(0,.035,pixels.shape)
            ok,rvec,tvec=cv2.solvePnP(objects,pixels,k,np.zeros(5))
            assert ok
            observed=np.eye(4);observed[:3,:3]=cv2.Rodrigues(rvec)[0];observed[:3,3]=tvec.ravel()
            records[rid].append({'sample_id':f'sample_{i:03d}','role':pose['role'],'T_base_tool0':m.tolist(),
                'T_camera_board':observed.tolist(),'object_points':objects.tolist(),'image_points':pixels.tolist(),
                'camera_matrix':k.tolist(),'distortion':[0.]*5})
    return layout,description,model,start,plans,records,truth


def test_joint_fit_recovers_unknown_handeye_and_relative_bases(data):
    *_,records,truth=data
    result=solve_session(records,bootstrap_count=12)
    assert result['passed']
    assert result['ground_truth_used_for_fit'] is False
    for rid,fit in result['robots'].items():
        error=pose_error(np.array(fit['T_tool0_camera']),truth[rid]['x'])
        assert error['translation_m']<.003,error
        assert error['rotation_deg']<.5,error
        assert fit['fit_count']==32 and fit['validation_count']==8
    for table,pair in result['relative_bases'].items():
        gt=truth[table+'_front']['y']@np.linalg.inv(truth[table+'_rear']['y'])
        error=pose_error(np.array(pair['T_front_rear']),gt)
        assert error['translation_m']<.005,error
        assert error['rotation_deg']<.5,error
    validate_result(result)


def test_held_out_images_cannot_change_the_fit(data):
    records=deepcopy(data[-2]['left_front'])
    baseline=solve_robot(records,bootstrap_count=0)
    for r in records:
        if r['role']=='validation':r['image_points']=(np.array(r['image_points'])+[6,0]).tolist()
        r['ground_truth']='must not be read'
    result=solve_robot(records,bootstrap_count=0)
    assert not result['passed']
    np.testing.assert_allclose(result['T_tool0_camera'],baseline['T_tool0_camera'],atol=1e-9)


def test_outliers_and_degenerate_poses_are_not_silently_accepted(data):
    records=deepcopy(data[-2]['left_front'])
    for r in [r for r in records if r['role']=='fit'][:2]:
        r['image_points']=(np.array(r['image_points'])+[8,-6]).tolist()
    result=solve_robot(records,bootstrap_count=0)
    assert result['passed'] and len(result['excluded_samples'])==2
    bad=deepcopy(records)
    for r in bad:r['T_base_tool0']=bad[0]['T_base_tool0']
    with pytest.raises(ValueError,match='rotations'):solve_robot(bad)


def test_full_cell_paths_limits_and_fixed_split(data):
    layout,description,model,start,plans,*_=data
    assert model.check(start)[0]
    for rid,plan in plans.items():
        assert len(plan['poses'])==40 and len(plan['reserve'])>=8
        assert sum(p['role']=='validation' for p in plan['poses'])==8
        for pose in plan['poses']:
            for point in pose['path']:
                assert max(abs(v) for v in point['velocities'])<=.100001
                assert max(abs(v) for v in point['accelerations'])<=.200001
        # Goal outside native UR joint limits must never yield an executable path.
        with pytest.raises(ValueError):timed_path(model,rid,start,[20]*6)


def test_calibrated_model_is_separate_and_other_arms_are_collision_geometry(data,tmp_path):
    layout,description,model,start,plans,records,truth=data
    result={'robots':{rid:{'T_tool0_camera':truth[rid]['x'].tolist(),'T_base_board':truth[rid]['y'].tolist()} for rid in ROBOT_IDS}}
    changed=calibrated_description(description,layout,result)
    assert 'calibrated/left_front_base_link' in changed
    assert 'calibrated/' not in description
    assert ET.fromstring(changed).find('gazebo') is None
    for rid in ROBOT_IDS:
        actual=Chain(changed,'calibrated/'+rid+'_tool0','calibrated/'+rid+'_wrist_camera_optical_frame').forward({})
        np.testing.assert_allclose(actual,truth[rid]['x'],atol=1e-10)
    original=ET.fromstring(description)
    # Put the second arm on top of the first to prove cross-arm collision checks
    # are retained; fixed table contacts must not disable moving-arm checks.
    a=next(j for j in original.findall('joint') if j.find('child').get('link')=='left_front_base_link')
    b=next(j for j in original.findall('joint') if j.find('child').get('link')=='right_front_base_link')
    b.find('parent').set('link',a.find('parent').get('link'))
    b.find('origin').attrib.update(a.find('origin').attrib)
    collision=CollisionModel(ET.tostring(original,encoding='unicode'),tmp_path)
    assert not collision.check(start)[0]


def test_invalid_profile_is_rejected_before_publication(data):
    result=solve_session({'left_front':data[-2]['left_front']},bootstrap_count=0)
    assert result['passed']
    bad=deepcopy(result);bad['robots']['left_front']['T_tool0_camera'][0][0]*=-1
    with pytest.raises(ValueError):validate_result(bad)
    bad=deepcopy(result);bad['robots']['left_front']['validation']['median_reprojection_rms_px']=10
    with pytest.raises(ValueError):validate_result(bad)


def test_passive_mimic_velocity_does_not_mask_actual_arm_motion():
    from types import SimpleNamespace
    from uwa_cell_calibration.backend import Backend
    state=SimpleNamespace(stop_joints=['arm_joint','gripper_driver'],velocities={'arm_joint':0.,'gripper_driver':0.,'mimic':.2})
    assert Backend.stationary(state)
    state.velocities['arm_joint']=.02
    assert not Backend.stationary(state)


def test_stationary_window_recovers_from_one_transient_velocity_sample():
    import time
    from types import SimpleNamespace
    from uwa_cell_calibration.backend import Backend
    readings=iter([False]+[True]*100)
    state=SimpleNamespace(description='live',last_joints=time.monotonic(),
        positions={j:0. for r in ROBOT_IDS for j in joint_names(r)},state={'phase':'CAPTURING'},
        halted=lambda:False,stationary=lambda:next(readings),velocities={},stop_joints=[])
    started=time.monotonic()
    Backend.require_telemetry(state)
    assert time.monotonic()-started>=.2


def test_failed_model_loading_and_profile_commit_keep_previous_model(data,tmp_path,monkeypatch):
    import threading
    from types import SimpleNamespace
    from uwa_cell_calibration import backend
    result=solve_session({'left_front':data[-2]['left_front']},bootstrap_count=0)
    attempts=[];publications=[]
    class Candidate:
        allowed=False
        def __init__(self,*args):self.cancelled=False;attempts.append(self)
        def call(self,*args):return self.allowed
        def cancel(self):self.cancelled=True
    old=Candidate()
    model=SimpleNamespace(description=data[1],layout=data[0],root=tmp_path,positions=data[3],
        halted=lambda:False,require_telemetry=lambda:None,motion_lock=threading.RLock(),
        planner=old,active_description='previous',model_xml='previous xml',
        description_pub=SimpleNamespace(publish=publications.append))
    monkeypatch.setattr(backend,'PlanningProcess',Candidate)
    with pytest.raises(ValueError,match='collision'):backend.Backend.install_model(model,result)
    assert model.planner is old and model.active_description=='previous' and not old.cancelled
    assert attempts[-1].cancelled and not publications
    Candidate.allowed=True
    def failing_commit():raise OSError('disk unavailable')
    with pytest.raises(OSError):backend.Backend.install_model(model,result,failing_commit)
    assert model.planner is old and not old.cancelled and not publications
    assert attempts[-1].cancelled
    profile_state={'active':'previous'}
    def publish_failure(_):raise RuntimeError('publisher unavailable')
    model.description_pub=SimpleNamespace(publish=publish_failure)
    with pytest.raises(RuntimeError,match='publisher'):
        backend.Backend.install_model(model,result,lambda:profile_state.update(active='new'),
                                     lambda:profile_state.update(active='previous'))
    assert profile_state['active']=='previous' and model.planner is old and not old.cancelled
    assert model.model_xml=='previous xml' and attempts[-1].cancelled


@pytest.mark.parametrize('pause_ack',[True,False])
@pytest.mark.parametrize('stationary,pending',[(False,False),(True,True)])
def test_unconfirmed_stop_and_pending_acceptance_require_pause(monkeypatch,pause_ack,stationary,pending):
    import threading
    from types import SimpleNamespace
    from uwa_cell_calibration import backend
    ticks=iter(np.arange(0,100,.1))
    monkeypatch.setattr(backend,'time',SimpleNamespace(monotonic=lambda:next(ticks),sleep=lambda _:None))
    events=[];requests=[]
    state=SimpleNamespace(shutdown_event=threading.Event(),abort=threading.Event(),last_joints=0.,
        goal_callback_pending=pending,pending_goal=None,motion_handle=None,stationary=lambda:stationary,
        pause_world=lambda:requests.append('pause') or pause_ack,
        status=lambda phase,**values:events.append((phase,values)))
    backend.Backend.confirm_halt(state)
    assert requests==['pause'] and state.abort.is_set()
    assert events[-1][0]=='STOPPED' and events[-1][1]['world_pause_confirmed'] is pause_ack
    assert ('Weder Stillstand' in events[-1][1]['message']) is not pause_ack

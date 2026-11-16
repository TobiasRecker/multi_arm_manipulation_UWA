"""Offline contracts: unknown geometry, metric directions, stale data and replay."""
import json
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from uwa_cell_control.digitization_geometry import vertices,pose,fit,solid_parts
from uwa_cell_control.digitization_job import create,read,save,summary,run_stage,ingest,fit_job,capture,lock,process_job
from uwa_cell_control.digitization_optics import check_optics,sha

POLICY=dict(proxy_width=1600,minimum_fit_views=2,minimum_validation_views=1,
    maximum_fit_rms_proxy_px=3.,maximum_validation_rms_proxy_px=5.,minimum_camera_baseline_m=.05)


def fixture(family='plate_l'):
    known=dict(plate_thickness_m=.01,profile_size_m=.02) if family=='plate_l' else dict(wall_thickness_m=.003)
    p=np.array([.03,-.04,.28,.30,.15,.16]);points=vertices(p,family,known)
    cameras={};annotations=dict(proxy_width=1600,observations={},initial_parameters_board_m_rad=(p+[.01,-.01,.03,.01,-.01,.01]).tolist())
    K=np.array([[1300.,0,1296],[0,1300,972],[0,0,1]])
    for i in range(3):
        T=np.eye(4);T[:3,:3]=Rotation.from_euler('xyz',[2.8,.1,.05]).as_matrix();T[:3,3]=[-.2+i*.2,-.02,1.2]
        name='view'+str(i);pixels=cv2.projectPoints(points,cv2.Rodrigues(T[:3,:3])[0],T[:3,3],K,np.zeros(5))[0].reshape(-1,2)*1600/2592
        cameras[name]=dict(K=K.tolist(),D=[0.]*5,image_size=[2592,1944],observation={'image_size':[2592,1944]},T_camera_board=T.tolist(),image_sha256=name,metric_eligible=True)
        annotations['observations'][name]=dict(ids=list(range(len(points))),pixels=pixels.tolist(),role='validation' if i==2 else 'fit')
    return p,known,cameras,annotations


@pytest.mark.parametrize('family',['plate_l','box_shell'])
def test_recover_unknown_shape_without_using_held_out_pixels(family):
    p,known,cameras,annotations=fixture(family)
    result=fit(cameras,annotations,family,known,[.3,.18,.19],POLICY)
    np.testing.assert_allclose(result['parameters_board_m_rad'],p,atol=1e-7)
    T=pose(p,family);assert np.linalg.det(T[:3,:3])==pytest.approx(1.)
    assert result['image_consistency_passed'] and not result['absolute_accuracy_validated']
    # A held-out view can fail without pulling the estimated shape towards it.
    o=annotations['observations']['view2'];o['pixels']=(np.array(o['pixels'])+[30,10]).tolist()
    second=fit(cameras,annotations,family,known,[.3,.18,.19],POLICY)
    np.testing.assert_allclose(second['parameters_board_m_rad'],result['parameters_board_m_rad'],atol=1e-10)
    assert not second['image_consistency_passed'] and not second['validation_used_in_fit']


def test_degenerate_baseline_and_diagnostic_only_view_are_rejected():
    p,k,c,a=fixture();c['view1']['T_camera_board']=c['view0']['T_camera_board']
    with pytest.raises(ValueError,match='baseline'):fit(c,a,'plate_l',k,[.3,.18,.19],POLICY)
    p,k,c,a=fixture();c['view1']['metric_eligible']=False
    with pytest.raises(ValueError,match='excluded'):fit(c,a,'plate_l',k,[.3,.18,.19],POLICY)


@pytest.mark.parametrize('family',['plate_l','box_shell'])
def test_support_edge_initialization_needs_no_previous_object_pose(family):
    p,k,c,a=fixture(family);a.pop('initial_parameters_board_m_rad')
    result=fit(c,a,family,k,[.30,.18,.19],POLICY)
    np.testing.assert_allclose(result['parameters_board_m_rad'],p,atol=1e-6)


def test_no_implicit_unit_change_or_duplicate_view_validation():
    p,k,c,a=fixture();k['plate_thickness_m']=10
    with pytest.raises(ValueError,match='metres'):fit(c,a,'plate_l',k,[.3,.18,.19],POLICY)
    p,k,c,a=fixture();c['view2']['image_sha256']=c['view0']['image_sha256']
    with pytest.raises(ValueError,match='Duplicate'):fit(c,a,'plate_l',k,[.3,.18,.19],POLICY)
    with pytest.raises(ValueError,match='Thickness'):solid_parts([0,0,0,.01,.02,.01],'box_shell',{'wall_thickness_m':.01})


def job(tmp_path,family='multiview_mesh'):
    root=tmp_path/'setup/digitization/job';create(root,tmp_path,'student_robot',family,[.33,.3,.33],views_per_wrist=3);return root


def test_complex_object_routes_to_explicit_input_without_fake_box(tmp_path):
    root=job(tmp_path);result=fit_job(root,None)
    assert result['status']=='NEEDS_INPUT' and 'no box substitution' in result['next_action']
    assert not (root/'fit/model.json').exists()
    assert result['quality']['manipulation']=='NOT_APPROVED'


def test_one_call_offline_run_does_not_capture_when_input_is_missing(tmp_path,monkeypatch):
    root=job(tmp_path)
    def forbidden(*args,**kwargs):raise AssertionError('Offline run must not acquire data')
    monkeypatch.setattr('uwa_cell_control.digitization_job.capture',forbidden)
    result=process_job(root)
    assert result['status']=='NEEDS_INPUT' and result['capture_sets']==0
    assert not (root/'captures').exists()


def test_one_call_stops_before_export_when_geometry_fails(tmp_path,monkeypatch):
    root=job(tmp_path,'plate_l');j,s=read(root);s['captures']=[{'test_input':True}];save(root/'state.json',s)
    annotation=root/'annotations.json';save(annotation,{})
    monkeypatch.setattr('uwa_cell_control.digitization_job.prepare_job',lambda root:None)
    def failed_fit(root,annotations):save(root/'fit/model.json',{'image_consistency_passed':False})
    monkeypatch.setattr('uwa_cell_control.digitization_job.fit_job',failed_fit)
    def forbidden(*args,**kwargs):raise AssertionError('Failed geometry cannot silently enter export')
    monkeypatch.setattr('uwa_cell_control.digitization_job.export_job',forbidden)
    process_job(root,annotation)
    assert not (root/'candidates').exists()


def test_exact_stage_replay_and_changed_artifact_invalidate_downstream(tmp_path,monkeypatch):
    root=job(tmp_path);calls=[];out=root/'prepared.json'
    def operation(j,s):
        calls.append(1);save(out,dict(value=len(calls)));return dict(next_action='review'),[out]
    monkeypatch.chdir(tmp_path)
    run_stage(Path('setup/digitization/job'),'prepare',{'images':'a'},operation)
    run_stage(root,'prepare',{'images':'a'},operation)
    assert len(calls)==1 and summary(root)['stages']['prepare']['cached']
    j,s=read(root);s['stages']['export']={'status':'DONE'};s['quality']['geometry']='IMAGE_CONSISTENT';save(root/'state.json',s)
    out.write_text('tampered')
    run_stage(root,'prepare',{'images':'a'},operation)
    assert len(calls)==2 and 'export' not in read(root)[1]['stages']
    assert summary(root)['quality']['geometry']=='NOT_TESTED'


def test_failure_and_interrupt_are_persisted_without_retry(tmp_path):
    root=job(tmp_path)
    def error(j,s):raise RuntimeError('invalid camera model')
    with pytest.raises(RuntimeError):run_stage(root,'prepare',{},error)
    assert summary(root)['status']=='FAILED'
    def cancel(j,s):raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_stage(root,'prepare',{},cancel)
    assert summary(root)['status']=='CANCELLED'


def test_status_distinguishes_live_job_lock_from_lost_runner(tmp_path):
    root=job(tmp_path);j,s=read(root);s['status']='RUNNING';save(root/'state.json',s)
    with lock(root):assert summary(root)['status']=='RUNNING'
    assert summary(root)['status']=='CANCELLED'


def test_failed_restore_keeps_partial_data_uncommitted_and_requires_recovery(tmp_path,monkeypatch):
    root=job(tmp_path);calls=[];session=root/'fake_camera_session';session.mkdir()
    class Rig:
        def __init__(self,*args,**kwargs):self.session=session;self.instance_lock=SimpleNamespace(close=lambda:calls.append('close'))
        def lock_focus(self):calls.append('focus')
        def capture_all(self,native):calls.append('capture');return {'directory':str(session/'partial_set')}
        def restore_focus(self):calls.append('restore');raise RuntimeError('Camera unavailable during restore')
    monkeypatch.setattr('uwa_cell_control.board_capture.CaptureRig',Rig)
    with pytest.raises(RuntimeError,match='restore'):capture(root,'rtde')
    assert calls==['focus','capture','restore','close']
    assert summary(root)['capture_sets']==0 and summary(root)['status']=='FAILED'
    assert not json.loads((root/'last_capture_transaction.json').read_text())['restoration_confirmed']
    with pytest.raises(ValueError,match='recover'):capture(root,'rtde')
    assert calls==['focus','capture','restore','close']


def test_job_specification_is_bound_and_existing_job_never_overwritten(tmp_path):
    root=job(tmp_path)
    with pytest.raises(FileExistsError):create(root,tmp_path,'another','box_shell',[.1,.2,.3])
    j,s=read(root);j['spec']['user_rough_dimensions_m']=[330,300,330];save(root/'job.json',j)
    with pytest.raises(ValueError,match='specification'):read(root)


def test_resolution_focus_physical_identity_cannot_be_substituted():
    opt=dict(K=[[1000,0,1296],[0,1000,972],[0,0,1]],D=[0]*5,image_size=[2592,1944],focus=435,identity='camera-A')
    record=dict(settings_before=dict(focus=435,focusAuto=False),camera_identity=dict(uniqueCamId='camera-A'))
    check_optics(record,opt,[2592,1944],'right_front')
    with pytest.raises(ValueError,match='native'):check_optics(record,opt,[640,480],'right_front')
    record['camera_identity']['uniqueCamId']='camera-B'
    with pytest.raises(ValueError,match='Physical'):check_optics(record,opt,[2592,1944],'right_front')
    record['camera_identity']['uniqueCamId']='camera-A';record['settings_before']['focusAuto']=True
    with pytest.raises(ValueError,match='focus'):check_optics(record,opt,[2592,1944],'right_front')


def fake_capture(folder):
    cameras={}
    for name in ('left_front','left_rear','right_front','right_rear','oak4'):
        p=folder/name/'image.jpg';p.parent.mkdir(parents=True);p.write_bytes(name.encode())
        save(p.parent/'record.json',dict(sha256=sha(p),observation={}))
        cameras[name]=dict(success=True,image='image.jpg')
    save(folder/'manifest.json',dict(all_captured=True,stationary_set_confirmed=True,cameras=cameras))
    return folder/'manifest.json'


def test_import_rejects_unconfirmed_set_and_modified_raw_image(tmp_path,monkeypatch):
    root=job(tmp_path);manifest=fake_capture(tmp_path/'capture')
    monkeypatch.setattr('uwa_cell_control.digitization_job.cv2.imread',lambda p:SimpleNamespace(shape=(6000,8000,3) if 'oak4' in p else (1944,2592,3)))
    d=json.loads(manifest.read_text());d['stationary_set_confirmed']=False;save(manifest,d)
    with pytest.raises(ValueError,match='unconfirmed'):ingest(root,manifest)
    assert summary(root)['capture_sets']==0
    d['stationary_set_confirmed']=True;save(manifest,d);ingest(root,manifest)
    assert summary(root)['capture_sets']==1
    (manifest.parent/'right_front/image.jpg').write_bytes(b'different photo')
    with pytest.raises(ValueError,match='Changed'):ingest(root,manifest)
    assert summary(root)['capture_sets']==1

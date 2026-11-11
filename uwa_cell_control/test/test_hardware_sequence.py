import json
import time
import pytest

from uwa_cell_gazebo.configuration import load_layout,joint_names,ROBOT_IDS
from uwa_cell_control.parking import make_model
from uwa_cell_control.hardware_sequence import (acquisition_plan,validate_batch,remaining_observations,
    validate_resume_records,assemble_plan,validate_session_model)
import uwa_cell_control.hardware_sequence as module
from uwa_cell_control.park_arm import JointObserver


def test_batch_preserves_roles_checked_samples_and_preview_cannot_execute_as_one_trajectory(tmp_path,monkeypatch):
    layout=load_layout();profiles={r:{'ur_type':a['type'],'kinematics_file':None} for r,a in layout['robots'].items()}
    model,layout=make_model(layout,profiles,tmp_path)
    start={j:q for r,a in layout['robots'].items() for j,q in zip(joint_names(r),a['initial_positions'])}
    q0=[start[j] for j in joint_names('right_rear')]
    poses=[]
    for i in range(30):
        target=list(q0);target[0]+=(i+1)*.001
        poses.append({'joints':target,'role':'validation' if i%5==4 else 'fit'})
    monkeypatch.setattr(module,'generate_plan',lambda *args,**kwargs:{'right_rear':{'poses':poses}})
    plan=acquisition_plan(model,layout,profiles,'right_rear',start,
        {r:'live_joint_states' for r in ROBOT_IDS},[],30,tmp_path,'/tmp/test-layout.yaml')
    validate_batch(plan,profiles,layout)
    assert len(plan['segments'])==30 and not plan['automatic_return']
    assert sum(s['role']=='validation' for s in plan['segments'])==6
    assert not json.loads((tmp_path/'plan.json').read_text())['executable']
    assert plan['planning_only_camera_model']['source'].startswith('nominal')
    # A resumed sequence reconnects to the outstanding targets from a measured
    # new start, retaining the original sample IDs and validation assignments.
    current=dict(start);current[joint_names('right_rear')[0]]+=.015
    resumed=assemble_plan(model,layout,profiles,'right_rear',current,
        {r:'live_joint_states' for r in ROBOT_IDS},[],
        [dict(poses[19],sample_id='sample_020'),dict(poses[20],sample_id='sample_021')],
        tmp_path/'resume','/tmp/test-layout.yaml',plan['planning_only_camera_model'],
        resume={'parent_fingerprint':plan['fingerprint']})
    assert resumed['new_observations']==2 and resumed['segments'][0]['role']=='validation'
    assert resumed['segments'][0]['points'][0]['positions'][0]==current[joint_names('right_rear')[0]]
    assert resumed['segments'][0]['sample_id']=='sample_020'
    validate_batch(resumed,profiles,layout)
    plan['segments'][0]['target'][0]+=.2
    with pytest.raises(ValueError,match='plan changed'):validate_batch(plan,profiles,layout)


def test_autonomous_camera_sequence_needs_actual_native_control_link_and_stops_on_loss():
    observer=JointObserver.__new__(JointObserver)
    observer.mode='hardware';observer.program_running={};observer.profiles={'right_rear':{}}
    observer.received={'right_rear':{'positions':[0.]*6,'received_monotonic':time.monotonic()}}
    plan={'arm':'right_rear','state_sources':{'right_rear':'live_joint_states'}}
    with pytest.raises(RuntimeError,match='External Control'):observer.guard(plan,require_program_link=True)
    observer.program_running['right_rear']=True;observer.guard(plan,require_program_link=True)
    observer.program_running['right_rear']=False
    with pytest.raises(RuntimeError,match='External Control'):observer.guard(plan,require_program_link=True)


def test_native_protective_stop_cancels_even_when_program_running_stays_true():
    observer=JointObserver.__new__(JointObserver)
    observer.mode='hardware';observer.program_running={'right_rear':True};observer.profiles={'right_rear':{}}
    observer.received={'right_rear':{'positions':[0.]*6,'received_monotonic':time.monotonic()}}
    observer.safety_modes={'right_rear':3}
    plan={'arm':'right_rear','state_sources':{'right_rear':'live_joint_states'}}
    with pytest.raises(RuntimeError,match='native UR safety stop'):observer.guard(plan,require_program_link=True)
    for allowed in (1,2):
        observer.safety_modes['right_rear']=allowed;observer.guard(plan,require_program_link=True)


def test_resume_preserves_roles_and_records_and_detects_mutation_or_holes(tmp_path):
    records=tmp_path/'records';records.mkdir()
    segments=[{'sample_id':f'sample_{i:03d}','role':'validation' if i==2 else 'fit',
               'target':[i*.01]*6} for i in range(1,4)]
    plan={'arm':'right_rear','fingerprint':'parent','segments':segments}
    def save(index,**changes):
        s=segments[index-1]
        record=dict(s,robot_id='right_rear',accepted=True,positions=s['target'],image=s['sample_id']+'.jpg')
        record.update(changes)
        (records/(s['sample_id']+'.json')).write_text(json.dumps(record))
        (records/record['image']).write_bytes(b'raw jpeg fixture')
    save(1)
    poses,resume=remaining_observations(plan,tmp_path)
    assert [p['sample_id'] for p in poses]==['sample_002','sample_003']
    assert poses[0]['role']=='validation' and resume['completed_samples']==['sample_001']
    validate_resume_records({'resume':resume},tmp_path)
    (records/'sample_001.jpg').write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):validate_resume_records({'resume':resume},tmp_path)
    save(3)
    with pytest.raises(ValueError,match='Non-contiguous'):remaining_observations(plan,tmp_path)


@pytest.mark.parametrize('changes',[{'accepted':False},{'role':'validation'},{'positions':[1.]*6}])
def test_resume_rejects_failed_or_mismatching_observations(tmp_path,changes):
    records=tmp_path/'records';records.mkdir()
    record=dict(sample_id='sample_001',role='fit',accepted=True,robot_id='right_rear',positions=[0.]*6)
    record.update(changes)
    (records/'sample_001.json').write_text(json.dumps(record))
    plan={'arm':'right_rear','fingerprint':'parent',
          'segments':[{'sample_id':'sample_001','role':'fit','target':[0.]*6}]}
    with pytest.raises(ValueError):remaining_observations(plan,tmp_path)


def test_session_rejects_changed_factory_kinematics_even_at_same_path(tmp_path):
    import hashlib
    from uwa_cell_control.parking import digest
    path=tmp_path/'factory.yaml';path.write_bytes(b'original')
    metadata={'mode':'hardware','robot_id':'right_rear','camera_ip':'192.168.8.170',
        'layout_fingerprint':digest({}),'kinematics_sha256':hashlib.sha256(b'original').hexdigest()}
    profile={'ip':'192.168.8.170','kinematics_file':str(path)}
    validate_session_model(metadata,'right_rear',profile,{})
    path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='kinematics'):validate_session_model(metadata,'right_rear',profile,{})


def test_larger_hardware_series_keeps_twelve_held_out_and_fifty_fit_including_initial(tmp_path,monkeypatch):
    layout=load_layout();profiles={r:{'ur_type':a['type'],'kinematics_file':None} for r,a in layout['robots'].items()}
    model,layout=make_model(layout,profiles,tmp_path)
    start={j:q for r,a in layout['robots'].items() for j,q in zip(joint_names(r),a['initial_positions'])}
    q0=[start[j] for j in joint_names('right_front')]
    def proposed(*args,**kwargs):
        assert kwargs['view_design']=='wide'
        return {'right_front':{'poses':[{'joints':[q0[0]+(i+1)*.001,*q0[1:]],
            'role':'validation' if i%5==4 else 'fit'} for i in range(61)]}}
    monkeypatch.setattr(module,'generate_plan',proposed)
    plan=acquisition_plan(model,layout,profiles,'right_front',start,
        {r:'live_joint_states' for r in ROBOT_IDS},[],61,tmp_path,'/tmp/test-layout.yaml',view_design='wide')
    assert len(plan['segments'])==61 and plan['new_observations']==61
    assert sum(s['role']=='validation' for s in plan['segments'])==12
    assert 1+sum(s['role']=='fit' for s in plan['segments'])==50
    assert plan['planning_only_camera_model']['view_design']=='wide'
    validate_batch(plan,profiles,layout)
    for count in (29,80):
        with pytest.raises(ValueError,match='30–79'):
            acquisition_plan(model,layout,profiles,'right_front',start,{},[],count,tmp_path,'/tmp/test-layout.yaml')


def test_larger_hardware_result_keeps_quality_and_simulation_limits():
    from copy import deepcopy
    from uwa_cell_calibration.storage import validate_result
    identity=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    result={'schema_version':1,'mode':'hardware','passed':True,'robots':{'right_front':{
        'passed':True,'fit_count':50,'validation_count':12,'T_tool0_camera':identity,
        'T_base_board':identity,'validation':{'median_reprojection_rms_px':.4,
            'board_translation_rms_m':.002,'board_rotation_rms_deg':.2}}}}
    validate_result(result)
    bad=deepcopy(result);bad['robots']['right_front']['validation']['board_translation_rms_m']=.006
    with pytest.raises(ValueError,match='limits exceeded'):validate_result(bad)
    bad=deepcopy(result);bad.pop('mode')
    with pytest.raises(ValueError,match='30-50'):validate_result(bad)
    bad=deepcopy(result);bad['robots']['right_front']['fit_count']=69
    with pytest.raises(ValueError,match='30-80'):validate_result(bad)

import json
import time
import pytest

from uwa_cell_gazebo.configuration import load_layout,joint_names,ROBOT_IDS
from uwa_cell_control.parking import make_model
from uwa_cell_control.hardware_sequence import acquisition_plan,validate_batch
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

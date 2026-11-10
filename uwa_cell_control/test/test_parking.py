from copy import deepcopy
import json

import numpy as np
import pytest

from uwa_cell_gazebo.configuration import load_layout,joint_names,ROBOT_IDS
from match_ur_hardware.profiles import load_profiles
from match_ur_hardware.trajectory import trajectory_goal
from uwa_cell_control.parking import (complete_state,digest,make_model,manual_states,
                                     plan_parking,save_plan,validate_artifact)
from pathlib import Path


def profiles():
    return load_profiles(Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml')


def test_missing_arms_are_explicit_preview_states_and_manual_units_required(tmp_path):
    layout=load_layout()
    start,sources,missing=complete_state(layout,{})
    assert missing==list(ROBOT_IDS) and len(start)==24
    assert all(s=='UNOBSERVED_LAYOUT_PREVIEW' for s in sources.values())
    path=tmp_path/'manual.json'
    path.write_text(json.dumps({'left_front':{'positions':[90]*6,'unit':'deg'}}))
    read=manual_states(path)
    np.testing.assert_allclose(read['left_front']['positions'],[np.pi/2]*6)
    assert complete_state(layout,read)[2]==['left_rear','right_front','right_rear']
    path.write_text(json.dumps({'left_front':{'positions':[90]*6}}))
    with pytest.raises(ValueError,match='unit'):manual_states(path)
    with pytest.raises(ValueError,match='finite'):complete_state(layout,{'right_front':{'positions':[float('nan')]*6,'source':'live_joint_states'}})


@pytest.fixture(scope='module')
def planned(tmp_path_factory):
    directory=tmp_path_factory.mktemp('parking')
    layout=load_layout();inventory=profiles()
    model,layout=make_model(layout,inventory,directory)
    read={r:{'positions':layout['robots'][r]['initial_positions'],'source':'mock_joint_states'} for r in ROBOT_IDS}
    start,sources,missing=complete_state(layout,read)
    path=plan_parking(model,layout,'right_front',start)
    artifact=save_plan(directory,path,model,layout,inventory,sources,missing,'mock')
    return model,artifact,inventory


def test_real_moveit_scene_sweeps_parking_path_and_only_target_arm_changes(planned):
    model,plan,_=planned
    assert plan['duration']>1 and plan['collision_samples']>=20
    assert plan['executable'] and not plan['unobserved_arms']
    for point in plan['points']:
        assert max(abs(np.array(point['velocities'])))<=.050001
        assert max(abs(np.array(point['accelerations'])))<=.100001
        state=dict(plan['start'],**dict(zip(plan['joint_names'],point['positions'])))
        assert model.check(state)[0]
        for r in ('left_front','left_rear','right_rear'):
            assert all(state[j]==plan['start'][j] for j in joint_names(r))
    with pytest.raises(ValueError,match='No checked'):plan_parking(model,plan['layout'],'right_front',plan['start'],target=[20]*6)


def test_trajectory_model_and_missing_state_tampering_never_become_executable(planned):
    _,original,inventory=planned
    validate_artifact(original,inventory)
    changed=deepcopy(original);changed['target'][0]+=.1
    with pytest.raises(ValueError,match='fingerprint'):validate_artifact(changed,inventory)
    changed=deepcopy(original);changed['unobserved_arms']=['left_front'];changed['executable']=False
    changed.pop('fingerprint');changed['fingerprint']=digest(changed)
    with pytest.raises(ValueError,match='missing'):validate_artifact(changed,inventory)
    changed=deepcopy(original);changed['mode']='hardware';changed['ros_domain']=66
    changed.pop('fingerprint');changed['fingerprint']=digest(changed)
    with pytest.raises(ValueError,match='Mock states'):validate_artifact(changed,inventory)
    changed_inventory=deepcopy(inventory);changed_inventory['right_front']['ip']='192.0.2.1'
    with pytest.raises(ValueError,match='Inventory changed'):validate_artifact(original,changed_inventory)


def test_native_trajectory_message_preserves_all_sample_fields_and_rejects_bad_time(planned):
    _,plan,_=planned
    goal=trajectory_goal(plan['joint_names'],plan['points'])
    assert list(goal.trajectory.joint_names)==plan['joint_names']
    assert len(goal.trajectory.points)==len(plan['points'])
    last=goal.trajectory.points[-1]
    np.testing.assert_allclose(last.positions,plan['target'])
    assert abs(last.time_from_start.sec+last.time_from_start.nanosec/1e9-plan['duration'])<1e-8
    bad=deepcopy(plan['points']);bad[1]['time']=0
    with pytest.raises(ValueError,match='increasing'):trajectory_goal(plan['joint_names'],bad)

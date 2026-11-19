"""Static closure retains existing arm state requirements and no-motion policy."""
import copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from carton_gripper_phase import held_error,closing_contact
from uwa_cell_motion.common import ROBOT_IDS,joint_names


def packets():
    positions={j:0. for a in ROBOT_IDS for j in joint_names(a)}
    common=dict(hardware_signature='expected',armed=True,evaluated_monotonic_s=1.)
    values=dict(guard=(dict(common,faults=[],model_match=True,stationary_arms=list(ROBOT_IDS)),1.),
      supervisor=(dict(common,witness_available=True,held_arms=list(ROBOT_IDS),ports={a:{k:True for k in ('held','manager_fresh','hardware_mode_verified','hold_config_verified')}for a in ROBOT_IDS}),1.),
      witness=(dict(common,tripped=False),1.),state=(dict(common,records={a:dict(received=1.,source_stamp=1.,q=[0.]*6,v=[0.]*6,status=dict(robot_mode=7,runtime_state=2,safety_mode=1))for a in ROBOT_IDS}),1.))
    limits=dict(state_timeout_s=.2,heartbeat_timeout_s=.25,standstill_velocity_rad_s=.001)
    return values,positions,limits


def test_static_phase_refuses_missing_holds_stale_state_or_moved_pose():
    values,positions,limits=packets();assert held_error(values,1.1,'expected',limits,positions)is None
    assert 'stale' in held_error(values,1.3,'expected',limits,positions)
    bad=copy.deepcopy(values);bad['supervisor'][0]['ports']['left_front']['held']=False
    assert held_error(bad,1.1,'expected',limits,positions)
    bad=copy.deepcopy(values);bad['state'][0]['records']['right_front']['q'][0]=.001
    assert 'pose changed' in held_error(bad,1.1,'expected',limits,positions)
    bad=copy.deepcopy(values);bad['witness'][0]['tripped']=True
    assert held_error(bad,1.1,'expected',limits,positions)


def test_object_contact_is_not_an_empty_endpoint_or_wrong_force_setting():
    status=dict(observed=True,busy=False,registers=dict(ACT=1,STA=3,OBJ=2,FLT=0,PRE=255,POS=210,FOR=0,SPE=16))
    assert closing_contact(status)
    for key,value in [('OBJ',3),('POS',255),('FLT',1),('FOR',1),('PRE',0),('ACT',0)]:
        changed=copy.deepcopy(status);changed['registers'][key]=value;assert not closing_contact(changed)


def test_stationary_held_left_program_need_not_run_for_static_right_grippers():
    values,positions,limits=packets()
    values["state"][0]["records"]["left_front"]["status"]["runtime_state"]=1
    assert held_error(values,1.1,"expected",limits,positions)is None
    values["state"][0]["records"]["right_front"]["status"]["runtime_state"]=1
    assert held_error(values,1.1,"expected",limits,positions)

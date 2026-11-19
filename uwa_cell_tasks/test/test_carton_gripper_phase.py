"""Static closure retains existing arm state requirements and no-motion policy."""
import copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from carton_gripper_phase import held_error,closing_contact,ready_for_open_preparation
from uwa_cell_tasks.hardware_carton_approach import unloaded_open_status
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


def test_activated_boot_state_only_allows_high_open_preparation():
    status=dict(observed=True,busy=False,registers=dict(ACT=1,STA=3,OBJ=0,FLT=0,PRE=0,POS=3,COU=0))
    assert ready_for_open_preparation(status)
    assert not unloaded_open_status(status)
    assert not closing_contact(status)
    for key,value in [('POS',9),('COU',1),('FLT',9),('PRE',255),('STA',1)]:
        changed=copy.deepcopy(status);changed['registers'][key]=value
        assert not ready_for_open_preparation(changed)


def test_stationary_held_left_program_need_not_run_for_static_right_grippers():
    values,positions,limits=packets()
    values["state"][0]["records"]["left_front"]["status"]["runtime_state"]=1
    assert held_error(values,1.1,"expected",limits,positions)is None
    values["state"][0]["records"]["right_front"]["status"]["runtime_state"]=1
    assert held_error(values,1.1,"expected",limits,positions)


def test_explicit_supported_release_allows_stopped_program_but_keeps_hold_and_safety():
    values,positions,limits=packets()
    values['state'][0]['records']['right_rear']['status']['runtime_state']=1
    assert held_error(values,1.1,'expected',limits,positions)
    assert held_error(values,1.1,'expected',limits,positions,require_running=False)is None
    values['supervisor'][0]['ports']['right_rear']['held']=False
    assert held_error(values,1.1,'expected',limits,positions,require_running=False)
    values['supervisor'][0]['ports']['right_rear']['held']=True
    values['state'][0]['records']['right_rear']['status']['safety_mode']=3
    assert held_error(values,1.1,'expected',limits,positions,require_running=False)


def test_contact_members_remain_recorded_when_final_native_readiness_fails(tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    import carton_gripper_phase as phase
    commands=[]
    class Gripper:
        def __init__(self,arm):self.arm=arm;self.closed=False
        def status(self):
            return dict(observed=True,busy=False,registers=dict(ACT=1,STA=3,OBJ=2 if self.closed else 3,
                FLT=0,PRE=255 if self.closed else 0,POS=204 if self.closed else 3,FOR=0,SPE=16))
        def close_gripper(self,**kwargs):self.closed=True;commands.append(self.arm);return dict(success=True)
        def close(self):pass
    class Monitor:
        def __init__(self,*args):self.calls=0;self.values={};self.node=SimpleNamespace(destroy_node=lambda:None)
        def connect(self):
            self.calls+=1
            if self.calls==3:raise RuntimeError('right_rear: native program/safety state not ready')
        def spin(self):pass
        def error(self):return None
    state=tmp_path/'entry.json';out=tmp_path/'out'
    state.write_text(json.dumps(dict(success=True,phase='BOTH_OPEN_AT_WALL_HELD_NO_CLOSE',
        hardware_signature='expected',supervision_limits={},segments=[dict(final_positions={})])))
    monkeypatch.setattr(phase,'GripperClient',Gripper);monkeypatch.setattr(phase,'HeldMonitor',Monitor)
    monkeypatch.setattr(phase,'require_domain',lambda mode:None)
    monkeypatch.setattr(phase.rclpy,'init',lambda:None);monkeypatch.setattr(phase.rclpy,'shutdown',lambda:None)
    monkeypatch.setattr(sys,'argv',['phase','close','--state',str(state),'--output',str(out),'--execute','--visual-confirmed'])
    assert phase.main()==1
    result=json.loads((out/'result.json').read_text())
    assert result['confirmed_contact_members']==['right_front','right_rear']
    assert result['group']['independent_arm_motion_allowed'] is False
    assert result['group']['allowed_next_action']=='HOLD'
    assert result['arm_commands']==[] and len(commands)==2

"""Frozen parking/acquisition use the shared backend; no live ROS context."""
from contextlib import contextmanager
import json
from types import SimpleNamespace as Box

import pytest

from uwa_cell_gazebo.configuration import ROBOT_IDS, joint_names
from uwa_cell_control import minimal_calibration, park_arm, hardware_sequence, handeye_hardware


def full_state(value=0.):
    return {j:value for arm in ROBOT_IDS for j in joint_names(arm)}


def points(start=0., end=.03):
    return [dict(time=0.,positions=[start]*6,velocities=[.09]*6,accelerations=[.1]*6),
            dict(time=1.7,positions=[end]*6,velocities=[0.]*6,accelerations=[0.]*6)]


def test_frozen_points_use_shared_client_without_retiming_or_guards():
    calls=[]
    client=Box(positions=full_state(), health=lambda:None,
               follow_group=lambda trajectories,**kw:calls.append((trajectories,kw)))
    motion=minimal_calibration.CheckedMotion(client)
    assert len(motion.snapshot())==24
    frozen=points()
    result=motion.follow('right_rear',frozen)
    assert calls[0][0]['right_rear']['points'] is frozen
    assert calls[0][0]['right_rear']['joint_names']==joint_names('right_rear')
    assert calls[0][1]==dict(duration_s=1.7)
    assert frozen[0]['velocities']==[.09]*6
    assert result['success'] and result['protection_backend']=='minimal'
    client.positions.pop(joint_names('left_front')[0])
    with pytest.raises(ValueError,match='24-joint'):motion.snapshot()
    client.positions=full_state(float('nan'))
    with pytest.raises(ValueError,match='finite'):motion.snapshot()


@pytest.mark.parametrize('dispatch',[False,True])
def test_interrupted_read_only_planning_does_not_pause_unrelated_motion(monkeypatch,dispatch):
    import uwa_cell_motion.hardware_model as hardware_model
    import uwa_cell_motion.minimal_execution as execution
    calls=[]
    def interrupted(*args,**kwargs):raise KeyboardInterrupt
    fake=Box(positions=full_state(),health=lambda:None,connect=lambda:None,
        follow_group=interrupted,stop=lambda:calls.append('pause'),destroy_node=lambda:calls.append('close'))
    monkeypatch.setattr(hardware_model,'HardwareProblem',lambda *args:None)
    monkeypatch.setattr(execution,'MinimalHardwareClient',lambda *args:fake)
    with pytest.raises(KeyboardInterrupt):
        with minimal_calibration.checked_motion('/tmp/inventory','/tmp/layout','mock',[]) as motion:
            if dispatch:motion.follow('right_rear',points())
            else:raise KeyboardInterrupt
    assert calls==(['pause','close'] if dispatch else ['close'])


def test_minimal_joint_observer_uses_only_shared_state_and_no_native_or_stationary_gate(monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    subscriptions=[]
    node=Box(create_subscription=lambda kind,name,callback,qos:subscriptions.append((name,callback)))
    profiles={arm:dict(namespace='/test/'+arm,joint_names=joint_names(arm)) for arm in ROBOT_IDS}
    observer=park_arm.JointObserver(node,profiles,ROBOT_IDS,'hardware')
    assert [name for name,_ in subscriptions]==['/uwa_cell/protection/state']
    observer.receive_protection(Box(data=json.dumps(dict(positions=full_state(.7)))))
    assert len(observer.received)==4
    observer.safety_modes={'right_rear':3}
    observer.program_running={'right_rear':False}
    for record in observer.received.values():record['received_monotonic']=-1000.
    observer.guard({},require_program_link=True)
    partial=full_state();partial.pop(joint_names('left_front')[0])
    observer.receive_protection(Box(data=json.dumps(dict(positions=partial))))
    assert 'left_front' not in observer.received


def test_minimal_planning_reads_complete_shared_input_instead_of_manual_fallback(monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    @contextmanager
    def shared(*args):
        assert args[-1]==[]
        yield Box(snapshot=lambda:full_state(.3))
    monkeypatch.setattr(minimal_calibration,'checked_motion',shared)
    monkeypatch.setattr(handeye_hardware,'JointObserver',lambda *args:Box(received={}))
    monkeypatch.setattr(handeye_hardware,'manual_states',lambda path:{
        'left_front':dict(positions=[9.]*6,source='manual_pendant')})
    profiles={arm:dict(ip='192.0.2.1') for arm in ROBOT_IDS}
    observer,readings=handeye_hardware.read_state(None,profiles,
        Box(manual_states=None,inventory='/tmp/inventory',layout='/tmp/layout',mode='hardware'))
    assert set(readings)==set(ROBOT_IDS)
    assert all(row['positions']==[.3]*6 for row in readings.values())
    assert observer.received==readings


def test_minimal_parking_keeps_frozen_path_and_uses_controller_completion(monkeypatch,capsys):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    calls=[];state=full_state()
    @contextmanager
    def shared(*args):
        calls.append(('context',args))
        yield Box(snapshot=lambda:dict(state), follow=lambda arm,path:
            calls.append(('follow',arm,path)) or dict(success=True,final_positions={}))
    monkeypatch.setattr(minimal_calibration,'checked_motion',shared)
    monkeypatch.setattr(park_arm,'node_for',lambda mode:Box(destroy_node=lambda:None))
    import rclpy
    monkeypatch.setattr(rclpy,'shutdown',lambda:None)
    monkeypatch.setattr(park_arm,'load_layout',lambda path:{})
    monkeypatch.setattr(park_arm,'make_model',lambda *args:(Box(check=lambda state:(True,[])),{}))
    frozen=points()
    artifact=dict(arm='right_rear',mode='mock',layout_file='/tmp/layout.yaml',layout={},start=state,
                  joint_names=joint_names('right_rear'),points=frozen,target=[.03]*6,fingerprint='bound')
    park_arm.execute_minimal(Box(inventory='/tmp/inventory.yaml',check_only=False),artifact,{})
    assert calls[-1]==('follow','right_rear',frozen)
    assert json.loads(capsys.readouterr().out)['success']


def test_minimal_acquisition_dispatches_each_frozen_segment_and_preserves_capture_order(
        tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    calls=[];state=full_state();rid='right_rear'
    @contextmanager
    def shared(*args):
        def follow(arm,path):
            calls.append(('motion',arm,path))
            state.update(zip(joint_names(arm),path[-1]['positions']))
        yield Box(snapshot=lambda:dict(state),follow=follow,client=Box(health=lambda:None))
    monkeypatch.setattr(minimal_calibration,'checked_motion',shared)
    monkeypatch.setattr(park_arm,'node_for',lambda mode:Box(destroy_node=lambda:None))
    monkeypatch.setattr(park_arm,'JointObserver',lambda *args:Box(sample=lambda dt:None,close=lambda:None))
    import rclpy
    monkeypatch.setattr(rclpy,'shutdown',lambda:None)
    import uwa_cell_gazebo.configuration as configuration
    import uwa_cell_control.parking as parking
    import uwa_cell_control.wrist_hd as wrist_hd
    monkeypatch.setattr(configuration,'load_layout',lambda path:{})
    monkeypatch.setattr(parking,'make_model',lambda *args:(Box(check=lambda state:(True,[])),{}))
    for name in ('validate_batch','validate_resume_records','validate_session_model'):
        monkeypatch.setattr(hardware_sequence,name,lambda *args:None)
    monkeypatch.setattr(wrist_hd,'make_camera',lambda *args,**kw:Box(settings=lambda:dict(focusAuto=False,focus=388)))
    def capture(*args,**kwargs):
        calls.append(('capture',args[-2],args[-1]))
        return dict(corners=24,role=args[-1])
    monkeypatch.setattr(handeye_hardware,'capture_observation',capture)
    records=tmp_path/'records';records.mkdir()
    (records/'sample_000.json').write_text(json.dumps(dict(camera_settings=dict(focus=388))))
    segments=[dict(sample_id='sample_001',role='validation',points=points()),
              dict(sample_id='sample_002',role='fit',points=points(.03,.05))]
    plan=dict(arm=rid,layout_file='/tmp/layout.yaml',start=full_state(),
        state_sources={arm:'live_joint_states' for arm in ROBOT_IDS},segments=segments,
        planning_only_camera_model={},fingerprint='bound')
    hardware_sequence.acquire_minimal(Box(inventory='/tmp/inventory.yaml',check_only=False),plan,
        {rid:dict(ip='192.0.2.1')},{},tmp_path)
    assert [item[0] for item in calls]==['motion','capture','motion','capture']
    assert calls[0][2] is segments[0]['points'] and calls[2][2] is segments[1]['points']
    assert calls[1][1:]==('sample_001','validation')
    assert calls[3][1:]==('sample_002','fit')
    assert 'ACQUISITION_COMPLETE' in capsys.readouterr().out

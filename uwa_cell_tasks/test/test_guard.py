"""Faults must latch the carrying members, never silently change their grip."""
from types import SimpleNamespace
import numpy as np
from std_msgs.msg import String
import json
from uwa_cell_tasks.core import ARMS
from uwa_cell_tasks.guard import TaskGuard


def guard_fixture():
    guard=TaskGuard.__new__(TaskGuard)
    guard.scene={'cfg':dict(relative_position_tolerance_m=.002,relative_angle_tolerance_rad=.0174533,joint_velocity_rad_s=.05)}
    guard.speed_violations={}
    guard.object={'T_world_object':np.eye(4).tolist()}
    guard.object_received=guard.contacts_received=guard.runner_received=10.
    guard.runner_completed=False;guard.supervisor={};guard.releasing=False
    guard.contacts=dict(pads={a:dict(left_pad=True,right_pad=True) for a in ARMS},supported=False,contacts=[])
    offsets={a:np.eye(4) for a in ARMS}
    for a,x in zip(ARMS,(-.2,.2)):offsets[a][0,3]=x
    guard.positions={a:t.copy() for a,t in offsets.items()}
    guard.eval_offsets={a:t.copy() for a,t in offsets.items()}
    guard.group=dict(object_to_tcp={a:t.tolist() for a,t in offsets.items()},contact_regions={})
    guard.core=SimpleNamespace(latched=set(),stationary=lambda a,t:True,records={a:dict(v=np.zeros(12)) for a in ARMS})
    guard.chains={a:SimpleNamespace(forward=lambda q,a=a:q[a]) for a in ARMS}
    return guard


def test_contact_loss_and_member_stop_affect_the_entire_loaded_group():
    guard=guard_fixture();assert not guard.faults(10.01)
    guard.contacts['pads'][ARMS[0]]['left_pad']=False
    faults=guard.faults(10.01)
    assert any(f['reason']=='GRASP CONTACT LOST' and f['arms']==list(ARMS) for f in faults)
    guard.contacts['pads'][ARMS[0]]['left_pad']=True
    guard.supervisor={'blocked_arms':[ARMS[1]]}
    assert any(f['reason']=='GRASP GROUP MEMBER STOPPED' and f['arms']==list(ARMS) for f in guard.faults(10.01))


def test_received_speed_peak_is_strict_and_survives_a_later_quiet_sample():
    from sensor_msgs.msg import JointState
    guard=guard_fixture();guard.names={}
    name=ARMS[0]+'_robotiq_85_left_finger_tip_joint'
    guard.joints(JointState(name=[name],position=[.7],velocity=[.05+1e-9]))
    assert not guard.speed_violations
    guard.joints(JointState(name=[name],position=[.7],velocity=[.05014682]))
    guard.joints(JointState(name=[name],position=[.7],velocity=[0.]))
    faults=guard.faults(10.01)
    assert any(f['reason']=='STRICT TASK SPEED LIMIT' and f['arms']==list(ARMS)
               and f['measured_peaks_rad_s'][name]==.05014682 for f in faults)
    response=SimpleNamespace(success=True,message='')
    guard.reset(None,response)
    assert not response.success and guard.speed_violations[name]==.05014682


def test_slip_and_telemetry_loss_cannot_be_hidden_by_new_membership():
    guard=guard_fixture();baseline=guard.eval_offsets[ARMS[0]].copy()
    guard.positions[ARMS[0]][2,3]+=.003
    assert any('SLIP' in f['reason'] and f['arms']==list(ARMS) for f in guard.faults(10.01))
    old_group=guard.group
    guard.membership(String(data=json.dumps(dict(object_to_tcp={a:t.tolist() for a,t in guard.positions.items()}))))
    assert guard.group is old_group and np.array_equal(guard.eval_offsets[ARMS[0]],baseline)
    assert any(f['reason']=='GRASP TELEMETRY STALE' for f in guard.faults(10.21))


def test_only_supported_stationary_release_dissolves_the_group():
    guard=guard_fixture();message=String(data=json.dumps(dict(released=True)))
    guard.membership(message);assert guard.group is not None
    guard.contacts['supported']=True;guard.core.stationary=lambda a,t:False
    guard.membership(message);assert guard.group is not None
    guard.core.stationary=lambda a,t:True
    guard.membership(message);assert guard.group is None and guard.eval_offsets is None


def test_stop_requests_both_members_even_if_one_transport_call_raises():
    import time
    from uwa_cell_tasks.runtime import Simulation
    from uwa_cell_description.configuration import joint_names
    requested=[]
    def request(arm):
        requested.append(arm)
        if arm==ARMS[0]:raise RuntimeError('transport unavailable')
        return object()
    sim=SimpleNamespace(handles=[],service_clients={
        'stop_'+a:SimpleNamespace(call_async=lambda req,a=a:request(a)) for a in ARMS},
        supervisor={'held_arms':list(ARMS)},supervisor_received=time.monotonic(),joint_received=time.monotonic(),
        v={j:0. for a in ARMS for j in joint_names(a)},
        call=lambda *args:SimpleNamespace(controller=[SimpleNamespace(name=a+'_collision_hold_controller',state='active') for a in ARMS]))
    def wait(predicate,timeout):assert predicate()
    sim.wait=wait
    result=Simulation.stop(sim)
    assert requested==list(ARMS) and result['confirmed'] and result['request_errors']
    sim.supervisor_received=0.
    def stale_wait(predicate,timeout):
        assert not predicate();raise TimeoutError('No fresh hold evidence')
    sim.wait=stale_wait
    assert not Simulation.stop(sim)['confirmed']


def test_transport_timeout_replays_only_the_read_only_controller_query():
    from uwa_cell_tasks.runtime import Simulation
    for key,expected in [('list',2),('switch',1)]:
        calls=[];removed=[];waits=[]
        future=SimpleNamespace(done=lambda:True,result=lambda:SimpleNamespace(controller=[]))
        client=SimpleNamespace(wait_for_service=lambda **kw:True,
            call_async=lambda req:(calls.append(req) or future),remove_pending_request=removed.append)
        def wait(*args,**kwargs):
            waits.append(1)
            if len(waits)==1:raise TimeoutError('Missing reply')
        sim=SimpleNamespace(service_clients={key:client},wait=wait)
        if key=='list':assert Simulation.call(sim,key,object()).controller==[]
        else:
            try:Simulation.call(sim,key,object())
            except TimeoutError:pass
            else:raise AssertionError('Mutation was retried')
        assert len(calls)==expected and len(removed)==1


def test_fault_probe_rejects_continued_slow_motion_despite_small_velocity():
    from importlib.machinery import SourceFileLoader
    from pathlib import Path
    module=SourceFileLoader('task_fault_probe_test',str(Path(__file__).resolve().parents[2]/'tools/test_manipulation_fault.py')).load_module()
    quiet=[(t,np.zeros(12),np.eye(4)) for t in np.linspace(0,.35,36)]
    assert module.stop_window(quiet)['ready']
    moving=[]
    for t in np.linspace(0,.35,36):
        obj=np.eye(4);obj[2,3]=.001*t
        moving.append((t,np.full(12,.002*t),obj))
    assert not module.stop_window(moving)['ready']
    assert not module.stop_window(quiet[:2])['ready']

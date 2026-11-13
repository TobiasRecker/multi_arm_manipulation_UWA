"""Common stop ordering, tracking corridor, native safety, and proof binding."""
from types import SimpleNamespace
import time
import numpy as np
import pytest
from uwa_cell_control.parallel_scan import ParallelMotion,path_deviation,collision_signature


def guard_runner():
    r=ParallelMotion.__new__(ParallelMotion)
    r.profiles={name:{} for name in ['a','b','c','d']}
    r.dashboard_watch=None;r.mock=False;r.tracking=.005;r.require_gui=True;r.stop_requested=False
    r.last_heartbeat=time.monotonic();r.last_clock=None
    r.node=SimpleNamespace(get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=1000000)))
    r.expected={rid:np.zeros(6) for rid in r.profiles};r.active={}
    r.observer=SimpleNamespace(received={rid:dict(positions=[0.]*6,received_monotonic=time.monotonic()) for rid in r.profiles},
        safety_modes={rid:1 for rid in r.profiles},robot_modes={rid:7 for rid in r.profiles},
        program_running={rid:True for rid in r.profiles})
    return r


def test_path_corridor_is_independent_of_timing_but_rejects_sideways_motion():
    a=np.zeros(6);b=np.array([1.,2,0,0,0,0])
    assert path_deviation(.4*b,a,b)<1e-12
    assert path_deviation(.9*b,a,b)<1e-12
    q=.4*b;q[3]=.006
    assert path_deviation(q,a,b)>.005
    assert path_deviation(np.ones(6)*.01,a,a)==.01


def test_guard_stops_on_native_stop_gui_loss_and_unexpected_neighbor_motion():
    r=guard_runner();r.guard()
    r.observer.safety_modes['b']=3
    with pytest.raises(RuntimeError,match='native safety'):r.guard()
    r=guard_runner();r.last_heartbeat-=1
    with pytest.raises(RuntimeError,match='heartbeat'):r.guard()
    r=guard_runner();r.observer.received['c']['positions'][2]=.01
    with pytest.raises(RuntimeError,match='unexpected motion'):r.guard()
    r=guard_runner();r.observer.robot_modes['d']=3
    with pytest.raises(RuntimeError,match='robot mode'):r.guard()


def test_abort_cancels_known_goals_before_waiting_for_a_late_ack():
    r=ParallelMotion.__new__(ParallelMotion);events=[]
    class Handle:
        accepted=True
        def __init__(self,name):self.name=name
        def cancel_goal_async(self):events.append('cancel '+self.name);return SimpleNamespace(name='cancel')
    r.stop_requested=False;r.claimed={'a','b'};r.owned={'a','b'};r.active={}
    r.handles={'a':Handle('a')};r.pending={'a':None,'b':SimpleNamespace(name='late b')}
    def wait(future,deadline,guard=False):
        events.append('wait '+future.name)
        return Handle('b') if future.name=='late b' else None
    r.wait=wait;r.deactivate=lambda:events.append('deactivate') or []
    r.spin=lambda timeout:None;r.observer=SimpleNamespace(settled=lambda:True)
    r.status=lambda phase,**data:events.append(phase)
    r.abort()
    assert events.index('cancel a')<events.index('deactivate')<events.index('wait late b')<events.index('cancel b')
    assert r.stop_requested and events[-1]=='STOPPED'


def test_collision_signature_ignores_visual_paths_but_not_mount_changes():
    a='<robot name="r"><link name="world"/><link name="a"><visual><geometry><mesh filename="/one"/></geometry></visual><collision><geometry><box size="1 1 1"/></geometry></collision></link><joint name="j" type="fixed"><parent link="world"/><child link="a"/><origin xyz="0 0 0"/></joint></robot>'
    assert collision_signature(a)==collision_signature(a.replace('/one','/two'))
    assert collision_signature(a)!=collision_signature(a.replace('xyz="0 0 0"','xyz=".1 0 0"'))


def test_cached_ros_state_cannot_replace_live_dashboard_confirmation():
    from uwa_cell_control.parallel_scan import DashboardWatch
    import threading
    d=DashboardWatch.__new__(DashboardWatch);d.profiles={'a':{}};d.lock=threading.Lock();d.records={}
    with pytest.raises(RuntimeError,match='cached ROS'):d.guard()
    d.records={'a':dict(received_monotonic=time.monotonic(),answers={
        'robotmode':'Robotmode: RUNNING','safetymode':'Safetymode: NORMAL','programState':'PLAYING ros.urp'})}
    d.guard()
    d.records['a']['received_monotonic']-=3
    with pytest.raises(RuntimeError,match='cached ROS'):d.guard()
    d.records={'a':dict(received_monotonic=time.monotonic(),error='network down')}
    with pytest.raises(RuntimeError,match='hardware link'):d.guard()


def test_replaced_or_missing_original_snapshot_invalidates_execution(tmp_path):
    import json,hashlib
    from uwa_cell_control.parallel_scan import load_checked
    from uwa_cell_control.parking import digest
    snapshot=tmp_path/'snapshot.json';snapshot.write_text(json.dumps({'mode':'hardware','arms':{}}))
    plan=tmp_path/'report.json';plan.write_text(json.dumps({'snapshot':str(snapshot),'snapshot_sha256':digest({'original':True})}))
    proof=tmp_path/'separation.json';proof.write_text(json.dumps({'source_plan_sha256':hashlib.sha256(plan.read_bytes()).hexdigest()}))
    (tmp_path/'cell.urdf').write_text('<robot name="test"/>')
    with pytest.raises(ValueError,match='snapshot changed'):load_checked(plan,proof)
    snapshot.unlink()
    with pytest.raises(ValueError,match='snapshot changed'):load_checked(plan,proof)


def test_abort_broadcasts_cancellation_even_without_any_goal_acknowledgement():
    r=ParallelMotion.__new__(ParallelMotion);events=[]
    r.stop_requested=False;r.claimed={'a','b'};r.owned={'a','b'};r.active={};r.handles={};r.pending={}
    class Client:
        def __init__(self,name):self.name=name
        def call_async(self,request):
            events.append('cancel server '+self.name)
            assert not any(request.goal_info.goal_id.uuid)
            return SimpleNamespace()
    r.cancel_clients={name:Client(name) for name in ['a','b']}
    r.deactivate=lambda:events.append('deactivate') or []
    r.wait=lambda *args,**kwargs:None;r.spin=lambda timeout:None
    r.observer=SimpleNamespace(settled=lambda:True);r.status=lambda *a,**k:None
    r.abort()
    assert events[:2]==['cancel server a','cancel server b'] and events[2]=='deactivate'

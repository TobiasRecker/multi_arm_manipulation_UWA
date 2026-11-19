"""Entry time law must preserve its smooth geometry and real command limits."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from run_carton_open_entry import timed_primitive,timed_sequence
from prepare_carton_open_entry import shell_boxes

@pytest.mark.parametrize('delta',[.001,.5])
def test_entry_limits_and_stop_boundaries(delta):
    segment=dict(kind='JOINT',knots=[0.,1.],positions=[[0.]*6,[delta]*6])
    t=timed_primitive(segment,[.0001]*6);pts=t['points']
    np.testing.assert_allclose(pts[0]['positions'],[.0001]*6,atol=1e-12)
    np.testing.assert_allclose(pts[-1]['positions'],[delta]*6,atol=1e-12)
    for p in [pts[0],pts[-1]]:
        np.testing.assert_allclose(p['velocities'],0,atol=1e-12)
        np.testing.assert_allclose(p['accelerations'],0,atol=1e-12)
    assert max(abs(x)for p in pts for x in p['velocities'])<=.100001
    assert max(abs(x)for p in pts for x in p['accelerations'])<=.200001
    assert all(b['time']>a['time']for a,b in zip(pts,pts[1:]))
    with pytest.raises(ValueError,match='start changed'):timed_primitive(segment,[.001]*6)

def test_wall_envelope_contains_both_original_end_walls_and_rims():
    scene=dict(shapes=[dict(axis=0,side=0,vertices=[[0,0,0],[.0025,.34,.13]]),dict(axis=0,side=1,vertices=[[.4015,0,0],[.404,.34,.13]])])
    boxes=shell_boxes(scene)
    for box,shape in zip(boxes,scene['shapes']):
        p=np.array(shape['vertices']);assert np.all(np.array(box['lo'])<=p.min(0));assert np.all(np.array(box['hi'])>=p.max(0))
        assert box['hi'][0]-box['lo'][0]==pytest.approx(.035)
        assert box['hi'][2]>=.135


def test_one_arm_sequence_preserves_primitive_timing_and_junction():
    a=dict(kind='JOINT',knots=[0.,1.],positions=[[0.]*6,[.01]*6])
    b=dict(kind='JOINT',knots=[0.,1.],positions=[[.01]*6,[.1]*6])
    first=timed_primitive(a,[.0001]*6);second=timed_primitive(b,[.01]*6)
    combined=timed_sequence([a,b],[.0001]*6)
    assert combined['duration_s']==pytest.approx(first['duration_s']+second['duration_s'])
    assert combined['points'][:len(first['points'])]==first['points']
    assert all(y['time']>x['time']for x,y in zip(combined['points'],combined['points'][1:]))
    assert combined['points'][-1]['positions']==second['points'][-1]['positions']
    with pytest.raises(ValueError,match='junction'):timed_sequence([a,a],[0.]*6)

def test_rpc_lifetime_cannot_interrupt_activation_telemetry():
    from types import SimpleNamespace
    from run_carton_pregrasp import ApproachClient
    calls=[];future=SimpleNamespace(done=lambda:True,result=lambda:'ok')
    endpoint=SimpleNamespace(service_is_ready=lambda:True,call_async=lambda request:future)
    def create(*args):calls.append(args);return endpoint
    def forbidden_teardown(*args):raise AssertionError('RMW teardown during activation punches a telemetry gap')
    fake=SimpleNamespace(rpc_clients={},service_timings=[],create_client=create,destroy_client=forbidden_teardown,
        spin_once=lambda **kw:None,wait=lambda predicate,timeout:predicate())
    assert ApproachClient.service(fake,object,'/manager/list',None)=='ok'
    assert ApproachClient.service(fake,object,'/manager/list',None)=='ok'
    assert len(calls)==1 and len(fake.service_timings)==2

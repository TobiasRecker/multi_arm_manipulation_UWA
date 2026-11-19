"""Serial arm handover retains the provisioned ROS graph until all holds."""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from run_carton_pregrasp import approach_resources,read_gripper_status,ROBOT_IDS


def test_complete_graph_precedes_first_arm_and_survives_handover():
    events=[]
    class Observer:
        def __init__(self,host):events.append(('observer',host))
        def close(self):events.append(('close_observer',))
    class Client:
        def __init__(self,problem,arm,observer):
            events.append(('client',arm));self.rpc_clients={}
        def create_client(self,kind,path):events.append(('rpc',path));return object()
        def destroy_node(self):events.append(('destroy',))
    arms=['right_front','right_rear'];problem=SimpleNamespace(profiles={a:dict(ip=a)for a in arms})
    with approach_resources(problem,arms,Client,Observer) as pool:
        assert list(pool)==arms
        assert sum(e[0]=='rpc'for e in events)==2*len(ROBOT_IDS)
        count=len(events)
        for arm in arms:
            assert len(pool[arm][1].rpc_clients)==len(ROBOT_IDS)
            assert len(events)==count
        assert not any(e[0].startswith(('close','destroy'))for e in events)
    assert sum(e[0]=='destroy'for e in events)==2
    assert sum(e[0]=='close_observer'for e in events)==2


def test_read_failure_does_not_become_open_status():
    client=SimpleNamespace(service=lambda *args:SimpleNamespace(success=False,message='not observed'))
    with pytest.raises(RuntimeError,match='not observed'):read_gripper_status(client,'right_rear')

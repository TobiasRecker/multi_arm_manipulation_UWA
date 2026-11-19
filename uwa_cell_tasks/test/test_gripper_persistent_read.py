"""Repeated gripper reads use the same graph endpoint and new device requests."""
from types import SimpleNamespace
import pytest
from uwa_cell_gripper_control.client import GripperClient


def test_persistent_read_is_fresh_and_does_not_allocate_again():
    requests=[]
    def request(value):requests.append(value);return len(requests)
    rpc=SimpleNamespace(wait_for_service=lambda **kw:True,call_async=request)
    client=GripperClient.__new__(GripperClient);client.path='/test';client.services={'read':rpc}
    client.wait=lambda future,timeout:SimpleNamespace(success=True,message='{"sample":'+str(future)+'}')
    def forbidden(*a,**kw):raise AssertionError('new graph endpoint during repeated read')
    client.node=SimpleNamespace(create_client=forbidden)
    assert client.status()=={'sample':1}
    assert client.status()=={'sample':2}
    client.wait=lambda *a:SimpleNamespace(success=False,message='not observed')
    with pytest.raises(RuntimeError,match='not observed'):client.status()

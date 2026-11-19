"""Armed known-controller stop paths never allocate new RMW clients."""
from types import SimpleNamespace
from uwa_cell_motion.hardware_ports import StopPort,HOLD,MOTION


def test_known_stop_clients_are_provisioned_before_first_armed_tick():
    requested=[]
    endpoint=lambda:SimpleNamespace(service_is_ready=lambda:True,call_async=lambda request:requested.append(request))
    node=SimpleNamespace(create_client=lambda *args,**kwargs:endpoint())
    port=StopPort(node,dict(namespace='/arm',joint_names=['joint'],id='right_front'),{},'mock')
    port.controllers=[SimpleNamespace(name=name,claimed_interfaces=['joint/position'])for name in (*MOTION,HOLD)]
    count=len(port.cancels)
    def forbidden(*args,**kwargs):raise AssertionError('RMW creation inside armed stop path')
    node.create_client=forbidden
    port.cancel();port.cancel()
    assert len(port.cancels)==count==len(MOTION)+2
    assert len(requested)==2*count

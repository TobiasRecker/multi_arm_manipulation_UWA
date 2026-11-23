"""Pure supervisor reset protocol; no ROS context or devices are created."""
import threading,time
from types import SimpleNamespace
from uwa_cell_motion.hardware_nodes import HardwareSupervisor
from uwa_cell_motion.interlock import Interlock
from uwa_cell_motion.common import ROBOT_IDS


def fake():
    now=time.monotonic();core=Interlock(.25);core.receive(dict(instance='guard',sequence=1,blocked_arms=[],reset_sequence=0,state='CLEAR'),now)
    server=SimpleNamespace(reset_lock=threading.Lock(),lock=threading.RLock(),core=core,cfg=dict(heartbeat_timeout_s=.25),armed=True,
        guard=SimpleNamespace(fresh=lambda *a:True),witness=SimpleNamespace(fresh=lambda *a:True,value=dict(tripped=False)),
        ports={r:SimpleNamespace(verified=True, hardware_verified=True, received=now, hardware_received=now,
            parameter_received=now, list_observed_from=now, hardware_observed_from=now,
            parameters_observed_from=now, hold_invalidated=now) for r in ROBOT_IDS},
        reset_guard=object(),reset_witness=object(),calls=[])
    def request(peer):
        server.calls.append(peer)
        if peer is server.reset_guard:core.receive(dict(instance='guard',sequence=2,blocked_arms=[],reset_sequence=1,reset_arms=list(ROBOT_IDS),state='CLEAR'),time.monotonic())
        return SimpleNamespace(success=True,message='geometry acknowledged')
    server.request=request;return server


def test_scoped_supervisor_reset_only_releases_the_requested_arm():
    server=fake();response=HardwareSupervisor.reset(server,None,SimpleNamespace(),arms={'right_front'})
    assert response.success and server.core.blocked==set(ROBOT_IDS)-{'right_front'}
    assert not server.reset_lock.locked()


def test_missing_selected_hold_manager_cannot_use_another_healthy_arm():
    server=fake();server.ports['right_front'].verified=False
    response=HardwareSupervisor.reset(server,None,SimpleNamespace(),arms={'right_front'})
    assert not response.success and not server.calls and server.core.blocked==set(ROBOT_IDS)


def test_simultaneous_reset_is_rejected_without_altering_existing_request():
    server=fake();server.reset_lock.acquire()
    response=HardwareSupervisor.reset(server,None,SimpleNamespace(),arms={'right_front'})
    assert not response.success and not server.calls and server.reset_lock.locked()
    server.reset_lock.release()


def test_witness_reports_stop_completion_even_after_software_reset():
    import json
    from uwa_cell_motion.hardware_nodes import HardwareWatchdog
    messages=[]
    fake=SimpleNamespace(ports={'right_front':SimpleNamespace(native_thread=SimpleNamespace(is_alive=lambda:True)),
        'right_rear':SimpleNamespace(native_thread=None)},sequence=0,signature='sig',armed=True,instance='i',tripped=False,
        publisher=SimpleNamespace(publish=lambda msg:messages.append(json.loads(msg.data))))
    HardwareWatchdog.publish(fake)
    assert messages[-1]['native_stop_pending']==['right_front'] and not messages[-1]['tripped']
    fake.ports['right_front'].native_thread=SimpleNamespace(is_alive=lambda:False)
    HardwareWatchdog.publish(fake)
    assert messages[-1]['native_stop_pending']==[]

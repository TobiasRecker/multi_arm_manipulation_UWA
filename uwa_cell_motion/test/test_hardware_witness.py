"""Reproduce a watchdog packet arriving while a supervisor tick acquires its lock."""
import json
from types import SimpleNamespace as NS
from uwa_cell_motion.hardware_nodes import HardwareSupervisor
from uwa_cell_motion.hardware_state import Peer


def test_tick_takes_time_after_lock_so_new_witness_is_not_marked_from_future(monkeypatch):
    from uwa_cell_motion import hardware_nodes
    clock=[1.]
    monkeypatch.setattr(hardware_nodes.time,'monotonic',lambda:clock[0])
    value=dict(hardware_signature='test',armed=False,instance='p',sequence=1,
               evaluated_monotonic_s=.99,tripped=False)
    guard,witness=Peer(),Peer()
    assert guard.receive(value,.99,'test',False)
    assert witness.receive(value,.99,'test',False)
    class Lock:
        def __enter__(self):
            # A heartbeat is received immediately before the tick gets the
            # lock. An earlier timestamp would make fresh() incorrectly fail.
            clock[0]=1.05
            assert witness.receive(dict(value,sequence=2,evaluated_monotonic_s=1.04),1.04,'test',False)
        def __exit__(self,*args):pass
    published=[]
    core=NS(tick=lambda now:set(),blocked=set(),last=None,reason='CLEAR')
    supervisor=NS(lock=Lock(),core=core,guard=guard,witness=witness,
        cfg=dict(heartbeat_timeout_s=.25),ports={},armed=False,stopping_since={},
        sequence=0,signature='test',instance='s',publisher=NS(publish=lambda msg:published.append(json.loads(msg.data))))
    HardwareSupervisor.tick(supervisor)
    assert not core.blocked
    assert published[0]['witness_available']
    assert 0 <= published[0]['witness_age_s'] < .02


def test_witness_callback_updates_peer_inside_supervisor_lock(monkeypatch):
    from uwa_cell_motion import hardware_nodes
    entered=[False]
    class Lock:
        def __enter__(self):entered[0]=True
        def __exit__(self,*args):entered[0]=False
    def receive(value,now,signature,armed):
        assert entered[0]
        assert value['sequence']==2
    supervisor=NS(lock=Lock(),witness=NS(receive=receive),signature='test',armed=False)
    HardwareSupervisor.receive_witness(supervisor,NS(data='{"sequence":2}'))

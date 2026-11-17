"""Use existing verified holds, never fresh empty RPC caches, for STOP proof."""
from types import SimpleNamespace
import pytest
from uwa_cell_motion import hardware_execution as execution


ARMS=('right_front','right_rear')


def client(monkeypatch, *, fail=None):
    clock=[0.];native=[];requests=[]
    ports={a:dict(held=False,manager_fresh=True,hardware_mode_verified=True,hold_config_verified=True) for a in ARMS}
    status=dict(armed=True,witness_available=True,ports=ports,blocked_arms=[])
    c=SimpleNamespace(handles={},cfg=dict(stop_latency_s=1.,heartbeat_timeout_s=.25),mode='hardware',
        problem=SimpleNamespace(profiles={a:dict(id=a) for a in ARMS}),supervisor=status)
    c.supervisor_peer=SimpleNamespace(fresh=lambda *args:fail!='stale')
    class StopClient:
        def service_is_ready(self):return True
        def call_async(self,request):requests.append(request);return object()
    c.stop_clients={a:StopClient() for a in ARMS}
    def spin_once(timeout_sec):
        if fail=='callback':raise RuntimeError('Independent observer failed')
        clock[0]+=timeout_sec
        if clock[0]>=.03:
            status['blocked_arms']=list(ARMS)
            if fail!='timeout':
                for port in ports.values():port['held']=True
    c.spin_once=spin_once
    if fail=='metadata':ports['right_rear']['hardware_mode_verified']=False
    if fail=='monitor':status['armed']=False
    if fail=='witness':status['witness_available']=False
    def fallback(profiles,mode):
        native.extend((r,'native fallback') for r in profiles)
        return {r:dict(acknowledged=True) for r in profiles}
    monkeypatch.setattr(execution,'stop_profiles',fallback)
    monkeypatch.setattr(execution.time,'monotonic',lambda:clock[0])
    return c,native,requests,clock


def test_existing_supervisor_hold_confirmation_does_not_interrupt_programs(monkeypatch):
    c,native,requests,clock=client(monkeypatch)
    result=execution.HardwareClient.stop(c,ARMS)
    assert len(requests)==2 and not native
    assert result['resource_holds_confirmed'] and result['latches_confirmed']
    assert not result['standstill_confirmed'] and not result['native_stop_requested_for']
    assert clock[0]<.1


@pytest.mark.parametrize('failure',['stale','metadata','monitor','witness','callback'])
def test_untrusted_confirmation_keeps_immediate_native_fallback(monkeypatch,failure):
    c,native,requests,clock=client(monkeypatch,fail=failure)
    result=execution.HardwareClient.stop(c,ARMS)
    assert {a for a,_ in native}==set(ARMS)
    assert not result['resource_holds_confirmed'] and not result['latches_confirmed']
    assert clock[0]<.1


def test_unconfirmed_hold_does_not_consume_more_than_the_existing_stop_latency(monkeypatch):
    c,native,requests,clock=client(monkeypatch,fail='timeout')
    result=execution.HardwareClient.stop(c,ARMS)
    assert {a for a,_ in native}==set(ARMS)
    assert 1.<=clock[0]<=1.02 and not result['resource_holds_confirmed']

"""Record the actual fallback request without changing dispatch/throttling."""
from types import SimpleNamespace
from uwa_cell_motion import hardware_ports as ports


class InlineThread:
    def __init__(self, target, daemon):self.target=target
    def start(self):self.target()
    def is_alive(self):return False


def port(monkeypatch, logger_failure=False):
    p=ports.StopPort.__new__(ports.StopPort)
    p.mode='hardware';p.profile={'id':'right_front'};p.native_thread=None
    p.native_sent=-float('inf');p.native_stop_events=[];p.native_ack=False;p.native_error=None
    logs=[];calls=[];clock=[1.]
    def log(message):
        if logger_failure:raise RuntimeError('logger unavailable')
        logs.append(message)
    p.node=SimpleNamespace(get_logger=lambda:SimpleNamespace(error=log))
    monkeypatch.setattr(ports.threading,'Thread',InlineThread)
    monkeypatch.setattr(ports.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(ports,'dashboard_stop',lambda profile:calls.append(profile))
    return p,calls,logs,clock


def test_reason_timestamps_ack_and_existing_throttle_are_retained(monkeypatch):
    p,calls,logs,clock=port(monkeypatch)
    p.native_stop('Manager verification stale')
    assert len(calls)==1 and p.native_ack
    assert p.native_stop_events==[dict(requested_monotonic_s=1.,reason='Manager verification stale',acknowledged=True,error=None)]
    clock[0]=1.1;p.native_stop('throttled second reason')
    assert len(calls)==1 and len(logs)==1 and len(p.native_stop_events)==1
    clock[0]=1.3;p.native_stop('Independent watchdog')
    assert len(calls)==2 and p.native_stop_events[-1]['reason']=='Independent watchdog'


def test_logging_failure_never_prevents_native_stop(monkeypatch):
    p,calls,logs,clock=port(monkeypatch,logger_failure=True)
    p.native_stop('Test fallback')
    assert len(calls)==1 and p.native_ack and p.native_stop_events[-1]['acknowledged']


def test_uncertain_stop_retains_error_without_fabricating_ack(monkeypatch):
    p,calls,logs,clock=port(monkeypatch)
    def fail(profile):raise OSError('connection ended')
    monkeypatch.setattr(ports,'dashboard_stop',fail)
    p.native_stop('Manager timeout')
    assert not p.native_ack and p.native_error=='connection ended'
    assert p.native_stop_events[-1]['error']=='connection ended'
    assert not p.native_stop_events[-1]['acknowledged']


def test_mock_stop_never_calls_real_dashboard(monkeypatch):
    p,calls,logs,clock=port(monkeypatch);p.mode='mock'
    p.native_stop('Mock only')
    assert p.native_ack and not calls and not logs and not p.native_stop_events

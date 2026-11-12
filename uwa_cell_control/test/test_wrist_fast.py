"""Fast native recovery must verify mode and use the exact service on fallback."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


def worker(monkeypatch):
    original = SimpleNamespace(restore=lambda *a: {'settings': a[1]},
        service_for_vision=lambda: ('/camera/exact', 123), wait_vision_exit=lambda pid: None)
    monkeypatch.setitem(sys.modules, 'wrist_worker', original)
    path = Path(__file__).resolve().parents[1] / 'remote/wrist_worker_fast.py'
    spec = importlib.util.spec_from_file_location('fast_worker_test', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.DIRECTORY = '/tmp/uwa_hd_this_request'
    return m


def test_fast_restore_requires_actual_format_and_interval_proof(monkeypatch):
    m = worker(monkeypatch)
    monkeypatch.setattr(m, 'verify_mode', lambda: {'verified': True, 'width': 640, 'height': 480})
    result = m.restore('/camera/exact', {'focus': 435})
    assert result['format_restore_strategy'] == 'visionserver_single_switch'
    assert result['v4l2_mode']['verified']


def test_mismatch_uses_explicit_restore_then_verifies_again(monkeypatch):
    m = worker(monkeypatch)
    attempts = []
    def verify():
        attempts.append(1)
        if len(attempts) == 1: raise RuntimeError('wrong interval')
        return {'verified': True}
    commands = []
    monkeypatch.setattr(m, 'verify_mode', verify)
    monkeypatch.setattr(m.subprocess, 'check_call', lambda args, **kw: commands.append(args))
    result = m.restore('/camera/exact', {'focus': 435})
    assert result['format_restore_strategy'] == 'explicit_fallback'
    assert commands[0] == ['sv', 'down', '/camera/exact']
    assert commands[1][1:] == ['--restore-mode', '/dev/video0', m.DIRECTORY]
    assert len(attempts) == 2


def test_changed_supervisor_or_failed_second_proof_cannot_succeed(monkeypatch):
    m = worker(monkeypatch)
    monkeypatch.setattr(m, 'verify_mode', lambda: (_ for _ in ()).throw(RuntimeError('wrong interval')))
    m.worker.service_for_vision = lambda: ('/other/service', 999)
    with pytest.raises(RuntimeError, match='identity changed'):
        m.restore('/camera/exact', {})
    m.worker.service_for_vision = lambda: ('/camera/exact', 123)
    monkeypatch.setattr(m.subprocess, 'check_call', lambda *a, **kw: None)
    with pytest.raises(RuntimeError, match='wrong interval'):
        m.restore('/camera/exact', {})

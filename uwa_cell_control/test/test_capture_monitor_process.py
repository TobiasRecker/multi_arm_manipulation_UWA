"""An image worker holding its GIL cannot stall the independent audit worker."""
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest
from uwa_cell_control.capture_telemetry import ProcessCaptureMonitor


def test_audit_keeps_recording_while_image_side_is_blocked(tmp_path,monkeypatch):
    popen=subprocess.Popen
    script='''import sys,time,json
from pathlib import Path
p=Path(sys.argv[1]);(p/'audit_ready.json').write_text('{}')
with (p/'ticks').open('w',buffering=1) as file:
 while not (p/'audit_finish').exists():file.write('tick\\n');time.sleep(.02)
(p/'stationarity.json').write_text(json.dumps(dict(stationarity_confirmed=True)))
'''
    def isolated(command,**kwargs):
        directory=command[command.index('--directory')+1]
        return popen([sys.executable,'-c',script,directory],**kwargs)
    monkeypatch.setattr(subprocess,'Popen',isolated)
    audit=ProcessCaptureMonitor(tmp_path,tmp_path,['arm'])
    try:
        audit.wait_still()
        # PyDLL deliberately holds THIS process's GIL for 0.8 s.
        ctypes.PyDLL(None).usleep(800000)
        assert len((tmp_path/'ticks').read_text().splitlines())>=20
        assert audit.finish()['stationarity_confirmed']
    finally:
        if audit.child.poll() is None:audit.finish()


def test_worker_exit_never_becomes_stationarity_pass(tmp_path,monkeypatch):
    popen=subprocess.Popen
    monkeypatch.setattr(subprocess,'Popen',lambda command,**kwargs:popen([sys.executable,'-c','raise SystemExit(2)'],**kwargs))
    audit=ProcessCaptureMonitor(tmp_path,tmp_path,['arm'])
    with pytest.raises(RuntimeError):audit.wait_still()
    with pytest.raises(RuntimeError):audit.finish()

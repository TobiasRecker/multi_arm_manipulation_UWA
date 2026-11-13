"""A GIL-blocked camera child cannot block the parent motion/stop event loop."""
from pathlib import Path
import sys
import time

from uwa_cell_control.scan_camera_worker import CameraProcess


def test_camera_process_keeps_parent_responsive_and_waits_for_restore(tmp_path, monkeypatch):
    import uwa_cell_control.scan_camera_worker as module
    popen = module.subprocess.Popen
    script = '''import sys,json,ctypes
from pathlib import Path
root=Path(sys.argv[1])
for line in sys.stdin:
 r=json.loads(line)
 if r['method']=='capture':ctypes.PyDLL(None).usleep(1200000)
 reply=dict(success=True,session='stationary-test',result={'method':r['method']})
 (root/(r['token']+'.json')).write_text(json.dumps(reply))
 if r['method']=='close':break
'''
    def isolated(command, **kwargs):
        return popen([sys.executable,'-c',script,command[-1]],**kwargs)
    monkeypatch.setattr(module.subprocess,'Popen',isolated)
    process=CameraProcess(tmp_path,tmp_path/'session')
    try:
        token=process.submit('capture');ticks=0;deadline=time.monotonic()+5
        while not process.ready(token):
            assert time.monotonic()<deadline
            ticks+=1;time.sleep(.02)
        assert ticks>=20
        assert process.result(token)=={'method':'capture'}
        assert process.session=='stationary-test'
        # Cleanup must wait for a second transaction rather than kill it.
        token=process.submit('capture');cleanup_ticks=[]
        def spin():cleanup_ticks.append(1);time.sleep(.02)
        process.close(spin)
        assert process.ready(token) and process.child.returncode==0
        assert len(cleanup_ticks)>=20
    finally:
        if process.child.poll() is None:process.close()

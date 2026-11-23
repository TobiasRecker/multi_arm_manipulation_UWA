"""Fresh native wrist frames, continuous ownership and controller recovery."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from uwa_cell_control.wrist_stream import ReplyReader, WristStream

REMOTE = Path(__file__).resolve().parents[1]/'remote'


def test_payload_can_follow_acquisition_confirmation():
    rd, wr = os.pipe()
    source = os.fdopen(rd, "rb", buffering=0)
    destination = os.fdopen(wr, "wb", buffering=0)
    try:
        reader = ReplyReader(source)
        destination.write(b'{"event":"frame","bytes":5}\n')
        header, data = reader.reply(1., lambda: destination.write(b'frame'))
        assert data == b'frame' and header['bytes'] == 5
    finally:
        source.close()
        destination.close()


def test_protocol_rejects_unbounded_payload():
    rd, wr = os.pipe()
    source = os.fdopen(rd, "rb", buffering=0)
    destination = os.fdopen(wr, "wb", buffering=0)
    try:
        destination.write(b'{"event":"frame","bytes":999999999}\n')
        with pytest.raises(ValueError, match='length'):
            ReplyReader(source).reply(1.)
    finally:
        source.close()
        destination.close()


def test_two_photos_one_owner_and_verified_close(monkeypatch, tmp_path):
    import uwa_cell_control.wrist_stream as client
    class Use:
        lease = None
        count = 0
        def __enter__(self):
            self.count += 1
        def __exit__(self, *args):
            self.count -= 1
    use = Use()
    monkeypatch.setattr(client.WristCamera, 'activity', lambda self: use)
    mock = tmp_path/'mock.py'
    mock.write_text('''import json,os,sys

def send(event, data=b'', **fields):
    fields.update(event=event, bytes=len(data))
    sys.stdout.buffer.write((json.dumps(fields)+'\\n').encode()+data)
    sys.stdout.buffer.flush()
send('ready',camera_identity={'id':'fake'},settings={'focus':245})
sequence = 5
while True:
    cmd=os.read(0,1)
    if cmd in (b'C', b'V'):
        sequence+=1
        send('frame', b'\\xff\\xd8abc', image_size=[2592,1944],device_sequence=sequence,
             sensor_controls={'focus_absolute':245, 'focus_auto':0})
    elif cmd==b'P':send('pong')
    else:
        send('closed',restore_ok=True)
        break
''')
    session = WristStream('left_front','127.0.0.1',tmp_path,245)
    monkeypatch.setattr(session, '_install', lambda: None)
    monkeypatch.setattr(session.ssh, 'base', lambda:[sys.executable,str(mock)])
    monkeypatch.setattr(session.ssh, 'run', lambda *args,**kwargs: None)
    session.start()
    try:
        assert use.count == 1
        _, live = session.read()
        acquired = []
        def clicked():
            acquired.append(time.monotonic())
            assert not (tmp_path/'set'/'image.jpg').exists()
        photo, meta = session.capture(tmp_path/'set', on_acquired=clicked)
        _, second = session.capture(tmp_path/'second')
        assert len(acquired) == 1 and photo.read_bytes().startswith(b'\xff\xd8')
        assert live['device_sequence'] < meta['device_sequence'] < second['device_sequence']
        assert use.count == 1
    finally:
        session.stop()
    session.stop()
    assert use.count == 0 and json.loads((session.directory/'restoration.json').read_text())['restore_ok']


def test_linux_native_abi_matches_headers(monkeypatch, tmp_path):
    import shutil
    if not shutil.which('cc') or not Path('/usr/include/linux/videodev2.h').exists():
        pytest.skip('Requires Linux V4L2 development headers')
    monkeypatch.syspath_prepend(str(REMOTE))
    import wrist_stream_v4l2 as driver
    probe = tmp_path/'probe'
    source = '''#include <linux/videodev2.h>
#include <stddef.h>
#include <stdio.h>
#define OFF(x) offsetof(struct v4l2_buffer,x)
int main(void) {
    printf("%zu %zu %zu %zu %zu %zu %zu %zu",sizeof(struct v4l2_format),
    offsetof(struct v4l2_format,fmt),sizeof(struct v4l2_buffer), OFF(timestamp),
    OFF(sequence),OFF(memory),OFF(m),OFF(length));return 0;}
'''
    subprocess.run(['cc','-x','c','-','-o',str(probe)], input=source.encode(), check=True)
    positions = list(map(int,subprocess.check_output([probe]).split()))
    assert positions == [driver.FORMAT_SIZE,driver.PIX_OFFSET,driver.BUFFER_SIZE,driver.TIME_OFFSET,
                         driver.SEQUENCE_OFFSET,driver.MEMORY_OFFSET,driver.MAP_OFFSET,driver.LENGTH_OFFSET]


def test_controller_restores_when_capture_owner_exits_without_cleanup(tmp_path):
    # Use a dedicated Python interpreter just like the remote ssh session.
    script = """import os,sys
sys.path.insert(0,sys.argv[1])
import wrist_stream_worker as worker
worker.restore_camera = lambda *args: dict(mode={'verified':True})
worker.restoration_watchdog(sys.argv[2],'camera-service',{'focus':1},None)
os._exit(1)
"""
    child = subprocess.run([sys.executable, '-c', script, str(REMOTE), str(tmp_path)])
    assert child.returncode == 1
    report = tmp_path/'restoration.json'
    due = time.monotonic()+3
    while not report.is_file() and time.monotonic()<due:
        time.sleep(.01)
    assert json.loads(report.read_text()) == {'restore_ok':True,'restoration':{'mode':{'verified':True}}}


def test_snapshot_flushes_queued_and_in_progress_frames(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.syspath_prepend(str(REMOTE))
    import wrist_stream_worker as worker
    events = iter(([4], [4], [4], [0, 4], [4], [0]))
    queued = iter(([4], [4], []))
    commands = iter((b'C', b'X'))
    sent = []
    class Camera:
        fd = 4
        maps = [None]*4
        sequence = 0
        def dequeue(self, copy_image):
            self.sequence += 1
            return {'device_sequence':self.sequence}, b'jpeg' if copy_image else None
    def poll(fds, writes, errors, timeout):
        return (next(queued) if len(fds) == 1 else next(events), [], [])
    monkeypatch.setattr(worker, 'select', SimpleNamespace(select=poll))
    monkeypatch.setattr(worker, 'os', SimpleNamespace(read=lambda *args: next(commands)))
    monkeypatch.setattr(worker, 'send', lambda header, data=None: sent.append((header,data)))
    monkeypatch.setattr(worker, 'checked_controls', lambda camera, focus: {'focus_absolute':focus})
    worker.stream(Camera(), {}, {}, 245)
    assert [header['event'] for header,_ in sent] == ['ready','frame']
    # Three warmup frames, two queued frames and the currently exposing frame.
    assert sent[1][0]['device_sequence'] == 7 and sent[1][1] == b'jpeg'

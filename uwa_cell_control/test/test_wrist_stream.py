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


def test_controller_restores_when_capture_owner_exits_without_cleanup(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(REMOTE))
    import wrist_stream_worker as worker
    monkeypatch.setattr(worker,'restore_camera',lambda *args: dict(mode={'verified':True}))
    dead = os.fork()
    if dead == 0:
        worker.restoration_watchdog(str(tmp_path),'camera-service',{'focus':1},None)
        os._exit(1)  # Simulate abrupt process loss without closing/releasing explicitly.
    os.waitpid(dead,0)
    report = tmp_path/'restoration.json'
    due = time.monotonic()+3
    while not report.is_file() and time.monotonic()<due:
        time.sleep(.01)
    assert json.loads(report.read_text()) == {'restore_ok':True,'restoration':{'mode':{'verified':True}}}

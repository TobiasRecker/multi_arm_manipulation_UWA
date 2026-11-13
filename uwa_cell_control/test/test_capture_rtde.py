"""Protocol framing and proof that the observer never sets RTDE inputs."""
import struct
import pytest
from uwa_cell_control.capture_rtde import OutputReader


def packet(kind,payload):return struct.pack('>HB',len(payload)+3,kind)+payload


class FakeSocket:
    def __init__(self,data):self.data=data;self.sent=[];self.closed=False
    def settimeout(self,value):pass
    def recv(self,count):
        part=self.data[:min(count,2)];self.data=self.data[len(part):];return part
    def sendall(self,value):self.sent.append(value)
    def close(self):self.closed=True


def reader(monkeypatch,recipe=7,timestamp=42.):
    fake=FakeSocket(packet(86,b'\x01')+packet(79,b'\x07DOUBLE,VECTOR6D,VECTOR6D')+
        packet(83,b'\x01')+packet(85,bytes([recipe])+struct.pack('>13d',timestamp,*range(12))))
    monkeypatch.setattr('socket.create_connection',lambda *a,**k:fake)
    return OutputReader('test'),fake


def test_output_only_recipe_partial_reads_and_no_input_commands(monkeypatch):
    obj,sock=reader(monkeypatch)
    timestamp,q,qd=obj.sample();assert timestamp==42.;assert q==list(range(6));assert qd==list(range(6,12))
    assert [p[2] for p in sock.sent]==[86,79,83]
    assert sock.sent[1][11:]==b'timestamp,actual_q,actual_qd'
    with pytest.raises(ValueError,match='Only output'):obj.request(73,b'anything')
    assert len(sock.sent)==3;obj.close();assert sock.closed


def test_wrong_recipe_and_nonfinite_controller_time_are_rejected(monkeypatch):
    obj,_=reader(monkeypatch,recipe=3)
    with pytest.raises(RuntimeError,match='Invalid RTDE'):obj.sample()
    obj.close();obj,_=reader(monkeypatch,timestamp=float('nan'))
    with pytest.raises(RuntimeError,match='timestamp'):obj.sample()
    obj.close()

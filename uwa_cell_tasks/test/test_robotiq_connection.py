"""Wire lifetime and framing against an in-memory protocol peer; no devices."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from uwa_cell_tasks.robotiq_gripper import Robotiq


def peer(monkeypatch,ack=b'ack'):
    registers=dict(ACT=1,STA=3,FLT=0,OBJ=3,POS=3,PRE=0,SPE=255,FOR=255,COU=0)
    connections=[]
    class Wire:
        def __init__(self):self.data=b'';self.commands=[];self.closed=False
        def settimeout(self,value):pass
        def sendall(self,data):
            self.commands.append(data.decode().strip());words=data.decode().split()
            if words[0]=='GET':self.data+=f'{words[1]} {registers[words[1]]}\n'.encode()
            else:
                for name,value in zip(words[1::2],words[2::2]):registers[name]=int(value)
                if 'GTO' in words:registers.update(PRE=registers['POS'],OBJ=3)
                self.data+=ack
        def recv(self,count):
            # Fragment all replies, including the ACK, like a TCP byte stream.
            count=min(count,2);result=self.data[:count];self.data=self.data[count:];return result
        def close(self):self.closed=True
    def connect(*args,**kwargs):
        wire=Wire();connections.append(wire);return wire
    monkeypatch.setattr('uwa_cell_tasks.robotiq_gripper.socket.create_connection',connect)
    monkeypatch.setattr('uwa_cell_tasks.robotiq_gripper.time.sleep',lambda _:None)
    return Robotiq('not-a-device',enabled=True,max_speed_raw=16),connections


def test_move_keeps_parameter_writes_and_confirmations_on_one_connection(monkeypatch):
    device,wires=peer(monkeypatch)
    result=device.command(1,0,16,0,2.)
    assert result['registers']['FOR']==0 and result['registers']['SPE']==16
    assert len(wires)==1 and wires[0].closed
    assert [c for c in wires[0].commands if c.startswith('SET')]==['SET FOR 0','SET SPE 16','SET POS 0','SET GTO 1']
    # A later independent GET does not retain or reuse a closed command socket.
    device.status();assert len(wires)==2 and all(w.closed for w in wires)


def test_bad_ack_closes_connection_and_never_reaches_position(monkeypatch):
    device,wires=peer(monkeypatch,ack=b'bad')
    with pytest.raises(RuntimeError,match='rejected'):device.command(1,0,16,0,2.)
    assert len(wires)==1 and wires[0].closed
    assert [c for c in wires[0].commands if c.startswith('SET')]==['SET FOR 0']


def test_other_thread_reads_do_not_share_a_command_socket(monkeypatch):
    device,wires=peer(monkeypatch);observed=[]
    def feedback(_):
        if not observed:
            with ThreadPoolExecutor(max_workers=1) as pool:observed.append(pool.submit(device.status).result())
    device.command(1,0,16,0,2.,feedback)
    assert len(wires)==2 and all(w.closed for w in wires)
    assert any(c.startswith('SET') for c in wires[0].commands)
    assert all(c.startswith('GET') for c in wires[1].commands)


def test_rejected_force_never_opens_any_connection(monkeypatch):
    device,wires=peer(monkeypatch)
    with pytest.raises(ValueError,match='force/speed'):device.command(1,0,16,1,2.)
    assert not wires

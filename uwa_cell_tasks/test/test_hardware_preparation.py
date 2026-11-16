"""Exercise the non-actuating boundary with fake transport, never real devices."""
import json
import socket
import struct
from pathlib import Path
import pytest
from uwa_cell_tasks import hardware_preparation as prep


class Socket:
    def __init__(self, replies):
        self.replies = list(replies); self.sent = []; self.closed = False
    def settimeout(self, value):
        pass
    def sendall(self, value):
        self.sent.append(value)
    def recv(self, size):
        return self.replies.pop(0) if self.replies else b''
    def close(self):
        self.closed = True


def test_read_only_probe_handles_fragmentation_without_activation(monkeypatch):
    values = dict(ACT=0, STA=0, FLT=0, OBJ=3, POS=120, PRE=120, SPE=0, FOR=20, COU=0)
    replies = []
    for name in prep.VARIABLES:
        message = f'{name} {values[name]}\n'.encode()
        replies.extend([message[:2], message[2:-1], message[-1:]])
    wire = Socket(replies)
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: wire)
    observer = prep.GripperObserver('test-only')
    result = observer.snapshot(); observer.close()
    assert result['registers'] == values and not result['activated']
    assert wire.sent == [('GET '+n+'\n').encode() for n in prep.VARIABLES]
    assert wire.closed and result['force_unit'] != 'N'


@pytest.mark.parametrize('name', ['SET ACT 1', 'ACT\nSET POS 255', 'ATR', 'RESET', 'POS 255'])
def test_no_write_command_can_be_injected(monkeypatch, name):
    wire = Socket([])
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: wire)
    observer = prep.GripperObserver('test-only')
    with pytest.raises(ValueError):
        observer.get(name)
    assert wire.sent == []


@pytest.mark.parametrize('reply', [b'POS 2', b'POS 999\n', b'ACT 1\n', b'POS -1\n', b'POS 2\nPOS 55\n'])
def test_missing_frame_wrong_register_or_out_of_range_fails(monkeypatch, reply):
    wire = Socket([reply])
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: wire)
    observer = prep.GripperObserver('test-only')
    with pytest.raises((RuntimeError, ValueError)):
        observer.get('POS')


def test_native_output_keeps_both_scaling_factors_and_base_frame():
    values = [12.]+[.1]*6+[0.]*6+[.2]*6+[4.9]*6+[.0]*6+[.5,.4]+[2,7,1]
    data = bytes([3])+struct.pack('>33dIii', *values)
    record = prep.decode_arm_output(data, 3)
    assert record['effective_speed_scaling'] == pytest.approx(.2)
    assert record['actual_tcp_pose_ur_base'] == [.2]*6
    assert record['actual_tcp_force_raw'] == [4.9]*6
    for broken in (data[:-1], bytes([4])+data[1:]):
        with pytest.raises(ValueError):
            prep.decode_arm_output(broken, 3)
    values[31] = float('nan')
    with pytest.raises(ValueError):
        prep.decode_arm_output(bytes([3])+struct.pack('>33dIii', *values), 3)


def test_offline_bundle_is_never_an_executable_hardware_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(prep, 'observe', lambda *a: pytest.fail('Offline preparation accessed devices'))
    repo = Path(__file__).parents[2]
    result = prep.prepare(tmp_path/'bundle', repo/'uwa_cell_tasks/config/carton_hardware_first_test.yaml',
                          repo/'config/hardware_inventory.yaml')
    assert result['prepared'] and not result['motion_ready'] and not result['hardware_plan']
    assert not result['actuation_capability'] and result['commands_sent'] == []
    assert json.loads((tmp_path/'bundle/observations.json').read_text())['arms'] == {}
    with pytest.raises(FileExistsError):
        prep.prepare(tmp_path/'bundle', repo/'uwa_cell_tasks/config/carton_hardware_first_test.yaml',
                     repo/'config/hardware_inventory.yaml')


def test_hardware_observer_refuses_simulation_or_mock_domain(monkeypatch):
    monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST')
    for domain in ('64', '67', '62'):
        monkeypatch.setenv('ROS_DOMAIN_ID', domain)
        with pytest.raises(ValueError):
            prep.require_observation_domain()

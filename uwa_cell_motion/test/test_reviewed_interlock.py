import hashlib
import json
import socket
import uuid
from types import SimpleNamespace

import numpy as np
import pytest

from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.motion_envelope import MotionEnvelope
from uwa_cell_motion.pilot_interlock import PilotGuardChannel, PilotInterlock, address, validate_operating_point
from uwa_cell_motion.pilot_mock import IsolatedPilotMock, Observation


ARM = 'right_front'


def description():
    items = []
    parent = 'world'
    for i, name in enumerate(joint_names(ARM)):
        child = f'{ARM}_joint_link_{i}'
        items.append(f'<joint name="{name}" type="revolute"><parent link="{parent}"/><child link="{child}"/>'
                     '<axis xyz="0 0 1"/></joint>')
        parent = child
    items.append(f'<joint name="tool" type="fixed"><parent link="{parent}"/><child link="{ARM}_tool0"/>'
                 '<origin xyz="0.3 0 0"/></joint>')
    items.append(f'<joint name="jaw" type="revolute"><parent link="{ARM}_tool0"/><child link="{ARM}_jaw"/></joint>')
    return '<robot name="fixture">' + ''.join(items) + '</robot>'


def envelope(joint=.1, tcp=.25/3):
    return MotionEnvelope(description(), {ARM:[dict(frame=ARM+'_tool0', offset_m=[0.,0.,0.]),
                                              dict(frame=ARM+'_tool0', offset_m=[.7,0.,0.])]}, joint, tcp)


def point(t, angle, derivatives=True):
    data = dict(time=t, positions=[0.]*5+[angle])
    if derivatives:
        data.update(velocities=[0.]*6, accelerations=[0.]*6)
    return data


def test_offset_jacobian_and_strict_measured_limits():
    env = envelope(joint=.3,tcp=.1)
    q, v = np.arange(6)*.05, [0.]*5+[.099]
    assert env.measured(ARM, q, v)['tcp_m_s'] == pytest.approx(.099)
    env.check_measured(ARM,q,v)
    with pytest.raises(ValueError, match='measured speed'):
        env.check_measured(ARM,q,[0.]*5+[.10001])
    with pytest.raises(ValueError, match='rigidly attached'):
        MotionEnvelope(description(),{ARM:ARM+'_jaw'},.1,.2)
    with pytest.raises(ValueError):
        env.check_measured(ARM,q,[float('nan')]*6)


def test_measured_joint_tolerance_preserves_strict_tcp_and_planned_limits():
    env=envelope(joint=.1,tcp=.25)
    q=[0.]*6
    env.check_measured(ARM,q,[0.]*5+[.115],joint_tolerance_ratio=.15)
    with pytest.raises(ValueError,match='joint_trip_rad_s=0.115'):
        env.check_measured(ARM,q,[0.]*5+[.115000001],joint_tolerance_ratio=.15)
    with pytest.raises(ValueError,match='measured speed'):
        envelope().check_measured(ARM,q,[0.]*5+[.09],joint_tolerance_ratio=.15)
    with pytest.raises(ValueError,match='interpolated'):
        env.check_trajectory(ARM,[point(0,0,False),point(1,.11,False)])


@pytest.mark.parametrize('derivatives', [False, True])
def test_curve_bound_and_normalized_retiming(derivatives):
    env = envelope()
    points = [point(0,0,derivatives),point(1,.1,derivatives)]
    with pytest.raises(ValueError, match='interpolated'):
        env.check_trajectory(ARM,points)
    scale = env.time_scale(ARM,points)
    expected_v = (.1 * 1.875) if derivatives else .1
    assert scale >= expected_v/env.tcp_limit_m_s - 1e-9
    assert scale < expected_v/env.tcp_limit_m_s * 1.02
    points[-1]['time'] *= scale
    assert env.check_trajectory(ARM,points)
    with pytest.raises(ValueError, match='time zero'):
        env.check_trajectory(ARM,[point(.1,0),point(.2,.01)])


def test_hermite_cubic_between_waypoint_peak():
    env = envelope(.15,.25)
    pts = [point(0,0),point(1,.115)]
    for p in pts:
        del p['accelerations']
    assert env.time_scale(ARM,pts) == pytest.approx(.115*1.5/.15, rel=.001)
    with pytest.raises(ValueError):
        env.check_trajectory(ARM,pts)


def proof():
    status = dict(faults=[], stationary_arms=list(ROBOT_IDS))
    ports = {r:dict(manager_fresh=True,hardware_mode_verified=True,hold_config_verified=True,held=True)
             for r in ROBOT_IDS}
    supervisor = dict(armed=True,witness_available=True,held_arms=list(ROBOT_IDS),
                      blocked_arms=list(ROBOT_IDS),ports=ports)
    records = {r:dict(q=[0.]*6,v=[0.]*6) for r in ROBOT_IDS}
    return records,status,supervisor


class Cell:
    def __init__(self, tolerance=None):
        self.problem = SimpleNamespace(original_description=description(), cfg=dict(
            heartbeat_timeout_s=.25, velocity_limit_rad_s=.1, command_velocity_limit_rad_s=.1))
        if tolerance is not None:self.problem.cfg['measured_joint_speed_tolerance_ratio']=tolerance
        self.sig = uuid.uuid4().hex
        self.instance = uuid.uuid4().hex
        self.channel = PilotGuardChannel(self.problem, 'mock', self.sig, self.instance)
        self.now = 15.
        self.records,self.status,self.supervisor = proof()

    def tick(self, dt=.01):
        self.now += dt
        return self.channel.tick(self.now,self.records,self.status,self.supervisor, True)

    def connect(self):
        s = socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET)
        s.settimeout(.2)
        s.connect(address(self.sig, self.instance))
        return s

    def acquire(self,s):
        env = envelope()
        s.send(json.dumps(dict(op='acquire', spec=env.spec, digest=env.digest)).encode())
        faults, state = self.tick()
        return json.loads(s.recv(8192)),faults,state


def test_guard_channel_uses_profile_tolerance_at_admission_and_during_execution():
    cell=Cell(tolerance=.15)
    try:
        cell.records[ARM]['v'][:2]=[.115,-.115]  # Coaxial fixture: zero TCP speed.
        with cell.connect() as s:
            answer,faults,summary=cell.acquire(s)
            assert answer['ok'] and not faults
            assert summary['measured_joint_trip_limit_rad_s']==.115
            assert summary['speed_envelope']['joint_limit_rad_s']==.1
            cell.records[ARM]['v'][:2]=[.115000001,-.115000001]
            faults,_=cell.tick()
            assert faults[0]['reason']=='REVIEWED JOINT/TCP SPEED OR STATE INVALID'
    finally:
        cell.channel.close()


def test_guard_exclusive_admission_endpoint_idle_unknown_always_armed():
    cell = Cell()
    try:
        with cell.connect() as s:
            cell.status['stationary_arms'] = [ARM]
            answer, _, summary = cell.acquire(s)
            assert not answer['ok'] and summary['state']=='ARMED_HOLD_OR_EXTERNAL_SOURCE'
        cell.status['stationary_arms'] = list(ROBOT_IDS)
        with cell.connect() as s:
            answer, faults, summary = cell.acquire(s)
            assert answer['ok'] and not faults and summary['digest']==envelope().digest
            assert summary['exclusive_commands_proved'] is False
            with cell.connect() as competing:
                cell.tick()
                assert competing.recv(8192)==b''
            cell.records[ARM]['v'][-1] = .095  # axis passes .1, offset TCP exceeds .0833
            faults,_ = cell.tick()
            assert 'SPEED' in faults[0]['reason']
            cell.records[ARM]['v'][-1] = 0.
        faults,state = cell.tick()
        assert 'OWNER LOST' in faults[0]['reason'] and state['speed_envelope']
        with cell.connect() as s:
            answer, _, _ = cell.acquire(s)
            assert answer['ok']
            cell.tick(.249)
            faults, summary = cell.tick(.002)
            assert 'OWNER LOST' in faults[0]['reason'] and not summary['token']
    finally:
        cell.channel.close()


def test_release_requires_all_fresh_holds_and_preserves_tcp_guard():
    cell = Cell()
    try:
        for held in (False,True):
            with cell.connect() as s:
                reply,_,_ = cell.acquire(s)
                assert reply['ok']
                cell.supervisor['ports'][ARM]['held'] = held
                s.send(json.dumps(dict(op='release',token=reply['token'])).encode())
                faults,status = cell.tick()
                assert bool(faults) is not held
                assert json.loads(s.recv(8192))['ok'] is held
                assert status['speed_envelope'] and not status['token']
                cell.supervisor['ports'][ARM]['held'] = True
    finally:
        cell.channel.close()


def test_live_client_handshake_and_progress_pumping():
    import time
    from threading import Thread, Event
    cell = Cell()
    done = Event()
    def guard():
        while not done.wait(.004):
            cell.channel.tick(time.monotonic(),cell.records,cell.status,cell.supervisor,True)
    worker = Thread(target=guard)
    worker.start()
    stops=[]
    client = SimpleNamespace(mode='mock',problem=cell.problem,expected=cell.sig,cfg=cell.problem.cfg,
                             guard=dict(armed=True,instance=cell.instance,pilot=dict(state='ARMED_HOLD_OR_EXTERNAL_SOURCE')),
                             spin_once=lambda timeout_sec=.002:time.sleep(timeout_sec),health=lambda:None,
                             stop=lambda arms:stops.extend(arms))
    review = [True]
    lock = PilotInterlock(client,envelope(),arms=[ARM],check_review=lambda: review[0])
    try:
        with lock.execution():
            start=time.monotonic()
            while time.monotonic()-start < .45:
                client.spin_once(timeout_sec=.01)
            lock.check()
        assert not stops
        with pytest.raises(RuntimeError,match='approval'):
            with lock.execution():
                review[0]=False
                lock.check()
        assert stops == [ARM]
    finally:
        done.set()
        worker.join()
        cell.channel.close()


def test_operating_point_needs_matching_measured_profile_report(tmp_path):
    env = envelope(.2,.15)
    cfg=dict(velocity_limit_rad_s=.2, stopping_reserve_policy='enforce')
    problem=SimpleNamespace(cfg=cfg,signature='cell-model',profiles={ARM:dict(serial='fixture')})
    with pytest.raises(ValueError,match='qualification'):
        validate_operating_point(problem,'hardware',env)
    path=tmp_path/'commissioning.json'
    report=dict(kind='measured_pilot_stopping_qualification',accepted=True,model_signature=problem.signature,
                guard_configuration=dict(cfg),tcp_frames=env.spec['tcp_frames'],joint_limit_rad_s=.2,tcp_limit_m_s=.15,
                hardware_profiles_sha256=hashlib.sha256(json.dumps(problem.profiles,sort_keys=True).encode()).hexdigest())
    path.write_text(json.dumps(report))
    cfg['pilot_operating_qualification']=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    validate_operating_point(problem,'hardware',env)
    path.write_text('{}')
    with pytest.raises(ValueError,match='changed'):
        validate_operating_point(problem,'hardware',env)


def test_idle_exclusion_restart_contact_and_loss_in_private_mock():
    clock = [100.]
    cell = IsolatedPilotMock({r:[0.]*6 for r in ROBOT_IDS},clock=lambda:clock[0])
    quiet=Observation(True,True,True)
    cell.observe(quiet)
    assert cell.state=='IDLE'
    cell.observe(Observation(False,False,True))
    assert cell.tick()=='IDLE'
    with pytest.raises(RuntimeError):
        cell.begin([ARM])
    with pytest.raises(RuntimeError):
        cell.command(None,ARM,[1]*6)
    cell.observe(quiet)
    token=cell.begin([ARM])
    cell.command(token,ARM,[.1]*6)
    with pytest.raises(RuntimeError):
        cell.end(token)
    cell.observe(quiet)
    cell.end(token)
    next_owner=cell.begin([ARM])
    with pytest.raises(RuntimeError):
        cell.command(token,ARM,[1.]*6)
    cell.owner_lost(next_owner)
    cell.observe(quiet)
    assert cell.state=='FAULT_HOLD'
    cell.reset_unloaded()
    owner=cell.begin([ARM])
    clock[0]+=.251
    assert cell.tick()=='FAULT_HOLD'
    cell.restart()
    with pytest.raises(RuntimeError):
        cell.command(owner,ARM,[2]*6)
    cell.observe(Observation(True,True,False))
    assert cell.state=='CONTACT_HOLD'
    with pytest.raises(RuntimeError):
        cell.reset_unloaded()
    cell.observe(quiet)
    assert cell.state=='CONTACT_HOLD'
    cell.reset_unloaded()
    assert cell.positions()[ARM]==[.1]*6


def test_executor_process_death_latches_even_without_a_finalizer():
    import os
    import subprocess
    import sys
    import time
    cell = Cell()
    code = """
import json, os, socket, sys, time
addr, packet = sys.argv[1:]
s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
s.connect(chr(0) + addr)
s.send(packet.encode())
reply=json.loads(s.recv(8192))
os._exit(0 if reply.get('ok') else 1)
"""
    packet=json.dumps(dict(op='acquire',spec=envelope().spec,digest=envelope().digest))
    proc = subprocess.Popen([sys.executable, '-c', code, address(cell.sig,cell.instance)[1:], packet])
    seen=[]
    try:
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            faults, state=cell.channel.tick(time.monotonic(),cell.records,cell.status,cell.supervisor,True)
            seen.extend(f['reason'] for f in faults)
            if seen:
                break
            time.sleep(.002)
        assert proc.wait(timeout=1)==0
        assert 'REVIEWED EXECUTION OWNER LOST' in seen and not state['token']
    finally:
        if proc.poll() is None:
            proc.terminate()
        proc.wait(timeout=2)
        cell.channel.close()

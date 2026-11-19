"""Host-local ownership of an additional speed envelope for reviewed actions.

The physical cell also has pendant, controller-manager and direct action command
sources. An absent pilot owner never proves those sources inhibited. Its armed
guard therefore stays armed before admission, throughout holds and after exit.
"""
from contextlib import contextmanager
import hashlib
import json
import os
import socket
import struct
import time
import uuid
from pathlib import Path

from .common import ROBOT_IDS, joint_velocity_limits
from .motion_envelope import MotionEnvelope


def address(signature, instance):
    digest = hashlib.sha256((signature + '/' + instance).encode()).hexdigest()
    return '\0uwa-reviewed-motion-' + str(os.getuid()) + '-' + digest


def _message(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()


def all_held(status, supervisor, fresh):
    arms = set(ROBOT_IDS)
    return bool(fresh and supervisor.get('armed') is True and supervisor.get('witness_available') is True
                and set(supervisor.get('blocked_arms', ())) == arms and set(supervisor.get('held_arms', ())) == arms
                and set(status.get('stationary_arms', ())) == arms and not status.get('faults')
                and all(all(supervisor.get('ports', {}).get(r, {}).get(k) is True for k in
                            ('manager_fresh', 'hardware_mode_verified', 'hold_config_verified', 'held')) for r in arms))


def _qualification(problem):
    ref = problem.cfg.get('pilot_operating_qualification')
    if not ref:
        return None
    path = Path(ref['path'])
    if not path.is_absolute():
        raise ValueError('Absolute local qualification report path required')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise ValueError('Hardware operating-point qualification report changed')
    return json.loads(raw)


def validate_operating_point(problem, mode, env, qualification_loader=_qualification):
    for arm in env.chains:
        maximum = min(min(joint_velocity_limits(problem.cfg, arm)), problem.cfg.get(
            'command_velocity_limit_rad_s', problem.cfg['velocity_limit_rad_s']))
        if env.joint_limit_rad_s > maximum + 1e-14:
            raise ValueError('Reviewed joint speed exceeds active hardware profile for ' + arm)
    if mode != 'hardware' or (env.joint_limit_rad_s <= .1 + 1e-14 and env.tcp_limit_m_s <= .25 / 3 + 1e-14):
        return
    report = qualification_loader(problem)
    if not report or problem.cfg.get('stopping_reserve_policy', 'enforce') != 'enforce':
        raise ValueError('Higher hardware operating point requires measured qualification and active stopping reserves')
    # The evidence is supplied by physical commissioning. Pilot settings,
    # operator acceptance and simulations cannot author this qualification.
    expected_cfg = {k:v for k,v in problem.cfg.items() if k != 'pilot_operating_qualification'}
    profile_hash = hashlib.sha256(json.dumps(problem.profiles,sort_keys=True).encode()).hexdigest()
    if (report.get('kind') != 'measured_pilot_stopping_qualification' or report.get('accepted') is not True
            or report.get('model_signature') != problem.signature or report.get('guard_configuration') != expected_cfg
            or report.get('hardware_profiles_sha256') != profile_hash
            or any(report.get('tcp_frames', {}).get(arm) != frames for arm, frames in env.spec['tcp_frames'].items())
            or not env.joint_limit_rad_s <= float(report.get('joint_limit_rad_s', 0)) <= .3
            or not env.tcp_limit_m_s <= float(report.get('tcp_limit_m_s', 0)) <= .25):
        raise ValueError('Qualification does not cover this model, profile, TCP binding and speed')


class PilotGuardChannel:
    """Serviced by the armed guard on its own steady-time tick, never blocks on I/O."""
    def __init__(self, problem, mode, signature, instance):
        self.problem = problem
        self.mode = mode
        self.timeout = problem.cfg['heartbeat_timeout_s']
        self.qualification = _qualification(problem) if mode == 'hardware' else None
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.listener.setblocking(False)
        self.listener.bind(address(signature, instance))
        self.listener.listen(4)
        self.client = None
        self.token = None
        self.envelope = None
        self.last = 0.
        self.loss = None

    def _disconnect(self):
        if self.client:
            self.client.close()
        self.client = None
        self.token = None

    def _accept(self, now):
        try:
            peer, _ = self.listener.accept()
        except BlockingIOError:
            return
        peer.setblocking(False)
        _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))
        if uid != os.getuid() or self.client is not None:
            peer.close()
        else:
            self.client, self.last = peer, now

    def tick(self, now, records, status, supervisor, fresh):
        self._accept(now)
        if self.client is not None:
            try:
                if now - self.last > self.timeout:
                    raise ValueError('Reviewed executor heartbeat expired')
                for _ in range(4):
                    try:
                        data = self.client.recv(16384)
                    except BlockingIOError:
                        break
                    if not data:
                        raise ValueError('Reviewed executor disconnected')
                    request = json.loads(data)
                    op = request.get('op')
                    if op == 'acquire' and self.token is None:
                        if not all_held(status, supervisor, fresh):
                            raise ValueError('A fresh armed cell and all four resource holds and stationary arms are required')
                        env = MotionEnvelope(self.problem.original_description, **request['spec'])
                        if env.digest != request['digest']:
                            raise ValueError('Reviewed TCP/speed identity mismatch')
                        validate_operating_point(self.problem, self.mode, env, lambda _: self.qualification)
                        for arm in env.chains:
                            env.check_measured(arm, records[arm]['q'], records[arm]['v'])
                        self.envelope = env
                        self.token = uuid.uuid4().hex
                        self.loss = None
                        self.client.send(_message(dict(ok=True, token=self.token, digest=env.digest)))
                    elif self.token and request.get('token') == self.token and op == 'heartbeat':
                        pass
                    elif self.token and request.get('token') == self.token and op == 'release':
                        if not all_held(status, supervisor, fresh):
                            raise ValueError('Reviewed execution ended without all four fresh stationary resource holds')
                        self.client.send(_message(dict(ok=True, released=True)))
                        self._disconnect()
                        # Keep the last speed envelope applied until a fresh
                        # atomic admission replaces it, including after contact.
                        break
                    else:
                        raise ValueError('Invalid reviewed execution ownership')
                    self.last = now
            except (ValueError, OSError, TypeError, AttributeError, KeyError, OverflowError) as error:
                if self.token:
                    self.loss = str(error)
                try:
                    self.client.send(_message(dict(ok=False, error=str(error))))
                except OSError:
                    pass
                self._disconnect()
        faults = []
        if self.loss:
            # A single cause is enough to latch the physical guard. It cannot
            # continuously block the operator's normal stationary reset.
            faults.append(dict(arms=list(ROBOT_IDS), reason='REVIEWED EXECUTION OWNER LOST', detail=self.loss))
            self.loss = None
        measured = {}
        if self.envelope:
            for arm in self.envelope.chains:
                try:
                    row = records[arm]
                    measured[arm] = self.envelope.check_measured(arm, row['q'], row['v'])
                except (KeyError, ValueError) as error:
                    faults.append(dict(arms=list(ROBOT_IDS), reason='REVIEWED JOINT/TCP SPEED OR STATE INVALID', detail=str(error)))
        summary = dict(state='REVIEWED_EXECUTION' if self.token else 'ARMED_HOLD_OR_EXTERNAL_SOURCE',
                       exclusive_commands_proved=False, token=self.token, measured=measured,
                       speed_envelope=None if self.envelope is None else self.envelope.spec,
                       digest=None if self.envelope is None else self.envelope.digest)
        return faults, summary

    def close(self):
        self._disconnect()
        self.listener.close()


class PilotInterlock:
    def __init__(self, client, envelope, *, check_review, arms):
        self.client = client
        self.envelope = envelope
        self.check_review = check_review
        self.arms = tuple(arms)
        if not self.arms or not set(self.arms) <= envelope.chains.keys():
            raise ValueError('Active arms require bound and monitored TCPs')
        self.channel = None
        self.token = None
        self.last_sent = 0.
        self._spin = client.spin_once
        self.guard_instance = None

    def _spin_with_progress(self, *args, **kwargs):
        # Resource switches, action acknowledgements and confirmed-stop waits
        # use this entry point too. Only a progressing executor renews ownership.
        result = self._spin(*args, **kwargs)
        if self.token and time.monotonic() - self.last_sent >= self.client.cfg['heartbeat_timeout_s'] / 5:
            self.check()
        return result

    def _review(self):
        if self.check_review() is False:
            raise RuntimeError('Motion approval expired')

    def _request(self, request):
        self.channel.send(_message(request))
        deadline = time.monotonic() + self.client.cfg['heartbeat_timeout_s']
        while time.monotonic() < deadline:
            try:
                data = self.channel.recv(16384)
            except BlockingIOError:
                self._spin(timeout_sec=.003)
                continue
            if not data:
                raise RuntimeError('Armed motion guard disconnected')
            reply = json.loads(data)
            if reply.get('ok') is not True:
                raise RuntimeError('Guard rejected motion ownership: ' + str(reply.get('error')))
            return reply
        raise RuntimeError('Armed motion guard did not confirm ownership')

    def check(self):
        self._review()
        if not self.channel or not self.token:
            raise RuntimeError('No active reviewed execution')
        if (self.client.guard or {}).get('instance') != self.guard_instance:
            raise RuntimeError('Armed guard instance changed during reviewed execution')
        # A supervisory fault may arrive while awaiting an Action reply.
        try:
            notice = self.channel.recv(16384)
        except BlockingIOError:
            notice = None
        if notice is not None:
            raise RuntimeError('Reviewed guard ended ownership: ' + notice.decode(errors='replace'))
        now = time.monotonic()
        if now - self.last_sent >= self.client.cfg['heartbeat_timeout_s'] / 5:
            self.channel.send(_message(dict(op='heartbeat', token=self.token)))
            self.last_sent = now

    @contextmanager
    def execution(self):
        self._review()
        self.client.health()
        guard = self.client.guard or {}
        self.guard_instance = guard.get('instance')
        if (not self.guard_instance or guard.get('armed') is not True or
                (guard.get('pilot') or {}).get('state') not in ('ARMED_HOLD_OR_EXTERNAL_SOURCE','REVIEWED_EXECUTION')):
            raise RuntimeError('Current armed guard has no available reviewed execution channel')
        validate_operating_point(self.client.problem, self.client.mode, self.envelope)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.channel = sock
        own_spin = self.client.__dict__.get('spin_once')
        try:
            sock.settimeout(self.client.cfg['heartbeat_timeout_s'])
            sock.connect(address(self.client.expected, self.guard_instance))
            sock.setblocking(False)
            reply = self._request(dict(op='acquire', digest=self.envelope.digest, spec=self.envelope.spec))
            if reply.get('digest') != self.envelope.digest or not reply.get('token'):
                raise RuntimeError('Unexpected reviewed speed envelope on the live guard')
            self.token = reply['token']
            self.client.spin_once = self._spin_with_progress
            self.check()
            yield self
            self.check()
            reply = self._request(dict(op='release', token=self.token))
            if reply.get('released') is not True:
                raise RuntimeError('Armed hold handover failed')
        except BaseException:
            sock.close()  # independent guard can latch even if client.stop fails
            if self.token:
                self.token = None
                self.client.stop(self.arms)
            raise
        finally:
            sock.close()
            self.token = None
            self.channel = None
            if own_spin is None:
                self.client.__dict__.pop('spin_once', None)
            else:
                self.client.spin_once = own_spin

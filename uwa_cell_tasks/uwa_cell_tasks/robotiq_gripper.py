"""Explicit Robotiq transport; no writes until an individually requested command.

SET framing, acknowledgement and register semantics follow the locally backed-up
Robotiq1.8.6 GripperCommunicationScript/GripperInstallationNodeScript.
No URScript, Dashboard, controller-manager or robot power commands exist here.
"""
import math
import socket
import threading
import time
from .hardware_preparation import GripperObserver


class Robotiq:
    def __init__(self, host, *, port=63352, enabled=False, max_force_raw=0, max_speed_raw=32):
        self.host, self.port, self.enabled = host, port, enabled
        self.max_force_raw, self.max_speed_raw = max_force_raw, max_speed_raw
        self.last_requested = None
        self._transaction = threading.local()

    def _reader(self):
        if getattr(self._transaction, 'active', False):
            existing = getattr(self._transaction, 'reader', None)
            if existing is not None:
                return existing
        observer = GripperObserver.__new__(GripperObserver)
        observer.socket = socket.create_connection((self.host, self.port), timeout=.5)
        observer.socket.settimeout(.5); observer.timeout=.5; observer.buffer=b''
        if getattr(self._transaction, 'active', False):
            self._transaction.reader = observer
        return observer

    def status(self):
        # One command owns one connection, including its strict GET replies.
        # Independent read requests keep their existing output-only connection.
        observer = self._reader()
        try:
            return observer.snapshot()
        finally:
            if not getattr(self._transaction, 'active', False):
                observer.close()

    def validate(self, operation, position, speed, force, timeout):
        if not self.enabled:
            raise ValueError('MONITOR ONLY: activation and movement disabled')
        if operation not in (1, 2):
            raise ValueError('Unsupported gripper operation')
        if any(type(v) is not int or not 0 <= v <= 255 for v in (position, speed, force)):
            raise ValueError('Raw registers must be integers0..255')
        if force > self.max_force_raw or speed > self.max_speed_raw:
            raise ValueError('Raw force/speed exceeds this commissioning profile')
        if not math.isfinite(timeout) or not 1. <= timeout <= 30.:
            raise ValueError('Command timeout must be1..30s')

    def _set(self, pairs):
        if not self.enabled:
            raise ValueError('MONITOR ONLY')
        allowed = {'ACT', 'POS', 'SPE', 'FOR', 'GTO'}
        if any(k not in allowed or type(v) is not int or not 0 <= v <= 255 for k, v in pairs):
            raise ValueError('Invalid Robotiq SET')
        command = ('SET '+' '.join(f'{k} {v}' for k, v in pairs)+'\n').encode('ascii')
        # Vendor ACK is exactly three bytes. Keep SET and confirmation GETs on
        # the same command connection: real RF/RR probes25November confirmed
        # parameter readback there after the former reconnect path failed.
        retained = getattr(self._transaction, 'active', False)
        wire = (self._reader().socket if retained else
                socket.create_connection((self.host, self.port), timeout=.5))
        try:
            wire.settimeout(.5); wire.sendall(command); reply=b''
            while len(reply) < 3:
                chunk=wire.recv(3-len(reply))
                if not chunk:
                    raise RuntimeError('Command outcome uncertain: incomplete acknowledgement; no retry')
                reply += chunk
            if reply != b'ack':
                raise RuntimeError('Gripper command rejected; no automatic retry')
        finally:
            if not retained:
                wire.close()

    def _wait(self, predicate, deadline, feedback, activation=False, *, stage, expected):
        consecutive = 0
        state = None
        while time.monotonic() < deadline:
            state=self.status(); regs=state['registers']; feedback(state)
            if regs['FLT'] >= 8 or (not activation and regs['FLT'] != 0):
                raise RuntimeError(f"Gripper fault {regs['FLT']}; target retained, no reset/open")
            consecutive = consecutive+1 if predicate(regs) else 0
            if consecutive >= 2:
                return state
            time.sleep(.05)
        registers = ('not observed during this step' if state is None else
                     ' '.join(f'{key}={value}' for key, value in state['registers'].items()))
        raise TimeoutError(f'Gripper outcome unconfirmed during {stage}; expected {expected}; '
                           f'last registers: {registers}; no reset/open or automatic command retry')

    def command(self, operation, position, speed, force, timeout, feedback=lambda value: None):
        self.validate(operation, position, speed, force, timeout)
        if getattr(self._transaction, 'active', False):
            raise RuntimeError('A gripper command is already active on this thread')
        self._transaction.active = True
        self._transaction.reader = None
        try:
            return self._command(operation, position, speed, force, timeout, feedback)
        finally:
            reader = self._transaction.reader
            self._transaction.active = False
            self._transaction.reader = None
            if reader is not None:
                reader.close()

    def _command(self, operation, position, speed, force, timeout, feedback):
        self.validate(operation, position, speed, force, timeout)
        deadline=time.monotonic()+timeout
        if operation == 2:
            # Activation is a separate explicit goal, never a side effect of
            # node startup or MOVE. The vendor requires reset before activation.
            state=self.status()
            if state['activated'] and state['fault_free']:
                return state
            self._set([('ACT', 0)])
            self._wait(lambda r:r['ACT']==0 and r['STA']==0, deadline, feedback, activation=True,
                       stage='activation reset', expected='ACT=0 STA=0')
            self._set([('ACT', 1)])
            return self._wait(lambda r:r['ACT']==1 and r['STA']==3 and r['FLT']==0,
                              deadline, feedback, activation=True,
                              stage='activation', expected='ACT=1 STA=3 FLT=0')
        state=self.status()
        if not state['activated'] or not state['fault_free']:
            raise RuntimeError('Gripper inactive/faulted; explicit activation required, no MOVE sent')
        self.last_requested=dict(position_raw=position, speed_raw=speed, force_raw=force)
        # Real commissioning found that an ACK to a batched POS/SPE/FOR did
        # not establish matching parameter readback on these URCap servers.
        # Configure and verify limits before changing POS: GTO may already be
        # latched from an earlier move, so a new POS can itself start motion.
        self._set([('FOR', force)])
        self._wait(lambda r:r['ACT']==1 and r['STA']==3 and r['FOR']==force,
                   deadline, feedback, stage='force confirmation', expected=f'ACT=1 STA=3 FOR={force}')
        self._set([('SPE', speed)])
        self._wait(lambda r:r['ACT']==1 and r['STA']==3 and r['SPE']==speed and r['FOR']==force,
                   deadline, feedback, stage='speed confirmation', expected=f'ACT=1 STA=3 SPE={speed} FOR={force}')
        self._set([('POS', position)])
        self._set([('GTO', 1)])
        return self._wait(lambda r:r['ACT']==1 and r['STA']==3 and r['PRE']==position and r['OBJ'] in (1,2,3),
                          deadline, feedback, stage='movement completion', expected=f'ACT=1 STA=3 PRE={position} OBJ=1/2/3')

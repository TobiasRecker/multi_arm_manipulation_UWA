"""In-process pilot mock with one command sink and no ROS or device interfaces."""
from dataclasses import dataclass
import threading
import time
import uuid

import numpy as np

from .common import ROBOT_IDS


@dataclass(frozen=True)
class Observation:
    healthy: bool
    held: bool
    unloaded: bool


class IsolatedPilotMock:
    """Actual gate at the mock's only write path. A graph-connected ROS mock
    or real UR cannot use this exclusion proof. Both have other command paths.
    """
    def __init__(self, positions, *, clock=time.monotonic, timeout=.25):
        if set(positions) != set(ROBOT_IDS):
            raise ValueError('A complete mock cell is required')
        self._q = {arm: self._joints(q) for arm,q in positions.items()}
        self._lock = threading.Lock()
        self._clock = clock
        self._timeout = timeout
        self.restart()

    @staticmethod
    def _joints(q):
        q = np.array(q, dtype=float, copy=True)
        if q.shape != (6,) or not np.isfinite(q).all():
            raise ValueError('Invalid mock joint state')
        return q

    def _hold(self, state):
        self._owner = None
        self._arms = frozenset()
        self.state = state

    def restart(self):
        with self._lock:
            before = getattr(self, 'state', None)
            if before == 'CONTACT_HOLD':
                self._hold('CONTACT_HOLD')
            elif before in ('EXECUTING','FAULT_HOLD'):
                self._hold('FAULT_HOLD')
            else:
                self._hold('UNKNOWN_HOLD')
            self._observation = None
            self._observed = -float('inf')
            self._started = self._clock()

    def observe(self, observation, sampled_at=None):
        if not isinstance(observation, Observation):
            raise ValueError('Mock observation required')
        with self._lock:
            now = self._clock()
            stamp = now if sampled_at is None else sampled_at
            if not np.isfinite(stamp) or stamp < max(self._observed,self._started) or stamp > now:
                raise ValueError('Stale epoch or invalid mock sample time')
            self._observed = stamp
            self._observation = observation
            if not observation.unloaded:
                self._hold('CONTACT_HOLD')
            elif self.state == 'EXECUTING' and not observation.healthy:
                self._hold('FAULT_HOLD')
            elif self.state in ('UNKNOWN_HOLD', 'IDLE') and observation.healthy and observation.held:
                # The in-process sink still has no owner here. All old command
                # tokens are invalid; observations can never write a target.
                self.state = 'IDLE'

    def _ready(self):
        now = self._clock()
        return (self._observation is not None and self._observation.healthy and self._observation.unloaded
                and 0 <= now - self._observed <= self._timeout)

    def begin(self, arms):
        arms = frozenset(arms)
        with self._lock:
            if not arms or not arms <= self._q.keys() or self.state != 'IDLE' or not self._ready() or not self._observation.held:
                raise RuntimeError('Current stationary unloaded mock cell required')
            self._owner = uuid.uuid4().hex
            self._arms = arms
            self.state = 'EXECUTING'
            return self._owner

    def command(self, owner, arm, q):
        q = self._joints(q)
        with self._lock:
            if self.state != 'EXECUTING' or owner != self._owner or arm not in self._arms:
                raise RuntimeError('Mock command source is inhibited')
            if not self._ready():
                self._hold('FAULT_HOLD')
                raise RuntimeError('Active mock supervision expired')
            self._q[arm] = q
            self._observation = Observation(True, False, True)

    def end(self, owner):
        with self._lock:
            if owner != self._owner or self.state != 'EXECUTING' or not self._ready() or not self._observation.held:
                raise RuntimeError('Fresh confirmed end hold and current mock owner required')
            self._hold('IDLE')

    def tick(self):
        with self._lock:
            if self.state == 'EXECUTING' and not self._ready():
                self._hold('FAULT_HOLD')
            return self.state

    def owner_lost(self, owner):
        with self._lock:
            if owner is not None and owner == self._owner:
                self._hold('FAULT_HOLD')

    def reset_unloaded(self):
        with self._lock:
            if self.state not in ('CONTACT_HOLD','FAULT_HOLD') or not self._ready() or not self._observation.held:
                raise RuntimeError('Fresh stationary unloaded mock recovery required')
            self._hold('IDLE')

    def positions(self):
        with self._lock:
            return {r:q.tolist() for r,q in self._q.items()}

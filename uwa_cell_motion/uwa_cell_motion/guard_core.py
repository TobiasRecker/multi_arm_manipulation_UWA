"""Pure state machine: pair faults latch until an explicit stationary reset."""
import numpy as np
from .common import PAIRS


class GuardState:
    def __init__(self, cfg):
        self.cfg = cfg
        self.latched = set()
        self.reset_sequence = 0
        self.records = {}
        self.history = {}
        self.last_stamp = {}
        self.last_source_advance = {}
        self.last_faults = []
        self.causes = []
        self.external_faults = []

    def receive(self, rid, positions, velocities, source_stamp, now):
        q, v = np.asarray(positions, float), np.asarray(velocities, float)
        if q.ndim != 1 or v.shape != q.shape or not np.isfinite([q, v]).all() or not np.isfinite(source_stamp):
            return False
        if source_stamp > self.last_stamp.get(rid, -np.inf):
            self.last_source_advance[rid] = now
        elif source_stamp < self.last_stamp.get(rid, -np.inf):
            self.latched.add(rid)  # clock reset invalidates trajectories
        self.last_stamp[rid] = source_stamp
        self.records[rid] = dict(q=q, v=v, received=now, stamp=source_stamp)
        history = self.history.setdefault(rid, [])
        history.append((now, q.copy(), v.copy()))
        self.history[rid] = [r for r in history if r[0] >= now-max(1., 2*self.cfg['standstill_window_s'])]
        return True

    def fresh(self, rid, now, source_now):
        r = self.records.get(rid)
        limit = self.cfg['state_timeout_s']
        return bool(r and 0 <= now-r['received'] <= limit and
                    0 <= now-self.last_source_advance.get(rid, -np.inf) <= limit and
                    -.02 <= source_now-r['stamp'] <= limit)

    def stationary(self, rid, now):
        window = self.cfg['standstill_window_s']
        h = [r for r in self.history.get(rid, []) if r[0] >= now-window-.05]
        if len(h) < 3 or h[-1][0]-h[0][0] < window*.8:
            return False
        qs, vs = np.asarray([r[1] for r in h]), np.asarray([r[2] for r in h])
        return bool(np.max(abs(vs)) <= self.cfg['standstill_velocity_rad_s'] and
                    np.max(np.ptp(qs, axis=0)) <= self.cfg['standstill_velocity_rad_s']*window)

    def evaluate(self, pairs, now, source_now):
        faults = list(self.external_faults)
        for rid,record in self.records.items():
            if np.max(abs(record['v']))>self.cfg['velocity_limit_rad_s']*1.05:
                faults.append(dict(arms=[rid],reason='SPEED LIMIT'))
        for a, b in PAIRS:
            if not self.fresh(a, now, source_now) or not self.fresh(b, now, source_now):
                faults.append(dict(arms=[a, b], reason='STATE STALE'))
        for pair in pairs:
            if not np.isfinite([pair['clearance_m'], pair['threshold_m']]).all() or pair['clearance_m'] <= pair['threshold_m']:
                faults.append(dict(arms=pair['arms'], reason='DISTANCE'))
        self.last_faults = faults
        for fault in faults:
            if not any(c['arms']==fault['arms'] and c['reason']==fault['reason'] for c in self.causes):
                self.causes.append(dict(fault,source_time_s=source_now))
            self.latched.update(fault['arms'])
        stopped = all(self.stationary(rid, now) and self.fresh(rid,now,source_now) for rid in self.latched)
        state = 'STATE STALE' if any(f['reason']=='STATE STALE' for f in faults) else (
            'STOPPED' if stopped and self.latched else 'STOPPING' if self.latched else 'CLEAR')
        return dict(state=state, blocked_arms=sorted(self.latched), faults=faults,latched_causes=list(self.causes),
                    standstill_confirmed=bool(self.latched and stopped), reset_sequence=self.reset_sequence)

    def reset(self, pairs, now, source_now):
        self.evaluate(pairs, now, source_now)
        if self.last_faults or any(not self.stationary(r, now) for r in self.records):
            return False, 'Reset refused: fresh clear geometry and confirmed standstill required'
        if any(p['clearance_m'] <= p['threshold_m']+self.cfg['reset_hysteresis_m'] for p in pairs):
            return False, 'Reset refused: clearance hysteresis not reached'
        self.latched.clear(); self.causes.clear(); self.reset_sequence += 1
        return True, 'Reset accepted; motion remains inactive. Submit a newly checked plan explicitly.'

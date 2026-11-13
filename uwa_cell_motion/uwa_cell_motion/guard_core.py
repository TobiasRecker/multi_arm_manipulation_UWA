"""Pure state machine: pair faults latch until an explicit stationary reset."""
import numpy as np
from .common import PAIRS


class GuardState:
    def __init__(self, cfg):
        self.cfg = cfg
        self.latched = set()
        self.reset_sequence = 0
        self.reset_arms = []
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
            affected=sorted({r for pair in PAIRS if rid in pair for r in pair})
            self.latched.update(affected)
            self.causes.append(dict(arms=affected,reason='CLOCK RESET',source_time_s=source_stamp))
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
                detail={}
                for rid in (a,b):
                    record=self.records.get(rid)
                    detail[rid]=None if record is None else dict(receive_age_s=now-record['received'],
                        source_age_s=source_now-record['stamp'],source_advance_age_s=now-self.last_source_advance.get(rid,now))
                faults.append(dict(arms=[a, b], reason='STATE STALE',state_detail=detail))
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
                    standstill_confirmed=bool(self.latched and stopped), reset_sequence=self.reset_sequence,reset_arms=list(self.reset_arms))

    def reset(self, pairs, now, source_now):
        self.evaluate(pairs, now, source_now)
        eligible=[]
        faulted={r for fault in self.last_faults for r in fault['arms']}
        for rid in {r for pair in PAIRS for r in pair}:
            neighbors={r for pair in PAIRS if rid in pair for r in pair}
            relevant=[p for p in pairs if rid in p['arms']]
            if (rid not in faulted and all(self.fresh(r,now,source_now) for r in neighbors)
                    and self.stationary(rid,now) and len(relevant)==2 and
                    all(p['clearance_m']>p['threshold_m']+self.cfg['reset_hysteresis_m'] for p in relevant)):
                eligible.append(rid)
        if not eligible:return False,'Reset refused: fresh clear geometry, hysteresis and confirmed standstill required'
        self.latched.difference_update(eligible);self.reset_arms=sorted(eligible);self.reset_sequence+=1
        self.causes=[c for c in self.causes if set(c['arms'])&self.latched]
        return True,'Reset accepted for '+', '.join(self.reset_arms)+'; motion remains inactive. Remaining holds: '+(', '.join(sorted(self.latched)) or 'none')

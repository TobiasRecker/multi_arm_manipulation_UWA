"""Independent heartbeat latch; a guard restart never implicitly releases it."""
import math
from .common import ROBOT_IDS


SUPERVISOR_PERIOD_S=.02


def expired_pair_leases(decision,now,cfg):
    """Do not spend a close pair's distance reserve on the full heartbeat timeout.

    A healthy decision already reserves one geometric check interval plus
    switching/braking. Excess clearance buys additional supervision time.
    Same-host monotonic evaluation time includes computation/transport delay.
    The supervisor period is deducted so its next tick fits that reserve.
    Assumes the normal Gazebo real-time factor <=1, as the stop budget does.
    """
    try:
        evaluated=float(decision['evaluated_monotonic_s'])
        if not math.isfinite(evaluated) or evaluated>now+.001:raise ValueError()
        expired=set()
        for pair in decision['pairs']:
            speed=float(pair['relative_speed_bound_m_s']);gap=float(pair['clearance_m']);threshold=float(pair['threshold_m'])
            if not all(map(math.isfinite,(speed,gap,threshold))) or speed<0:raise ValueError()
            lease=cfg['heartbeat_timeout_s']
            if speed>0:
                lease=min(lease,max(0.,1/cfg['rate_hz']-SUPERVISOR_PERIOD_S+(gap-threshold)/speed))
            if now-evaluated>=lease:expired.update(pair['arms'])
        return expired
    except (KeyError,TypeError,ValueError):return set(ROBOT_IDS)


class Interlock:
    def __init__(self, timeout):
        self.timeout=timeout; self.blocked=set(ROBOT_IDS)
        self.last=None; self.received=-float('inf'); self.pending_reset=None
        self.reason='STARTUP: explicit reset required'

    def receive(self, decision, now):
        if (set(decision.get('blocked_arms',[]))-set(ROBOT_IDS) or
                not isinstance(decision.get('sequence'),int) or not decision.get('instance')):
            return False
        previous=self.last
        if previous and decision['instance']==previous['instance'] and decision['sequence']<=previous['sequence']:
            return False
        if previous and previous['instance']!=decision['instance']:
            self.blocked.update(ROBOT_IDS); self.pending_reset=None
            self.reason='GUARD RESTART: explicit reset required'
        self.last=decision; self.received=now
        self.blocked.update(decision['blocked_arms'])
        if (self.pending_reset and self.pending_reset[0]==decision['instance'] and
                decision['reset_sequence']>self.pending_reset[1]):
            released=decision.get('reset_arms',list(ROBOT_IDS) if not decision['blocked_arms'] else [])
            self.blocked.difference_update(set(released)-set(decision['blocked_arms']))
            self.pending_reset=None; self.reason='CLEAR' if not self.blocked else 'PARTIAL RESET: remaining holds latched'
        if decision['blocked_arms']:self.reason=decision['state']
        return True

    def tick(self, now):
        if now-self.received>self.timeout:
            self.blocked.update(ROBOT_IDS); self.pending_reset=None; self.reason='GUARD LOST'
        return set(self.blocked)

    def request_reset(self, now):
        if self.last is None or now-self.received>self.timeout:
            return False
        self.pending_reset=(self.last['instance'],self.last['reset_sequence'])
        return True

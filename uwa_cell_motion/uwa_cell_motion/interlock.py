"""Independent heartbeat latch; a guard restart never implicitly releases it."""
from .common import ROBOT_IDS


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
                decision['reset_sequence']>self.pending_reset[1] and not decision['blocked_arms']):
            self.blocked.clear(); self.pending_reset=None; self.reason='CLEAR'
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

"""Do not turn one missing window after a long quiet hold into an instant STOP."""
import numpy as np
from uwa_cell_motion.hardware_ports import standstill_deadline_expired
from uwa_cell_motion.guard_core import GuardState


def due(since,now,*,quiet=False,fresh=True,blocked=True,stamp=None):
    return standstill_deadline_expired(since,'right_front',now,blocked=blocked,
        guard_fresh=fresh,reported_stationary=quiet,quiet_stamp=now if stamp is None else stamp,latency=1.)


def test_initial_stop_keeps_the_same_one_second_deadline():
    since={}
    assert not due(since,10.) and not due(since,10.999)
    assert due(since,11.001)


def test_brief_missing_quiet_window_after_minutes_of_verified_hold_is_not_instant_stop():
    since={}
    assert not due(since,0.)
    assert not due(since,.5,quiet=True)
    assert not due(since,600.,quiet=True)
    assert not due(since,600.02)
    assert not due(since,600.1,quiet=True)
    assert not due(since,601.)
    assert due(since,601.101)


def test_stale_quiet_packet_never_keeps_renewing_the_deadline():
    since={}
    assert not due(since,10.,quiet=True)
    assert not due(since,10.8,quiet=True,fresh=False)
    assert due(since,11.01,quiet=True,fresh=False)


def test_repeated_same_quiet_packet_uses_its_evaluation_time_not_receipt_time():
    since={}
    assert not due(since,10.,quiet=True,stamp=10.)
    assert not due(since,10.2,quiet=True,stamp=10.)
    assert since['right_front']==10.
    assert due(since,11.01,quiet=True,stamp=10.)


def test_unblock_discards_old_deadline_and_next_stop_is_a_new_episode():
    since={}
    due(since,0.);assert not due(since,.2,blocked=False) and not since
    assert not due(since,20.) and due(since,21.01)


def state():
    return GuardState(dict(standstill_window_s=.5,standstill_velocity_rad_s=.001,velocity_limit_rad_s=.003))


def test_stationarity_diagnostics_distinguish_short_window_and_actual_speed():
    guard=state();guard.receive('right_front',[0.]*6,[0.]*6,0.,0.)
    assert not guard.stationary('right_front',0.)
    assert guard.stationarity_evidence('right_front',0.)['reason']=='INSUFFICIENT_WINDOW'
    for now in np.linspace(.1,.5,5):guard.receive('right_front',[0.]*6,[0.]*6,float(now),float(now))
    assert guard.stationary('right_front',.5)
    guard.receive('right_front',[0.]*6,[.002]*6,.51,.51)
    evidence=guard.stationarity_evidence('right_front',.51)
    assert not evidence['confirmed'] and evidence['reason']=='VELOCITY'
    assert max(evidence['velocity_peaks_rad_s'])==.002


def test_position_span_failure_remains_rejected_with_zero_reported_speed():
    guard=state()
    for now in np.linspace(0,.5,6):guard.receive('right_front',[now*.002]*6,[0.]*6,float(now),float(now))
    evidence=guard.stationarity_evidence('right_front',.5)
    assert not guard.stationary('right_front',.5) and evidence['reason']=='POSITION_SPAN'
    assert max(evidence['position_spans_rad'])==.001

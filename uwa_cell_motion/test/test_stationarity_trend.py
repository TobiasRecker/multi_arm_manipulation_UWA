"""Explicit candidate: stable encoders versus actual drift, default unchanged."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from uwa_cell_motion.common import config
from uwa_cell_motion.guard_core import GuardState


def sample(cfg,drift=0.,spike=.00101570075,jump=0.):
    core=GuardState(cfg)
    for i,t in enumerate(np.linspace(0,.5,11)):
        q=np.full(6,drift*t+2e-5*np.sin(i));v=np.zeros(6)
        if i==5:v[0]=spike
        if i==10:q[0]+=jump
        core.receive('right_rear',q,v,t,t)
    return core


def test_candidate_handles_isolated_estimator_peak_without_widening_span():
    root=Path(__file__).resolve().parents[1]/'config'
    original=config(root/'hardware_carton_supported.yaml');candidate=config(root/'hardware_carton_supported_trend_candidate.yaml')
    assert not sample(original).stationary('right_rear',.5)
    core=sample(candidate);e=core.stationarity_evidence('right_rear',.5)
    assert e['confirmed']
    assert e['position_span_limits_rad']==[.0005]*6
    assert candidate['velocity_limit_rad_s']==original['velocity_limit_rad_s']==.1
    assert not sample(candidate,drift=.002,spike=0.).stationary('right_rear',.5)
    assert not sample(candidate,jump=.001).stationary('right_rear',.5)


def test_candidate_does_not_hide_raw_speed_limit_or_stale_data():
    cfg=config(Path(__file__).resolve().parents[1]/'config/hardware_carton_supported_trend_candidate.yaml')
    core=sample(cfg,spike=.2);status=core.evaluate([],.5,.5)
    # Last sample is deliberately oversized: normal instantaneous speed guard
    # remains independent of the stationarity estimator.
    core.receive('right_rear',np.zeros(6),np.full(6,.2),.55,.55)
    assert any(f['reason']=='SPEED LIMIT'for f in core.evaluate([],.55,.55)['faults'])
    assert not core.fresh('right_rear',1.,1.)

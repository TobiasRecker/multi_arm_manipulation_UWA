import numpy as np
import pytest
from uwa_cell_motion.state_alignment import aligned_driver


def test_delayed_native_sample_matches_fast_driver_at_same_time():
    rows=[(float(t),[.1*t]*6) for t in np.linspace(0,1,501)]
    target=.83;native=np.full(6,.1*target)
    assert max(abs(np.array(rows[-1][1])-native))>.005
    result=aligned_driver(rows,target,np.full(6,.132),.2)
    np.testing.assert_allclose(result['q'],native,atol=1e-12)
    assert max(result['uncertainty_rad'])<.001


def test_frozen_positions_with_advancing_driver_timestamps_remain_detectable():
    rows=[(float(t),[0.]*6) for t in np.linspace(0,1,501)]
    result=aligned_driver(rows,.83,np.full(6,.132),.2)
    assert max(abs(np.array(result['q'])-.083)+result['uncertainty_rad'])>.005


@pytest.mark.parametrize('rows,target,gap',[
    ([(1.,[0]*6)],1.,.2), ([(1.,[0]*6),(1.,[0]*6)],1.,.2),
    ([(1.,[0]*6),(2.,[0]*6)],.9,.2), ([(1.,[0]*6),(2.,[0]*6)],2.1,.2),
    ([(1.,[0]*6),(2.,[0]*6)],1.5,.2)])
def test_missing_nonmonotonic_unbracketed_or_wide_history_fails(rows,target,gap):
    with pytest.raises(ValueError):aligned_driver(rows,target,np.ones(6)*.1,gap)


def test_interpolation_uncertainty_spends_rather_than_enlarges_tolerance():
    result=aligned_driver([(1.,[0.]*6),(1.1,[.01]*6)],1.05,np.full(6,.2),.2)
    np.testing.assert_allclose(result['uncertainty_rad'],.01)
    assert max(result['uncertainty_rad'])>.005

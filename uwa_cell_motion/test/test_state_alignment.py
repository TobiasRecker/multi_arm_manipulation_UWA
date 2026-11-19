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


def test_preemption_between_clock_reads_is_not_a_clock_jump():
    from uwa_cell_motion.state_alignment import host_clock_sample
    monotonic=iter([0.,.03,.031,.031002]);wall=iter([1000.03,1000.031001])
    # The former wall()-before formula mistakes this 30ms preemption for a
    # wall-clock step. Discard that uncertain pair, then use the bounded one.
    result=host_clock_sample(monotonic=lambda:next(monotonic),wall=lambda:next(wall))
    assert result['offset_s']==pytest.approx(1000.,abs=1e-9)
    assert result['uncertainty_s']<=.0000011


def test_unsampled_host_clock_cannot_refresh_driver_data():
    from uwa_cell_motion.state_alignment import host_clock_sample
    values=iter([0.,.03,1.,1.03,2.,2.03])
    with pytest.raises(ValueError,match='bounded time'):
        host_clock_sample(monotonic=lambda:next(values),wall=lambda:1000.)


def test_real_wall_clock_step_remains_visible_with_bounded_sampling():
    from uwa_cell_motion.state_alignment import host_clock_sample
    a=iter([0.,.000002]);b=iter([1.,1.000002])
    before=host_clock_sample(monotonic=lambda:next(a),wall=lambda:1000.000001)
    after=host_clock_sample(monotonic=lambda:next(b),wall=lambda:1001.030001)
    assert after['offset_s']-before['offset_s']==pytest.approx(.03,abs=1e-9)


def test_clock_sampling_error_spends_spatial_tolerance():
    result=aligned_driver([(1.,[0.]*6,.0001),(1.002,[.0002]*6,.0001)],1.001,np.ones(6)*.1,.2)
    np.testing.assert_allclose(result['uncertainty_rad'],.00012)

"""Recorded planning quiet evidence is identical to the selected guard profile."""
import copy
from pathlib import Path
from uwa_cell_motion.common import config
from uwa_cell_tasks.hardware_preparation import operating_stationarity
CFG=Path(__file__).resolve().parents[2]/'uwa_cell_motion/config/hardware_carton_supported_trend.yaml'


def observation(drift=0.,speed=.049):
    return dict(arms={'left_front':dict(observed=True,stationary_observed=False,samples=[dict(device_timestamp_s=10+i*.05,robot_mode=7,safety_mode=1,actual_q=[drift*i/19]*6,actual_qd=[speed]*6)for i in range(20)])},grippers={})


def test_same_position_window_accepts_selected_trend_and_retains_raw_peak():
    raw=observation();changed=operating_stationarity(copy.deepcopy(raw),config(CFG))['arms']['left_front']
    assert changed['stationary_observed'] and not changed['peak_stationary_observed']
    assert changed['samples']==raw['arms']['left_front']['samples']
    assert max(changed['stationarity_evidence']['velocity_peaks_rad_s'])==.049
    peak=config(CFG);peak['standstill_velocity_measure']='peak'
    assert not operating_stationarity(observation(),peak)['arms']['left_front']['stationary_observed']


def test_real_drift_short_window_and_operating_speed_excess_are_rejected():
    cfg=config(CFG)
    assert not operating_stationarity(observation(drift=.003),cfg)['arms']['left_front']['stationary_observed']
    assert not operating_stationarity(observation(speed=.11),cfg)['arms']['left_front']['stationary_observed']
    short=observation();short['arms']['left_front']['samples']=short['arms']['left_front']['samples'][:3]
    assert not operating_stationarity(short,cfg)['arms']['left_front']['stationary_observed']


def test_power_off_cached_positions_are_not_a_valid_planning_start():
    data=observation()
    for row in data['arms']['left_front']['samples']:row['robot_mode']=3
    result=operating_stationarity(data,config(CFG))['arms']['left_front']
    assert result['stationarity_evidence']['confirmed']
    assert not result['stationary_observed']
    assert not result['stationarity_evidence']['native_state_suitable_for_planning']

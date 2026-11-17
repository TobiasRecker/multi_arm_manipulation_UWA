#!/usr/bin/env python3
"""Offline received-sample stop metrics; never equate hold confirmation with braking."""
import argparse,json,math
from pathlib import Path
import numpy as np


def analyze(record):
    rows=record['native_records'];t0=record['stop_sent_monotonic']
    times=np.array([r['received'] for r in rows]);device=np.array([r['device_stamp'] for r in rows])
    if len(rows)<10 or not np.isfinite(times).all() or not np.isfinite(device).all() or np.any(np.diff(times)<=0) or np.any(np.diff(device)<=0):
        raise ValueError('Finite advancing native samples required')
    q=np.array([r['q'] for r in rows]);v=np.abs(np.array([r['v'] for r in rows]))
    if q.shape!=(len(rows),6) or v.shape!=q.shape or not np.isfinite(q).all() or not np.isfinite(v).all():
        raise ValueError('Finite measured6joint vectors required')
    before=(times>=t0-.12)&(times<=t0)
    if sum(before)<3:raise ValueError('Insufficient pre-request motion samples')
    speed=float(np.median(v[before,5]))
    if speed<.0012:raise ValueError('No confirmed pre-request q6 motion')
    def sustained(mask):
        for i in np.flatnonzero((times>=t0)&mask):
            end=int(np.searchsorted(times,times[i]+.02))
            if end<len(times) and np.all(mask[i:end+1]):return int(i)
        return None
    slow=sustained(v[:,5]<=.8*speed);still=sustained(np.max(v,axis=1)<=.0002)
    metrics=dict(pre_request_q6_speed_rad_s=speed,device_interval_max_s=float(max(np.diff(device))),
        receive_interval_max_s=float(max(np.diff(times))),
        request_to_observed_20pct_speed_drop_s=None if slow is None else float(times[slow]-t0),
        request_to_observed_low_speed_s=None if still is None else float(times[still]-t0),
        low_speed_threshold_rad_s=.0002,low_speed_observation_window_s=.02,
        confirmed_hold_window_delay_s=record.get('confirmation_delay_s'),
        post_request_q6_travel_rad=None if still is None else float(abs(q[still,5]-np.interp(t0,times,q[:,5]))))
    return dict(kind='right_front_received_stop_observation',metrics=metrics,
        execution_passed=bool(record.get('success')),
        interpretation='Receipt-time observations include transport/buffering.20percent-drop is an observable threshold, not true braking onset. Post-request travel includes reaction and braking. Hold-window delay is separate.',
        hardware_braking_limit_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('record',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=analyze(json.loads(a.record.read_text()))
    with a.output.open('x') as f:f.write(json.dumps(result,indent=2)+chr(10))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

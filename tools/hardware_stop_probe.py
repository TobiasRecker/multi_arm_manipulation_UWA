#!/usr/bin/env python3
"""Explicit, unloaded right-front q6 probe using the normal checked runner.

Requires an already armed/reset guard and an operator at the hardware stop.
Requests the existing per-arm supervisor stop after independent RTDE confirms
motion. Leaves the stop latched. No power, play, gripper or reset operations.
"""
import argparse
import json
from pathlib import Path
import tempfile
import threading
import time

import numpy as np
from std_srvs.srv import Trigger
from uwa_cell_motion.common import dump, joint_names
from uwa_cell_motion.execution import _follow, motion_context
from uwa_cell_motion.hardware_execution import HardwareClient
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import MotionOutputReader, require_domain


def quiet_window(rows):
    """Tighter observation criterion than the operational standstill detector."""
    if len(rows) < 9 or rows[-1]['received']-rows[0]['received'] < .45:
        return False
    q, v = np.asarray([r['q'] for r in rows]), np.asarray([r['v'] for r in rows])
    # Real stationary UR encoder positions show about0.1mrad peak-to-peak
    # noise. Bound its amplitude separately from a sustained position trend;
    # neither bound changes the operational guard's standstill thresholds.
    times=np.asarray([r['received'] for r in rows]);times-=times.mean()
    slope=times @ (q-q.mean(axis=0)) / np.dot(times,times)
    return bool(np.max(abs(v)) <= .0002 and np.max(np.ptp(q, axis=0)) <= .0002
                and np.max(abs(slope)) <= .0002)


class Observer:
    def __init__(self, host):
        self.reader=MotionOutputReader(host)
        self.rows=[];self.error=None;self.lock=threading.Lock();self.done=threading.Event()
        self.worker=threading.Thread(target=self.run, daemon=True);self.worker.start()

    def run(self):
        previous=None
        try:
            while not self.done.is_set():
                stamp,q,v,status=self.reader.sample();now=time.monotonic()
                if previous is not None and stamp <= previous:
                    raise RuntimeError('Independent RTDE device time did not advance')
                previous=stamp
                with self.lock:
                    self.rows.append(dict(device_stamp=stamp,received=now,q=q,v=v,status=status))
        except Exception as error:
            if not self.done.is_set():self.error=str(error)

    def snapshot(self):
        with self.lock:return list(self.rows)

    def close(self):
        self.done.set();self.worker.join(timeout=.5);self.reader.close()


class Probe(HardwareClient):
    def __init__(self, problem, observer):
        super().__init__(problem, 'hardware', ['right_front'])
        self.observer=observer;self.probe_enabled=False;self.stop_future=None
        self.stop_sent=None;self.trace=[];self.last_sequence=None
        self.baseline=None

    def spin_once(self, timeout_sec=.01):
        super().spin_once(timeout_sec=timeout_sec)
        if self.guard and self.guard.get('sequence') != self.last_sequence:
            self.last_sequence=self.guard.get('sequence')
            self.trace.append(dict(received=time.monotonic(),guard=self.guard,supervisor=self.supervisor))
        if not self.probe_enabled:return
        rows=self.observer.snapshot();now=time.monotonic()
        if self.observer.error or not rows or now-rows[-1]['received'] > .2:
            raise RuntimeError('Independent RTDE observer unavailable: '+str(self.observer.error))
        if self.stop_future is not None or not self.pending:return
        recent=rows[-3:]
        if (len(recent)==3 and recent[-1]['received']-recent[0]['received'] >= .08
                and all(abs(r['v'][5]) >= .0012 for r in recent)
                and abs(recent[-1]['q'][5]-self.baseline[5]) >= .0005):
            client=self.stop_clients['right_front']
            if not client.service_is_ready():raise RuntimeError('Supervisor stop service unavailable')
            self.stop_sent=now
            self.stop_future=client.call_async(Trigger.Request())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute',action='store_true',required=True)
    args=parser.parse_args();require_domain('hardware')
    if args.output.exists():raise ValueError('Output exists; use a unique test record')
    plan=json.loads(args.plan.read_text());rid='right_front';names=joint_names(rid)
    if (not plan.get('success') or not plan.get('hardware_plan') or plan.get('execution_mode') != 'hardware'
            or plan['request']['selected'] != [rid] or plan['config']['velocity_limit_rad_s'] > .003
            or plan['config']['acceleration_limit_rad_s2'] > .006):
        raise ValueError('Successful slow single right-front hardware plan required')
    delta=np.asarray(plan['request']['goals'][rid])-[plan['request']['start'][j] for j in names]
    if np.max(abs(delta[:5])) > 1e-10 or not 0 < abs(delta[5]) <= .03000001:
        raise ValueError('Only a checked q6 displacement of at most0.03rad is allowed')
    result=dict(success=False,kind='intentional_unloaded_software_stop_probe',
                phase_count=0,guard_stops=0,record_path=str(args.output),stage='CONNECT',
                qualification='RTDE receive-time observation; not hardware E-stop or certified braking accuracy')
    with motion_context(), tempfile.TemporaryDirectory(prefix='uwa-stop-probe-') as directory:
        problem=HardwareProblem(directory,plan['config'],plan['inventory'],plan.get('layout_path'))
        if problem.binding != plan['hardware_binding'] or problem.spheres.geometry.assets != plan['mesh_sha256']:
            raise ValueError('Plan binding changed; replan')
        observer=Observer(problem.profiles[rid]['robot_ip'] if 'robot_ip' in problem.profiles[rid]
                          else problem.profiles[rid]['ip'])
        client=Probe(problem,observer)
        try:
            client.connect();client.health()
            if max(abs(client.positions[j]-plan['request']['start'][j]) for n in problem.names.values() for j in n) > .002:
                raise ValueError('Actual start changed; replan without automatic repositioning')
            if problem.time_parameterize(plan['request'],plan['trajectory']['waypoints']) != plan['trajectory']:
                raise ValueError('Timed plan changed')
            client.baseline=np.asarray([client.positions[j] for j in names])
            client.probe_enabled=True;result['stage']='EXECUTION'
            _follow(problem,client,plan,result)
            client.probe_enabled=False
            if client.stop_sent is None:raise RuntimeError('No confirmed moving-state stop was injected')
            result['stop_sent_monotonic']=client.stop_sent
            end=time.monotonic()+4.
            while time.monotonic() < end:
                client.spin_once(.01)
                rows=[r for r in observer.snapshot() if r['received'] >= client.stop_sent]
                window=[r for r in rows if r['received'] >= time.monotonic()-.55]
                held=client.supervisor.get('ports',{}).get(rid,{}).get('held',False)
                latched=rid in client.supervisor.get('blocked_arms',[])
                if held and latched and quiet_window(window):
                    result.update(success=True,standstill_confirmed=True,hold_confirmed=True,latch_confirmed=True,
                                  observation_window=window,
                                  confirmation_delay_s=time.monotonic()-client.stop_sent)
                    break
            if not result['success']:raise RuntimeError('Measured standstill/hold/latch not confirmed')
            result['stage']='STOP_CONFIRMED';result.pop('error',None)
        except BaseException as error:
            result['error']=str(error)
            now=time.monotonic()
            result['health_diagnostic']=dict(observed_monotonic=now,
                state_receive_age_s=now-client.state_received,
                state_record_arms=sorted(client.records),
                source_ages_s={r:now-v['source_stamp'] for r,v in client.records.items()},
                guard_age_s=now-client.guard_received,supervisor_age_s=now-client.supervisor_received)
        finally:
            client.probe_enabled=False
            if client.stop_sent is not None:result['stop_sent_monotonic']=client.stop_sent
            if client.owned and not result['success']:
                result['retained_stop']=client.stop(client.owned)
            observer.close();result['native_records']=observer.snapshot();result['observer_error']=observer.error
            result['trace']=client.trace;result['guard_status']=client.guard;result['supervisor_status']=client.supervisor
            if client.stop_future is not None:
                result['stop_service_ack']=bool(client.stop_future.done() and client.stop_future.result() is not None
                                                and client.stop_future.result().success)
            dump(args.output,result);client.destroy_node()
    print(json.dumps({k:v for k,v in result.items() if k not in ('native_records','trace','guard_status','supervisor_status','observation_window')},indent=2))
    if not result['success']:raise SystemExit(1)


if __name__ == '__main__':main()

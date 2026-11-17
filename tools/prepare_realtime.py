#!/usr/bin/env python3
"""Read-only host audit, ordinary-scheduler jitter baseline and passive ROS trace.

No kernel installation, priority change, robot publisher, service or action.
"""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import time


def stats(values):
    values=sorted(values)
    if not values:return dict(samples=0)
    def q(p):
        x=p*(len(values)-1);i=int(x);j=min(i+1,len(values)-1)
        return values[i]+(values[j]-values[i])*(x-i)
    return dict(samples=len(values),min=min(values),p50=q(.5),p99=q(.99),maximum=max(values))


def command(args):
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=30)
        return dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except (OSError,subprocess.TimeoutExpired) as e:return dict(error=str(e))


def read(path):
    try:return Path(path).read_text()
    except OSError:return None


def audit():
    release=platform.release()
    return dict(kind='read_only_realtime_readiness',kernel=release,
        os_release=read('/etc/os-release'),boot_id=read('/proc/sys/kernel/random/boot_id'),
        kernel_config='\n'.join(l for l in (read('/boot/config-'+release) or '').splitlines()
            if 'CONFIG_PREEMPT' in l or l.startswith('CONFIG_HZ=')),
        realtime_sysfs=read('/sys/kernel/realtime'),cpu_affinity=sorted(os.sched_getaffinity(0)),
        scheduler=os.sched_getscheduler(0),rtprio_limits=resource.getrlimit(resource.RLIMIT_RTPRIO),
        memlock_limits_bytes=resource.getrlimit(resource.RLIMIT_MEMLOCK),
        rt_runtime_us=read('/proc/sys/kernel/sched_rt_runtime_us'),
        rt_period_us=read('/proc/sys/kernel/sched_rt_period_us'),
        cyclictest=shutil.which('cyclictest'),
        packages=command(['apt-cache','policy','ubuntu-realtime','linux-realtime','rt-tests']),
        install_dry_run=command(['apt-get','-s','install','ubuntu-realtime','rt-tests']),
        interpretation='Current process/session limits; no configuration changed')


def jitter(seconds,period):
    # Absolute deadlines prevent cumulative sleep drift from hiding overruns.
    end=time.monotonic()+seconds;deadline=time.monotonic()+period;late=[];missed=0
    while deadline<end:
        time.sleep(max(0.,deadline-time.monotonic()))
        now=time.monotonic();delay=max(0.,now-deadline);late.append(delay*1e6)
        skipped=int(delay//period);missed+=skipped;deadline+=(skipped+1)*period
    return dict(kind='ordinary_python_scheduler_probe',period_us=period*1e6,
        duration_s=seconds,lateness_us=stats(late),missed_deadlines=missed,
        scheduler=os.sched_getscheduler(0),kernel=platform.release(),
        interpretation='Python/process wakeup observation, not cyclictest or a real-time bound')


def record(args):
    if os.environ.get('ROS_DOMAIN_ID')!=str(args.domain):
        raise ValueError('Source the intended environment first; ROS_DOMAIN_ID must match --domain')
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from std_msgs.msg import String
    from sensor_msgs.msg import JointState
    rclpy.init();node=rclpy.create_node('uwa_passive_reaction_trace')
    root=args.namespace.rstrip('/');last={};gaps={};evaluations=[];intervals=[];ages=[]
    with args.output.open('x') as stream:
        stream.write(json.dumps(dict(kind='trace_header',boot_id=read('/proc/sys/kernel/random/boot_id'),
            domain=args.domain,namespace=root,clock='host CLOCK_MONOTONIC',commands_sent=0))+'\n')
        def callback(topic,msg):
            now=time.monotonic()
            if topic in last:gaps.setdefault(topic,[]).append(1000*(now-last[topic]))
            last[topic]=now
            if isinstance(msg,String):
                value=json.loads(msg.data)
                if topic=='guard':
                    t=value.get('timing',{})
                    if t.get('evaluation_ms') is not None:evaluations.append(t['evaluation_ms'])
                    if t.get('interval_ms') is not None:intervals.append(t['interval_ms'])
                    ages.extend(1000*a for a in value.get('state_ages_s',{}).values())
            else:
                value=dict(names=list(msg.name),positions=list(msg.position),velocities=list(msg.velocity),
                    source_stamp_s=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9)
            stream.write(json.dumps(dict(topic=topic,receive_monotonic_s=now,value=value))+'\n')
        for label,topic in [('guard','collision_guard/decision'),('supervisor','collision_supervisor/status')]:
            node.create_subscription(String,root+'/'+topic,lambda m,k=label:callback(k,m),10)
        node.create_subscription(JointState,root+'/joint_states',lambda m:callback('joints',m),qos_profile_sensor_data)
        end=time.monotonic()+args.seconds
        try:
            while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.02)
        finally:
            node.destroy_node();rclpy.shutdown()
    return dict(kind='passive_reaction_trace_summary',commands_sent=0,
        receive_gaps_ms={k:stats(v) for k,v in gaps.items()},guard_evaluation_ms=stats(evaluations),
        guard_intervals_ms=stats(intervals),state_receive_ages_ms=stats(ages),
        interpretation='Reception/callback timing only; missing command/deceleration stages are NOT a braking measurement')



def reaction_chain(events):
    """Explicit correlated local timestamps, never inferred from receipt order."""
    stages=['state_received','guard_started','guard_finished','stop_dispatched',
            'deceleration_observed','standstill_observed']
    cases={}
    for e in events:cases.setdefault(e['trial_id'],[]).append(e)
    results={}
    for trial,rows in cases.items():
        if len({r['boot_id'] for r in rows})!=1 or any(r.get('clock')!='host_monotonic' for r in rows):
            raise ValueError('Different clocks/boots cannot be subtracted')
        by={r['stage']:r for r in rows}
        if len(by)!=len(rows) or set(by)!=set(stages):
            raise ValueError('Exactly one timestamp per chain stage required')
        times=[by[k]['time_s'] for k in stages]
        if not all(math.isfinite(t) for t in times) or any(b<a for a,b in zip(times,times[1:])):
            raise ValueError('Finite chronological stage timestamps required')
        results[trial]=dict(stage_intervals_ms={a+'__'+b:1000*(by[b]['time_s']-by[a]['time_s'])
            for a,b in zip(stages,stages[1:])},state_to_deceleration_ms=1000*(times[-2]-times[0]),
            state_to_standstill_ms=1000*(times[-1]-times[0]))
    if not results:raise ValueError('No correlated trial events')
    return dict(kind='correlated_reaction_chain',trials=results,
        interpretation='Observed timestamps only; standstill threshold/window and instrumentation must be documented by the experiment')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['audit','jitter','record','analyze'])
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=30.)
    p.add_argument('--period-ms',type=float,default=2.);p.add_argument('--domain',type=int,choices=[64,66,67],default=64)
    p.add_argument('--namespace',default='/uwa_cell');p.add_argument('--input',type=Path);a=p.parse_args()
    if not math.isfinite(a.seconds) or not .1<=a.seconds<=3600:p.error('seconds must be between0.1 and3600')
    if not math.isfinite(a.period_ms) or not .1<=a.period_ms<=1000:p.error('period-ms must be between0.1 and1000')
    if a.output.exists():p.error('Use a new output file')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.mode=='record':
        summary=a.output.with_suffix(a.output.suffix+'.summary.json')
        if summary.exists():p.error('Summary already exists')
        result=record(a);summary.write_text(json.dumps(result,indent=2)+'\n')
    else:
        if a.mode=='analyze':
            if a.input is None:p.error('analyze requires --input')
            result=reaction_chain([json.loads(line) for line in a.input.read_text().splitlines() if line.strip()])
        else:result=audit() if a.mode=='audit' else jitter(a.seconds,a.period_ms/1000)
        with a.output.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

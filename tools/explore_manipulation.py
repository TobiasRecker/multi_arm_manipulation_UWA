#!/usr/bin/env python3
"""Run a finite simulation speed ladder; agent image/plan reviews stay mandatory.

Each case gets a fresh world and immutable evidence. Run in the sourced cell
environment. This runner contains no hardware transport or automatic review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import yaml

from uwa_cell_motion.common import simulation_only
from uwa_cell_tasks.core import configuration,write_json,seal


def read(path):
    return json.loads(path.read_text())


def live_grasp_launches():
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:args=(path/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
        except (OSError,UnicodeError):continue
        if len(args)>4 and Path(args[1]).name=='ros2' and args[2:5]==['launch','uwa_cell_tasks','grasp.launch.py']:
            result.append(int(path.name))
    return result


def end_world(launch,run):
    state=read(run/'state.json')
    if state['state'] not in ('DONE','FAILED') or not state.get('stop',{}).get('confirmed'):
        raise RuntimeError('Own world retained: measured task stop is not confirmed')
    if state['state']=='DONE' and not state.get('group',{}).get('released'):
        raise RuntimeError('Own world retained: completed task has not released on support')
    # The exact Popen child is the only process signalled. ROS launch cleans its
    # own children; no process-name kill or signal to unrelated process groups.
    if launch.poll() is None:
        launch.send_signal(signal.SIGINT)
        launch.wait(timeout=30.)


def classify(state,validation,loads,diagnostic):
    text=json.dumps(diagnostic).lower()+' '+str(state.get('error','')).lower()
    if not validation['passed']:
        if 'stale' in text or 'expired' in text:return 'telemetry_or_lease_failure'
        if 'distance' in text or 'stopping reserve' in text:return 'configured_stopping_reserve'
        if 'speed limit' in text:return 'configured_speed_envelope'
        if 'slip' in text or 'rigid' in text:return 'grasp_rigidity_failure'
        return 'task_failure_inspect_raw_evidence'
    if not loads['coverage_complete']:return 'incomplete_force_measurement'
    if any(p['maximum_mean_load_upper_bound_n']>loads['pad_load_reference_n'] for p in loads['pads'].values()):
        return 'user_load_reference_exceeded_not_proven_material_damage'
    return 'observed_simulation_pass'


def case(root,cfg,reference,index,timeout):
    directory=root/f'case{index:02d}';directory.mkdir()
    scene=directory/'scene';run=directory/'run';profile=directory/'profile.yaml'
    profile.write_text(yaml.safe_dump(cfg,sort_keys=False))
    tools=Path(__file__).resolve().parent
    def checked(args,log):
        with (directory/log).open('w') as output:
            subprocess.run(args,stdout=output,stderr=subprocess.STDOUT,check=True)
    checked(['ros2','run','uwa_cell_tasks','cell_task','prepare','--config',str(profile),'--output',str(scene)],'prepare.log')
    logs=[];launch=recorder=runner=None
    def start(args,name):
        output=(directory/name).open('w');logs.append(output)
        return subprocess.Popen(args,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        launch=start(['ros2','launch','uwa_cell_tasks','grasp.launch.py','scene:='+str(scene)],'launch.log')
        recorder=start([sys.executable,str(tools/'trace_manipulation.py'),str(run),'--prepare','--timeout',str(timeout+90)],'trace.log')
        deadline=time.monotonic()+100.
        while True:
            if launch.poll() is not None:raise RuntimeError('Own simulation startup failed')
            with (directory/'cpu.log').open('w') as output:
                ready=subprocess.run([sys.executable,str(tools/'configure_manipulation_cpu.py'),'--scene',str(scene)],
                    stdout=output,stderr=subprocess.STDOUT).returncode==0
            if ready and (run/'force-trace.jsonl').exists() and (run/'evaluation-trace.jsonl').exists():break
            if time.monotonic()>deadline:raise TimeoutError('Own controllers/recorder not ready')
            time.sleep(1.)
        time.sleep(10.)  # DDS discovery before arming, never during motion.
        runner=start(['taskset','-c','6-11','ros2','run','uwa_cell_tasks','cell_task','run',
            '--scene',str(scene),'--output',str(run),'--reference',str(reference)],'runner.log')
        write_json(directory/'processes.json',dict(launch=launch.pid,runner=runner.pid,recorder=recorder.pid))
        print('CASE RUNNING; REVIEW FILE: '+str(run/'review.json'),flush=True)
        deadline=time.monotonic()+timeout;last_review=None
        while runner.poll() is None:
            if (run/'review.json').exists():
                review=read(run/'review.json');sha=review.get('sha256')
                if sha!=last_review:
                    print('AGENT REVIEW REQUIRED: '+str(run),flush=True);last_review=sha
            if time.monotonic()>deadline:
                (run/'STOP').write_text('EXPERIMENT TIMEOUT: STOP REQUESTED\n')
                runner.wait(timeout=15.);break
            time.sleep(.2)
        recorder.wait(timeout=10.)
        state=read(run/'state.json')
        end_world(launch,run)
        checked([sys.executable,str(tools/'validate_manipulation.py'),'--scene',str(scene),str(run)],'validation.log')
        # Incomplete force coverage is retained as a failed measurement, not
        # hidden by a subprocess exception or accepted as a successful case.
        with (directory/'loads.log').open('w') as output:
            subprocess.run([sys.executable,str(tools/'analyze_manipulation_loads.py'),str(run),'--scene',str(scene),
                '--output',str(run/'load-summary.json')],stdout=output,stderr=subprocess.STDOUT)
        validation=read(run/'validation-report.json');loads=read(run/'load-summary.json')
        below=bool(loads['pads']) and all(p['maximum_mean_load_upper_bound_n']<=cfg['pad_load_reference_n'] for p in loads['pads'].values())
        diagnostic=read(run/'stop-diagnostic.json') if (run/'stop-diagnostic.json').exists() else {}
        phase_times={};previous=None
        for line in (run/'evaluation-trace.jsonl').open():
            row=json.loads(line)
            if previous and row['phase']==previous['phase']:
                phase=row['phase'];phase_times[phase]=phase_times.get(phase,0.)+row['elapsed_wall_s']-previous['elapsed_wall_s']
            previous=row
        return dict(directory=str(directory),object_speed_m_s=cfg['max_object_speed_m_s'],
            task_passed=validation['passed'],force_coverage_complete=loads['coverage_complete'],
            per_jaw_10ms_mean_below_user_reference=below,
            accepted=validation['passed'] and loads['coverage_complete'] and below,
            classification=classify(state,validation,loads,diagnostic),
            sampled_phase_wall_durations_s=phase_times,
            error=state.get('error'),scene_sha256=read(scene/'scene.json')['sha256'],
            validation_sha256=validation['sha256'],loads_sha256=loads['sha256'])
    finally:
        if runner is not None and runner.poll() is None:
            (run/'STOP').write_text('EXPERIMENT DRIVER EXIT: STOP REQUESTED\n')
            try:runner.wait(timeout=15.)
            except subprocess.TimeoutExpired:pass
        if launch is not None and launch.poll() is None:
            if runner is None:
                # No recipe was ever launched; no ownership or motion exists.
                launch.send_signal(signal.SIGINT);launch.wait(timeout=30.)
            else:end_world(launch,run)  # Retain world if stop unconfirmed.
        if recorder is not None and recorder.poll() is None:
            recorder.send_signal(signal.SIGINT);recorder.wait(timeout=10.)
        for output in logs:output.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--object-speeds',type=float,nargs='+',required=True)
    p.add_argument('--repeats',type=int,default=2);p.add_argument('--case-timeout',type=float,default=1500.)
    args=p.parse_args();simulation_only()
    if live_grasp_launches():p.error('An own grasp world is already running; finish it first')
    cfg=configuration(args.config)
    if not cfg['exploration_mode'] or not cfg['force_observation']:p.error('Explicit instrumented exploration profile required')
    if not 1<=args.repeats<=5 or not 1<=len(args.object_speeds)<=8 or any(not 0<s<=.1 for s in args.object_speeds):
        p.error('Finite ladder:1–8 speeds in(0,0.1]m/s,1–5 repeats')
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    result=dict(kind='finite_simulation_speed_ladder',complete=False,cases=[],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        interpretation='Observed cases only; no monotonic boundary, material damage model or hardware qualification')
    try:
        for speed in args.object_speeds:
            for repeat in range(args.repeats):
                entry=case(root,dict(cfg,max_object_speed_m_s=speed),args.reference.resolve(),len(result['cases']),args.case_timeout)
                entry['repeat']=repeat;result['cases'].append(entry)
                write_json(root/'result.json',seal(result))
        result['complete']=True
    except BaseException as error:
        result['error']=str(error);raise
    finally:write_json(root/'result.json',seal(result))
    print('EXPERIMENT LADDER FINISHED: '+str(root/'result.json'),flush=True)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Timed supported-grasp workflow. Explicit execution; stop for agent image review."""
import argparse,json,os,subprocess,sys,time
from datetime import datetime
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--close-after-review',action='store_true');ap.add_argument('--visual-confirmed',action='store_true');ap.add_argument('--start-ros-programs',action='store_true',help='Explicit unloaded regular startup under confirmed holds; no safety acknowledgement')
    for name in ['image','metadata','intrinsics','recipe']:ap.add_argument('--'+name,type=Path)
    ap.add_argument('--config',type=Path,default=REPO/'uwa_cell_motion/config/hardware_carton_supported_trend.yaml')
    a=ap.parse_args();out=a.output.resolve();record=out/'workflow.json';env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    if a.close_after_review:
        if not a.execute or not a.visual_confirmed:ap.error('Explicit --execute --visual-confirmed required after actual entry image review')
        report=json.loads(record.read_text())
        if report['phase']!='WAITING_VISUAL_REVIEW':raise ValueError('Current entry review required; no automatic retry')
    else:
        if any(getattr(a,n)is None for n in ['image','metadata','intrinsics','recipe']):ap.error('Image, metadata, intrinsics and recipe required')
        if out.exists():raise ValueError('Use a fresh workflow output directory')
        report=dict(success=False,phase='PREPARED',execute=a.execute,started_wall=datetime.now().astimezone().isoformat(),started_monotonic_s=time.monotonic(),events=[],loaded_motion=False,scope='Runtime invocation onward; external camera/transfer time separately recorded')
        if a.execute:out.mkdir(parents=True)
    def save():record.write_text(json.dumps(report,indent=2)+'\n')
    def phase(name,tool,*args):
        command=[sys.executable,str(REPO/'tools'/tool),*map(str,args)]
        if not a.execute:print(json.dumps(dict(phase=name,command=command,executed=False)));return
        event=dict(phase=name,started_monotonic_s=time.monotonic(),command=command);report['events'].append(event);report['phase']=name;save()
        with (out/(name+'.log')).open('w')as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env)
        event.update(duration_s=time.monotonic()-event['started_monotonic_s'],returncode=result.returncode);save()
        if result.returncode:raise RuntimeError(name+' failed; no automatic retry; see '+str(out/(name+'.log')))
    try:
        if a.close_after_review:
            phase('close','carton_gripper_phase.py','close','--state',out/'entry/result.json','--output',out/'grasp','--execute','--visual-confirmed',*(['--start-ros-programs']if a.start_ros_programs else []))
            report.update(success=True,phase='SUPPORTED_CONTACT_HELD')
        else:
            phase('snapshot','prepare_carton_hardware.py','--observe','--output',out/'snapshot')
            phase('registration','register_carton_from_oak.py','--image',a.image,'--metadata',a.metadata,'--intrinsics',a.intrinsics,'--description',a.recipe/'hardware.urdf','--output',out/'registration')
            phase('plan_high','prepare_carton_pregrasp.py','--observations',out/'snapshot/observations.json','--object-pose',out/'registration/object-pose.json','--contact-design',a.recipe/'contacts.json','--contact-scene',a.recipe/'scene.json','--config',a.config,'--pregrasp-m','.15','--output',out/'high-plan')
            if a.execute:
                evidence=json.loads((out/'high-plan/evidence.json').read_text());future=dict(evidence['saved_start'])
                future.update(zip(evidence['path']['joint_names'],evidence['path']['waypoints'][-1]))
                (out/'planned-high.json').write_text(json.dumps(dict(planned_only=True,segments=[dict(final_positions=future)]),indent=2)+'\n')
            # Decide that the chosen branches can complete the task BEFORE
            # spending a real approach on a merely valid isolated high pose.
            phase('plan_entry','prepare_carton_open_entry.py','--evidence',out/'high-plan','--approach',out/'planned-high.json','--planned-start','--output',out/'entry-plan')
            phase('high','run_carton_pregrasp.py','--evidence',out/'high-plan','--output',out/'high','--command-velocity','.1','--execute','--reset-unloaded',*(['--start-ros-programs']if a.start_ros_programs else []))
            # Already activated/open from release: read readiness, don't send
            # another opening or activation merely to repeat the same state.
            phase('open_readiness','carton_gripper_phase.py','prepare','--state',out/'high/result.json','--output',out/'open-readiness')
            phase('entry','run_carton_open_entry.py','--plan',out/'entry-plan/result.json','--output',out/'entry','--execute','--reset-unloaded',*(['--start-ros-programs']if a.start_ros_programs else []))
            report['phase']='WAITING_VISUAL_REVIEW'
    except BaseException as error:report.update(success=False,phase='STOPPED_NO_AUTOMATIC_RECOVERY',error=str(error))
    finally:
        grasp=out/'grasp/result.json'
        if a.close_after_review and grasp.exists():
            contact=json.loads(grasp.read_text())
            report['confirmed_contact_members']=contact.get('confirmed_contact_members',[])
            report['static_contact_hold_verified']=contact.get('static_contact_hold_verified',False)
            report['closing_control_result_success']=contact.get('success',False)
        report['elapsed_s']=time.monotonic()-report['started_monotonic_s'];report['updated_wall']=datetime.now().astimezone().isoformat()
        if a.execute:save()
    print(json.dumps({k:v for k,v in report.items()if k!='events'},indent=2));return 0 if report['phase']in ('WAITING_VISUAL_REVIEW','SUPPORTED_CONTACT_HELD')or not a.execute else 1


if __name__=='__main__':raise SystemExit(main())

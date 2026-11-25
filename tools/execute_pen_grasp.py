#!/usr/bin/env python3
"""N100 execution of one frozen left-rear pen sequence, after the existing operator reviews."""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import time

import numpy as np

try:  # Run-scoped copy, same existing SQLite review protocol; no runtime deployment.
    from pen_review_store import ReviewStore,caps,digest,encoded
except ModuleNotFoundError:
    from uwa_cell_tasks.motion_review import ReviewStore,caps,digest,encoded
from uwa_cell_gripper_control.client import GripperClient
from uwa_cell_motion.common import dump
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_execution import HardwareClient
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import require_domain
from uwa_cell_motion.protection_backend import minimal_enabled
from execute_calibration_observation_motion import checked_plans,follow_frozen

TASK='pen_holder_grasp'
ARM='left_rear'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def photo_packet(folder,earliest):
    from PIL import Image
    metadata=json.loads((folder/'metadata.json').read_text())
    raw=folder/'standard.png'
    first=datetime.fromisoformat(metadata['started_at']).timestamp()
    last=datetime.fromisoformat(metadata['finished_at']).timestamp()
    if (metadata.get('success') is not True or metadata.get('device_id')!='18443010314F3B1300'
            or metadata.get('standard',{}).get('path')!='standard.png'
            or metadata['standard']['lens_position']!=112 or not earliest<=first<=last<=time.time()):
        raise ValueError('A current OAK Pro entry photograph is required for this pen contact')
    with Image.open(raw) as im:
        if im.size!=(4056,3040):raise ValueError('Entry image must retain native OAK Pro pixels')
        im=im.rotate(180);im.thumbnail((1920,1440));stream=BytesIO();im.convert('RGB').save(stream,format='JPEG',quality=92)
    b=stream.getvalue()
    return dict(mime_type='image/jpeg',data_base64=base64.b64encode(b).decode(),display_sha256=digest(b),
                original_sha256=sha(raw),captured_at=metadata['finished_at'])


@contextmanager
def approval(store,operation,meta,preview):
    identifier=store.submit(operation,meta,preview);claimed=False
    try:
        print('WAITING_FOR_'+meta['stage'].upper()+'_REVIEW '+identifier,flush=True)
        while not store.claim(identifier):time.sleep(.4)
        claimed=True
        print('REVIEW_ACCEPTED_'+meta['stage'].upper()+' '+identifier,flush=True)
        yield identifier
    except BaseException as error:
        if claimed:store.finish(identifier,False,str(error) or 'Interrupted')
        else:store.withdraw(identifier)
        raise
    else:
        if store.finish(identifier,True)!='done':raise RuntimeError('Pen review was revoked')


def load_sequence(folder,expected):
    if sha(folder/'sequence.json')!=expected:raise ValueError('Pen sequence changed after ROSmini compilation')
    sequence=json.loads((folder/'sequence.json').read_text())
    cap=sequence['command_velocity_limit_rad_s']
    if (sequence.get('kind')!='pen_holder_grasp' or sequence['arm']!=ARM
            or [x.get('phase') for x in sequence['segments']]!=['approach','entry','lift']
            or any(x['arm']!=ARM for x in sequence['segments'])):raise ValueError('Expected exactly the left-rear pen approach/entry/lift')
    _,plans=checked_plans(folder,expected,cap)
    last=sequence['start']
    for plan in plans:
        if set(last)!=set(plan['request']['start']) or any(abs(last[j]-plan['request']['start'][j])>1e-8 for j in last):
            raise ValueError('Discontinuous pen sequence')
        last=dict(last,**dict(zip(plan['trajectory']['joint_names'],plan['trajectory']['points'][-1]['positions'])))
    return sequence,plans


def gripper_step(report,save,operation,command,**request):
    """Retain existing action feedback; no additional reads or command retries."""
    record=dict(arm=ARM,operation=operation,success=False,phase='RUNNING',**request)
    report['finger_commands'].append(record)
    report.update(success=False,phase='GRIPPER_'+operation.upper()+'_RUNNING');save()
    def feedback(state):
        # Keep only the latest existing action feedback in memory. Write the
        # workflow at the action boundary rather than adding per-poll disk I/O.
        record['last_feedback']=state
    try:
        result=command(feedback=feedback,**request)
    except BaseException as error:
        record.update(phase='FAILED',error=str(error) or 'Interrupted')
        report['phase']='GRIPPER_'+operation.upper()+'_FAILED';save()
        raise
    record.update(success=True,phase='COMPLETE',result=result)
    report['phase']='GRIPPER_'+operation.upper()+'_COMPLETED';save()
    return result


def pen_controller_ready(status):
    """The existing controller admission conditions, for this task's next command."""
    if not isinstance(status,dict) or status.get('paused') is not False:return False
    arm=status.get('arms',{}).get(ARM,{})
    return (arm.get('confirmed') is True and arm.get('paused') is False
            and isinstance(status.get('generation'),int)
            and arm.get('generation')==status['generation']
            and isinstance(arm.get('factor'),(int,float)) and arm['factor']>=1.-1e-9)


def await_pen_controller(client,report,save):
    """Wait once at command handoff, using already subscribed status only."""
    if not minimal_enabled():return
    if not pen_controller_ready(client.protection_status):
        report['phase']='WAITING_CONTROLLER_RESUME';save()
        print('WAITING_CONTROLLER_RESUME',flush=True)
        while not pen_controller_ready(client.protection_status):client.spin_once(timeout_sec=.05)
        print('CONTROLLER_RESUME_CONFIRMED',flush=True)
    report['controller_before_dispatch']=dict(generation=client.protection_status['generation'],
        arm=dict(client.protection_status['arms'][ARM]))


def run(args):
    require_domain('hardware')
    args.plans=args.plans.resolve();args.output=args.output.resolve()
    for name in ('entry','initial'):
        if getattr(args,name,None) is not None:setattr(args,name,getattr(args,name).resolve())
    sequence,plans=load_sequence(args.plans,args.sequence_sha256)
    args.output.mkdir(parents=True,exist_ok=True)
    state_file=args.output/'workflow.json'
    store=ReviewStore();status=store.status(task=TASK)
    if not status['area_released'] or status['session_id']!=sequence['scene_session']:
        raise ValueError('Work area changed since planning; capture and plan again')
    speed=status['settings']['speed_percent'];joint,tcp=caps(speed)
    if not(np.isclose(joint,sequence['command_velocity_limit_rad_s']) and np.isclose(tcp,sequence['tcp_limit_m_s'])):
        raise ValueError('Active command limits changed since pen planning')
    first=plans[0]
    problem=HardwareProblem(args.output/'model',first['config'],first['inventory'],first.get('layout_path'))
    for plan in plans:
        if (problem.binding!=plan['hardware_binding'] or problem.spheres.geometry.assets!=plan['mesh_sha256']
                or problem.cfg!=plan['config']):raise ValueError('Active model changed since pen planning')
    groups=[dict(phase=s['phase'],arms=[ARM],trajectories={ARM:p['trajectory']}) for s,p in zip(sequence['segments'],plans)]
    preview=dict(start=sequence['start'],robot_description=sequence['robot_description'],groups=groups,pen=sequence.get('pen'),
        duration_s=sequence['total_duration_s'])
    report=json.loads(state_file.read_text()) if args.phase=='contact' else dict(success=False,phase='PREPARED',arm=ARM,arm_commands=[],finger_commands=[])
    meta=dict(task=TASK,risk='high',stage='motion' if args.phase=='approach' else 'contact',arms=[ARM],
        speed_percent=speed,scene_session=sequence['scene_session'],requires_area=True,
        summary='Approach and enter the pen holder with left rear' if args.phase=='approach' else 'Close left rear on the adapter, lift vertically and hold',
        reason='New pen task. Review the complete approach, vertical entry and carried-tool lift. '+sequence['qualification'],
        duration_s=sequence['total_duration_s'],explicit_regular_start=False)
    def save():dump(state_file,report)
    client=None
    try:
        with motion_context():
            client=(__import__('uwa_cell_motion.minimal_execution',fromlist=['MinimalHardwareClient']).MinimalHardwareClient
                    if minimal_enabled() else HardwareClient)(problem,'hardware',[ARM])
            if args.phase=='approach':
                if getattr(args,'initial',None):
                    preview['image']=photo_packet(args.initial,0.)
                    if preview['image']['original_sha256']!=sequence['perception']['image_sha256']:
                        raise ValueError('Initial photograph differs from the localized pen image')
                meta['components']=[sequence['segments'][i]['sha256'] for i in (0,1)]
                with approval(store,str(args.output.resolve())+'/motion',meta,preview) as identifier:
                    client.connect()
                    with GripperClient(ARM) as gripper:
                        # Included in the movement review, at the held pregrasp pose.
                        for i,plan in enumerate(plans[:2]):
                            component=sequence['segments'][i]['sha256'];store.begin_component(identifier,component,'motion')
                            if i==1:
                                gripper_step(report,save,'activate',gripper.activate)
                                gripper_step(report,save,'open',gripper.open,force_raw=0,speed_raw=16)
                            record=dict(phase=sequence['segments'][i]['phase'],success=False)
                            await_pen_controller(client,report,save)
                            report['phase']=sequence['segments'][i]['phase'].upper()+'_RUNNING'
                            report['arm_commands'].append(record);save();follow_frozen(client,plan,record)
                            report['phase']=sequence['segments'][i]['phase'].upper()+'_COMPLETED';save()
                    report.update(phase='WAITING_VISUAL_REVIEW',entry_finished_unix=time.time(),sequence_sha256=args.sequence_sha256,
                                  motion_review=identifier,success=True);save()
            else:
                if report.get('phase')!='WAITING_VISUAL_REVIEW' or report.get('sequence_sha256')!=args.sequence_sha256:
                    raise ValueError('No completed open pen entry awaits contact review')
                image=photo_packet(args.entry,report['entry_finished_unix'])
                component=digest(encoded(dict(sequence=args.sequence_sha256,image=image['original_sha256'],arm=ARM,
                    force_raw=sequence['definition']['force_raw'],speed_raw=sequence['definition']['gripper_speed_raw'])).encode())
                meta.update(components=[component],capture_sha256=image['original_sha256'])
                contact_preview=dict(preview,start=plans[2]['request']['start'],groups=[groups[2]],image=image,
                    duration_s=plans[2]['trajectory']['duration_s'])
                with approval(store,str(args.output.resolve())+'/contact',meta,contact_preview) as identifier:
                    client.connect()
                    # Reuse the normal reviewed frozen-start check before closure.
                    from uwa_cell_tasks.reviewed_carton_execution import _start_matches
                    client.health();_start_matches(problem,client,plans[2]['request']['start'])
                    store.begin_component(identifier,component,'contact')
                    with GripperClient(ARM) as gripper:
                        report['close_result']=gripper_step(report,save,'close',gripper.close_gripper,
                            force_raw=sequence['definition']['force_raw'],speed_raw=sequence['definition']['gripper_speed_raw'])
                    report['phase']='GRIPPER_CLOSE_COMPLETED';save()
                    if not report['close_result'].get('contact_detected'):
                        report['phase']='NO_OBJECT_CONTACT';save()
                        raise RuntimeError('Pen grasp unconfirmed: close action reported no object contact; no lift sent')
                    record=dict(phase='lift',success=False);report['arm_commands'].append(record)
                    await_pen_controller(client,report,save)
                    report['phase']='LIFT_RUNNING';save()
                    follow_frozen(client,plans[2],record)
                    report.update(phase='PEN_LIFT_COMPLETED',success=True,contact_review=identifier,
                        qualification='Close action and checked lift completed; holding force and pen-tip TCP are not measured')
                    save()
    except BaseException as error:
        if minimal_enabled() and client is not None:
            report['controller_on_failure']=client.protection_status
        if report['phase'].endswith('_RUNNING'):
            report['phase']=report['phase'].removesuffix('_RUNNING')+'_FAILED'
        report.update(success=False,error=str(error) or 'Interrupted');save()
        # Ordinary task errors never open a potentially loaded gripper or retry.
        if isinstance(error,KeyboardInterrupt) and client is not None:
            report['stop_result']=client.stop() if minimal_enabled() else client.stop(client.owned);save()
        elif not minimal_enabled() and client is not None and client.owned:
            report['stop_result']=client.stop(client.owned);save()
        raise
    finally:
        if client is not None:client.destroy_node()
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=['approach','contact'],required=True)
    p.add_argument('--plans',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sequence-sha256',required=True);p.add_argument('--entry',type=Path)
    p.add_argument('--initial',type=Path)
    run(p.parse_args())

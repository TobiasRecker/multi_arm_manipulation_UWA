#!/usr/bin/env python3
"""Library program: OAK Pro/OpenCV, Gemini ROI fallback, checked left-rear pen pickup."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from run_carton_program import Progress,logged_command,n100,offline_tool,SSH_OPTIONS,N100_HOST,remote_location,live_inputs
from carton_camera_session import validate_session

REPO=Path(__file__).resolve().parents[1]
WORKSPACE=REPO.parents[1]
PROGRAM='pen-left-rear-v1'
DEFINITION=REPO/'config/pen_programs/pen-left-rear-v1.json'


def config():
    definition=json.loads(DEFINITION.read_text())
    if definition['arm']!='left_rear' or definition['program_id']!=PROGRAM:
        raise ValueError('Expected the left rear pen program')
    camera=live_inputs(WORKSPACE/definition['camera_config'],camera_id='oak_usb')
    validate_session(json.loads(camera['camera_session'].read_text()),camera['intrinsics'])
    return definition,camera


def availability(enabled):
    try:
        definition,camera=config()
        if not definition['mount']['centered_confirmed']:raise ValueError('Confirm the centered marker mounting first')
    except (OSError,ValueError,KeyError,TypeError) as error:
        return dict(live_available=False,plan_available=False,inspect_available=False,live_blocker=str(error))
    return dict(live_available=enabled,plan_available=enabled,inspect_available=True,
                live_blocker=None if enabled else 'Open the N100-enabled UWA Robot Power library for real execution.')


def capture(camera,out,name):
    folder=out/(name+'-photo');folder.mkdir()
    began=datetime.now(timezone.utc).isoformat()
    image,raw=camera.capture(folder)
    target=folder/'standard.png';shutil.copyfile(image,target)
    report=dict(success=True,mode='standard',source='fixed_focus_single_capture',camera_kind='oak_usb',
        device_id=raw['device_id'],started_at=began,finished_at=datetime.now(timezone.utc).isoformat(),
        standard=dict(raw['photo'],path='standard.png'),raw_metadata='native/metadata.json')
    (folder/'metadata.json').write_text(json.dumps(report,indent=2)+'\n')
    return folder


def wait_camera(camera,timeout=25.):
    deadline=time.monotonic()+timeout
    history=[];last=None
    while time.monotonic()<deadline:
        try:
            _,frame=camera.read()
        except RuntimeError:
            time.sleep(.05);continue
        stamp=frame['sequence']
        if stamp!=last:
            last=stamp
            product=float(frame['exposure_us'])*frame['reported_iso']
            history=(history+[product])[-3:]
            if len(history)==3 and min(history)>0 and max(history)/min(history)<=1.15:return
        time.sleep(.05)
    raise RuntimeError('OAK Pro exposure did not settle before the initial pen capture')


def upload(remote,local,log,recursive=False):
    return logged_command(['/usr/bin/scp',*SSH_OPTIONS,*(['-r'] if recursive else []),local,remote_location(remote)],log,100)


def download(remote,destination,log):
    return logged_command(['/usr/bin/scp',*SSH_OPTIONS,'-r',remote_location(remote),destination],log,100)


def observe(progress,remote):
    out=progress.output
    helper=REPO/'tools/observe_calibration_start.py'
    logged_command(n100('mkdir -p -- "$1"',remote),out/'remote-directory.log',15)
    upload(remote+'/observe_calibration_start.py',helper,out/'upload-observer.log')
    command=n100('''test "$(sha256sum "$1/observe_calibration_start.py" | cut -d ' ' -f 1)" = "$2"
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 "$1/observe_calibration_start.py" --output "$PWD/$1/observation"
''',remote,hashlib.sha256(helper.read_bytes()).hexdigest())
    logged_command(command,out/'observation.log',60)
    download(remote+'/observation',out,out/'download-observation.log')
    return out/'observation'


def remote_review(progress,remote,phase,sequence_sha):
    out=progress.output
    helper_sha=hashlib.sha256((out/'execution-helpers.json').read_bytes()).hexdigest()
    script='''/usr/bin/python3 -c 'import hashlib,json,pathlib,sys; p=pathlib.Path(sys.argv[1]); f=p/"execution-helpers.json"; assert hashlib.sha256(f.read_bytes()).hexdigest()==sys.argv[2]; assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in json.loads(f.read_text()).items())' "$1" "$4" || exit $?
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u "$1/execute_pen_grasp.py" \
  --phase "$2" --plans "$1/plans" --output "$1/execution" --sequence-sha256 "$3" --entry "$1/entry" --initial "$1/initial"
'''
    with (out/('n100-'+phase+'.log')).open('w') as log,subprocess.Popen(n100(script,remote,phase,sequence_sha,helper_sha),
            cwd=WORKSPACE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True) as child:
        for line in child.stdout:
            log.write(line);log.flush()
            if line.startswith('WAITING_FOR_'):
                progress.update('motion_review' if phase=='approach' else 'contact_review',
                    'Review this pen '+phase+' in UWA Robot Power. Left rear only.')
            elif line.startswith('REVIEW_ACCEPTED_'):
                progress.update('pen_positioning' if phase=='approach' else 'pen_grasp_lift','Review accepted. Executing the checked left-rear pen '+phase+'.')
        code=child.wait()
    try:
        download(remote+'/execution',out,out/('download-'+phase+'.log'))
    except RuntimeError as error:
        if code:
            lines=(out/('n100-'+phase+'.log')).read_text().strip().splitlines()
            raise RuntimeError('N100 pen '+phase+' failed before a result was saved: '+(lines[-1] if lines else str(error))) from error
        raise
    report=json.loads((out/'execution/workflow.json').read_text())
    if code or not report.get('success'):raise RuntimeError(report.get('error') or 'N100 pen '+phase+' failed; inspect run log and Motion review')
    return report


def run(mode,progress):
    definition,camera_config=config();out=progress.output
    (out/'definition.json').write_bytes(DEFINITION.read_bytes())
    (out/'camera-session.json').write_bytes(camera_config['camera_session'].read_bytes())
    (out/'intrinsics.json').write_bytes(camera_config['intrinsics'].read_bytes())
    remote='setup/tasks/pen-grasp/'+out.name
    observation=None
    if mode!='inspect':
        progress.update('snapshot','Reading the current four-arm start and the active N100 model; no robot commands.')
        observation=observe(progress,remote)
    sys.path.insert(0,str(REPO/'uwa_cell_control'))
    from uwa_cell_control.n100_usb_camera import N100UsbCamera
    camera=N100UsbCamera(WORKSPACE,out/'camera-transport',camera_config['focus'])
    try:
        progress.update('capture','Capturing a fresh native OAK Pro image with the two 30 mm pen markers.')
        camera.start()
        wait_camera(camera)
        photo=capture(camera,out,'initial')
        progress.update('registration','OpenCV measures markers 97 and 96; Gemini may guide a second native ROI measurement.')
        command=offline_tool('prepare_pen_grasp.py','--definition',out/'definition.json',
            '--camera',out/'intrinsics.json','--session',out/'camera-session.json','--image',photo/'standard.png','--output',out/'plans')
        if mode=='inspect':command+=['--inspect-only']
        else:
            snapshot=json.loads((observation/'snapshot.json').read_text())
            # Shared speed is read from the same review store on the N100.
            speed=json.loads(logged_command(n100('''source src/multi_arm_manipulation_UWA/scripts/control_env.bash
/usr/bin/python3 -c 'import json; from uwa_cell_tasks.motion_review import ReviewStore; print(json.dumps(ReviewStore().status()))'
'''),out/'review-status.log',20))['settings']['speed_percent']
            command+=['--snapshot',observation/'snapshot.json','--context',observation/'model-context.json','--tcp-cap',.25*speed/100]
            progress.update('planning','Checking the complete left-rear approach, vertical entry and carried-pen lift against the full cell and CAD holder.')
        logged_command(command,out/'perception-and-planning.log',240)
        artifact='plans/perception/pen-preview.jpg'
        if mode=='inspect':
            return dict(perception=json.loads((out/'plans/perception/object-pose.json').read_text()),
                motion='No robot or gripper commands.',artifacts=dict(pen_preview=artifact))
        if mode=='plan':
            sequence=json.loads((out/'plans/sequence.json').read_text())
            return dict(arm='left_rear',motion='Complete pickup planned; no robot or gripper commands.',
                        duration_s=sequence['total_duration_s'],artifacts=dict(pen_preview=artifact),
                        qualification=sequence['qualification'])
        sequence_sha=hashlib.sha256((out/'plans/sequence.json').read_bytes()).hexdigest()
        files={'execute_pen_grasp.py':REPO/'tools/execute_pen_grasp.py',
               'execute_calibration_observation_motion.py':REPO/'tools/execute_calibration_observation_motion.py',
               'pen_review_store.py':REPO/'uwa_cell_tasks/uwa_cell_tasks/motion_review.py'}
        for name,path in files.items():upload(remote+'/'+name,path,out/('upload-'+name+'.log'))
        manifest=out/'execution-helpers.json'
        manifest.write_text(json.dumps({name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()},indent=2)+'\n')
        upload(remote+'/execution-helpers.json',manifest,out/'upload-helper-binding.log')
        handoff=out/'handoff-plans';handoff.mkdir()
        for name in ('sequence.json','approach.json','entry.json','lift.json'):
            shutil.copyfile(out/'plans'/name,handoff/name)
        upload(remote+'/plans',handoff,out/'upload-plans.log',recursive=True)
        upload(remote+'/initial',photo,out/'upload-initial.log',recursive=True)
        # All entry/lift plans exist and passed before the first approach is reviewed.
        report=remote_review(progress,remote,'approach',sequence_sha)
        if report['phase']!='WAITING_VISUAL_REVIEW':raise ValueError('The open pen entry was not completed')
        progress.update('entry_capture','Capturing the actual open-gripper alignment for contact and lift review.')
        entry=capture(camera,out,'entry')
    finally:
        camera.stop()
    upload(remote+'/entry',entry,out/'upload-entry.log',recursive=True)
    report=remote_review(progress,remote,'contact',sequence_sha)
    if report['phase']!='PEN_LIFT_COMPLETED':raise ValueError('The pen close/lift sequence did not complete')
    return dict(remote_run=remote,arm='left_rear',result=report,artifacts=dict(pen_preview=artifact),
                qualification='Normal close action and vertical lift completed; actual holding force and writing TCP not measured')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['inspect','plan','live'],required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--live-config',type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);progress=Progress(args.output)
    try:result=run(args.mode,progress)
    except Exception as error:
        fields={}
        if (args.output/'plans/perception/pen-preview.jpg').is_file():
            fields['result']=dict(artifacts=dict(pen_preview='plans/perception/pen-preview.jpg'))
        progress.update('failed',str(error),error=str(error),**fields);return 1
    messages=dict(inspect='Pen image inspection completed.',plan='Complete pen pickup planned; no robot or gripper commands.',
                  live='Pen close and lift completed; left rear remains at the lifted pose.')
    progress.update('done',messages[args.mode],result=result)
    return 0


if __name__=='__main__':raise SystemExit(main())

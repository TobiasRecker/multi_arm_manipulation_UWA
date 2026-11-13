"""Resumable, camera-only digitization jobs. No robot command entry point.

Heavy algorithms and hardware routines stay outside the agent's instruction
loop. All data/recipe/code hashes and quality outcomes remain reviewable.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import time

import cv2
import numpy as np

from .digitization_geometry import FAMILIES,fit
from .digitization_optics import sha,load_optics,prepare

CAMERAS=('left_front','left_rear','right_front','right_rear','oak4')
STAGES=('acquisition','prepare','fit','export','tracking')


def now():return datetime.now(timezone.utc).isoformat()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def create(root,workspace,object_id,family,size,known=None,views_per_wrist=1):
    root=Path(root).resolve();workspace=Path(workspace).resolve()
    if not root.is_relative_to(workspace/'setup/digitization'):raise ValueError('Jobs belong under workspace/setup/digitization')
    if not re.fullmatch('[a-z][a-z0-9_]*',object_id) or family not in FAMILIES:raise ValueError('Invalid object ID/family')
    size=np.asarray(size,float)
    if size.shape!=(3,) or not np.isfinite(size).all() or min(size)<=0 or max(size)>2:raise ValueError('Three finite positive rough sizes in metres required')
    if type(views_per_wrist)!=int or not 1<=views_per_wrist<=100:raise ValueError('Invalid wrist view count')
    spec=dict(object_id=object_id,family=family,user_rough_dimensions_m=size.tolist(),
        known_dimensions_m=known or {},dimensions_source='user supplied, not independently measured',
        desired_views_per_wrist=views_per_wrist)
    root.mkdir(parents=True,exist_ok=True)
    # Exclusive creation protects an existing job, even across two agents.
    with (root/'job.json').open('x') as stream:
        json.dump(dict(schema=1,created_at=now(),workspace=str(workspace),spec=spec,spec_sha256=digest(spec)),stream,indent=2);stream.write('\n')
    save(root/'state.json',dict(schema=1,status='NEEDS_INPUT',next_action='capture or ingest a stationary native photo set',stages={},captures=[],quality=dict(geometry='NOT_TESTED',visual='NOT_TESTED',tracking='NOT_TESTED',manipulation='NOT_APPROVED')))
    return summary(root)


def read(root):
    root=Path(root).resolve();job=json.loads((root/'job.json').read_text())
    if job.get('schema')!=1 or digest(job['spec'])!=job['spec_sha256']:raise ValueError('Job specification changed; create a new version')
    return job,json.loads((root/'state.json').read_text())


@contextmanager
def lock(root):
    with (Path(root)/'.lock').open('a') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('This digitization job is already running') from None
        yield


def summary(root):
    job,state=read(root)
    return dict(job=str(Path(root).resolve()),object_id=job['spec']['object_id'],family=job['spec']['family'],
        status=state['status'],next_action=state.get('next_action'),quality=state['quality'],capture_sets=len(state['captures']),
        stages={k:{x:v[x] for x in ('status','duration_s','cached','result') if x in v} for k,v in state['stages'].items()})


def code_signature():
    import scipy
    paths=[Path(__file__),Path(__file__).with_name('digitization_optics.py'),Path(__file__).with_name('digitization_geometry.py'),Path(__file__).with_name('object_digitization.py'),Path(__file__).with_name('board_photo_evaluation.py')]
    return dict(files={str(p):sha(p) for p in paths},python=platform.python_version(),numpy=np.__version__,opencv=cv2.__version__,scipy=scipy.__version__)


def run_stage(root,name,inputs,operation):
    """An input/output change invalidates downstream work, never raw captures."""
    root=Path(root);job,state=read(root);key=digest(dict(spec=job['spec_sha256'],inputs=inputs,implementation=code_signature()))
    previous=state['stages'].get(name)
    if previous and previous.get('key')==key and previous['status']=='DONE':
        if all(Path(p).is_file() and sha(p)==s for p,s in previous['outputs'].items()):
            previous['cached']=True;save(root/'state.json',state);return previous['result']
    for downstream in STAGES[STAGES.index(name)+1:]:state['stages'].pop(downstream,None)
    if name in ('acquisition','prepare','fit'):state['quality']=dict(geometry='NOT_TESTED',visual='NOT_TESTED',tracking='NOT_TESTED',manipulation='NOT_APPROVED')
    stage=dict(status='RUNNING',key=key,started_at=now(),cached=False);state['stages'][name]=stage
    state.update(status='RUNNING',next_action=name);save(root/'state.json',state);started=time.monotonic()
    try:
        result,outputs=operation(job,state)
        stage.update(status='DONE',result=result,outputs={str(Path(p).resolve()):sha(p) for p in outputs})
        state.update(status='NEEDS_INPUT',next_action=result.get('next_action','review result'))
    except KeyboardInterrupt:
        stage.update(status='CANCELLED');state.update(status='CANCELLED',next_action='inspect interrupted stage; no automatic device retry');raise
    except Exception as error:
        stage.update(status='FAILED',error=str(error));state.update(status='FAILED',next_action=str(error));raise
    finally:
        stage.update(duration_s=round(time.monotonic()-started,3),finished_at=now());save(root/'state.json',state)
    return result


def verify_manifest(path):
    path=Path(path).resolve();m=json.loads(path.read_text())
    if not m.get('all_captured') or not m.get('stationary_set_confirmed'):raise ValueError('Incomplete/unconfirmed stationary set')
    if set(m.get('cameras',{}))!=set(CAMERAS):raise ValueError('Expected all four wrists plus OAK')
    images=[];files={str(path):sha(path)}
    for name,c in m['cameras'].items():
        if not c.get('success'):raise ValueError('Failed camera '+name)
        image=(path.parent/name/c['image']).resolve()
        if not image.is_relative_to(path.parent):raise ValueError('Image escapes capture directory')
        record=image.parent/'record.json';r=json.loads(record.read_text());im=cv2.imread(str(image))
        if im is None or sha(image)!=r['sha256']:raise ValueError('Changed/missing photograph '+name)
        expected=[8000,6000] if name=='oak4' else [2592,1944]
        if [im.shape[1],im.shape[0]]!=expected:raise ValueError('Native image required '+name)
        files.update({str(image):sha(image),str(record):sha(record)})
        images.append(dict(camera=name,image=str(image),sha256=sha(image),board_id=r.get('observation',{}).get('board_id')))
    return m,images,files


def ingest(root,manifest):
    root=Path(root);job,state=read(root);m,images,files=verify_manifest(manifest)
    existing=list(state['captures']);path=str(Path(manifest).resolve())
    same=next((c for c in existing if c['manifest']==path),None)
    if same:
        if same['files']!=files:raise ValueError('An imported capture changed; preserve original and create a new job')
        return summary(root)
    old_hashes={e['sha256'] for row in existing for e in row['images']}
    if any(e['sha256'] in old_hashes for e in images):raise ValueError('Duplicate photographs cannot count as new views')
    row=dict(round=len(existing)+1,manifest=path,files=files,images=images,stationary_set_confirmed=True)
    def operation(job,state):
        state['captures']=existing+[row]
        data=dict(schema=1,acquisition_complete=True,rounds=state['captures'])
        save(root/'dataset.json',data)
        return dict(sets=len(state['captures']),images=5*len(state['captures']),next_action='prepare camera models and inspect coverage'),[root/'dataset.json']
    run_stage(root,'acquisition',dict(captures=[c['files'] for c in existing]+[files]),operation)
    return summary(root)


def capture(root,telemetry_source,new_view=False):
    root=Path(root);job,state=read(root)
    if state['captures'] and not new_view:raise ValueError('A set already exists; --new-view explicitly requests another photograph set')
    from .board_capture import CaptureRig,FIVE_CAMERAS
    ws=Path(job['workspace']);rig=CaptureRig(ws,root/'captures',cameras=FIVE_CAMERAS,
        optics_path=ws/'src/multi_arm_manipulation_UWA/config/digitization/five_camera_capture.yaml',board='both',telemetry_source=telemetry_source)
    started=time.monotonic()
    try:
        rig.lock_focus();report=rig.capture_all(native=True)
    finally:
        try:rig.restore_focus()
        finally:rig.instance_lock.close()
    save(root/'last_capture_transaction.json',dict(session=str(rig.session),duration_s=time.monotonic()-started,robot_commands=False,restoration_confirmed=True))
    return ingest(root,Path(report['directory'])/'manifest.json')


def prepare_job(root):
    root=Path(root);job,state=read(root);ws=Path(job['workspace']);repo=ws/'src/multi_arm_manipulation_UWA'
    registry=repo/'config/digitization/native_optics.json';policy_path=repo/'config/digitization/quality_v1.json'
    if not state['captures']:raise ValueError('Acquire or ingest a photo set first')
    for row in state['captures']:
        for p,s in row['files'].items():
            if sha(p)!=s:raise ValueError('Capture input changed: '+p)
    from uwa_cell_description.configuration import load_layout
    layout=load_layout();optics=load_optics(ws,json.loads(registry.read_text()));policy=json.loads(policy_path.read_text())
    def operation(job,state):
        data=json.loads((root/'dataset.json').read_text());out=root/'prepared'
        result=prepare(data,optics,layout['charuco'],out,policy)
        save(out/'camera_models.json',result['cameras']);save(out/'preparation.json',result)
        save(out/'policy.json',policy)
        request=dict(schema=1,object_id=job['spec']['object_id'],family=job['spec']['family'],
            cameras=result['cameras'],user_rough_dimensions_m=job['spec']['user_rough_dimensions_m'],
            metric_frame='right_table_board',world_pose_required=False,
            masks_required=job['spec']['family']=='multiview_mesh',backend_registered=False if job['spec']['family']=='multiview_mesh' else True,
            absolute_accuracy_validated=False)
        save(out/'reconstruction_request.json',request)
        missing={k:v for k,v in result['unique_camera_centres_10mm'].items() if k!='oak4' and v<job['spec']['desired_views_per_wrist']}
        action=('additional checked wrist viewpoints required: '+str(missing)) if missing else (
            'complex object: supply reviewed object masks and a validated multiview mesh backend' if job['spec']['family']=='multiview_mesh' else 'supply image-bound fit/validation landmarks')
        return dict(camera_views=len(result['cameras']),rejected_views=result['rejected_views'],
            unique_centres=result['unique_camera_centres_10mm'],warnings=result['warnings'],next_action=action),list(out.glob('*.json'))+list(out.glob('*.jpg'))
    run_stage(root,'prepare',dict(dataset=sha(root/'dataset.json'),registry=sha(registry),policy=sha(policy_path),optics=optics,board=layout['charuco']),operation)
    return summary(root)


def fit_job(root,annotations):
    root=Path(root);job,state=read(root)
    if job['spec']['family']=='multiview_mesh':
        state.update(status='NEEDS_INPUT',next_action='Complex geometry: multiple views, object masks and a validated mesh backend required; no box substitution')
        save(root/'state.json',state);return summary(root)
    prepare_job(root);job,state=read(root);path=Path(annotations).resolve();data=json.loads(path.read_text())
    models_path=root/'prepared/camera_models.json';models=json.loads(models_path.read_text())
    for key,o in data['observations'].items():
        if key not in models or o.get('image_sha256')!=models[key]['image_sha256']:raise ValueError('Landmarks must match original image SHA256: '+key)
    policy_path=root/'prepared/policy.json'
    def operation(job,state):
        result=fit(models,data,job['spec']['family'],job['spec']['known_dimensions_m'],job['spec']['user_rough_dimensions_m'],json.loads(policy_path.read_text()))
        result.update(annotation_sha256=sha(path),camera_models_sha256=sha(models_path),policy_sha256=sha(policy_path))
        save(root/'fit/model.json',result)
        state['quality']['geometry']='IMAGE_CONSISTENT' if result['image_consistency_passed'] else 'REVIEW_REQUIRED'
        # Annotations are copied so their exact split and coordinates survive edits.
        save(root/'fit/annotations.json',data)
        return dict(dimensions_m=result['dimensions_m'],metrics=result['metrics'],
            next_action='export candidate asset' if result['image_consistency_passed'] else 'review residuals; thresholds unchanged'),[root/'fit/model.json',root/'fit/annotations.json']
    run_stage(root,'fit',dict(annotations=sha(path),models=sha(models_path),policy=sha(policy_path)),operation)
    return summary(root)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='operation',required=True)
    init=sub.add_parser('init');init.add_argument('--job',type=Path,required=True);init.add_argument('--workspace',type=Path,default=Path(os.environ.get('UWA_WS',Path.home()/'UWA_ws')))
    init.add_argument('--id',required=True);init.add_argument('--family',choices=FAMILIES,required=True);init.add_argument('--size-m',type=float,nargs=3,required=True)
    init.add_argument('--known-dimensions',type=Path);init.add_argument('--views-per-wrist',type=int,default=1)
    for name in ('status','ingest','capture','prepare','fit'):
        p=sub.add_parser(name);p.add_argument('--job',type=Path,required=True)
        if name=='ingest':p.add_argument('--manifest',type=Path,required=True)
        if name=='capture':p.add_argument('--telemetry-source',choices=('ros','rtde'),default='ros');p.add_argument('--new-view',action='store_true')
        if name=='fit':p.add_argument('--annotations',type=Path)
    args=parser.parse_args();cv2.setNumThreads(2)
    try:
        if args.operation=='init':result=create(args.job,args.workspace,args.id,args.family,args.size_m,
            json.loads(args.known_dimensions.read_text()) if args.known_dimensions else None,args.views_per_wrist)
        else:
            with lock(args.job):
                if args.operation=='status':result=summary(args.job)
                elif args.operation=='ingest':result=ingest(args.job,args.manifest)
                elif args.operation=='capture':result=capture(args.job,args.telemetry_source,args.new_view)
                elif args.operation=='prepare':result=prepare_job(args.job)
                else:
                    if args.annotations is None and read(args.job)[0]['spec']['family']!='multiview_mesh':raise ValueError('--annotations required')
                    result=fit_job(args.job,args.annotations)
        print(json.dumps(result,indent=2));return 0
    except Exception as error:
        print(json.dumps(dict(status='FAILED',error=str(error)),indent=2));return 1


if __name__=='__main__':sys.exit(main())

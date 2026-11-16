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
import subprocess

import cv2
import numpy as np

from .digitization_geometry import FAMILIES,fit
from .digitization_optics import sha,load_optics,prepare

CAMERAS=('left_front','left_rear','right_front','right_rear','oak4')
STAGES=('acquisition','prepare','fit','texture','export','tracking')


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
    if state['status']=='RUNNING':
        with (Path(root)/'.lock').open('a') as stream:
            try:
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                state['status']='CANCELLED'
                for stage in state['stages'].values():
                    if stage['status']=='RUNNING':stage['status']='CANCELLED'
                state['next_action']='Previous process ended without completing the stage; inspect logs and explicitly resume. No device action was restarted.'
            except BlockingIOError:pass
    return dict(job=str(Path(root).resolve()),object_id=job['spec']['object_id'],family=job['spec']['family'],
        status=state['status'],next_action=state.get('next_action'),quality=state['quality'],capture_sets=len(state['captures']),
        stages={k:{x:v[x] for x in ('status','duration_s','cached','result','error') if x in v} for k,v in state['stages'].items()})


def code_signature():
    import scipy
    paths=[Path(__file__),Path(__file__).with_name('digitization_optics.py'),Path(__file__).with_name('digitization_geometry.py'),Path(__file__).with_name('object_digitization.py'),Path(__file__).with_name('board_photo_evaluation.py')]
    return dict(files={str(p.resolve()):sha(p) for p in paths},python=platform.python_version(),numpy=np.__version__,opencv=cv2.__version__,scipy=scipy.__version__)


def run_stage(root,name,inputs,operation):
    """An input/output change invalidates downstream work, never raw captures."""
    root=Path(root).resolve();job,state=read(root);key=digest(dict(spec=job['spec_sha256'],inputs=inputs,implementation=code_signature()))
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


def commit_manifest(root,job,state,manifest,validated=None):
    root=Path(root).resolve();m,images,files=validated if validated is not None else verify_manifest(manifest)
    existing=list(state['captures']);path=str(Path(manifest).resolve())
    if any(c['manifest']==path for c in existing):raise ValueError('Capture already committed')
    old_hashes={e['sha256'] for row in existing for e in row['images']}
    if any(e['sha256'] in old_hashes for e in images):raise ValueError('Duplicate photographs cannot count as new views')
    state['captures']=existing+[dict(round=len(existing)+1,manifest=path,files=files,images=images,stationary_set_confirmed=True)]
    save(root/'dataset.json',dict(schema=1,acquisition_complete=True,rounds=state['captures']))
    return dict(sets=len(state['captures']),images=5*len(state['captures']),next_action='prepare camera models and inspect coverage'),[root/'dataset.json']


def ingest(root,manifest):
    root=Path(root).resolve();job,state=read(root);m,images,files=verify_manifest(manifest)
    existing=list(state['captures']);path=str(Path(manifest).resolve())
    same=next((c for c in existing if c['manifest']==path),None)
    if same:
        if same['files']!=files:raise ValueError('An imported capture changed; preserve original and create a new job')
        return summary(root)
    def operation(job,state):
        return commit_manifest(root,job,state,manifest,(m,images,files))
    run_stage(root,'acquisition',dict(captures=[c['files'] for c in existing]+[files]),operation)
    return summary(root)


def capture(root,telemetry_source,new_view=False):
    root=Path(root).resolve();job,state=read(root)
    previous=root/'last_capture_transaction.json';recovery=root/'recovery.json'
    if previous.exists() and not json.loads(previous.read_text()).get('restoration_confirmed'):
        if not recovery.exists() or json.loads(recovery.read_text()).get('source_attempt_sha256')!=sha(previous):
            raise ValueError('Previous camera restore unconfirmed; run explicit recover when devices and cameras are available')
    if state['captures'] and not new_view:raise ValueError('A set already exists; --new-view explicitly requests another photograph set')
    def operation(job,state):
        from .board_capture import CaptureRig,FIVE_CAMERAS
        ws=Path(job['workspace']);started=time.monotonic();rig=None
        attempt=dict(started_at=now(),robot_commands=False,restoration_confirmed=False)
        try:
            rig=CaptureRig(ws,root/'captures',cameras=FIVE_CAMERAS,
                optics_path=ws/'src/multi_arm_manipulation_UWA/config/digitization/five_camera_capture.yaml',board='both',telemetry_source=telemetry_source)
            attempt['session']=str(rig.session)
            try:
                rig.lock_focus();report=rig.capture_all(native=True)
                attempt['manifest']=str(Path(report['directory'])/'manifest.json')
            finally:
                try:rig.restore_focus();attempt['restoration_confirmed']=True
                finally:rig.instance_lock.close()
            attempt['status']='DONE'
            return commit_manifest(root,job,state,attempt['manifest'])
        except BaseException as error:
            attempt.update(status='FAILED',error=str(error));raise
        finally:
            attempt['duration_s']=time.monotonic()-started
            save(root/'last_capture_transaction.json',attempt)
            save(root/'capture_attempts'/(attempt['started_at'].replace(':','_')+'.json'),attempt)
    run_stage(root,'acquisition',dict(explicit_capture_requested_at=now(),telemetry_source=telemetry_source),operation)
    return summary(root)


def recover_job(root):
    """Explicit camera-only restoration; never called by status/prepare/resume."""
    root=Path(root).resolve();job,state=read(root);attempt_path=root/'last_capture_transaction.json'
    attempt=json.loads(attempt_path.read_text());original=Path(attempt['session'])/'original_wrist_settings.json'
    from .board_capture import CaptureRig,FIVE_CAMERAS
    ws=Path(job['workspace']);rig=CaptureRig(ws,root/'recovery_sessions',cameras=FIVE_CAMERAS,
        optics_path=ws/'src/multi_arm_manipulation_UWA/config/digitization/five_camera_capture.yaml',board='both',telemetry_source='rtde')
    try:
        rig.original_settings=json.loads(original.read_text());rig.restore_focus()
        # restore_focus checks the changed fields; read every camera as final
        # evidence, including those already at the acquisition focus originally.
        readback={name:rig.wrist(name).settings(refresh=True) for name in rig.wrist_cameras}
        save(root/'recovery.json',dict(restoration_confirmed=True,source_attempt_sha256=sha(attempt_path),
            session=str(rig.session),camera_readback=readback,finished_at=now(),robot_commands=False))
        state.update(status='NEEDS_INPUT',next_action='camera configuration restored; explicitly request a new native capture')
        save(root/'state.json',state)
    finally:rig.instance_lock.close()
    return summary(root)


def prepare_job(root):
    root=Path(root).resolve();job,state=read(root);ws=Path(job['workspace']);repo=ws/'src/multi_arm_manipulation_UWA'
    registry=repo/'config/digitization/native_optics.json';policy_path=repo/'config/digitization/quality_v1.json'
    if not state['captures']:raise ValueError('Acquire or ingest a photo set first')
    for row in state['captures']:
        for p,s in row['files'].items():
            if sha(p)!=s:raise ValueError('Capture input changed: '+p)
    if json.loads((root/'dataset.json').read_text())!=dict(schema=1,acquisition_complete=True,rounds=state['captures']):
        raise ValueError('Dataset index changed independently of committed captures')
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
    root=Path(root).resolve();job,state=read(root)
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


def export_job(root,draft=False):
    root=Path(root).resolve();job,state=read(root);source=root/'fit/model.json'
    if not source.exists() or state['stages'].get('fit',{}).get('status')!='DONE':raise ValueError('A completed parametric fit is required')
    # Revalidate frozen upstream data before trusting a cached fit/export.
    annotations=root/'fit/annotations.json';fit_job(root,annotations)
    job,state=read(root);model=json.loads(source.read_text());ws=Path(job['workspace'])
    if not model['image_consistency_passed'] and not draft:raise ValueError('Geometry needs review; --draft permits an explicitly unapproved candidate export')
    script=ws/'src/multi_arm_manipulation_UWA/tools/export_digitization_asset.py'
    textures=root/'fit/textures.json';texture_files={}
    if textures.exists() and state['stages'].get('texture',{}).get('status')=='DONE':
        texture_files[str(textures)]=sha(textures)
        for item in json.loads(textures.read_text()):texture_files[item['texture']]=sha(item['texture'])
    def operation(job,state):
        parent=root/'candidates';parent.mkdir(exist_ok=True)
        n=1
        while ((parent/(job['spec']['object_id']+'_r'+str(n))).exists() or
               (root/'export_work'/(job['spec']['object_id']+'_r'+str(n))).exists()):n+=1
        out=parent/(job['spec']['object_id']+'_r'+str(n))
        command=[str(ws/'.venvs/oak-model/bin/python'),str(script),'--job',str(root.resolve()),'--output',str(out.resolve())]
        # CAD/VTK use their own environment; do not inherit ROS Qt/library paths.
        env={k:v for k,v in os.environ.items() if k not in ('LD_LIBRARY_PATH','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH')}
        with (root/'export.log').open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=180)
        if result.returncode:raise RuntimeError('CAD exporter failed; see '+str(root/'export.log'))
        manifest=json.loads((out/'asset.json').read_text())
        preview_script=script.with_name('preview_digitization_asset.py')
        with (root/'preview.log').open('w') as log:
            preview=subprocess.run([str(ws/'.venvs/oak-model/bin/python'),str(preview_script),
                '--asset',str(out.resolve()),'--output',str((out/'preview.png').resolve())],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45)
        preview_ok=preview.returncode==0 and (out/'preview.png').is_file()
        if preview_ok:
            manifest['files']['preview.png']=sha(out/'preview.png');save(out/'asset.json',manifest)
        state['quality']['visual']='CANDIDATE_EXPORTED'
        return dict(asset=str(out.resolve()),asset_id=manifest['asset_id'],draft=not model['image_consistency_passed'],preview_generated=preview_ok,
            next_action='inspect candidate rendering and run held-out tracking check; not installed in the cell'),[p for p in out.rglob('*') if p.is_file()]
    packer=script.with_name('package_carton_asset.py')
    run_stage(root,'export',dict(model=sha(source),models=sha(root/'prepared/camera_models.json'),script=sha(script),
        preview=sha(script.with_name('preview_digitization_asset.py')),preview_backend=sha(script.with_name('preview_ptfe_l.py')),
        packer=sha(packer),textures=texture_files,draft=draft),operation)
    return summary(root)


def track_job(root):
    root=Path(root).resolve();job,state=read(root);stage=state['stages'].get('export')
    if not stage or stage['status']!='DONE':raise ValueError('Export a candidate first')
    for p,s in stage['outputs'].items():
        if sha(p)!=s:raise ValueError('Candidate asset changed since export')
    asset=Path(stage['result']['asset']);model=json.loads((root/'fit/model.json').read_text())
    cameras=json.loads((root/'prepared/camera_models.json').read_text());manifest=json.loads((asset/'asset.json').read_text())
    from uwa_cell_tracking.model import surface_reference
    from uwa_cell_tracking.core import TexturePose
    from uwa_cell_tracking.cli import record,annotate
    def operation(job,state):
        out=root/'tracking';out.mkdir(exist_ok=True);reference=out/'reference.npz';report=dict(single_frame_diagnostic=True,absolute_accuracy_validated=False,manipulation_approved=False,views={})
        try:
            bank=surface_reference(asset,reference)
        except ValueError as error:
            if 'Insufficient textured surface features' not in str(error):raise
            report.update(status='NO_TEXTURE_REFERENCE',reason=str(error));state['quality']['tracking']='NO_TEXTURE_REFERENCE'
            save(out/'report.json',report)
            return dict(status=report['status'],next_action='supply measured photo textures or use a validated geometry/depth tracker'),[out/'report.json']
        estimator=TexturePose(reference);source_images=set(manifest['provenance'].get('texture_source_image_sha256',[]))
        for key,metric in model['metrics'].items():
            if metric['role']!='validation':continue
            c=cameras[key]
            if c['image_sha256'] in source_images:
                report['views'][key]=dict(status='NOT_INDEPENDENT',reason='Image supplied asset texture');continue
            if sha(c['image'])!=c['image_sha256']:raise ValueError('Held-out photograph changed')
            image=cv2.imread(c['image']);K=np.array(c['K']);D=np.array(c['D']);result=estimator.register(image,K,D)
            report['views'][key]=record(result);cv2.imwrite(str(out/(key+'.jpg')),annotate(image,result,K,D))
        valid=any(v['status']=='VALID' for v in report['views'].values())
        report.update(status='DETECTED_IN_HELD_OUT_IMAGE' if valid else 'NO_HELD_OUT_DETECTION',features=bank['features'],reference_pose_used=False)
        state['quality']['tracking']=report['status'];save(out/'report.json',report)
        return dict(status=report['status'],views=report['views'],next_action='review single-image check; online tracking and absolute accuracy still unvalidated'),[p for p in out.iterdir() if p.is_file()]
    backend=Path(job['workspace'])/'src/multi_arm_manipulation_UWA/uwa_cell_tracking/uwa_cell_tracking'
    sources={n:sha(backend/n) for n in ('core.py','model.py','cli.py')}
    run_stage(root,'tracking',dict(asset=sha(asset/'asset.json'),models=sha(root/'prepared/camera_models.json'),model=sha(root/'fit/model.json'),backend=sources),operation)
    return summary(root)


def texture_job(root,faces):
    root=Path(root).resolve();job,state=read(root)
    if state['stages'].get('fit',{}).get('status')!='DONE':raise ValueError('Complete the fit first')
    fit_job(root,root/'fit/annotations.json');job,state=read(root)
    models=json.loads((root/'prepared/camera_models.json').read_text());source=Path(faces).resolve();data=json.loads(source.read_text())
    if data.get('proxy_width')!=1600:raise ValueError('Texture corners use full unrotated1600px proxies')
    if not data.get('faces'):raise ValueError('No texture faces supplied')
    def operation(job,state):
        result=[];out=root/'textures';out.mkdir(exist_ok=True)
        for index,item in enumerate(data['faces']):
            name=item['camera_view'];camera=models[name]
            if item['source_image_sha256']!=camera['image_sha256']:raise ValueError('Texture photograph binding mismatch')
            if not camera['metric_eligible']:raise ValueError('Diagnostic-only camera cannot provide metric texture mapping')
            if item.get('normal_sign') not in (-1,1):raise ValueError('Texture normal_sign must be explicitly +1 or -1')
            origin=np.asarray(item['origin_m'],float);u=np.asarray(item['u_m'],float);v=np.asarray(item['v_m'],float)
            if any(a.shape!=(3,) for a in (origin,u,v)) or not np.isfinite([origin,u,v]).all() or min(np.linalg.norm(u),np.linalg.norm(v))<.001 or abs(u@v)>1e-8:
                raise ValueError('Texture aperture needs finite orthogonal metric axes')
            corners=np.asarray(item['pixels'],float);w,h=camera['image_size'];image=cv2.imread(camera['image'])
            if corners.shape!=(4,2) or not np.isfinite(corners).all() or (corners<0).any() or (corners[:,0]>=1600).any() or (corners[:,1]>=1600*h/w).any():raise ValueError('Invalid texture image corners')
            if abs(cv2.contourArea(corners.astype(np.float32)))<25:raise ValueError('Degenerate texture aperture')
            K=np.array(camera['K']);D=np.array(camera['D']);corners*=w/1600
            normalized=cv2.undistortPointsIter(corners[:,None,:],K,D,None,None,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,100,1e-10)).reshape(-1,2)
            H=cv2.getPerspectiveTransform(np.array([[0,0],[1,0],[1,1],[0,1]],np.float32),normalized.astype(np.float32))
            nw=1200;nh=max(48,min(1600,round(nw*np.linalg.norm(v)/np.linalg.norm(u))))
            uu,vv=np.meshgrid(np.linspace(0,1,nw),np.linspace(1,0,nh));rays=np.c_[uu.ravel(),vv.ravel(),np.ones(nw*nh)]@H.T
            if np.min(rays[:,2])*np.max(rays[:,2])<=0 or np.any(abs(rays[:,2])<1e-8):raise ValueError('Texture homography crosses infinity')
            rays=np.c_[rays[:,:2]/rays[:,2,None],np.ones(len(rays))]
            pixels=cv2.projectPoints(rays,np.zeros(3),np.zeros(3),K,D)[0].reshape(nh,nw,2).astype(np.float32)
            if not np.isfinite(pixels).all() or pixels[:,:,0].min()<0 or pixels[:,:,1].min()<0 or pixels[:,:,0].max()>=w-1 or pixels[:,:,1].max()>=h-1:
                raise ValueError('Rectified texture maps outside the source photograph')
            path=out/(f'face_{index}.jpg');cv2.imwrite(str(path),cv2.remap(image,pixels[:,:,0],pixels[:,:,1],cv2.INTER_LINEAR))
            result.append(dict(texture=str(path.resolve()),texture_sha256=sha(path),camera_view=name,
                source_image_sha256=camera['image_sha256'],origin_m=origin.tolist(),u_m=u.tolist(),v_m=v.tolist(),normal_sign=item['normal_sign']))
        save(root/'fit/textures.json',result);save(out/'face_annotations.json',data)
        return dict(planes=len(result),next_action='export candidate asset'),[root/'fit/textures.json',out/'face_annotations.json']+[Path(i['texture']) for i in result]
    run_stage(root,'texture',dict(faces=sha(source),model=sha(root/'fit/model.json'),cameras=sha(root/'prepared/camera_models.json')),operation)
    return summary(root)


def process_job(root,annotations=None,faces=None,draft=False):
    """One offline call for the stable workflow. Never captures or moves devices."""
    root=Path(root).resolve();job,state=read(root)
    if not state['captures']:
        state.update(status='NEEDS_INPUT',next_action='No accepted complete photo set. Devices are not queried or started; recover/capture only when explicitly available.')
        save(root/'state.json',state);return summary(root)
    prepare_job(root)
    if job['spec']['family']=='multiview_mesh':return fit_job(root,None)
    annotations=Path(annotations) if annotations else root/'fit/annotations.json'
    if not annotations.is_file():
        job,state=read(root);state.update(status='NEEDS_INPUT',next_action='Supply image-bound fit/validation landmark data')
        save(root/'state.json',state);return summary(root)
    fit_job(root,annotations);model=json.loads((root/'fit/model.json').read_text())
    if not model['image_consistency_passed'] and not draft:return summary(root)
    if faces is not None:texture_job(root,Path(faces))
    export_job(root,draft=draft);track_job(root)
    job,state=read(root)
    if model['image_consistency_passed']:
        state.update(status='DONE',next_action='Candidate exported. Read separate tracking/accuracy limits; no cell installation or robot action.')
        save(root/'state.json',state)
    return summary(root)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='operation',required=True)
    init=sub.add_parser('init');init.add_argument('--job',type=Path,required=True);init.add_argument('--workspace',type=Path,default=Path(os.environ.get('UWA_WS',Path.home()/'UWA_ws')))
    init.add_argument('--id',required=True);init.add_argument('--family',choices=FAMILIES,required=True);init.add_argument('--size-m',type=float,nargs=3,required=True)
    init.add_argument('--known-dimensions',type=Path);init.add_argument('--views-per-wrist',type=int,default=1)
    for name in ('status','ingest','capture','recover','prepare','fit','texture','export','track-check','run','envelope'):
        p=sub.add_parser(name);p.add_argument('--job',type=Path,required=True)
        if name=='ingest':p.add_argument('--manifest',type=Path,required=True)
        if name=='capture':p.add_argument('--telemetry-source',choices=('ros','rtde'),default='ros');p.add_argument('--new-view',action='store_true')
        if name=='fit':p.add_argument('--annotations',type=Path)
        if name=='export':p.add_argument('--draft',action='store_true')
        if name=='texture':p.add_argument('--faces',type=Path,required=True)
        if name=='run':
            p.add_argument('--annotations',type=Path);p.add_argument('--faces',type=Path);p.add_argument('--draft',action='store_true')
        if name=='envelope':
            p.add_argument('--oak-result',type=Path,required=True);p.add_argument('--support-pixel',type=float,nargs=2,required=True)
            p.add_argument('--proxy-width',type=int,default=1800);p.add_argument('--support-confirmed',action='store_true')
    args=parser.parse_args();cv2.setNumThreads(2)
    try:
        if args.operation=='init':result=create(args.job,args.workspace,args.id,args.family,args.size_m,
            json.loads(args.known_dimensions.read_text()) if args.known_dimensions else None,args.views_per_wrist)
        elif args.operation=='status':result=summary(args.job)
        else:
            with lock(args.job):
                if args.operation=='ingest':result=ingest(args.job,args.manifest)
                elif args.operation=='capture':result=capture(args.job,args.telemetry_source,args.new_view)
                elif args.operation=='recover':result=recover_job(args.job)
                elif args.operation=='envelope':
                    from .digitization_views import envelope
                    result=envelope(args.job,args.oak_result,args.support_pixel,args.proxy_width,support_confirmed=args.support_confirmed)
                elif args.operation=='prepare':result=prepare_job(args.job)
                elif args.operation=='export':result=export_job(args.job,args.draft)
                elif args.operation=='texture':result=texture_job(args.job,args.faces)
                elif args.operation=='track-check':result=track_job(args.job)
                elif args.operation=='run':result=process_job(args.job,args.annotations,args.faces,args.draft)
                else:
                    if args.annotations is None and read(args.job)[0]['spec']['family']!='multiview_mesh':raise ValueError('--annotations required')
                    result=fit_job(args.job,args.annotations)
        print(json.dumps(result,indent=2));return 0
    except Exception as error:
        print(json.dumps(dict(status='FAILED',error=str(error)),indent=2));return 1


if __name__=='__main__':sys.exit(main())

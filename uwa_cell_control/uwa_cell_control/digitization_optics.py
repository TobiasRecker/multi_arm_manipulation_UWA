"""Freeze per-photograph optics/board poses. No device clients or shape prior."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np

from .object_digitization import board_observation, in_anchor_board
from .board_photo_evaluation import pose_from_observation


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_optics(workspace,registry):
    from uwa_cell_description.configuration import load_layout
    ws=Path(workspace);profile=load_layout()['calibration'];result={}
    for name,item in registry['robots'].items():
        path=ws/item['file'];data=json.loads(path.read_text())
        result[name]=dict(K=data['camera_matrix'],D=data['distortion'],image_size=data['image_size'],
            focus=data['focus'],identity=item['identity'],source=str(path),source_sha256=sha(path),
            calibration_passed=data.get('passed'),metric_eligible=item['metric_default'],
            quality_note=item.get('note','Saved camera-specific native intrinsic profile'))
    factory=profile['overview_camera']['factory'];item=registry['oak4']
    result['oak4']=dict(K=factory['camera_matrix_8000x6000'],D=factory['distortion'],
        image_size=[8000,6000],focus=item['focus'],identity=factory['device_id'],
        source='factory optics in '+profile['profile_id'],source_sha256=profile['sha256'],
        calibration_passed=None,metric_eligible=item['metric_default'],quality_note=item['note'])
    return result


def check_optics(record,opt,image_size,camera):
    K=np.array(opt['K']);D=np.array(opt['D'])
    if (K.shape!=(3,3) or not np.isfinite(K).all() or not np.isfinite(D).all() or
            min(K[0,0],K[1,1])<=0 or list(image_size)!=opt['image_size']):
        raise ValueError('Invalid or mismatched native image optics: '+camera)
    if camera=='oak4':
        if record['camera_metadata']['standard']['lens_position']!=opt['focus']:raise ValueError('OAK focus mismatch')
    else:
        settings=record['settings_before']
        if (record['camera_identity']['uniqueCamId']!=opt['identity'] or
                settings['focusAuto'] or settings['focus']!=opt['focus']):
            raise ValueError('Physical camera/focus mismatch: '+camera)


def prepare(dataset,optics,board_config,output,policy):
    """Keep every image and every rejection; never replace missing poses by FK."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True);models={};failures={};warnings=[]
    for row in dataset['rounds']:
        observations={};records={}
        for entry in row['images']:
            name=entry['camera'];key=f"r{row['round']}_{name}";path=Path(entry['image'])
            try:
                if sha(path)!=entry['sha256']:raise ValueError('Source photograph changed')
                record=json.loads((path.parent/'record.json').read_text());image=cv2.imread(str(path))
                if image is None:raise ValueError('Cannot decode photograph')
                check_optics(record,optics[name],[image.shape[1],image.shape[0]],name)
                views={}
                for table in ('right','left'):
                    try:
                        obs=board_observation(image,board_config,table)
                        T,rms=pose_from_observation(obs,{k:np.array(optics[name][k]) for k in ('K','D')})
                        views[table]=(T,rms,obs)
                    except (ValueError,cv2.error):pass
                if not views:raise ValueError('No usable metric board visible')
                observations[key]=views;records[key]=(entry,record)
                proxy=cv2.resize(image,(1600,round(image.shape[0]*1600/image.shape[1])))
                cv2.imwrite(str(output/(key+'.jpg')),proxy)
            except Exception as error:failures[key]=str(error)
        # A simultaneous static scene permits an observed bridge from ANY view
        # seeing both boards. No nominal table transform enters this bridge.
        bridges=[(sum(v[t][1] for t in ('left','right')),v,k) for k,v in observations.items() if len(v)==2]
        best=min(bridges,key=lambda item:item[0]) if bridges else None
        bridge={t:best[1][t][0] for t in ('left','right')} if best else {}
        for key,observed in observations.items():
            entry,record=records[key];name=entry['camera'];preferred='right' if 'right' in observed else 'left'
            try:
                T,rms,obs=observed[preferred];anchored=in_anchor_board(T,preferred,'right',bridge)
                opt=optics[name]
                model=dict(**opt,image=entry['image'],image_sha256=entry['sha256'],
                    record_sha256=sha(Path(entry['image']).parent/'record.json'),round=row['round'],physical_camera=name,
                    reference='right_table_board',source_board=preferred,observation=obs,board_rms_px=rms,
                    T_camera_board=anchored.tolist(),
                    pose_source='direct observed board' if preferred=='right' else 'observed two-board bridge',
                    bridge_source=None if preferred=='right' else best[2])
                if rms>policy['board_rms_warning_native_px']:warnings.append(key+': high board reprojection RMS')
                if not opt['metric_eligible']:warnings.append(key+': retained as diagnostic, excluded from metric fit')
                if opt['calibration_passed'] is False:warnings.append(key+': original calibration failed; accepted status not rewritten')
                models[key]=model
            except ValueError as error:failures[key]=str(error)
    coverage={}
    for name in optics:
        centres=[]
        for c in models.values():
            if c['physical_camera']!=name:continue
            centre=np.linalg.inv(np.array(c['T_camera_board']))[:3,3]
            if not any(np.linalg.norm(centre-old)<.01 for old in centres):centres.append(centre)
        coverage[name]=len(centres)
    return dict(cameras=models,rejected_views=failures,warnings=warnings,
        unique_camera_centres_10mm=coverage,nominal_world_pose_used=False,
        absolute_accuracy_validated=False)

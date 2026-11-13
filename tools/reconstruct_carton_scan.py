"""Offline, image-only carton reconstruction from a frozen five-camera scan.

Run with the workspace Python/ROS import environment. No ROS nodes or device
clients are created. Native optics are explicitly frozen, not activated.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.sparse import lil_matrix

from uwa_cell_control.object_digitization import (
    board_observation, in_anchor_board, object_pose, project, vertices, save,
)
from uwa_cell_control.board_photo_evaluation import pose_from_observation
from uwa_cell_control.board_photo_evaluation import vector, from_vector


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(dataset, out, ws):
    from uwa_cell_description.configuration import load_layout
    layout = load_layout()
    profile = layout['calibration']
    sources = {
        'left_front': ('left_front_hd_20261112/intrinsics.json', '028E1F350009061C'),
        'left_rear': ('left_rear_hd_20261112/result_v2/intrinsics.json', '06561F1400090106'),
        'right_rear': ('right_rear_hd_20261112/result_v1/intrinsics.json', '01D1111A00090912'),
        'right_front': ('right_front_hd_20261112/evaluation_v1/diagnostic_intrinsics.json', '01D10E1900090912'),
    }
    optics = {}
    for name, (source, identity) in sources.items():
        path = ws / 'setup/calibration/hardware_handeye' / source
        intrinsic = json.loads(path.read_text())
        optics[name] = dict(K=intrinsic['camera_matrix'], D=intrinsic['distortion'],
            image_size=intrinsic['image_size'], focus=intrinsic['focus'], identity=identity,
            source=str(path), source_sha256=sha(path), calibration_passed=intrinsic.get('passed'),
            quality_note=('Operator accepted below threshold; not an automatic PASS' if name == 'right_front'
                          else 'Saved HD calibration; peripheral extrapolation not independently validated'))
    factory = profile['overview_camera']['factory']
    optics['oak4'] = dict(K=factory['camera_matrix_8000x6000'], D=factory['distortion'],
        image_size=[8000, 6000], focus=116, identity=factory['device_id'],
        source='factory EEPROM in profile '+profile['profile_id'],
        profile_sha256=profile['sha256'], calibration_passed=None,
        quality_note='Factory reference, no independent session intrinsic validation')
    data = json.loads(dataset.read_text())
    if not data['acquisition_complete']:
        raise ValueError('Incomplete acquisition')
    coarse = json.loads((ws/'setup/digitization/four_arm_scan_20261113/overview_estimate/estimate.json').read_text())
    params = coarse['parameters_board_m_rad']
    models = {}
    for row in data['rounds']:
        if not row['stationary_set_confirmed']:
            raise ValueError('Nonstationary set')
        bridge = {}
        for entry in sorted(row['images'], key=lambda e: e['camera'] != 'oak4'):
            name = entry['camera']; key = f"r{row['round']}_{name}"
            path = Path(entry['image']); record_path = path.parent/'record.json'
            record = json.loads(record_path.read_text())
            if sha(path) != entry['sha256'] or record['sha256'] != entry['sha256']:
                raise ValueError('Image hash mismatch: '+key)
            image = cv2.imread(str(path)); opt = optics[name]
            if image is None or [image.shape[1], image.shape[0]] != opt['image_size']:
                raise ValueError('Native image size mismatch: '+key)
            if name != 'oak4':
                settings = record['settings_before']
                if (record['camera_identity']['uniqueCamId'] != opt['identity'] or
                        settings['focusAuto'] or settings['focus'] != opt['focus']):
                    raise ValueError('Camera identity/focus mismatch: '+key)
            elif record['camera_metadata']['standard']['lens_position'] != opt['focus']:
                raise ValueError('OAK focus mismatch')
            observed = {}
            for table in ('right', 'left'):
                obs = board_observation(image, layout['charuco'], table)
                try:
                    pose, rms = pose_from_observation(obs, {k: np.asarray(opt[k]) for k in ('K','D')})
                    observed[table] = (pose, rms, obs)
                except (ValueError, cv2.error):
                    pass
            if name == 'oak4':
                bridge = {t: value[0].tolist() for t, value in observed.items()}
            # The carton occludes the left board in OAK. All four wrist views
            # still see the right board: prefer this direct common reference.
            preferred = 'right' if 'right' in observed else ('left' if entry['board_id'] == 'left_table_board' else 'right')
            if preferred not in observed:
                raise ValueError('Recorded metric reference lost: '+key)
            pose, rms, obs = observed[preferred]
            anchored = in_anchor_board(pose, preferred, 'right', bridge)
            camera = dict(**opt, image=str(path), image_sha256=sha(path), record_sha256=sha(record_path),
                round=row['round'], physical_camera=name, observation=obs,
                T_camera_board=anchored.tolist(), board_rms_px=rms,
                source_board=preferred, reference='right_table_board',
                observed_board_poses={t:dict(T_camera_board=p.tolist(),rms_px=r,observation=o) for t,(p,r,o) in observed.items()},
                pose_source=('Directly visible right board; no bridge/FK/handeye' if preferred == 'right'
                             else 'Visible left board and observed OAK bridge; no FK/handeye'))
            models[key] = camera
            proxy = cv2.resize(image, (1600,1200), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(out/(key+'.jpg')), proxy)
            try:
                points = project(vertices(params),camera,1600)
                for i,(x,y) in enumerate(points):
                    cv2.circle(proxy,(round(x),round(y)),5,(0,255,0),2)
                    cv2.putText(proxy,str(i),(round(x)+8,round(y)),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,0,255),2)
                cv2.imwrite(str(out/(key+'_initial.jpg')), proxy)
            except ValueError:
                pass
            print(key, 'reference', preferred, 'board RMS', round(rms,3), flush=True)
    save(out/'camera_models.json',models)
    save(out/'provenance.json',dict(dataset=str(dataset.resolve()), dataset_sha256=sha(dataset),
        image_count=len(models), hardware_commands=False, depth_used=False, global_calibration_changed=False,
        board_square_m=.04, print_scale_independently_measured=False, optics=optics))


def track_annotations(out):
    """Track reviewable first-round landmarks; do not synthesize observations."""
    seed=json.loads((out/'landmark_seeds.json').read_text())
    cameras=json.loads((out/'camera_models.json').read_text())
    rows={}
    for name, observation in seed['observations'].items():
        raw=np.asarray(observation['pixels'],np.float32)
        if observation.get('rotated_180'):
            raw=np.array([1599,1199],np.float32)-raw
        source=cv2.cvtColor(cv2.imread(str(out/f'r1_{name}.jpg')),cv2.COLOR_BGR2GRAY)
        for n in range(1,6):
            key=f'r{n}_{name}'
            if key not in cameras:continue
            dest=cv2.cvtColor(cv2.imread(str(out/(key+'.jpg'))),cv2.COLOR_BGR2GRAY)
            if n==1:
                points=raw.copy();ok=np.ones(len(raw),bool);fb=np.zeros(len(raw))
            else:
                points,good,_=cv2.calcOpticalFlowPyrLK(source,dest,raw[:,None,:],None,
                    winSize=(41,41),maxLevel=4,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,50,.001))
                back,reverse,_=cv2.calcOpticalFlowPyrLK(dest,source,points,None,
                    winSize=(41,41),maxLevel=4,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,50,.001))
                points=points.reshape(-1,2);fb=np.linalg.norm(back.reshape(-1,2)-raw,axis=1)
                ok=(good.ravel()!=0)&(reverse.ravel()!=0)&(fb<1.5)
            rows[key]=dict(ids=np.asarray(observation['ids'])[ok].tolist(),pixels=points[ok].tolist(),
                tracking_forward_backward_px=fb[ok].tolist(),rejected_ids=np.asarray(observation['ids'])[~ok].tolist(),
                role='validation' if n in (2,4) else 'fit')
            im=cv2.imread(str(out/(key+'.jpg')))
            for i,(x,y) in zip(rows[key]['ids'],rows[key]['pixels']):
                cv2.circle(im,(round(x),round(y)),5,(0,0,255),2)
                cv2.putText(im,str(i),(round(x)+7,round(y)),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,0,255),2)
            cv2.imwrite(str(out/(key+'_landmarks.jpg')),im)
    result=dict(proxy_width=1600,coordinate_convention='raw image pixels; no source image rotation',
        seed_sha256=sha(out/'landmark_seeds.json'),tracking='Pyramidal LK, round1 -> round N; forward/backward <=1.5proxy px',
        observations=rows)
    save(out/'landmarks.json',result)
    return result


def fit_model(out, ws):
    models=json.loads((out/'camera_models.json').read_text())
    annotation=json.loads((out/'landmarks.json').read_text())
    observations=annotation['observations'];width=annotation['proxy_width']
    initial=np.asarray(json.loads((ws/'setup/digitization/four_arm_scan_20261113/overview_estimate/estimate.json').read_text())['parameters_board_m_rad'])
    def fit(selected):
        def residual(value):
            points=vertices(value)
            return np.concatenate([(project(points[observations[k]['ids']],models[k],width)-observations[k]['pixels']).ravel()
                                   for k in selected])
        solution=least_squares(residual,initial,loss='soft_l1',f_scale=3,max_nfev=400,
            bounds=([-3,-3,-10,.1,.1,.05],[3,3,10,1,1,.5]),xtol=1e-11,ftol=1e-11,gtol=1e-10)
        if not solution.success:raise ValueError(solution.message)
        return solution.x
    training=[k for k,o in observations.items() if o['role']=='fit']
    params=fit(training)
    individual={name:fit([k for k in training if models[k]['physical_camera']==name]).tolist()
                for name in sorted({models[k]['physical_camera'] for k in training})}
    metrics={}
    for key,o in observations.items():
        errors=project(vertices(params)[o['ids']],models[key],width)-o['pixels']
        rms=float(np.sqrt(np.mean(np.sum(errors**2,axis=1))))
        metrics[key]=dict(role=o['role'],corners=len(errors),rms_proxy_px=rms,
            rms_native_px=rms*models[key]['image_size'][0]/width,board_rms_native_px=models[key]['board_rms_px'])
        im=cv2.imread(str(out/(key+'.jpg')))
        projection=project(vertices(params),models[key],width)
        for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
            cv2.line(im,tuple(np.round(projection[a]).astype(int)),tuple(np.round(projection[b]).astype(int)),(0,255,0),2)
        for x,y in o['pixels']:cv2.circle(im,(round(x),round(y)),5,(0,0,255),2)
        cv2.imwrite(str(out/(key+'_fit.jpg')),im)
    result=dict(schema=1,model='rectangular open tray envelope; contour refinement separate',
        parameters_board_m_rad=params.tolist(),length_m=params[3],width_m=params[4],height_m=params[5],
        T_board_object=object_pose(params).tolist(),metrics=metrics,individual_camera_fits=individual,
        absolute_accuracy_validated=False,landmark_sha256=sha(out/'landmarks.json'),camera_models_sha256=sha(out/'camera_models.json'),
        validation_rounds=[2,4],fit_rounds=[1,3,5],wall_thickness_m=.0025,wall_thickness_measured=False)
    save(out/'result.json',result)
    print(json.dumps(dict(parameters=params.tolist(),individual=individual,metrics=metrics),indent=2))


def refine(out, *, render=True):
    """Fixed-optics bundle adjustment, using only training object landmarks.

    Both observed boards constrain the cameras. Their relative transform is
    estimated from images (not nominal layout). Holdout poses use boards only.
    """
    models=json.loads((out/'camera_models.json').read_text())
    observations=json.loads((out/'landmarks.json').read_text())['observations']
    training=[k for k,o in observations.items() if o['role']=='fit' and
              models[k]['physical_camera']!='left_front' and (models[k]['physical_camera']!='oak4' or k=='r1_oak4')]
    initial=np.array(json.loads((out/'result.json').read_text())['parameters_board_m_rad'])
    relatives=[]
    for key in training:
        seen=models[key]['observed_board_poses']
        if 'left' in seen:
            relatives.append(np.linalg.inv(seen['right']['T_camera_board'])@seen['left']['T_camera_board'])
    bridge=np.eye(4);bridge[:3,:3]=Rotation.from_matrix([p[:3,:3] for p in relatives]).mean().as_matrix()
    bridge[:3,3]=np.median([p[:3,3] for p in relatives],axis=0)
    x0=np.r_[initial,vector(bridge),np.concatenate([vector(np.asarray(models[k]['T_camera_board'])) for k in training])]
    blocks=[]
    for j,key in enumerate(training):
        c=models[key]
        for table,reference in c['observed_board_poses'].items():
            o=reference['observation']
            blocks.append((j,key,table,np.array(o['object_points']),np.array(o['image_points']),
                           .9))  # native board pixel sigma; nominal residual weighting, not measured covariance
        o=observations[key]
        blocks.append((j,key,'carton',np.array(o['ids']),np.array(o['pixels']),3.))
    def residual(x,chosen_blocks=blocks):
        b=from_vector(x[6:12]);points=vertices(x[:6]);errors=[]
        for j,key,table,obj,pixels,sigma in chosen_blocks:
            c=models[key];pose=from_vector(x[12+6*j:18+6*j])
            if table=='left':pose=pose@b
            objects=points[obj] if table=='carton' else obj
            pp=cv2.projectPoints(objects,cv2.Rodrigues(pose[:3,:3])[0],pose[:3,3],np.array(c['K']),np.array(c['D']))[0].reshape(-1,2)
            if table=='carton':pp*=1600/c['image_size'][0]
            errors.extend(((pp-pixels)/sigma).ravel())
        return np.array(errors)
    n=sum(2*len(b[4]) for b in blocks);sparsity=lil_matrix((n,len(x0)),dtype=int);offset=0
    for j,key,table,obj,pixels,sigma in blocks:
        count=2*len(pixels);sparsity[offset:offset+count,12+6*j:18+6*j]=1
        if table=='carton':sparsity[offset:offset+count,:6]=1
        elif table=='left':sparsity[offset:offset+count,6:12]=1
        offset+=count
    fit=least_squares(residual,x0,loss='soft_l1',f_scale=2.,jac_sparsity=sparsity.tocsr(),
        x_scale='jac',max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-7)
    if not fit.success:raise ValueError('Bundle failed: '+fit.message)
    params=fit.x[:6];bridge=from_vector(fit.x[6:12]);refined={};metrics={}
    for key,c in models.items():
        if c['physical_camera']=='left_front':continue
        c={**c}
        if key in training:
            pose=from_vector(fit.x[12+6*training.index(key):18+6*training.index(key)])
            role='fit'
        else:
            # Strict holdout: solve pose from boards alone, never carton pixels.
            def board_errors(value):
                pose=from_vector(value);errors=[]
                for table,reference in c['observed_board_poses'].items():
                    bpose=pose@bridge if table=='left' else pose;o=reference['observation']
                    pp=cv2.projectPoints(np.array(o['object_points']),cv2.Rodrigues(bpose[:3,:3])[0],bpose[:3,3],np.array(c['K']),np.array(c['D']))[0].reshape(-1,2)
                    errors.extend(((pp-o['image_points'])/.9).ravel())
                return np.array(errors)
            solution=least_squares(board_errors,vector(np.array(c['T_camera_board'])),loss='soft_l1',f_scale=2.,max_nfev=100)
            if not solution.success:raise ValueError('Holdout board pose failed '+key)
            pose=from_vector(solution.x);role='validation'
        c['T_camera_board']=pose.tolist();refined[key]=c
        board_errors_px={}
        for table,reference in c['observed_board_poses'].items():
            bpose=pose@bridge if table=='left' else pose;o=reference['observation']
            pp=cv2.projectPoints(np.array(o['object_points']),cv2.Rodrigues(bpose[:3,:3])[0],bpose[:3,3],np.array(c['K']),np.array(c['D']))[0].reshape(-1,2)
            board_errors_px[table]=float(np.sqrt(np.mean(np.sum((pp-o['image_points'])**2,axis=1))))
        o=observations[key];errors=project(vertices(params)[o['ids']],c,1600)-o['pixels']
        rms=float(np.sqrt(np.mean(np.sum(errors**2,axis=1))))
        metrics[key]=dict(role=role,landmarks=len(errors),rms_proxy_px=rms,
            rms_native_px=rms*c['image_size'][0]/1600,board_rms_native_px=board_errors_px,
            pose_used_carton_observations=role=='fit')
    result=dict(schema=2,parameters_board_m_rad=params.tolist(),length_m=params[3],width_m=params[4],height_m=params[5],
        T_board_object=object_pose(params).tolist(),T_right_board_left_board=bridge.tolist(),metrics=metrics,
        excluded_metric_cameras={'left_front':'Native intrinsic extrapolation inconsistent: independent views imply ~370x299x136mm vs ~400-432x319-357x158-165mm; board PnP RMS3.6-8.7px in round1. No intrinsic replacement or flag rewrite.'},
        method='Robust joint fixed-optics bundle of visible metric board corners and assisted carton envelope landmarks; right board anchor; both-board geometry estimated from training photos',
        fit_views=training,board_sigma_native_px=.9,landmark_sigma_proxy_px=3.,
        optimizer=dict(message=fit.message,evaluations=fit.nfev,success=bool(fit.success)),
        measured_accuracy_validated=False,wall_thickness_m=.0025,wall_thickness_measured=False,
        assumptions=['40mm board squares printed at1:1','bottom coplanar with reference board','rectangular footprint and vertical walls','thickness2.5mm assumed','hidden underside not observed'],
        source_hashes={p:sha(out/p) for p in ('camera_models.json','landmarks.json')})
    save(out/'refined_camera_models.json',refined);save(out/'refined_result.json',result)
    if not render:return result
    for key,c in refined.items():
        im=cv2.imread(str(out/(key+'.jpg')));pp=project(vertices(params),c,1600)
        for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
            cv2.line(im,tuple(np.round(pp[a]).astype(int)),tuple(np.round(pp[b]).astype(int)),(0,255,0),2)
        for x,y in observations[key]['pixels']:cv2.circle(im,(round(x),round(y)),5,(0,0,255),2)
        cv2.putText(im,metrics[key]['role'].upper(),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),3)
        cv2.imwrite(str(out/(key+'_refined.jpg')),im)
    print(json.dumps(dict(params=params.tolist(),optimizer=result['optimizer'],metrics=metrics),indent=2))
    return result


def contours(out):
    """Intersect explicit, reviewable wall-edge pixels with fitted wall planes."""
    cameras=json.loads((out/'refined_camera_models.json').read_text())
    r=json.loads((out/'refined_result.json').read_text());T=np.array(r['T_board_object']);inverse=np.linalg.inv(T)
    L,W,H=[r[k] for k in ('length_m','width_m','height_m')]
    source=json.loads((out/'contour_seeds.json').read_text());panels={}
    for name,o in source['panels'].items():
        c=cameras[o['camera']];pixels=np.array(o['pixels'],float)
        if o.get('rotated_180'):pixels=np.array([1599,1199])-pixels
        native=pixels*c['image_size'][0]/1600
        xy=cv2.undistortPointsIter(native[:,None,:],np.array(c['K']),np.array(c['D']),None,None,
            (cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,100,1e-10)).reshape(-1,2)
        camera_object=inverse@np.linalg.inv(np.array(c['T_camera_board']))
        origin=camera_object[:3,3];rays=np.c_[xy,np.ones(len(xy))]@camera_object[:3,:3].T
        axis=1 if name in ('front','back') else 0
        constant={'front':0,'back':W,'left':0,'right':L}[name]
        distance=(constant-origin[axis])/rays[:,axis]
        if np.any(distance<=0):raise ValueError('Wall behind camera')
        points=origin+distance[:,None]*rays;s=points[:,1-axis];z=points[:,2]
        # Wall endpoints are a rectangular model convention. Keep the measured
        # normalized cutout locations; preserve unclamped intersections too.
        extent=L if axis==1 else W
        if s[0]>s[-1]:s=s[::-1];z=z[::-1]
        fractions=(s-s[0])/(s[-1]-s[0])
        # A traced vertical grip edge can lean by a pixel. Keep its order and
        # collapse tiny reversals to a vertical edge instead of making a spike.
        fractions=np.maximum.accumulate(np.clip(fractions,0,1))
        top=np.c_[fractions*extent,np.clip(z,.02,H)]
        panels[name]=dict(camera=o['camera'],axis=axis,constant_m=constant,
            extent_m=extent,raw_intersections_object_m=points.tolist(),
            top_profile_m=top.tolist(),endpoint_normalization=True,
            source_pixels_raw_proxy=pixels.tolist())
        # A rectified picture of each observed planar panel, useful for review.
        nw=1400;nh=round(nw*H/extent);sx=np.linspace(0,extent,nw);zz=np.linspace(H,0,nh)
        ss,zgrid=np.meshgrid(sx,zz);obj=np.zeros((nh,nw,3));obj[:,:,axis]=constant
        obj[:,:,1-axis]=ss;obj[:,:,2]=zgrid
        board=obj.reshape(-1,3)@T[:3,:3].T+T[:3,3]
        pp=project(board,c,c['image_size'][0]).reshape(nh,nw,2).astype(np.float32)
        image=cv2.imread(c['image']);texture=cv2.remap(image,pp[:,:,0],pp[:,:,1],cv2.INTER_LINEAR)
        cv2.imwrite(str(out/(name+'_texture.jpg')),texture)
        review=texture.copy();profile=top.copy();profile[:,0]*=(nw-1)/extent;profile[:,1]=(H-profile[:,1])*(nh-1)/H
        cv2.polylines(review,[np.round(profile).astype(np.int32)],False,(0,0,255),3)
        cv2.imwrite(str(out/(name+'_profile.jpg')),review)
    r.update(panels=panels,model='open carton with four image-derived polygonal wall-top contours',
        contour_source_sha256=sha(out/'contour_seeds.json'),
        contour_limitations=['Panel plane assumption; endpoint normalized and heights clipped to envelope',
            'Cutout profiles traced in one training view per wall, not independent multi-view detail triangulation',
            'Creases, perforations, staples, texture relief and folded corner reinforcements not modeled'])
    save(out/'carton_model.json',r)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['prepare','track','fit','refine','contours'])
    p.add_argument('--workspace',type=Path,default=Path(__file__).resolve().parents[3])
    p.add_argument('--dataset',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.operation=='prepare':
        prepare(args.dataset.resolve(),args.output.resolve(),args.workspace.resolve())
    elif args.operation=='track':track_annotations(args.output.resolve())
    elif args.operation=='fit':fit_model(args.output.resolve(),args.workspace.resolve())
    elif args.operation=='refine':refine(args.output.resolve())
    else:contours(args.output.resolve())


if __name__=='__main__':
    main()

"""Image-only, assisted reconstruction of a supported rectangular tray.

No device/ROS writers and no depth data. Geometry is constrained to a support
plane and a rectangular box. Image landmarks remain explicit/reviewable.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def prepare_capture(capture,output):
    """Freeze image-specific optics and independently observed metric board poses."""
    from uwa_cell_description.configuration import load_layout
    from uwa_cell_gazebo.charuco import make_board
    from .hardware_charuco import observe
    from .board_photo_evaluation import pose_from_observation
    capture=Path(capture).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((capture/'manifest.json').read_text())
    if manifest.get('all_captured') is not True:raise ValueError('Three successful original photos required')
    layout=load_layout();profile=layout['calibration']
    context=json.loads((capture.parent/'calibration_context.json').read_text())
    if context['profile_sha256']!=profile['sha256']:
        raise ValueError('Active calibration changed since capture; select/freeze its original optics explicitly')
    board=make_board(layout['charuco'],'right');models={}
    for name in ('oak4','right_front','right_rear'):
        record=json.loads((capture/name/'record.json').read_text())
        path=capture/name/record['image']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Original image hash mismatch: '+name)
        image=cv2.imread(str(path));observation=observe(image,layout['charuco'],'right');observation.pop('annotated')
        if observation['corners']<4:
            params=cv2.aruco.DetectorParameters();params.cornerRefinementMethod=cv2.aruco.CORNER_REFINE_SUBPIX
            detected,ids,_=cv2.aruco.ArucoDetector(board.getDictionary(),params).detectMarkers(image)
            known={int(i):np.asarray(p).reshape(4,3) for i,p in zip(board.getIds().ravel(),board.getObjPoints())}
            objects=[];pixels=[];used=[]
            if ids is not None:
                for corners,index in zip(detected,ids.ravel()):
                    if int(index) in known:
                        objects.extend(known[int(index)].tolist());pixels.extend(corners.reshape(4,2).tolist());used.append(int(index))
            observation.update(corners=len(objects),object_points=objects,image_points=pixels,
                               reference_type='aruco_marker_corners',marker_ids=used)
        else:observation['reference_type']='charuco_chess_corners'
        camera={'image':str(path),'observation':observation,'profile_id':profile['profile_id'],
                'profile_sha256':profile['sha256'],'metric_usable':False,'metric_pose_source':'visible right-table board; no robot FK'}
        if name=='oak4':
            factory=profile['overview_camera']['factory']
            focus=record['camera_metadata']['standard']['lens_position']
            if focus!=factory['factory_calibration_lens_position']:
                raise ValueError('OAK photograph focus differs from its factory intrinsic reference')
            optics={'K':np.asarray(factory['camera_matrix_8000x6000']),'D':np.asarray(factory['distortion'])}
            if observation['image_size']!=[8000,6000]:raise ValueError('OAK native8K mode required')
            camera['intrinsics_status']='factory reference; not independently validated for this session'
        else:
            intrinsic=profile['robots'][name].get('camera');settings=record['settings_before']
            if (not intrinsic or intrinsic['image_size']!=observation['image_size'] or
                    settings['focusAuto'] or intrinsic['focus']!=settings['focus']):
                camera['reason']='No matching native image-size/manual-focus intrinsic profile'
                models[name]=camera
                continue
            optics={'K':np.asarray(intrinsic['camera_matrix']),'D':np.asarray(intrinsic['distortion'])}
            camera['intrinsics_status']=profile['robots'][name]['quality_status']['intrinsics']
        pose,rms=pose_from_observation(observation,optics)
        camera.update(K=optics['K'].tolist(),D=optics['D'].tolist(),T_camera_board=pose.tolist(),
                      board_rms_px=rms,metric_usable=True)
        models[name]=camera
    save(output/'camera_models.json',models)
    save(output/'preparation.json',{'schema':1,'capture_manifest':str(capture/'manifest.json'),
        'capture_manifest_sha256':hashlib.sha256((capture/'manifest.json').read_bytes()).hexdigest(),
        'reference':'right-table ChArUco board,40mm squares; print scale assumed correct',
        'metric_cameras':[name for name,model in models.items() if model['metric_usable']],
        'depth_used':False,'new_camera_calibration':False,'hardware_commands':False})
    return models


def vertices(parameters):
    x,y,yaw,length,width,height=np.asarray(parameters,float)
    if not np.isfinite(parameters).all() or min(length,width,height)<=0:
        raise ValueError('Tray dimensions must be finite and positive')
    points=np.array([[0,0,0],[length,0,0],[length,width,0],[0,width,0],
                     [0,0,-height],[length,0,-height],[length,width,-height],[0,width,-height]],float)
    c,s=np.cos(yaw),np.sin(yaw)
    points[:,:2]=points[:,:2]@np.array([[c,s],[-s,c]])+[x,y]
    return points


def object_pose(parameters):
    """Right-handed CAD frame: +Z up, origin at fitted bottom corner3."""
    x,y,yaw,length,width,height=np.asarray(parameters,float)
    c,s=np.cos(yaw),np.sin(yaw)
    return np.array([[c,s,0,x-width*s],[s,-c,0,y+width*c],
                     [0,0,-1,0],[0,0,0,1.]])


def project(points,camera,annotation_width):
    transform=np.asarray(camera['T_camera_board'],float)
    local=np.asarray(points)@transform[:3,:3].T+transform[:3,3]
    if np.any(local[:,2]<=0):
        raise ValueError('Object is behind a camera')
    pixels=cv2.projectPoints(np.asarray(points,float),cv2.Rodrigues(transform[:3,:3])[0],
        transform[:3,3],np.asarray(camera['K'],float),np.asarray(camera['D'],float))[0].reshape(-1,2)
    return pixels*annotation_width/camera['observation']['image_size'][0]


def plane_point(pixel,camera,annotation_width):
    transform=np.linalg.inv(np.asarray(camera['T_camera_board'],float))
    native=np.asarray(pixel,float)*camera['observation']['image_size'][0]/annotation_width
    ray=np.r_[cv2.undistortPoints(native.reshape(1,1,2),np.asarray(camera['K'],float),
                                np.asarray(camera['D'],float)).ravel(),1.]
    direction=transform[:3,:3]@ray;origin=transform[:3,3]
    if abs(direction[2])<1e-8:raise ValueError('View ray parallel to support plane')
    distance=-origin[2]/direction[2]
    if distance<=0:raise ValueError('Support plane behind camera')
    return origin+distance*direction


def solve(cameras,annotations,*,sensitivity_draws=80):
    width=annotations['proxy_width'];observations=annotations['observations']
    selected=annotations['metric_cameras']
    if len(set(selected))<2:raise ValueError('At least two calibrated views required')
    for name in selected:
        camera=cameras[name];observation=observations[name]
        if not all(key in camera for key in ('K','D','T_camera_board')):
            raise ValueError('Metric camera has no matching intrinsics/board pose: '+name)
        ids=observation['ids'];pixels=np.asarray(observation['pixels'],float)
        if (len(ids)<4 or len(set(ids))!=len(ids) or set(ids)-set(range(8)) or
                pixels.shape!=(len(ids),2) or not np.isfinite(pixels).all()):
            raise ValueError('Invalid box landmark correspondences')
    centres=[np.linalg.inv(cameras[name]['T_camera_board'])[:3,3] for name in selected]
    if max(np.linalg.norm(a-b) for a in centres for b in centres)<.02:
        raise ValueError('Degenerate views: camera baseline below20mm')
    first=selected[0];ids=observations[first]['ids'];pixels=observations[first]['pixels']
    if not {2,3}<=set(ids):raise ValueError('Reference view requires visible support corners2 and3')
    d=plane_point(pixels[ids.index(3)],cameras[first],width)
    c=plane_point(pixels[ids.index(2)],cameras[first],width)
    direction=c-d;length=np.linalg.norm(direction[:2]);yaw=np.arctan2(direction[1],direction[0])
    side=np.array([-np.sin(yaw),np.cos(yaw)])
    initial=np.r_[d[:2]-.08*side,yaw,length,.08,.06]
    lower=[-3,-3,-10,.02,.005,.005];upper=[3,3,10,3,2,1.5]
    def residual(parameters,obs=observations):
        points=vertices(parameters)
        return np.concatenate([(project(points[obs[name]['ids']],cameras[name],width)-
            np.asarray(obs[name]['pixels'])).ravel() for name in selected])
    fit=least_squares(residual,initial,bounds=(lower,upper),loss='soft_l1',f_scale=2.,max_nfev=300,
                      ftol=1e-11,xtol=1e-11,gtol=1e-10)
    if not fit.success or not np.isfinite(fit.x).all():raise ValueError('Box fit failed: '+fit.message)
    singular=np.linalg.svd(fit.jac,compute_uv=False)
    if singular[-1]<=1e-7 or singular[-1]/singular[0]<1e-7:
        raise ValueError('Degenerate box fit; capture better separated views')
    points=vertices(fit.x);metrics={}
    for name in selected:
        delta=project(points[observations[name]['ids']],cameras[name],width)-np.asarray(observations[name]['pixels'])
        rms=float(np.sqrt(np.mean(np.sum(delta**2,axis=1))))
        metrics[name]={'landmarks':len(delta),'fit_rms_at_annotation_width_px':rms,
            'fit_rms_native_px':rms*cameras[name]['observation']['image_size'][0]/width,
            'board_pose_rms_native_px':cameras[name]['board_rms_px']}
    # This sensitivity measures annotation noise only; no claim of absolute
    # accuracy or a full confidence interval for uncertain camera calibration.
    rng=np.random.default_rng(441);draws=[]
    for _ in range(sensitivity_draws):
        perturbed={name:{**observations[name],'pixels':(np.asarray(observations[name]['pixels'])+
                     rng.normal(0,2,np.asarray(observations[name]['pixels']).shape)).tolist()} for name in selected}
        result=least_squares(lambda p:residual(p,perturbed),fit.x,bounds=(lower,upper),loss='soft_l1',f_scale=2.,max_nfev=100)
        if result.success:draws.append(result.x[3:])
    fractions=[];partition_metrics=[]
    for divider in annotations.get('dividers',[]):
        def partition_points(fraction):
            b=vertices(fit.x);return np.array([b[4]+float(fraction)*(b[5]-b[4]),b[7]+float(fraction)*(b[6]-b[7])])
        def errors(value):
            return np.concatenate([(project(partition_points(value[0]),cameras[name],width)-
                np.asarray(pixels)).ravel() for name,pixels in divider['pixels'].items()])
        result=least_squares(errors,[divider['initial_fraction']],bounds=([.03],[.97]),loss='soft_l1',f_scale=2.)
        fractions.append(float(result.x[0]));partition_metrics.append(float(np.sqrt(np.mean(errors(result.x)**2))))
    if fractions!=sorted(fractions):raise ValueError('Divider positions must be ordered')
    thickness=float(annotations.get('assumed_wall_thickness_m',.0025))
    if not 0<thickness<min(fit.x[3:])/4:raise ValueError('Invalid assumed wall thickness')
    if fractions and min(np.diff([0.,*fractions,1.]))*fit.x[3]<=2*thickness:
        raise ValueError('Divider material overlaps an adjacent divider or end wall')
    per_camera={}
    for name in selected:
        one=least_squares(lambda p:(project(vertices(p)[observations[name]['ids']],cameras[name],width)-
            np.asarray(observations[name]['pixels'])).ravel(),fit.x,bounds=(lower,upper),loss='soft_l1',f_scale=2.)
        per_camera[name]=(one.x[3:]*1000).tolist()
    return {'schema':1,'model':'open_rectangular_tray','image_only':True,'depth_used':False,
        'parameters_board_m_rad':fit.x.tolist(),'vertices_board_m':points.tolist(),
        'T_board_object':object_pose(fit.x).tolist(),
        'length_m':float(fit.x[3]),'width_m':float(fit.x[4]),'height_m':float(fit.x[5]),
        'divider_fractions':fractions,'divider_fit_coordinate_rms_proxy_px':partition_metrics,
        'wall_thickness_m':thickness,'wall_thickness_source':'assumed; not independently resolved from images',
        'fit_metrics':metrics,'metric_cameras':selected,
        'uncalibrated_review_cameras':[n for n in cameras if n not in selected],
        'fit_independent_validation':False,'single_view_dimensions_mm':per_camera,
        'annotation_sensitivity':{'draws':len(draws),'sigma_proxy_px':2.,
            'dimensions_p05_mm':(np.percentile(draws,5,axis=0)*1000).tolist() if draws else [],
            'dimensions_p95_mm':(np.percentile(draws,95,axis=0)*1000).tolist() if draws else [],
            'scope':'annotation-only perturbation; does not include calibration, support-plane or cardboard deformation uncertainty'},
        'assumptions':['Box bottom rests on visible right-table board plane',
            'Opposite walls parallel, corners rectangular and walls vertical',
            'Rigid stationary object during unsynchronized exposures',
            'Constant wall/bottom/divider thickness is assumed',
            'Folds, staples, labels, corrugation and local warping are not reconstructed'],
        'absolute_accuracy_validated':False}


def solid_parts(result):
    """Disjoint axis-aligned slabs in object frame, metres, local+Z up."""
    length,width,height=(result[k] for k in ('length_m','width_m','height_m'));t=result['wall_thickness_m']
    parts=[('bottom',[0,0,0],[length,width,t]),('wall_y0',[0,0,t],[length,t,height-t]),
        ('wall_y1',[0,width-t,t],[length,t,height-t]),('end_x0',[0,t,t],[t,width-2*t,height-t]),
        ('end_x1',[length-t,t,t],[t,width-2*t,height-t])]
    for index,fraction in enumerate(result['divider_fractions']):
        parts.append((f'divider_{index+1}',[fraction*length-t/2,t,t],[t,width-2*t,height-t]))
    return parts


def overlays(cameras,annotations,result,output):
    width=annotations['proxy_width'];points=vertices(result['parameters_board_m_rad'])
    for name in result['metric_cameras']:
        original=cv2.imread(cameras[name]['image']);height=round(original.shape[0]*width/original.shape[1])
        im=cv2.resize(original,(width,height),interpolation=cv2.INTER_AREA);uv=project(points,cameras[name],width)
        for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
            cv2.line(im,tuple(np.rint(uv[a]).astype(int)),tuple(np.rint(uv[b]).astype(int)),(20,245,20),2)
        for fraction in result['divider_fractions']:
            endpoints=np.array([points[4]+fraction*(points[5]-points[4]),points[7]+fraction*(points[6]-points[7])])
            ends=project(endpoints,cameras[name],width);cv2.line(im,tuple(np.rint(ends[0]).astype(int)),tuple(np.rint(ends[1]).astype(int)),(255,180,20),3)
        for pixel in annotations['observations'][name]['pixels']:
            cv2.circle(im,tuple(np.rint(pixel).astype(int)),4,(0,0,255),-1)
        cv2.putText(im,'IMAGE-BASED APPROXIMATION | green: fitted | red: selected points',(20,40),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,0,0),4)
        cv2.putText(im,'IMAGE-BASED APPROXIMATION | green: fitted | red: selected points',(20,40),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
        cv2.imwrite(str(output/(name+'-overlay.jpg')),im)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-set',type=Path,help='Prepare image-specific camera models from a saved three-camera set')
    parser.add_argument('--cameras',type=Path)
    parser.add_argument('--landmarks',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.capture_set:
        models=prepare_capture(args.capture_set,args.output)
        print(json.dumps({name:{key:camera.get(key) for key in ('metric_usable','board_rms_px','reason')} for name,camera in models.items()},indent=2))
        return
    if not args.cameras or not args.landmarks:parser.error('Fit requires --cameras and --landmarks')
    cameras=json.loads(args.cameras.read_text());annotations=json.loads(args.landmarks.read_text());result=solve(cameras,annotations)
    result['input_sha256']={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.cameras,args.landmarks]}
    result['source_images']={name:{'file':camera['image'],'sha256':hashlib.sha256(Path(camera['image']).read_bytes()).hexdigest()} for name,camera in cameras.items()}
    result['solid_parts']=solid_parts(result);save(args.output/'reconstruction.json',result)
    overlays(cameras,annotations,result,args.output)
    print(json.dumps({key:result[key] for key in ('length_m','width_m','height_m','divider_fractions','fit_metrics','annotation_sensitivity')},indent=2))


if __name__=='__main__':main()

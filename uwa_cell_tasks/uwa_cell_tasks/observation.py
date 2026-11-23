"""Image-only observation worker; simulator truth never enters pose estimation."""
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from uwa_cell_gazebo.charuco_views import Chain
from match_cooperative_handling.rigid_object import pose_error
from .core import ARMS,CAMERAS,seal,write_json


def rendered_static_pose(estimator,frames,K,D,records):
    """Only our timestamp-audited noiseless renderer may repeat pixels."""
    from uwa_cell_tracking.static import static_pose
    hashes=[hashlib.sha256(np.ascontiguousarray(frame).tobytes()).hexdigest() for frame in frames]
    if len(set(hashes))>=3:return static_pose(estimator,frames,K,D)
    stamps=[r['stamp'] for r in records]
    if (len(frames)<3 or len(records)!=len(frames)
            or not all(r.get('environment') in ('own_gazebo_renderer','own_gazebo_snapshot_renderer') for r in records)
            or not np.isfinite(stamps).all() or not all(b>a for a,b in zip(stamps,stamps[1:]))):
        raise ValueError('Repeated pixels need advancing own-renderer source stamps')
    result=estimator.register(frames[-1],K,D)
    result.reason+='; noiseless renderer; unique source stamps, one image information content'
    return result


class OakFeatureFallback:
    """Try stretched descriptors, then fit their matches in native pixels."""

    def __init__(self, estimator):
        self.estimator = estimator

    def register(self, image, K, D, stamp=0.):
        import cv2
        from uwa_cell_tracking.core import estimate

        started = time.perf_counter()
        original = self.estimator.register(image, K, D, stamp=stamp)
        if original.status != 'LOST' or original.reason != 'No reliable global/panel pose hypothesis':
            return original

        height, width = image.shape[:2]
        native_threshold = 4. / min(1., self.estimator.width / width)
        for factor in (1.5, 1.3, 1.7):
            stretched_height = round(factor * height)
            scale = stretched_height / height
            # cv2.resize maps pixel centers as (v + 0.5) * scale - 0.5.
            offset = (scale - 1.) / 2
            transform = np.array([[1., 0., 0.], [0., scale, offset], [0., 0., 1.]])
            stretched = cv2.resize(image, (width, stretched_height), interpolation=cv2.INTER_LINEAR)
            candidate = self.estimator.register(stretched, transform @ K, D, stamp=stamp)
            if candidate.status == 'LOST':
                continue
            if candidate.status == 'AMBIGUOUS':
                return candidate

            native_pixels = candidate.pixels.copy()
            native_pixels[:, 1] = (native_pixels[:, 1] - offset) / scale
            refined = estimate(candidate.points, native_pixels, K, D, threshold=native_threshold)
            if refined.status == 'LOST':
                continue
            refined.reason += f'; vertical feature stretch {factor:.1f}, refit in native pixels'
            refined.source_stamp = float(stamp)
            refined.processing_ms = (time.perf_counter() - started) * 1000
            return refined
        return original


def observe(sim,description,reference,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    reference_meta=json.loads(Path(reference).with_suffix('.json').read_text())
    scene=json.loads((sim.directory/'scene.json').read_text())
    if (reference_meta['asset_id']!=scene['asset_id'] or reference_meta['asset_manifest_sha256']!=scene['asset_manifest_sha256']):
        raise ValueError('Image reference belongs to a different asset revision')
    from std_srvs.srv import Trigger
    records=[]
    minimum_stamp=sim.now()
    deadline=time.monotonic()+30.
    while not records and time.monotonic()<deadline:
        sim.check_cancel()
        try:batch=json.loads(sim.call('capture',Trigger.Request(),timeout=35.).message)
        except RuntimeError as error:
            if 'WAITING for' not in str(error):raise
            time.sleep(.1);continue
        if any(r.get('snapshot_physics_stamp',-1)<minimum_stamp-.02 for r in batch):
            raise RuntimeError('Renderer snapshot predates the stationary inspection')
        for record in batch:
            arm=record['arm']
            if arm == 'oak_usb':
                record['T_world_camera'] = scene['T_world_external_optical']['oak_usb']
            elif arm == 'oak':
                record['T_world_camera'] = scene['T_world_overview_optical']
            else:
                record['T_world_camera'] = Chain(description, 'world', arm+'_wrist_camera_optical_frame').forward(
                    record['snapshot_physics_joint_positions']).tolist()
        records=batch
    if not records:raise RuntimeError('No fresh calibrated camera images')
    write_json(directory/'inputs.json',records)
    command=[sys.executable,'-m','uwa_cell_tasks.observation','--inputs',str(directory/'inputs.json'),
             '--reference',str(reference),'--output',str(directory/'result.json')]
    if scene['cfg'].get('seek_contact'):
        worker(directory/'inputs.json',reference,directory/'result.json',scene['seek_support_height_m'])
    else:
        result=subprocess.run(command,capture_output=True,text=True,timeout=30.)
        if result.returncode:raise RuntimeError('Image worker failed: '+result.stderr[-1000:])
    observation=json.loads((directory/'result.json').read_text())
    if observation['status']!='VALID':raise RuntimeError('Visual localization '+observation['status']+': '+observation['reason'])
    age=sim.now()-observation['source_stamp']
    if age<-.02 or age>scene['cfg']['maximum_observation_age_s']:
        raise RuntimeError('Visual observation expired or has a future source stamp')
    return observation


def fit_supported_pose(result, image_width, estimator_width, T_world_camera, K, D, support_height_m):
    """Refit the visible carton standing on the fixture's right tabletop."""
    import cv2
    from scipy.optimize import least_squares

    free_pose = T_world_camera @ result.T_camera_object
    camera_world = np.linalg.inv(T_world_camera)
    threshold = 4. / min(1., estimator_width / image_width)

    def camera_pose(params):
        x, y, yaw = params
        c, s = np.cos(yaw), np.sin(yaw)
        return camera_world @ np.array([[c, -s, 0., x], [s, c, 0., y],
                                        [0., 0., 1., support_height_m], [0., 0., 0., 1.]])

    def pixels_error(params):
        pose = camera_pose(params)
        projected = cv2.projectPoints(result.points, cv2.Rodrigues(pose[:3,:3])[0],
                                      pose[:3,3], K, D)[0].reshape(-1,2)
        return projected - result.pixels

    initial = [*free_pose[:2,3], np.arctan2(free_pose[1,0],free_pose[0,0])]
    model = least_squares(lambda p: pixels_error(p).ravel(), initial, loss='soft_l1', f_scale=2.)
    errors = np.linalg.norm(pixels_error(model.x), axis=1)
    inliers = errors <= threshold
    if not model.success or int(inliers.sum()) < 24:
        raise ValueError('Fewer than 24 accepted native image points for the supported carton pose')
    result.T_camera_object = camera_pose(model.x)
    result.inliers = int(inliers.sum())
    result.rms_px = float(np.sqrt(np.mean(errors[inliers]**2)))
    result.reason += '; table-supported XY/yaw refit from native image points'
    return free_pose.tolist()


def worker(inputs,reference,output,support_height_m=None):
    import cv2
    from uwa_cell_tracking.core import TexturePose
    from uwa_cell_tracking.static import static_pose
    from uwa_cell_tracking.cli import record,annotate
    cv2.setNumThreads(2)
    records=json.loads(Path(inputs).read_text())

    def localize(arm):
        selected=[r for r in records if r['arm']==arm]
        if len(selected)<3:return None
        if any(r['K']!=selected[0]['K'] or r['D']!=selected[0]['D'] for r in selected):
            raise ValueError('Camera calibration changed during static burst')
        estimator=TexturePose(Path(reference),width=2400)
        if arm=='oak' and support_height_m is not None:estimator=OakFeatureFallback(estimator)
        frames=[np.load(r['image'],allow_pickle=False) for r in selected]
        K=np.array(selected[-1]['K']).reshape(3,3);D=np.array(selected[-1]['D'])
        result=rendered_static_pose(estimator,frames,K,D,selected)
        T_world_camera=np.asarray(selected[-1]['T_world_camera'])
        free_pose = None
        if arm=='oak' and support_height_m is not None and result.status=='VALID':
            try:
                free_pose=fit_supported_pose(result, frames[-1].shape[1], 2400, T_world_camera, K, D, support_height_m)
            except ValueError as error:
                result.status='LOST';result.reason=str(error)
        data=record(result);data.update(arm=arm,source_stamp=selected[-1].get('snapshot_physics_stamp',selected[-1]['stamp']),
            renderer_source_stamp=selected[-1]['stamp'],renderer_clock_domain=selected[-1].get('clock_domain','physical_world'))
        if result.status=='VALID':data['T_world_object']=(T_world_camera@result.T_camera_object).tolist()
        if free_pose is not None:data['T_world_object_unconstrained']=free_pose
        cv2.imwrite(str(Path(output).parent/(arm+'-inspection.jpg')),annotate(frames[-1],result,K,D))
        return data

    with ThreadPoolExecutor(max_workers=len(CAMERAS)) as workers:
        views=[result for result in workers.map(localize,CAMERAS) if result is not None]
    valid=[v for v in views if v['status']=='VALID']
    if not valid:answer=dict(status='LOST',reason='No camera passed image-only localization',views=views)
    else:
        best=min(valid,key=lambda v:v['reprojection_rms_px'])
        disagreement=any(pose_error(v['T_world_object'],best['T_world_object'])[0]>.003 or
                         pose_error(v['T_world_object'],best['T_world_object'])[1]>.02 for v in valid)
        answer=dict(status='AMBIGUOUS' if disagreement else 'VALID',reason='Cross-camera disagreement' if disagreement else 'Static calibrated image burst',
            T_world_object=best['T_world_object'],source_stamp=best['source_stamp'],views=views,
            source='image_only_tracking',absolute_accuracy_validated=False)
    write_json(output,seal(answer));return answer


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--reference',required=True);p.add_argument('--output',required=True)
    p.add_argument('--support-height-m',type=float)
    args=p.parse_args();worker(args.inputs,args.reference,args.output,args.support_height_m)

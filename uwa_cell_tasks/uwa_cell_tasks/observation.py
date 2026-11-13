"""Image-only observation worker; simulator truth never enters pose estimation."""
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from uwa_cell_gazebo.charuco_views import Chain
from match_cooperative_handling.rigid_object import pose_error
from .core import ARMS,CAMERAS,seal,write_json


def observe(sim,description,reference,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    sim.wait(lambda:all(abs(sim.v.get(j,1))<.003 for j in sim.q if '_robotiq_' not in j),10.,health=True)
    baseline=dict(sim.q);records=[];seen={a:None for a in CAMERAS};counts={a:0 for a in CAMERAS}
    deadline=time.monotonic()+12.
    while min(counts.values())<3 and time.monotonic()<deadline:
        sim.health()
        if any(abs(sim.q.get(j,1e9)-q)>.001 for j,q in baseline.items() if '_robotiq_' not in j):
            raise RuntimeError('Arm moved during static image inspection')
        for arm in CAMERAS:
            msg=sim.images.get(arm);info=sim.infos.get(arm)
            if msg is None or info is None or counts[arm]>=3:continue
            stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
            if stamp==seen[arm] or not 0<=sim.now()-stamp<=1.:continue
            if (msg.header.frame_id!=info.header.frame_id or [msg.width,msg.height]!=[info.width,info.height]
                    or msg.encoding not in ('rgb8','bgr8')):continue
            seen[arm]=stamp
            image=np.frombuffer(msg.data,np.uint8).reshape(msg.height,msg.step)[:,:msg.width*3].reshape(msg.height,msg.width,3)
            if msg.encoding=='rgb8':image=image[:,:,::-1]
            path=directory/f'{arm}-{counts[arm]}.npy';np.save(path,image)
            camera_pose=(json.loads((sim.directory/'scene.json').read_text())['T_world_overview_optical'] if arm=='oak'
                else Chain(description,'world',msg.header.frame_id).forward(baseline).tolist())
            records.append(dict(arm=arm,image=str(path.resolve()),K=list(info.k),D=list(info.d),stamp=stamp,T_world_camera=camera_pose))
            counts[arm]+=1
        time.sleep(.02)
    if not records:raise RuntimeError('No fresh calibrated camera images')
    write_json(directory/'inputs.json',records)
    command=[sys.executable,'-m','uwa_cell_tasks.observation','--inputs',str(directory/'inputs.json'),
             '--reference',str(reference),'--output',str(directory/'result.json')]
    result=subprocess.run(command,capture_output=True,text=True,timeout=30.)
    if result.returncode:raise RuntimeError('Image worker failed: '+result.stderr[-1000:])
    observation=json.loads((directory/'result.json').read_text())
    if observation['status']!='VALID':raise RuntimeError('Visual localization '+observation['status']+': '+observation['reason'])
    if sim.now()-observation['source_stamp']>5.:raise RuntimeError('Visual observation expired during processing')
    return observation


def worker(inputs,reference,output):
    import cv2
    from uwa_cell_tracking.core import TexturePose
    from uwa_cell_tracking.static import static_pose
    from uwa_cell_tracking.cli import record,annotate
    cv2.setNumThreads(2);estimator=TexturePose(Path(reference));views=[]
    records=json.loads(Path(inputs).read_text())
    for arm in CAMERAS:
        selected=[r for r in records if r['arm']==arm]
        if len(selected)<3:continue
        if any(r['K']!=selected[0]['K'] or r['D']!=selected[0]['D'] for r in selected):
            raise ValueError('Camera calibration changed during static burst')
        frames=[np.load(r['image'],allow_pickle=False) for r in selected]
        K=np.array(selected[-1]['K']).reshape(3,3);D=np.array(selected[-1]['D'])
        result=static_pose(estimator,frames,K,D);data=record(result);data.update(arm=arm,source_stamp=selected[-1]['stamp'])
        if result.status=='VALID':data['T_world_object']=(np.array(selected[-1]['T_world_camera'])@result.T_camera_object).tolist()
        cv2.imwrite(str(Path(output).parent/(arm+'-inspection.jpg')),annotate(frames[-1],result,K,D));views.append(data)
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
    args=p.parse_args();worker(args.inputs,args.reference,args.output)

"""OAK-grounded conservative scan envelope, not a reconstructed object model."""
import json
from pathlib import Path
from itertools import product
import cv2
import numpy as np
import yaml

from .digitization_optics import sha
from .object_digitization import plane_point,project
from .board_photo_evaluation import pose_from_observation
from .hardware_charuco import observe
from uwa_cell_description.configuration import load_layout
from uwa_cell_gazebo.charuco import table_board_transform


def envelope(job,oak_result,support_pixel,proxy_width=1800,centre_allowance=.05,support_confirmed=False):
    if not support_confirmed:raise ValueError('Object support height must be confirmed before using a tabletop plane')
    if not 0<centre_allowance<=.25:raise ValueError('Invalid planning allowance')
    job=Path(job);spec=json.loads((job/'job.json').read_text())['spec'];source=json.loads(Path(oak_result).read_text())
    image_path=Path(source['images']['standard']);meta=json.loads(Path(source['metadata']).read_text());image=cv2.imread(str(image_path))
    layout=load_layout();factory=layout['calibration']['overview_camera']['factory']
    if image is None or [image.shape[1],image.shape[0]]!=[8000,6000]:raise ValueError('Expected native OAK photograph')
    if meta['standard']['lens_position']!=116 or str(meta['device_id'])!=str(factory['device_id']):raise ValueError('OAK identity/focus mismatch')
    pixel=np.asarray(support_pixel,float)
    if pixel.shape!=(2,) or not np.isfinite(pixel).all() or (pixel<0).any() or pixel[0]>=proxy_width or pixel[1]>=proxy_width*.75:raise ValueError('Invalid support-plane pixel')
    available=[]
    for table in ('right','left'):
        try:
            observation=observe(image,layout['charuco'],table);observation.pop('annotated',None)
            T,rms=pose_from_observation(observation,dict(K=np.array(factory['camera_matrix_8000x6000']),D=np.array(factory['distortion'])))
            available.append((rms,table,T,observation))
        except (ValueError,cv2.error):pass
    if not available:raise ValueError('No visible board for metric planning reference')
    rms,table,T,observation=min(available,key=lambda item:item[0])
    camera=dict(K=factory['camera_matrix_8000x6000'],D=factory['distortion'],T_camera_board=T.tolist(),observation=observation)
    point=plane_point(pixel,camera,proxy_width);B=table_board_transform(layout['charuco'],table)
    table_point=(B@np.r_[point,1])[:3]
    size=np.array(spec['user_rough_dimensions_m']);xy=float(np.linalg.norm(size[:2])+2*centre_allowance)
    height=float(size[2]*1.1+.04)
    repo=Path(json.loads((job/'job.json').read_text())['workspace'])/'src/multi_arm_manipulation_UWA'
    design=yaml.safe_load((repo/'config/digitization/object_scan.yaml').read_text())
    design.update(reference_frame=table+'_table_top',centre_m=[float(table_point[0]),float(table_point[1]),float(table_point[2]+height/2)],size_m=[xy,xy,height],
        yaw_rad=0.,geometry_source='user rough size and reviewed OAK support-centre ray; collision envelope only',
        horizontal_distances_m=[.65,.8,.95],heights_above_centre_m=[.15,.3,.45],
        azimuth_offsets_deg=[0,-20,20],keep_per_arm=3,target_extra_views_per_arm=2,
        extra_camera_orbit_deg=[-12,12,-20,20],extra_max_joint_change_rad=.7,
        extra_camera_xy_offsets_m=[[.06,0],[-.06,0],[0,.06],[0,-.06]])
    out=job/'planning';out.mkdir(exist_ok=True)
    report=dict(schema=1,source_image=str(image_path),source_image_sha256=sha(image_path),metadata_sha256=sha(source['metadata']),
        support_pixel= pixel.tolist(),proxy_width=proxy_width,reference_table=table,board_rms_native_px=rms,
        T_camera_board=T.tolist(),support_point_board_m=point.tolist(),support_point_table_m=table_point.tolist(),
        centre_allowance_m=centre_allowance,allowance_is_statistical_bound=False,
        known_dimensions_source='user rough dimensions; support height confirmed by user',
        calibration_profile_sha256=layout['calibration']['sha256'],design=design,hardware_commands=False,
        limitations=['Pixel is reviewed rough footprint centre, not an automatic object segmentation',
            'Square horizontal envelope covers unknown yaw plus design allowance; not measured CAD',
            'Board/table/world calibration remains provisional; no cable/person model'])
    (out/'envelope.json').write_text(json.dumps(report,indent=2)+'\n');(out/'scan_geometry.yaml').write_text(yaml.safe_dump(design,sort_keys=False))
    centre=np.array(design['centre_m']);half=np.array(design['size_m'])/2
    table_corners=np.array(list(product(*zip(centre-half,centre+half))));board_corners=(np.linalg.inv(B)@np.c_[table_corners,np.ones(8)].T).T[:,:3]
    pp=project(board_corners,camera,proxy_width);preview=cv2.resize(image,(proxy_width,round(proxy_width*.75)))
    for i,a in enumerate(pp):
        for j,b in enumerate(pp):
            if i<j and bin(i^j).count('1')==1:cv2.line(preview,tuple(np.rint(a).astype(int)),tuple(np.rint(b).astype(int)),(0,180,255),3)
    cv2.rectangle(preview,(0,0),(proxy_width,76),(0,0,0),-1)
    cv2.putText(preview,'PLANNING ENVELOPE / NOT CAD / NO MOTION',(18,48),cv2.FONT_HERSHEY_SIMPLEX,1.,(255,255,255),2)
    cv2.imwrite(str(out/'envelope_review.jpg'),preview)
    return dict(report=str(out/'envelope.json'),config=str(out/'scan_geometry.yaml'),reference=table,board_rms_native_px=rms,size_m=design['size_m'])

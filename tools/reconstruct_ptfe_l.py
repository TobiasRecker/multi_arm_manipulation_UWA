"""Assisted metric reconstruction of two perpendicular PTFE plates (offline).

Known from operator: 10mm plates, 20x20mm supports. No box geometry/poses
are reused. Board-camera bundle adjustment is shared with the earlier tool.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
import reconstruct_carton_scan as shared
from uwa_cell_control.object_digitization import project,save

PROFILE=.02
PLATE=.01


def object_pose(parameters):
    x,y,yaw,width,depth,height=np.asarray(parameters,float);c,s=np.cos(yaw),np.sin(yaw)
    return np.array([[c,s,0,x],[s,-c,0,y],[0,0,-1,0],[0,0,0,1.]])


def local_vertices(parameters):
    _,_,_,W,D,H=np.asarray(parameters,float);b=PROFILE+PLATE
    return np.array([[0,b,b],[W,b,b],[W,b+D,b],[0,b+D,b],[0,b,H+b],[W,b,H+b],
                     [0,0,0],[W,0,0],[0,0,H+b],[W,0,H+b],[0,D+b,0],[W,D+b,0]])


def vertices(parameters):
    T=object_pose(parameters);return local_vertices(parameters)@T[:3,:3].T+T[:3,3]


def observations(out):
    seeds=json.loads((out/'landmark_seeds.json').read_text());result={}
    for key,o in seeds['observations'].items():
        pixels=np.asarray(o['pixels'],float)
        if o.get('rotated_180'):pixels=np.array([1599,1199])-pixels
        result[key]=dict(ids=o['ids'],pixels=pixels.tolist(),role=o['role'])
    data=dict(proxy_width=1600,observations=result,source='Explicit physical white plate corners, raw image coordinates')
    save(out/'landmarks.json',data);return result


def fit(out):
    cameras=json.loads((out/'camera_models.json').read_text());obs=observations(out)
    first='r1_oak4';c=cameras[first];o=obs[first]
    transform=np.linalg.inv(np.array(c['T_camera_board']));K=np.array(c['K']);D=np.array(c['D'])
    ground=[]
    for index in (3,2):
        pixel=np.array(o['pixels'][o['ids'].index(index)])*c['image_size'][0]/1600
        ray=np.r_[cv2.undistortPointsIter(pixel[None,None,:],K,D,None,None,
            (cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,100,1e-10)).ravel(),1.]
        direction=transform[:3,:3]@ray;origin=transform[:3,3]
        ground.append(origin+(-.03-origin[2])/direction[2]*direction)
    v=ground[1]-ground[0];yaw=np.arctan2(v[1],v[0]);W=np.linalg.norm(v[:2]);D0=.15
    xy=ground[0][:2]-(D0+.03)*np.array([np.sin(yaw),-np.cos(yaw)])
    initial=np.r_[xy,yaw,W,D0,.18]
    def solve(keys,start):
        def residual(value):
            return np.concatenate([(project(vertices(value)[obs[k]['ids']],cameras[k],1600)-obs[k]['pixels']).ravel() for k in keys])
        result=least_squares(residual,start,bounds=([-2,-2,-10,.08,.03,.04],[2,2,10,.8,.6,.6]),
            loss='soft_l1',f_scale=2,max_nfev=400,ftol=1e-11,xtol=1e-11,gtol=1e-10)
        if not result.success:raise ValueError(result.message)
        return result.x
    initial=solve([first],initial)
    keys=[k for k,o in obs.items() if o['role']=='fit' and cameras[k]['physical_camera']!='left_front']
    parameters=solve(keys,initial)
    save(out/'result.json',dict(parameters_board_m_rad=parameters.tolist(),initial_oak_parameters=initial.tolist(),
        known_profile_m=PROFILE,known_plate_m=PLATE,known_dimensions_source='user supplied, not independently measured'))
    refined=shared.refine(out,render=False,vertices_fn=vertices,object_pose_fn=object_pose)
    parameters=np.array(refined['parameters_board_m_rad'])
    refined.update(model='perpendicular PTFE plate assembly with external20mm supports',
        width_m=parameters[3],base_plate_depth_m=parameters[4],upright_plate_height_m=parameters[5],
        dimensions_m=[parameters[3],parameters[4]+.03,parameters[5]+.03],
        profile_cross_section_m=[PROFILE,PROFILE],plate_thickness_m=PLATE,
        measured_dimensions_source='user reports20x20mm profiles,10mm plates; overall sizes from images',
        excluded_metric_cameras={'left_front':'Native intrinsic/board inconsistency: right4.54px/left8.42px RMS in these images; diagnostic only'},
        assumptions=['rigid90degree L, perpendicular planar plates','base20mm profile plus10mm plate above support plane',
            'profile placement inferred from visible frame; hidden underside approximate','profile internal slots and plate perforations not measured'],
        method='robust fixed-optics multi-view plate fit and board-camera bundle; no prior object pose',
        wall_thickness_m=None,wall_thickness_measured=False)
    save(out/'assembly_result.json',refined)
    models=json.loads((out/'refined_camera_models.json').read_text())
    for key,c in models.items():
        image=cv2.imread(c['image']);image=cv2.resize(image,(1600,1200));pp=project(vertices(parameters),c,1600)
        for a,b in [(0,1),(1,2),(2,3),(3,0),(0,4),(4,5),(5,1)]:
            cv2.line(image,tuple(np.round(pp[a]).astype(int)),tuple(np.round(pp[b]).astype(int)),(0,255,0),2)
        for index,(x,y) in zip(obs[key]['ids'],obs[key]['pixels']):
            cv2.circle(image,(round(x),round(y)),4,(0,0,255),2)
            cv2.putText(image,str(index),(round(x)+5,round(y)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
        if c['physical_camera'] in ('left_rear','right_front'):image=cv2.rotate(image,cv2.ROTATE_180)
        cv2.imwrite(str(out/(key+'_fit.jpg')),image)
    print(json.dumps(dict(dimensions_m=refined['dimensions_m'],metrics=refined['metrics']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();fit(args.output.resolve())

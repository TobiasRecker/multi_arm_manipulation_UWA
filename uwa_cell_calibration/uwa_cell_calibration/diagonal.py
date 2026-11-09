"""Diagonal cohorts, explicit parking and phase-independent geometric separation.

Each arm's path is checked in the full MoveIt scene. Conservative swept boxes
enclose every collision shape; disjoint expanded boxes make the two planned
paths independent of relative progress (including one arm holding position).
"""
from functools import lru_cache
from itertools import product,permutations
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from uwa_cell_gazebo.charuco import transform
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_gazebo.configuration import ROBOT_IDS,joint_names
from .planner import generate_plan,timed_path

DIAGONALS=(('left_front','right_rear'),('left_rear','right_front'))
ENVELOPE_MARGIN_M=.08


def cohorts(ids):
    return [[r for r in pair if r in ids] for pair in DIAGONALS if any(r in ids for r in pair)]


@lru_cache(maxsize=64)
def mesh_bounds(filename):
    if filename.startswith('package://'):
        from ament_index_python.packages import get_package_share_directory
        package,relative=filename[len('package://'):].split('/',1)
        path=Path(get_package_share_directory(package))/relative
    else:path=Path(filename.removeprefix('file://'))
    raw=path.read_bytes()
    count=int.from_bytes(raw[80:84],'little')
    if len(raw)==84+count*50:
        dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
        points=np.frombuffer(raw,dtype=dtype,offset=84,count=count)['vertices'].reshape(-1,3)
    elif raw.lstrip().startswith(b'solid'):
        points=np.array([list(map(float,line.split()[1:])) for line in raw.decode().splitlines() if line.strip().startswith('vertex ')])
    else:raise ValueError(f'Cannot certify collision-mesh envelope: {path}')
    if not len(points) or not np.isfinite(points).all():raise ValueError('Invalid collision mesh')
    return points.min(axis=0),points.max(axis=0)


class ArmEnvelopes:
    def __init__(self,model):
        self.model=model;self.shapes={r:[] for r in ROBOT_IDS}
        root=ET.fromstring(model.description)
        for rid in ROBOT_IDS:
            for link in root.findall('link'):
                if not link.get('name').startswith(model.prefix+rid+'_'):continue
                for collision in link.findall('collision'):
                    geometry=collision.find('geometry');shape=list(geometry)[0]
                    if shape.tag=='mesh':
                        lo,hi=mesh_bounds(shape.get('filename'))
                        scale=np.fromstring(shape.get('scale','1 1 1'),sep=' ')
                        values=np.array([lo*scale,hi*scale]);lo,hi=values.min(axis=0),values.max(axis=0)
                    elif shape.tag=='box':
                        hi=np.fromstring(shape.get('size'),sep=' ')/2;lo=-hi
                    elif shape.tag=='cylinder':
                        hi=np.array([float(shape.get('radius'))]*2+[float(shape.get('length'))/2]);lo=-hi
                    elif shape.tag=='sphere':hi=np.full(3,float(shape.get('radius')));lo=-hi
                    else:raise ValueError('Unsupported collision geometry for parallel paths')
                    corners=np.array(list(product(*zip(lo,hi))))
                    origin=collision.find('origin')
                    local=transform(np.fromstring(origin.get('xyz','0 0 0'),sep=' '),
                                    np.fromstring(origin.get('rpy','0 0 0'),sep=' ')) if origin is not None else np.eye(4)
                    points=corners@local[:3,:3].T+local[:3,3]
                    self.shapes[rid].append((link.get('name'),points))

    def at_current_state(self,rid):
        points=[]
        for link,corners in self.shapes[rid]:
            t=np.asarray(self.model.state.get_global_link_transform(link))
            points.append(corners@t[:3,:3].T+t[:3,3])
        all_points=np.concatenate(points)
        return np.array([all_points.min(axis=0),all_points.max(axis=0)])


def coordinated_paths(model,start,targets):
    ids=list(targets)
    if not ids or len(ids)>2 or not any(set(ids)<=set(pair) for pair in DIAGONALS):
        raise ValueError('Only a single arm or one diagonal cohort may move together')
    # First find the shared duration without issuing or accepting a ROS goal.
    duration=max(max(1.,1.875*np.max(abs(np.array(targets[r])-[start[j] for j in joint_names(r)]))/.1,
                     np.sqrt(5.774*np.max(abs(np.array(targets[r])-[start[j] for j in joint_names(r)]))/.2)) for r in ids)
    paths={r:timed_path(model,r,start,targets[r],duration=duration) for r in ids}
    separation=None;boxes={}
    if len(ids)==2:
        envelopes=getattr(model,'arm_envelopes',None)
        if envelopes is None:model.arm_envelopes=envelopes=ArmEnvelopes(model)
        for rid,path in paths.items():
            bounds=[];q=dict(start)
            for point in path:
                q.update(zip(joint_names(rid),point['positions']))
                # Other arm held at its starting pose; all static/parked obstacles
                # are checked above. The boxes certify all relative progress.
                model.check(q)
                bounds.append(envelopes.at_current_state(rid))
            boxes[rid]=np.array([np.min([b[0] for b in bounds],axis=0),np.max([b[1] for b in bounds],axis=0)])
        a,b=(boxes[r] for r in ids)
        separation=float(np.linalg.norm(np.maximum(0,np.maximum(a[0]-b[1],b[0]-a[1]))))
        if separation<2*ENVELOPE_MARGIN_M:
            raise ValueError(f'Diagonal swept envelopes too close ({separation:.3f} m); parallel motion rejected')
    return {'paths':paths,'duration':duration,'envelope_separation_m':separation,
            'envelope_margin_per_arm_m':ENVELOPE_MARGIN_M,'envelopes':{r:b.tolist() for r,b in boxes.items()}}


def parking_poses(model,layout,start):
    result={}
    centres={name:Chain(model.description,'world',model.prefix+name+'_table_top').forward({})[:3,3] for name in layout['tables']}
    middle=np.mean(list(centres.values()),axis=0)
    for rid in ROBOT_IDS:
        names=joint_names(rid);q0=np.array([start[j] for j in names])
        chain=Chain(model.description,'world',model.prefix+rid+'_wrist_camera_optical_frame')
        base=Chain(model.description,'world',model.prefix+rid+'_base_link').forward({})[:3,3]
        outward=centres[layout['robots'][rid]['table']]-middle;outward[2]=0;outward/=np.linalg.norm(outward)
        nominal=chain.forward(start);solutions=[]
        bounds=np.array([model.bounds[j] for j in names]).T
        for offset,height in product((.25,.35),(.5,.65)):
            target=nominal.copy();target[:3,3]=base+outward*offset+[0,0,height]
            def residual(q):
                actual=chain.forward(dict(zip(names,q)))
                # Parking has no viewing-orientation constraint. Keeping joints
                # near their current values avoids needless wrist/base turns.
                return np.r_[actual[:3,3]-target[:3,3],.025*(q-q0)]
            for seed in (q0,q0+np.array([.4,0,0,0,0,0]),q0-np.array([.4,0,0,0,0,0])):
                fit=least_squares(residual,np.clip(seed,bounds[0]+1e-6,bounds[1]-1e-6),bounds=bounds,max_nfev=100)
                if np.linalg.norm(chain.forward(dict(zip(names,fit.x)))[:3,3]-target[:3,3])>.03:continue
                try:path=timed_path(model,rid,start,fit.x)
                except ValueError:continue
                solutions.append((path[-1]['time'],fit.x.tolist()))
        if not solutions:raise ValueError(f'{rid}: no collision-checked parking pose reachable from session start')
        result[rid]=min(solutions,key=lambda p:p[0])[1]
    return result


def prepare_schedule(model,layout,start,matrices,ids,count,diagonal_pairs=True,progress=lambda p:None):
    if not diagonal_pairs:
        plans=generate_plan(model,layout,start,matrices,ids,count,progress)
        stages=[]
        for rid in ids:
            stages.extend([{'kind':'measure','robots':[rid]},
                           {'kind':'returning','robot':rid,'target':[start[j] for j in joint_names(rid)]}])
        return {'plans':plans,'stages':stages,'parking':{},'mode':'sequential'}
    parks=parking_poses(model,layout,start);state=dict(start);stages=[];plans={}
    def reposition(rid,target,kind):
        if np.max(abs(np.asarray(target)-[state[j] for j in joint_names(rid)]))<.001:return
        path=timed_path(model,rid,state,target)
        stages.append({'kind':kind,'robot':rid,'target':target,'duration':path[-1]['time']})
        state.update(zip(joint_names(rid),target))
    for pair in cohorts(ids):
        for rid in ROBOT_IDS:
            if rid not in pair:reposition(rid,parks[rid],'parking')
        # A previous stopped session may have left these arms parked. Use the
        # configured board-view posture as a planning reference, never require
        # a parked camera to see the board before it can be repositioned.
        for rid in pair:reposition(rid,list(layout['robots'][rid]['initial_positions']),'positioning')
        group=generate_plan(model,layout,state,matrices,pair,count,progress)
        plans.update(group);certificates=[]
        for index in range(count):
            targets={r:group[r]['poses'][index]['joints'] for r in pair}
            checked=coordinated_paths(model,state,targets)
            certificates.append({'duration':checked['duration'],'envelope_separation_m':checked['envelope_separation_m']})
            for r,target in targets.items():state.update(zip(joint_names(r),target))
        stages.append({'kind':'measure','robots':pair,'certificates':certificates})
    # Prefer a direct serial return order. Additional parking is only needed if
    # no direct order is collision-free; all intermediate states are checked.
    orders=[tuple(pair+[r for r in ROBOT_IDS if r not in pair])]+list(permutations(ROBOT_IDS))
    for order in orders:
        trial=dict(state);returns=[]
        try:
            for rid in order:
                target=[start[j] for j in joint_names(rid)]
                if np.max(abs(np.asarray(target)-[trial[j] for j in joint_names(rid)]))<.001:continue
                path=timed_path(model,rid,trial,target)
                returns.append({'kind':'returning','robot':rid,'target':target,'duration':path[-1]['time']})
                trial.update(zip(joint_names(rid),target))
        except ValueError:continue
        stages.extend(returns);state=trial;break
    else:
        for rid in ROBOT_IDS:reposition(rid,parks[rid],'parking')
        for rid in ROBOT_IDS:reposition(rid,[start[j] for j in joint_names(rid)],'returning')
    return {'plans':plans,'stages':stages,'parking':parks,'mode':'diagonal_pairs',
            'envelope_margin_per_arm_m':ENVELOPE_MARGIN_M}

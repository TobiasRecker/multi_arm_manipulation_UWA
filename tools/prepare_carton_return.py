#!/usr/bin/env python3
"""Offline open-jaw retreat/home from measured encoders and current carton pose."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'uwa_cell_tasks'))
from uwa_cell_motion.common import config,joint_names,dump
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.carton_paths import cartesian_entry,evaluate,joint_segment
from uwa_cell_gazebo.charuco_views import Chain
from prepare_carton_open_entry import open_model
from run_carton_open_entry import timed_primitive


def home_near(q,bounds):
    nominal=np.array([0.,-np.pi/2,0.,-np.pi/2,0.,0.]);result=[]
    for value,wanted,(lo,hi)in zip(q,nominal,bounds):
        choices=[wanted+2*np.pi*k for k in range(-2,3)if lo<=wanted+2*np.pi*k<=hi]
        if not choices:raise ValueError('Home outside joint bounds')
        result.append(min(choices,key=lambda x:abs(x-value)))
    return result


class ReturnProblem(HardwareProblem):
    def check(self,request,q,*,margin=True):
        return super().check(request,q,margin=margin) and self.current_open.check(self.state(request,q))[0]


def prepare(a):
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cfg=config(a.config);binding=json.loads(a.object_pose.read_text());scene=json.loads(a.contact_scene.read_text());obs=json.loads(a.observations.read_text())
    p=ReturnProblem(out/'model',cfg,a.inventory);p.chains={r:Chain(p.original_description,'world',r+'_tool0')for r in p.names}
    start={}
    for arm,names in p.names.items():
        row=obs['arms'][arm]
        if row.get('observed')is not True or row.get('stationary_observed')is not True:raise ValueError(arm+': stationary measurement missing')
        s=row['samples'][-1]
        if s['robot_mode']!=7 or s['safety_mode']!=1:raise ValueError(arm+': native state unsuitable')
        start.update(zip(names[:6],s['actual_q']));start.update({j:0. for j in names[6:]})
    if a.after_retreat:
        future=json.loads(a.after_retreat.read_text())
        if a.operation!='home'or not future.get('success')or future.get('motion_kind')!='unloaded_retreat':raise ValueError('Successful explicit future retreat required')
        start=dict(future['final_positions'])
    evidence=out/'evidence.json'
    dump(evidence,dict(artifact_type='offline_hardware_open_return_evidence',configuration=cfg,
        inputs={k:dict(path=str(v.resolve()),sha256=hashlib.sha256(v.read_bytes()).hexdigest())for k,v in [('object_pose',a.object_pose),('contact_scene',a.contact_scene)]}))
    inputs=[evidence,a.object_pose,a.contact_scene,a.observations,a.config,a.inventory,Path(__file__)]
    if a.after_retreat:inputs.append(a.after_retreat)
    report=dict(success=False,executable=False,motion_kind='unloaded_'+a.operation,base_signature=p.signature,
        planned_only=bool(a.after_retreat),start_kind='PLANNED_AFTER_RETREAT_NOT_CURRENT'if a.after_retreat else 'MEASURED_STATIONARY_ENCODERS',
        inputs={str(v.resolve()):hashlib.sha256(v.read_bytes()).hexdigest()for v in inputs},segments=[],
        arm_commands=[],finger_commands=[],loaded_motion=False,home_definition='[0,-90,0,-90,0,0]deg, nearest equivalent winding within physical bounds')
    try:
        for arm in ['right_front','right_rear']:
            p.current_open=open_model(p,binding,scene,arm,out/('open-'+arm));q0=np.array([start[j]for j in joint_names(arm)]);T=p.chains[arm].forward(start)
            if a.operation=='retreat':
                primitive=cartesian_entry(p,arm,start,T,q0,pregrasp_m=.15)
                primitive['positions']=primitive['positions'][::-1];primitive['kind']='CARTESIAN_UP'
                qend=primitive['positions'][-1]
                parts=[('RETREAT',primitive)]
            else:
                # Home is authorized only after the open fingers are above the
                # carton, and the entire subsequent path is collision checked.
                top=float(np.array(binding['T_world_object_candidate'])[2,3])+.1633108564
                if T[2,3]<top+.20:raise ValueError(arm+': retreat before Home')
                qend=home_near(q0,[p.collision.bounds[j]for j in joint_names(arm)])
                primitive=joint_segment(q0,qend)
                request=p.normalize(dict(start=start,goals={arm:qend}))
                parts=[('HOME',primitive)]
                if not all(p.check(request,q)for q in evaluate(primitive,np.linspace(0,1,257))):
                    # First take the upright Home shape at the current base
                    # angle, then rotate that compact upright arm to Home.
                    # The direct diagonal path can violate neighbor margins.
                    raised=np.array(qend);raised[0]=q0[0]
                    parts=[('HOME_RAISE',joint_segment(q0,raised)),('HOME_BASE',joint_segment(raised,qend))]
            for name,primitive in parts:
                q0=[start[j]for j in joint_names(arm)];qend=primitive['positions'][-1];request=p.normalize(dict(start=start,goals={arm:qend}))
                if not p.check(request,qend):raise ValueError(arm+'/'+name+': invalid endpoint')
                u=np.linspace(0,1,257)
                for _ in range(8):
                    qs=evaluate(primitive,u)
                    if np.max(abs(np.diff(qs,axis=0)))<=.005:break
                    u=np.linspace(0,1,len(u)*2-1)
                else:raise ValueError('Return sampling bound')
                for phase,q in zip(u,qs):
                    if not p.check(request,q):raise ValueError(f'{arm}/{name}: return collision at {phase}')
                    if a.operation=='retreat':
                        actual=p.chains[arm].forward(dict(start,**dict(zip(joint_names(arm),q))));wanted=T.copy();wanted[2,3]+=.15*(10*phase**3-15*phase**4+6*phase**5)
                        if np.linalg.norm(actual[:3,3]-wanted[:3,3])>1e-4 or Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).magnitude()>1e-3:raise ValueError('Upward Cartesian line error')
                trajectory=timed_primitive(primitive,q0)
                report['segments'].append(dict(arm=arm,name=name,request=request,primitive=primitive,trajectory=trajectory,geometry_samples=len(qs)))
                start.update(zip(joint_names(arm),qend))
        report.update(success=True,phase='OFFLINE_OPEN_RETURN_GEOMETRY_VALID',final_positions=start)
    except Exception as error:report.update(error=str(error),phase='OFFLINE_OPEN_RETURN_REJECTED')
    dump(out/'result.json',report);print(json.dumps({k:v for k,v in report.items()if k not in ['segments','final_positions']},indent=2));return 0 if report['success']else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['observations','object-pose','contact-scene','output']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--operation',choices=['retreat','home'],required=True);ap.add_argument('--after-retreat',type=Path,help='Explicit planned future high start for offline Home preparation; runner still requires matching real start');ap.add_argument('--config',type=Path,default=REPO/'uwa_cell_motion/config/hardware_carton_supported.yaml');ap.add_argument('--inventory',type=Path,default=REPO/'config/hardware_inventory.yaml')
    raise SystemExit(prepare(ap.parse_args()))

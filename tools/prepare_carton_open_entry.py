#!/usr/bin/env python3
"""Offline open-finger entry diagnostic. Never sends device commands.

Keep the primary whole-opening cell/interarm model and its40mm neighbor margin.
A second exact-open tool model checks a conservative hollow carton per moving
arm's fixed camera/base binding. Other arms are stationary, checked separately
against their own carton binding; primary interarm checks always include all.
"""
import argparse,json,sys,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'uwa_cell_tasks'))
from uwa_cell_motion.common import config,joint_names,dump
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.carton_paths import solve_near,cartesian_entry,evaluate,joint_segment
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_calibration.model import CollisionModel


def shell_boxes(scene):
    """Conservative design envelope, NOT a measurement of the real wall stack."""
    result=[]
    for shape in scene['shapes']:
        pts=np.array(shape['vertices']);lo=pts.min(0)-.005;hi=pts.max(0)+.005
        if shape['axis']==0:
            edge=float(pts[:,0].min()) if shape['side']==0 else float(pts[:,0].max())
            lo[0],hi[0]=(edge-.005,edge+.030) if shape['side']==0 else (edge-.030,edge+.005)
        result.append(dict(lo=lo.tolist(),hi=hi.tolist(),axis=shape['axis'],side=shape['side']))
    return result


def open_model(problem,binding,scene,arm,directory):
    root=ET.fromstring(problem.original_description);obj=ET.SubElement(root,'link',name='entry_carton')
    for b in shell_boxes(scene):
        lo,hi=np.array(b['lo']),np.array(b['hi']);c=ET.SubElement(obj,'collision');ET.SubElement(c,'origin',xyz=' '.join(map(str,(lo+hi)/2)));ET.SubElement(ET.SubElement(c,'geometry'),'box',size=' '.join(map(str,hi-lo)))
    T=np.array(binding['world_object_by_arm'][arm]);j=ET.SubElement(root,'joint',name='entry_carton_anchor',type='fixed');ET.SubElement(j,'parent',link='world');ET.SubElement(j,'child',link='entry_carton');ET.SubElement(j,'origin',xyz=' '.join(map(str,T[:3,3])),rpy=' '.join(map(str,Rotation.from_matrix(T[:3,:3]).as_euler('xyz'))))
    collision=CollisionModel(ET.tostring(root,encoding='unicode'),directory)
    base_srdf=ET.fromstring((problem.directory/'moveit/robot.srdf').read_text())
    for allowed in base_srdf.findall('disable_collisions'):collision.scene.allowed_collision_matrix.set_entry(allowed.get('link1'),allowed.get('link2'),True)
    # Each held member has a different nominal display representation of the
    # SAME object. Validate its physical carton clearance in its own model;
    # never move/remove another arm from the primary interarm checker.
    for link in root.findall('link'):
        if any(link.get('name').startswith(other+'_') for other in problem.names if other!=arm):
            collision.scene.allowed_collision_matrix.set_entry(link.get('name'),'entry_carton',True)
    return collision


def prepare(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);e=json.loads((args.evidence/'evidence.json').read_text());run=json.loads(args.approach.read_text());binding=json.loads(Path(e['inputs']['object_pose']['path']).read_text());scene=json.loads(Path(e['inputs']['contact_scene']['path']).read_text());p=HardwareProblem(out/'base',e['configuration'],args.inventory);p.chains={r:Chain(p.original_description,'world',r+'_tool0') for r in p.names};start=dict(run['segments'][-1]['final_positions']);report=dict(inputs={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.evidence/'evidence.json',args.approach,Path(e['inputs']['object_pose']['path']),Path(e['inputs']['contact_scene']['path']),Path(__file__)]},success=False,executable=False,finger_commands=[],arm_commands=[],loaded_motion=False,base_signature=p.signature,shell_boxes=shell_boxes(scene),segments=[],limits=['35mm short-wall normal envelope and5mm rim expansion are conservative DESIGN assumptions, not measured bounds.','Actual open jaw state and independent visual agreement required before any execution.','Primary full-opening/interarm/table model and40mm neighbor margin retained.','No contact exemptions for moving arm/carton in exact-open model.'])
    dump(out/'result.json',report)
    try:
        for arm in ['right_front','right_rear']:
            target=np.array(e['goals'][arm]['theoretical_tool0_entry']);normal=np.array(binding['world_object_by_arm'][arm])[:3,0];target[:3,3]+=normal*(.01125 if arm=='right_front' else -.01125)
            qstart=np.array([start[j] for j in joint_names(arm)]);qend=solve_near(p,arm,start,target,qstart);line=cartesian_entry(p,arm,start,target,qend,pregrasp_m=.15);align=joint_segment(qstart,line['positions'][0]);cm=open_model(p,binding,scene,arm,out/('open-'+arm));request=p.normalize(dict(start=start,goals={arm:qend.tolist()}))
            for name,segment in [('ALIGN',align),('ENTRY',line)]:
                u=np.linspace(0,1,257);qs=evaluate(segment,u);max_pe=0.;max_re=0.
                for phase,q in zip(u,qs):
                    state=dict(start,**dict(zip(joint_names(arm),q)))
                    if not p.check(request,q):raise ValueError(f'{arm}/{name}: primary full-cell/margin collision at {phase:.6f}')
                    if not cm.check(state)[0]:
                        cm.check(state,contacts=True)
                        raise ValueError(f'{arm}/{name}: exact-open conservative carton collision at {phase:.6f}')
                    if name=='ENTRY':
                        actual=p.chains[arm].forward(state);wanted=target.copy();wanted[2,3]+=.15*(1-(10*phase**3-15*phase**4+6*phase**5));pe=np.linalg.norm(actual[:3,3]-wanted[:3,3]);re=Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).magnitude();max_pe=max(max_pe,pe);max_re=max(max_re,re)
                        if pe>1e-4 or re>1e-3:raise ValueError('Smoothed Cartesian line error')
                dense=np.linspace(0,1,8193);v=float(abs(evaluate(segment,dense,1)).max());a=float(abs(evaluate(segment,dense,2)).max());duration=max(v/.1,np.sqrt(a/.2));ts=np.linspace(0,duration,max(2,int(np.ceil(duration/.02))+1));phase=ts/duration;points=[dict(time=float(t),positions=q.tolist(),velocities=v.tolist(),accelerations=a.tolist()) for t,q,v,a in zip(ts,evaluate(segment,phase),evaluate(segment,phase,1)/duration,evaluate(segment,phase,2)/duration**2)]
                segment_start=dict(start,**dict(zip(joint_names(arm),segment['positions'][0])));segment_request=p.normalize(dict(start=segment_start,goals={arm:segment['positions'][-1]}))
                report['segments'].append(dict(arm=arm,name=name,primitive=segment,request=segment_request,trajectory=dict(duration_s=duration,joint_names=joint_names(arm),points=points),max_line_error_m=float(max_pe),max_angle_error_rad=float(max_re),geometry_samples=len(u)));dump(out/'result.json',report)
            start.update(zip(joint_names(arm),qend))
        report.update(success=True,phase='OFFLINE_OPEN_ENTRY_GEOMETRY_VALID',final_positions=start)
    except Exception as error:report.update(error=str(error),phase='OFFLINE_OPEN_ENTRY_REJECTED')
    dump(out/'result.json',report);print(json.dumps({k:v for k,v in report.items()if k not in ['segments','shell_boxes','final_positions']},indent=2));return 0 if report['success']else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--approach',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--inventory',type=Path,default=REPO/'config/hardware_inventory.yaml');raise SystemExit(prepare(ap.parse_args()))

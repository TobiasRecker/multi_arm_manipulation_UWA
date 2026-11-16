#!/usr/bin/env python3
"""Run known-load Gazebo reference worlds without ROS/controllers/hardware.

The bounded server invocation exits after iterations. Raw measurements and
failed attempts are retained. No assumption that a sensor API implies accuracy.
"""
import argparse
import hashlib
import json
import math
import os
import signal
from pathlib import Path
import subprocess
import time
import uuid
import xml.etree.ElementTree as E

from ament_index_python.packages import get_package_prefix
from uwa_cell_tasks.core import seal,write_json

ENGINE=Path('/opt/ros/lyrical/opt/gz_physics_vendor/lib/libgz-physics-dartsim-plugin.so.9.5.2')


def world(path,plugin,step,mass):
    root=E.Element('sdf',version='1.12');w=E.SubElement(root,'world',name='uwa_force_lab_'+uuid.uuid4().hex[:10])
    E.SubElement(w,'gravity').text='0 0 -9.81'
    physics=E.SubElement(w,'physics',name='force_reference',type='ignored')
    E.SubElement(physics,'max_step_size').text=str(step);E.SubElement(physics,'real_time_factor').text='0.6'
    p=E.SubElement(w,'plugin',filename='gz-sim-physics-system',name='gz::sim::systems::Physics')
    E.SubElement(E.SubElement(p,'engine'),'filename').text=str(ENGINE)
    E.SubElement(w,'plugin',filename='gz-sim-contact-system',name='gz::sim::systems::Contact')
    p=E.SubElement(w,'plugin',filename=str(plugin),name='uwa_cell_tasks::ForceProbe')
    for k,v in dict(output=str(path/'trace.jsonl'),mass=mass,push=2.,down=1.).items():E.SubElement(p,k).text=str(v)
    def body(model_name,link_name,pose,size,*,static=False,link_pose=None,contact=False):
        m=E.SubElement(w,'model',name=model_name);E.SubElement(m,'pose').text=pose
        if static:E.SubElement(m,'static').text='true'
        l=E.SubElement(m,'link',name=link_name)
        if link_pose:E.SubElement(l,'pose').text=link_pose
        if not static:
            inertial=E.SubElement(l,'inertial');E.SubElement(inertial,'mass').text=str(mass)
            inertia=E.SubElement(inertial,'inertia');x,y,z=size
            for k,v in dict(ixx=mass*(y*y+z*z)/12,iyy=mass*(x*x+z*z)/12,izz=mass*(x*x+y*y)/12,ixy=0,ixz=0,iyz=0).items():E.SubElement(inertia,k).text=str(v)
        c=E.SubElement(l,'collision',name=link_name+'_collision')
        E.SubElement(E.SubElement(E.SubElement(c,'geometry'),'box'),'size').text=' '.join(map(str,size))
        friction=E.SubElement(E.SubElement(E.SubElement(c,'surface'),'friction'),'ode')
        for key in ('mu','mu2'):E.SubElement(friction,key).text='.4'
        if contact:
            sensor=E.SubElement(l,'sensor',name=link_name+'_contact',type='contact')
            E.SubElement(sensor,'always_on').text='true';E.SubElement(sensor,'update_rate').text='0'
            E.SubElement(E.SubElement(sensor,'contact'),'collision').text=link_name+'_collision'
        return m
    body('floor','floor_body','0 0 -.05 0 0 0',(20,20,.1),static=True,contact=True)
    body('load','load_body','0 0 .05 0 0 0',(.1,.1,.1),contact=True)
    body('free','free_body','2 0 1 0 0 0',(.1,.1,.1))
    body('drop','drop_body','-2 0 .4 0 0 0',(.1,.1,.1),contact=True)
    for suffix,y,yaw in [('',2,0.),('_rotated',-2,math.pi/2)]:
        fixed=body('reference'+suffix,'wrench_body'+suffix,f'0 {y} 1 0 0 0',(.1,.1,.1),link_pose='.15 0 0 0 0 0')
        joint=E.SubElement(fixed,'joint',name='reference_fixed'+suffix,type='fixed')
        E.SubElement(joint,'pose').text=f'-.15 0 0 0 0 {yaw}'
        E.SubElement(joint,'parent').text='world';E.SubElement(joint,'child').text='wrench_body'+suffix
    E.indent(root);text=E.tostring(root,encoding='unicode');(path/'world.sdf').write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--steps',type=float,nargs='+',default=[.001,.0005,.00025]);p.add_argument('--masses',type=float,nargs='+',default=[.3,.6]);p.add_argument('--repeats',type=int,default=2)
    args=p.parse_args()
    if os.environ.get('ROS_DOMAIN_ID')!='64' or os.environ.get('GZ_PARTITION')!='uwa_cell_sim':p.error('Source the cell simulation environment.')
    if any(not math.isfinite(s) or not .0001<=s<=.002 for s in args.steps):p.error('Physics step outside reference range.')
    if any(not math.isfinite(m) or not .05<=m<=2 for m in args.masses) or not 1<=args.repeats<=5:p.error('Invalid mass/repeat count.')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    plugin=(Path(get_package_prefix('uwa_cell_tasks'))/'lib/libforce_probe.so').resolve()
    manifest=seal(dict(kind='known_load_force_reference',hardware=False,controllers=False,
        engine=str(ENGINE),engine_sha256=hashlib.sha256(ENGINE.read_bytes()).hexdigest(),
        probe=str(plugin),probe_sha256=hashlib.sha256(plugin.read_bytes()).hexdigest(),
        runner_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        steps=args.steps,masses=args.masses,repeats=args.repeats))
    write_json(out/'experiment.json',manifest);cases=[]
    for mass in args.masses:
        for step in args.steps:
            for repeat in range(args.repeats):
                directory=out/f'm{mass:g}_dt{step:g}_r{repeat}';directory.mkdir()
                digest=world(directory,plugin,step,mass);start=time.monotonic()
                command=['gz','sim','-s','-r','--iterations',str(round(3./step)),str(directory/'world.sdf'),'-v','2']
                with (directory/'server.log').open('w') as log:
                    proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:code=proc.wait(timeout=40.)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGINT)
                        try:proc.wait(timeout=10.)
                        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                        code='timeout'
                case=dict(path=str(directory),mass_kg=mass,step_s=step,repeat=repeat,world_sha256=digest,returncode=code,wall_s=time.monotonic()-start)
                cases.append(case);write_json(directory/'case.json',seal(case))
                print(json.dumps(case),flush=True)
                if code!=0:raise RuntimeError('Reference server failed; inspect '+str(directory/'server.log'))
    write_json(out/'cases.json',seal(dict(cases=cases,experiment_sha256=manifest['sha256'])))
    return 0

if __name__=='__main__':raise SystemExit(main())

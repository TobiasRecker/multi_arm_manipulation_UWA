#!/usr/bin/env python3
"""Bind a planned new grasp to cached canonical air paths before any approach.

File preparation and an isolated titanpc job only. No robot/gripper commands.
The old completed grasp remains historical; the new start is explicitly future.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import unquote,urlsplit

import numpy as np

REPO=Path(__file__).resolve().parents[1]
WS=REPO.parents[1]
BASE=WS/'setup/tasks/carton-air-demo-20261126'
TEMPLATE=BASE/'input-cache01'


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def prepare(plan,output):
    from uwa_cell_tasks.reviewed_carton import START_TOLERANCE
    plan=Path(plan).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    workflow=read(plan/'workflow.json');lift=read(plan/'weigh-plan/proof.json')
    evidence=read(plan/'high-plan/evidence.json');program_path=Path(workflow['program']['path'])
    definition=read(program_path)
    if (workflow.get('phase')!='OFFLINE_APPROACH_PREPARED' or workflow.get('success')is not True
            or workflow.get('execute')is not False or lift.get('success')is not True
            or lift.get('height_m')!=.020 or definition.get('program_id')!='carton-supported-simulation-v1'
            or sha(program_path)!=workflow['program']['sha256']):
        raise ValueError('A complete checked future simulation-grip approach and weighing lift is required')
    for entry in evidence['inputs'].values():
        if sha(entry['path'])!=entry['sha256']:raise ValueError('Bound grasp input changed')
    pose_path=Path(evidence['inputs']['object_pose']['path']);pose=read(pose_path)
    transforms=pose['world_object_by_arm'];world=np.asarray(transforms['right_front'])
    if not all(np.allclose(world,t,atol=1e-8,rtol=0)for t in transforms.values()):
        raise ValueError('One common two-camera carton registration is required')
    scene_path=Path(evidence['inputs']['contact_scene']['path']);scene=read(scene_path)
    original=read(TEMPLATE/'input.json')
    def geometry(shapes):return [{k:v for k,v in s.items()if k!='uri'}for s in shapes]
    if geometry(scene['shapes'])!=geometry(original['object_shapes']):
        raise ValueError('New grasp and cached air sequence use different carton geometry')
    for shape in scene['shapes']:
        url=urlsplit(shape['uri'])
        if url.scheme!='file' or url.netloc or sha(Path(unquote(url.path)))!=shape['sha256']:
            raise ValueError('New grasp skin source changed')
    review=read(plan/'weigh-plan/review.json')
    if review['model_signature']!=original['model_signature']:
        raise ValueError('New grasp and cached hardware model differ')
    if definition['contact_design']['object_to_tool0']!=original['reference_group']['object_to_tcp']:
        raise ValueError('New contact transforms differ from the qualified simulation grips')
    end=lift['end'];data=copy.deepcopy(original)
    # Idle arms keep their already checked nominal starts, within the existing
    # start tolerance of the new measured snapshot. No live coordinates change.
    for arm in ('left_front','left_rear'):
        for joint in data['names'][arm][:6]:
            if abs(end[joint]-data['start'][joint])>START_TOLERANCE:
                raise ValueError(arm+': idle start changed; cached approach is not reusable')
    for arm in ('right_front','right_rear'):
        for joint in data['names'][arm][:6]:data['start'][joint]=end[joint]
    future=world.copy();future[2,3]+=.020
    data['pose']=future.tolist();data['planned_grip_end']=end
    data['planned_grasp_binding']=dict(workflow_sha256=sha(plan/'workflow.json'),
        lift_sha256=sha(plan/'weigh-plan/proof.json'),pose_sha256=sha(pose_path),
        scene_sha256=sha(scene_path),program_sha256=sha(program_path),plan=str(plan))
    bundle=output/'input';shutil.copytree(TEMPLATE,bundle)
    write(bundle/'input.json',data)
    for name,new in [('prepare_carton_air_demo.py','prepare_carton_air_demo.py'),
                     ('qualify_carton_air_demo.py','qualify.py'),('carton_air_cache.py','carton_air_cache.py'),
                     ('task_obstacles.py','task_obstacles.py')]:
        shutil.copyfile(REPO/'tools'/name,bundle/new)
    write(output/'binding.json',dict(planned_only=True,robot_commands_sent=False,
        start_kind='PLANNED_AFTER_NEW_GRASP_NOT_CURRENT',binding=data['planned_grasp_binding']))
    return bundle


def compute(bundle,output,job):
    from run_carton_program import logged_command
    command=['python3',WS/'setup/titanpc/compute.py']
    logged_command([*command,'host-status'],output/'compute-host.log',30)
    logged_command([*command,'submit','--image','planning.sif','--cpus','4','--memory-gib','8',
        '--seconds','1200','cpu',job,bundle,'--','bash','/input/qualified-sequence.bash'],output/'submit.log',240)
    deadline=time.monotonic()+1200
    while True:
        raw=logged_command([*command,'status',job],output/'status.log',30,separate_stdout=True)
        # compute.py reports the state JSON alongside the systemd status text.
        status=None
        for line in raw.splitlines():
            try:value=json.loads(line)
            except ValueError:continue
            if isinstance(value,dict)and 'state'in value:status=value['state']
        if status is None:
            # The CLI's state.json is pretty printed; decode the first JSON object.
            start=raw.find('{')
            if start>=0:
                try:status=json.JSONDecoder().raw_decode(raw[start:])[0].get('state')
                except ValueError:pass
        if status in ('DONE','FAILED','CANCELLED','TIMED_OUT'):
            break
        if time.monotonic()>deadline:raise TimeoutError('Offline followup qualification did not finish')
        time.sleep(3.)
    logged_command([*command,'fetch',job,output/'result'],output/'fetch.log',240)
    proof=read(output/'result/output/qualified/proof.json')
    if status!='DONE' or proof.get('success')is not True:
        raise ValueError('Future air connectors rejected: '+str(proof.get('error',status)))
    write(output/'qualified.json',dict(success=True,executable=False,robot_commands_sent=False,
        proof_sha256=sha(output/'result/output/qualified/proof.json'),
        binding_sha256=sha(output/'binding.json'),phases=len(proof['phases']),
        total_duration_s=proof['total_duration_s'],job=job))
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--job',required=True)
    args=parser.parse_args();bundle=prepare(args.plan,args.output);compute(bundle,args.output.resolve(),args.job)

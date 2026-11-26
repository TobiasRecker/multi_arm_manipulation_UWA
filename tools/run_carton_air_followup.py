"""Stage the prequalified continuation and use the existing Motion Review UI."""
import copy
import json
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

from run_carton_program import (REPO,WORKSPACE,CELL,capture_oak,carton_camera,load_json,
    logged_command,n100,upload)
from uwa_cell_tasks.reviewed_carton import check_boundaries
from prepare_carton_air_followup import sha,read,write


def preview_model(data,bundle,phases):
    root=ET.fromstring((bundle/'original.urdf').read_text())
    for mesh in root.findall('.//mesh'):
        name=mesh.get('filename')
        if name and name.startswith('file:///input/assets/'):
            mesh.set('filename',(bundle/'assets'/name.rsplit('/',1)[-1]).resolve().as_uri())
    body=ET.SubElement(root,'link',name='review_carried_carton')
    for shape in data['object_shapes']:
        visual=ET.SubElement(body,'visual')
        ET.SubElement(ET.SubElement(visual,'geometry'),'mesh',filename=shape['uri'])
        material=ET.SubElement(visual,'material',name='air_carton')
        ET.SubElement(material,'color',rgba='0.85 0.55 0.18 0.8')
    joint=ET.SubElement(root,'joint',name='review_carton_grip',type='fixed')
    ET.SubElement(joint,'parent',link='right_front_tool0');ET.SubElement(joint,'child',link=body.get('name'))
    offset=np.linalg.inv(np.asarray(data['reference_group']['object_to_tcp']['right_front']))
    ET.SubElement(joint,'origin',xyz=' '.join(map(str,offset[:3,3])),
        rpy=' '.join(map(str,Rotation.from_matrix(offset[:3,:3]).as_euler('xyz'))))
    tip=ET.SubElement(root,'link',name='review_virtual_tool_reference')
    visual=ET.SubElement(tip,'visual');ET.SubElement(ET.SubElement(visual,'geometry'),'sphere',radius='.005')
    material=ET.SubElement(visual,'material',name='virtual_reference');ET.SubElement(material,'color',rgba='0 0.9 1 1')
    joint=ET.SubElement(root,'joint',name='review_virtual_reference_joint',type='fixed')
    ET.SubElement(joint,'parent',link='left_front_tool0');ET.SubElement(joint,'child',link=tip.get('name'))
    ET.SubElement(joint,'origin',xyz='0 0 .3')
    return ET.tostring(root,encoding='unicode')


def build_plan(followup,grasp_plan):
    followup=Path(followup);grasp_plan=Path(grasp_plan)
    receipt=read(followup/'qualified.json');binding=read(followup/'binding.json')
    if (not receipt.get('success') or receipt['binding_sha256']!=sha(followup/'binding.json')
            or binding['binding']['workflow_sha256']!=sha(grasp_plan/'workflow.json')
            or binding['binding']['lift_sha256']!=sha(grasp_plan/'weigh-plan/proof.json')):
        raise ValueError('Qualified followup and actual selected grasp plan changed')
    directory=followup/'result/output/qualified';proof=read(directory/'proof.json')
    if sha(directory/'proof.json')!=receipt['proof_sha256'] or not proof.get('success'):
        raise ValueError('Air qualification proof changed')
    data=read(followup/'input/input.json');draft=read(followup/'result/output/draft/result.json')
    groups=[];start=None
    for summary in proof['phases']:
        phase=read(directory/(summary['id']+'.json'))
        if proof.get('controller_files',{}).get(summary['id'])!=sha(directory/(summary['id']+'.json')):
            raise ValueError('Qualified controller file changed')
        if any(phase[key]!=value for key,value in summary.items()):
            raise ValueError('Air phase summary and frozen controller path differ')
        trajectories=copy.deepcopy(phase['trajectories'])
        for trajectory in trajectories.values():trajectory['duration_s']=trajectory['points'][-1]['time']
        group=dict(phase=phase['id'],arms=sorted(trajectories),start=phase['start'],
            trajectories=trajectories,duration_s=phase['duration_s'])
        if start is None:start=dict(group['start'])
        groups.append(group)
    selected=sorted({arm for group in groups for arm in group['arms']})
    check_boundaries(dict(start=start,groups=groups),start,proof['end'],selected)
    if len(groups)!=62 or draft['proposed_offsets']!=data['reference_group']['object_to_tcp']:
        raise ValueError('Complete exact simulation-grip sequence required')
    preview_start=dict(start,**draft['nominal_jaws'])
    preview=dict(start=preview_start,groups=groups,robot_description=preview_model(data,followup/'input',groups),
        duration_s=proof['total_duration_s'])
    return dict(kind='carton_air_demo',version=1,physical_tool=False,model_identity=data['model_identity'],
        speed_percent=read(grasp_plan/'workflow.json')['speed_percent'],start=start,end=proof['end'],phases=groups,
        duration_s=proof['total_duration_s'],preview=preview,
        qualification_sha256=sha(directory/'proof.json'),grasp_binding=binding['binding'],
        phase_sha256={summary['id']:sha(directory/(summary['id']+'.json'))for summary in proof['phases']})


def plausible_grip(report):
    """Use the already requested finite post-grasp weighing result once."""
    return (report.get('success')is True and report.get('phase')=='CARTON_LIFTED_AND_WEIGHED'
        and report.get('measurement_available')is True
        and (report.get('weighing')or{}).get('assessment')=='BOTH_ARMS_LOAD_PLAUSIBLE')


def execute_followup(progress,followup,grasp_plan,remote,target_workspace,status):
    followup=Path(followup);out=progress.output
    if not plausible_grip(read(out/'n100-contact-workflow.json')):
        raise ValueError('The finite post-grasp measurement does not confirm plausible load on both arms; no air-trial motion was requested')
    plan=build_plan(followup,grasp_plan);stage=followup/'execution';stage.mkdir()
    write(stage/'plan.json',plan)
    camera_config=read(out/'camera-session.json')
    camera=carton_camera(out,camera_config['optics']['focus']);after_lift=time.time()
    try:
        camera.start();photo,metadata=capture_oak(out,'air-held',camera)
    finally:camera.stop()
    destination=remote+'/air'
    logged_command(n100('mkdir -- "$1"',destination),stage/'mkdir.log',20)
    for source,name in [(REPO/'tools/execute_carton_air_demo.py','execute_carton_air_demo.py'),
            (REPO/'tools/execute_return_home.py','return_home_helpers.py'),
            (REPO/'tools/return_home_model.py','return_home_model.py'),
            (REPO/'uwa_cell_tasks/uwa_cell_tasks/motion_review.py','air_review_store.py')]:
        local=stage/name;local.write_bytes(source.read_bytes());upload(destination+'/'+name,local,stage/('upload-'+name+'.log'))
    upload(destination+'/',stage/'plan.json',stage/'upload-plan.log',photo,metadata)
    command=n100('''source "$1/scripts/control_env.bash"
exec python3 "$2/execute_carton_air_demo.py" --plan "$2/plan.json" --sha256 "$3" --session "$4" --after-lift "$5" --photo "$2/standard.png" --metadata "$2/metadata.json"
''',CELL,destination,sha(stage/'plan.json'),status['session_id'],after_lift)
    progress.update('air_review','Review the complete empty-tool carton trial in UWA Robot Power.')
    with (stage/'execution.log').open('w')as stream:
        with subprocess.Popen([str(x)for x in command],cwd=WORKSPACE,text=True,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT)as child:
            for line in child.stdout:
                stream.write(line);stream.flush()
                if line.startswith('WAITING_FOR_'):
                    progress.update('air_review','Review the complete empty-tool carton trial in UWA Robot Power.',review_id=line.split()[-1])
                elif line.startswith('REVIEW_ACCEPTED_'):
                    progress.update('air_demo','Review accepted. Executing the checked empty-tool carton trial.')
                elif line.startswith('AIR_PHASE '):
                    event=json.loads(line.removeprefix('AIR_PHASE '));progress.update('air_demo',
                        'Air trial: '+event['phase'].replace('_',' ')+' · '+event['state'],air_phase=event)
            code=child.wait()
    raw=logged_command(n100('cat -- "$1/execution.json"',destination),stage/'result.log',20,separate_stdout=True)
    result=json.loads(raw);write(stage/'result.json',result)
    if code or result.get('success')is not True:
        raise RuntimeError('Air trial did not complete: '+str(result.get('error','See Safety log')))
    return dict(success=True,remote_run=destination,duration_s=plan['duration_s'],phases=len(plan['phases']))

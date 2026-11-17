#!/usr/bin/env python3
"""Predeclared rotation-amplitude challenges reusing two checked start states."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys


def arguments():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('parent',type=Path)
    parser.add_argument('--output-dir',type=Path,required=True)
    return parser.parse_args()


args=arguments() if __name__=='__main__' else None
if __name__=='__main__' and os.environ.get('UWA_ENCOUNTER_FROZEN')!='1':
    root=(args.parent/'frozen-source').resolve();env=dict(os.environ)
    env.update(UWA_ENCOUNTER_FROZEN='1',UWA_TEACHER_FROZEN='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    packages=['uwa_cell_motion','uwa_cell_calibration','uwa_cell_control','uwa_cell_description','uwa_cell_gazebo']
    env['PYTHONPATH']=os.pathsep.join([str(root/'tools')]+[str(root/p) for p in packages]+[env.get('PYTHONPATH','')])
    env['UWA_ENCOUNTER_TOOLS']=str(root/'tools')
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],env=env))

if os.environ.get('UWA_ENCOUNTER_TOOLS'):sys.path.insert(0,os.environ['UWA_ENCOUNTER_TOOLS'])
from generate_diverse_teacher_dataset import run_family
from generate_teacher_dataset import sha,load_completed,summarize
from uwa_cell_motion.teacher_dataset import atomic_json,digest


def main(args):
    parent=args.parent.resolve();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ('starts','cases'):(out/name).mkdir(exist_ok=True)
    frozen=out/'frozen-source'
    if not frozen.exists():frozen.symlink_to((parent/'frozen-source').resolve(),target_is_directory=True)
    elif frozen.resolve()!=(parent/'frozen-source').resolve():raise ValueError('Different frozen source parent')
    source=json.loads((parent/'manifest.json').read_text());manifest=deepcopy(source)
    manifest['artifact_type']='fixed_start_arm_encounter_challenges'
    manifest['parent_manifest_sha256']=digest(source);manifest['probe_code_sha256']=sha(Path(__file__))
    manifest['parent_path']=str(parent);manifest['cases']=[]
    selected=[('east_high',0),('positive_tilt',1)]
    manifest['families']=[f for f in source['families'] if f['id'] in dict(selected)]
    manifest['parent_start_sha256']={name:sha(parent/'starts'/f'{name}.json') for name,_ in selected}
    for name,variant in selected:
        base=next(c for c in source['cases'] if c['id']==f'{name}-v{variant}')
        for i,factor in enumerate((1.4,1.8,2.2)):
            case=deepcopy(base);case.update(id=f'{name}-challenge-{i}',variant=i,rotation_excursion_factor=factor,
                                          parent_case_id=base['id'])
            case['task']['name']=case['id']
            case['task']['rotation_vector_deg']=[factor*v for v in base['task']['rotation_vector_deg']]
            manifest['cases'].append(case)
    manifest['assumptions'].append('Targeted diagnostic extension: start and endpoint unchanged, rotation excursion scaled; inherits parent splits')
    path=out/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=manifest:raise ValueError('Challenge manifest changed')
    else:atomic_json(path,manifest)
    for family in manifest['families']:
        path=out/'starts'/f"{family['id']}.json"
        if not path.exists():
            bank=json.loads((parent/'starts'/path.name).read_text())
            bank['reused_parent_manifest_sha256']=bank['manifest_sha256']
            bank['reused_parent_start_sha256']=manifest['parent_start_sha256'][family['id']]
            bank['manifest_sha256']=digest(manifest);atomic_json(path,bank)
    done=load_completed(out,manifest)
    with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(run_family,f,manifest,str(out),False) for f in manifest['families']]
        for future in as_completed(futures):
            result=future.result();done.update((r['case']['id'],r) for r in result['completed'])
            summary=summarize(out,manifest,done)
            print('FAMILY',result['family'],'RESULTS',[(r['case']['id'],r['status']) for r in result['completed']],flush=True)
    print('SUMMARY',json.dumps({k:summary[k] for k in ('planned','completed','accepted','repaired','transitions')}),flush=True)


if __name__=='__main__':main(args)

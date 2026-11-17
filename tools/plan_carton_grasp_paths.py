#!/usr/bin/env python3
"""Standard offline carton approach: fixed goals, IK/path alternatives, C3 timing.

No ROS nodes or robot execution. Historical primitive/10x results are retained
as intermediate comparison artifacts; the delivered default is always smoothed.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--grasp-pattern',choices=['corners','sides'],default='corners')
    parser.add_argument('--endpoint-policy',choices=['static_margin','stop_reserve'],default='static_margin')
    parser.add_argument('--layout');parser.add_argument('--config')
    args=parser.parse_args();out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=False)
    tools=Path(__file__).resolve().parent
    extra=[]
    for key in ['layout','config']:
        if getattr(args,key):extra+=['--'+key,str(Path(getattr(args,key)).resolve())]
    steps=[('primitives',[str(tools/'plan_carton_corner_paths.py'),'--output-dir',str(out/'primitives'),
                          '--grasp-pattern',args.grasp_pattern,'--endpoint-policy',args.endpoint_policy,*extra]),
           ('baseline',[str(tools/'compare_carton_path_speed.py'),str(out/'primitives'),'--output-dir',str(out/'baseline')]),
           ('smoothed',[str(tools/'smooth_carton_paths.py'),str(out/'baseline'),'--output-dir',str(out/'smoothed')]),
           ('verification',[str(tools/'verify_smooth_carton_paths.py'),str(out/'smoothed')])]
    report=dict(executable=False,grasp_pattern=args.grasp_pattern,timing='smooth_by_default',
                offline_endpoint_policy=args.endpoint_policy,status='RUNNING',steps=[])
    for name,command in steps:
        print(name,flush=True)
        with (out/(name+'.log')).open('w') as log:
            done=subprocess.run([sys.executable,*command],stdout=log,stderr=subprocess.STDOUT)
        report['steps'].append(dict(name=name,returncode=done.returncode))
        report['status']='FAILED_'+name.upper() if done.returncode else 'RUNNING'
        (out/'run.json').write_text(json.dumps(report,indent=2))
        if done.returncode:raise SystemExit(done.returncode)
    shutil.copyfile(out/'smoothed/viewer.html',out/'viewer.html')
    report['status']='SAMPLED_GEOMETRY_CLEAR_RESERVE_DIAGNOSTIC_ONLY'
    (out/'run.json').write_text(json.dumps(report,indent=2));print(out/'viewer.html')


if __name__=='__main__':main()

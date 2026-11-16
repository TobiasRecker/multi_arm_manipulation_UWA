"""Offline single-UR CDF: prepare, query, plan, preview and reproducible demo."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
from .common import config,dump,ROBOT_IDS
from .planning import Problem
from .cdf_geometry import FrozenScene
from .cdf import ContactBank,build_bank,plan


def prepare(scene,request,args):
    return build_bank(scene,request,samples=args.samples,seed=args.seed,budget_s=args.prepare_budget,
        progress=lambda n,k,t:print(f'PREPARING CDF: {n}/{args.samples} seeds, {k} contacts, {t:.1f}s',flush=True))


def demo(problem,args):
    from ament_index_python.packages import get_package_share_directory
    from .cdf_report import render_report
    source=Path(get_package_share_directory('uwa_cell_motion'))/'config/benchmark_suite_20261113.json'
    suite=json.loads(source.read_text());cases=[]
    for category in ('free','blocked_direct','unreachable'):
        cases.append(next(c for c in suite['cases'] if c['category']==category and list(c['request']['goals'])==[args.arm]))
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    if (output/'summary.json').exists():raise ValueError('Use a fresh demo output directory to preserve previous results')
    rows=[];banks=[];summary=dict(schema_version=1,arm=args.arm,complete=False,rows=rows,banks=banks,
        qualification='Offline simulation model only; no Gazebo execution or real motion',scene_model=problem.signature)
    for seed in range(args.seeds):
        args.seed=seed;reference=problem.normalize(cases[1]['request']);scene=FrozenScene(problem,reference)
        if args.bank_directory:
            bank=ContactBank.load(Path(args.bank_directory)/f'contacts-{seed}.npz',scene)
            if bank.metadata.get('seed')!=seed:raise ValueError('Reused CDF bank seed differs')
        else:bank=prepare(scene,reference,args)
        bank.save(output/f'contacts-{seed}.npz');banks.append(bank.metadata)
        summary['reused_bank_directory']=str(args.bank_directory) if args.bank_directory else None
        for case in cases:
            dump(output/(case['id']+'-request.json'),case['request'])
            for method in ('rrtconnect','circular','cdf'):
                result=plan(problem,case['request'],bank,seed=seed,gamma=args.gamma,max_step=args.max_step) if method=='cdf' else problem.plan(case['request'],method,seed)
                name=f"{case['id']}-{seed}-{method}";dump(output/(name+'.json'),result)
                if result['success']:
                    from .preview import render
                    render(result,output/(name+'.html'))
                row=dict(case_id=case['id'],category=case['category'],seed=seed,method=method,success=result['success'],
                    error=result.get('error'),planning_time_s=result['planning_time_s'],total_offline_time_s=result['total_offline_time_s'],
                    preparation_time_s=bank.metadata['preparation_time_s'] if method=='cdf' else 0.,metrics=result.get('metrics'),record=name+'.json')
                rows.append(row);dump(output/'summary.json',summary)
                print(f"DONE {name}: {'PASS' if result['success'] else result.get('error')}",flush=True)
    summary['complete']=True;dump(output/'summary.json',summary);render_report(problem,summary,output)
    print(str(output/'report.html'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--layout');parser.add_argument('--config')
    sub=parser.add_subparsers(dest='op',required=True)
    def data_args(p):
        p.add_argument('--samples',type=int,default=1024);p.add_argument('--seed',type=int,default=0);p.add_argument('--prepare-budget',type=float,default=120.)
    def qp_args(p):
        p.add_argument('--gamma',type=float,default=.9);p.add_argument('--max-step',type=float,default=.04)
    p=sub.add_parser('prepare');p.add_argument('request');p.add_argument('--output',required=True);data_args(p)
    p=sub.add_parser('query');p.add_argument('request');p.add_argument('--bank',required=True);p.add_argument('--q',nargs=6,type=float);p.add_argument('--output',required=True)
    p=sub.add_parser('plan');p.add_argument('request');p.add_argument('--bank',required=True);p.add_argument('--output',required=True);qp_args(p)
    p=sub.add_parser('preview');p.add_argument('plan');p.add_argument('--output',required=True)
    p=sub.add_parser('demo');p.add_argument('--arm',choices=ROBOT_IDS,default='right_rear');p.add_argument('--seeds',type=int,default=1);p.add_argument('--bank-directory');p.add_argument('--output',required=True);data_args(p);qp_args(p)
    args=parser.parse_args()
    if args.op=='preview':
        from .preview import render
        value=json.loads(Path(args.plan).read_text())
        if value.get('method')!='cdf' or not value.get('simulation_only'):raise ValueError('Expected simulation CDF plan')
        render(value,args.output);print(args.output);return
    with tempfile.TemporaryDirectory(prefix='uwa-cdf-') as directory:
        problem=Problem(directory,config(args.config),args.layout)
        if args.op=='demo':
            if not 1<=args.seeds<=5:raise ValueError('Expected1..5 preparation seeds')
            return demo(problem,args)
        request=problem.normalize(json.loads(Path(args.request).read_text()));scene=FrozenScene(problem,request)
        if args.op=='prepare':
            bank=prepare(scene,request,args);bank.save(args.output);dump(str(args.output)+'.json',bank.metadata)
        else:
            bank=ContactBank.load(args.bank,scene)
            if args.op=='query':
                q=np.array(args.q if args.q else [request['start'][j] for j in request['joint_names']]);d,g,i=bank.query(q)
                candidate=q-d*g;residual=scene.sdf(candidate)[0][0]
                dump(args.output,dict(cdf_rad=d,gradient=g.tolist(),template=i,projection=candidate.tolist(),
                    projection_sdf_residual_m=float(residual),scene_binding=scene.binding,
                    qualification='Sampled unsigned CDF; projection may not hit the true boundary and is not a safe motion'))
            elif args.op=='plan':
                value=plan(problem,request,bank,gamma=args.gamma,max_step=args.max_step);dump(args.output,value)
                print(json.dumps(dict(success=value['success'],error=value.get('error'),planning_time_s=value['planning_time_s'])))
                if not value['success']:raise SystemExit(1)

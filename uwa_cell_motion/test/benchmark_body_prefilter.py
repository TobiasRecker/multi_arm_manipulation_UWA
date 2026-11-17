"""Read-only offline v2 before/after timing against an immutable hardware plan."""
import argparse,json,tempfile,time
from pathlib import Path
import numpy as np
from uwa_cell_motion.common import BODY_RESERVE_MODEL,dump
from uwa_cell_motion.hardware_model import HardwareProblem


def dense(problem,request,q,*,margin=True):
    state=problem.state(request,q)
    if not problem.collision.check(state)[0]:return False
    if not margin:return True
    _,pairs=problem.spheres.pairs(state,{r:np.zeros(len(n)) for r,n in problem.names.items()},
        {r:problem.cfg['state_timeout_s'] for r in problem.names},problem.cfg)
    return all(p['remaining_clearance_m']>0 for p in pairs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repeats',type=int,default=3);args=parser.parse_args()
    if args.repeats<3:raise ValueError('At least three rotated repetitions required')
    args.output.mkdir(parents=True,exist_ok=False)
    saved=json.loads(args.plan.read_text())
    if not saved.get('success') or saved['config'].get('stopping_reserve_model')!=BODY_RESERVE_MODEL:
        raise ValueError('Successful bound body-reserve plan required')
    with tempfile.TemporaryDirectory(prefix='uwa-body-prefilter-') as directory:
        began=time.perf_counter();model=HardwareProblem(directory,saved['config'],saved['inventory'],saved.get('layout_path'))
        model_s=time.perf_counter()-began
        if model.binding!=saved['hardware_binding'] or model.spheres.geometry.assets!=saved['mesh_sha256']:
            raise ValueError('Frozen source model/config binding changed')
        request=saved['request'];points=saved['trajectory']['points']
        sample=[points[i]['positions'] for i in np.unique(np.linspace(0,len(points)-1,150).astype(int))]
        checks={'dense_v2':lambda r,q,**kw:dense(model,r,q,**kw),'aabb_v2':model.check}
        expected=[checks['dense_v2'](request,q) for q in sample];timings={k:[] for k in checks};counts={}
        for repeat in range(args.repeats):
            for name in list(checks)[::1 if repeat%2==0 else -1]:
                model.spheres._planning_cache.clear();model.spheres.planning_stats={k:0 for k in model.spheres.planning_stats}
                began=time.perf_counter();actual=[checks[name](request,q) for q in sample];elapsed=time.perf_counter()-began
                if actual!=expected:raise AssertionError('Different decisions: '+name)
                timings[name].append(elapsed);counts[name]=dict(model.spheres.planning_stats)
        report=dict(offline_only=True,no_robot_commands=True,source=str(args.plan.resolve()),
            model_construction_s=model_s,spheres_per_arm={r:len(v) for r,v in model.spheres.radii.items()},
            states=len(sample),repeats=args.repeats,identical_decisions=True,
            state_checks={k:dict(median_s=float(np.median(v)),ms_per_state=1000*float(np.median(v))/len(sample),
                repetitions_s=v,counters=counts[k]) for k,v in timings.items()},full_plans={})
        full={};original=model.check
        for name in checks:
            print('OFFLINE full plan: '+name,flush=True)
            model.check=checks[name];model.spheres._planning_cache.clear()
            began=time.perf_counter();value=model.plan(request,saved['method'],saved.get('seed',0));wall=time.perf_counter()-began
            full[name]=value
            report['full_plans'][name]=dict(success=value['success'],error=value.get('error'),
                wall_s=wall,geometry_planning_s=value['planning_time_s'],reported_total_s=value['total_offline_time_s'],
                trajectory_points=len(value.get('trajectory',{}).get('points',[])),coordination=value.get('coordination'))
            dump(args.output/'result.json',report)
        model.check=original
        if not all(v['success'] for v in full.values()):raise AssertionError('A full plan failed')
        report['identical_full_trajectory']=full['dense_v2']['trajectory']==full['aabb_v2']['trajectory']
        if not report['identical_full_trajectory']:raise AssertionError('Timed trajectory changed')
        report['qualification']='One frozen LF path; repeated state timing and one complete plan per method. No general speedup or real stopping qualification.'
        dump(args.output/'result.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':main()

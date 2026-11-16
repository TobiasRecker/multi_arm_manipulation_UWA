"""Offline before/after checks on identical states; never connects to robots."""
import argparse
import html
import json
from pathlib import Path
import subprocess
import tempfile
import time
import numpy as np
from uwa_cell_motion.common import config,dump
from uwa_cell_motion.geometry import sphere_aabb
from uwa_cell_motion.planning import Problem


def dense(problem,request,q):
    state=problem.state(request,q)
    if not problem.collision.check(state)[0]:return False
    world=problem.spheres.world(state)
    for pair in problem.thresholds():
        problem.spheres.planning_stats['pair_queries']+=1;problem.spheres.planning_stats['fine_queries']+=1
        if problem.spheres.nearest(world,*pair['arms'])['clearance_m']<=pair['threshold_m']:return False
    return True


def uncached(problem,request,q):
    state=problem.state(request,q)
    if not problem.collision.check(state)[0]:return False
    world=problem.spheres.world(state);bounds={r:sphere_aabb(v,problem.spheres.radii[r]) for r,v in world.items()}
    return all(problem.spheres.pair_clear(world,bounds,*p['arms'],p['threshold_m']) for p in problem.thresholds())


def benchmark(problem,dataset,repeats):
    methods={'dense_original':dense,'aabb_uncached':uncached,'aabb_cached':lambda p,r,q:p.check(r,q)}
    expected=[dense(problem,r,q) for r,q in dataset];times={m:[] for m in methods};counts={}
    for repeat in range(repeats):
        order=list(methods);order=order[repeat%3:]+order[:repeat%3]
        for name in order:
            problem.spheres._planning_cache.clear()
            problem.spheres.planning_stats={k:0 for k in problem.spheres.planning_stats}
            began=time.perf_counter();actual=[methods[name](problem,r,q) for r,q in dataset];elapsed=time.perf_counter()-began
            assert actual==expected,(repeat,name)
            times[name].append(elapsed);counts[name]=dict(problem.spheres.planning_stats)
    return dict(states=len(dataset),valid=sum(expected),invalid=len(dataset)-sum(expected),identical_decisions=True,
        methods={m:dict(median_s=float(np.median(t)),min_s=min(t),max_s=max(t),ms_per_state=1000*float(np.median(t))/len(dataset),counters=counts[m]) for m,t in times.items()},
        speedup=float(np.median(times['dense_original'])/np.median(times['aabb_cached'])))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trajectory',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--repeats',type=int,default=5);parser.add_argument('--native',action='store_true');args=parser.parse_args()
    if args.repeats<3:raise ValueError('At least three rotated timing repeats required')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    if (output/'result.json').exists():raise ValueError('Use fresh benchmark output directory')
    saved=json.loads(Path(args.trajectory).read_text())
    if not saved.get('success') or not saved.get('simulation_only'):raise ValueError('Successful simulation trajectory required')
    with tempfile.TemporaryDirectory(prefix='uwa-prefilter-benchmark-') as directory:
        p=Problem(directory,config(saved.get('config_path')),saved.get('layout_path'))
        if p.cfg!=saved['config'] or p.signature!=saved['model_signature'] or p.spheres.geometry.assets!=saved['mesh_sha256']:raise ValueError('Saved plan model/limits differ')
        points=saved['trajectory']['points'];r=saved['request'];trajectory=[(r,points[i]['positions']) for i in np.unique(np.linspace(0,len(points)-1,150).astype(int))]
        from ament_index_python.packages import get_package_share_directory,get_package_prefix
        suite=json.loads((Path(get_package_share_directory('uwa_cell_motion'))/'config/benchmark_suite_20261113.json').read_text());fixed=[]
        for case in suite['cases']:
            request=p.normalize(case['request']);q0=np.array([request['start'][j] for j in request['joint_names']]);target=np.array(request['target'])
            fixed.extend((request,q0+u*(target-q0)) for u in np.linspace(0,1,9))
        result=dict(qualification='Offline identical-state threshold/FCL microbenchmark; no physical execution, no geometry or margin reduction',
            trajectory_source=str(Path(args.trajectory).resolve()),model_signature=p.signature,repeats=args.repeats,
            trajectory=benchmark(p,trajectory,args.repeats),fixed_suite=benchmark(p,fixed,args.repeats))
        # Measure complete CDF planning + final timing/metrics on the same bank.
        from uwa_cell_motion.cdf import ContactBank,plan
        from uwa_cell_motion.cdf_geometry import FrozenScene
        bank=ContactBank.load(Path(args.trajectory).parent/'contacts-0.npz',FrozenScene(p,r));checks={};original_check=p.check
        for name,check in [('dense_original',lambda request,q,margin=True:dense(p,request,q)),('aabb_cached',original_check)]:
            p.check=check;began=time.perf_counter();value=plan(p,r,bank);elapsed=time.perf_counter()-began
            checks[name]=dict(success=value['success'],error=value.get('error'),total_wall_s=elapsed,planning_time_s=value['planning_time_s'])
            dump(output/(name+'-cdf-plan.json'),value)
        p.check=original_check
        baseline=json.loads((output/'dense_original-cdf-plan.json').read_text());filtered=json.loads((output/'aabb_cached-cdf-plan.json').read_text())
        assert baseline['success'] and filtered['success'] and baseline['trajectory']==filtered['trajectory']
        result['cdf_end_to_end']=dict(methods=checks,identical_trajectory=True,speedup=checks['dense_original']['total_wall_s']/checks['aabb_cached']['total_wall_s'],bank_preparation_excluded=True)
        if args.native:
            began=time.perf_counter();path,error=p.rrt(r,0,10.);elapsed=time.perf_counter()-began
            data=json.loads((p.directory/'rrt-result.json').read_text()) if (p.directory/'rrt-result.json').exists() else dict(success=False,error=error)
            native=dict(aabb_cached=dict(wall_s=elapsed,result=data));payload=json.loads((p.directory/'rrt-request.json').read_text());payload['sphere_prefilter']=False
            source=output/'native-dense-request.json';target=output/'native-dense-result.json';dump(source,payload)
            began=time.perf_counter()
            try:
                subprocess.run([str(Path(get_package_prefix('uwa_cell_motion'))/'lib/uwa_cell_motion/rrt_worker'),str(source),str(target)],capture_output=True,text=True,timeout=10.)
                data=json.loads(target.read_text())
            except subprocess.TimeoutExpired:data=dict(success=False,error='TIMEOUT')
            native['dense_original']=dict(wall_s=time.perf_counter()-began,result=data)
            for method,row in native.items():
                if row['result']['success']:p.time_parameterize(r,row['result']['path']);row['full_validation_passed']=True
            result['native_rrt']=native
        dump(output/'result.json',result)
        rows=[]
        for dataset in ('trajectory','fixed_suite'):
            for method,row in result[dataset]['methods'].items():
                rows.append(f'<tr><td>{dataset}</td><td>{method}</td><td>{row["ms_per_state"]:.4f}</td><td>{row["counters"]["prefilter_clear"]}</td><td>{row["counters"]["fine_queries"]}</td></tr>')
        page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>AABB prefilter comparison</title>
<style>body{font:18px sans-serif;background:#111a28;color:white;margin:30px}td,th{padding:12px;border:1px solid white}table{border-collapse:collapse}a{color:#8dddff}h1{color:#ffe080}</style>
<h1>AABB prefilter — OFFLINE comparison</h1><p>Identical states, geometry, thresholds and decisions. Full MoveIt/FCL still runs. Near/contact pairs use the original fine query. No real motion or physics replay.</p>
<p>Five rotated timing repeats by default. This is a microbenchmark of the saved single-arm trajectory and30 fixed tasks, not a universal planning speedup.</p>
<table><tr><th>Dataset</th><th>Method</th><th>ms/state</th><th>Coarse clear</th><th>Fine queries</th></tr>'''+''.join(rows)+'''</table><p>Native RRT and complete CDF timings, cache counters and checks: <a href="result.json">full result</a>.</p></html>'''
        (output/'report.html').write_text(page);print(json.dumps(result,indent=2))


if __name__=='__main__':main()

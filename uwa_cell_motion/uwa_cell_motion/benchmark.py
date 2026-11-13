"""Fixed seeds and preserved failures; offline metrics separate from execution."""
import json
from pathlib import Path
import time
import numpy as np

from .common import ROBOT_IDS, PAIRS, nominal_state, joint_names, dump,sha


def generate_suite(problem):
    rng=np.random.default_rng(20261113);home=nominal_state(problem.layout)
    cases=[];categories=['free','blocked_direct','neighbor_crossing','four_arm','tool_passage','unreachable']
    def request(start,selected,q):
        return dict(schema_version=1,start=start,goals={r:q[i*6:i*6+6].tolist() for i,r in enumerate(selected)})
    for category in categories:
        accepted=0;attempts=0
        while accepted<5 and attempts<4000:
            attempts+=1
            selected=([ROBOT_IDS[accepted%4]] if category in ('free','blocked_direct','unreachable') else
                      list(PAIRS[accepted%4]) if category in ('neighbor_crossing','tool_passage') else list(ROBOT_IDS))
            # Wider joint-space trials produce actual blocked shortcuts and
            # near-tool passages; categorization is checked, never assumed.
            start=dict(home)
            if category in ('blocked_direct','tool_passage'):
                for r in selected:
                    for j in joint_names(r):start[j]+=float(rng.uniform(-.7,.7))
            amplitude={'free':.08,'blocked_direct':1.5,'neighbor_crossing':.4,'four_arm':.15,'tool_passage':.3,'unreachable':.1}[category]
            q=np.asarray([start[j] for r in selected for j in joint_names(r)])+rng.uniform(-amplitude,amplitude,len(selected)*6)
            if category=='unreachable':q[0]=problem.collision.bounds[joint_names(selected[0])[0]][1]+.2
            candidate=request(start,selected,q);normalized=problem.normalize(candidate)
            a=[start[j] for j in normalized['joint_names']]
            if not problem.check(normalized,a):continue
            if category!='unreachable' and not problem.check(normalized,q):continue
            if category=='blocked_direct' and problem.edge(normalized,a,q):continue
            if category=='tool_passage':
                world=problem.spheres.world(problem.state(normalized,q));near=[]
                for pair in problem.thresholds():
                    x,y=pair['arms'];n=problem.spheres.nearest(world,x,y)
                    if any('robotiq' in link or 'wrist_camera' in link for link in n['links']):near.append(n['clearance_m']-pair['threshold_m'])
                if not near or min(near)>.12:continue
            cases.append(dict(id=f'{category}_{accepted+1:02}',category=category,request=candidate,
                              expected_unreachable=category=='unreachable',direct_path_checked=category=='blocked_direct'))
            accepted+=1
        if accepted!=5:
            raise RuntimeError(f'Could generate only {accepted}/5 verified {category} cases after {attempts} trials; no misleading labels written')
        print(f'PREPARED {category}:5/5',flush=True)
    crossings=generate_crossings(problem)
    for case,crossing in zip([c for c in cases if c['category']=='neighbor_crossing'],crossings):
        case['request']={k:crossing[k] for k in ('start','goals')}
        case.update(neighbor_sphere_intersection_verified=True,full_cell_collision_at_crossing=crossing['full_cell_collision_at_crossing'])
    return dict(schema_version=1,generation_version=2,model_signature=problem.signature,mesh_sha256=problem.spheres.geometry.assets,
                generation_seed=20261113,seeds=[0,1,2,3,4],planning_budget_s=10.,cases=cases)


def generate_crossings(problem):
    """Verified intersecting neighbor sphere paths, not merely nearby arms.

    A sphere intersection is a conservative-model crossing, not necessarily a
    physical mesh contact; retain the separate FCL result explicitly.
    """
    rng=np.random.default_rng(12973);home=nominal_state(problem.layout);found=[]
    for attempt in range(20000):
        pair=PAIRS[len(found)%4];names=[j for r in pair for j in joint_names(r)];start=dict(home)
        for j in names:start[j]+=float(rng.uniform(-.8,.8))
        q0=np.array([start[j] for j in names]);q1=q0+rng.uniform(-1.5,1.5,12)
        request=problem.normalize(dict(start=start,goals={a:q1[i*6:i*6+6].tolist() for i,a in enumerate(pair)}))
        if not problem.check(request,q0) or not problem.check(request,q1):continue
        for u in np.linspace(.05,.95,19):
            state=problem.state(request,q0+u*(q1-q0));world=problem.spheres.world(state)
            if problem.spheres.nearest(world,*pair)['clearance_m']<=0:
                found.append(dict(start=start,goals=request['goals'],attempt=attempt,
                    full_cell_collision_at_crossing=not problem.collision.check(state)[0]))
                print(f'VERIFIED crossing {len(found)}/5',flush=True);break
        if len(found)==5:return found
    raise RuntimeError('Could not generate five verified neighbor-sphere crossing cases')


def benchmark(problem,suite,output,limit=None,seeds=5,execute=False):
    if suite['model_signature']!=problem.signature or suite['mesh_sha256']!=problem.spheres.geometry.assets:
        raise ValueError('Benchmark model changed; regenerate suite explicitly')
    if not 1<=seeds<=5:raise ValueError('Seeds must be1..5')
    if problem.cfg['planning_budget_s']!=10.:raise ValueError('Comparison budget is10s per planner')
    directory=Path(output);directory.mkdir(parents=True,exist_ok=True)
    results=[];started=time.monotonic()
    for case in suite['cases'][:limit]:
        try:request=problem.normalize(case['request']);normalization_error=None
        except ValueError as error:request=None;normalization_error=str(error)
        for seed in suite['seeds'][:seeds]:
            for method in ('rrtconnect','circular'):
                path=directory/f"{case['id']}-{seed}-{method}.json"
                if path.exists():
                    previous=json.loads(path.read_text())
                    if previous.get('model_signature')!=problem.signature:raise ValueError('Existing result has a different model')
                    result=previous
                elif normalization_error:
                    result=dict(success=False,error=normalization_error,planning_time_s=0.,method=method,seed=seed,model_signature=problem.signature)
                else:result=problem.plan(request,method,seed,normalized=True)
                result.update(case_id=case['id'],category=case['category'],expected_unreachable=case['expected_unreachable'])
                if execute and result['success'] and 'execution' not in result:
                    from .execution import execute as run
                    result['execution']=run(result,str(path.with_suffix('.execution.json')),restore_start=True)
                dump(path,result);results.append(result)
                summary=summarize(results);summary.update(elapsed_wall_s=time.monotonic()-started,completed=len(results),expected=len(suite['cases'][:limit])*seeds*2,
                                                         complete=len(results)==len(suite['cases'][:limit])*seeds*2,execution_requested=execute)
                dump(directory/'summary.json',summary)
                print(f"DONE {case['id']} seed={seed} {method}: {'PASS' if result['success'] else result.get('error')}",flush=True)
    return summarize(results)


def summarize(results):
    summary={}
    for method in ('rrtconnect','circular'):
        rows=[r for r in results if r['method']==method];success=[r for r in rows if r['success']]
        summary[method]=dict(attempts=len(rows),successes=len(success),failures=len(rows)-len(success),
            success_rate=len(success)/len(rows) if rows else 0.,
            median_planning_time_s=float(np.median([r['planning_time_s'] for r in rows])) if rows else None,
            median_planned_duration_s=float(np.median([r['metrics']['planned_duration_s'] for r in success])) if success else None,
            executions=sum('execution' in r for r in rows),execution_successes=sum(r.get('execution',{}).get('success',False) for r in rows),
            guard_stops=sum(r.get('execution',{}).get('guard_stops',0) for r in rows))
        reachable=[r for r in rows if not r.get('expected_unreachable',False)]
        summary[method].update(valid_goal_attempts=len(reachable),valid_goal_successes=sum(r['success'] for r in reachable),
            expected_unreachable_rejections=sum(not r['success'] and r.get('expected_unreachable',False) for r in rows))
    return summary


def replay_comparison(directory,limit=None):
    """Execute unique successful trajectories; explicitly link identical repeats.

    Seeds test planning variability. Exact duplicate geometric/timed requests
    share an execution record rather than counting one physical run repeatedly.
    """
    from .execution import execute
    directory=Path(directory);groups={};records=[]
    for path in sorted(directory.glob('*.json')):
        value=json.loads(path.read_text())
        if 'case_id' not in value or 'method' not in value:continue
        records.append((path,value))
        if value['success']:
            key=sha(json.dumps([value['request']['start'],value['trajectory']],sort_keys=True))
            groups.setdefault(key,[]).append((path,value))
    completed=0;started=time.monotonic();execution_directory=directory/'executions';execution_directory.mkdir(exist_ok=True)
    ordered=sorted(groups.items(),key=lambda item:item[1][0][1]['trajectory']['duration_s'])
    for key,members in ordered[:limit]:
        output=execution_directory/(key+'.json')
        newly_executed=not output.exists()
        if output.exists():result=json.loads(output.read_text())
        else:
            result=execute(members[0][1],output,restore_start=True)
        for path,value in members:
            value['execution']=dict(result,record=str(output),identical_trajectory_repeats=len(members))
            dump(path,value)
        completed+=1
        summary=json.loads((directory/'summary.json').read_text());summary.update(summarize([r for _,r in records]))
        summary['execution_summary']=dict(unique_trajectories=len(groups),completed_unique=completed,
            successes_unique=sum(json.loads(p.read_text()).get('success',False) for p in execution_directory.glob('*.json')),
            elapsed_wall_s=time.monotonic()-started,complete=completed==len(groups),exact_duplicates_share_record=True)
        dump(directory/'summary.json',summary)
        print(f"EXECUTED {completed}/{len(groups)} {members[0][1]['case_id']}: {result['success']} {result.get('error','')}",flush=True)
        if newly_executed and not result['success']:
            raise RuntimeError('Execution failed; batch stopped and latch retained. Inspect result before an explicit reset/new invocation.')

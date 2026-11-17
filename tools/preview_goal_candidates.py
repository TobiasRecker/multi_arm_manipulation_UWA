#!/usr/bin/env python3
"""Render saved endpoint alternatives with their exact frozen model. No ROS node."""
import argparse,json
from pathlib import Path
import numpy as np
from uwa_cell_motion.common import ROBOT_IDS,joint_names
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_control.parallel_scan import collision_signature

p=argparse.ArgumentParser();p.add_argument('result');p.add_argument('--urdf',required=True);p.add_argument('--output',required=True);p.add_argument('--description',default='');args=p.parse_args()
r=json.loads(Path(args.result).read_text());description=Path(args.urdf).read_text()
if r.get('artifact_type') not in ('offline_goal_candidates','offline_goal_selection') or collision_signature(description)!=r['model_signature']:raise ValueError('Matching saved endpoint result and URDF required')
names={rid:[j for j in r['start'] if j.startswith(rid+'_')] for rid in ROBOT_IDS}
model=SphereModel(description,names,r['configuration']['sphere_spacing_m'])
if model.geometry.assets!=r['mesh_sha256']:raise ValueError('Mesh hashes changed')
frames=model.geometry.fk.frames(r['start']);boxes=[]
for b in model.environment:
 T=frames[b.link]@b.fixed;lo=b.visual_vertices.min(axis=0);hi=b.visual_vertices.max(axis=0)
 corners=np.asarray([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]])
 boxes.append((corners@T[:3,:3].T+T[:3,3]).tolist())
def frame(goals,label,valid,ids):
 state=dict(r['start'])
 for rid,q in goals.items():state.update(zip(joint_names(rid),q))
 return dict(label=label,valid=valid,ids=ids,goals=goals,world={k:v.tolist() for k,v in model.world(state).items()})
combined=[frame(c['goals'],f'Combination {i+1} / {len(r["combinations"])}',True,c['candidate_ids']) for i,c in enumerate(r['combinations'])]
individual={rid:[frame({rid:c['positions']},c['id'],False,[c['id']]) for c in cs] for rid,cs in r['candidates'].items()}
for f,c in zip(combined,r['combinations']):
 f['clearances']=c['pair_clearances']
 if r['artifact_type']=='offline_goal_selection':
  f['label']=c['id']+' — '+', '.join(c['selection_reasons'])
  f['metrics']={k:c[k] for k in ['id','start_distance_sum_rad','min_pair_clearance_m','min_pair_reserve_m','joint_limit_reserve_fraction','selection_reasons']}
spacing=float(np.linalg.norm(frames['left_rear_base_link'][:3,3]-frames['right_rear_base_link'][:3,3]))
data=dict(arms=list(ROBOT_IDS),combined=combined,individual=individual,boxes=boxes,radii={k:v.tolist() for k,v in model.radii.items()},base_spacing_m=spacing,description=args.description)
if r['artifact_type']=='offline_goal_selection':
 data['selection']=dict(search=r['search'],recommended_id=r['recommended_id'],policy_winners=r['policy_winners'],
                        points=[dict(id=c['id'],x=c['start_distance_sum_rad'],y=c['min_pair_clearance_m']*1000,pareto=c['pareto']) for c in r['evaluated_combinations']])
template=Path(__file__).with_name('preview_goal_candidates.html').read_text()
Path(args.output).write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
print(args.output)

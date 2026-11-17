#!/usr/bin/env python3
"""Self-contained animation of checked individual paths and unresolved timing."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct
import tempfile

import numpy as np

from uwa_cell_motion.common import ROBOT_IDS,config,joint_names
from uwa_cell_motion.carton_paths import CartonProblem,diagnose_parallel,path_at


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory')
    parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(args.directory);result=json.loads((root/'paths.json').read_text())
    if result['artifact_type']!='offline_carton_primitive_paths' or result['executable'] is not False:
        raise ValueError('Expected non-executable primitive-path artifact')
    with tempfile.TemporaryDirectory(prefix='uwa-carton-preview-') as d:
        p=CartonProblem(d,config(root/'motion.yaml'),root/'layout.yaml')
        if p.signature!=result['model_signature'] or p.spheres.geometry.assets!=result['mesh_sha256']:
            raise ValueError('Frozen model/mesh identity changed')
        mesh=p.carton['mesh_file'].parent/p.carton['manifest']['solid_mesh'];raw=mesh.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=result['task']['object_mesh_sha256']:raise ValueError('Carton mesh changed')
        triangles=np.array([[struct.unpack_from('<3f',raw,84+k*50+12+i*12) for i in range(3)] for k in range(struct.unpack_from('<I',raw,80)[0])])
        T=p.carton['T_world_object'];triangles=triangles@T[:3,:3].T+T[:3,3]
        start=result['task']['start'];frames=p.spheres.geometry.fk.frames(start);boxes=[]
        for body in p.spheres.environment:
            if body.link=='offline_carton':continue
            lo=body.visual_vertices.min(axis=0);hi=body.visual_vertices.max(axis=0)
            corners=np.array([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]])
            tf=frames[body.link]@body.fixed;boxes.append((corners@tf[:3,:3].T+tf[:3,3]).tolist())
        paths={path['id']:path for values in result['paths'].values() for path in values}
        sets=[]
        thresholds={tuple(sorted(v['arms'])):v['threshold_m'] for v in p.thresholds()}
        for index,combination in enumerate(result['combinations'][:3]):
            selected={arm:paths[pid] for arm,pid in zip(ROBOT_IDS,combination['path_ids'])}
            diagnostic=diagnose_parallel(p,start,selected)
            times=np.linspace(0,diagnostic['duration_s'],241);samples=[];traces={r:[] for r in ROBOT_IDS}
            for time in times:
                state=dict(start);stages={}
                for arm,path in selected.items():
                    state.update(zip(joint_names(arm),path_at(path,float(time))))
                    elapsed=0.;stage='AT FIXED GOAL'
                    for segment in path['segments']:
                        elapsed+=segment['check']['duration_s']
                        if time<elapsed:
                            stage='VERTICAL APPROACH' if segment['kind']=='CARTESIAN_LINE' else 'JOINT TRANSIT';break
                    stages[arm]=stage
                    tcp=p.chains[arm].forward(state)@result['task']['targets'][arm]['tool0_to_tcp']
                    traces[arm].append(tcp[:3,3].round(5).tolist())
                world=p.spheres.world(state);gaps=[]
                for a,b in itertools.combinations(ROBOT_IDS,2):
                    gap=float(p.spheres.nearest(world,a,b)['clearance_m'])
                    threshold=max(p.cfg['model_margin_m'],thresholds.get(tuple(sorted((a,b))),0.))
                    gaps.append(dict(arms=[a,b],gap_mm=round(gap*1000,2),required_mm=round(threshold*1000,2),violation=gap<threshold))
                samples.append(dict(time_s=float(time),world={r:w.round(5).tolist() for r,w in world.items()},
                                    gaps=gaps,fcl_clear=p.collision.check(state)[0],stages=stages))
            sets.append(dict(label=f'Joint solution {index+1} — identical corner targets',
                             id=combination['id'],path_ids=combination['path_ids'],frames=samples,traces=traces,
                             diagnostic=diagnostic,joint_arc_length_sum_rad=combination['joint_arc_length_sum_rad']))
        zero=dict(start)
        for arm in ROBOT_IDS:zero.update(dict.fromkeys(joint_names(arm),0.))
        data=dict(arms=list(ROBOT_IDS),sets=sets,boxes=boxes,carton_triangles=triangles.round(5).tolist(),
                  targets=result['task']['targets'],radii={r:v.tolist() for r,v in p.spheres.radii.items()},
                  zero_world={r:v.round(5).tolist() for r,v in p.spheres.world(zero).items()},
                  task=result['task'],total_path_sets=len(result['combinations']))
        template=Path(__file__).with_name('preview_carton_paths.html').read_text()
        Path(args.output).write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
    print(args.output)


if __name__=='__main__':main()

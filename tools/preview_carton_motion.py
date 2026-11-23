#!/usr/bin/env python3
"""Standalone model animation of a sealed object-led plan, without ROS commands."""
import argparse
import json
from pathlib import Path
import numpy as np
from uwa_cell_tasks.core import verify
from uwa_cell_tasks.scene import verify_scene
from uwa_cell_tasks.planning import TaskProblem
from uwa_cell_description.configuration import load_layout


def render(scene_directory,plan_path,output,layout=None):
    scene=verify_scene(scene_directory);plan=verify(json.loads(plan_path.read_text()))
    recipe=plan['recipe'];start=plan['start']
    problem=TaskProblem(output.parent/'preview-model',(scene_directory/'robot.urdf').read_text(),
                        load_layout(layout),scene,scene['T_world_object'],static=False)
    frames=[];elapsed=0.
    for phase,motion in recipe['motions'].items():
        for i in np.unique(np.linspace(0,len(motion['points'])-1,90).astype(int)):
            point=motion['points'][i];state=dict(start,**dict(zip(motion['joint_names'],point['positions'])))
            world=problem.spheres.world(state)
            frames.append(dict(time=round(elapsed+point['time'],3),phase=phase,
                arms={a:np.round(c,4).tolist() for a,c in world.items()},pose=np.round(point['object_pose'],7).tolist()))
        elapsed+=motion['duration_s']
    vertices=[];faces=[]
    from scipy.spatial import ConvexHull
    for shape in scene['shapes']:
        v=np.array(shape['vertices']);hull=ConvexHull(v);offset=len(vertices)
        faces.extend((hull.simplices+offset).tolist());vertices.extend(v.tolist())
    tables=[]
    from uwa_cell_description.scene_assets import transform
    for name,t in problem.layout['tables'].items():
        tf=transform(t['xyz'],t['rpy']);corners=np.array([[x,y,t['height']] for x,y in
            [(-t['width']/2,-t['length']/2),(t['width']/2,-t['length']/2),(t['width']/2,t['length']/2),(-t['width']/2,t['length']/2)]])
        tables.append(dict(name=name,corners=(corners@tf[:3,:3].T+tf[:3,3]).tolist()))
    data=dict(frames=frames,radii={a:np.round(r,4).tolist() for a,r in problem.spheres.radii.items()},
        vertices=vertices,faces=faces,tables=tables,
        cameras=scene.get('T_world_external_optical', {'oak4': scene['T_world_overview_optical']}),
        duration=elapsed,scene_sha256=scene['sha256'],plan_sha256=plan['sha256'])
    template=Path(__file__).with_suffix('.html').read_text()
    output.write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',required=True,type=Path)
    p.add_argument('--plan',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--layout',type=Path)
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.exists():p.error('Use a new output file')
    render(a.scene,a.plan,a.output,a.layout)

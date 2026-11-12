"""Plot conservative XY sweep envelopes; not a collision or hardware viewer."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
from scipy.spatial import ConvexHull
import yaml


def expanded_polygon(points, padding):
    points=np.asarray(points)
    angle=np.linspace(0,2*np.pi,24,endpoint=False)
    circle=np.column_stack([np.cos(angle),np.sin(angle)])*padding/np.cos(np.pi/24)
    expanded=(points[:,None,:]+circle[None,:,:]).reshape(-1,2)
    return expanded[ConvexHull(expanded).vertices]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();data=json.loads(args.analysis.read_text())
    source=Path(data['source_plan']);plan=json.loads(source.read_text())
    layout=yaml.safe_load((source.parent/'model/layout.yaml').read_text())
    fig,axes=plt.subplots(1,2,figsize=(15,8),facecolor='white')
    colors=dict(zip(data['phases']['all']['arms'],['#2166ac','#00806a','#b96a00','#8945ad']))
    for ax,phase_name in zip(axes,['initial','extra']):
        phase=data['phases'][phase_name]
        for name,table in layout['tables'].items():
            x,y=table['xyz'][:2];w,l=table['width']/2,table['length']/2
            ax.add_patch(Polygon(np.array([[-w,-l],[w,-l],[w,l],[-w,l]])+[x,y],fill=False,edgecolor='#333333',linewidth=1.5))
        unique=[]
        for pair in phase['pairs']:
            n=np.asarray(pair['wall_normal_world'])[:2];c=np.asarray(pair['wall_midpoint_world'])[:2]
            if any(np.linalg.norm(n-m)<1e-3 or np.linalg.norm(n+m)<1e-3 for m in unique):continue
            unique.append(n);tangent=np.array([-n[1],n[0]])
            line=np.array([c-3*tangent,c+3*tangent]);ax.plot(*line.T,'--',color='#747474',linewidth=1,zorder=0)
        for rid,arm in phase['arms'].items():
            poly=expanded_polygon(arm['xy_hull'],arm['max_interpolation_padding_m']+data['required_interarm_clearance_m']/2)
            ax.add_patch(Polygon(poly,facecolor=colors[rid],edgecolor=colors[rid],alpha=.2,linewidth=2))
            ax.plot(*np.vstack([poly,poly[0]]).T,color=colors[rid],linewidth=1.3)
            middle=poly.mean(axis=0)
            ax.text(*middle,rid.replace('_',' '),color=colors[rid],fontsize=11,weight='bold',ha='center',
                    bbox=dict(facecolor='white',alpha=.85,edgecolor='none',pad=2))
        T=np.asarray(plan['T_world_object']);sx,sy=plan['design']['size_m'][:2]
        local=np.array([[-sx/2,-sy/2,0],[sx/2,-sy/2,0],[sx/2,sy/2,0],[-sx/2,sy/2,0]])
        obj=local@T[:3,:3].T+T[:3,3]
        ax.add_patch(Polygon(obj[:,:2],facecolor='#e5a047',edgecolor='#6b3a00',alpha=.65))
        ax.set(xlim=(-1.2,1.2),ylim=(-1.25,1.4),xlabel='World X / m',ylabel='World Y / m')
        ax.set_aspect('equal');ax.grid(alpha=.2)
        ax.set_title('APPROACH TO INITIAL VIEWS' if phase_name=='initial' else 'ADDITIONAL VIEWS',weight='bold')
        status='4 arms: model separation proven' if phase['all_four_phase_independent_separation_proven'] else 'Rear pair: 20 mm clearance not proven'
        ax.text(.5,-.13,status,transform=ax.transAxes,ha='center',weight='bold',fontsize=11)
    fig.suptitle('SCAN SWEEP ENVELOPES — NO HARDWARE MOTION',fontsize=19,weight='bold')
    fig.text(.035,.035,'XY projection: conservative collision-body envelopes, including interpolation and 10 mm buffer per arm.\n'
             'Dashed: base-midpoint walls. XY overlap may still be separated in 3D. Frozen provisional model; no general workspace approval.',fontsize=11)
    fig.tight_layout(rect=[0,.12,1,.93]);args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=140);plt.close(fig);print(args.output)


if __name__=='__main__':main()

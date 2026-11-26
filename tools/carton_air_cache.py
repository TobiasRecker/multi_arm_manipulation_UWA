"""Reuse sealed, unchanged middle paths under exact revolute winding changes.

This is finite offline evidence reuse. It neither subscribes to robot data nor
changes the protection runtime. New acquisition/return connectors are excluded.
"""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import BPoly

CHANGED={'park_left_rear','lift','align_reference','restore_current_pose','set_down'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())


def seal(root,bundle,output):
    root=Path(root).resolve();bundle=Path(bundle).resolve()
    proof=read(root/'qualified/proof.json');draft=read(root/'draft/result.json')
    if not proof.get('success') or not draft.get('success') or len(proof['phases'])!=62:
        raise ValueError('A complete successful air-demo qualification is required')
    paths=[root/'qualified/proof.json',root/'draft/result.json',bundle/'input.json',
           bundle/'hardware.urdf',bundle/'hardware.srdf',bundle/'original.urdf',bundle/'reference.urdf']
    paths += [root/'qualified'/(p['id']+'.json')for p in proof['phases']]
    paths += sorted((bundle/'assets').glob('*'))
    manifest=dict(version=1,root=str(root),bundle=str(bundle),files={str(p):sha(p)for p in paths})
    Path(output).write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


class Cache:
    def __init__(self,manifest_path,data,bundle):
        self.path=Path(manifest_path).resolve();self.manifest=read(self.path)
        if self.manifest.get('version')!=1:raise ValueError('Unknown evidence cache version')
        for name,digest in self.manifest['files'].items():
            if sha(name)!=digest:raise ValueError('Cached evidence changed: '+name)
        self.root=Path(self.manifest['root']);oldbundle=Path(self.manifest['bundle'])
        old=read(oldbundle/'input.json');self.draft=read(self.root/'draft/result.json')
        self.proof=read(self.root/'qualified/proof.json')
        if (self.proof['sources'].get('/input/input.json')!=sha(oldbundle/'input.json')
                or self.proof['sources'].get('/output/draft/result.json')!=sha(self.root/'draft/result.json')):
            raise ValueError('Cached source and completed qualification do not agree')
        for name in ('hardware.urdf','hardware.srdf','original.urdf','reference.urdf'):
            if sha(oldbundle/name)!=sha(Path(bundle)/name):
                raise ValueError('Cached hardware/reference model differs: '+name)
        oldassets={p.name:sha(p)for p in (oldbundle/'assets').glob('*')}
        newassets={p.name:sha(p)for p in (Path(bundle)/'assets').glob('*')}
        if oldassets!=newassets:raise ValueError('Cached collision mesh contents differ')
        for key in ('config','names','reference_initial','reference_group','phases',
                    'object_boxes','object_shapes','dimensions_m','task_obstacles','model_identity'):
            if old.get(key)!=data.get(key):raise ValueError('Cached task geometry differs: '+key)
        if (not self.proof.get('success') or not self.draft.get('success')
                or self.draft.get('work_offset_m')!=[0.,0.,0.]
                or self.draft.get('opposite_roll_deg')!=0.
                or self.draft.get('opposite_pose_center_xyz_rpy_deg') is not None
                or self.draft.get('contact_model')!='physical_skin_and_outer_hull'):
            raise ValueError('Only the complete canonical simulation-grip qualification is reusable')
        self.phases={p['id']:p for p in self.draft['phases']}
        self.shift=None

    def bind_contact(self,offsets,jaws):
        for arm,offset in offsets.items():
            if not np.allclose(offset,self.draft['proposed_offsets'][arm],atol=1e-12,rtol=0):
                raise ValueError('Cached rigid grasp differs')
        if jaws!=self.draft['nominal_jaws']:raise ValueError('Cached nominal contact geometry differs')

    def coarse(self,identifier,state,bounds):
        if identifier in CHANGED:return None
        result=copy.deepcopy(self.phases[identifier]);first=result['samples'][0]['positions']
        delta={j:float(state[j]-q)for j,q in first.items()}
        turns={j:int(round(v/(2*np.pi)))for j,v in delta.items()}
        if any(abs(delta[j]-2*np.pi*turns[j])>1e-7 for j in delta):
            raise ValueError(identifier+': changed cache junction is not an exact winding equivalence')
        if self.shift is None:self.shift={j:2*np.pi*n for j,n in turns.items()}
        if any(abs(self.shift[j]-delta[j])>1e-7 for j in delta):
            raise ValueError('Cached middle winding changed between phases')
        for row in result['samples']:
            for j in row['positions']:
                row['positions'][j]+=self.shift[j]
                if j in bounds and not bounds[j][0]<=row['positions'][j]<=bounds[j][1]:
                    raise ValueError('Equivalent cached path exceeds a joint limit')
        result['reuse_qualified']=dict(manifest_sha256=sha(self.path),manifest=str(self.path),
            record_sha256=sha(self.root/'qualified'/(identifier+'.json')),winding_shift_rad=self.shift)
        return result


def controller_record(phase,previous,bounds):
    reuse=phase['reuse_qualified'];manifest=Path(reuse['manifest'])
    if sha(manifest)!=reuse['manifest_sha256']:raise ValueError('Cache manifest changed')
    archive=read(manifest);path=Path(archive['root'])/'qualified'/(phase['id']+'.json')
    if sha(path)!=reuse['record_sha256'] or archive['files'][str(path)]!=sha(path):
        raise ValueError('Cached controller path changed')
    record=read(path);shift=reuse['winding_shift_rad']
    for j,q in record['start'].items():
        if abs(q+shift[j]-previous[j])>1e-7:raise ValueError('Cached controller junction changed')
    record['start']=dict(previous)
    record['end']={j:q+shift[j]for j,q in record['end'].items()}
    for trajectory in record['trajectories'].values():
        joints=trajectory['joint_names']
        for point in trajectory['points']:
            point['positions']=[q+shift[j]for j,q in zip(joints,point['positions'],strict=True)]
        curve=BPoly.from_derivatives([r['time']for r in trajectory['points']],
            [[r[k]for k in ('positions','velocities','accelerations')]for r in trajectory['points']])
        # Bernstein control points bound every interpolated position, not only knots.
        for k,j in enumerate(joints):
            if curve.c[:,:,k].min()<bounds[j][0] or curve.c[:,:,k].max()>bounds[j][1]:
                raise ValueError('Equivalent controller polynomial exceeds joint bounds')
    record['reused_qualification']=reuse
    return record

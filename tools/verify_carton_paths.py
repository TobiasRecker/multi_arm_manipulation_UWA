#!/usr/bin/env python3
"""Independent denser evaluation of the stored cubic primitives and fixed targets."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation

from uwa_cell_motion.carton_paths import CartonProblem
from uwa_cell_motion.common import config,dump,joint_names


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory')
    parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(args.directory);result=json.loads((root/'paths.json').read_text())
    if Path(args.output).exists():raise ValueError('Choose a fresh verification output')
    count=0;max_position=0.;max_angle=0.;max_step=0.;npaths=0
    with tempfile.TemporaryDirectory(prefix='uwa-carton-verify-') as directory:
        p=CartonProblem(directory,config(root/'motion.yaml'),root/'layout.yaml')
        assert result['model_signature']==p.signature
        assert result['mesh_sha256']==p.spheres.geometry.assets
        mesh=p.carton['mesh_file'].parent/p.carton['manifest']['solid_mesh']
        assert hashlib.sha256(mesh.read_bytes()).hexdigest()==result['task']['object_mesh_sha256']
        start=result['task']['start']
        assert p.collision.check(start)[0]
        for arm,paths in result['paths'].items():
            names=joint_names(arm);target=np.asarray(result['task']['targets'][arm]['tool0_target'])
            for path in paths:
                previous=np.asarray([start[j] for j in names]);npaths+=1
                for segment in path['segments']:
                    assert np.allclose(previous,segment['positions'][0],rtol=0,atol=1e-9)
                    spline=CubicSpline(segment['knots'],segment['positions'],bc_type='natural')
                    u=np.linspace(0,1,max(513,2*segment['check']['samples']-1))
                    progress=u**3*(10+u*(-15+6*u));positions=spline(progress)
                    max_step=max(max_step,float(np.max(abs(np.diff(positions,axis=0)))))
                    for s,q in zip(progress,positions):
                        state=dict(start,**dict(zip(names,q)));assert p.isolated[arm].check(state)[0]
                        count+=1
                        if segment['kind']=='CARTESIAN_LINE':
                            wanted=target.copy();wanted[2,3]+=.12*(1-s)
                            actual=p.chains[arm].forward(state)
                            position=float(np.linalg.norm(actual[:3,3]-wanted[:3,3]))
                            angle=float(np.linalg.norm(Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).as_rotvec()))
                            max_position=max(max_position,position);max_angle=max(max_angle,angle)
                            assert position<=1e-4 and angle<=1e-3
                    previous=positions[-1]
                final=dict(start,**dict(zip(names,previous)));actual=p.chains[arm].forward(final)
                assert np.linalg.norm(actual[:3,3]-target[:3,3])<=1e-4
                assert np.linalg.norm(Rotation.from_matrix(actual[:3,:3]@target[:3,:3].T).as_rotvec())<=1e-3
                tcp=actual@result['task']['targets'][arm]['tool0_to_tcp']
                assert np.linalg.norm(tcp[:3,3]-result['task']['targets'][arm]['tcp_world_m'])<=1e-4
        assert max_step<=.005
        report=dict(status='PASS',paths=npaths,static_collision_samples=count,
                    max_joint_step_rad=max_step,max_cartesian_position_error_m=max_position,
                    max_cartesian_orientation_error_rad=max_angle,model_signature=p.signature,
                    scope='Independent denser evaluation of individual paths; no timing coordination or physical grasp proof')
        dump(args.output,report);print(json.dumps(report))


if __name__=='__main__':main()

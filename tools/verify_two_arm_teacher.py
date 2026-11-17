#!/usr/bin/env python3
"""Independent two-arm FK/gradient checks and deliberate negative controls."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation
from uwa_cell_motion.common import ROBOT_IDS,joint_names,dump
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher,pose_at
from uwa_cell_motion.object_transport import yaw_basis
from uwa_cell_motion.smooth_paths import sample_segment


def object_features(problem,pose,state,indices=None):
    """Independent fixed-sphere distance for testing a selected min branch.

    Equal nearest spheres make the minimum nondifferentiable. The analytic
    derivative is of the selected sphere, not an arbitrary central average
    of two different nearest spheres.
    """
    model=problem.problem.spheres;world=model.world(state);values=[];selected=[]
    for k,arm in enumerate(ROBOT_IDS):
        ids=[i for i,link in enumerate(model.links[arm]) if not ('_robotiq_' in link or '_wrist_camera_' in link or link.endswith('_wrist_3_link'))]
        local=(world[arm][ids]-pose[:3,3])@pose[:3,:3];q=np.abs(local)-problem.dimensions/2
        distance=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(q.max(axis=1),0)-model.radii[arm][ids]
        nearest=int(np.argmin(distance));selected.append(ids[nearest])
        index=nearest if indices is None else ids.index(indices[k]);values.append(distance[index])
    return np.array(values),selected


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('result',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('Verification output exists')
    raw=args.result.read_bytes();report=json.loads(raw)
    for filename,wanted in report['code_sha256'].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest()!=wanted:raise ValueError('Changed code: '+filename)
    with tempfile.TemporaryDirectory(prefix='uwa-two-arm-verify-') as directory:
        p=TwoArmTeacher(directory,report['source_path'],elevation=report['elevation_m'])
        assert p.source_sha256==report['source_sha256'] and p.problem.signature==report['model_signature']
        assert p.problem.spheres.geometry.assets==report['mesh_sha256']
        assert np.allclose(p.initial,report['initial_pose'],atol=1e-12)
        assert p.arms==('right_front','right_rear') and len(p.names)==12
        inactive=set(ROBOT_IDS)-set(p.arms)
        for arm in inactive:
            assert all(p.start[n]==p.saved['task']['start'][n] for n in joint_names(arm))
        assert p.grasp_sides=={'right_front':'x_min','right_rear':'x_max'}
        # The original side-centre targets are fixed, not arbitrary FK offsets.
        for arm,side in p.grasp_sides.items():
            o=p.offsets[arm];local=o[:3,3]+p.dimensions/2
            assert abs(local[0]-(0 if side=='x_min' else p.dimensions[0]))<1e-8
            assert abs(local[1]-p.dimensions[1]/2)<1e-8
        assert p.full_check(p.initial,p.start)
        lowered=p.initial.copy();lowered[2,3]-=.2
        assert not p.full_check(lowered,p.start),'Moving carton/table negative was missed'
        assert p.full_check(p.initial,p.start)
        checks=[];maxK=maxgap=maxobject=0.;accepted=0;timing=[];feature_switches=0
        for case in report['cases']:
            if not case.get('accepted_variant'):continue
            accepted+=1;variant=next(v for v in case['variants'] if v['label']==case['accepted_variant'])
            trajectory=variant['trajectory'];assert variant['validation']['passed']
            controls=np.array(trajectory['controls']);rows=p.path_rows(case['task'],controls,count=101)
            for row in [rows[23],rows[51],rows[77]]:
                pose=np.array(row['pose']);state=dict(p.start,**dict(zip(p.names,row['q'])))
                K,_=p.differential(pose,state);pairs=p.distances(pose,state,True)
                values,objJ=p.object_arm_gaps(pose,state,True)
                independently,features=object_features(p,pose,state)
                assert np.allclose(independently,values,atol=1e-12)
                fdK=np.zeros_like(K);fdgap=np.zeros((6,6));fdobj=np.zeros((4,6));eps=1e-5
                for axis in range(6):
                    both=[]
                    for sign in [-1,1]:
                        X=pose.copy()
                        if axis<3:X[axis,3]+=sign*eps
                        else:
                            v=np.zeros(3);v[axis-3]=sign*eps;X[:3,:3]=Rotation.from_rotvec(v).as_matrix()@pose[:3,:3]
                        q=p.solve(X,state)
                        fixed,nearest=object_features(p,X,q,features)
                        feature_switches+=sum(a!=b for a,b in zip(features,nearest))
                        both.append((np.array([q[n] for n in p.names]),np.array([v['clearance_m'] for v in p.distances(X,q)]),fixed))
                    fdK[:,axis]=(both[1][0]-both[0][0])/(2*eps)
                    fdgap[:,axis]=(both[1][1]-both[0][1])/(2*eps)
                    fdobj[:,axis]=(both[1][2]-both[0][2])/(2*eps)
                eK=float(np.max(abs(fdK-K)));eG=float(np.max(abs(fdgap-np.array([r['gradient'] for r in pairs]))));eO=float(np.max(abs(fdobj-objJ)))
                maxK=max(maxK,eK);maxgap=max(maxgap,eG);maxobject=max(maxobject,eO)
                assert eK<2e-4 and eG<2e-4 and eO<2e-4,(eK,eG,eO)
                checks.append(dict(case=case['id'],s=row['s'],K_error=eK,pair_error=eG,object_arm_error=eO))
            segment=trajectory['segment'];T=trajectory['duration_s'];peaks=[]
            for derivative,cap in [(1,.45),(2,.4),(3,2.)]:
                peak=float(np.max(abs(sample_segment(segment,np.linspace(0,T,20001),derivative))))
                assert peak<=cap+1e-7
                assert np.max(abs(sample_segment(segment,[0,T],derivative)))<1e-8
                peaks.append(peak)
            # Independently verify the prescribed endpoints and common clock.
            for s,t in [(0,0),(1,T)]:
                pose,state,_=p.sample(trajectory,t)
                assert np.allclose(pose,pose_at(p.initial,case['task'],s,np.zeros((6,6))),atol=1e-10)
                for arm in inactive:assert all(state[n]==p.start[n] for n in joint_names(arm))
            timing.append(dict(case=case['id'],dense_samples=20001,derivative_peaks=peaks))
        assert accepted>=1
        dump(args.output,dict(passed=True,result_sha256=hashlib.sha256(raw).hexdigest(),accepted_examples=accepted,
            active_joints=12,stationary_arms=sorted(inactive),moving_object_negative_passed=True,
            max_joint_jacobian_error=maxK,max_pair_gradient_error=maxgap,max_object_arm_gradient_error=maxobject,
            nearest_object_sphere_switches=feature_switches,
            object_gradient_scope='Finite difference of the selected sphere feature; ties in the minimum are nondifferentiable and counted separately',
            gradient_checks=checks,timing_checks=timing,
            scope='Independent finite-difference kinematics/gradients, dense derivative sampling, endpoints and negative geometry; not continuous collision proof'))
        print('PASS',accepted,'examples; gradient errors',maxK,maxgap,maxobject)


if __name__=='__main__':main()

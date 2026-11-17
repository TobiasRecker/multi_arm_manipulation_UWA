#!/usr/bin/env python3
"""Independent FK/IK finite-difference and negative moving-object checks."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
from scipy.spatial.transform import Rotation
from uwa_cell_motion.common import dump
from uwa_cell_motion.object_transport import ObjectTransport,object_pose


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('result',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    raw=args.result.read_bytes();saved=json.loads(raw)
    with tempfile.TemporaryDirectory(prefix='uwa-object-verify-') as directory:
        p=ObjectTransport(directory,saved['source_path']);checks=[];maximum_q=maximum_gap=0.
        assert saved['source_sha256']==p.source_sha256
        assert p.full_check(p.initial,p.start)
        lowered=p.initial.copy();lowered[2,3]-=.02
        assert not p.full_check(lowered,p.start),'Moving object into table was not detected'
        assert p.full_check(p.initial,p.start),'Object failed to move back out of collision'
        for variant in saved['variants']:
            assert variant['validation']['passed']
            rows=p.path(saved['offset_m'],saved['lift_m'],variant['trajectory']['controls'],61)
            for row in [rows[0],rows[len(rows)//2],rows[-1]]:
                pose=np.array(row['pose']);state=dict(p.start,**dict(zip(p.names,row['q'])))
                K,_=p.differential(pose,state);pairs=p.distances(pose,state,gradients=True)
                q_fd=np.zeros_like(K);gap_fd=np.zeros((6,6));eps=1e-5
                for axis in range(6):
                    values=[]
                    for sign in [-1,1]:
                        delta=np.zeros(6);delta[axis]=sign*eps;X=pose.copy();X[:3,3]+=delta[:3]
                        X[:3,:3]=Rotation.from_rotvec(delta[3:]).as_matrix()@pose[:3,:3]
                        moved=p.solve(X,state);near=p.distances(X,moved)
                        values.append((np.array([moved[j] for j in p.names]),np.array([v['clearance_m'] for v in near])))
                    q_fd[:,axis]=(values[1][0]-values[0][0])/(2*eps)
                    gap_fd[:,axis]=(values[1][1]-values[0][1])/(2*eps)
                qe=float(np.max(abs(q_fd-K)));ge=float(np.max(abs(gap_fd-np.array([v['gradient'] for v in pairs]))))
                maximum_q=max(maximum_q,qe);maximum_gap=max(maximum_gap,ge)
                checks.append(dict(variant=variant['label'],progress=row['s'],max_joint_jacobian_error=qe,max_gap_gradient_error=ge))
                assert qe<2e-4 and ge<2e-4,(qe,ge)
        # The yaw experiment must address a real extra-clearance deficit, rather
        # than merely moving a carton whose original path met that new demand.
        baseline=p.path(saved['offset_m'],saved['lift_m'],count=241)
        demanding=p.check_path(baseline,extra_margin=.04)
        assert not demanding['passed']
        result=dict(passed=True,result_sha256=hashlib.sha256(raw).hexdigest(),
            moving_object_table_negative_passed=True,baseline_fails_extra_clearance=True,
            baseline_extra_clearance_failure_samples=len(demanding['failures']),
            max_joint_jacobian_error=maximum_q,max_distance_gradient_error=maximum_gap,checks=checks)
        dump(args.output,result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()

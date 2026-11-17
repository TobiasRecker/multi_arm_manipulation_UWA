from collections import defaultdict
import numpy as np
from scipy.spatial.transform import Rotation
from uwa_cell_motion.teacher_starts import start_families,make_pose,wrapped_distance,coverage


def test_starts_are_substantially_different_and_families_keep_all_tasks():
    families=start_families();assert families==start_families()
    assert len({f['id'] for f in families})==12
    assert {f['split'] for f in families}=={'train','validation','test'}
    for f in families:
        assert len(f['tasks'])==2
        assert np.linalg.norm(f['translation_m'])>.1
        assert np.linalg.norm(f['rotation_vector_deg'])>20
    xyz=np.array([f['translation_m'] for f in families])
    assert np.all(np.ptp(xyz,axis=0)>=[.3,.3,.1])


def test_pose_rotates_around_object_centre_and_joint_wraps_not_counted_as_branch():
    anchor=np.eye(4);anchor[:3,3]=[.1,.2,1.]
    anchor[:3,:3]=Rotation.from_euler('xyz',[.1,.3,-.5]).as_matrix()
    f=start_families()[0];pose=make_pose(anchor,f)
    assert np.allclose(pose[:3,3],anchor[:3,3]+f['translation_m'])
    assert np.allclose(pose[:3,:3],Rotation.from_rotvec(np.deg2rad(f['rotation_vector_deg'])).as_matrix()@anchor[:3,:3])
    assert wrapped_distance([0,1,2],[2*np.pi,1-2*np.pi,2])<1e-12
    assert wrapped_distance([0,1,2],[0,-1,2])>1


def test_coverage_excludes_failed_start_and_reports_geodesic_rotation():
    a=np.eye(4);b=np.eye(4);b[0,3]=.2;b[:3,:3]=Rotation.from_euler('y',60,degrees=True).as_matrix()
    rows=[dict(initial_pose=p.tolist(),selected=dict(check=dict(pair_gap_m=.04)),valid_candidates=2) for p in [a,b]]
    rows.append(dict(selected=None))
    result=coverage(rows,a)
    assert result['valid_starts']==2
    assert abs(result['max_pair_orientation_angle_deg']-60)<1e-10
    assert abs(result['max_pair_position_distance_m']-.2)<1e-12
    assert result['families_with_alternative_valid_ik']==2

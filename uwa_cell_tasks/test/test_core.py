import json
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from match_cooperative_handling.rigid_object import tcp_target, common_scale, interpolate, rigid
from uwa_cell_tasks.core import GraspGroup, RunStore, ARMS, seal, verify


CFG=dict(relative_position_tolerance_m=.002,relative_angle_tolerance_rad=np.pi/180)


def group():
    tcps={a:np.eye(4) for a in ARMS}
    tcps[ARMS[0]][0,3]=-.2;tcps[ARMS[1]][0,3]=.2
    return GraspGroup('carton',np.eye(4),tcps,
        {a:dict(left_pad=True,right_pad=True) for a in ARMS},CFG)


def test_object_rotation_has_opposite_tangential_tcp_velocities():
    g=group();targets=g.targets(np.eye(4),[0,0,0,0,0,1])
    assert targets[ARMS[0]][1][1]==pytest.approx(-.2)
    assert targets[ARMS[1]][1][1]==pytest.approx(.2)
    end=np.eye(4);end[:3,:3]=Rotation.from_euler('z',np.pi/2).as_matrix()
    assert g.targets(end)[ARMS[0]][0][:3,3]==pytest.approx([0,-.2,0])


def test_shared_saturation_preserves_both_members_ratio():
    s,commands=common_scale({'a':[2.,1.],'b':[.5,1.]},{'a':[1.,1.],'b':[1.,1.]})
    assert s==.5;assert commands['b']==pytest.approx([.25,.5])


def test_contact_required_and_offsets_are_not_mutable():
    with pytest.raises(ValueError):GraspGroup('box',np.eye(4),{a:np.eye(4) for a in ARMS},
        {a:dict(left_pad=True,right_pad=False) for a in ARMS},CFG)
    g=group();copy=g.offsets;copy[ARMS[0]][0,3]=100
    assert g.offsets[ARMS[0]][0,3]==-.2


def test_slip_stops_whole_group_and_forbids_resume():
    g=group();tcps={a:t for a,(t,_) in g.targets(np.eye(4)).items()}
    tcps[ARMS[0]][2,3]+=.003
    assert not g.check(np.eye(4),tcps);assert g.stop('other fault')==ARMS
    with pytest.raises(RuntimeError):g.targets(np.eye(4))
    with pytest.raises(RuntimeError):g.release(supported=False,stationary=True)
    g.release(supported=True,stationary=True)


def test_review_is_bound_to_revision_and_evidence(tmp_path):
    store=RunStore(tmp_path);first=store.request_review('review_plan',dict(plan='a'))
    store.submit_review(first['sha256'],'continue','Reviewed collision report')
    assert store.decision(first)['decision']=='continue'
    second=store.request_review('review_plan',dict(plan='b'))
    assert store.decision(second) is None
    with pytest.raises(ValueError):store.submit_review(first['sha256'],'continue','old')
    second['evidence']['plan']='tampered'
    with pytest.raises(ValueError):verify(second)


def test_invalid_transform_is_not_accepted_as_pose():
    reflected=np.eye(4);reflected[0,0]=-1
    with pytest.raises(ValueError):rigid(reflected)
    malformed=np.eye(4);malformed[0,3]=np.nan
    with pytest.raises(ValueError):tcp_target(malformed,np.eye(4))
    end=np.eye(4);end[2,3]=.03
    assert interpolate(np.eye(4),end,.5)[2,3]==pytest.approx(.015)


def test_noiseless_renderer_does_not_weaken_real_frame_freshness():
    from types import SimpleNamespace
    from uwa_cell_tasks.observation import rendered_static_pose
    class Estimator:
        calls=0
        def register(self,*args):
            self.calls+=1;return SimpleNamespace(status='VALID',inliers=42,reason='single render')
    e=Estimator();frames=[np.zeros((8,8,3),np.uint8)]*3
    records=[dict(environment='own_gazebo_renderer',stamp=t) for t in (1.,2.,3.)]
    result=rendered_static_pose(e,frames,np.eye(3),[],records)
    assert result.inliers==42 and e.calls==1
    with pytest.raises(ValueError):rendered_static_pose(e,frames,np.eye(3),[],[dict(r,environment='physical') for r in records])
    with pytest.raises(ValueError):rendered_static_pose(e,frames,np.eye(3),[],[dict(r,stamp=1.) for r in records])

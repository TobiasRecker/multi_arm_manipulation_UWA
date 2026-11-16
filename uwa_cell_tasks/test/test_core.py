import json
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from match_cooperative_handling.rigid_object import tcp_target, common_scale, interpolate, rigid
from uwa_cell_tasks.core import GraspGroup, RunStore, ARMS, seal, verify, resource_lease,gripper_profile,measured_open,object_point_height


CFG=dict(relative_position_tolerance_m=.002,relative_angle_tolerance_rad=np.pi/180)


def test_lift_reference_is_declared_com_and_keeps_corner_motion_separate():
    com=np.array([.20,.17,.05]);start=np.eye(4)
    end=np.eye(4);end[:3,:3]=Rotation.from_euler('y',.011).as_matrix()
    end[2,3]=.03-((end[:3,:3]@com)[2]-com[2])
    assert object_point_height(end,com)-object_point_height(start,com)==pytest.approx(.03)
    assert abs(end[2,3]-.03)>.002
    shift=np.eye(4);shift[2,3]=.03
    assert object_point_height(shift,com)-object_point_height(start,com)==pytest.approx(.03)
    with pytest.raises(ValueError):object_point_height(start,[0.,float('nan'),0.])


def test_open_confirmation_requires_actual_passive_fingers_and_standstill():
    names=['driver','passive'];q=dict(driver=.008,passive=-.009);v=dict(driver=0.,passive=0.)
    assert measured_open(names,q,v)
    assert not measured_open(names,dict(q,passive=.798),v)
    assert not measured_open(names,{'driver':0.},v)
    assert not measured_open(names,q,dict(v,passive=.004))
    assert not measured_open(names,dict(q,passive=float('nan')),v)
    assert not measured_open([],{}, {})


def test_contact_qualification_rejects_accelerated_physics(tmp_path):
    import yaml
    from uwa_cell_tasks.core import configuration
    cfg=configuration();cfg['simulation_real_time_factor']=1.01
    path=tmp_path/'accelerated.yaml';path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='unaccelerated'):configuration(path)


def test_native_gears_cannot_silently_run_with_unsupported_dart_engine(tmp_path):
    import yaml
    from uwa_cell_tasks.core import configuration
    cfg=configuration();cfg['physics_engine']='dartsim';cfg['gripper_transmission']='native_gear'
    path=tmp_path/'unsupported.yaml';path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='require Bullet Featherstone'):configuration(path)


def test_two_recipes_cannot_own_the_same_controller_resources(tmp_path):
    with resource_lease('/uwa_grasp_test',tmp_path):
        with pytest.raises(RuntimeError,match='Another task owns'):
            with resource_lease('/uwa_grasp_test',tmp_path):pytest.fail('Concurrent controller ownership')
        with resource_lease('/uwa_grasp_other',tmp_path):pass
    with resource_lease('/uwa_grasp_test',tmp_path):pass


def test_contact_closure_slows_before_the_wall_but_opening_remains_coarse():
    cfg=dict(gripper_coarse_velocity_rad_s=.02,gripper_fine_velocity_rad_s=.004,gripper_fine_start_rad=.65)
    closing=gripper_profile([.01,.03],.8,cfg);points=closing['points']
    q=np.array([p['positions'] for p in points]);t=np.array([p['time'] for p in points])
    assert q[0]==pytest.approx([.01,.03]) and q[-1]==pytest.approx([.8,.8])
    velocity=np.diff(q,axis=0)/np.diff(t)[:,None]
    assert (velocity>=-1e-12).all() and velocity.max()<=.02+1e-12
    assert velocity[(q[:-1]>.66).all(axis=1)].max()<=.004+1e-12
    assert 60<closing['duration_s']<80
    opening=gripper_profile([.8,.78],0.,cfg)
    assert opening['duration_s']==pytest.approx(40.)
    assert opening['points'][-1]['positions']==pytest.approx([0.,0.])


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

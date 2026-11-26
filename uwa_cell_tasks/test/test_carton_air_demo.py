"""The finite dry-run adapter cannot silently continue a changed grasp."""
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from scipy.interpolate import BPoly, make_interp_spline

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
import prepare_carton_air_demo as demo
from qualify_carton_air_demo import controller_points
from prepare_carton_air_demo import bind_grip, carton_coordinates, HOLDERS
from uwa_cell_motion.common import joint_names


def fixture():
    state={j:0. for a in HOLDERS for j in joint_names(a)}
    proof=dict(success=True,height_m=.020,end=state)
    obs=dict(arms={a:dict(observed=True,samples=[dict(actual_q=[0.]*6)])for a in HOLDERS})
    binding=dict(world_object_by_arm={a:np.eye(4).tolist()for a in HOLDERS})
    chains={a:SimpleNamespace(forward=lambda state:np.eye(4))for a in HOLDERS}
    return proof,obs,binding,chains


def test_current_grip_retains_measured_lift_and_both_tool_offsets():
    proof,obs,binding,chains=fixture()
    state,pose,offsets=bind_grip(proof,obs,binding,chains)
    assert pose[2,3]==pytest.approx(.020)
    for arm in HOLDERS:
        np.testing.assert_allclose(pose@offsets[arm],chains[arm].forward(state))


def test_changed_holder_is_not_reinterpreted_as_an_old_successful_grasp():
    proof,obs,binding,chains=fixture()
    obs['arms']['right_rear']['samples'][0]['actual_q'][2]=.1
    with pytest.raises(ValueError,match='current joints differ'):
        bind_grip(proof,obs,binding,chains)


def test_two_separate_registered_poses_are_not_averaged():
    proof,obs,binding,chains=fixture()
    binding['world_object_by_arm']['right_rear'][0][3]=.02
    with pytest.raises(ValueError,match='common registered'):
        bind_grip(proof,obs,binding,chains)


def test_failed_lift_is_not_a_continuation_source():
    proof,obs,binding,chains=fixture();proof['success']=False
    with pytest.raises(ValueError,match='successful checked'):
        bind_grip(proof,obs,binding,chains)


@pytest.mark.parametrize('angles',[(.2,-.4,.8),(-1.4,1.1,-2.8),(0.,np.pi/2,0.)])
def test_carton_auxiliary_chain_reconstructs_full_pose(angles):
    pose=np.eye(4);pose[:3,:3]=Rotation.from_euler('xyz',angles).as_matrix()
    pose[:3,3]=[.4,-.2,.7]
    values=carton_coordinates(pose)
    actual=np.eye(4);actual[:3,3]=[values['air_demo_'+a+'_joint']for a in ('x','y','z')]
    actual[:3,:3]=Rotation.from_euler('ZYX',[values['air_demo_'+a+'_joint']
        for a in ('yaw','pitch','roll')]).as_matrix()
    np.testing.assert_allclose(actual,pose,atol=1e-12)


def test_incomplete_cell_is_not_silently_filled_with_parked_arms():
    proof,obs,binding,chains=fixture();chains['left_rear']=chains['right_rear']
    with pytest.raises(ValueError,match='Complete current four-arm'):
        bind_grip(proof,obs,binding,chains)


def test_free_arm_route_rejects_colliding_middle_even_with_clear_endpoint(monkeypatch):
    arm='left_front';names=joint_names(arm);start=dict.fromkeys(names,0.)
    goal=np.array([2.,2.,0.,0.,0.,0.])
    def check(problem,held,data,state,pose):
        if .8<state[names[0]]<1.2 and .8<state[names[1]]<1.2:
            raise ValueError('middle of direct path intersects table')
        return 1.
    monkeypatch.setattr(demo,'check_state',check)
    route=demo.free_route(None,None,{},start,np.eye(4),arm,[goal])
    assert len(route)==3
    np.testing.assert_allclose(route[-1],goal)


def test_all_blocked_free_routes_do_not_return_an_endpoint_only_plan(monkeypatch):
    arm='left_front';start=dict.fromkeys(joint_names(arm),0.)
    def check(*args,**kwargs):raise ValueError('blocked')
    monkeypatch.setattr(demo,'check_state',check)
    with pytest.raises(ValueError,match='no checked direct/upright'):
        demo.free_route(None,None,{},start,np.eye(4),arm,[np.ones(6)])


def test_home_keeps_nearest_winding_inside_limits():
    arm='left_rear';names=joint_names(arm)
    problem=SimpleNamespace(collision=SimpleNamespace(bounds=dict.fromkeys(names,(-2*np.pi,2*np.pi))))
    start=dict(zip(names,[-4.65,-1.7,2.2,-2.08,-1.56,1.47]))
    q=demo.nearest_home(problem,start,arm)
    assert q[0]==pytest.approx(-2*np.pi+.001)
    assert np.all(q>-2*np.pi) and np.all(q<2*np.pi)


@pytest.mark.parametrize('angle',[-90.,45.,90.,180.])
def test_opposite_circle_clocking_preserves_wall_normal_and_carton_center(angle):
    dims=np.array([.404,.342,.163]);pose=np.eye(4)
    pose[:3,:3]=Rotation.from_euler('xyz',[160.,0.,145.],degrees=True).as_matrix()
    pose[:3,3]=[.2,-.1,1.3]
    changed=demo.roll_face_pose(pose,dims,angle)
    np.testing.assert_allclose(changed[:3,1],pose[:3,1],atol=1e-12)
    np.testing.assert_allclose(changed[:3,:3]@(dims/2)+changed[:3,3],
                               pose[:3,:3]@(dims/2)+pose[:3,3],atol=1e-12)


def test_controller_knots_reproduce_the_audited_quintic_and_rest_endpoints():
    u=np.linspace(0.,1.,17);q=np.column_stack([np.sin(u*(j+1))for j in range(6)])
    zeros=np.zeros(6)
    spline=make_interp_spline(u,q,k=5,bc_type=([(1,zeros),(2,zeros)],[(1,zeros),(2,zeros)]))
    knots=np.unique(np.r_[0.,spline.t[(spline.t>0)&(spline.t<1)],1.]);duration=3.2
    points=controller_points(spline,knots,duration)
    actual=BPoly.from_derivatives([p['time']for p in points],
        [[p[k]for k in ('positions','velocities','accelerations')]for p in points])
    samples=np.linspace(0.,duration,513)
    np.testing.assert_allclose(actual(samples),spline(samples/duration),atol=1e-8)
    np.testing.assert_allclose(actual([0.,duration],1),0.,atol=1e-12)
    np.testing.assert_allclose(actual([0.,duration],2),0.,atol=1e-10)

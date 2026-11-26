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


def test_task_obstacle_overlap_exempts_static_table_but_never_robot_or_carton():
    import xml.etree.ElementTree as ET
    from task_obstacles import append_boxes, static_pairs
    root=ET.fromstring('<robot><link name="world"/><link name="left_table_plate"/>'
        '<link name="left_front_forearm_link"/><link name="air_demo_carton"/></robot>')
    boxes=[dict(name='task_obstacle_camera',lo_m=[-1.,-.1,.9],hi_m=[-.8,.1,2.3])]
    append_boxes(root,boxes)
    flags={}
    model=SimpleNamespace(scene=SimpleNamespace(allowed_collision_matrix=SimpleNamespace(
        set_entry=lambda a,b,value:flags.__setitem__((a,b),value))))
    static_pairs(model,root,boxes,['left_front'],objects=['air_demo_carton'])
    assert flags[('task_obstacle_camera','left_table_plate')]
    assert ('task_obstacle_camera','left_front_forearm_link') not in flags
    assert ('task_obstacle_camera','air_demo_carton') not in flags


def test_named_simulation_recipe_requires_rigid_offsets_and_keeps_reference_branches():
    from prepare_carton_recipe import load_program
    program=load_program('carton-supported-simulation-v1')
    design=program['contact_design']
    assert design['entry_inward_shift_m']==0.
    assert design['elbow_signs']==dict(right_front=1,right_rear=-1)
    for transform in design['object_to_tool0'].values():
        T=np.asarray(transform)
        np.testing.assert_allclose(T[:3,:3].T@T[:3,:3],np.eye(3),atol=1e-10)


def test_offline_obstacle_route_checks_a_whole_detour_and_its_final_shortcuts():
    def valid(q):return not (.4<q[0]<.6 and abs(q[1])<.15)
    start=np.array([0.,0.]);goal=np.array([1.,0.])
    route=demo.obstacle_route(start,goal,np.array([[0.,1.],[-.5,.5]]),valid,budget_s=2.)
    assert route is not None and len(route)>2
    np.testing.assert_allclose(route[0],start);np.testing.assert_allclose(route[-1],goal)
    for a,b in zip(route,route[1:]):
        assert all(valid(a+(b-a)*u)for u in np.linspace(0,1,513))


def test_cached_middle_accepts_only_whole_turn_equivalence_and_keeps_other_joints():
    from carton_air_cache import Cache
    cache=Cache.__new__(Cache);cache.shift=None
    cache.phases={'draw':dict(id='draw',samples=[dict(positions={'a':.1,'b':.2}),dict(positions={'a':.2,'b':.3})])}
    # Binding mismatch is rejected before any cached controller file can be used.
    with pytest.raises(ValueError,match='exact winding'):
        cache.coarse('draw',{'a':.11,'b':.2},{})


def test_cached_controller_turn_shift_preserves_velocity_acceleration_and_checks_all_bounds(tmp_path):
    import json
    from carton_air_cache import controller_record,sha
    root=tmp_path/'cache';(root/'qualified').mkdir(parents=True)
    record=dict(id='draw',start={'j':.1},end={'j':.2},duration_s=1.,
        trajectories={'right_front':dict(joint_names=['j'],points=[
            dict(time=0.,positions=[.1],velocities=[0.],accelerations=[0.]),
            dict(time=1.,positions=[.2],velocities=[0.],accelerations=[0.])])})
    path=root/'qualified/draw.json';path.write_text(json.dumps(record))
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(dict(root=str(root),files={str(path):sha(path)})))
    phase=dict(id='draw',reuse_qualified=dict(manifest=str(manifest),manifest_sha256=sha(manifest),
        record_sha256=sha(path),winding_shift_rad={'j':-2*np.pi}))
    value=controller_record(phase,{'j':.1-2*np.pi},{'j':(-2*np.pi,2*np.pi)})
    assert value['end']['j']==pytest.approx(.2-2*np.pi)
    assert value['trajectories']['right_front']['points'][0]['velocities']==[0.]
    with pytest.raises(ValueError,match='joint bounds'):
        controller_record(phase,{'j':.1-2*np.pi},{'j':(-6.,6.)})
    path.write_text('{}')
    with pytest.raises(ValueError,match='controller path changed'):
        controller_record(phase,{'j':.1-2*np.pi},{'j':(-2*np.pi,2*np.pi)})


def test_air_handoff_consumes_only_own_successful_controller_completion():
    from execute_carton_air_demo import completion_ack
    state=dict(arms=dict(right_front=dict(action_active=True),left_front=dict(action_active=True)))
    calls=[]
    def wait(predicate,timeout):
        calls.append(timeout)
        assert not predicate()
        state['arms']['right_front']['action_active']=False
        assert predicate()
    client=SimpleNamespace(protection_status=state,wait=wait)
    completion_ack(client,['right_front'])
    assert calls==[3.]
    assert state['arms']['left_front']['action_active']


def test_air_preview_attaches_carton_to_grasp_and_contains_only_a_virtual_reference():
    import xml.etree.ElementTree as ET
    from run_carton_air_followup import preview_model
    from uwa_cell_gazebo.charuco_views import Chain
    from tempfile import TemporaryDirectory
    with TemporaryDirectory()as tmp:
        root=Path(tmp)
        (root/'original.urdf').write_text('<robot name="test"><link name="world"/>'
            '<link name="right_front_tool0"/><link name="left_front_tool0"/>'
            '<joint name="rf" type="fixed"><parent link="world"/><child link="right_front_tool0"/></joint>'
            '<joint name="lf" type="fixed"><parent link="world"/><child link="left_front_tool0"/></joint></robot>')
        offset=np.eye(4);offset[:3,3]=[.01,.17,.25]
        data=dict(object_shapes=[],reference_group=dict(object_to_tcp=dict(right_front=offset.tolist())))
        xml=preview_model(data,root,[])
        np.testing.assert_allclose(Chain(xml,'right_front_tool0','review_carried_carton').forward({}),np.linalg.inv(offset))
        np.testing.assert_allclose(Chain(xml,'left_front_tool0','review_virtual_tool_reference').forward({})[:3,3],[0,0,.3])
        visual=ET.fromstring(xml).find("link[@name='review_virtual_tool_reference']")
        assert visual.find('visual/geometry/sphere')is not None
        assert visual.find('collision')is None


def test_air_continuation_uses_the_requested_post_grasp_result_once():
    from run_carton_air_followup import plausible_grip
    report=dict(success=True,phase='CARTON_LIFTED_AND_WEIGHED',measurement_available=True,
        weighing=dict(assessment='BOTH_ARMS_LOAD_PLAUSIBLE',mass_kg=.51))
    assert plausible_grip(report)
    assert not plausible_grip(dict(report,measurement_available=False))
    assert not plausible_grip(dict(report,weighing=dict(assessment='SINGLE_ARM_LOAD')))

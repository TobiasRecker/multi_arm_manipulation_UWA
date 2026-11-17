"""Common-reference contracts with synthetic poses; no ROS, camera or UR access."""
from dataclasses import replace
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from uwa_cell_tasks.hardware_object_reference import SharedObjectReference,MemberObservation,MEMBERS
from match_cooperative_handling.rigid_object import tcp_target,pose_error


def reference(**kwargs):
    start=np.eye(4);end=start.copy();end[2,3]=.005
    tcps={a:np.eye(4) for a in MEMBERS};tcps[MEMBERS[0]][0,3]=-.2;tcps[MEMBERS[1]][0,3]=.2
    return SharedObjectReference(start,end,tcps,**kwargs)


def observations(ref,now,scales=(1.,1.)):
    pose,_=ref.sample(ref.tau)
    states={a:MemberObservation(now,now,pose@ref.offsets[a],scales[i],1.,True)
            for i,a in enumerate(MEMBERS)}
    return pose,states


def test_different_native_scaling_produces_one_object_clock_and_fixed_offsets():
    ref=reference();dt=.01;last_tau=0.
    for index in range(500):
        now=10.+dt*index;pose,states=observations(ref,now,(1.,.4))
        packet=ref.step(now,states,pose,now)
        assert not packet['stop_requested_for']
        assert packet['object_time_s']==pytest.approx(max(0,index)*dt*.4)
        for arm in MEMBERS:
            assert np.allclose(np.linalg.inv(packet['object_pose'])@packet['tcp_targets'][arm],ref.offsets[arm])
        assert not packet['executable'] and not packet['standstill_confirmed']
        last_tau=packet['object_time_s']
    assert last_tau<ref.duration


@pytest.mark.parametrize('fault',['member_stop','grip_loss','state_stale','object_stale','source_reverse','scale_zero','relative_error','timer_gap'])
def test_fault_requests_both_stops_and_never_resumes_or_rebases(fault):
    ref=reference();pose,states=observations(ref,10.);ref.step(10.,states,pose,10.)
    now=10.01;pose,states=observations(ref,now);bad=MEMBERS[1];object_time=now
    if fault=='member_stop':states[bad]=replace(states[bad],stop_latched=True)
    if fault=='grip_loss':states[bad]=replace(states[bad],grip_retained=False)
    if fault=='state_stale':states[bad]=replace(states[bad],received_monotonic=now-1.)
    if fault=='object_stale':object_time=now-1.
    if fault=='source_reverse':states[bad]=replace(states[bad],device_stamp=9.)
    if fault=='scale_zero':states[bad]=replace(states[bad],speed_scaling=0.)
    if fault=='relative_error':
        tcp=np.asarray(states[bad].world_tcp).copy();tcp[2,3]+=.002;states[bad]=replace(states[bad],world_tcp=tcp)
    if fault=='timer_gap':now=11.
    offsets=ref.offsets;packet=ref.step(now,states,pose,object_time)
    assert packet['stop_requested_for']==MEMBERS and packet['reason']
    assert all(np.array_equal(v,np.zeros(6)) for v in packet['tcp_twists'].values())
    frozen=ref.tau;pose,states=observations(ref,12.)
    assert ref.step(12.,states,pose,12.)['stop_requested_for']==MEMBERS
    assert ref.tau==frozen and all(np.array_equal(ref.offsets[a],offsets[a]) for a in MEMBERS)


def test_repeated_native_stamps_cannot_be_refreshed_by_receipt_time():
    ref=reference();pose,states=observations(ref,10.);ref.step(10.,states,pose,10.)
    for index in range(1,30):
        now=10.+index*.01;pose,states=observations(ref,now)
        states={a:replace(s,device_stamp=10.) for a,s in states.items()}
        packet=ref.step(now,states,pose,now)
        if packet['stop_requested_for']:break
    assert 'source frozen' in packet['reason']


def test_object_rotation_includes_opposite_lever_motion_and_shared_limit():
    start=np.eye(4);end=np.eye(4);end[:3,:3]=Rotation.from_euler('z',.1).as_matrix()
    offsets={a:np.eye(4) for a in MEMBERS};offsets[MEMBERS[0]][0,3]=-.2;offsets[MEMBERS[1]][0,3]=.4
    ref=SharedObjectReference(start,end,offsets,tcp_speed=.0005)
    pose,twist=ref.sample(ref.duration/2)
    commands={a:tcp_target(pose,ref.offsets[a],twist)[1] for a in MEMBERS}
    assert np.linalg.norm(commands[MEMBERS[1]][:3])<=.0005+1e-12
    assert np.linalg.norm(commands[MEMBERS[1]][:3])==pytest.approx(2*np.linalg.norm(commands[MEMBERS[0]][:3]))


def test_exposed_offset_copies_cannot_change_the_grasp():
    ref=reference();copy=ref.offsets;copy[MEMBERS[0]][0,3]=99.
    assert ref.offsets[MEMBERS[0]][0,3]==pytest.approx(-.2)


def test_complete_lift_generates_one_endpoint_without_release_command():
    ref=reference();packet=None
    for index in range(int(ref.duration/.01)+3):
        now=10.+index*.01;pose,states=observations(ref,now)
        packet=ref.step(now,states,pose,now)
        assert not packet['stop_requested_for']
    assert packet['complete'] and packet['object_pose'][2,3]==pytest.approx(.005)
    assert np.allclose(packet['object_twist'],0.)
    assert not any('gripper' in key or 'release' in key for key in packet)


def test_abrupt_native_scaling_change_latches_instead_of_clipping_one_arm():
    ref=reference()
    for index in range(700):
        now=10.+index*.01;pose,states=observations(ref,now)
        assert not ref.step(now,states,pose,now)['stop_requested_for']
    now=17.;pose,states=observations(ref,now,(1.,.1))
    packet=ref.step(now,states,pose,now)
    assert packet['stop_requested_for']==MEMBERS and 'scaling discontinuity' in packet['reason']

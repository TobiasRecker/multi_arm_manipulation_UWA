"""Separate commanded timing from unchanged monitored limits/model identity."""
import copy
import numpy as np
import pytest
from uwa_cell_tasks.hardware_carton_approach import slow_trajectory, canonical_base, unloaded_open_status, unloaded_guard_ready, wait_service_spinning, unloaded_program_start_ready


def test_time_dilation_preserves_geometry_and_does_not_mutate_original():
    original = dict(duration_s=10., waypoints=[[0.]*6,[1.]*6],
                    joint_names=['q'+str(i) for i in range(6)],
                    points=[dict(time=t,positions=[t]*6,velocities=[.003]*6,accelerations=[.004]*6) for t in [0.,10.]])
    before = copy.deepcopy(original); slower = slow_trajectory(original, .003, .0015)
    assert original == before and slower['waypoints'] == original['waypoints']
    assert slower['duration_s'] == 20.
    for p,q in zip(slower['points'], original['points']):
        assert p['positions'] == q['positions'] and p['time'] == 2*q['time']
        np.testing.assert_allclose(p['velocities'], np.array(q['velocities'])/2)
        np.testing.assert_allclose(p['accelerations'], np.array(q['accelerations'])/4)


@pytest.mark.parametrize('command', [0., -.1, .004, float('nan')])
def test_command_profile_cannot_increase_the_guard_bound(command):
    with pytest.raises(ValueError):slow_trajectory({}, .003, command)


def test_equal_command_and_monitor_keeps_the_original_timing():
    trajectory=dict(duration_s=10.,points=[dict(time=10.,positions=[1.],velocities=[.1],accelerations=[.2])])
    assert slow_trajectory(trajectory,.1,.1)==trajectory


def test_inactive_open_gripper_does_not_require_an_activation_stroke():
    status=dict(observed=True,busy=False,registers=dict(ACT=0,STA=0,OBJ=0,FLT=0,PRE=0,POS=3))
    assert unloaded_open_status(status)
    for key,value in [('OBJ',2),('POS',128),('PRE',255),('FLT',1),('STA',1)]:
        changed=copy.deepcopy(status);changed['registers'][key]=value
        assert not unloaded_open_status(changed)
    status['busy']=True
    assert not unloaded_open_status(status)


def test_clear_guard_has_physical_quiet_without_a_guard_latched_stop():
    guard=dict(standstill_confirmed=False,stationary_arms=['left_front','left_rear','right_front','right_rear'],faults=[])
    assert unloaded_guard_ready(guard)
    guard['stationary_arms'].pop()
    assert not unloaded_guard_ready(guard)
    guard['stationary_arms'].append('right_rear');guard['faults']=['stale']
    assert not unloaded_guard_ready(guard)


def test_service_discovery_processes_telemetry_instead_of_blocking():
    from types import SimpleNamespace
    ticks=[]
    client=SimpleNamespace(service_is_ready=lambda:len(ticks)>=4)
    wait_service_spinning(client,lambda **kw:ticks.append(kw),clock=lambda:len(ticks)*.005)
    assert len(ticks)==4
    with pytest.raises(TimeoutError):
        wait_service_spinning(SimpleNamespace(service_is_ready=lambda:False),lambda **kw:ticks.append(kw),timeout=.01,clock=lambda:len(ticks)*.005)


def test_explicit_unloaded_program_start_keeps_all_holds_and_native_safety():
    arms=['left_front','left_rear','right_front','right_rear']
    guard=dict(stationary_arms=arms,faults=[])
    sup=dict(held_arms=arms,witness_available=True,ports={r:{k:True for k in
        ('held','manager_fresh','hardware_mode_verified','hold_config_verified')} for r in arms})
    records={r:dict(v=[0.]*6,status=dict(robot_mode=7,safety_mode=1,runtime_state=1)) for r in arms}
    assert unloaded_program_start_ready(guard,sup,records,set())
    assert not unloaded_program_start_ready(guard,sup,records,{'right_front'})
    for r in arms:
        bad=copy.deepcopy(records);bad[r]['status']['safety_mode']=3
        assert not unloaded_program_start_ready(guard,sup,bad,set())
        bad=copy.deepcopy(records);bad[r]['v'][0]=.002
        assert not unloaded_program_start_ready(guard,sup,bad,set())
        bad=copy.deepcopy(sup);bad['ports'][r]['held']=False
        assert not unloaded_program_start_ready(guard,bad,records,set())
    assert not unloaded_program_start_ready(guard,dict(sup,witness_available=False),records,set())


def test_supplemental_object_does_not_hide_a_changed_robot_link():
    base = '<robot name="a"><link name="world"/><link name="arm"/></robot>'
    extra = '<link name="pregrasp_carton_static"/><joint name="pregrasp_carton_anchor" type="fixed"/>'
    augmented = base.replace('</robot>', extra+'</robot>')
    assert canonical_base(base) == canonical_base(augmented)
    assert canonical_base(base) != canonical_base(augmented.replace('name="arm"','name="changed"'))


def test_generated_visual_paths_are_irrelevant_but_collision_geometry_is_bound():
    xml = '<robot name="a"><link name="arm"><visual><geometry><mesh filename="/output1/board.dae"/></geometry></visual><collision><geometry><sphere radius=".1"/></geometry></collision></link></robot>'
    assert canonical_base(xml) == canonical_base(xml.replace('/output1/', '/output2/'))
    assert canonical_base(xml) != canonical_base(xml.replace('radius=".1"','radius=".2"'))


def test_scoped_release_can_reuse_other_holds_without_any_rpc():
    from uwa_cell_tasks.hardware_carton_approach import retained_holds
    arms={'left_front','left_rear','right_rear'}
    supervisor=dict(armed=True,witness_available=True,held_arms=list(arms),blocked_arms=list(arms),
        ports={r:{k:True for k in ('manager_fresh','hardware_mode_verified','hold_config_verified','held')}for r in arms})
    answer=retained_holds(supervisor,arms)
    assert answer['resource_holds_confirmed'] and answer['latches_confirmed']
    supervisor['ports']['left_rear']['held']=False
    assert not retained_holds(supervisor,arms)['resource_holds_confirmed']


def test_open_carton_check_requires_both_full_cell_and_exact_open_scene():
    from types import SimpleNamespace
    from uwa_cell_tasks.hardware_carton_approach import OpenCartonCollision
    calls=[]
    def model(name,free):
        def check(state,contacts=False):calls.append((name,contacts));return free,[name]
        return SimpleNamespace(bounds={'joint':(-1.,1.)},check=check)
    for primary,auxiliary,expected in [(False,True,False),(True,False,False),(True,True,True)]:
        calls.clear();base=model('full-opening cell',primary)
        combined=OpenCartonCollision(base,model('open carton',auxiliary))
        assert combined.check({'joint':0.},contacts=True)[0] is expected
        assert combined.bounds is base.bounds
        assert calls==([('full-opening cell',True),('open carton',True)] if primary else [('full-opening cell',True)])


def test_task_open_scene_preserves_other_arms_cell_geometry_and_every_carton_pair(tmp_path,monkeypatch):
    import hashlib
    from types import SimpleNamespace
    import xml.etree.ElementTree as ET
    from uwa_cell_tasks.hardware_carton_approach import open_carton_collision
    import uwa_cell_calibration.model as models
    mesh=tmp_path/'finger mesh.stl';mesh.write_bytes(b'exact hardware mesh fixture')
    original=f'<robot name="cell"><link name="right_front_robotiq_85_left_finger_tip_link"><collision><geometry><mesh filename="{mesh.as_uri()}"/></geometry></collision></link></robot>'
    frozen='<robot name="cell"><link name="right_front_robotiq_85_left_finger_tip_link"><collision><geometry><sphere radius="0.1"/></geometry></collision></link><link name="left_rear_robotiq_85_left_finger_tip_link"><collision><geometry><sphere radius="0.2"/></geometry></collision></link><link name="right_front_forearm_link"><collision><geometry><sphere radius="0.3"/></geometry></collision></link><link name="pregrasp_carton_static"><collision><geometry><box size="1 1 1"/></geometry></collision></link></robot>'
    (tmp_path/'moveit').mkdir();(tmp_path/'moveit/robot.srdf').write_text('<robot name="cell"><disable_collisions link1="mechanical_a" link2="mechanical_b"/></robot>')
    captured={};allowed=[]
    def collision(xml,directory):
        captured['xml']=xml
        return SimpleNamespace(scene=SimpleNamespace(allowed_collision_matrix=SimpleNamespace(set_entry=lambda *args:allowed.append(args))))
    monkeypatch.setattr(models,'CollisionModel',collision)
    base=SimpleNamespace(bounds={})
    problem=SimpleNamespace(original_description=original,directory=tmp_path,collision=base)
    result,hashes=open_carton_collision(problem,frozen,tmp_path/'aux')
    root=ET.fromstring(captured['xml'])
    assert result.primary is base
    assert root.find("link[@name='right_front_robotiq_85_left_finger_tip_link']/collision/geometry/mesh") is not None
    assert root.find("link[@name='left_rear_robotiq_85_left_finger_tip_link']/collision/geometry/sphere").get('radius')=='0.2'
    assert root.find("link[@name='right_front_forearm_link']/collision/geometry/sphere").get('radius')=='0.3'
    assert root.find("link[@name='pregrasp_carton_static']/collision/geometry/box") is not None
    assert allowed==[('mechanical_a','mechanical_b',True)]
    assert hashes=={str(mesh.resolve()):hashlib.sha256(mesh.read_bytes()).hexdigest()}

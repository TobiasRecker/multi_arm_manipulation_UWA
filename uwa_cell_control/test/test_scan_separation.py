"""Full-body wall support, between-sample bounds, asynchronous separation."""
from copy import deepcopy
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from uwa_cell_control.scan_separation import Geometry, Body, separation, validated_steps, sweep


def robot(kind='revolute'):
    return f'''<robot name="test"><link name="world"/>
    <link name="a_base_link"/><link name="a_link"><collision><origin xyz="1 0 0"/>
      <geometry><box size="2 .02 .02"/></geometry></collision></link>
    <link name="b_base_link"/><link name="b_link"><collision><geometry><sphere radius=".1"/></geometry></collision></link>
    <joint name="a_base" type="fixed"><parent link="world"/><child link="a_base_link"/></joint>
    <joint name="b_base" type="fixed"><parent link="world"/><child link="b_base_link"/><origin xyz="4 0 0"/></joint>
    <joint name="a_joint" type="{kind}"><parent link="a_base_link"/><child link="a_link"/>
      <axis xyz="0 0 1"/><limit lower="-5" upper="5"/></joint>
    <joint name="b_joint" type="revolute"><parent link="b_base_link"/><child link="b_link"/>
      <axis xyz="0 0 1"/><limit lower="-5" upper="5"/></joint></robot>'''


def test_full_collision_body_crosses_wall_even_when_link_origin_stays_home():
    geometry = Geometry(robot(), {'a': ['a_joint'], 'b': ['b_joint']})
    frames = geometry.fk.frames({'a_joint': 0., 'b_joint': 0.})
    low, high = geometry.bodies['a'][0].support(frames, np.array([[1., 0, 0]]))
    assert frames['a_link'][0, 3] == 0 and high[0] == 2.
    result = separation(low[0], high[0], 3.9, 4.1, .5, .02)
    assert result['a_wall_intrusion_bound_m'] == 1.5


def test_curved_motion_between_clear_endpoints_is_included_in_bound():
    geometry = Geometry(robot(), {'a': ['a_joint'], 'b': ['b_joint']})
    body = geometry.bodies['a'][0]
    normal = np.array([[1., 0, 0]])
    endpoints = [body.support(geometry.fk.frames({'a_joint': q}), normal)[1][0] for q in [-.4, .4]]
    assert max(endpoints) < 1.9
    padding = float(body.radii @ np.array([.8]) / 2)
    upper = max(endpoints) + padding
    dense = [body.support(geometry.fk.frames({'a_joint': q}), normal)[1][0] for q in np.linspace(-.4, .4, 101)]
    assert max(dense) > 1.9 and max(dense) <= upper
    assert not separation(0., upper, 1.95, 3., 1.9, .02)['phase_independent_separation_proven']


def test_offset_separator_can_work_even_when_midpoint_wall_is_crossed():
    result = separation(-1., .1, .4, 2., 0., .02)
    assert not result['midpoint_wall_with_buffer_pass']
    assert result['phase_independent_separation_proven']
    assert result['a_wall_intrusion_bound_m'] == .1
    assert result['separator_shift_from_midpoint_m'] == .25


def test_same_time_clearance_does_not_prove_arbitrary_phase_clearance():
    # At the same progress u, centers u and 1+u always have 1m separation.
    # If A finishes and B stops at its start, both can occupy x=1.
    assert min((1+u)-u for u in np.linspace(0, 1, 30)) > .99
    result = separation(-.1, 1.1, .9, 2.1, .5, .02)
    assert not result['phase_independent_separation_proven']
    assert result['projected_gap_bound_m'] < 0


def test_mesh_support_respects_scale_and_collision_frame(tmp_path):
    source = tmp_path / 'tetra.stl'
    source.write_text('solid test\n' + '\n'.join('vertex '+' '.join(map(str,v)) for v in
        [[0,0,0],[1,0,0],[0,1,0],[0,0,1]]) + '\nendsolid test\n')
    collision = ET.fromstring(f'<collision><origin xyz=".3 0 0"/><geometry><mesh filename="{source}" scale="2 1 1"/></geometry></collision>')
    body = Body('a', 'a_link', 0, collision, lambda radius: np.array([radius]))
    low, high = body.support({'a_link': np.eye(4)}, np.eye(3))
    np.testing.assert_allclose(low, [.3, 0, 0])
    np.testing.assert_allclose(high, [2.3, 1., 1.])


def points(q0, q1):
    delta=np.asarray(q1)-q0
    return [dict(time=u, positions=(q0+(10*u**3-15*u**4+6*u**5)*delta).tolist(),
        velocities=((30*u**2-60*u**3+30*u**4)*delta).tolist(),
        accelerations=((60*u-180*u**2+120*u**3)*delta).tolist()) for u in (0., .5, 1.)]


def plan():
    start={'a_joint':0.,'b_joint':0.}
    one=dict(arm='a',start=dict(start),target=[.2],points=points(np.array([0.]),np.array([.2])),purpose='common_object_initial_view')
    two=dict(arm='b',start={'a_joint':.2,'b_joint':0.},target=[.3],points=points(np.array([0.]),np.array([.3])),purpose='common_object_initial_view')
    return dict(purpose='object_scan_review_only',paths_checked=True,common_view_found=True,start=start,
        common_state={'a_joint':.2,'b_joint':.3},steps=[one,two])


def test_changed_quintic_or_discontinuous_sequence_is_rejected():
    names={'a':['a_joint'],'b':['b_joint']}
    original=plan()
    assert len(validated_steps(original,names))==2
    changed=deepcopy(original);changed['steps'][0]['points'][1]['positions']=[.19]
    with pytest.raises(ValueError,match='quintic'):validated_steps(changed,names)
    changed=deepcopy(original);changed['steps'][1]['start']['a_joint']=.1
    with pytest.raises(ValueError,match='continuity'):validated_steps(changed,names)


def test_no_extra_motion_still_includes_both_held_arm_geometries():
    geometry=Geometry(robot(),{'a':['a_joint'],'b':['b_joint']})
    planes=[dict(normal=np.array([1.,0,0]))]
    result=sweep(geometry,plan(),planes,'extra',{})
    assert result['a']['samples']==result['b']['samples']==1
    assert result['a']['body_count']==1 and result['a']['max'][0]>1.9


def test_tilted_plane_can_separate_hulls_with_overlapping_x_projection():
    from uwa_cell_control.scan_separation import alternative_separator, corners
    A=corners(np.array([.2,.05,.05]))+[-.1,0,0]
    B=corners(np.array([.2,.05,.05]))+[.1,.5,0]
    assert A[:,0].max()>B[:,0].min()
    result=alternative_separator(A,B,.005,.005,.02)
    assert result['proven'] and result['gap_bound_m']>=.02
    n=np.asarray(result['normal_world'])
    assert np.isclose(np.linalg.norm(n),1)
    assert (B@n).min()-(A@n).max()-.01>=.02
    assert not alternative_separator(A,A+.01,.005,.005,.02)['proven']


def test_optimizer_success_does_not_replace_support_gap_check(monkeypatch):
    from uwa_cell_control import scan_separation as module
    A=np.array([[0.,0,0],[1.,0,0],[0.,1,0],[0.,0,1]])
    B=A+[.01,0,0]
    monkeypatch.setattr(module,'linprog',lambda *args,**kwargs:SimpleNamespace(x=np.array([1.,0,0,0,0]),success=True))
    result=module.alternative_separator(A,B,0.,0.,.02)
    assert result['optimizer_converged'] and not result['proven']


def test_per_body_hulls_can_prove_separation_when_whole_arm_hulls_overlap():
    from uwa_cell_control.scan_separation import alternative_separator, bodywise_separator, corners
    def body(center):
        return dict(hull=(corners(np.array([.05,.05,.05]))+center).tolist(),
                    link=str(center),collision_index=0,padding_m=.005)
    A=[body([-1,0,0]),body([1,0,0])]
    B=[body([0,0,0])]
    assert not alternative_separator(np.concatenate([h['hull'] for h in A]),B[0]['hull'],.005,.005,.02)['proven']
    result=bodywise_separator(A,B,.02)
    assert result['proven'] and result['body_pairs_checked']==2
    assert result['smallest_proven_gap']['gap_bound_m']>.8
    assert not bodywise_separator(B,B,.02)['proven']

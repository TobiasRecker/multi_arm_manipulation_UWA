"""Frame and strategy checks for offline hardware pregrasp generation."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

spec = importlib.util.spec_from_file_location('prepare_carton_pregrasp', Path(__file__).parents[2]/'tools/prepare_carton_pregrasp.py')
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)


def fixture():
    xml = '<robot name="tools"><link name="world"/>'
    contacts = {}
    for arm, x in zip(tool.MEMBERS, (0., .4)):
        xml += f'''<link name="{arm}_tool0"/><link name="{arm}_robotiq_85_base_link"/>
        <joint name="{arm}_anchor" type="fixed"><parent link="world"/><child link="{arm}_tool0"/></joint>
        <joint name="{arm}_mount" type="fixed"><parent link="{arm}_tool0"/>
        <child link="{arm}_robotiq_85_base_link"/><origin xyz="0 0 .012" rpy="0 0 .3"/></joint>'''
        contacts[arm] = dict(point_object=[x, .17, .095], normal_object=[1., 0., 0.])
    return xml+'</robot>', contacts


def test_reconstructs_world_contacts_with_real_tool_offset_and_vertical_pregrasp():
    from uwa_cell_gazebo.charuco_views import Chain
    xml, contacts = fixture()
    T = np.eye(4); T[:3, :3] = Rotation.from_euler('xyz', [.01, -.015, 1.3]).as_matrix()
    T[:3, 3] = [.2, -.3, .9]
    result = tool.targets(xml, contacts, T)
    for arm in tool.MEMBERS:
        target = np.asarray(result[arm]['theoretical_tool0_entry'])
        pre = np.asarray(result[arm]['tool0_pregrasp'])
        base = target@Chain(xml, arm+'_tool0', arm+'_robotiq_85_base_link').forward({})
        point = (base@np.array([0., 0., .145, 1.]))[:3]
        np.testing.assert_allclose(point, (T@np.r_[contacts[arm]['point_object'], 1.])[:3], atol=1e-12)
        np.testing.assert_allclose(base[:3, 2], [0., 0., -1.], atol=1e-12)
        np.testing.assert_allclose(pre[:3, 3]-target[:3, 3], [0., 0., .08], atol=1e-12)
        np.testing.assert_allclose(pre[:3, :3], target[:3, :3])


@pytest.mark.parametrize('angle', [3., 90., 180.])
def test_rejects_unsupported_carton_tilt(angle):
    xml, contacts = fixture(); T = np.eye(4)
    T[:3, :3] = Rotation.from_euler('x', angle, degrees=True).as_matrix()
    with pytest.raises(ValueError, match='upright'):
        tool.targets(xml, contacts, T)


@pytest.mark.parametrize('distance', [.0, .049, .301, float('nan')])
def test_requires_clear_pregrasp_separation(distance):
    xml, contacts = fixture()
    with pytest.raises(ValueError, match='separation'):
        tool.targets(xml, contacts, np.eye(4), distance)


def test_rejects_incomplete_membership_and_nonfinite_contact():
    xml, contacts = fixture(); bad = dict(contacts); bad.pop(tool.MEMBERS[0])
    with pytest.raises(ValueError, match='both right'):
        tool.targets(xml, bad, np.eye(4))
    contacts[tool.MEMBERS[0]]['point_object'][0] = float('nan')
    with pytest.raises(ValueError, match='Finite'):
        tool.targets(xml, contacts, np.eye(4))


def test_equivalent_winding_uses_start_and_real_limits():
    q = tool.nearest_winding([-6.23, 4.71, -5.4], [-1.57, 0., 3.15], [(-2*np.pi, 2*np.pi)]*3)
    np.testing.assert_allclose(q, [-6.23+2*np.pi, 4.71-2*np.pi, -5.4+2*np.pi])
    # A narrow physical interval can rule out the numerically closest winding.
    assert tool.nearest_winding([.1], [6.], [(-.2, .2)]) == [.1]
    with pytest.raises(ValueError):
        tool.nearest_winding([1.], [0.], [(-.2, .2)])


def test_exact_simulation_grip_preserves_the_two_object_relative_transforms():
    xml, contacts = fixture()
    T=np.eye(4);T[:3,:3]=Rotation.from_euler('z',.9).as_matrix();T[:3,3]=[.3,-.2,.9]
    offsets={}
    for arm,x in zip(tool.MEMBERS,(.0013,.4028)):
        offset=np.eye(4);offset[:3,:3]=Rotation.from_euler('xyz',[np.pi,0.,.0016]).as_matrix()
        offset[:3,3]=[x,.171,.254];offsets[arm]=offset.tolist()
    result=tool.targets(xml,contacts,T,.15,object_to_tool0=offsets)
    for arm in tool.MEMBERS:
        entry=np.asarray(result[arm]['theoretical_tool0_entry'])
        np.testing.assert_allclose(np.linalg.inv(T)@entry,offsets[arm],atol=1e-12)
        np.testing.assert_allclose(np.asarray(result[arm]['tool0_pregrasp'])[:3,3]-entry[:3,3],[0,0,.15])

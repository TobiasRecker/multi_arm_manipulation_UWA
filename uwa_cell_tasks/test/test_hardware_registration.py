"""A changed model anchor must not silently reuse its old absolute camera pose."""
import copy
import numpy as np
import pytest
from uwa_cell_tasks.hardware_registration import bind_camera_pose, board_camera_candidate, board_relative_bases, per_arm_camera_binding, validate_per_arm_binding


def fixture():
    xml='<robot name="a"><link name="world"/><link name="right_front_base_link"/><joint name="mount" type="fixed"><parent link="world"/><child link="right_front_base_link"/><origin xyz=".4955 0 0"/></joint></robot>'
    old=np.eye(4);old[0,3]=.45
    relative=np.eye(4);relative[:3,3]=[1.,.2,1.8]
    reg=dict(anchor_frame='right_front_base_link',T_world_anchor_at_registration=old.tolist(),
             T_anchor_oak_optical=relative.tolist(),T_world_oak_optical=(old@relative).tolist())
    return xml,reg


def test_anchor_correction_is_explicit_and_does_not_mutate_calibration():
    xml,reg=fixture();before=copy.deepcopy(reg)
    result=bind_camera_pose(xml,reg,np.eye(4))
    np.testing.assert_allclose(result['anchor_translation_change_m'],[.0455,0,0],atol=1e-12)
    np.testing.assert_allclose(np.array(result['T_world_object_candidate'])[:3,3],[1.4955,.2,1.8])
    assert reg==before and not result['executable'] and not result['global_camera_profile_modified']


def test_inconsistent_original_chain_is_rejected():
    xml,reg=fixture();reg['T_world_oak_optical'][0][3]+=.01
    with pytest.raises(ValueError,match='Inconsistent'):bind_camera_pose(xml,reg,np.eye(4))


def test_a_moving_anchor_cannot_be_treated_as_a_static_camera_registration():
    xml,reg=fixture();xml=xml.replace('type="fixed"','type="revolute"')
    with pytest.raises(ValueError,match='world-fixed'):bind_camera_pose(xml,reg,np.eye(4))


def test_board_chain_recovers_camera_and_relative_bases_with_rotations():
    from scipy.spatial.transform import Rotation
    rng=np.random.default_rng(1711)
    for _ in range(20):
        transforms=[]
        for i in range(4):
            t=np.eye(4);t[:3,:3]=Rotation.random(random_state=rng).as_matrix();t[:3,3]=rng.normal(size=3)
            transforms.append(t)
        a,b,board,camera=transforms
        ab=np.linalg.inv(a)@board;bb=np.linalg.inv(b)@board;cb=np.linalg.inv(camera)@board
        np.testing.assert_allclose(board_camera_candidate(a,ab,cb),camera,atol=1e-12)
        np.testing.assert_allclose(board_relative_bases(ab,bb),np.linalg.inv(a)@b,atol=1e-12)


def test_board_registration_rejects_nonrigid_input():
    bad=np.eye(4);bad[0,0]=2
    with pytest.raises(ValueError):board_camera_candidate(np.eye(4),bad,np.eye(4))


def test_per_arm_camera_reference_is_preserved_and_tampering_rejected():
    xml='<robot name="a"><link name="world"/>'
    transforms={}
    for arm,x in [('right_front',.5),('right_rear',-.5)]:
        xml+=f'<link name="{arm}_base_link"/><joint name="{arm}" type="fixed"><parent link="world"/><child link="{arm}_base_link"/><origin xyz="{x} 0 0"/></joint>'
        t=np.eye(4);t[:3,3]=[1-x,.02 if x<0 else 0,1.5]
        transforms[arm]=dict(parent_frame=arm+'_base_link',child_frame='oak4_rgb_optical_frame',T_parent_child=t.tolist())
    xml+='</robot>';o=np.eye(4);o[2,3]=.2
    binding=per_arm_camera_binding(xml,dict(transforms=transforms),o)
    objects=validate_per_arm_binding(xml,binding)
    np.testing.assert_allclose(np.array(objects['right_front'])[:3,3],[1,0,1.7])
    np.testing.assert_allclose(np.array(objects['right_rear'])[:3,3],[1,.02,1.7])
    changed=copy.deepcopy(binding);changed['world_object_by_arm']['right_rear'][1][3]=0
    with pytest.raises(ValueError,match='binding changed'):validate_per_arm_binding(xml,changed)
    with pytest.raises(ValueError,match='binding changed'):validate_per_arm_binding(xml.replace('xyz="0.5 0 0"','xyz="0.6 0 0"'),binding)

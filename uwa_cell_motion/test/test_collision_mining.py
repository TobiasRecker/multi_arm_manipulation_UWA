import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

tools=Path(__file__).resolve().parents[2]/'tools'
sys.path.insert(0,str(tools))
spec=importlib.util.spec_from_file_location('collision_mining',tools/'mine_teacher_collisions.py')
mining=importlib.util.module_from_spec(spec);spec.loader.exec_module(mining)
from uwa_cell_motion.two_arm_teacher import pose_at


def test_direct_reference_has_no_artificial_excursion_and_preserves_endpoints():
    a=np.eye(4);a[:3,3]=[.1,.2,1.]
    a[:3,:3]=Rotation.from_euler('xyz',[.2,-.7,.5]).as_matrix()
    b=np.eye(4);b[:3,3]=[-.1,.1,1.2]
    b[:3,:3]=Rotation.from_euler('xyz',[-.4,.8,-.3]).as_matrix()
    task=mining.direct_task('test',a,b)
    assert task['excursion_m']==[0,0,0] and task['rotation_vector_deg']==[0,0,0]
    assert np.allclose(pose_at(a,task,0,np.zeros((6,6))),a)
    assert np.allclose(pose_at(a,task,1,np.zeros((6,6))),b)
    assert np.allclose(pose_at(a,task,.5,np.zeros((6,6)))[:3,3],(a[:3,3]+b[:3,3])/2)


def test_native_contact_labels_distinguish_arm_object_and_self_collisions():
    pairs=[('right_front_forearm_link','right_rear_forearm_link'),
           ('offline_carried_carton','right_front_forearm_link'),
           ('offline_carried_carton','table'),
           ('right_front_wrist_1_link','right_front_upper_arm_link'),
           ('left_rear_forearm_link','right_rear_forearm_link')]
    assert set(mining.contact_categories(pairs))=={'active_arm_arm','object_arm','object_environment','self_collision','other_arm_arm'}
    assert mining.contact_categories([])==[]


def test_hull_overlap_is_not_claimed_as_native_contact_or_just_positive_margin():
    assert mining.screen_status(0,-.01)=='ARM_HULL_OVERLAP'
    assert mining.screen_status(0,.005)=='MARGIN_ONLY'
    assert mining.screen_status(1,.05)=='FCL_COLLISION'
    assert mining.screen_status(0,.021)=='NO_FCL_OR_ARM_MARGIN_HIT'


def test_progress_roundoff_does_not_hide_a_real_range_error():
    assert mining.checked_progress(1+2e-16)==1
    assert mining.checked_progress(-2e-16)==0
    for value in (1.0001,-.0001,np.nan):
        with pytest.raises(ValueError):mining.checked_progress(value)

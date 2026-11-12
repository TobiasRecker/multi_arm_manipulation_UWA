import time
from types import SimpleNamespace
import pytest
from uwa_cell_gazebo.configuration import joint_names
from uwa_cell_control.hardware_parallel import independent_arm,configure_model
from uwa_cell_control.park_arm import JointObserver


def test_only_named_diagonal_pair_collisions_are_exempted():
    entries=[]
    model=SimpleNamespace(description='''<robot name="x"><link name="right_front_arm"/>
<link name="right_front_camera"/><link name="left_rear_arm"/><link name="left_rear_gripper"/>
<link name="right_rear_arm"/><link name="right_table_plate"/></robot>''',prefix='',
        scene=SimpleNamespace(allowed_collision_matrix=SimpleNamespace(set_entry=lambda a,b,v:entries.append((a,b,v)))))
    configure_model(model,'right_front','left_rear')
    assert len(entries)==4 and all(a.startswith('right_front_') and b.startswith('left_rear_') and v for a,b,v in entries)
    with pytest.raises(ValueError,match='diagonal'):configure_model(model,'right_front','right_rear')
    with pytest.raises(ValueError,match='diagonal'):independent_arm({'arm':'right_front','independent_diagonal_arm':'right_rear'})


def test_diagonal_motion_or_missing_data_does_not_cancel_but_same_table_and_own_stop_do():
    observer=JointObserver.__new__(JointObserver);observer.mode='hardware'
    observer.profiles={r:{} for r in ['right_front','right_rear','left_rear']}
    observer.program_running={'right_front':True};observer.safety_modes={'right_front':1,'left_rear':3}
    observer.received={r:{'positions':[0.]*6,'received_monotonic':time.monotonic()} for r in ['right_front','right_rear']}
    plan={'arm':'right_front','independent_diagonal_arm':'left_rear',
          'state_sources':{r:'live_joint_states' for r in observer.profiles},
          'start':{j:0. for r in observer.profiles for j in joint_names(r)}}
    observer.guard(plan,require_program_link=True)
    observer.received['left_rear']={'positions':[3.]*6,'received_monotonic':0}
    observer.guard(plan,require_program_link=True)
    observer.received['right_rear']['positions'][0]=.02
    with pytest.raises(RuntimeError,match='stationary-arm'):observer.guard(plan,require_program_link=True)
    observer.received['right_rear']['positions'][0]=0
    observer.safety_modes['right_front']=3
    with pytest.raises(RuntimeError,match='native UR safety stop'):observer.guard(plan,require_program_link=True)

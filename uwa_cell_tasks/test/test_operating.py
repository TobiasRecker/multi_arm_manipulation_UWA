import numpy as np
import pytest
import yaml
from uwa_cell_tasks.core import configuration
from uwa_cell_tasks.operating import velocity_limits,TaskSphereModel,motion_configuration


def test_exploration_requires_explicit_mode_and_force_observation(tmp_path):
    cfg=configuration();cfg['joint_velocity_rad_s']=.1;cfg['joint_acceleration_rad_s2']=.3
    cfg['finger_velocity_limit_rad_s']=.5;cfg['gripper_coarse_velocity_rad_s']=.15;cfg['gripper_fine_velocity_rad_s']=.02
    path=tmp_path/'profile.yaml';path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='operating envelope'):configuration(path)
    cfg['exploration_mode']=True;path.write_text(yaml.safe_dump(cfg));accepted=configuration(path)
    assert motion_configuration(accepted)['velocity_limit_rad_s']==.1
    cfg['force_observation']=False;path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='requires force'):configuration(path)


def test_per_joint_limits_do_not_raise_unselected_obstacle_limits():
    names=['right_front_wrist_3_joint','right_front_robotiq_85_left_knuckle_joint','left_front_robotiq_85_left_knuckle_joint']
    np.testing.assert_allclose(velocity_limits(names,dict(joint_velocity_rad_s=.1,finger_velocity_limit_rad_s=.5)),[.1,.5,.05])


@pytest.mark.parametrize('step,accepted',[(.0005,True),(.00025,True),(.00001,False),(.002,False)])
def test_physics_step_is_explicit_and_bounded(tmp_path,step,accepted):
    cfg=configuration();cfg['physics_step_s']=step
    path=tmp_path/'profile.yaml';path.write_text(yaml.safe_dump(cfg))
    if accepted:assert configuration(path)['physics_step_s']==step
    else:
        with pytest.raises(ValueError,match='Physics step'):configuration(path)


def test_stopping_budget_accounts_for_faster_fingers_and_actual_overspeed():
    model=TaskSphereModel.__new__(TaskSphereModel)
    model.names={'right_front':['right_front_wrist_3_joint','right_front_robotiq_85_left_knuckle_joint']}
    model.motion_radii={'right_front':np.array([[.5,.05]])}
    model.task=dict(joint_velocity_rad_s=.1,finger_velocity_limit_rad_s=.5)
    cfg=dict(braking_acceleration_rad_s2=1.,rate_hz=10.,stop_latency_s=.1)
    reserve,speed=model.arm_budget('right_front',[0.,0.],.02,cfg)
    assert speed==pytest.approx(.075) and reserve==pytest.approx(.02525)
    reserve,speed=model.arm_budget('right_front',[.2,0.],.02,cfg)
    assert speed==pytest.approx(.125) and reserve==pytest.approx(.04375)

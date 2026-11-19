import numpy as np
import pytest
import yaml
from uwa_cell_tasks.core import configuration
from uwa_cell_tasks.operating import velocity_limits,TaskSphereModel,motion_configuration


def test_exploration_requires_explicit_mode(tmp_path):
    cfg=configuration();cfg['joint_velocity_rad_s']=.1;cfg['joint_acceleration_rad_s2']=.3
    cfg['finger_velocity_limit_rad_s']=.5;cfg['gripper_coarse_velocity_rad_s']=.15;cfg['gripper_fine_velocity_rad_s']=.02
    path=tmp_path/'profile.yaml';path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='operating envelope'):configuration(path)
    cfg['exploration_mode']=True;path.write_text(yaml.safe_dump(cfg));accepted=configuration(path)
    assert motion_configuration(accepted)['velocity_limit_rad_s']==.1
    assert not accepted['force_observation']


def test_per_joint_limits_do_not_raise_unselected_obstacle_limits():
    names=['right_front_wrist_3_joint','right_front_robotiq_85_left_knuckle_joint','left_front_robotiq_85_left_knuckle_joint']
    np.testing.assert_allclose(velocity_limits(names,dict(joint_velocity_rad_s=.1,finger_velocity_limit_rad_s=.5)),[.1,.5,.05])


def test_motor_torque_increase_is_explicit_exploration(tmp_path):
    cfg=configuration();cfg['gripper_motor_torque_limit_nm']=.7
    path=tmp_path/'profile.yaml';path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='motor torque'):configuration(path)
    cfg['exploration_mode']=True;path.write_text(yaml.safe_dump(cfg))
    assert configuration(path)['gripper_motor_torque_limit_nm']==.7
    cfg['gripper_motor_torque_limit_nm']=2.01;path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='motor torque'):configuration(path)


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


def test_carrier_override_remains_in_full_stopping_budget_and_excludes_obstacles(tmp_path):
    names=['right_front_wrist_1_joint','left_front_wrist_1_joint','right_front_robotiq_85_left_knuckle_joint']
    cfg=configuration();cfg.update(exploration_mode=True,force_observation=True,
        force_comparison_lift=True,lift_m=.147548945,carrying_speed_multiplier=5,
        joint_velocity_overrides_rad_s={names[0]:.065})
    path=tmp_path/'comparison.yaml';path.write_text(yaml.safe_dump(cfg));accepted=configuration(path)
    np.testing.assert_allclose(velocity_limits(names,accepted),[.065,.05,cfg['finger_velocity_limit_rad_s']])
    cfg['joint_velocity_overrides_rad_s'][names[1]]=.2;path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError,match='Only carrying-arm'):configuration(path)


@pytest.mark.parametrize('exploration,forces,mode,accepted',[
    (False,True,'observe',False),(True,False,'observe',True),
    (True,True,'observe',True),(True,True,'disabled',False),
    (False,True,'enforce',True)])
def test_reserve_mode_is_explicit_exploration(tmp_path,exploration,forces,mode,accepted):
    cfg=configuration();cfg.update(exploration_mode=exploration,force_observation=forces,
        simulation_stop_reserve_mode=mode)
    path=tmp_path/'profile.yaml';path.write_text(yaml.safe_dump(cfg))
    if accepted:assert configuration(path)['simulation_stop_reserve_mode']==mode
    else:
        with pytest.raises(ValueError):configuration(path)


def test_observe_mode_keeps_geometric_margin_and_logs_full_reserve(monkeypatch):
    from uwa_cell_motion.geometry import SphereModel
    from uwa_cell_motion.planning import Problem
    model=TaskSphereModel.__new__(TaskSphereModel)
    model.names={'right_front':['right_front_wrist_3_joint'],'right_rear':['right_rear_wrist_3_joint']}
    model.motion_radii={rid:np.array([[1.]]) for rid in model.names}
    model.task=dict(joint_velocity_rad_s=.2,simulation_stop_reserve_mode='observe')
    cfg=dict(braking_acceleration_rad_s2=2.,rate_hz=10.,stop_latency_s=.1,
        state_timeout_s=.15,model_margin_m=.02)
    velocities={rid:[0.] for rid in model.names};ages={rid:.15 for rid in model.names}
    monkeypatch.setattr(SphereModel,'world',lambda self,*a,**k:{rid:np.zeros((1,3)) for rid in self.names})
    monkeypatch.setattr(SphereModel,'nearest',lambda self,*a:dict(clearance_m=.05))
    _,pairs=model.pairs({},velocities,ages,cfg)
    pair=pairs[0]
    assert pair['threshold_m']==pytest.approx(.02)
    assert pair['modeled_stopping_threshold_m']==pytest.approx(.18)
    assert pair['modeled_stopping_reserve_violated']
    # Planning uses the same model and reserve mode.
    problem=Problem.__new__(Problem);problem.names=model.names;problem.spheres=model;problem.cfg=cfg
    monkeypatch.setattr('uwa_cell_motion.planning.PAIRS',[('right_front','right_rear')])
    assert problem.thresholds()[0]['threshold_m']==pytest.approx(.02)
    model.task['simulation_stop_reserve_mode']='enforce'
    _,pairs=model.pairs({},velocities,ages,cfg)
    assert pairs[0]['threshold_m']==pytest.approx(.18)
    assert problem.thresholds()[0]['threshold_m']==pytest.approx(.18)


@pytest.mark.parametrize('rate,exploration,valid',[(10,False,True),(25,True,True),
    (50,True,True),(100,True,True),(25,False,False),(101,True,False),(9,True,False)])
def test_offline_reserve_model_cadence(tmp_path,rate,exploration,valid):
    cfg=configuration();cfg.update(simulation_guard_rate_hz=rate,exploration_mode=exploration)
    path=tmp_path/'rate.yaml';path.write_text(yaml.safe_dump(cfg))
    if valid:assert motion_configuration(configuration(path))['rate_hz']==rate
    else:
        with pytest.raises(ValueError):configuration(path)

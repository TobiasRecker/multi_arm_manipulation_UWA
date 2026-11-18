"""Scene-bound simulation envelopes; arm and finger motion remain distinct."""
import numpy as np
from uwa_cell_motion.common import config as motion_config
from uwa_cell_motion.geometry import SphereModel


def motion_configuration(task):
    cfg=motion_config()
    cfg.update(rate_hz=task.get('simulation_guard_rate_hz',10.),
        velocity_limit_rad_s=task['joint_velocity_rad_s'],
        acceleration_limit_rad_s2=task['joint_acceleration_rad_s2'],
        braking_acceleration_rad_s2=task.get('braking_acceleration_rad_s2',.5))
    return cfg


def velocity_limits(names,task):
    arm=task['joint_velocity_rad_s'];finger=task.get('finger_velocity_limit_rad_s',arm)
    # Unselected left obstacles retain their commissioning envelope.
    overrides=task.get('joint_velocity_overrides_rad_s',{})
    return np.array([(finger if '_robotiq_' in n else overrides.get(n,arm))
        if n.startswith(('right_front_','right_rear_')) else arm if task.get('drawing_recipe') and n.startswith('left_front_') and '_robotiq_' not in n else .05 for n in names])


class TaskSphereModel(SphereModel):
    def __init__(self,description,names,task,spacing=.05):
        super().__init__(description,names,spacing);self.task=task

    def stopping_budget(self,rid,velocities,age,cfg):
        v=np.maximum(np.abs(velocities),velocity_limits(self.names[rid],self.task))
        radii=self.motion_radii[rid]
        speed=float(np.max(radii@v))
        braking=float(np.max(radii@(v*v/(2*cfg['braking_acceleration_rad_s2']))))
        latency=1/cfg['rate_hz']+age+cfg['stop_latency_s']
        return speed*latency+braking,speed


    def arm_budget(self,rid,velocities,age,cfg):
        reserve,speed=self.stopping_budget(rid,velocities,age,cfg)
        if self.task.get('simulation_stop_reserve_mode','enforce')=='observe':
            return 0.,speed
        return reserve,speed

    def pairs(self,positions,velocities,ages,cfg,partial=False):
        world,pairs=super().pairs(positions,velocities,ages,cfg,partial=partial)
        budgets={rid:self.stopping_budget(rid,velocities[rid],ages[rid],cfg)[0] for rid in world}
        mode=self.task.get('simulation_stop_reserve_mode','enforce')
        for pair in pairs:
            a,b=pair['arms']
            threshold=cfg['model_margin_m']+budgets[a]+budgets[b]
            pair.update(stopping_reserve_mode=mode,modeled_stopping_threshold_m=threshold,
                modeled_stopping_reserve_violated=pair['clearance_m']<=threshold)
        return world,pairs

"""Scene-bound simulation envelopes; arm and finger motion remain distinct."""
import numpy as np
from uwa_cell_motion.common import config as motion_config
from uwa_cell_motion.geometry import SphereModel


def motion_configuration(task):
    cfg=motion_config()
    cfg.update(velocity_limit_rad_s=task['joint_velocity_rad_s'],
        acceleration_limit_rad_s2=task['joint_acceleration_rad_s2'],
        braking_acceleration_rad_s2=task.get('braking_acceleration_rad_s2',.5))
    return cfg


def velocity_limits(names,task):
    arm=task['joint_velocity_rad_s'];finger=task.get('finger_velocity_limit_rad_s',arm)
    # Unselected left obstacles retain their commissioning envelope.
    return np.array([(finger if '_robotiq_' in n else arm)
        if n.startswith(('right_front_','right_rear_')) else .05 for n in names])


class TaskSphereModel(SphereModel):
    def __init__(self,description,names,task,spacing=.05):
        super().__init__(description,names,spacing);self.task=task

    def arm_budget(self,rid,velocities,age,cfg):
        v=np.maximum(np.abs(velocities),velocity_limits(self.names[rid],self.task))
        radii=self.motion_radii[rid]
        speed=float(np.max(radii@v))
        braking=float(np.max(radii@(v*v/(2*cfg['braking_acceleration_rad_s2']))))
        latency=1/cfg['rate_hz']+age+cfg['stop_latency_s']
        return speed*latency+braking,speed

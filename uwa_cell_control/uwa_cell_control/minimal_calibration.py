"""Frozen calibration/parking paths using the shared minimal execution adapter."""
from contextlib import contextmanager
from datetime import datetime,timezone
import os
from pathlib import Path
import tempfile
import time

import numpy as np

from uwa_cell_gazebo.configuration import ROBOT_IDS, joint_names


def enabled():
    return os.environ.get('UWA_PROTECTION_BACKEND') == 'minimal'


class CheckedMotion:
    def __init__(self, client):
        self.client = client
        self.in_motion = False

    def snapshot(self):
        """Read complete finite model input once, without a runtime age gate."""
        self.client.health()
        names = [joint for arm in ROBOT_IDS for joint in joint_names(arm)]
        values = self.client.positions
        if not set(names) <= values.keys() or not np.isfinite([values[j] for j in names]).all():
            raise ValueError('Current complete finite 24-joint model input unavailable')
        return {joint: values[joint] for joint in names}

    def follow(self, arm, points):
        # Keep the exact frozen geometry, timing, velocity and acceleration.
        duration = points[-1]['time']
        self.in_motion = True
        self.client.follow_group({arm: dict(joint_names=joint_names(arm), points=points)},
                                 duration_s=duration)
        self.in_motion = False
        self.client.health()
        return dict(success=True, protection_backend='minimal', duration_s=duration,
                    completion_source='FollowJointTrajectory result',
                    final_positions=dict(self.client.positions))


def shared_readings(motion, mode):
    state=motion.snapshot()
    return {arm:dict(positions=[state[j] for j in joint_names(arm)],
        source='mock_joint_states' if mode=='mock' else 'live_joint_states',
        measurement_source='shared_protection_state',received_monotonic=time.monotonic(),
        recorded_at=datetime.now(timezone.utc).isoformat()) for arm in ROBOT_IDS}


@contextmanager
def checked_motion(inventory, layout, mode, arms):
    """Own one shared client/model per operation; no legacy stop fallback."""
    from uwa_cell_motion.common import config
    from uwa_cell_motion.hardware_model import HardwareProblem
    from uwa_cell_motion.minimal_execution import MinimalHardwareClient
    from ament_index_python.packages import get_package_share_directory
    default = Path(get_package_share_directory('uwa_cell_motion'))/'config/hardware_carton_supported_trend.yaml'
    with tempfile.TemporaryDirectory(prefix='uwa-minimal-calibration-') as directory:
        problem = HardwareProblem(directory, config(Path(os.environ.get('UWA_PROTECTION_CONFIG', default))),
                                  inventory, layout)
        client = MinimalHardwareClient(problem, mode, arms)
        motion = None
        try:
            client.connect()
            motion = CheckedMotion(client)
            motion.snapshot()
            yield motion
        except KeyboardInterrupt:
            if motion is not None and motion.in_motion:
                client.stop()  # Interruption of our dispatched motion uses the shared pause.
            raise
        finally:
            client.destroy_node()

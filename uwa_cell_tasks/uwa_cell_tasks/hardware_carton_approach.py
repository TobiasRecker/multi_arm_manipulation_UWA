"""Unloaded pregrasp checks layered onto the existing real hardware runner.

The base guard/model binding remains distinct from the extra static carton
collision model. This module cannot descend, command fingers or carry a load.
"""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import numpy as np


def unloaded_open_status(status):
    """Open/no-contact register state, including inactive grippers after boot.

    No activation cycle is needed for an unloaded arm approach. Full opening
    sweeps remain in collision checking; this does not qualify a loaded grip.
    """
    r=status.get('registers',{})
    if status.get('observed') is not True or status.get('busy') is not False:
        return False
    if r.get('FLT')!=0 or r.get('PRE')!=0 or not 0<=r.get('POS',256)<=8:
        return False
    return ((r.get('ACT'),r.get('STA'),r.get('OBJ')) in ((0,0,0),(1,3,3)))


def unloaded_guard_ready(guard):
    """Freshness is checked by the client; physical quiet is per-arm evidence."""
    return (set(guard.get('stationary_arms',[]))==
            {'left_front','left_rear','right_front','right_rear'} and not guard.get('faults'))


def slow_trajectory(trajectory, monitored_velocity, command_velocity):
    """Uniform time dilation, preserving geometry and monitored stop budgets."""
    if not (np.isfinite([monitored_velocity, command_velocity]).all() and
            0 < command_velocity <= monitored_velocity):
        raise ValueError('Command velocity must be positive and at most monitored bound')
    result = copy.deepcopy(trajectory); factor = monitored_velocity/command_velocity
    result['duration_s'] *= factor
    for point in result['points']:
        point['time'] *= factor
        point['velocities'] = (np.asarray(point['velocities'])/factor).tolist()
        point['accelerations'] = (np.asarray(point['accelerations'])/factor**2).tolist()
    return result


def canonical_base(description):
    root = ET.fromstring(description)
    for tag, name in [('link','pregrasp_carton_static'),('joint','pregrasp_carton_anchor')]:
        for node in list(root.findall(tag)):
            if node.get('name')==name or node.get('name','').startswith(name+'_'):
                root.remove(node)
    # Generated visual-only ChArUco files live under each output directory.
    # They do not participate in this kinematic/collision-model comparison.
    for link in root.findall('link'):
        for visual in list(link.findall('visual')):link.remove(visual)
    return ET.canonicalize(ET.tostring(root, encoding='unicode'), strip_text=True)


def checked_problem(directory, evidence_directory, inventory, *, command_velocity=.1):
    from uwa_cell_calibration.model import CollisionModel
    from uwa_cell_control.parallel_scan import collision_signature
    from uwa_cell_motion.geometry import SphereModel
    from uwa_cell_motion.hardware_model import HardwareProblem
    from uwa_cell_motion.common import arm_velocity_limit
    from uwa_cell_motion.planning import Problem

    directory = Path(directory).resolve()
    inventory = Path(inventory).resolve()
    evidence_directory = Path(evidence_directory).resolve()
    evidence = json.loads((evidence_directory/'evidence.json').read_text())
    if (evidence.get('artifact_type') != 'offline_hardware_pregrasp_evidence' or
        evidence.get('executable') is not False or evidence.get('hardware_plan') is not False or
        evidence.get('status') != 'GEOMETRIC_PATH_FOUND' or not evidence.get('saved_start_valid')):
        raise ValueError('Successful non-executable offline pregrasp evidence required')
    for entry in evidence['inputs'].values():
        if hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Pregrasp input changed: '+entry['path'])

    class UnloadedCartonProblem(HardwareProblem):
        def time_parameterize(self, request, path):
            # First validate all geometry/timing under the original monitored
            # limits. Slowing it changes neither thresholds nor configuration.
            monitored=min(arm_velocity_limit(self.cfg,r) for r in request['selected'])
            # The proxy changes timing only. Its collision/edge callbacks stay
            # bound to this full, unchanged per-arm monitored configuration.
            timing=SimpleNamespace(cfg=dict(self.cfg,velocity_limit_rad_s=monitored),
                                   check=self.check,edge=self.edge)
            original=Problem.time_parameterize(timing,request,path)
            return slow_trajectory(original,monitored,command_velocity)

    problem = UnloadedCartonProblem(directory, evidence['configuration'], inventory)
    frozen = (evidence_directory/'moveit/robot.urdf').read_text()
    if canonical_base(frozen) != canonical_base(problem.description):
        raise ValueError('Base hardware model changed since the pregrasp check')
    if collision_signature(frozen) != evidence['model_signature']:
        raise ValueError('Supplemental carton model signature changed')
    model = SphereModel(frozen, problem.names, problem.cfg['sphere_spacing_m'])
    if model.geometry.assets != evidence['mesh_sha256']:
        raise ValueError('Hardware/carton collision mesh changed')
    # Preserve every original allowed collision and the opening sweep policy;
    # add NO touch exemptions between carton and tools/robots.
    base_srdf = ET.fromstring((Path(directory)/'moveit/robot.srdf').read_text())
    problem.base_collision = problem.collision
    problem.collision = CollisionModel(frozen, Path(directory)/'carton-moveit')
    for entry in base_srdf.findall('disable_collisions'):
        problem.collision.scene.allowed_collision_matrix.set_entry(entry.get('link1'), entry.get('link2'), True)
    problem.supplemental_signature = evidence['model_signature']
    problem.pregrasp_evidence = evidence
    return problem

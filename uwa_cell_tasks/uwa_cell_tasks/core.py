"""Deterministic task contracts and immutable grasp groups; no ROS transport."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import yaml
from match_cooperative_handling.rigid_object import rigid, relative, tcp_target, pose_error

ARMS = ('right_front', 'right_rear')
CAMERAS = ARMS + ('oak',)
PHASES = ('observe', 'propose_grasp', 'plan_approach', 'review_plan', 'approach',
          'inspect_pregrasp', 'review_alignment', 'grasp', 'form_group', 'move_object',
          'set_down', 'release', 'done')
REVIEWS = ('review_strategy', 'review_plan', 'review_alignment')


def plain(value):
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    raise TypeError(type(value).__name__)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False, default=plain).encode()).hexdigest()


def seal(value):
    result = dict(value)
    result.pop('sha256', None)
    result['sha256'] = digest(result)
    return result


def verify(value):
    if value.get('sha256') != seal(value)['sha256']:
        raise ValueError('Artifact changed: regenerate and review it')
    return value


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False, default=plain) + '\n')
    temporary.replace(path)


def configuration(path=None):
    if path is None:
        from ament_index_python.packages import get_package_share_directory
        path = Path(get_package_share_directory('uwa_cell_tasks')) / 'config/carton.yaml'
    cfg = yaml.safe_load(Path(path).read_text())
    if cfg.get('schema_version') != 1 or tuple(cfg.get('arms', [])) != ARMS:
        raise ValueError('v1 requires schema1 and the two right arms in stable order')
    for key, value in cfg.items():
        if key in ('schema_version', 'arms', 'object_id', 'simulation_assumptions'): continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Expected positive finite ' + key)
    if cfg['lift_m'] > .05 or cfg['joint_velocity_rad_s'] > .05 or cfg['joint_acceleration_rad_s2'] > .10:
        raise ValueError('Task exceeds the first simulation operating envelope')
    if cfg['maximum_attempts'] != int(cfg['maximum_attempts']):
        raise ValueError('maximum_attempts must be integral')
    return cfg


@dataclass(frozen=True)
class Skill:
    id: str
    inputs: tuple
    requires: tuple
    provides: tuple
    resources: tuple = ()
    timeout_s: float = 30.
    stop_behavior: str = 'stop owned arms; retain grip; latch; no automatic resume'
    evidence: str = 'implementation present; consult validation report for tested conditions'
    version: int = 1
    environment: str = 'simulation64 only'


def skills():
    specs = [
        Skill('observe', ('asset_id', 'camera frames/K/D/timestamps'), ('stationary scene',), ('observation with provenance/quality',)),
        Skill('propose_grasp', ('observation', 'asset', 'joint state'), ('fresh unambiguous pose',), ('ranked local wall grasps',)),
        Skill('plan_approach', ('grasp', 'complete start'), ('full collision scene',), ('bound approach plan',), timeout_s=120),
        Skill('review', ('review packet hash', 'decision', 'reason'), ('stationary owned arms',), ('version-bound review',), timeout_s=300),
        Skill('approach', ('checked plan',), ('reviewed plan', 'fresh measured start', 'guard'), ('pregrasp reached',), ARMS, 600),
        Skill('inspect_pregrasp', ('fresh images', 'expected contacts'), ('stationary arms',), ('alignment evidence',)),
        Skill('grasp', ('grasp', 'contact telemetry'), ('alignment reviewed', 'object supported'), ('two-sided contacts per gripper',), ARMS, 60),
        Skill('form_group', ('object pose', 'measured TCPs', 'contacts'), ('both grasps confirmed',), ('immutable object-to-TCP offsets',), ARMS),
        Skill('move_object', ('GraspGroup', 'object-frame path'), ('group active', 'whole-scene validation',), ('shared-time object-derived motion',), ARMS, 120),
        Skill('set_down', ('GraspGroup', 'support telemetry'), ('group active',), ('stationary supported object',), ARMS, 120),
        Skill('release', ('supported object',), ('support independently confirmed', 'stationary group'), ('open grippers; dissolved group',), ARMS, 60),
    ]
    return [asdict(spec) for spec in specs]


class GraspGroup:
    """No per-arm motion API. Offsets cannot be changed while loaded."""
    def __init__(self, object_id, world_object, tcps, contacts, cfg):
        if tuple(tcps) != ARMS or set(contacts) != set(tcps):
            raise ValueError('Both right members and contact records required')
        if not all(contacts[a].get('left_pad') and contacts[a].get('right_pad') for a in tcps):
            raise ValueError('Both pads of every gripper must contact the object')
        self.object_id = object_id; self.members = tuple(tcps); self.cfg = dict(cfg)
        self._offsets = {a: relative(world_object, t) for a, t in tcps.items()}
        for t in self._offsets.values(): t.setflags(write=False)
        self.stopped = None; self.released = False

    @property
    def offsets(self): return {a: t.copy() for a, t in self._offsets.items()}

    def targets(self, world_object, twist=None):
        if self.stopped or self.released: raise RuntimeError(self.stopped or 'Group released')
        return {a: tcp_target(world_object, t, twist) for a, t in self._offsets.items()}

    def check(self, world_object, measured_tcps):
        if set(measured_tcps) != set(self.members):
            self.stop('Member state missing'); return False
        for a, (target, _) in self.targets(world_object).items():
            distance, angle = pose_error(measured_tcps[a], target)
            if distance > self.cfg['relative_position_tolerance_m'] or angle > self.cfg['relative_angle_tolerance_rad']:
                self.stop(a + ': rigid grasp error/slip'); return False
        return True

    def stop(self, reason):
        self.stopped = self.stopped or str(reason)
        return self.members

    def release(self, *, supported, stationary):
        if not supported or not stationary: raise RuntimeError('Release requires confirmed support and standstill')
        self.released = True

    def record(self):
        return dict(object_id=self.object_id, members=self.members, object_to_tcp=self.offsets,
                    stopped=self.stopped, released=self.released)


class RunStore:
    """One runner owns state.json; external reviewers append hash-bound requests."""
    def __init__(self, directory):
        self.directory = Path(directory).resolve(); self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'state.json'
        self.state = json.loads(self.path.read_text()) if self.path.exists() else dict(
            schema_version=1, state='CREATED', phase='observe', revision=0, history=[])

    def event(self, state, phase, **data):
        self.state.update(state=state, phase=phase, **data)
        self.state['history'].append(dict(state=state, phase=phase, time_unix_s=time.time(), **data))
        write_json(self.path, self.state)

    def request_review(self, stage, evidence):
        self.state['revision'] += 1
        packet = seal(dict(stage=stage, revision=self.state['revision'], evidence=evidence))
        write_json(self.directory / 'review.json', packet)
        self.event('WAITING_REVIEW', stage, review_sha256=packet['sha256'])
        return packet

    def submit_review(self, packet_hash, decision, reason):
        packet = verify(json.loads((self.directory / 'review.json').read_text()))
        if (self.state['state'] != 'WAITING_REVIEW' or packet_hash != packet['sha256']
                or packet_hash != self.state['review_sha256']):
            raise ValueError('Review does not match the current waiting revision')
        if decision not in ('continue', 'observe', 'replan', 'abort') or not reason.strip():
            raise ValueError('Explicit supported decision and reason required')
        decision_path=self.directory / ('decision-' + packet_hash + '.json')
        if decision_path.exists():raise ValueError('This review already has a decision')
        write_json(decision_path, dict(
            packet_sha256=packet_hash, decision=decision, reason=reason, time_unix_s=time.time()))

    def decision(self, packet):
        path = self.directory / ('decision-' + packet['sha256'] + '.json')
        if not path.exists(): return None
        value = json.loads(path.read_text())
        if value['packet_sha256'] != packet['sha256']: raise ValueError('Stale review')
        return value

"""Deterministic task contracts and immutable grasp groups; no ROS transport."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path
import time
import fcntl
import os
from contextlib import contextmanager

import numpy as np
import yaml
from match_cooperative_handling.rigid_object import rigid, relative, tcp_target

ARMS = ('right_front', 'right_rear')
CAMERAS = ARMS + ('oak',)
PHASES = ('observe', 'propose_grasp', 'plan_approach', 'review_plan', 'approach',
          'inspect_pregrasp', 'review_alignment', 'grasp', 'form_group', 'move_object',
          'set_down', 'release', 'done')
REVIEWS = ('review_strategy', 'review_plan', 'review_alignment')


@contextmanager
def resource_lease(namespace,root=Path('/tmp')):
    """All recipes in one simulation namespace share its controller resources."""
    key=digest(dict(domain=64,namespace=namespace))[:24]
    with (Path(root)/f'uwa-task-{os.getuid()}-{key}.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise RuntimeError('Another task owns this simulation namespace') from error
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


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
    cfg.setdefault('simulation_real_time_factor',.7)
    cfg.setdefault('force_observation',False)
    cfg.setdefault('exploration_mode',False)
    cfg.setdefault('simulation_stop_reserve_mode','enforce')
    cfg.setdefault('simulation_guard_rate_hz',10.)
    cfg.setdefault('finger_velocity_limit_rad_s',cfg['joint_velocity_rad_s'])
    cfg.setdefault('grasp_entry_min_duration_s',30.)
    cfg.setdefault('braking_acceleration_rad_s2',.5)
    cfg.setdefault('physics_step_s',.001)
    cfg.setdefault('gripper_motor_torque_limit_nm',.35)
    if not isinstance(cfg['force_observation'],bool):raise ValueError('force_observation must be boolean')
    if not isinstance(cfg['exploration_mode'],bool):raise ValueError('exploration_mode must be boolean')
    if cfg.get('schema_version') != 1 or tuple(cfg.get('arms', [])) != ARMS:
        raise ValueError('v1 requires schema1 and the two right arms in stable order')
    drawing = cfg.get('drawing_recipe')
    if drawing is not None:
        if not isinstance(drawing, str) or not Path(drawing).is_absolute():
            raise ValueError('Drawing recipe must be an absolute file path')
        if not (cfg['exploration_mode'] and cfg['simulation_stop_reserve_mode']=='observe'):
            raise ValueError('Drawing contact experiment requires force-observed simulation')
        if cfg['joint_velocity_rad_s'] != .1 or cfg.get('roll_long_axis'):
            raise ValueError('Drawing requires the 0.1 rad/s profile and one recipe')
    for key, value in cfg.items():
        if key in ('schema_version', 'arms', 'object_id', 'simulation_assumptions','gripper_transmission','physics_engine','force_observation','exploration_mode','roll_long_axis','placement_table','force_comparison_lift','joint_velocity_overrides_rad_s','simulation_stop_reserve_mode','drawing_recipe'): continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Expected positive finite ' + key)
    if cfg['simulation_stop_reserve_mode'] not in ('enforce','observe'):
        raise ValueError('simulation_stop_reserve_mode must be enforce or observe')
    if cfg['simulation_stop_reserve_mode']=='observe' and not (cfg['exploration_mode'] and cfg['force_observation']):
        raise ValueError('Observe-only stopping reserve requires explicit force-observed simulation exploration')
    if not 10<=cfg['simulation_guard_rate_hz']<=100 or (cfg['simulation_guard_rate_hz']!=10 and not cfg['exploration_mode']):
        raise ValueError('Faster simulation guard requires exploration and a rate in[10,100]Hz')
    comparison=cfg.get('force_comparison_lift',False)
    multiplier=cfg.get('carrying_speed_multiplier',1.)
    if not isinstance(comparison,bool):raise ValueError('force_comparison_lift must be boolean')
    if comparison and (not cfg['exploration_mode'] or cfg.get('roll_long_axis')):
        raise ValueError('Force comparison requires explicit exploration and a translation-only prefix')
    if not 1<=multiplier<=5 or (multiplier!=1 and not cfg['exploration_mode']):
        raise ValueError('Carrying multiplier requires exploration and must be in[1,5]')
    overrides=cfg.get('joint_velocity_overrides_rad_s',{})
    from uwa_cell_description.configuration import joint_names
    allowed={j for a in ARMS for j in joint_names(a)}
    if not isinstance(overrides,dict) or set(overrides)-allowed:raise ValueError('Only carrying-arm joints may override velocity')
    if overrides and not cfg['exploration_mode']:raise ValueError('Velocity overrides require exploration')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=1 for v in overrides.values()):
        raise ValueError('Invalid per-joint velocity envelope')
    if cfg.get('placement_table') not in (None,'left','right'):raise ValueError('placement_table must be left or right')
    if not isinstance(cfg.get('roll_long_axis',False),bool):raise ValueError('roll_long_axis must be boolean')
    if cfg.get('maximum_roll_lift_m',.25)>.25:raise ValueError('Roll lift exceeds simulation envelope')
    exploration=cfg['exploration_mode']
    if not .0001<=cfg['physics_step_s']<=.001:
        raise ValueError('Physics step must be between0.1ms and1ms')
    if cfg['gripper_motor_torque_limit_nm']>(2. if exploration else .35):
        raise ValueError('Task exceeds the simulation motor torque envelope')
    if cfg['lift_m'] > (.25 if comparison else .05) or cfg['joint_velocity_rad_s'] > (1. if exploration else .05) or cfg['joint_acceleration_rad_s2'] > (2. if exploration else .10):
        raise ValueError('Task exceeds the first simulation operating envelope')
    if cfg['finger_velocity_limit_rad_s']>(2. if exploration else .05) or cfg['braking_acceleration_rad_s2']>5.:
        raise ValueError('Task exceeds the simulation observation/stop envelope')
    if exploration and not cfg['force_observation']:raise ValueError('Exploration requires force observation')
    if cfg['simulation_real_time_factor']>1.:
        raise ValueError('Contact qualification requires an unaccelerated simulation')
    if cfg['maximum_attempts'] != int(cfg['maximum_attempts']):
        raise ValueError('maximum_attempts must be integral')
    if cfg['gripper_transmission'] not in ('native_gear','elastic_gear'):
        raise ValueError('Unsupported gripper transmission model')
    if cfg['physics_engine'] not in ('bullet_featherstone','dartsim'):
        raise ValueError('Unsupported physics engine')
    if cfg['gripper_transmission']=='native_gear' and cfg['physics_engine']!='bullet_featherstone':
        raise ValueError('Native gear constraints require Bullet Featherstone in this installation')
    if not (0<cfg['gripper_fine_velocity_rad_s']<=cfg['gripper_coarse_velocity_rad_s']<=min(.5 if exploration else .02,cfg['finger_velocity_limit_rad_s'])
            and 0<cfg['gripper_fine_start_rad']<.8):
        raise ValueError('Invalid coarse/fine contact closure envelope')
    return cfg


def object_point_height(pose,point_object):
    """World height of an explicitly declared asset-frame verification point."""
    t=rigid(pose);point=np.asarray(point_object,dtype=float)
    if point.shape!=(3,) or not np.isfinite(point).all():raise ValueError('Finite object reference point required')
    return float(t[2,:3]@point+t[2,3])


def gripper_profile(starts,target,cfg):
    """Shared schedule: coarse free closure, fine contact entry, coarse opening."""
    coarse=cfg['gripper_coarse_velocity_rad_s'];fine=cfg['gripper_fine_velocity_rad_s'];threshold=cfg['gripper_fine_start_rad']
    starts=np.asarray(starts,float)
    if not np.isfinite(starts).all() or not np.isfinite(target) or not 0<=target<=.8:
        raise ValueError('Invalid physical gripper target')
    first=np.maximum(0.,np.minimum(target,threshold)-starts)
    second=np.maximum(0.,target-np.maximum(starts,threshold))
    durations=np.where(target>=starts,first/coarse+second/fine,(starts-target)/coarse)
    duration=max(1.,float(durations.max()));points=[]
    for t in np.linspace(0,duration,int(np.ceil(duration/.1))+2):
        local=t*durations/duration
        positions=np.where(target>=starts,starts+np.minimum(local*coarse,first)+np.minimum(np.maximum(0.,local-first/coarse)*fine,second),
            starts-local*coarse)
        points.append(dict(time=float(t),positions=positions.tolist()))
    return dict(duration_s=duration,points=points)


@dataclass(frozen=True)
class Skill:
    id: str
    inputs: tuple
    requires: tuple
    provides: tuple
    resources: tuple = ()
    timeout_s: float = 30.
    stop_behavior: str = 'cancel active trajectory goals; retain grip latch'
    evidence: str = 'implementation present; consult validation report for tested conditions'
    version: int = 1
    environment: str = 'simulation64 only'


def skills():
    specs = [
        Skill('observe', ('asset_id', 'camera frames/K/D/timestamps'), ('stationary scene',), ('observation with provenance/quality',),timeout_s=90),
        Skill('propose_grasp', ('observation', 'asset', 'joint state'), ('fresh unambiguous pose',), ('ranked local wall grasps',)),
        Skill('plan_approach', ('grasp', 'complete start'), ('full collision scene',), ('bound approach plan',), timeout_s=120),
        Skill('review', ('review packet hash', 'decision', 'reason'), ('stationary owned arms',), ('version-bound review',), timeout_s=300),
        Skill('approach', ('checked plan',), ('reviewed plan', 'matching start snapshot'), ('pregrasp reached',), ARMS, 600),
        Skill('inspect_pregrasp', ('fresh images', 'expected contacts'), ('stationary arms',), ('alignment evidence',),timeout_s=90),
        Skill('grasp', ('grasp', 'contact telemetry'), ('alignment reviewed', 'object supported'), ('two-sided contacts per gripper',), ARMS, 1200),
        Skill('form_group', ('object pose', 'measured TCPs', 'contacts'), ('both grasps confirmed',), ('immutable object-to-TCP offsets',), ARMS),
        Skill('move_object', ('GraspGroup', 'object-frame path'), ('group active', 'whole-scene validation',), ('shared-time object-derived motion',), ARMS, 120),
        Skill('set_down', ('GraspGroup', 'support telemetry'), ('group active',), ('planned set-down reached',), ARMS, 120),
        Skill('release', ('supported object',), ('set-down phase complete',), ('open grippers; dissolved group',), ARMS, 240),
        Skill('validate_force_backend',('engine/plugin hashes','known loads','physics steps/repeats'),
            ('own finite reference world','no robot commands'),('force/frame/impulse reference evidence',),
            timeout_s=300,stop_behavior='end own finite reference world; never commands robots',
            evidence='12-case known-load matrix passed; consult force_reference_20261116_matrix01'),
        Skill('observe_loads',('bound native force windows','scene'),
            ('validated force backend','recorder started before arming'),
            ('per-jaw means/peaks/impulses','joint-frame reactions','coverage report'),
            stop_behavior='read-only observation; no motion or release commands'),
        Skill('prepare_contact_fixture',('verified pregrasp plan','source scene'),
            ('new output directory','unchanged collision/kinematic signature'),('new virtual initial-state layout',),
            stop_behavior='files only; never resets an existing world or loaded group'),
        Skill('run_simulation_experiment',('explicit exploration profile','speed/repeat matrix','image reference'),
            ('fresh isolated world','bound source/binaries','pre-armed recorder','agent reviews'),
            ('retained positive/negative cases','motion/load/coverage reports'),ARMS,1500),
    ]
    return [asdict(spec) for spec in specs]


class GraspGroup:
    """No per-arm motion API. Offsets cannot be changed while loaded."""
    def __init__(self, object_id, world_object, tcps, contacts, cfg, contact_regions=None):
        if set(tcps) != set(ARMS) or set(contacts) != set(tcps):
            raise ValueError('Both right members and contact records required')
        if not all(contacts[a].get('left_pad') and contacts[a].get('right_pad') for a in tcps):
            raise ValueError('Both pads of every gripper must contact the object')
        self.object_id = object_id; self.members = ARMS; self.cfg = dict(cfg)
        self._offsets = {a: relative(world_object, tcps[a]) for a in ARMS}
        for t in self._offsets.values(): t.setflags(write=False)
        self.released = False
        self.contact_regions=json.loads(json.dumps(contact_regions or {},default=plain))

    @property
    def offsets(self): return {a: t.copy() for a, t in self._offsets.items()}

    def targets(self, world_object, twist=None):
        if self.released: raise RuntimeError('Group released')
        return {a: tcp_target(world_object, t, twist) for a, t in self._offsets.items()}

    def release(self):
        self.released = True

    def record(self):
        return dict(object_id=self.object_id, members=self.members, object_to_tcp=self.offsets,
                    released=self.released,contact_regions=self.contact_regions)


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

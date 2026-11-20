"""Read-only observations for real carton commissioning. No actuation API."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import struct
import time

import yaml

from .core import ARMS, seal, write_json

VARIABLES = ('ACT', 'STA', 'FLT', 'OBJ', 'POS', 'PRE', 'SPE', 'FOR', 'COU')
OUTPUT_FIELDS = ('timestamp,actual_q,actual_qd,actual_TCP_pose,actual_TCP_force,'
                 'tcp_offset,speed_scaling,target_speed_fraction,runtime_state,robot_mode,safety_mode')
OUTPUT_TYPES = b'DOUBLE,VECTOR6D,VECTOR6D,VECTOR6D,VECTOR6D,VECTOR6D,DOUBLE,DOUBLE,UINT32,INT32,INT32'


def require_observation_domain():
    if (os.environ.get('ROS_DOMAIN_ID') != '66' or
            os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE') != 'LOCALHOST'):
        raise ValueError('Real observations require domain66 and LOCALHOST discovery')


class GripperObserver:
    """Strict GET allowlist; no SET, activation, calibration or motion method.

    The backed-up Robotiq URCap1.8.6 communication script specifies63352 and
    these variables. Both actual endpoints returned newline-framed ACT replies.
    A malformed/incomplete response fails instead of guessing a register value.
    """
    def __init__(self, host, timeout=.5):
        self.socket = socket.create_connection((host, 63352), timeout=timeout)
        self.socket.settimeout(timeout)
        self.timeout = timeout
        self.buffer = b''

    def get(self, name):
        if name not in VARIABLES:
            raise ValueError('Unsupported read-only gripper variable')
        self.socket.sendall(('GET ' + name + '\n').encode('ascii'))
        deadline = time.monotonic() + self.timeout
        while b'\n' not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Incomplete gripper reply')
            self.socket.settimeout(remaining)
            chunk = self.socket.recv(128)
            if not chunk:
                raise RuntimeError('Gripper connection ended before framed reply')
            self.buffer += chunk
            if len(self.buffer) > 256:
                raise ValueError('Oversized gripper reply')
        line, self.buffer = self.buffer.split(b'\n', 1)
        match = re.fullmatch(name.encode('ascii') + rb' ([0-9]{1,3})\r?', line)
        if match is None or int(match[1]) > 255 or self.buffer:
            raise ValueError('Unexpected gripper reply')
        return int(match[1])

    def snapshot(self):
        start = time.monotonic()
        registers = {name: self.get(name) for name in VARIABLES}
        return dict(registers=registers, read_duration_s=time.monotonic()-start,
                    activated=registers['ACT'] == 1 and registers['STA'] == 3,
                    fault_free=registers['FLT'] == 0,
                    object_detected=registers['OBJ'] in (1, 2),
                    atomic_snapshot=False, force_unit='raw setting; not newtons',
                    motor_current_unit='raw register; not per-jaw force',
                    note='Object detection alone does not prove four pad contacts or holding strength')

    def close(self):
        self.socket.close()


def decode_arm_output(payload, recipe):
    if len(payload) != 277 or payload[0] != recipe:
        raise ValueError('Unexpected read-only commissioning RTDE frame')
    values = struct.unpack('>33dIii', payload[1:])
    if not all(math.isfinite(x) for x in values[:33]) or values[0] < 0:
        raise ValueError('Invalid RTDE observation')
    if not all(0 <= x <= 1 for x in values[31:33]):
        raise ValueError('Invalid native speed scaling')
    return dict(device_timestamp_s=values[0], actual_q=list(values[1:7]),
                actual_qd=list(values[7:13]), actual_tcp_pose_ur_base=list(values[13:19]),
                actual_tcp_force_raw=list(values[19:25]), active_tcp_offset=list(values[25:31]),
                speed_scaling=values[31], target_speed_fraction=values[32],
                effective_speed_scaling=values[31]*values[32], runtime_state=values[33],
                robot_mode=values[34], safety_mode=values[35])


def arm_observation(host, samples=20):
    from uwa_cell_control.capture_rtde import OutputReader
    # Reuse the existing strictly output-only transport. Construct without
    # its short recipe: this probe requests more OUTPUT fields, never inputs.
    reader = OutputReader.__new__(OutputReader)
    reader.socket = socket.create_connection((host, 30004), timeout=1.)
    reader.socket.settimeout(2.)
    try:
        if reader.request(86, struct.pack('>H', 2)) != b'\x01':
            raise ValueError('RTDE protocol2 rejected')
        reply = reader.request(79, struct.pack('>d', 20.)+OUTPUT_FIELDS.encode('ascii'))
        if len(reply) < 2 or reply[0] == 0 or reply[1:] != OUTPUT_TYPES:
            raise ValueError('Required commissioning RTDE OUTPUT fields unavailable')
        recipe = reply[0]
        if reader.request(83) != b'\x01':
            raise ValueError('RTDE output streaming rejected')
        reader.socket.settimeout(.3)
        rows = []; deadline = time.monotonic()+4.; last_received = None
        while len(rows) < samples:
            if time.monotonic() > deadline:
                raise TimeoutError('Commissioning observation deadline exceeded')
            kind, payload = reader.receive()
            if kind != 85:
                continue
            value = decode_arm_output(payload, recipe); now = time.monotonic()
            if rows and value['device_timestamp_s'] <= rows[-1]['device_timestamp_s']:
                raise ValueError('Device timestamp did not advance')
            if last_received is not None and now-last_received > .2:
                raise ValueError('Actual-state reception gap exceeds200ms')
            value['received_monotonic_s'] = now
            value['reception_gap_s'] = 0. if last_received is None else now-last_received
            rows.append(value); last_received = now
        return dict(samples=rows, stationary_observed=max(abs(v) for r in rows for v in r['actual_qd']) <= .001,
                    source='RTDE OUTPUT only30004',
                    tcp_frame='Native UR base; not calibrated cell world',
                    wrench_interpretation='Raw native TCP wrench; frame/payload/tare not independently qualified; not jaw clamping force')
    finally:
        reader.close()


def observe(inventory):
    require_observation_domain()
    robots = yaml.safe_load(Path(inventory).read_text())['robots']
    expected = {'left_front', 'left_rear', *ARMS}
    if set(robots) != expected:
        raise ValueError('Complete four-arm inventory required for obstacle observations')
    def item(request):
        kind, rid = request; host = robots[rid]['ip']
        try:
            if kind == 'arm':
                result = arm_observation(host)
            else:
                observer = GripperObserver(host)
                try:
                    result = observer.snapshot()
                finally:
                    observer.close()
            return kind, rid, dict(observed=True, **result)
        except (OSError, RuntimeError, ValueError) as error:
            return kind, rid, dict(observed=False, error=str(error))
    requests = [('arm', rid) for rid in sorted(robots)]+[('gripper', rid) for rid in ARMS]
    result = dict(arms={}, grippers={})
    with ThreadPoolExecutor(max_workers=6) as pool:
        for kind, rid, value in pool.map(item, requests):
            result['arms' if kind == 'arm' else 'grippers'][rid] = value
    return result


def operating_stationarity(observation,cfg):
    """Use exactly the armed guard's configured quiet criterion on recorded data."""
    from uwa_cell_motion.guard_core import GuardState
    from uwa_cell_motion.common import joint_velocity_limits,SPEED_TOLERANCE
    for rid,arm in observation['arms'].items():
        if not arm.get('observed') or not arm.get('samples'):continue
        arm['peak_stationary_observed']=arm.get('stationary_observed',False)
        core=GuardState(cfg);rows=arm['samples']
        for row in rows:
            stamp=row['device_timestamp_s'];core.receive(rid,row['actual_q'],row['actual_qd'],stamp,stamp)
        evidence=core.stationarity_evidence(rid,rows[-1]['device_timestamp_s'])
        limits=joint_velocity_limits(cfg,rid,6)
        within_speed=all(all(abs(v)<=float(limit)*SPEED_TOLERANCE for v,limit in zip(row['actual_qd'],limits))for row in rows)
        evidence['operating_speed_within_bounds']=within_speed
        evidence['scope']='Recorded device-time window; live freshness/holds must still pass before motion'
        native_ready=all(r.get('robot_mode')==7 and r.get('safety_mode') in (1,2) for r in rows)
        evidence['native_state_suitable_for_planning']=native_ready
        arm['stationarity_evidence']=evidence
        arm['stationary_observed']=evidence['confirmed'] and within_speed and native_ready
    return observation


def validate_planning_snapshot(observation):
    """Check saved snapshot eligibility before computing a carton approach."""
    expected = ("left_front", "left_rear", *ARMS)
    arms = observation.get("arms", {})
    errors = []
    for rid in expected:
        arm = arms.get(rid, {})
        samples = arm.get("samples", ())
        if arm.get("observed") is not True or not samples:
            errors.append(f"{rid}: {arm.get('error') or 'native observation missing'}")
            continue
        sample = samples[-1]
        mode, safety, runtime = (sample.get(key) for key in ("robot_mode", "safety_mode", "runtime_state"))
        if mode != 7 or safety != 1 or runtime not in (1, 2):
            label = {3: "POWER_OFF", 7: "RUNNING"}.get(mode, str(mode))
            errors.append(f"{rid}: {label} (robot_mode={mode}, safety_mode={safety}, runtime_state={runtime})")
        elif arm.get("stationary_observed") is not True:
            evidence = arm.get("stationarity_evidence", {})
            reason = evidence.get("reason") or "stationarity not confirmed"
            if evidence.get("operating_speed_within_bounds") is False:
                reason = "operating velocity limit exceeded"
            elif evidence.get("native_state_suitable_for_planning") is False:
                reason = "native state unsuitable during snapshot"
            errors.append(f"{rid}: {reason}")
        else:
            joints = sample.get("actual_q", ())
            if (not isinstance(joints, (list, tuple)) or len(joints) != 6
                    or not all(isinstance(q, (int, float)) and math.isfinite(q) for q in joints)):
                errors.append(f"{rid}: invalid native joint positions")
    if errors:
        raise ValueError("Carton planning snapshot unsuitable. " + ". ".join(errors))
    return list(expected)


def prepare(directory, profile_path, inventory, *, live=False, stationarity_config=None):
    """Write a preparation bundle, never a plan accepted by hardware execute."""
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    profile_path, inventory = Path(profile_path), Path(inventory)
    profile = yaml.safe_load(profile_path.read_text())
    if (profile.get('mode') != 'hardware_preparation_only' or tuple(profile.get('arms', [])) != ARMS or
            profile.get('object_speed_m_s') != .0005 or profile.get('lift_m') != .005):
        raise ValueError('Expected the explicit slow first-test preparation profile')
    observation = observe(inventory) if live else dict(arms={}, grippers={})
    if stationarity_config is not None:
        from uwa_cell_motion.common import config
        operating_stationarity(observation,config(stationarity_config))
        observation['stationarity_configuration']=dict(path=str(Path(stationarity_config).resolve()),sha256=hashlib.sha256(Path(stationarity_config).read_bytes()).hexdigest())
    write_json(directory/'observations.json', seal(observation))
    (directory/'profile.yaml').write_bytes(profile_path.read_bytes())
    blockers = ['world/base/table registration requires real verification',
                'real object localization and jaw alignment require live verification',
                'gripper activation, empty travel and low-force setting unqualified',
                'coupled hardware object executor and loaded stopping unqualified']
    if live:
        for rid, value in observation['arms'].items():
            if not value['observed']:
                blockers.append(rid+': actual state unavailable')
        for rid, value in observation['grippers'].items():
            if not value['observed'] or not value.get('activated'):
                blockers.append(rid+': gripper not confirmed active; no activation attempted')
    record = seal(dict(kind='carton_hardware_preparation', prepared=True, motion_ready=False,
        hardware_plan=False, simulation_only=False, commands_sent=[], actuation_capability=False,
        observed_at_utc=datetime.now(timezone.utc).isoformat(), profile=profile,
        inventory_sha256=hashlib.sha256(inventory.read_bytes()).hexdigest(),
        profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        observer_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        live_observation=live, blockers=blockers,
        scope='Read-only commissioning observations; starting URs grants no automatic movement',
        next_step='Operator starts URs when present; repeat observation, align model and validate real gripper/control chain before motion'))
    write_json(directory/'preparation.json', record)
    return record

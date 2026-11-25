"""Finite task measurements, not a safety monitor. No native sensor/payload changes."""
import math
import socket
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ARMS = ('right_front', 'right_rear')
G = 9.80665
FIELDS = ('timestamp,actual_q,actual_qd,actual_TCP_pose,actual_TCP_force,'
          'tcp_offset,payload,payload_cog')
TYPES = b'DOUBLE,VECTOR6D,VECTOR6D,VECTOR6D,VECTOR6D,VECTOR6D,DOUBLE,VECTOR3D'


def sample_arm(host, seconds=2.):
    if not math.isfinite(seconds) or not .1 <= seconds <= 10:
        raise ValueError('Finite weighing window must be between .1 and 10 seconds')
    from uwa_cell_control.capture_rtde import OutputReader
    reader = OutputReader.__new__(OutputReader)
    reader.socket = socket.create_connection((host, 30004), timeout=2.)
    reader.socket.settimeout(3.)
    try:
        if reader.request(86, struct.pack('>H', 2)) != b'\x01':
            raise ValueError('RTDE protocol rejected')
        reply = reader.request(79, struct.pack('>d', 20.) + FIELDS.encode())
        if len(reply) < 2 or reply[1:] != TYPES or not reply[0]:
            raise ValueError('Weighing output fields unavailable')
        if reader.request(83) != b'\x01':
            raise ValueError('RTDE output stream rejected')
        rows = []
        deadline = time.monotonic() + seconds + 4.
        while time.monotonic() < deadline:
            kind, payload = reader.receive()
            if kind != 85:
                continue
            if len(payload) != 281 or payload[0] != reply[0]:
                raise ValueError('Unexpected weighing frame')
            values = struct.unpack('>35d', payload[1:])
            if not all(math.isfinite(x) for x in values):
                raise ValueError('Nonfinite weighing frame')
            if rows and values[0] <= rows[-1]['device_time_s']:
                raise ValueError('Weighing device time did not advance')
            rows.append(dict(device_time_s=values[0], received_monotonic_s=time.monotonic(),
                q=list(values[1:7]), qd=list(values[7:13]), tcp_pose=list(values[13:19]),
                wrench_base=list(values[19:25]), tcp_offset=list(values[25:31]),
                payload_kg=values[31], payload_cog=list(values[32:35])))
            if len(rows) >= 3 and rows[-1]['device_time_s']-rows[0]['device_time_s'] >= seconds:
                return rows
        raise TimeoutError('Weighing measurement window incomplete')
    finally:
        reader.close()


def capture(inventory, seconds=2.):
    import yaml
    robots = yaml.safe_load(Path(inventory).read_text())['robots']
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {arm: pool.submit(sample_arm, robots[arm]['ip'], seconds) for arm in ARMS}
        return dict(schema_version=1, method='stored_unloaded_reference; no zero_ftsensor command',
                    window_s=seconds, arms={arm: f.result() for arm, f in futures.items()})


def estimate(reference, supported, lifted, rotations):
    """Project signed *summed* external forces, never sum their magnitudes."""
    result = dict(method='sum of world-vertical load increments / standard gravity',
        gravity_m_s2=G, mass_kg=None, arms={}, warnings=[],
        interpretation='Task evidence only; no independent proof of four pads, no slip or absence of table contact',
        sensor_spec_note='UR5e published force accuracy ±4 N per arm; sample scatter is not absolute mass accuracy',
        user_mass_estimate_kg=[.5, 1.], user_mass_estimate_is_reference=False)
    totals = dict(reference=0., supported=0., lifted=0.)
    spans = dict(reference=0., supported=0., lifted=0.)
    valid_payload = True
    for arm in ARMS:
        R = np.asarray(rotations[arm], float)
        if (R.shape != (3, 3) or not np.isfinite(R).all()
                or not np.allclose(R.T@R, np.eye(3), atol=1e-8)
                or not np.isclose(np.linalg.det(R), 1., atol=1e-8)):
            raise ValueError('Invalid UR-base to world rotation')
        arm_result = {}
        settings = []
        for name, window in [('reference', reference), ('supported', supported), ('lifted', lifted)]:
            rows = window['arms'][arm]
            if len(rows) < 3:
                raise ValueError('Insufficient weighing samples')
            stamps = np.asarray([r['device_time_s'] for r in rows], float)
            if (not np.isfinite(stamps).all() or np.any(np.diff(stamps) <= 0)
                    or stamps[-1]-stamps[0] < window['window_s']-1e-6):
                raise ValueError('Incomplete or nonadvancing weighing window')
            forces = np.asarray([r['wrench_base'][:3] for r in rows], float)
            if forces.shape != (len(rows), 3) or not np.isfinite(forces).all():
                raise ValueError('Invalid force samples')
            downward = -(forces@R.T)[:, 2]
            median = float(np.median(downward))
            lo, hi = map(float, np.quantile(downward, [.05, .95]))
            arm_result[name] = dict(downward_median_n=median, central_90_percent_n=[lo, hi], samples=len(rows))
            totals[name] += median
            spans[name] += max(median-lo, hi-median)
            settings.extend((r['payload_kg'], *r['payload_cog'], *r['tcp_offset']) for r in rows)
        if not np.isfinite(settings).all() or not np.allclose(settings, settings[0], atol=1e-10, rtol=0):
            valid_payload = False
            result['warnings'].append(arm+': payload or TCP settings changed; differential mass invalid')
        arm_result['load_n'] = arm_result['lifted']['downward_median_n']-arm_result['reference']['downward_median_n']
        arm_result['equivalent_mass_kg'] = arm_result['load_n']/G
        result['arms'][arm] = arm_result
    load = totals['lifted']-totals['reference']
    scatter = spans['lifted']+spans['reference']
    result.update(total_load_n=load, reference_to_lift_scatter_n=scatter,
        supported_to_lift_transfer_n=totals['lifted']-totals['supported'],
        mass_kg=load/G if valid_payload else None,
        empirical_mass_band_kg=[(load-scatter)/G, (load+scatter)/G] if valid_payload else None,
        empirical_band_is_accuracy_interval=False,
        assessment=('BOTH_ARMS_LOAD_PLAUSIBLE' if valid_payload and load > scatter and load > 0
                    and all(a['load_n'] > sum(max(abs(a[w]['downward_median_n']-x)
                        for x in a[w]['central_90_percent_n']) for w in ('reference','lifted'))
                        for a in result['arms'].values())
                    else 'INCONCLUSIVE'))
    if load <= 0:
        result['warnings'].append('No positive downward load established; do not use absolute force magnitudes')
    for arm in ARMS:
        result['arms'][arm]['load_fraction'] = result['arms'][arm]['load_n']/load if load > 0 else None
        if result['arms'][arm]['load_n'] <= 0:
            result['warnings'].append(arm+': positive individual load share unresolved; equal sharing is not assumed')
    return result

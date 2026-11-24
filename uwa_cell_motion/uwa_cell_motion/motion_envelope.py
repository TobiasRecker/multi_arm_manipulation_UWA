"""Strict speed bounds at the fixed physical TCPs of a reviewed joint trajectory."""
import hashlib
import json
import math
from collections.abc import Mapping
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

from .common import ROBOT_IDS, joint_names, measured_joint_speed_limit


def _positive(value, maximum):
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError('Invalid physical speed limit')
    return float(value)


def _vector(value, size):
    vector = np.asarray(value, dtype=float)
    if vector.shape != (size,) or not np.isfinite(vector).all():
        raise ValueError('Incomplete or nonfinite motion vector')
    return vector


def _xyz(element, key):
    return _vector([float(v) for v in element.get(key, '0 0 0').split()], 3)


class _Tcp:
    """Factory URDF joint chain and the translational Jacobian at its TCP."""
    def __init__(self, parents, arm, frame, offset):
        chain = []
        names = joint_names(arm)
        link = frame
        found_tool = False
        visited = set()
        while link != 'world':
            if link == arm + '_tool0':
                found_tool = True
            if link not in parents or link in visited:
                raise ValueError('Unknown TCP frame or broken world chain: ' + frame)
            visited.add(link)
            joint = parents[link]
            kind = joint.get('type')
            if kind != 'fixed':
                if not found_tool:
                    raise ValueError('TCP must be rigidly attached to the selected tool0: ' + frame)
                if kind not in ('revolute', 'continuous') or joint.get('name') not in names:
                    raise ValueError('TCP depends on an unsupported or foreign joint: ' + frame)
            origin = joint.find('origin')
            xyz = _xyz(origin, 'xyz') if origin is not None else np.zeros(3)
            rotation = Rotation.from_euler('xyz', _xyz(origin, 'rpy')).as_matrix() if origin is not None else np.eye(3)
            axis_element = joint.find('axis')
            axis = _xyz(axis_element, 'xyz') if axis_element is not None else np.array([1., 0., 0.])
            if kind != 'fixed' and not np.isclose(np.linalg.norm(axis), 1., rtol=0, atol=1e-10):
                raise ValueError('Invalid physical joint axis')
            chain.append((xyz, rotation, None if kind == 'fixed' else joint.get('name'), axis))
            link = joint.find('parent').get('link')
        if not found_tool:
            raise ValueError('TCP must be rigidly attached to the selected tool0: ' + frame)
        self.offset = offset
        self.chain = list(reversed(chain))
        if [name for _, _, name, _ in self.chain if name] != list(names):
            raise ValueError('TCP does not use exactly the six ordered joints of ' + arm)
        distance = float(np.linalg.norm(offset))
        radii = []
        for xyz, _, name, _ in chain:
            if name:
                radii.append(distance)
            distance += float(np.linalg.norm(xyz))
        self.radii = np.array(radii[::-1])

    def speed(self, q, v):
        position = np.zeros(3)
        rotation = np.eye(3)
        axes = []
        origins = []
        for xyz, basis, name, axis in self.chain:
            position = position + rotation @ xyz
            rotation = rotation @ basis
            if name:
                i = len(axes)
                axes.append(rotation @ axis)
                origins.append(position)
                rotation = rotation @ Rotation.from_rotvec(axis * q[i]).as_matrix()
        tcp = position + rotation @ self.offset
        jacobian = np.cross(axes, tcp - origins)
        return float(np.linalg.norm(v @ jacobian))


def _controls(point, next_point, dt):
    q, v, a = point
    stop, end_v, end_a = next_point
    if (v is None) != (end_v is None) or (a is None) != (end_a is None):
        raise ValueError('Mixed derivative fields across a controller interval')
    if v is None:
        return np.stack((q, stop))
    if a is None:
        return np.stack((q, q + dt * v / 3, stop - dt * end_v / 3, stop))
    # Quintic Hermite interpolation by the joint_trajectory_controller, expressed
    # in Bernstein form. Convex hulls of derivative control points enclose the
    # whole interval, including peaks between published samples.
    return np.stack((q, q + dt*v/5, q + 2*dt*v/5 + dt*dt*a/20,
                     stop - 2*dt*end_v/5 + dt*dt*end_a/20, stop - dt*end_v/5, stop))


def _halves(controls):
    row = controls
    left = [row[0]]
    right = [row[-1]]
    while len(row) > 1:
        row = (row[1:] + row[:-1]) * .5
        left.append(row[0])
        right.append(row[-1])
    return np.stack(left), np.stack(right[::-1])


def _point(point):
    if isinstance(point, Mapping):
        stamp = point['time']
        # Use the same nanosecond timestamps ultimately sent to the controller.
        if not math.isfinite(stamp):
            raise ValueError('Nonfinite controller timestamp')
        stamp = round(stamp * 1e9) / 1e9
        get = point.get
    else:
        stamp = point.time_from_start.sec + point.time_from_start.nanosec * 1e-9
        get = lambda name: getattr(point, name, None)
    q = _vector(get('positions'), 6)
    v = get('velocities')
    a = get('accelerations')
    v = _vector(v, 6) if v is not None and len(v) else None
    a = _vector(a, 6) if a is not None and len(a) else None
    if a is not None and v is None:
        raise ValueError('Acceleration without velocity in controller point')
    return stamp, (q, v, a)


class MotionEnvelope:
    def __init__(self, description, tcp_frames, joint_limit_rad_s, tcp_limit_m_s):
        self.joint_limit_rad_s = _positive(joint_limit_rad_s, .3)
        self.tcp_limit_m_s = _positive(tcp_limit_m_s, .25)
        if not tcp_frames or not isinstance(tcp_frames, dict) or set(tcp_frames) - set(ROBOT_IDS):
            raise ValueError('Explicit cell-arm TCP bindings required')
        tree = ET.fromstring(description)
        parents = {j.find('child').get('link'): j for j in tree.findall('joint')}
        self.chains = {}
        frames = {}
        for arm, values in tcp_frames.items():
            if isinstance(values, str):
                values = [dict(frame=values, offset_m=[0., 0., 0.])]
            if not isinstance(values, list) or not 1 <= len(values) <= 8:
                raise ValueError('Explicit physical TCP frames required for ' + arm)
            frames[arm] = []
            self.chains[arm] = []
            for tcp in values:
                frame = tcp['frame']
                if not isinstance(frame, str) or not frame.startswith(arm + '_'):
                    raise ValueError('TCP belongs to another arm')
                offset = _vector(tcp['offset_m'], 3)
                self.chains[arm].append(_Tcp(parents, arm, frame, offset))
                frames[arm].append(dict(frame=frame, offset_m=offset.tolist()))
        self.spec = dict(tcp_frames=frames, joint_limit_rad_s=self.joint_limit_rad_s, tcp_limit_m_s=self.tcp_limit_m_s)
        self.digest = hashlib.sha256(json.dumps(self.spec, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def measured(self, arm, q, v):
        q, v = _vector(q, 6), _vector(v, 6)
        return dict(joint_rad_s=float(max(abs(v))), tcp_m_s=max(t.speed(q, v) for t in self.chains[arm]))

    def check_measured(self, arm, q, v, *, joint_tolerance_ratio=0.):
        observed = self.measured(arm, q, v)
        joint_trip = measured_joint_speed_limit(self.joint_limit_rad_s, joint_tolerance_ratio)
        if observed['joint_rad_s'] > joint_trip or observed['tcp_m_s'] > self.tcp_limit_m_s:
            raise ValueError(f'{arm}: measured speed exceeds reviewed limit: {observed}; '
                             f'joint_trip_rad_s={joint_trip}, tcp_limit_m_s={self.tcp_limit_m_s}')
        return observed

    def _bound(self, arm, origin, controls, dt, depth=0):
        degree = len(controls) - 1
        velocity = degree * np.diff(controls, axis=0) / dt
        vmax = np.max(abs(velocity), axis=0)
        amax = np.max(abs((degree - 1) * np.diff(velocity, axis=0) / dt), axis=0) if degree > 1 else np.zeros(6)
        left, right = _halves(controls)
        qmid = origin + left[-1]
        vmid = 2 * degree * (left[-1] - left[-2]) / dt
        joint_bound = max(vmax) / self.joint_limit_rad_s
        tcp_bound = 0.
        sampled_ratio = max(np.max(abs(velocity[[0,-1]])), np.max(abs(vmid))) / self.joint_limit_rad_s
        for chain in self.chains[arm]:
            # Each link offset is a product of rotations followed by a fixed
            # translation. Differentiating twice gives the triangle bound for
            # TCP acceleration below, valid for all configurations in the span.
            coarse = chain.radii @ vmax
            if coarse <= self.tcp_limit_m_s and joint_bound <= 1:
                tcp_bound = max(tcp_bound, coarse / self.tcp_limit_m_s)
                continue
            amid_bound = chain.radii @ amax + max(chain.radii) * sum(vmax)**2
            midpoint = chain.speed(qmid, vmid)
            tcp_bound = max(tcp_bound, min(coarse, midpoint + .5 * dt * amid_bound) / self.tcp_limit_m_s)
            sampled_ratio = max(sampled_ratio, midpoint / self.tcp_limit_m_s)
        upper = max(joint_bound, tcp_bound)
        if upper <= 1 or depth >= 7 or upper <= max(1., sampled_ratio) * (1 + 1e-7):
            return upper
        return max(self._bound(arm, origin, left, dt / 2, depth + 1),
                   self._bound(arm, origin, right, dt / 2, depth + 1))

    def _trajectory_bound(self, arm, points):
        points = [_point(p) for p in points]
        if len(points) < 2 or points[0][0] != 0:
            raise ValueError('Checked controller trajectory must include an explicit start point at time zero')
        peak = 1.
        min_interval = math.inf
        for (start, a), (end, b) in zip(points, points[1:]):
            duration = end - start
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('Controller times must strictly increase')
            min_interval = min(min_interval, duration)
            # Local coordinates avoid losing derivative accuracy when small
            # intervals are added to a joint position several radians from zero.
            first = (np.zeros(6), a[1], a[2])
            last = (b[0]-a[0], b[1], b[2])
            peak = max(peak, self._bound(arm, a[0], _controls(first, last, duration), duration))
        return float(peak), min_interval

    def time_scale(self, arm, points):
        scale, min_interval = self._trajectory_bound(arm, points)
        if scale > 1:
            # After rescaling, ROS nanosecond conversion can move each end of
            # each interval. Resolve this quantization before final validation.
            scale += 4e-9 / min_interval
        return scale

    def check_trajectory(self, arm, points):
        scale, _ = self._trajectory_bound(arm, points)
        # Roundoff from nanosecond quantization is only relevant to planning;
        # the measured speed check above uses the exact configured limit.
        if scale > 1. + 1e-10:
            raise ValueError(f'{arm}: interpolated joint/TCP trajectory needs time scale {scale:.12g}')
        return True

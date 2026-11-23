"""Workpiece-relative, force-terminated axial motion and its Gazebo tool model."""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

from uwa_cell_description.configuration import joint_names
from uwa_cell_motion.carton_paths import solve_near
from .box_drawing import SURFACES, WORKER


@dataclass(frozen=True)
class ProbeTool:
    length_m: float
    tip_radius_m: float

    def __post_init__(self):
        if not .18 < self.length_m <= .5 or not 0 < self.tip_radius_m < (self.length_m - .18)/2:
            raise ValueError('Unsupported axial tool dimensions')


@dataclass(frozen=True)
class SeekContact:
    skill: str
    arm: str
    tool: ProbeTool
    face: str
    uv_m: tuple
    clearance_m: float
    travel_m: float
    speed_m_s: float
    threshold_n: float

    @classmethod
    def read(cls, path):
        return cls.from_record(json.loads(Path(path).read_text()))

    @classmethod
    def from_record(cls, data):
        return cls(**dict(data, tool=ProbeTool(**data['tool']), uv_m=tuple(data['uv_m'])))

    def __post_init__(self):
        if self.skill != 'seek_contact' or self.arm != WORKER or self.face not in SURFACES:
            raise ValueError('Unsupported skill, worker or surface for this presentation')
        if len(self.uv_m) != 2 or not all(map(math.isfinite, self.uv_m)):
            raise ValueError('Expected finite workpiece UV coordinates')
        if not all(math.isfinite(v) and v > 0 for v in
                   (self.travel_m, self.clearance_m, self.speed_m_s, self.threshold_n)):
            raise ValueError('Search parameters must be positive and finite')
        if self.travel_m - self.clearance_m > .0030000001 or self.speed_m_s > .020:
            raise ValueError('Search exceeds approved 3 mm model depth or 20 mm/s process feed')

    @property
    def sensor_joint(self):
        return self.arm + '_probe_mount'

    def record(self):
        return asdict(self)


def add_probe_physics(description, spec):
    """Physics-only tool. The offline validator checks its shaft and spherical tip."""
    root = ET.fromstring(description)
    link = ET.SubElement(root, 'link', name=spec.arm+'_probe')
    length, radius = spec.tool.length_m, spec.tool.tip_radius_m
    inertial = ET.SubElement(link, 'inertial')
    ET.SubElement(inertial, 'origin', xyz=f'0 0 {(length+.18)/2}')
    ET.SubElement(inertial, 'mass', value='0.025')
    transverse = .025*((length-.18)**2/12 + radius**2/4)
    ET.SubElement(inertial, 'inertia', ixx=str(transverse), iyy=str(transverse),
                  izz=str(.025*radius**2/2), ixy='0', ixz='0', iyz='0')
    for name in ('shaft', 'tip'):
        part = ET.SubElement(link, 'collision', name='probe_'+name)
        center = (length-radius+.18)/2 if name=='shaft' else length-radius
        ET.SubElement(part, 'origin', xyz=f'0 0 {center}')
        geometry = ET.SubElement(part, 'geometry')
        if name=='shaft':
            ET.SubElement(geometry, 'cylinder', radius=str(radius), length=str(length-radius-.18))
        else:
            ET.SubElement(geometry, 'sphere', radius=str(radius))
    joint = ET.SubElement(root, 'joint', name=spec.sensor_joint, type='fixed')
    ET.SubElement(joint, 'parent', link=spec.arm+'_tool0')
    ET.SubElement(joint, 'child', link=link.get('name'))
    ET.SubElement(ET.SubElement(root,'gazebo', reference=spec.sensor_joint),'preserveFixedJoint').text='true'
    return ET.tostring(root,encoding='unicode')


def add_surface_patch(sdf, spec, dims, height):
    """Local physical protrusion on the selected face, independent of the search plan."""
    root = ET.fromstring(sdf)
    link = root.find('model/link')
    axis, sign = SURFACES[spec.face]
    normal = np.eye(3)[axis]*sign
    u = np.array([1., 0., 0.])
    center = dims/2 + normal*(dims[axis]/2+height/2) + u*spec.uv_m[0] + np.cross(normal,u)*spec.uv_m[1]
    size = np.full(3, .024)
    size[axis] = height
    part = ET.SubElement(link, 'collision', name='probe_surface_patch')
    ET.SubElement(part,'pose').text = ' '.join(map(str,[*center,0,0,0]))
    ET.SubElement(ET.SubElement(ET.SubElement(part,'geometry'),'box'),'size').text = ' '.join(map(str,size))
    ET.SubElement(link.find("sensor[@type='contact']/contact"),'collision').text = 'probe_surface_patch'
    return ET.tostring(root,encoding='unicode')


class ProbePath:
    """One checked presentation. Only the working arm advances on the surface normal."""
    def __init__(self, spec, checker, names, holder_to_center, start, limits):
        self.spec, self.checker, self.names, self.limits = spec, checker, names, limits
        self.problem = checker.p
        self.holder = next(iter(checker.holding.offsets))
        self.holder_to_center = holder_to_center
        self.frame = checker.surface_frame(spec.face)
        self.entry = dict(start)
        self.work_joints = joint_names(spec.arm)
        self.hold = self.center(start)
        self.mount = np.eye(4)
        self.mount[2,3] = spec.tool.length_m

    def center(self, state):
        return self.problem.chains[self.holder].forward(state) @ self.holder_to_center

    def tip(self, state):
        return self.problem.chains[self.spec.arm].forward(state) @ self.mount

    def observation(self, state):
        local = np.linalg.solve(self.center(state), self.tip(state))
        height = (local[:3,3]-self.frame.origin_m) @ self.frame.outward
        return dict(tip_in_workpiece=local.tolist(), travel_m=self.spec.clearance_m-float(height))

    def leg(self, name, start, height, *, contact=False, search=False, target_state=None):
        from .contact_drawing import controller_spline
        target = self.hold @ self.frame.tool_pose(self.spec.uv_m, height)
        first = self.tip(start)
        orient = Rotation.from_matrix(target[:3,:3] @ first[:3,:3].T).as_rotvec()
        delta = target[:3,3] - first[:3,3]
        # Start from measured joints at handoff. Retain the approved common
        # holder reference; the transport controller holds its twelve targets.
        states = [dict(start)]
        knots = np.linspace(0.,1.,max(9, math.ceil(np.linalg.norm(delta)/.001)+1))
        for u in knots[1:]:
            tip = first.copy()
            tip[:3,3] += u*delta
            tip[:3,:3] = Rotation.from_rotvec(u*orient).as_matrix() @ first[:3,:3]
            previous = states[-1]
            q = solve_near(self.problem,self.spec.arm,previous,tip @ np.linalg.inv(self.mount),
                           [previous[j] for j in self.work_joints])
            state = dict(self.entry, **dict(zip(self.work_joints,q)))
            states.append(state)
        if target_state is not None:
            if max(abs(states[-1][j]-target_state[j]) for j in self.names) > .002:
                raise ValueError('Retraction does not join the checked return branch')
            states[-1] = dict(target_state)
        rows = [[s[j] for j in self.names] for s in states]
        times, values, spline, scale = controller_spline(rows, knots, self.limits, name)
        # Fixed-orientation straight line. Evaluate actual TCP velocity on the
        # controller quintics so the limiting feed applies to the tool tip.
        checks = np.linspace(0,times[-1],max(3,2*len(times)-1))
        allowance = dict(operation='seek_contact', face=self.spec.face, uv_m=self.spec.uv_m,
                         max_depth_m=max(0., self.spec.travel_m-self.spec.clearance_m)) if contact else None
        peak = 0.
        for t,q,qd in zip(checks,spline(checks),spline(checks,1)):
            state = dict(start, **dict(zip(self.names,q)))
            self.checker.check(self.center(state), state, axial_allowance=allowance)
            if search:
                epsilon = 1.e-5
                later = dict(state, **dict(zip(self.names,q+epsilon*qd)))
                earlier = dict(state, **dict(zip(self.names,q-epsilon*qd)))
                peak = max(peak,np.linalg.norm(self.tip(later)[:3,3]-self.tip(earlier)[:3,3])/(2*epsilon))
        feed_scale = max(1., peak/self.spec.speed_m_s)
        times *= feed_scale
        values[:,1] /= feed_scale
        values[:,2] /= feed_scale**2
        points = [dict(time=float(t),positions=q.tolist(),velocities=v.tolist(),accelerations=a.tolist())
                  for t,(q,v,a) in zip(times,values)]
        return dict(phase=name, joint_names=self.names, points=points, duration_s=float(times[-1]),
                    checked_samples=len(checks),controller_time_factor=scale,
                    search_peak_tcp_m_s=float(peak/feed_scale) if search else None), states[-1]

    def compile(self):
        pre, self.pre = self.leg('probe_preposition',self.entry,self.spec.clearance_m)
        seek, end = self.leg('seek_contact',self.pre,self.spec.clearance_m-self.spec.travel_m,
                             contact=True,search=True)
        # Verify the longest return in the model before any search motion.
        self.leg('probe_return_witness',end,self.spec.clearance_m,contact=True,target_state=self.pre)
        # Reverse the already checked approach back to the connector.
        leave = dict(pre,phase='probe_leave',points=[
            dict(point,time=pre['duration_s']-point['time'],velocities=[-v for v in point['velocities']])
            for point in reversed(pre['points'])])
        return [pre, seek, leave]

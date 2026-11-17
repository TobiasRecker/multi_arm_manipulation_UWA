"""Transport-free common object reference for hardware commissioning.

This core never connects to ROS/devices. Its output is NOT an executable robot
plan. A real port must validate IK, complete collision/stopping envelopes,
registration, grip evidence and command delivery before using these references.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy.spatial.transform import Rotation
from match_cooperative_handling.rigid_object import rigid, relative, tcp_target, interpolate, pose_error

MEMBERS = ('right_front', 'right_rear')


@dataclass(frozen=True)
class MemberObservation:
    device_stamp: float
    received_monotonic: float
    world_tcp: object
    speed_scaling: float
    target_speed_fraction: float
    grip_retained: bool
    stop_latched: bool = False


class SharedObjectReference:
    """One object path/clock, fixed offsets; faults latch the whole membership.

    Native scaling slows the SAME object clock using the most restrictive
    member. No arm has an independent trajectory or progress parameter.
    Output zeros on failure are a stop REQUEST, never measured standstill.
    """
    def __init__(self, start, end, measured_tcps, *, linear_speed=.0005,
                 angular_speed=.01, tcp_speed=.0005, linear_acceleration=.0001,
                 angular_acceleration=.01, state_timeout=.2, tick_timeout=.05,
                 position_tolerance=.001, angle_tolerance=.01):
        if set(measured_tcps) != set(MEMBERS):
            raise ValueError('Exactly the two right holding members required')
        limits=(linear_speed,angular_speed,tcp_speed,linear_acceleration,angular_acceleration,
                state_timeout,tick_timeout,position_tolerance,angle_tolerance)
        if any(isinstance(x,bool) or not math.isfinite(x) or x <= 0 for x in limits):
            raise ValueError('Positive finite reference bounds required')
        self.start,self.end=rigid(start),rigid(end)
        self.start.setflags(write=False);self.end.setflags(write=False)
        self._offsets={a:relative(start,measured_tcps[a]) for a in MEMBERS}
        for matrix in self._offsets.values():matrix.setflags(write=False)
        self.distance,self.angle=pose_error(start,end)
        self.rotation=Rotation.from_matrix(self.end[:3,:3]@self.start[:3,:3].T).as_rotvec()
        radius=max(np.linalg.norm(t[:3,3]) for t in self._offsets.values())
        # Conservative norm bounds over the complete common quintic law.
        self.duration=max(1.,1.875*self.distance/linear_speed,1.875*self.angle/angular_speed,
            1.875*(self.distance+radius*self.angle)/tcp_speed,
            math.sqrt((5.774*(self.distance+radius*self.angle)+radius*(1.875*self.angle)**2)/linear_acceleration),
            math.sqrt(5.774*self.angle/angular_acceleration))
        self.linear_acceleration,self.angular_acceleration=linear_acceleration,angular_acceleration
        self.state_timeout,self.tick_timeout=state_timeout,tick_timeout
        self.position_tolerance,self.angle_tolerance=position_tolerance,angle_tolerance
        self.tau=0.;self.last_now=None;self.stopped=None;self.last_twist=np.zeros(6)
        self.last_tcp_twists={a:np.zeros(6) for a in MEMBERS}
        self.stamps={};self.advanced={}

    @property
    def offsets(self):return {a:t.copy() for a,t in self._offsets.items()}

    def sample(self, tau, factor=1.):
        u=float(np.clip(tau/self.duration,0.,1.))
        progress=10*u**3-15*u**4+6*u**5
        rate=(30*u**2-60*u**3+30*u**4)/self.duration*factor
        pose=interpolate(self.start,self.end,progress)
        twist=np.r_[(self.end[:3,3]-self.start[:3,3])*rate,self.rotation*rate]
        return pose,twist

    def stop(self, reason):
        if self.stopped is None:self.stopped=str(reason)

    def _packet(self, factor=0.):
        pose,twist=self.sample(self.tau,factor if self.stopped is None else 0.)
        targets={a:tcp_target(pose,self._offsets[a],twist) for a in MEMBERS}
        return dict(object_time_s=self.tau,object_pose=pose,object_twist=twist,
            tcp_targets={a:v[0] for a,v in targets.items()},tcp_twists={a:v[1] for a,v in targets.items()},
            common_speed_factor=factor if self.stopped is None else 0.,
            stop_requested_for=MEMBERS if self.stopped is not None else (),reason=self.stopped,
            complete=self.stopped is None and self.tau>=self.duration,
            executable=False,standstill_confirmed=False)

    def step(self, now, members, measured_object, object_source_monotonic):
        if self.stopped is not None:return self._packet()
        try:
            if not math.isfinite(now) or self.last_now is not None and not 0 < now-self.last_now <= self.tick_timeout:
                raise ValueError('Common monotonic control clock stale/reversed')
            if set(members)!=set(MEMBERS):raise ValueError('Holding membership incomplete')
            if not math.isfinite(object_source_monotonic) or not 0<=now-object_source_monotonic<=self.state_timeout:
                raise ValueError('Object observation stale/future')
            measured_object=rigid(measured_object);factors=[]
            expected_object,_=self.sample(self.tau)
            if any(e>bound for e,bound in zip(pose_error(measured_object,expected_object),
                    (self.position_tolerance,self.angle_tolerance))):
                raise ValueError('Measured object left the reference corridor')
            for arm in MEMBERS:
                value=members[arm]
                if not all(math.isfinite(v) for v in (value.device_stamp,value.received_monotonic,
                        value.speed_scaling,value.target_speed_fraction)):
                    raise ValueError(arm+': invalid native state')
                if value.device_stamp<0:raise ValueError(arm+': invalid native timestamp')
                if not 0<=now-value.received_monotonic<=self.state_timeout:
                    raise ValueError(arm+': stale/future state')
                if arm in self.stamps and value.device_stamp<self.stamps[arm]:
                    raise ValueError(arm+': native clock reversed')
                if arm not in self.stamps or value.device_stamp>self.stamps[arm]:
                    self.advanced[arm]=now;self.stamps[arm]=value.device_stamp
                if now-self.advanced[arm]>self.state_timeout:raise ValueError(arm+': native source frozen')
                if value.grip_retained is not True or value.stop_latched is not False:
                    raise ValueError(arm+': grip/member stop')
                if not (0<value.speed_scaling<=1 and 0<value.target_speed_fraction<=1):
                    raise ValueError(arm+': native scaling paused/invalid')
                factors.append(value.speed_scaling*value.target_speed_fraction)
                expected=measured_object@self._offsets[arm]
                if any(e>bound for e,bound in zip(pose_error(value.world_tcp,expected),
                        (self.position_tolerance,self.angle_tolerance))):
                    raise ValueError(arm+': frozen grasp transform violated')
            factor=min(factors);dt=0. if self.last_now is None else now-self.last_now
            next_tau=min(self.duration,self.tau+dt*factor)
            next_object,twist=self.sample(next_tau,factor)
            tcp_twists={a:tcp_target(next_object,self._offsets[a],twist)[1] for a in MEMBERS}
            if dt and any(np.linalg.norm(v[:3]-previous[:3])/dt>self.linear_acceleration*1.001 or
                          np.linalg.norm(v[3:]-previous[3:])/dt>self.angular_acceleration*1.001
                          for v,previous in [(twist,self.last_twist)]+
                              [(tcp_twists[a],self.last_tcp_twists[a]) for a in MEMBERS]):
                raise ValueError('Shared scaling discontinuity exceeds reference acceleration; no member clipping')
            self.tau=next_tau;self.last_now=now;self.last_twist=twist;self.last_tcp_twists=tcp_twists
            return self._packet(factor)
        except (ValueError,TypeError,AttributeError,KeyError,np.linalg.LinAlgError) as error:
            self.stop(error);return self._packet()

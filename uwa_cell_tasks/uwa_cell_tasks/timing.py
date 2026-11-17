"""Uniform retiming using exact extrema of the controller's quintic segments."""
from copy import deepcopy
import numpy as np
from scipy.interpolate import BPoly, PPoly


def interpolation_peaks(trajectory, derivative):
    """Position/velocity/acceleration points select quintic interpolation in JTC."""
    points=trajectory['points']
    times=np.array([p['time'] for p in points])
    if len(times)<2 or np.any(np.diff(times)<=0):
        raise ValueError('Strictly increasing trajectory times required')
    peak=np.zeros(len(points[0]['positions']))
    # Bound native interpolation construction so the ROS executor can service
    # its heartbeat while long recipes are checked. Each segment is independent;
    # one shared endpoint keeps the exact controller polynomial unchanged.
    for start in range(0,len(points)-1,128):
        batch=points[start:start+129]
        batch_times=times[start:start+len(batch)]
        values=[[p['positions'],p['velocities'],p['accelerations']] for p in batch]
        polynomial=PPoly.from_bernstein_basis(BPoly.from_derivatives(batch_times,values)).derivative(derivative)
        for i,width in enumerate(np.diff(batch_times)):
            for joint in range(len(points[0]['positions'])):
                coefficients=polynomial.c[:,i,joint]
                roots=np.roots(np.polyder(coefficients))
                candidates=[0.,width]+[float(r.real) for r in roots if abs(r.imag)<1e-9 and 0<r.real<width]
                peak[joint]=max(peak[joint],float(np.max(np.abs(np.polyval(coefficients,candidates)))))
    return peak


def interpolation_peak(trajectory,derivative):
    return float(np.max(interpolation_peaks(trajectory,derivative)))


def limit_shared_jerk(trajectory, limit):
    """Scale every joint by the SAME time factor; geometry and grasp stay fixed."""
    if not np.isfinite(limit) or limit<=0:raise ValueError('Positive finite jerk limit required')
    result=deepcopy(trajectory)
    peak=interpolation_peak(result,3)
    factor=max(1.,(peak/limit)**(1/3)*(1.000001 if peak>limit else 1.))
    for point in result['points']:
        point['time']*=factor
        point['velocities']=(np.asarray(point['velocities'])/factor).tolist()
        point['accelerations']=(np.asarray(point['accelerations'])/factor**2).tolist()
    result['duration_s']*=factor
    result['jerk_retiming']=dict(limit_rad_s3=limit,shared_time_factor=factor,
        controller_interpolation_peak_rad_s3=interpolation_peak(result,3),
        interpretation='Planned quintic command jerk; not measured actuator jerk or stop qualification')
    return result


def object_law_duration(spline, velocity_limit, acceleration_limit):
    """Conservative local bounds for q(s(u)), s(u)=10u³-15u⁴+6u⁵.

    Unlike multiplying unrelated global maxima, each spline interval is paired
    with its own quintic time interval. All joints still share one duration.
    """
    from scipy.optimize import brentq
    def progress(u):return 10*u**3-15*u**4+6*u**5
    times=np.array([0. if x==0 else 1. if x==1 else brentq(lambda u:progress(u)-x,0,1,xtol=1e-14) for x in spline.x])
    speed_bound=0.;acceleration_bound=0.
    for i,(lo,hi) in enumerate(zip(times[:-1],times[1:])):
        width=spline.x[i+1]-spline.x[i];c3,c2,c1,_=spline.c[:,i]
        grad=np.maximum(abs(c1),abs(3*c3*width**2+2*c2*width+c1))
        root=np.divide(-c2,3*c3,out=np.zeros_like(c2),where=c3!=0)
        valid=(c3!=0)&(root>0)&(root<width)
        grad=np.maximum(grad,np.where(valid,abs(3*c3*root**2+2*c2*root+c1),0.))
        curvature=np.maximum(abs(2*c2),abs(6*c3*width+2*c2))
        candidates=[lo,hi]+[u for u in (.5,) if lo<u<hi]
        ds=max(abs(30*u*u*(1-u)**2) for u in candidates)
        candidates=[lo,hi]+[u for u in ((3-np.sqrt(3))/6,(3+np.sqrt(3))/6) if lo<u<hi]
        dds=max(abs(60*u-180*u*u+120*u**3) for u in candidates)
        speed_bound=max(speed_bound,float(np.max(grad))*ds)
        acceleration_bound=max(acceleration_bound,float(np.max(curvature))*ds**2+float(np.max(grad))*dds)
    return max(speed_bound/velocity_limit,np.sqrt(acceleration_bound/acceleration_limit))


def scale_object_time(trajectory,cfg):
    """Compress the complete object's time law; never retime members separately."""
    from .core import seal,verify,digest
    from .operating import velocity_limits
    verify(trajectory)
    factor=cfg.get('carrying_speed_multiplier',1.)
    if not np.isfinite(factor) or not 1<=factor<=5:raise ValueError('Invalid carrying speed multiplier')
    velocity_peaks=interpolation_peaks(trajectory,1)*factor
    acceleration_peak=interpolation_peak(trajectory,2)*factor**2
    if np.any(velocity_peaks>velocity_limits(trajectory['joint_names'],cfg)+1e-8):
        raise ValueError('Time-scaled controller exceeds bound per-joint velocity')
    if acceleration_peak>cfg['joint_acceleration_rad_s2']+1e-8:
        raise ValueError('Time-scaled controller exceeds acceleration envelope')
    result=deepcopy(trajectory)
    for p in result['points']:
        p['time']/=factor
        p['velocities']=(np.asarray(p['velocities'])*factor).tolist()
        p['accelerations']=(np.asarray(p['accelerations'])*factor**2).tolist()
        if np.any(abs(np.asarray(p['velocities']))>velocity_limits(result['joint_names'],cfg)+1e-8):
            raise ValueError('Time-scaled motion exceeds bound per-joint velocity')
        if np.max(abs(np.asarray(p['accelerations'])))>cfg['joint_acceleration_rad_s2']+1e-8:
            raise ValueError('Time-scaled motion exceeds acceleration envelope')
    result['duration_s']/=factor
    if 'jerk_retiming' in result:
        result['jerk_retiming']['controller_interpolation_peak_rad_s3']*=factor**3
        if result['jerk_retiming']['controller_interpolation_peak_rad_s3']>cfg['joint_jerk_rad_s3']*(1+1e-5):
            raise ValueError('Time-scaled motion exceeds jerk envelope')
    result['time_scaling']=dict(multiplier=factor,controller_velocity_peaks_rad_s=velocity_peaks.tolist(),
        controller_acceleration_peak_rad_s2=float(acceleration_peak),source_trajectory_sha256=trajectory['sha256'],
        position_path_sha256=digest(dict(joint_names=trajectory['joint_names'],
            points=[dict(positions=p['positions'],object_pose=p.get('object_pose')) for p in trajectory['points']])),
        statement='Identical positions and object poses, t/f, v*f, a*f^2, jerk*f^3')
    return seal(result)

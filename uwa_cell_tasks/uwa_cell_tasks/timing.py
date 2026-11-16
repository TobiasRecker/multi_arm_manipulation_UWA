"""Uniform retiming using exact extrema of the controller's quintic segments."""
from copy import deepcopy
import numpy as np
from scipy.interpolate import BPoly, PPoly


def interpolation_peak(trajectory, derivative):
    """Position/velocity/acceleration points select quintic interpolation in JTC."""
    points=trajectory['points']
    times=np.array([p['time'] for p in points])
    if len(times)<2 or np.any(np.diff(times)<=0):
        raise ValueError('Strictly increasing trajectory times required')
    values=[[p['positions'],p['velocities'],p['accelerations']] for p in points]
    polynomial=PPoly.from_bernstein_basis(BPoly.from_derivatives(times,values)).derivative(derivative)
    peak=0.
    for i,width in enumerate(np.diff(times)):
        for joint in range(len(points[0]['positions'])):
            coefficients=polynomial.c[:,i,joint]
            roots=np.roots(np.polyder(coefficients))
            candidates=[0.,width]+[float(r.real) for r in roots if abs(r.imag)<1e-9 and 0<r.real<width]
            peak=max(peak,float(np.max(np.abs(np.polyval(coefficients,candidates)))))
    return peak


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

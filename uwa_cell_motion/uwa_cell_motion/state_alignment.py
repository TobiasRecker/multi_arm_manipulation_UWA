"""Compare independent joint data at the same host-monotonic source time."""
import numpy as np


def aligned_driver(history,target,speed_bounds,max_gap):
    rows=list(history);times=np.asarray([r[0] for r in rows],float)
    if len(rows)<2 or not np.isfinite(target) or np.any(np.diff(times)<=0):
        raise ValueError('Driver time history unavailable/nonmonotonic')
    right=int(np.searchsorted(times,target,side='left'))
    if right==len(times) or (right==0 and target<times[0]):
        raise ValueError('Native source time is not bracketed by driver history')
    if times[right]==target:
        q=np.asarray(rows[right][1],float);uncertainty=np.zeros_like(q);left=right
    else:
        left=right-1;gap=times[right]-times[left]
        if gap>max_gap:raise ValueError('Driver alignment sampling gap too large')
        u=(target-times[left])/gap
        q=(1-u)*np.asarray(rows[left][1],float)+u*np.asarray(rows[right][1],float)
        # Lipschitz bound on deviation from linear interpolation. Include it
        # in the existing spatial tolerance; never enlarge that tolerance.
        uncertainty=2*u*(1-u)*gap*np.asarray(speed_bounds,float)
    if not np.isfinite(q).all() or not np.isfinite(uncertainty).all():raise ValueError('Nonfinite aligned driver state')
    return dict(q=q.tolist(),uncertainty_rad=uncertainty.tolist(),
        source_monotonic_s=float(target),driver_bracket_monotonic_s=[float(times[left]),float(times[right])])

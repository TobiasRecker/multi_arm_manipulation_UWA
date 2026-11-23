"""Body-specific stopping bounds with explicit enforced joint-speed contracts.

No measured velocity or instantaneous Jacobian is treated as a future bound.
All sphere pairs are checked. The critical clearance and the shortest time
reserve can belong to different pairs. Physical stop parameters remain inputs.
"""
import numpy as np
from .common import SPEED_TOLERANCE,BODY_RESERVE_MODEL
from .interlock import SUPERVISOR_PERIOD_S


def body_budgets(motion_radii,velocities,caps,age,cfg):
    r=np.asarray(motion_radii,float);v=np.asarray(velocities,float);caps=np.asarray(caps,float)
    if (r.ndim!=2 or v.ndim!=1 or caps.shape!=v.shape or r.shape[1]!=len(v)
            or not np.isfinite(r).all() or np.any(r<0) or not np.isfinite(v).all()
            or not np.isfinite(caps).all() or np.any(caps<0) or not np.isfinite(age) or age<0):
        raise ValueError('Malformed body reserve inputs')
    # Include the monitor's accepted speed tolerance in future stopping bounds.
    speed_bound=np.maximum(abs(v),SPEED_TOLERANCE*caps)
    speeds=r@speed_bound
    if cfg.get('stopping_reserve_policy','enforce')=='geometric_only':
        components = {name: np.zeros_like(speeds) for name in
                      ('total_m', 'data_age_m', 'sampling_m', 'reaction_m', 'braking_m')}
        return dict(speed_m_s=speeds, **components)
    parts=dict(data_age_m=speeds*age,sampling_m=speeds/cfg['rate_hz'],
        reaction_m=speeds*cfg['stop_latency_s'],
        braking_m=r@(speed_bound**2/(2*cfg['braking_acceleration_rad_s2'])))
    return dict(speed_m_s=speeds,total_m=sum(parts.values()),**parts)


def sphere_distances(left, right, left_radii, right_radii, margin=None):
    """Surface gaps, closest pair, and first pair with least margin-adjusted gap."""
    delta = np.asarray(left)[:, None, :] - np.asarray(right)[None, :, :]
    gaps = np.linalg.norm(delta, axis=2) - np.asarray(left_radii)[:, None] - np.asarray(right_radii)[None, :]
    if not np.isfinite(gaps).all():
        raise ValueError('Nonfinite sphere clearance')
    closest = np.unravel_index(np.argmin(gaps), gaps.shape)
    # Subtracting the common margin can round distinct gaps to the same slack.
    # Preserve the diagnostic witness selected by the full matrix evaluation.
    critical = None if margin is None else np.unravel_index(np.argmin(gaps - margin), gaps.shape)
    return gaps, closest, critical


class GeometricPairQuery:
    """Exact minima for fixed sphere radii and successive read-only world poses."""

    def __init__(self):
        self.reference = None
        self.last = None

    def minimum(self, left, right, left_radii, right_radii, margin):
        if self.last is not None:
            old_left, old_right, old_margin, minimum = self.last
            if left is old_left and right is old_right and margin == old_margin:
                return minimum
        minimum = self._candidate_minimum(left, right, left_radii, right_radii, margin)
        if minimum is None:
            gaps, closest, critical = sphere_distances(left, right, left_radii, right_radii, margin)
            minimum = gaps[closest], critical, gaps[critical]
            self.reference = None
            # Only the cost of the next fine query depends on this count.
            count = 32
            if gaps.size > count and all(x.dtype == np.float64 for x in (left, right, left_radii, right_radii)):
                ranked = np.argpartition(gaps.ravel(), count)
                # Preserve full-matrix row-major tie breaking among candidates.
                indices = np.unravel_index(np.sort(ranked[:count]), gaps.shape)
                first_omitted = gaps.flat[ranked[count]]
                scale = max(1., np.max(abs(left)), np.max(abs(right)),
                            np.max(abs(left_radii)), np.max(abs(right_radii)))
                self.reference = left, right, indices, first_omitted, scale
        self.last = left, right, margin, minimum
        return minimum

    def _candidate_minimum(self, left, right, left_radii, right_radii, margin):
        if self.reference is None:
            return None
        old_left, old_right, (rows, cols), first_omitted, scale = self.reference
        if left.dtype != old_left.dtype or right.dtype != old_right.dtype:
            return None
        # In 3D, 2*max(abs(delta_xyz)) bounds every centre's Euclidean shift.
        # Triangle inequality bounds the decrease of every omitted surface gap.
        left_shift = 0. if left is old_left else np.max(abs(left - old_left))
        right_shift = 0. if right is old_right else np.max(abs(right - old_right))
        travel = 2. * (left_shift + right_shift)
        scale += travel
        # Keep square/sum in the full float64 norm away from overflow. At this
        # scale 64 eps covers roundoff of both 3D norms, subtractions of radii,
        # displacement and the lower bound, including subnormal coordinates.
        if not scale < 1e150:
            return None
        lower = first_omitted - travel - 64. * np.finfo(float).eps * scale
        delta = left[rows] - right[cols]
        gaps = np.linalg.norm(delta, axis=1) - left_radii[rows] - right_radii[cols]
        closest_gap = np.min(gaps)
        slack = gaps - margin
        k = np.argmin(slack)
        # The subtraction can round distinct gaps to equal slack. Exclude ties
        # for BOTH objectives before accepting the row-major candidate witness.
        if lower > closest_gap and lower - margin > slack[k]:
            return closest_gap, (rows[k], cols[k]), gaps[k]
        return None


def critical_pair(a,b,centres,radii,links,budgets,cfg,distances=None,geometric_minimum=None):
    """Return the sphere pair with least clearance after both stop bounds."""
    ca,cb=np.asarray(centres[a]),np.asarray(centres[b])
    ba,bb=budgets[a],budgets[b]
    policy=cfg.get('stopping_reserve_policy','enforce')
    margin=cfg['model_margin_m']
    geometric = policy=='geometric_only' and not np.any(ba['total_m']) and not np.any(bb['total_m'])
    if geometric_minimum is None or not geometric:
        if distances is None:
            distances=sphere_distances(ca,cb,radii[a],radii[b],margin if policy=='geometric_only' else None)
        gaps,closest,critical=distances
        closest_gap=gaps[closest]
    if geometric:
        # Every sphere has the same threshold. Time and velocity may change
        # while these poses stay fixed; only the geometry is reusable.
        if geometric_minimum is None:
            i,j=critical
            gap=gaps[i,j]
        else:
            closest_gap,(i,j),gap=geometric_minimum
        threshold=margin
        remaining=gap-threshold
        if not np.isfinite(remaining):raise ValueError('Nonfinite pair reserve')
        lease=0. if remaining<=0 else cfg['heartbeat_timeout_s']
    else:
        thresholds=margin+ba['total_m'][:,None]+bb['total_m'][None,:]
        slack=gaps-thresholds
        if not np.isfinite(slack).all():raise ValueError('Nonfinite pair reserve')
        i,j=np.unravel_index(np.argmin(slack),slack.shape)
        gap=gaps[i,j]
        remaining,threshold=slack[i,j],thresholds[i,j]
        lease=0. if remaining<=0 else cfg['heartbeat_timeout_s']
        if lease>0 and policy!='geometric_only':
            # The shortest lease can belong to a faster, farther body pair.
            speeds=ba['speed_m_s'][:,None]+bb['speed_m_s'][None,:]
            extra=np.full(slack.shape,np.inf)
            np.divide(slack,speeds,out=extra,where=speeds>0)
            lease=min(lease,max(0.,1/cfg['rate_hz']-SUPERVISOR_PERIOD_S+float(np.min(extra))))
    direction=cb[j]-ca[i];length=np.linalg.norm(direction)
    direction=direction/length if length>1e-12 else np.array([1.,0.,0.])
    components={key:float(ba[key][i]+bb[key][j]) for key in
        ('data_age_m','sampling_m','reaction_m','braking_m')}
    return dict(arms=[a,b],clearance_m=float(gap),threshold_m=float(threshold),
        geometric_min_clearance_m=float(closest_gap),remaining_clearance_m=float(remaining),
        relative_speed_bound_m_s=float(ba['speed_m_s'][i]+bb['speed_m_s'][j]),maximum_evaluation_age_s=float(lease),
        reserve_model=BODY_RESERVE_MODEL,reserve_policy=policy,speed_tolerance_factor=SPEED_TOLERANCE,
        reserve_components_m=dict(model_m=cfg['model_margin_m'],**components),
        sphere_indices=[int(i),int(j)],links=[links[a][i],links[b][j]],
        surface_points=[(ca[i]+direction*radii[a][i]).tolist(),(cb[j]-direction*radii[b][j]).tolist()],
        centres=[ca[i].tolist(),cb[j].tolist()])

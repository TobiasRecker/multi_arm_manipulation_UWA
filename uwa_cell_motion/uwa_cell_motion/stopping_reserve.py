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
    parts=dict(data_age_m=speeds*age,sampling_m=speeds/cfg['rate_hz'],
        reaction_m=speeds*cfg['stop_latency_s'],
        braking_m=r@(speed_bound**2/(2*cfg['braking_acceleration_rad_s2'])))
    if cfg.get('stopping_reserve_policy','enforce')=='geometric_only':
        # Explicit operator choice: geometric model margin only. Keep speed
        # monitoring, geometry and independent state/heartbeat checks intact.
        parts={name:np.zeros_like(value) for name,value in parts.items()}
    return dict(speed_m_s=speeds,total_m=sum(parts.values()),**parts)


def critical_pair(a,b,centres,radii,links,budgets,cfg):
    """Return the sphere pair with least clearance after both stop bounds."""
    ca,cb=np.asarray(centres[a]),np.asarray(centres[b])
    distances=np.linalg.norm(ca[:,None,:]-cb[None,:,:],axis=2)
    gaps=distances-np.asarray(radii[a])[:,None]-np.asarray(radii[b])[None,:]
    ba,bb=budgets[a],budgets[b]
    thresholds=cfg['model_margin_m']+ba['total_m'][:,None]+bb['total_m'][None,:]
    slack=gaps-thresholds
    if not np.isfinite(slack).all():raise ValueError('Nonfinite pair reserve')
    i,j=np.unravel_index(np.argmin(slack),slack.shape)
    speeds=ba['speed_m_s'][:,None]+bb['speed_m_s'][None,:]
    # A farther but faster-approaching body pair can exhaust its reserve first.
    extra=np.full(slack.shape,np.inf)
    np.divide(slack,speeds,out=extra,where=speeds>0)
    lease=0. if np.any(slack<=0) else min(cfg['heartbeat_timeout_s'],max(0.,
        1/cfg['rate_hz']-SUPERVISOR_PERIOD_S+float(np.min(extra))))
    policy=cfg.get('stopping_reserve_policy','enforce')
    if policy=='geometric_only':lease=0. if np.any(slack<=0) else cfg['heartbeat_timeout_s']
    direction=cb[j]-ca[i];length=np.linalg.norm(direction)
    direction=direction/length if length>1e-12 else np.array([1.,0.,0.])
    components={key:float(ba[key][i]+bb[key][j]) for key in
        ('data_age_m','sampling_m','reaction_m','braking_m')}
    return dict(arms=[a,b],clearance_m=float(gaps[i,j]),threshold_m=float(thresholds[i,j]),
        geometric_min_clearance_m=float(np.min(gaps)),remaining_clearance_m=float(slack[i,j]),
        relative_speed_bound_m_s=float(speeds[i,j]),maximum_evaluation_age_s=float(lease),
        reserve_model=BODY_RESERVE_MODEL,reserve_policy=policy,speed_tolerance_factor=SPEED_TOLERANCE,
        reserve_components_m=dict(model_m=cfg['model_margin_m'],**components),
        sphere_indices=[int(i),int(j)],links=[links[a][i],links[b][j]],
        surface_points=[(ca[i]+direction*radii[a][i]).tolist(),(cb[j]-direction*radii[b][j]).tolist()],
        centres=[ca[i].tolist(),cb[j].tolist()])

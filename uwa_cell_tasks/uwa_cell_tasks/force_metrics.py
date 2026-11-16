"""Force observation arithmetic, with explicit Gazebo contact attribution limits.

GazeboSim10 duplicates contact rows per collision component, reversing collision
IDs without reversing the original raw force. Never label body_1_wrench as the
force on contact.collision1. Invariants (magnitudes) remain usable. Directional
forces require trusted engine shape IDs, a known analytic reference surface or
a transmitted joint wrench with its declared frame.
"""
import numpy as np


def contact_loads(contacts):
    """Select one complete collision-component manifold per unordered pair.

    Missing/malformed force data is an error, not an observed zero load.
    Distinct collision pairs remain distinct even at a shared position.
    Do not deduplicate by rounded point positions: Gazebo may cache each
    component's geometry independently within1um, duplicating a whole manifold.
    """
    unique={};duplicates=0
    for contact in sorted(contacts,key=lambda c:(c['collision1'],c['collision2'])):
        pair=tuple(sorted((contact['collision1'],contact['collision2'])))
        points=[]
        for point in contact['points']:
            if not point.get('wrench_present'):raise ValueError('Contact wrench missing')
            pos=np.asarray(point['position_world'],float);n=np.asarray(point['normal_world'],float)
            f=np.asarray(point['body1']['force'],float);other=np.asarray(point['body2']['force'],float)
            if any(v.shape!=(3,) or not np.isfinite(v).all() for v in (pos,n,f,other)) or np.linalg.norm(n)<.99:
                raise ValueError('Malformed contact force/normal/position')
            if not np.allclose(f,-other,atol=1e-6,rtol=1e-6):raise ValueError('Raw paired wrenches inconsistent')
            n=n/np.linalg.norm(n);normal=abs(float(f@n));tangent=float(np.linalg.norm(f-(f@n)*n))
            data=dict(pair=pair,position_world=pos.tolist(),raw_force_world_unassigned=f.tolist(),
                normal_load_n=normal,tangential_load_n=tangent,force_norm_n=float(np.linalg.norm(f)))
            points.append(data)
        if pair in unique:
            for field in ('normal_load_n','tangential_load_n'):
                if not np.isclose(sum(p[field] for p in unique[pair]),sum(p[field] for p in points),rtol=1e-5,atol=1e-5):
                    raise ValueError('Duplicate contact carries inconsistent load')
            duplicates+=len(points)
        else:unique[pair]=points
    points=[p for manifold in unique.values() for p in manifold]
    return dict(points=points,unique_points=len(points),duplicate_points_removed=duplicates,
        normal_load_n=sum(p['normal_load_n'] for p in points),
        tangential_load_n=sum(p['tangential_load_n'] for p in points),
        raw_body_attribution_trusted=False,
        interpretation='Unsigned loads; raw force direction is not assigned to reported collision1.')


def analytic_upper_plane_force(points):
    """Reference test only: upper body above a known horizontal support plane.

    The normal must point up on that body. This geometry-based orientation is
    never a generic correction of the Gazebo body attribution problem.
    """
    forces=[]
    for p in points:
        f=np.array(p['raw_force_world_unassigned'],float)
        if abs(f[2])<1e-12 and np.linalg.norm(f)>1e-9:raise ValueError('No identifiable support normal')
        forces.append(f if f[2]>=0 else -f)
    return np.sum(forces,axis=0) if forces else np.zeros(3)


def pad_load_window(observation,reference_n):
    """Aggregate all carton contacts on each jaw before comparing a reference.

    Sum-of-pair peaks is a conservative upper bound, not an observed coincident
    peak. Neither rigid solver peaks nor a reported load reference prove damage.
    """
    if not np.isfinite(reference_n) or reference_n<=0:raise ValueError('Positive pad reference required')
    if observation.get('schema_version')!=1:raise ValueError('Unsupported force observation')
    pads={}
    for arm in ('right_front','right_rear'):
        for side in ('left','right'):
            token=arm+'_robotiq_85_'+side+'_finger_tip_pad'
            pairs=[p for p in observation['contact_loads'] if any(token in c for c in p['collisions'])]
            normal=sum(p['mean_normal_load_n'] for p in pairs)
            tangent=sum(p['mean_tangential_load_n'] for p in pairs)
            peak_normal=sum(p['peak_normal_load_n'] for p in pairs)
            peak_tangent=sum(p['peak_tangential_load_n'] for p in pairs)
            values=np.array([normal,tangent,peak_normal,peak_tangent])
            if not np.isfinite(values).all() or (values<0).any():raise ValueError('Invalid pad load')
            mean_upper=float(np.hypot(normal,tangent));peak_upper=float(np.hypot(peak_normal,peak_tangent))
            pads[arm+'/'+side]=dict(contact_pairs=len(pairs),mean_normal_n=normal,
                mean_load_upper_bound_n=mean_upper,peak_load_upper_bound_n=peak_upper,
                mean_reference_ratio=mean_upper/reference_n,peak_reference_ratio_upper_bound=peak_upper/reference_n)
    usable=observation['missing_wrenches']==0 and observation['invalid_wrenches']==0
    return dict(usable=usable,pads=pads,reference_n=reference_n,reference_scope='One jaw/wall contact patch',
        damage_assessed=False,interpretation='Contact-mean load and noncoincident peak upper bounds; no cardboard failure model.')

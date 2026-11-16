"""Force observation arithmetic, with explicit Gazebo contact attribution limits.

GazeboSim10 duplicates contact rows per collision component, reversing collision
IDs without reversing the original raw force. Never label body_1_wrench as the
force on contact.collision1. Invariants (magnitudes) remain usable. Directional
forces require trusted engine shape IDs, a known analytic reference surface or
a transmitted joint wrench with its declared frame.
"""
import numpy as np


def contact_loads(contacts,position_digits=8):
    """Deduplicate points; retain unsigned normal/tangential loads per pair.

    Missing/malformed force data is an error, not an observed zero load.
    Distinct collision pairs remain distinct even at a shared position.
    """
    unique={};duplicates=0
    for contact in contacts:
        pair=tuple(sorted((contact['collision1'],contact['collision2'])))
        for point in contact['points']:
            if not point.get('wrench_present'):raise ValueError('Contact wrench missing')
            pos=np.asarray(point['position_world'],float);n=np.asarray(point['normal_world'],float)
            f=np.asarray(point['body1']['force'],float);other=np.asarray(point['body2']['force'],float)
            if any(v.shape!=(3,) or not np.isfinite(v).all() for v in (pos,n,f,other)) or np.linalg.norm(n)<.99:
                raise ValueError('Malformed contact force/normal/position')
            if not np.allclose(f,-other,atol=1e-6,rtol=1e-6):raise ValueError('Raw paired wrenches inconsistent')
            n=n/np.linalg.norm(n);normal=abs(float(f@n));tangent=float(np.linalg.norm(f-(f@n)*n))
            axis=next((x for x in n if abs(x)>1e-9),1.);canonical_n=n*np.sign(axis)
            key=pair+tuple(np.round(pos,position_digits))+tuple(np.round(canonical_n,position_digits))
            data=dict(pair=pair,position_world=pos.tolist(),raw_force_world_unassigned=f.tolist(),
                normal_load_n=normal,tangential_load_n=tangent,force_norm_n=float(np.linalg.norm(f)))
            if key in unique:
                old=unique[key]
                if not np.isclose(old['normal_load_n'],normal,rtol=1e-5,atol=1e-5) or not np.isclose(old['tangential_load_n'],tangent,rtol=1e-5,atol=1e-5):
                    raise ValueError('Duplicate contact carries inconsistent load')
                duplicates+=1
            else:unique[key]=data
    points=list(unique.values())
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

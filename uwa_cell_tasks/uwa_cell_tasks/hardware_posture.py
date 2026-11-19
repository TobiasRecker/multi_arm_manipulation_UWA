"""Task suitability first; explicit, bounded posture metrics after feasibility."""
import numpy as np
from scipy.spatial.transform import Rotation
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import joint_names


def branch_allowed(q,required_sign):
    """Use physical elbow branch, invariant to equivalent +/-2pi windings."""
    return required_sign is None or required_sign*np.sin(q[2])>1e-4


def rank_postures(problem,start,combinations):
    """Pareto rank reserves, scaled Jacobian, wrist separation and travel.

    These are ranking proxies, not new safety limits or a full-workspace
    manipulability qualification. 0.5m is an explicit characteristic length
    for comparing translation/rotation Jacobian rows without mixing units.
    """
    names=problem.names;cache={};eps=1e-5
    for combo in combinations:
        state=dict(start)
        for arm,q in combo['goals'].items():state.update(zip(joint_names(arm),q))
        world=problem.spheres.world(state);metrics={}
        for arm,q in combo['goals'].items():
            q=np.array(q);joints=joint_names(arm);bounds=np.array([problem.collision.bounds[j]for j in joints]);margin=np.minimum(q-bounds[:,0],bounds[:,1]-q)
            chain=cache.setdefault(arm,Chain(problem.original_description,'world',arm+'_tool0'));cols=[]
            for i in range(6):
                plus=q.copy();minus=q.copy();plus[i]+=eps;minus[i]-=eps
                tp=chain.forward(dict(state,**dict(zip(joints,plus))));tm=chain.forward(dict(state,**dict(zip(joints,minus))))
                cols.append(np.r_[(tp[:3,3]-tm[:3,3])/.5,Rotation.from_matrix(tp[:3,:3]@tm[:3,:3].T).as_rotvec()]/(2*eps))
            singular=np.linalg.svd(np.array(cols).T,compute_uv=False)
            mask=np.array([link.startswith(arm+'_wrist_')for link in problem.spheres.links[arm]])
            clear=[]
            for other in names:
                if other==arm:continue
                d=np.linalg.norm(world[arm][mask,None,:]-world[other][None,:,:],axis=2)-problem.spheres.radii[arm][mask,None]-problem.spheres.radii[other][None,:]
                clear.append(float(d.min()))
            elbow=Chain(problem.original_description,'world',arm+'_forearm_link').forward(state)[:3,3]
            metrics[arm]=dict(joint_margin_rad=margin.tolist(),minimum_joint_margin_fraction=float(np.min(2*margin/(bounds[:,1]-bounds[:,0]))),scaled_jacobian_sigma_min=float(singular[-1]),jacobian_characteristic_length_m=.5,wrist_neighbor_clearance_m=min(clear),elbow_world_z_m=float(elbow[2]),travel_rad=float(np.linalg.norm(q-[start[j]for j in joints])))
        combo['posture_metrics']=metrics
        combo['_quality']=np.array([min(m['minimum_joint_margin_fraction']for m in metrics.values()),min(m['scaled_jacobian_sigma_min']for m in metrics.values()),min(m['wrist_neighbor_clearance_m']for m in metrics.values()),-sum(m['travel_rad']for m in metrics.values())])
    pending=list(combinations);rank=0;ordered=[]
    while pending:
        front=[c for c in pending if not any(np.all(d['_quality']>=c['_quality'])and np.any(d['_quality']>c['_quality'])for d in pending)]
        front.sort(key=lambda c:c['start_distance_sum_rad'])
        for c in front:c['posture_pareto_rank']=rank;ordered.append(c)
        pending=[c for c in pending if not any(c is d for d in front)];rank+=1
    for c in ordered:c.pop('_quality')
    return ordered

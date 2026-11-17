"""Deterministic nearest-free side allocation and fixed top-down wall targets."""
import numpy as np
from itertools import permutations

from uwa_cell_gazebo.charuco_views import Chain
from .common import ROBOT_IDS


def nearest_free_assignment(bases, sites):
    """Reserve one of each robot's nearest two sites; minimize total distance.

    Horizontal base-to-site distance is the preference, not planned path length.
    Enumerating assignments avoids greedy starvation onto a third preference.
    This optimizes horizontal assignment distance, not robot motion duration.
    """
    distances=np.linalg.norm(np.asarray(bases)[:,None,:2]-np.asarray(sites)[None,:,:2],axis=2)
    if distances.shape[0]>distances.shape[1] or not np.isfinite(distances).all():
        raise ValueError('Need at least one finite site per robot')
    ranked=[sorted(range(len(sites)),key=lambda s:(distances[r,s],s))[:2] for r in range(len(bases))]
    choices=[(sum(distances[r,s] for r,s in enumerate(choice)),choice)
             for choice in permutations(range(len(sites)),len(bases))
             if all(s in ranked[r] for r,s in enumerate(choice))]
    if not choices:raise ValueError('No unique assignment within the nearest two sides')
    _,choice=min(choices)
    return dict(enumerate(choice)),distances


def side_targets(problem, *, entry_depth_m=.015, pregrasp_m=.12):
    if not 0<=entry_depth_m<=.04 or not .02<=pregrasp_m<=.3:
        raise ValueError('Unsupported side depth or pregrasp distance')
    item=problem.carton;dims=np.asarray(item['manifest']['dimensions_m']);T=item['T_world_object']
    if not np.allclose(T[:3,2],[0,0,1],atol=1e-8):
        raise ValueError('Top-down side task requires an upright carton')
    x,y,z=dims
    local_sites=np.array([[0,y/2,z],[x,y/2,z],[x/2,0,z],[x/2,y,z]])
    names=['x_min','x_max','y_min','y_max'];inward=np.array([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0]])
    world=local_sites@T[:3,:3].T+T[:3,3]
    bases=[Chain(problem.description,'world',r+'_base_link').forward({})[:3,3] for r in ROBOT_IDS]
    assigned,distances=nearest_free_assignment(bases,world);targets={}
    for i,arm in enumerate(ROBOT_IDS):
        side=assigned[i];closing=T[:3,:3]@inward[side];down=np.array([0.,0.,-1.])
        R=np.column_stack([closing,np.cross(down,closing),down])
        tcp=world[side]-[0,0,entry_depth_m]
        gripper=np.eye(4);gripper[:3,:3]=R;gripper[:3,3]=tcp-R@np.array([0,0,.145])
        tool_gripper=Chain(problem.description,arm+'_tool0',arm+'_robotiq_85_base_link').forward({})
        target=gripper@np.linalg.inv(tool_gripper);pre=target.copy();pre[2,3]+=pregrasp_m
        offset=np.eye(4);offset[2,3]=.145
        ranking=sorted(range(4),key=lambda s:(distances[i,s],s))
        targets[arm]=dict(side_index=side,side_name=names[side],side_world_m=world[side].tolist(),
                          side_local_m=local_sites[side].tolist(),tcp_world_m=tcp.tolist(),
                          closing_axis_world=closing.tolist(),tool0_target=target.tolist(),
                          tool0_pregrasp=pre.tolist(),tool0_to_tcp=(tool_gripper@offset).tolist(),
                          base_world_m=np.asarray(bases[i]).tolist(),preference_rank=ranking.index(side)+1,
                          assignment_policy='unique nearest-two assignment minimizing summed horizontal distance',
                          distance_to_side_m=float(distances[i,side]),
                          ranked_sides=[dict(side=names[s],distance_m=float(distances[i,s])) for s in ranking])
    return targets

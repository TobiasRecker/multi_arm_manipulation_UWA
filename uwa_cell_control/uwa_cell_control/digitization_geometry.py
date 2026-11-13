"""Fixed geometry recipes for the digitization runner; no hardware interfaces."""
import cv2
import numpy as np
from scipy.optimize import least_squares

from .object_digitization import vertices as box_vertices, object_pose as box_pose, project, plane_point

FAMILIES=('box_shell','plate_l','multiview_mesh')


def known_sizes(family, known):
    required={'box_shell':('wall_thickness_m',),'plate_l':('plate_thickness_m','profile_size_m')}.get(family,())
    for key in required:
        value=known.get(key)
        if type(value) not in (int,float) or not np.isfinite(value) or not 0<value<.1:
            raise ValueError('Known dimension required in metres: '+key)


def pose(parameters,family):
    if family=='box_shell':return box_pose(parameters)
    if family!='plate_l':raise ValueError('No parametric recipe for '+family)
    x,y,yaw,*_=parameters;c,s=np.cos(yaw),np.sin(yaw)
    return np.array([[c,s,0,x],[s,-c,0,y],[0,0,-1,0],[0,0,0,1.]])


def local_vertices(parameters,family,known):
    p=np.asarray(parameters,float)
    if p.shape!=(6,) or not np.isfinite(p).all() or min(p[3:])<=0:raise ValueError('Invalid shape parameters')
    if family=='box_shell':
        T=pose(p,family);return (box_vertices(p)-T[:3,3])@T[:3,:3]
    if family!='plate_l':raise ValueError('No parametric recipe for '+family)
    known_sizes(family,known);W,D,H=p[3:];b=known['profile_size_m']+known['plate_thickness_m']
    return np.array([[0,b,b],[W,b,b],[W,b+D,b],[0,b+D,b],[0,b,H+b],[W,b,H+b],
                     [0,0,0],[W,0,0],[0,0,H+b],[W,0,H+b],[0,D+b,0],[W,D+b,0]])


def vertices(parameters,family,known):
    T=pose(parameters,family);return local_vertices(parameters,family,known)@T[:3,:3].T+T[:3,3]


def solid_parts(parameters,family,known):
    """Named disjoint/touching gross bodies; fasteners and holes not inferred."""
    known_sizes(family,known);W,D,H=np.asarray(parameters)[3:]
    if family=='box_shell':
        t=known['wall_thickness_m']
        if min(W,D)<=2*t or H<=t:raise ValueError('Thickness exceeds box dimensions')
        return [('base',[0,0,0],[W,D,t]),('front',[0,0,t],[W,t,H-t]),
                ('rear',[0,D-t,t],[W,t,H-t]),('left',[0,t,t],[t,D-2*t,H-t]),
                ('right',[W-t,t,t],[t,D-2*t,H-t])]
    if family!='plate_l':raise ValueError('Unsupported solid recipe')
    p,t=known['profile_size_m'],known['plate_thickness_m'];b=p+t
    if W<=2*p or H<=p:raise ValueError('Profile exceeds plate dimensions')
    # Hidden clearance removes line-only contact; recorded as an assumption.
    gap=min(.0001,t/10)
    return [('base_left',[0,0,0],[p,D+b,p]),('base_right',[W-p,0,0],[p,D+b,p]),
            ('base_back',[p,0,0],[W-2*p,p,p]),('base_front',[p,D+t,0],[W-2*p,p,p]),
            ('upright_left',[0,0,p],[p,p,H+t]),('upright_right',[W-p,0,p],[p,p,H+t]),
            ('upright_top',[p,0,H+t],[W-2*p,p,p]),('base_ptfe',[0,p+gap,p],[W,D+t-gap,t]),
            ('upright_ptfe',[0,p,b],[W,t,H])]


def dimensions(parameters,family,known):
    v=local_vertices(parameters,family,known);return np.ptp(v,axis=0).tolist()


def fit(cameras,annotations,family,known,rough_size,policy):
    """Robust fit with pre-labelled held-out views and frozen camera models."""
    if family not in ('box_shell','plate_l'):raise ValueError('Complex geometry needs a multiview mesh backend')
    known_sizes(family,known);width=annotations.get('proxy_width')
    if width!=policy['proxy_width']:raise ValueError('Annotation/policy proxy width mismatch')
    observations=annotations['observations'];fit_keys=[];validation_keys=[]
    limit=8 if family=='box_shell' else 12
    for key,o in observations.items():
        if key not in cameras:raise ValueError('Unknown camera view '+key)
        if not cameras[key].get('metric_eligible',True):raise ValueError('View excluded from metric use: '+key)
        ids=o['ids'];pixels=np.asarray(o['pixels'],float)
        if (len(set(ids))!=len(ids) or len(ids)<4 or
                any(type(i)!=int or not 0<=i<limit for i in ids) or
                pixels.shape!=(len(ids),2) or not np.isfinite(pixels).all()):
            raise ValueError('Invalid image landmarks '+key)
        native=cameras[key]['image_size'];height=width*native[1]/native[0]
        if (pixels<0).any() or (pixels[:,0]>=width).any() or (pixels[:,1]>=height).any():
            raise ValueError('Landmarks outside full unrotated proxy image: '+key)
        if o.get('role')=='fit':fit_keys.append(key)
        elif o.get('role')=='validation':validation_keys.append(key)
        else:raise ValueError('Explicit fit/validation role required before fitting')
    if len(fit_keys)<policy['minimum_fit_views'] or len(validation_keys)<policy['minimum_validation_views']:
        raise ValueError('Insufficient independent fit/validation views')
    centers=[np.linalg.inv(np.array(cameras[k]['T_camera_board']))[:3,3] for k in fit_keys]
    if max(np.linalg.norm(a-b) for a in centers for b in centers)<policy['minimum_camera_baseline_m']:
        raise ValueError('Degenerate camera baseline')
    if len({cameras[k].get('image_sha256',k) for k in observations})!=len(observations):
        raise ValueError('Duplicate photographs cannot be independent observations')
    initial=annotations.get('initial_parameters_board_m_rad')
    if initial is None:
        # Initial geometry from support edge in one FIT image, never validation.
        first=next((k for k in fit_keys if {2,3}<=set(observations[k]['ids'])),None)
        if first is None:raise ValueError('A fit view needs support corners2 and3 or an explicit initial seed')
        o=observations[first];c=cameras[first]
        support=[plane_point(np.array(o['pixels'][o['ids'].index(i)]),c,width) for i in (3,2)]
        if family=='plate_l':
            # Plate corners are above support by profile+plate thickness.
            T=np.linalg.inv(np.array(c['T_camera_board']));support=[];b=known['profile_size_m']+known['plate_thickness_m']
            for i in (3,2):
                pixel=np.array(o['pixels'][o['ids'].index(i)])*c['image_size'][0]/width
                ray=np.r_[cv2.undistortPoints(pixel[None,None,:],np.array(c['K']),np.array(c['D'])).ravel(),1.]
                direction=T[:3,:3]@ray
                if abs(direction[2])<1e-6:raise ValueError('Support ray parallel to plane')
                support.append(T[:3,3]+(-b-T[2,3])/direction[2]*direction)
        edge=support[1]-support[0];yaw=np.arctan2(edge[1],edge[0]);W=np.linalg.norm(edge[:2]);D,H=rough_size[1:]
        if family=='plate_l':
            b=known['profile_size_m']+known['plate_thickness_m'];D=max(.02,D-b);H=max(.02,H-b)
            xy=support[0][:2]-(D+b)*np.array([np.sin(yaw),-np.cos(yaw)])
        else:xy=support[0][:2]-D*np.array([-np.sin(yaw),np.cos(yaw)])
        initial=np.r_[xy,yaw,W,D,H]
    initial=np.asarray(initial,float)
    def residual(parameters):
        points=vertices(parameters,family,known)
        return np.concatenate([(project(points[observations[k]['ids']],cameras[k],width)-observations[k]['pixels']).ravel() for k in fit_keys])
    result=least_squares(residual,initial,bounds=([-5,-5,-10,.01,.01,.01],[5,5,10,2,2,2]),
        loss='soft_l1',f_scale=2.,max_nfev=400)
    singular=np.linalg.svd(result.jac,compute_uv=False)
    if not result.success or singular[-1]/singular[0]<1e-8:raise ValueError('Fit failed or underconstrained')
    metrics={};passed=True
    for key,o in observations.items():
        errors=project(vertices(result.x,family,known)[o['ids']],cameras[key],width)-o['pixels']
        rms=float(np.sqrt(np.mean(np.sum(errors**2,axis=1))))
        bound=policy['maximum_fit_rms_proxy_px'] if o['role']=='fit' else policy['maximum_validation_rms_proxy_px']
        metrics[key]=dict(role=o['role'],rms_proxy_px=rms,threshold_proxy_px=bound,passed=rms<=bound)
        passed &= rms<=bound
    return dict(schema=1,family=family,parameters_board_m_rad=result.x.tolist(),
        T_board_object=pose(result.x,family).tolist(),dimensions_m=dimensions(result.x,family,known),
        known_dimensions_m=known,parts=[dict(name=n,origin_m=list(o),size_m=list(s)) for n,o,s in solid_parts(result.x,family,known)],
        metrics=metrics,image_consistency_passed=bool(passed),absolute_accuracy_validated=False,
        tracking_validated=False,manipulation_approved=False,validation_used_in_fit=False,
        hidden_cad_clearance_m=.0001 if family=='plate_l' else 0,
        assumptions=['Rigid supported object; rectangular perpendicular surfaces; gross-body recipe, not measured fine details'])

"""Uniform offline retiming and analytical derivative bounds for saved primitives."""
from copy import deepcopy
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq

from .carton_paths import evaluate,quintic


def scale_path(path,factor):
    if not np.isfinite(factor) or factor<=0:raise ValueError('Positive finite time scale required')
    result=deepcopy(path)
    result['duration_s']/=factor
    for segment in result['segments']:
        segment['check']['duration_s']/=factor
        segment['check']['limits_kind']='Retimed offline trial; original motion-profile compliance is not inherited'
    result['time_scale']=factor
    return result


def velocity_at(path,time_s):
    if time_s<0:return np.zeros(6)
    remaining=float(time_s)
    for segment in path['segments']:
        duration=segment['check']['duration_s']
        if remaining<=duration:return evaluate(segment,remaining/duration,1)/duration
        remaining-=duration
    return np.zeros(6)


def primitive_bounds(segment,subdivisions=1024):
    """Local interval bounds for q(h(u)); include both sides of cubic-spline knots.

    Bound cubic derivatives and quintic derivatives analytically on each small
    interval, then apply the chain rule/triangle inequality. These are floating
    point conservative mathematical bounds, not measured actuator peaks.
    """
    spline=CubicSpline(segment['knots'],segment['positions'],bc_type='natural')
    inverse=[0. if s==0 else 1. if s==1 else brentq(lambda u:quintic(u)-s,0,1,xtol=1e-14) for s in spline.x]
    edges=np.unique(np.r_[np.linspace(0,1,subdivisions+1),inverse])
    lo,hi=edges[:-1],edges[1:];valid=hi-lo>1e-13;lo,hi=lo[valid],hi[valid]
    mid=quintic((lo+hi)/2);idx=np.clip(np.searchsorted(spline.x,mid,side='right')-1,0,len(spline.x)-2)
    xlo=quintic(lo)-spline.x[idx];xhi=quintic(hi)-spline.x[idx]
    c3,c2,c1,_=spline.c[:,idx]
    a=xlo[:,None];b=xhi[:,None]
    grad=np.maximum(abs(3*c3*a*a+2*c2*a+c1),abs(3*c3*b*b+2*c2*b+c1))
    roots=np.divide(-c2,3*c3,out=np.zeros_like(c2),where=c3!=0)
    inside=(c3!=0)&(roots>a)&(roots<b)
    grad=np.maximum(grad,np.where(inside,abs(3*c3*roots**2+2*c2*roots+c1),0))
    curvature=np.maximum(abs(6*c3*a+2*c2),abs(6*c3*b+2*c2));third=abs(6*c3)
    def interval_max(function,critical):
        peak=np.maximum(abs(function(lo)),abs(function(hi)))
        for point in critical:peak=np.maximum(peak,np.where((lo<=point)&(point<=hi),abs(function(point)),0))
        return peak[:,None]
    hp=interval_max(lambda u:30*u*u*(1-u)**2,[.5])
    hpp=interval_max(lambda u:60*u-180*u*u+120*u**3,[(3-np.sqrt(3))/6,(3+np.sqrt(3))/6])
    hppp=interval_max(lambda u:60-360*u+360*u*u,[.5])
    duration=segment['check']['duration_s']
    bounds=[np.max(grad*hp,axis=0)/duration,
            np.max(curvature*hp**2+grad*hpp,axis=0)/duration**2,
            np.max(third*hp**3+3*curvature*hp*hpp+grad*hppp,axis=0)/duration**3]
    # Numerical slack for inverse-knot/IEEE rounding, not a physical uncertainty allowance.
    return dict(velocity_rad_s=(bounds[0]*(1+1e-10)+1e-12).tolist(),
                acceleration_rad_s2=(bounds[1]*(1+1e-10)+1e-12).tolist(),
                jerk_rad_s3=(bounds[2]*(1+1e-10)+1e-12).tolist(),
                intervals=len(lo),method='Local analytic derivative envelopes and chain-rule triangle bounds')


def path_bounds(path):
    records=[primitive_bounds(s) for s in path['segments']]
    return {key:np.max([r[key] for r in records],axis=0).tolist()
            for key in ['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3']}


def reserve_check(problem,world,paths,time_s):
    """Existing four-neighbour stop model, evaluated with actual commanded speed.

    Keep original operating-cap floor, ages, latency and braking assumptions.
    This evaluates their consequences; it does not authorize a larger cap.
    """
    import itertools
    from .common import ROBOT_IDS,PAIRS
    budgets={}
    for arm in ROBOT_IDS:
        velocities=np.zeros(len(problem.names[arm]));velocities[:6]=velocity_at(paths[arm],time_s)
        budgets[arm]=problem.spheres.arm_budget(arm,velocities,problem.cfg['state_timeout_s'],problem.cfg)[0]
    neighbours={frozenset(pair) for pair in PAIRS};pairs=[]
    for a,b in itertools.combinations(ROBOT_IDS,2):
        gap=float(problem.spheres.nearest(world,a,b)['clearance_m'])
        required=problem.cfg['model_margin_m']+(budgets[a]+budgets[b] if frozenset((a,b)) in neighbours else 0.)
        pairs.append(dict(arms=[a,b],gap_m=gap,required_m=required,violation=gap<required))
    return pairs

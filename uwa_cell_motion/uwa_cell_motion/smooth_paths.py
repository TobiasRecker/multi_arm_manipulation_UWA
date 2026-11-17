"""Offline C3 timing and minimally changed C4 Cartesian joint interpolation."""
from copy import deepcopy
from math import comb
import numpy as np
from scipy.interpolate import CubicSpline,make_interp_spline,PPoly


def curve(segment):
    if segment['kind']=='JOINT':
        return make_interp_spline([0.,1.],segment['positions'],k=1)
    return make_interp_spline(segment['knots'],segment['positions'],k=5)


def curve_bounds(segment):
    """Conservative derivative bounds via local power-to-Bernstein coefficients."""
    sp=curve(segment);result=np.zeros((3,6))
    for joint in range(6):
        pp=PPoly.from_spline((sp.t,sp.c[:,joint],sp.k))
        for derivative in range(1,4):
            polynomial=pp.derivative(derivative)
            for i,width in enumerate(np.diff(polynomial.x)):
                if width<=0 or polynomial.x[i+1]<=0 or polynomial.x[i]>=1:continue
                power=polynomial.c[:,i][::-1]*width**np.arange(len(polynomial.c))
                degree=len(power)-1
                bernstein=[sum(power[j]*comb(k,j)/comb(degree,j) for j in range(k+1)) for k in range(degree+1)]
                result[derivative-1,joint]=max(result[derivative-1,joint],max(abs(np.asarray(bernstein))))
    return result*(1+1e-10)+1e-12


def ramp_profile(vmax,amax,jmax):
    """Unit progress; quintic velocity ramps and optional constant-speed cruise."""
    if not np.isfinite([vmax,amax,jmax]).all() or min(vmax,amax,jmax)<=0:
        raise ValueError('Positive finite limits required')
    acceleration_peak=1.875;jerk_peak=10*np.sqrt(3)/3
    v=min(vmax,np.sqrt(amax/acceleration_peak),(jmax/jerk_peak)**(1/3))
    ramp=max(acceleration_peak*v/amax,np.sqrt(jerk_peak*v/jmax))
    cruise=max(0.,1/v-ramp)
    return dict(peak_progress_speed=v,ramp_s=ramp,cruise_s=cruise,duration_s=2*ramp+cruise)


def progress(profile,t):
    """Position through jerk. Velocity, acceleration and jerk match at joins."""
    t=np.asarray(t,float);r=profile['ramp_s'];c=profile['cruise_s'];v=profile['peak_progress_speed']
    def ramp(u):
        u=np.clip(u,0,1)
        h=10*u**3-15*u**4+6*u**5
        H=2.5*u**4-3*u**5+u**6
        hp=30*u*u*(1-u)**2;hpp=60*u-180*u*u+120*u**3
        return H,h,hp,hpp
    H,h,hp,hpp=ramp(t/r)
    values=[v*r*H,v*h,v/r*hp,v/r**2*hpp]
    cruise=(t>=r)&(t<r+c)
    values=[np.where(cruise,z,y) for y,z in zip(values,[v*(.5*r+t-r),v,0.,0.])]
    u=(t-r-c)/r;H,h,hp,hpp=ramp(u)
    down=(t>=r+c)&(t<=2*r+c)
    values=[np.where(down,z,y) for y,z in zip(values,[v*(.5*r+c+r*(np.clip(u,0,1)-H)),v*(1-h),-v/r*hp,-v/r**2*hpp])]
    values[0]=np.where(t<=0,0.,np.where(t>=2*r+c,1.,values[0]))
    for i in range(1,4):values[i]=np.where((t<=0)|(t>=2*r+c),0.,values[i])
    return values


def plan_segment(segment,*,velocity=.45,acceleration=.4,jerk=2.):
    if not np.isfinite([velocity,acceleration,jerk]).all() or min(velocity,acceleration,jerk)<=0:
        raise ValueError('Positive finite joint limits required')
    bound=curve_bounds(segment);g,c,k=np.max(bound,axis=1)
    law=ramp_profile(velocity/g,acceleration/g,jerk/g)
    v=law['peak_progress_speed'];a=1.875*v/law['ramp_s'];j=(10*np.sqrt(3)/3)*v/law['ramp_s']**2
    joint_bounds=np.array([g*v,c*v*v+g*a,k*v**3+3*c*v*a+g*j])
    scale=max(1.,joint_bounds[0]/velocity,np.sqrt(joint_bounds[1]/acceleration),(joint_bounds[2]/jerk)**(1/3))*(1+1e-8)
    law['peak_progress_speed']/=scale
    for key in ['ramp_s','cruise_s','duration_s']:law[key]*=scale
    out=deepcopy(segment);out['time_law']=law
    out['check']['duration_s']=law['duration_s']
    out['check']['validation']='PENDING_NEW_CURVE_AND_TIME_CHECK'
    out['smooth_bounds']=dict(velocity_rad_s=float(joint_bounds[0]/scale),
                              acceleration_rad_s2=float(joint_bounds[1]/scale**2),
                              jerk_rad_s3=float(joint_bounds[2]/scale**3))
    out['spatial_interpolation']='linear' if segment['kind']=='JOINT' else 'quintic_interpolating_bspline'
    return out


def sample_segment(segment,t,derivative=0):
    s,v,a,j=progress(segment['time_law'],t);sp=curve(segment)
    if derivative==0:return sp(s)
    def d(n):return sp(s,nu=n) if n<=sp.k else np.zeros_like(sp(s))
    if derivative==1:return d(1)*np.expand_dims(v,-1)
    if derivative==2:return d(2)*np.expand_dims(v*v,-1)+d(1)*np.expand_dims(a,-1)
    if derivative==3:return d(3)*np.expand_dims(v**3,-1)+3*d(2)*np.expand_dims(v*a,-1)+d(1)*np.expand_dims(j,-1)
    raise ValueError('Supported derivatives: 0..3')


def plan_path(path,**limits):
    result=deepcopy(path);result['segments']=[plan_segment(s,**limits) for s in path['segments']]
    result['duration_s']=sum(s['time_law']['duration_s'] for s in result['segments'])
    result['limits']=limits;result['time_law_kind']='C3 progress ramps with cruise; C4 Cartesian joint spline'
    return result


def path_at(path,t,derivative=0):
    remaining=float(t)
    for segment in path['segments']:
        duration=segment['time_law']['duration_s']
        if remaining<=duration:return sample_segment(segment,max(0.,remaining),derivative)
        remaining-=duration
    return np.asarray(path['segments'][-1]['positions'][-1]) if derivative==0 else np.zeros(6)


def spatial_deviation(original,smoothed,s):
    return curve(smoothed)(s)-CubicSpline(original['knots'],original['positions'],bc_type='natural')(s)

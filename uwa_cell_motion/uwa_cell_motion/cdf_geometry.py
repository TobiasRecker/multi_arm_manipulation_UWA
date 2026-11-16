"""Batched UR sphere SDF for CDF contact data; no ROS clients or motion.

The three unselected arms and tool driving joints are frozen. This steering
geometry encloses complete collision volumes; the shared full MoveIt validator
remains authoritative (including self collisions and allowed contact pairs).
"""
import json
import numpy as np
from scipy.spatial.distance import cdist
from .common import joint_names,sha


class FrozenScene:
    def __init__(self,problem,request):
        if len(request['selected'])!=1:raise ValueError('CDF prototype requires exactly one moving UR')
        self.arm=request['selected'][0];self.names=joint_names(self.arm);self.problem=problem
        self.start=dict(request['start']);model=problem.spheres
        self.bounds=np.asarray([problem.collision.bounds[j] for j in self.names])
        zero=dict(self.start,**{j:0. for j in self.names});frames=model.geometry.fk.frames(zero)
        joints={j[0]:j for j in model.geometry.fk.joints};self.fixed=[];self.axes=[];children=[]
        previous=np.eye(4)
        for name in self.names:
            _,kind,parent,child,fixed,axis,_=joints[name]
            if kind not in ('revolute','continuous'):raise ValueError('CDF currently supports six revolute arm joints')
            self.fixed.append(np.linalg.inv(previous)@frames[parent]@fixed)
            axis=axis/np.linalg.norm(axis);self.axes.append(axis);children.append(child);previous=frames[child]
        depth=np.sum(model.motion_radii[self.arm][:,:6]>0,axis=1)
        self.indices=np.flatnonzero(depth>0);self.depth=depth[self.indices].astype(int)
        self.radii=model.radii[self.arm][self.indices];self.local=[]
        for index,k in zip(self.indices,self.depth):
            reference=frames[children[k-1]];link=model.links[self.arm][index]
            world=frames[link][:3,:3]@model.local[self.arm][index]+frames[link][:3,3]
            self.local.append(reference[:3,:3].T@(world-reference[:3,3]))
        self.local=np.asarray(self.local);self.fixed=np.asarray(self.fixed);self.axes=np.asarray(self.axes)
        world=model.world(self.start);thresholds={frozenset(p['arms']):p['threshold_m'] for p in problem.thresholds()}
        centres=[];radii=[];labels=[]
        for rid in problem.names:
            if rid==self.arm:continue
            margin=thresholds.get(frozenset((rid,self.arm)),problem.cfg['model_margin_m'])
            centres.extend(world[rid]);radii.extend(model.radii[rid]+margin);labels.extend([rid]*len(world[rid]))
        self.obstacles=np.asarray(centres);self.obstacle_radii=np.asarray(radii);self.labels=labels
        self.boxes=[]
        for body in model.environment:
            T=frames[body.link]@body.fixed
            lo,hi=body.visual_vertices.min(axis=0),body.visual_vertices.max(axis=0)
            self.boxes.append((T,(lo+hi)/2,(hi-lo)/2,body.link))
        self.margin=problem.cfg['model_margin_m']
        self.binding=sha(json.dumps(dict(version=1,model=problem.signature,assets=model.geometry.assets,arm=self.arm,
            frozen={j:v for j,v in self.start.items() if j not in self.names},
            thresholds=problem.thresholds(),margin=self.margin,geometry='whole-body-spheres-static-spheres-oriented-AABBs-floor'),sort_keys=True))

    def forward(self,q):
        q=np.atleast_2d(np.asarray(q,float))
        if q.shape[1]!=6 or not np.isfinite(q).all():raise ValueError('Expected finite six-joint configurations')
        B=len(q);T=np.broadcast_to(np.eye(4),(B,4,4)).copy();poses=[];origins=[];axes=[]
        for i,(fixed,axis) in enumerate(zip(self.fixed,self.axes)):
            T=T@fixed;origins.append(T[:,:3,3].copy());axes.append(T[:,:3,:3]@axis)
            x,y,z=axis;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
            angle=q[:,i,None,None];R=np.eye(3)+np.sin(angle)*K+(1-np.cos(angle))*(K@K)
            T[:,:3,:3]=T[:,:3,:3]@R;poses.append(T.copy())
        poses=np.stack(poses,axis=1)[:,self.depth-1]
        centres=np.einsum('bsij,sj->bsi',poses[:,:,:3,:3],self.local)+poses[:,:,:3,3]
        return centres,np.stack(origins,axis=1),np.stack(axes,axis=1)

    def sdf(self,q):
        """Scene min SDF [m], analytic joint gradient and contact prefix length.

        This is the SDF used to find CDF zero-level sets, NOT the CDF itself.
        Every frozen arm participates, including diagonals.
        """
        centres,origins,axes=self.forward(q);B,S,_=centres.shape;rows=np.arange(B)
        distances=cdist(centres.reshape(-1,3),self.obstacles).reshape(B,S,-1)
        distances-=self.radii[None,:,None]+self.obstacle_radii[None,None,:]
        flat=np.argmin(distances.reshape(B,-1),axis=1);sphere=flat//len(self.obstacles);obstacle=flat%len(self.obstacles)
        value=distances[rows,sphere,obstacle];normal=centres[rows,sphere]-self.obstacles[obstacle]
        normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
        for T,mid,half,label in self.boxes:
            local=(centres-T[:3,3])@T[:3,:3]-mid
            delta=abs(local)-half;outside=np.maximum(delta,0.);length=np.linalg.norm(outside,axis=2)
            d=length+np.minimum(np.max(delta,axis=2),0.)-self.radii[None]-self.margin
            index=np.argmin(d,axis=1);chosen=d[rows,index];replace=chosen<value
            p=local[rows,index];out=outside[rows,index];norm=length[rows,index]
            n=np.sign(p)*out/np.maximum(norm[:,None],1e-12)
            inside=norm<1e-12;a=np.argmax(delta[rows,index],axis=1)
            n[inside]=0.;n[rows[inside],a[inside]]=np.where(p[rows[inside],a[inside]]<0,-1.,1.)
            n=n@T[:3,:3].T
            value=np.where(replace,chosen,value);normal[replace]=n[replace];sphere[replace]=index[replace]
        # Same floor as CollisionModel, with steering reserve.
        d=centres[:,:,2]-self.radii[None]+.003-self.margin;index=np.argmin(d,axis=1)
        replace=d[rows,index]<value;value=np.minimum(value,d[rows,index]);sphere[replace]=index[replace];normal[replace]=[0.,0.,1.]
        depth=self.depth[sphere];point=centres[rows,sphere]
        jac=np.cross(axes,point[:,None]-origins);jac[np.arange(6)[None]>=depth[:,None]]=0.
        gradient=np.einsum('bi,bji->bj',normal,jac)
        return value,gradient,depth

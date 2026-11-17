"""Conservative sphere unions enclosing complete URDF collision-body boxes.

Each slice of a body's local AABB lies inside its circumsphere. This encloses
the entire mesh/primitive volume, not merely a finite set of mesh vertices.
Finger mimic FK uses measured driving joints, including the open configuration.
"""
import xml.etree.ElementTree as ET
import numpy as np

from uwa_cell_control.scan_separation import Geometry, Body
from .common import PAIRS,arm_velocity_limit,joint_velocity_limits,BODY_RESERVE_MODEL


def box_spheres(lo, hi, spacing):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    if lo.shape != (3,) or hi.shape != (3,) or not np.isfinite([lo, hi]).all() or np.any(hi < lo) or not spacing > 0:
        raise ValueError('Invalid box/sphere spacing')
    axis = int(np.argmax(hi-lo))
    count = max(1, int(np.ceil((hi[axis]-lo[axis])/spacing)))
    half = (hi-lo)/2
    half[axis] /= count
    centres = np.tile((lo+hi)/2, (count, 1))
    centres[:, axis] = lo[axis]+half[axis]+np.arange(count)*2*half[axis]
    return centres, np.full(count, np.linalg.norm(half)+1e-9)


def sphere_aabb(centres,radii):
    """Outward-rounded bounds of complete spheres, not their centres."""
    return np.array([np.nextafter(np.min(centres-radii[:,None],axis=0),-np.inf),
                     np.nextafter(np.max(centres+radii[:,None],axis=0),np.inf)])


def aabb_separated(a,b,threshold):
    # A lower bound above the required clearance proves this pair clear.
    # Near equality/roundoff always falls back to the original fine query.
    gap=np.maximum(np.maximum(a[0]-b[1],b[0]-a[1]),0.)
    reserve=1e-12*(1+abs(threshold)+np.max(abs(a))+np.max(abs(b)))
    return bool(np.dot(gap,gap)>(threshold+reserve)**2)


class SphereModel:
    def __init__(self, description, names, spacing=.05):
        self.geometry = Geometry(description, names)
        self.names = names
        self.local, self.radii, self.links, self.motion_radii = {}, {}, {}, {}
        self.coverage = []
        self.environment=[]
        for link in ET.fromstring(description).findall('link'):
            name=link.get('name')
            if any(name.removeprefix('calibrated/').startswith(r+'_') for r in names):continue
            for index,collision in enumerate(link.findall('collision')):
                self.environment.append(Body('environment',name,index,collision,lambda _:np.zeros(1)))
        for rid, bodies in self.geometry.bodies.items():
            centres, radii, links, motion = [], [], [], []
            for body in bodies:
                vertices = body.visual_vertices
                c,r=(np.zeros((1,3)),np.asarray([body.radius])) if body.kind=='sphere' else box_spheres(vertices.min(axis=0),vertices.max(axis=0),spacing)
                c = c @ body.fixed[:3, :3].T + body.fixed[:3, 3]
                centres.extend(c); radii.extend(r); links.extend([body.link]*len(r))
                motion.extend([body.radii]*len(r))
                self.coverage.append(dict(arm=rid, link=body.link, collision_index=body.index,
                                          spheres=len(r), method='exact sphere primitive' if body.kind=='sphere' else 'complete local AABB slice circumspheres'))
            self.local[rid], self.radii[rid] = np.asarray(centres), np.asarray(radii)
            self.links[rid], self.motion_radii[rid] = links, np.asarray(motion)
        # Cache is used only by offline/planning threshold checks. Keys include
        # every upstream moving/mimic source, so changed tools/ancestors cannot
        # silently reuse frozen geometry. Each model instance owns its cache.
        joints={j[0]:j for j in self.geometry.fk.joints};dependencies={'world':set()}
        def source(name):
            mimic=joints[name][6]
            return source(mimic.get('joint')) if mimic is not None else name
        for name,kind,parent,child,fixed,axis,mimic in self.geometry.fk.joints:
            dependencies[child]=dependencies[parent]|({source(name)} if kind in ('revolute','continuous','prismatic') else set())
        self.planning_dependencies={r:tuple(sorted(set().union(*(dependencies[l] for l in self.links[r])))) for r in names}
        self._planning_cache={}
        self.planning_stats=dict(cache_hits=0,cache_misses=0,pair_queries=0,prefilter_clear=0,fine_queries=0)

    def planning_world(self,positions):
        required={j for n in self.names.values() for j in n}
        if not required<=positions.keys() or not np.isfinite([positions[j] for j in required]).all():
            raise ValueError('Missing/nonfinite measured arm or gripper joints')
        keys={r:tuple(positions.get(j,0.) for j in deps) for r,deps in self.planning_dependencies.items()}
        if not all(np.isfinite(k).all() for k in keys.values()):raise ValueError('Nonfinite upstream joint state')
        changed=[r for r,k in keys.items() if r not in self._planning_cache or self._planning_cache[r][0]!=k]
        frames=self.geometry.fk.frames(positions) if changed else None
        for rid in changed:
            transforms=np.asarray([frames[l] for l in self.links[rid]])
            points=np.einsum('nij,nj->ni',transforms[:,:3,:3],self.local[rid])+transforms[:,:3,3]
            bounds=sphere_aabb(points,self.radii[rid]);points.setflags(write=False);bounds.setflags(write=False)
            self._planning_cache[rid]=(keys[rid],points,bounds)
        self.planning_stats['cache_misses']+=len(changed);self.planning_stats['cache_hits']+=len(keys)-len(changed)
        return ({r:self._planning_cache[r][1] for r in keys},{r:self._planning_cache[r][2] for r in keys})

    def pair_clear(self,world,bounds,a,b,threshold):
        """Same strict threshold decision as nearest(), with a broad phase."""
        if not np.isfinite(threshold) or threshold<0:raise ValueError('Invalid clearance threshold')
        self.planning_stats['pair_queries']+=1
        if aabb_separated(bounds[a],bounds[b],threshold):
            self.planning_stats['prefilter_clear']+=1;return True
        self.planning_stats['fine_queries']+=1
        return bool(self.nearest(world,a,b)['clearance_m']>threshold)

    def world(self, positions, partial=False):
        required = {j for names in self.names.values() for j in names}
        if (not partial and not required <= positions.keys()) or not np.isfinite([positions[j] for j in required if j in positions]).all():
            raise ValueError('Missing/nonfinite measured arm or gripper joints')
        frames = self.geometry.fk.frames(positions)
        result = {}
        for rid, centres in self.local.items():
            if partial and not all(j in positions for j in self.names[rid]):continue
            transforms = np.asarray([frames[link] for link in self.links[rid]])
            result[rid] = np.einsum('nij,nj->ni', transforms[:, :3, :3], centres)+transforms[:, :3, 3]
        return result

    def nearest(self, world, a, b):
        delta = world[a][:, None, :]-world[b][None, :, :]
        clearances = np.linalg.norm(delta, axis=2)-self.radii[a][:, None]-self.radii[b][None, :]
        i, j = np.unravel_index(np.argmin(clearances), clearances.shape)
        direction=world[b][j]-world[a][i];length=np.linalg.norm(direction)
        direction=direction/length if length>1e-12 else np.array([1.,0.,0.])
        return dict(clearance_m=float(clearances[i, j]), sphere_indices=[int(i), int(j)],
                    links=[self.links[a][i], self.links[b][j]],
                    surface_points=[(world[a][i]+direction*self.radii[a][i]).tolist(),
                                    (world[b][j]-direction*self.radii[b][j]).tolist()],
                    centres=[world[a][i].tolist(), world[b][j].tolist()])

    def arm_budget(self, rid, velocities, age, cfg):
        if cfg.get('stopping_reserve_model')==BODY_RESERVE_MODEL:
            budget=self.body_budget(rid,velocities,age,cfg)
            return float(np.max(budget['total_m'])),float(np.max(budget['speed_m_s']))
        # Joint-space triangle-inequality bounds cover every point in every body.
        v = np.maximum(np.abs(velocities), arm_velocity_limit(cfg,rid))
        radii = self.motion_radii[rid]
        speed = float(np.max(radii @ v))
        braking = float(np.max(radii @ (v*v/(2*cfg['braking_acceleration_rad_s2']))))
        latency = 1/cfg['rate_hz']+age+cfg['stop_latency_s']
        return speed*latency+braking, speed

    def body_budget(self,rid,velocities,age,cfg):
        from .stopping_reserve import body_budgets
        caps=joint_velocity_limits(cfg,rid,len(velocities))
        v=np.asarray(velocities,float).copy()
        for index in getattr(self,'enveloped_dofs',{}).get(rid,()):
            # Only HardwareProblem supplies this proof: the complete opening
            # sweep is already in fixed model-coordinate geometry.
            if v[index]!=0.:raise ValueError('Enveloped tool coordinate must remain fixed in the model')
            caps[index]=0.
        return body_budgets(self.motion_radii[rid],v,caps,age,cfg)

    def pairs(self, positions, velocities, ages, cfg,partial=False):
        world = self.world(positions,partial=partial)
        if cfg.get('stopping_reserve_model')==BODY_RESERVE_MODEL:
            from .stopping_reserve import critical_pair
            budgets={r:self.body_budget(r,velocities[r],ages[r],cfg) for r in world}
            return world,[critical_pair(a,b,world,self.radii,self.links,budgets,cfg)
                for a,b in PAIRS if a in world and b in world]
        budgets = {rid: self.arm_budget(rid, velocities[rid], ages[rid], cfg) for rid in world}
        result = []
        for a, b in PAIRS:
            if a not in world or b not in world:continue
            nearest = self.nearest(world, a, b)
            threshold = cfg['model_margin_m']+budgets[a][0]+budgets[b][0]
            result.append(dict(arms=[a, b], threshold_m=threshold,
                               relative_speed_bound_m_s=budgets[a][1]+budgets[b][1], **nearest))
        return world, result

    def jacobians(self, positions, selected, epsilon=1e-5):
        names = [j for rid in selected for j in self.names[rid][:6]]
        world = self.world(positions)
        jac = {rid: np.zeros((len(points), 3, len(names))) for rid, points in world.items()}
        frames=self.geometry.fk.frames(positions)
        joints={entry[0]:entry for entry in self.geometry.fk.joints}
        for k,name in enumerate(names):
            _,kind,parent,child,fixed,axis,mimic=joints[name]
            transform=frames[parent]@fixed;world_axis=transform[:3,:3]@axis
            rid=next(r for r in selected if name in self.names[r]);index=self.names[rid].index(name)
            mask=self.motion_radii[rid][:,index]>0
            jac[rid][mask,:,k]=np.cross(world_axis,world[rid][mask]-transform[:3,3])
        return world, jac

    def environment_nearest(self,positions,world,jac):
        """Oriented collision-body boxes and floor used for field steering only.

        Full FCL validation remains authoritative, including attached bases.
        Return the nearest movable control point for each environment body.
        """
        frames=self.geometry.fk.frames(positions);terms=[]
        for rid,centres in world.items():
            moving=np.linalg.norm(jac[rid],axis=(1,2))>1e-5
            for body in self.environment:
                T=frames[body.link]@body.fixed
                local=(centres-T[:3,3])@T[:3,:3]
                lo,hi=body.visual_vertices.min(axis=0),body.visual_vertices.max(axis=0)
                nearest=np.clip(local,lo,hi);delta=local-nearest
                distance=np.linalg.norm(delta,axis=1)-self.radii[rid]
                distance[~moving]=np.inf;i=int(np.argmin(distance))
                if not np.isfinite(distance[i]):continue
                normal=T[:3,:3]@delta[i];normal/=max(np.linalg.norm(normal),1e-9)
                terms.append((float(distance[i]),normal,jac[rid][i]))
            distances=centres[:,2]-self.radii[rid]+.003;distances[~moving]=np.inf
            i=int(np.argmin(distances))
            if np.isfinite(distances[i]):terms.append((float(distances[i]),np.array([0.,0.,1.]),jac[rid][i]))
        return terms

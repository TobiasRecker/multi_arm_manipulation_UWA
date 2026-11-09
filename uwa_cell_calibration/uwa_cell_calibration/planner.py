"""Isolated MoveIt planning worker. It has no robot-commanding ROS clients.

Local quintic paths are swept through the complete MoveIt collision scene.
Blocked paths are rejected, never executed via unchecked interpolation.
"""
import multiprocessing as mp
from pathlib import Path
import tempfile
import threading
import time
import traceback

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.stats import qmc

from uwa_cell_gazebo.charuco import table_board_transform, transform
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_gazebo.configuration import joint_names
from .model import CollisionModel


def timed_path(model, rid, start, target, velocity=.10, acceleration=.20, duration=None):
    names = joint_names(rid)
    q0 = np.array([start[j] for j in names])
    delta = np.asarray(target)-q0
    duration = max(duration or 0., 1., 1.875*np.max(abs(delta))/velocity,
                   np.sqrt(5.774*np.max(abs(delta))/acceleration))
    count = max(20, int(np.ceil(duration/.1)), int(np.ceil(np.max(abs(delta))/.005)))
    points = []
    state = dict(start)
    for u in np.linspace(0, 1, count+1):
        s, ds, dds = 10*u**3-15*u**4+6*u**5, 30*u**2-60*u**3+30*u**4, 60*u-180*u**2+120*u**3
        q = q0+s*delta
        state.update(zip(names,q))
        if not model.check(state)[0]:
            raise ValueError(f'{rid}: path intersects collision geometry or exceeds joint limits')
        points.append({'time': float(u*duration), 'positions': q.tolist(),
                       'velocities': (ds*delta/duration).tolist(),
                       'accelerations': (dds*delta/duration**2).tolist()})
    return points


def generate_plan(model, layout, start, matrices, ids, count, progress=lambda value: None):
    if not model.check(start)[0]:
        model.check(start, True)
        raise ValueError('Current full-cell state is in collision; see MoveIt contact log')
    plans = {}
    for rid in ids:
        robot, c = layout['robots'][rid], layout['charuco']
        table = robot['table']
        t = layout['tables'][table]
        world_table = transform(t['xyz'], t['rpy']) @ transform([0,0,t['height']], [0,0,0])
        world_board = world_table @ table_board_transform(c, table)
        centre = world_board @ np.array([c['squares_x']*c['square_length']/2,
                                         c['squares_y']*c['square_length']/2,0,1])
        chain = Chain(model.description, 'world', model.prefix+f'{rid}_wrist_camera_optical_frame')
        camera = chain.forward(start)
        direction = camera[:3,3]-centre[:3]
        radius = np.linalg.norm(direction)
        direction /= radius
        tangent = camera[:3,0] - direction*np.dot(camera[:3,0], direction)
        tangent /= np.linalg.norm(tangent)
        second = np.cross(direction,tangent)
        names = joint_names(rid)
        bounds = np.array([model.bounds[j] for j in names]).T
        current = np.array([start[j] for j in names])
        accepted, rejected = [], 0
        proposals = qmc.Halton(4, scramble=True, seed=64).random(count*20)
        desired = count+max(8,int(np.ceil(count*.2)))
        for index, (a,b,candidate_radius,roll) in enumerate(proposals):
            polar, azimuth = np.radians(18)*np.sqrt(a), 2*np.pi*b
            ray = np.cos(polar)*direction+np.sin(polar)*(np.cos(azimuth)*tangent+np.sin(azimuth)*second)
            eye = centre[:3]+radius*(.9+.2*candidate_radius)*ray
            z = centre[:3]-eye
            z /= np.linalg.norm(z)
            x = camera[:3,0]-z*np.dot(camera[:3,0],z)
            x /= np.linalg.norm(x)
            target = np.eye(4)
            target[:3,:3] = np.column_stack([x,np.cross(z,x),z]) @ Rotation.from_euler('z', (roll-.5)*np.radians(40)).as_matrix()
            target[:3,3] = eye
            bw,bh,margin = layout['charuco']['squares_x']*layout['charuco']['square_length'], layout['charuco']['squares_y']*layout['charuco']['square_length'],layout['charuco']['margin']
            board_camera = np.linalg.inv(target) @ world_board
            corners = np.array([[-margin,-margin,0],[bw+margin,-margin,0],
                                [bw+margin,bh+margin,0],[-margin,bh+margin,0]])
            points = corners @ board_camera[:3,:3].T+board_camera[:3,3]
            k = np.asarray(matrices[rid]['k'])
            projection = points @ k.T
            pixels = projection[:,:2]/projection[:,2:]
            width,height=matrices[rid]['width'],matrices[rid]['height']
            if np.any(points[:,2] <= .1) or not np.all((pixels > [12,12]) & (pixels < [width-12,height-12])):
                rejected += 1
                continue
            def residual(q):
                actual = chain.forward(dict(zip(names,q)))
                return np.r_[actual[:3,3]-target[:3,3], .2*Rotation.from_matrix(actual[:3,:3]@target[:3,:3].T).as_rotvec()]
            fit = least_squares(residual,current,bounds=bounds,max_nfev=80,ftol=1e-8,xtol=1e-8,gtol=1e-8)
            if np.linalg.norm(residual(fit.x)) > 1e-5 or any(np.linalg.norm(fit.x-np.array(p['joints'])) < .08 for p in accepted):
                rejected += 1
                continue
            try:
                state = dict(start)
                state.update(zip(names,current))
                path = timed_path(model,rid,state,fit.x)
            except ValueError:
                rejected += 1
                continue
            accepted.append({'candidate':index,'joints':fit.x.tolist(),'T_world_camera_expected':target.tolist(),
                             'role':'validation' if len(accepted)%5==4 else 'fit', 'path':path})
            current=fit.x
            progress({'robot_id':rid,'accepted':len(accepted),'target':desired,'rejected':rejected})
            if len(accepted) >= desired:
                break
        if len(accepted) < desired:
            raise ValueError(f'{rid}: only {len(accepted)} of {desired} valid poses (including reserve)')
        # Keep the held-out labels, but reduce travel using a deterministic
        # nearest-neighbour route plus 2-opt. Every changed connection is swept again.
        main,reserve=accepted[:count],accepted[count:]
        home=np.array([start[j] for j in names])
        ordered=[];remaining=list(main);q=home
        while remaining:
            chosen=min(remaining,key=lambda p:np.max(abs(np.asarray(p['joints'])-q)))
            remaining.remove(chosen);ordered.append(chosen);q=np.asarray(chosen['joints'])
        def cost(a,b):return np.max(abs(a-b))
        for _ in range(5):
            improved=False
            for i in range(count-1):
                for j in range(i+1,count):
                    a=home if i==0 else np.asarray(ordered[i-1]['joints'])
                    b=np.asarray(ordered[i]['joints']);cc=np.asarray(ordered[j]['joints'])
                    d=home if j==count-1 else np.asarray(ordered[j+1]['joints'])
                    if cost(a,cc)+cost(b,d)+1e-8 < cost(a,b)+cost(cc,d):
                        ordered[i:j+1]=reversed(ordered[i:j+1]);improved=True
            if not improved:break
        state=dict(start)
        for p in ordered:
            p['path']=timed_path(model,rid,state,p['joints']);state.update(zip(names,p['joints']))
        from .solver import diverse
        tool_chain=Chain(model.description,model.prefix+f'{rid}_base_link',model.prefix+f'{rid}_tool0')
        singular=diverse([{'T_base_tool0':tool_chain.forward(dict(zip(names,p['joints']))).tolist()}
                         for p in ordered if p['role']=='fit'])
        accepted=ordered+reserve
        # Return paths are checked from the final main and reserve targets.
        for p in (accepted[count-1],accepted[-1]):
            state=dict(start);state.update(zip(names,p['joints']))
            timed_path(model,rid,state,[start[j] for j in names])
        plans[rid]={'poses':accepted[:count],'reserve':accepted[count:],
                    'rotation_singular_values':singular,
                    'rejected_candidates':rejected,'start_joints':[start[j] for j in names]}
    return plans


def worker(connection, description, directory):
    try:
        model = CollisionModel(description,directory)
        connection.send({'ready':True})
        while True:
            request=connection.recv()
            try:
                if request['op']=='prepare':
                    from .diagonal import prepare_schedule
                    result=prepare_schedule(model,request['layout'],request['start'],request['matrices'],
                                            request['robots'],request['count'],request.get('diagonal_pairs',True),
                                            lambda p:connection.send({'progress':p}))
                elif request['op']=='paths':
                    from .diagonal import coordinated_paths
                    result=coordinated_paths(model,request['start'],request['targets'])
                elif request['op']=='path':
                    result=timed_path(model,request['robot'],request['start'],request['target'])
                elif request['op']=='solve':
                    from .solver import solve_session
                    result=solve_session(request['records'])
                elif request['op']=='check':
                    result=model.check(request['positions'])[0]
                else:
                    raise ValueError('Unknown planning operation')
                connection.send({'result':result})
            except Exception as error:
                connection.send({'error':str(error),'traceback':traceback.format_exc()})
    except (EOFError,BrokenPipeError):
        pass
    except Exception as error:
        try:connection.send({'error':str(error)})
        except (EOFError,BrokenPipeError):pass


class PlanningProcess:
    def __init__(self, description, directory):
        self.description,self.directory=description,str(directory)
        self.process=None
        self.lock=threading.Lock()

    def call(self, request, cancelled=lambda:False, progress=lambda value:None):
        with self.lock:
            if self.process is None or not self.process.is_alive():
                ctx=mp.get_context('spawn')
                self.connection,child=ctx.Pipe()
                self.process=ctx.Process(target=worker,args=(child,self.description,self.directory),daemon=True)
                self.process.start();child.close()
                while not self.connection.poll(.1):
                    if cancelled():self.cancel();raise InterruptedError('Planning cancelled')
                    if not self.process.is_alive():raise RuntimeError('MoveIt worker exited')
                ready=self.connection.recv()
                if not ready.get('ready'):raise RuntimeError(ready.get('error','Worker initialization failed'))
            self.connection.send(request)
            while True:
                if cancelled():self.cancel();raise InterruptedError('Planning cancelled')
                if not self.connection.poll(.1):
                    if not self.process.is_alive():raise RuntimeError('MoveIt worker exited')
                    continue
                response=self.connection.recv()
                if 'progress' in response:progress(response['progress']);continue
                if 'error' in response:raise RuntimeError(response['error'])
                return response['result']

    def cancel(self):
        if self.process is not None:
            if self.process.is_alive():self.process.terminate();self.process.join(timeout=.5)
            self.process=None

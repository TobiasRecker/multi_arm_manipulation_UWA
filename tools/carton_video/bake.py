"""Bake the archived controller references to deterministic 15 Hz visual poses."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.spatial.transform import Rotation


def transform(xyz=(0, 0, 0), rpy=(0, 0, 0)):
    t = np.eye(4)
    t[:3, :3] = Rotation.from_euler('xyz', rpy).as_matrix()
    t[:3, 3] = xyz
    return t


def pose(t):
    return [*t[:3, 3].tolist(), *Rotation.from_matrix(t[:3, :3]).as_quat().tolist()]


def sdf_pose(node):
    v = np.fromstring(node.findtext('pose', '0 0 0 0 0 0'), sep=' ')
    return transform(v[:3], v[3:])


def label(name):
    if name.startswith('draw_z_min_edge'):
        return 'Draw the house', 'DRAW', 'z_min'
    if name.startswith('axial_') or name.startswith('transit_z_min_site'):
        return 'Six virtual drilling positions', 'DRILL', 'z_min'
    if name == 'draw_bottom_circle':
        return 'Draw the bottom circle', 'DRAW', 'z_min'
    if name == 'draw_y_max':
        return 'Draw the near-side circle', 'DRAW', 'y_max'
    if name == 'draw_y_min':
        return 'Draw by moving the carton', 'DRAW', 'y_min'
    if name in ('present_z_min', 'return_from_z_min'):
        return 'Coordinated carton rotation', 'ROTATE', 'z_min'
    if name in ('present_y_min', 'return_from_y_min'):
        return 'Present the opposite side', 'ROTATE', 'y_min'
    if name == 'lift':
        return 'Lift the carton together', 'LIFT', 'y_max'
    if name == 'set_down':
        return 'Place the carton on the table', 'PLACE', 'y_max'
    if name in ('approach', 'entry', 'close', 'home'):
        return {'home': 'Ready in home position', 'approach': 'Approach together',
                'entry': 'Enter the grasp', 'close': 'Close both grippers'}[name], 'GRASP', 'y_max'
    if name == 'open':
        return 'Open both grippers', 'RELEASE', 'y_max'
    if name == 'complete':
        return 'Cycle complete', 'COMPLETE', 'y_max'
    if 'bottom_circle' in name or 'z_min' in name:
        return 'Position the drawing tool', 'POSITION', 'z_min'
    if 'y_min' in name:
        return 'Position for the opposite side', 'POSITION', 'y_min'
    return 'Position the drawing tool', 'POSITION', 'y_max'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path('/input'))
    p.add_argument('--output', type=Path, default=Path('/output'))
    p.add_argument('--fps', type=int, default=15)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    root = ET.parse(a.input / 'robot.urdf').getroot()
    materials = {m.get('name'): m for m in root.findall('material')}
    joints = []
    for j in root.findall('joint'):
        origin = j.find('origin')
        t = transform(np.fromstring(origin.get('xyz', '0 0 0'), sep=' '),
                      np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')) if origin is not None else np.eye(4)
        axis = j.find('axis')
        joints.append((j.get('name'), j.get('type'), j.find('parent').get('link'),
                       j.find('child').get('link'), t,
                       np.fromstring(axis.get('xyz'), sep=' ') if axis is not None else np.array([1., 0, 0])))

    def fk(q):
        result = {'world': np.eye(4)}
        pending = list(joints)
        while pending:
            later = []
            for name, kind, parent, child, t, axis in pending:
                if parent not in result:
                    later.append((name, kind, parent, child, t, axis))
                    continue
                m = np.eye(4)
                if kind in ('revolute', 'continuous'):
                    m[:3, :3] = Rotation.from_rotvec(axis * q.get(name, 0.)).as_matrix()
                elif kind == 'prismatic':
                    m[:3, 3] = axis * q.get(name, 0.)
                result[child] = result[parent] @ t @ m
            if len(later) == len(pending):
                raise ValueError('Unresolved URDF tree')
            pending = later
        return result

    nodes, visuals = [], []

    def add_visual(v, parent, t, urdf=False):
        geom = v.find('geometry')
        shape = list(geom)[0]
        d = {'parent': parent, 'pose': pose(t), 'shape': shape.tag}
        if shape.tag == 'mesh':
            d['mesh'] = shape.get('filename') if urdf else shape.findtext('uri')
            d['scale'] = list(np.fromstring(shape.get('scale', '1 1 1') if urdf else shape.findtext('scale', '1 1 1'), sep=' '))
        elif shape.tag == 'box':
            d['scale'] = list(np.fromstring(shape.get('size') if urdf else shape.findtext('size'), sep=' '))
        elif shape.tag in ('cylinder', 'sphere'):
            radius = float(shape.get('radius') if urdf else shape.findtext('radius'))
            length = float(shape.get('length') if urdf else shape.findtext('length')) if shape.tag == 'cylinder' else 2 * radius
            d['scale'] = [2 * radius, 2 * radius, length]
        else:
            raise ValueError('Unsupported visual ' + shape.tag)
        material = v.find('material')
        if material is not None:
            color = material.find('color')
            if urdf and color is None:
                ref = materials.get(material.get('name'))
                if ref is not None:
                    color = ref.find('color')
            rgba = color.get('rgba') if color is not None else material.findtext('diffuse')
            if rgba is not None:
                d['color'] = list(np.fromstring(rgba, sep=' '))
        visuals.append(d)

    for link in root.findall('link'):
        if not link.findall('visual'):
            continue
        name = link.get('name')
        nodes.append(name)
        for v in link.findall('visual'):
            origin = v.find('origin')
            t = transform(np.fromstring(origin.get('xyz', '0 0 0'), sep=' '), np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')) if origin is not None else np.eye(4)
            add_visual(v, name, t, True)
    nodes += ['carton', 'pen']
    carton = ET.parse(a.input / 'carton.sdf').getroot().find('model')
    for link in carton.findall('link'):
        for v in link.findall('visual'):
            add_visual(v, 'carton', sdf_pose(link) @ sdf_pose(v))
    for model in ET.parse(a.input / 'world.sdf').findall('.//world/model'):
        for link in model.findall('link'):
            for v in link.findall('visual'):
                add_visual(v, 'world', sdf_pose(model) @ sdf_pose(link) @ sdf_pose(v))
    # A visible virtual tool, matching the archived 300 mm tool reference.
    visuals += [{'parent': 'pen', 'pose': [0, 0, .215, 0, 0, 0, 1],
                 'shape': 'cylinder', 'scale': [.008, .008, .158], 'color': [.94, .95, .98, 1]},
                {'parent': 'pen', 'pose': [0, 0, .297, 0, 0, 0, 1],
                 'shape': 'cylinder', 'scale': [.004, .004, .006], 'color': [.13, .17, .21, 1]}]
    visuals.append({'parent': 'world', 'pose': [0, 0, -.025, 0, 0, 0, 1],
                    'shape': 'box', 'scale': [200, 200, .05], 'color': [.22, .26, .31, 1]})

    plan = json.loads((a.input / 'plan.json').read_text())
    group = json.loads((a.input / 'group.json').read_text())
    history = json.loads((a.input / 'state.json').read_text())['history']
    phases = []

    def trajectory(name, d):
        ts = np.array([r['time'] for r in d['points']])
        qs = np.array([r['positions'] for r in d['points']])
        vs = np.array([r.get('velocities', [0.] * len(d['joint_names'])) for r in d['points']])
        phases.append((name, d['duration_s'], d['joint_names'], CubicHermiteSpline(ts, qs, vs)))

    phases.append(('home', 2., [], None))
    trajectory('approach', plan['trajectory'])
    trajectory('entry', plan['entry'])
    phases.append(('close', 2., [], None))
    phase_names = []
    for event in history:
        name = event.get('step')
        if name and (a.input / 'trajectories' / (name + '.json')).exists() and name not in phase_names:
            phase_names.append(name)
    # Lift / set-down are stored separately from named move_object history events.
    if 'lift' not in phase_names:
        phase_names.insert(0, 'lift')
    if 'set_down' not in phase_names:
        phase_names.append('set_down')
    available = {x.stem for x in (a.input / 'trajectories').glob('*.json')}
    if set(phase_names) != available:
        raise ValueError(f'Missing archived phases: {available - set(phase_names)}')
    for name in phase_names:
        trajectory(name, json.loads((a.input / 'trajectories' / (name + '.json')).read_text()))
    phases += [('open', 2., [], None), ('complete', 4., [], None)]
    q = dict(plan['request']['start'])
    hold_inv = np.linalg.inv(np.array(group['object_to_tcp']['right_front']))
    lift = json.loads((a.input / 'trajectories/lift.json').read_text())
    lift_q = q | dict(zip(lift['joint_names'], lift['points'][0]['positions']))
    initial_carton = fk(lift_q)['right_front_tool0'] @ hold_inv
    frames, traces, chapters = [], [], []
    elapsed = 0.
    last_tip = None
    last_phase = None
    grip_error = 0.
    for name, duration, names, curve in phases:
        title, mode, face = label(name)
        chapters.append({'phase': name, 'title': title, 'source_time_s': elapsed, 'video_time_s': elapsed / 2})
        count = max(1, int(np.ceil((elapsed + duration) * a.fps)) - len(frames))
        for _ in range(count):
            t = min(duration, max(0., len(frames) / a.fps - elapsed))
            if curve is not None:
                q.update(zip(names, map(float, curve(t))))
            finger = .72 if name not in ('home', 'approach', 'entry') else 0.
            if name == 'close':
                finger *= t / duration
            elif name == 'open':
                finger *= 1 - t / duration
            elif name == 'complete':
                finger = 0.
            for arm in ('right_front', 'right_rear'):
                for key in q:
                    if key.startswith(arm + '_robotiq'):
                        # Same ideal mimic signs as the visual URDF.
                        right = '_right_' in key
                        tip_joint = 'finger_tip_joint' in key
                        q[key] = finger * (-1 if right != tip_joint else 1)
            transforms = fk(q)
            carrying = name not in ('home', 'approach', 'entry', 'close')
            obj = transforms['right_front_tool0'] @ hold_inv if carrying else initial_carton
            if carrying and name not in ('open', 'complete'):
                second = transforms['right_rear_tool0'] @ np.linalg.inv(np.array(group['object_to_tcp']['right_rear']))
                grip_error = max(grip_error, float(np.linalg.norm(obj[:3, 3] - second[:3, 3])))
            pen = transforms['left_front_tool0']
            tip = (pen @ [0, 0, .3, 1])[:3]
            local = (np.linalg.inv(obj) @ [*tip, 1])[:3]
            normal = np.array({'y_max': [0, 1, 0], 'y_min': [0, -1, 0], 'z_min': [0, 0, -1]}[face])
            if name.startswith('draw_'):
                point = local + normal * .002
                if last_phase == name and last_tip is not None and np.linalg.norm(point - last_tip) > 1e-6:
                    traces.append({'a': last_tip.tolist(), 'b': point.tolist(), 'red': False, 'born': len(frames)})
                last_tip = point
            elif name.startswith('axial_feed_') and last_phase != name:
                traces.append({'a': (local + normal * .002).tolist(),
                               'b': (local + normal * .014).tolist(), 'red': True, 'born': len(frames)})
                last_tip = None
            else:
                last_tip = None
            last_phase = name
            transforms['carton'], transforms['pen'] = obj, pen
            frames.append({'time': len(frames) / a.fps, 'phase': name, 'title': title, 'mode': mode,
                           'face': face, 'object': pose(obj), 'tip': tip.tolist(),
                           'poses': [pose(transforms[n]) for n in nodes]})
        if curve is not None:
            q.update(zip(names, map(float, curve(duration))))
        elapsed += duration
    if grip_error > .002:
        raise ValueError(f'Archived grasp closure mismatch: {grip_error} m')
    data = {'nodes': nodes, 'visuals': visuals, 'frames': frames, 'traces': traces,
            'fps': a.fps, 'duration': len(frames) / a.fps, 'chapters': chapters,
            'grasp_closure_max_m': grip_error, 'archived_motion_phases': len(phase_names)}
    (a.output / 'movie.json').write_text(json.dumps(data, separators=(',', ':')))
    print(json.dumps({k: data[k] for k in ('duration', 'grasp_closure_max_m', 'archived_motion_phases')}), flush=True)
    print(f'Baked {len(frames)} unique states, {len(traces)} trace segments', flush=True)


if __name__ == '__main__':
    main()

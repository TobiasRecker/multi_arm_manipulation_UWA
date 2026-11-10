"""Command-free, full-cell MoveIt collision checking for single-arm parking.

Only checked local quintic connections are accepted. This is not an OMPL
obstacle-detour planner, nor a claim of calibrated real-cell geometry.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_gazebo.configuration import ROBOT_IDS, joint_names, render_description
from uwa_cell_calibration.model import CollisionModel
from uwa_cell_calibration.planner import timed_path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def six(values):
    q = np.asarray(values, dtype=float)
    if q.shape != (6,) or not np.isfinite(q).all():
        raise ValueError('Expected six finite joint angles')
    return q.tolist()


def manual_states(path):
    """Explicit pendant readings; never silently interpret degrees as radians."""
    data = json.loads(Path(path).read_text()) if path else {}
    if set(data) - set(ROBOT_IDS):
        raise ValueError('Unknown arm in manual states')
    result = {}
    for rid, record in data.items():
        if record.get('unit') not in ('deg', 'rad'):
            raise ValueError(f'{rid}: manual state requires unit deg or rad')
        q = six(record['positions'])
        if record['unit'] == 'deg':
            q = np.radians(q).tolist()
        result[rid] = {'positions': q, 'source': 'manual_pendant',
                       'recorded_at': record.get('recorded_at', 'not supplied')}
    return result


def complete_state(layout, readings):
    """Missing arms may be drawn, but can never make an executable plan."""
    start, sources, missing = {}, {}, []
    if set(readings) - set(ROBOT_IDS):
        raise ValueError('Unknown arm in state snapshot')
    for rid in ROBOT_IDS:
        record = readings.get(rid)
        if record:
            values = six(record['positions'])
            source = record['source']
            if source not in ('live_joint_states', 'manual_pendant', 'mock_joint_states'):
                raise ValueError(f'{rid}: unsupported state provenance {source}')
        else:
            values = six(layout['robots'][rid]['initial_positions'])
            source = 'UNOBSERVED_LAYOUT_PREVIEW'
            missing.append(rid)
        start.update(zip(joint_names(rid), values))
        sources[rid] = source
    return start, sources, missing


def make_model(layout, profiles, directory):
    layout = deepcopy(layout)
    for rid, profile in profiles.items():
        layout['robots'][rid]['type'] = profile['ur_type']
        layout['robots'][rid]['kinematics_file'] = profile['kinematics_file']
    description = render_description(layout, directory)[0]
    return CollisionModel(description, Path(directory)/'moveit'), layout


def plan_parking(model, layout, rid, start, *, target=None, velocity=.05,
                 acceleration=.10):
    """Find an outward, raised pose, then sweep the entire connecting path."""
    if rid not in ROBOT_IDS:
        raise ValueError('Unknown arm')
    if not 0 < velocity <= .10 or not 0 < acceleration <= .20:
        raise ValueError('Parking limits: velocity <=0.10 rad/s, acceleration <=0.20 rad/s²')
    if not model.check(start)[0]:
        model.check(start, contacts=True)
        raise ValueError('Full-cell start state is in collision or outside limits; no path generated')
    names = joint_names(rid)
    q0 = np.array([start[j] for j in names])
    chain = Chain(model.description, 'world', f'{rid}_tool0')
    base = Chain(model.description, 'world', f'{rid}_base_link').forward({})[:3, 3]
    centres = {t: Chain(model.description, 'world', t+'_table_top').forward({})[:3, 3]
               for t in layout['tables']}
    direction = centres[layout['robots'][rid]['table']] - np.mean(list(centres.values()), axis=0)
    direction[2] = 0
    if np.linalg.norm(direction) < 1e-6:
        raise ValueError('Cannot derive outward parking direction from coincident table centres')
    direction /= np.linalg.norm(direction)
    bounds = np.array([model.bounds[j] for j in names]).T
    candidates = []
    if target is not None:
        candidates.append((six(target), None))
    else:
        # No arbitrary wrist orientation: prefer minimal change from measured start.
        for offset, height in product((.30, .40, .25), (.50, .65)):
            desired = base + direction*offset + [0, 0, height]
            def residual(q):
                actual = chain.forward(dict(zip(names, q)))[:3, 3]
                return np.r_[actual-desired, .015*(q-q0)]
            for yaw in (0., .5, -.5):
                seed = np.clip(q0 + [yaw, 0, 0, 0, 0, 0], bounds[0]+1e-6, bounds[1]-1e-6)
                fit = least_squares(residual, seed, bounds=bounds, max_nfev=140)
                if np.linalg.norm(residual(fit.x)[:3]) <= .025:
                    candidates.append((fit.x.tolist(), desired.tolist()))
    accepted = []
    for q, desired in candidates:
        try:
            path = timed_path(model, rid, start, q, velocity=velocity, acceleration=acceleration)
        except ValueError:
            continue
        accepted.append((path[-1]['time'], q, desired, path))
    if not accepted:
        raise ValueError('No checked direct parking path found. Change the target or add a reviewed waypoint; no unchecked detour.')
    duration, q, desired, path = min(accepted, key=lambda p: p[0])
    poses = [chain.forward(dict(start, **dict(zip(names, p['positions']))))[:3, 3].tolist()
             for p in path]
    return {'arm': rid, 'joint_names': names, 'start': start, 'target': q, 'points': path,
            'duration': duration, 'tool_path_world': poses, 'desired_tool_world': desired,
            'velocity_limit': velocity, 'acceleration_limit': acceleration,
            'method': 'MoveIt full-cell collision sweep of local quintic joint path',
            'collision_samples': len(path), 'max_joint_sample_step_rad': .005}


def save_plan(directory, plan, model, layout, profiles, sources, missing, mode):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    plan = dict(plan, schema_version=1, mode=mode, ros_domain=67 if mode=='mock' else 66,
                created_at=datetime.now(timezone.utc).isoformat(), state_sources=sources,
                unobserved_arms=missing, executable=not missing,
                layout=layout, inventory_fingerprint=digest(profiles),
                description=model.description,
                limitations=['Table/base/tool geometry is provisional, not a calibrated real-cell map.',
                             'No people, loose objects or unmodelled fixtures are perceived.',
                             'Manual pendant readings require the corresponding arms to remain stationary.'])
    # Hash ties the trajectory to its state/model/provenance, not just its target.
    plan['fingerprint'] = digest(plan)
    (directory/'plan.json').write_text(json.dumps(plan, indent=2, allow_nan=False)+'\n')
    write_preview(plan, directory/'preview.png')
    return plan


def validate_artifact(plan, profiles):
    original = dict(plan)
    fingerprint = original.pop('fingerprint', None)
    if fingerprint != digest(original):
        raise ValueError('Plan fingerprint changed; generate a new checked plan')
    if plan.get('schema_version') != 1 or plan.get('mode') not in ('mock', 'hardware'):
        raise ValueError('Unsupported parking plan')
    if plan['inventory_fingerprint'] != digest(profiles):
        raise ValueError('Inventory changed; regenerate the plan')
    if not plan['executable'] or plan['unobserved_arms']:
        raise ValueError('Preview only: missing real/manual states for '+', '.join(plan['unobserved_arms']))
    expected = 67 if plan['mode']=='mock' else 66
    if plan['ros_domain'] != expected:
        raise ValueError('Plan ROS domain/mode mismatch')
    rid = plan['arm']
    if plan['joint_names'] != joint_names(rid):
        raise ValueError('Plan joint identity mismatch')
    # Mock provenance can never be used as a measured hardware obstacle state.
    if plan['mode']=='hardware' and any(s=='mock_joint_states' for s in plan['state_sources'].values()):
        raise ValueError('Mock states cannot authorize a hardware path')


def write_preview(plan, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 2, figsize=(13, 6))
    chain = {r: [Chain(plan['description'], 'world', r+'_'+link) for link in
                 ('base_link', 'shoulder_link', 'upper_arm_link', 'forearm_link',
                  'wrist_1_link', 'wrist_2_link', 'wrist_3_link', 'tool0')]
             for r in ROBOT_IDS}
    end = dict(plan['start'], **dict(zip(plan['joint_names'], plan['target'])))
    for ax, (a, b), title in zip(axes, ((0, 1), (0, 2)), ('Top (X/Y)', 'Front (X/Z)')):
        for table in plan['layout']['tables'].values():
            # Lines from the actual table frame also support non-zero table yaw.
            from uwa_cell_gazebo.charuco import transform
            t = transform(table['xyz'], table['rpy'])
            w, l, z = table['width']/2, table['length']/2, table['height']
            points = np.array([[-w,-l,z],[w,-l,z],[w,l,z],[-w,l,z],[-w,-l,z]])
            points = points @ t[:3,:3].T+t[:3,3]
            ax.plot(points[:, a], points[:, b], color='gray')
        for rid, links in chain.items():
            points = np.array([c.forward(plan['start'])[:3, 3] for c in links])
            unknown = rid in plan['unobserved_arms']
            ax.plot(points[:, a], points[:, b], 'o--' if unknown else 'o-',
                    color='#999999' if unknown else '#3c596b', alpha=.6,
                    label=rid+(' UNOBSERVED' if unknown else ' start'))
            if rid==plan['arm']:
                points = np.array([c.forward(end)[:3, 3] for c in links])
                ax.plot(points[:, a], points[:, b], 'o-', color='#bb3a00', label=rid+' target')
        points = np.array(plan['tool_path_world'])
        ax.plot(points[:, a], points[:, b], color='#bd8500', linewidth=2, label='tool0 path')
        ax.set_title(title);ax.set_xlabel('X [m]');ax.set_ylabel(('Y' if b==1 else 'Z')+' [m]')
        ax.axis('equal');ax.grid(True, alpha=.3)
    axes[0].legend(fontsize=8)
    warning = 'PREVIEW ONLY: unobserved '+', '.join(plan['unobserved_arms']) if plan['unobserved_arms'] else 'Checked model path; physical geometry remains provisional'
    figure.suptitle(f"{plan['arm']} parking · {plan['duration']:.1f} s · {warning}", fontsize=12)
    figure.text(.5, .015, 'Joint-chain sketch only. Use the RViz animation for full robot/tool geometry. No real motion is sent.', ha='center', fontsize=9)
    figure.tight_layout(rect=(0,.04,1,.94));figure.savefig(path, dpi=150);plt.close(figure)

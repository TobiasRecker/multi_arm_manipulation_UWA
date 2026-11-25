"""Export a self-contained playback of the wood-frame kinematic plan."""

from base64 import b64encode
from itertools import product
import json
from numbers import Real
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from uwa_cell_description.configuration import ROBOT_IDS, gripper_joint, joint_names
from uwa_cell_motion.geometry import SphereModel
from .core import plain


TEMPLATE = Path(__file__).resolve().parents[2] / 'tools/wood_frame_viewer.html'
PHASE_LABELS = {
    'localize': 'Locate the crossbar and posts',
    'approach': 'Approach the crossbar',
    'high_approach': 'Move both grippers above the crossbar',
    'open_entry': 'Lower the open grippers',
    'grasp': 'Close both grippers',
    'lift': 'Lift the crossbar',
    'transfer': 'Carry the crossbar and approach with the screwdriver',
    'carry': 'Carry the crossbar while the screwdriver approaches',
    'place': 'Center the crossbar on the joints',
    'seat': 'Center and seat the crossbar',
    'axial_approach': 'Approach',
    'axial_feed': 'Drive the virtual screw',
    'axial_retract': 'Retract the screwdriver',
    'tool_retreat': 'Clear the assembly with the screwdriver',
    'fasten': 'Set virtual joints',
    'release': 'Release the mounted crossbar',
    'lift_clear': 'Lift the open grippers clear',
    'retreat': 'Retreat from the assembled frame',
}


def _model(description):
    joints = {joint.attrib['name'] for joint in ET.fromstring(description).findall('joint')}
    names = {arm: joint_names(arm) + ([gripper_joint(arm)] if gripper_joint(arm) in joints else [])
             for arm in ROBOT_IDS}
    return SphereModel(description, names, spacing=.065)


def _table_boxes(model, state):
    frames = model.geometry.fk.frames(state)
    boxes = []
    for body in model.environment:
        if body.kind != 'box' or not (body.link.endswith('_table_plate') or '_leg_' in body.link):
            continue
        half = np.abs(body.vertices).max(axis=0)
        corners = np.asarray(list(product(*[(-extent, extent) for extent in half])))
        pose = frames[body.link] @ body.fixed
        boxes.append((corners @ pose[:3, :3].T + pose[:3, 3]).round(5).tolist())
    return boxes


def _phase_label(phase, screw):
    if phase.get('label'):
        return phase['label']
    kind = phase['kind']
    if screw:
        return f"{PHASE_LABELS.get(kind, kind.replace('_', ' ').capitalize())} · {screw['label']}"
    return PHASE_LABELS.get(phase['id'], phase['id'].replace('_', ' ').capitalize())


def _sample_indices(times):
    """Keep boundaries plus existing model samples at a bounded display rate."""
    if len(times) < 2:
        return [0]
    buckets = np.linspace(times[0], times[-1], min(96, int(np.ceil((times[-1] - times[0]) * 10)) + 1))
    indices = np.searchsorted(times, buckets, side='left')
    return sorted({0, len(times) - 1, *indices.tolist()})


def _frame(model, state, scene, *, time, phase, beam, screw, fastened):
    positions, _ = model.planning_world(state)
    tool = scene['tool']
    mount = model.geometry.fk.frames(state)[f"{tool['arm']}_tool0"]
    tip = mount @ np.asarray(tool['tool0_to_tip'])
    body = []
    if 'body_start_m' in tool and 'body_end_m' in tool:
        axis = tip[:3, 3] - mount[:3, 3]
        axis /= np.linalg.norm(axis)
        body = [(mount[:3, 3] + axis * tool[key]).round(5).tolist()
                for key in ('body_start_m', 'body_end_m')]
    return dict(time_s=round(float(time), 8), phase=phase, pose=beam, screw=screw,
                fastened=list(fastened), tool_base=mount[:3, 3].round(5).tolist(),
                tool_tip=tip[:3, 3].round(5).tolist(), tool_body=body,
                world={arm: points.round(5).tolist() for arm, points in positions.items()})


def _trajectory(plan, scene, model, screws):
    frames = []
    phases = []
    fastened = []
    elapsed = 0.
    state = {name: 0. for names in model.names.values() for name in names}
    start = dict(state)
    screw_by_id = {screw['id']: screw for screw in screws}
    holder_fingers = [gripper_joint(arm) for arm in scene['holders']]
    names = plan['joint_names']
    for phase in plan['phases']:
        times = np.asarray(phase['time_s'], float)
        if not len(times):
            continue
        phase_id = phase['id']
        screw_id = phase.get('screw_id')
        phases.append(dict(id=phase_id, label=_phase_label(phase, screw_by_id.get(screw_id)),
                           start_s=round(elapsed, 8)))
        fingers = phase.get('gripper_positions')
        for i in _sample_indices(times):
            state.update(zip(names, phase['positions'][i], strict=True))
            if fingers is not None:
                state.update(dict.fromkeys(holder_fingers, float(fingers[i])))
            if not frames:
                start = dict(state)
            if screw_id and phase['kind'] == 'axial_feed' and i == len(times) - 1:
                fastened.append(screw_id)
            frames.append(_frame(model, state, scene, time=elapsed+times[i], phase=phase_id,
                                 beam=phase['beam_poses'][i], screw=screw_id, fastened=fastened))
        elapsed += float(times[-1])
    if not frames:
        initial = plan.get('initial_state')
        if initial:
            start.update(initial)
            frames.append(_frame(model, start, scene, time=0., phase='initial',
                                 beam=scene['beam']['start_pose'], screw=None, fastened=[]))
        else:
            frames.append(dict(time_s=0., phase='initial', pose=scene['beam']['start_pose'],
                               world={}, screw=None, fastened=[]))
        phases.append(dict(id='initial', label='Initial scene', start_s=0.))
    return phases, frames, round(elapsed, 8), start


def _image(path, label):
    path = Path(path)
    media_type = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}[path.suffix.lower()]
    return dict(label=label, src=f'data:{media_type};base64,{b64encode(path.read_bytes()).decode()}')


def _localization(observation, directory, overlay):
    if not observation:
        return None
    description = 'Synthetic camera image in the browser model.'
    camera = observation.get('camera')
    if camera:
        description += f' Pose fitted from {camera}.'
    residuals = [fit['rms_px'] for fit in observation.get('residuals', {}).values() if 'rms_px' in fit]
    if residuals:
        description += f' The largest fit RMS is {max(residuals):.2f} px.'
    if observation.get('reason'):
        description += ' ' + observation['reason']
    image = observation.get('image')
    selected_dir = (directory / image).parent if image else directory
    images = []
    for filename, label in [(image, 'Camera image'),
                            (overlay or observation.get('overlay'), 'Pose fit overlay')]:
        if filename and (directory / filename).is_file():
            images.append(_image(directory / filename, f'{camera} · {label}' if camera else label))
    notes = []
    for name, view in observation.get('views', {}).items():
        if name == camera:
            continue
        if view.get('reason'):
            notes.append(f"{name} · {view['reason']}")
        for key, label in [('image', 'Camera image'), ('overlay', 'Pose fit overlay')]:
            filename = view.get(key)
            if not filename or (key == 'overlay' and view.get('status') != 'VALID'):
                continue
            path = directory / filename
            if not path.is_file():
                path = selected_dir / filename
            if path.is_file():
                images.append(_image(path, f'{name} · {label}'))
    return dict(description=description, images=images, notes=notes)


def _metrics(audit):
    values = []
    for key, label, factor, unit, precision in (
        ('samples', 'Checked samples', 1, '', 0),
        ('arm_pairs_checked', 'Arm pairs', 1, '', 0),
        ('three_arm_overlap_s', 'Concurrent motion', 1, ' s', 2),
        ('seating_error_m', 'Seating error', 1000, ' mm', 2),
        ('max_grasp_position_error_m', 'Grip position error', 1000, ' mm', 2),
        ('min_arm_gap_m', 'Smallest arm gap', 1000, ' mm', 1),
        ('min_arm_clearance_m', 'Smallest arm clearance', 1000, ' mm', 1),
        ('max_joint_speed_rad_s', 'Peak joint speed', 1, ' rad/s', 3),
        ('center_offset_m', 'Center offset', 1000, ' mm', 2),
    ):
        value = audit.get(key)
        if isinstance(value, Real) and not isinstance(value, bool) and np.isfinite(value):
            values.append([label, f'{factor*value:.{precision}f}{unit}'])
    return values


def export_viewer(plan, description, output, *, observation_overlay=None):
    """Write an offline HTML file from a compiled plan and its rendered URDF."""
    output = Path(output)
    scene = plan['scene']
    model = _model(description)
    screws = [dict(screw, label=screw['id'].replace('_', ' ').capitalize()) for screw in scene['screws']]
    phases, frames, elapsed, start = _trajectory(plan, scene, model, screws)
    target = np.asarray(scene['beam']['target_pose'])[:3, 3]
    direction = screws[0]['direction'] if screws else [0., 1., 0.]
    status = plan['status']
    complete = status == 'MODEL_SEQUENCE_COMPLETE'
    label = 'Model sequence complete' if complete else status.replace('_', ' ').capitalize()
    reason = plan.get('reason') or plan.get('failure')
    if isinstance(reason, dict):
        reason = reason.get('reason') or json.dumps(reason, ensure_ascii=False)
    payload = dict(complete=complete, result_label=label, failure=reason, phases=phases,
                   frames=frames, duration_s=elapsed, screws=screws, view_center_m=[0., 0., 1.05],
                   joint_view_center_m=target.tolist(),
                   joint_view_yaw_rad=float(np.arctan2(-direction[0], -direction[1])),
                   uprights=scene['posts'], tables=_table_boxes(model, start),
                   crossbar_size_m=scene['beam']['size_m'], holders=scene['holders'], worker=scene['tool']['arm'],
                   tool_radii_m={key: scene['tool'].get(f'{key}_radius_m', default)
                                 for key, default in [('shaft', .006), ('body', .02)]},
                   radii={name: values.round(6).tolist() for name, values in model.radii.items()},
                   metrics=_metrics(plan.get('audit') or {}), policy=plan.get('policy'),
                   localization=_localization(plan.get('observation'), output.parent, observation_overlay))
    data = json.dumps(payload, ensure_ascii=True, allow_nan=False, default=plain,
                      separators=(',', ':')).replace('<', '\\u003c')
    text = TEMPLATE.read_text(encoding='utf-8').replace('__DATA__', data)
    temporary = output.with_suffix('.html.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(output)
    return output

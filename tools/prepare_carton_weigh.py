#!/usr/bin/env python3
"""File-only two-arm vertical lift. No ROS node, device connection or safety changes."""
import argparse
import itertools
import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.interpolate import BPoly
from uwa_cell_calibration.model import CollisionModel, set_origin
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_motion.common import dump, joint_names
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.carton_paths import cartesian_entry, evaluate, quintic
from uwa_cell_tasks.reviewed_carton import (speed_envelope, retime, prove_group, write_bundle,
    preview_model, file_hash, check_boundaries)
from uwa_cell_tasks.timing import interpolation_peaks
from prepare_carton_open_entry import shell_boxes

REPO = Path(__file__).resolve().parents[1]
ARMS = ('right_front', 'right_rear')
HEIGHT = .020
LIFT_JOINT = 'weigh_carton_vertical'


def moving_carton(problem, pose, scene, directory):
    """Nominal grasp geometry, separate from the unchanged full-opening cell proof."""
    root = ET.fromstring(problem.description)
    original = ET.fromstring(problem.original_description)
    for link in root.findall('link'):
        if any(link.get('name').startswith(arm+'_robotiq_85_') for arm in ARMS):
            for collision in list(link.findall('collision')):link.remove(collision)
            for collision in original.find("link[@name='%s']" % link.get('name')).findall('collision'):
                link.append(copy.deepcopy(collision))
    body = ET.SubElement(root, 'link', name='weigh_carton')
    boxes = shell_boxes(scene)
    for box in boxes:
        lo, hi = np.asarray(box['lo']), np.asarray(box['hi'])
        collision = ET.SubElement(body, 'collision')
        ET.SubElement(collision, 'origin', xyz=' '.join(map(str, (lo+hi)/2)))
        ET.SubElement(ET.SubElement(collision, 'geometry'), 'box', size=' '.join(map(str, hi-lo)))
    joint = ET.SubElement(root, 'joint', name=LIFT_JOINT, type='prismatic')
    ET.SubElement(joint, 'parent', link='world'); ET.SubElement(joint, 'child', link='weigh_carton')
    set_origin(joint, pose)
    ET.SubElement(joint, 'axis', xyz=' '.join(map(str, pose[:3,:3].T @ [0.,0.,1.])))
    ET.SubElement(joint, 'limit', lower='0', upper=str(HEIGHT), effort='1', velocity='1')
    model = CollisionModel(ET.tostring(root, encoding='unicode'), directory)
    model.bounds[LIFT_JOINT] = (0., HEIGHT)
    srdf = ET.fromstring((problem.directory/'moveit/robot.srdf').read_text())
    for item in srdf.findall('disable_collisions'):
        model.scene.allowed_collision_matrix.set_entry(item.get('link1'), item.get('link2'), True)
    for arm in ARMS:
        for side in ('left','right'):
            model.scene.allowed_collision_matrix.set_entry('weigh_carton', arm+f'_robotiq_85_{side}_finger_tip_link', True)
    table = Chain(problem.original_description, 'world', 'right_table_top').forward({})
    if not np.allclose(table[:3,2], [0,0,1], atol=1e-8):
        raise ValueError('Weigh lift requires the horizontal right support table')
    corners = np.array([p for box in boxes for p in itertools.product(*zip(box['lo'],box['hi']))])
    bottom = float((corners@pose[:3,:3].T+pose[:3,3])[:,2].min()-table[2,3])
    # The existing shell expands by5mm below the measured supporting plane.
    raw = np.concatenate([np.asarray(s['vertices']) for s in scene['shapes']])
    raw_bottom = float((raw@pose[:3,:3].T+pose[:3,3])[:,2].min()-table[2,3])
    if abs(raw_bottom)>1e-6 or bottom < -.005-1e-6 or bottom+HEIGHT <= 0:
        raise ValueError('Carton must start on the table plane and clear its existing shell expansion after20mm')
    for side in ('left','right'):
        other = Chain(problem.original_description, 'world', side+'_table_top').forward({})
        if not np.allclose(other[:3,2],[0,0,1],atol=1e-8) or abs(other[2,3]-table[2,3])>1e-8:
            raise ValueError('Initial support contact requires coplanar horizontal tables')
    return model, dict(initial_shell_bottom_above_table_m=bottom,
        final_shell_bottom_above_table_m=bottom+HEIGHT,
        initial_physical_model_bottom_above_table_m=raw_bottom,
        support_contact_policy='horizontal table plates only while the original5mm shell expansion intersects; monotonically separating vertical lift')


def nominal_pad_contact(model,problem,start,support):
    """Find the first modeled pad/wall contact, never close through the object.

    The primary cell proof still contains every opening. This auxiliary grasp
    scene describes the nominal contact constraint, not a measured jaw angle.
    """
    state=dict(start);result={}
    for side in ('left','right'):
        model.scene.allowed_collision_matrix.set_entry('weigh_carton',side+'_table_plate',True)
    for arm in ARMS:
        tips=[arm+f'_robotiq_85_{side}_finger_tip_link' for side in ('left','right')]
        for tip in tips:model.scene.allowed_collision_matrix.set_entry('weigh_carton',tip,False)
        joint=problem.names[arm][6];lo,hi=model.bounds[joint]
        state[joint]=lo
        if not model.check(state)[0]:raise ValueError(arm+': open grasp scene already collides')
        bracket=None
        previous=lo
        for value in np.linspace(lo,hi,81)[1:]:
            state[joint]=float(value)
            if not model.check(state)[0]:bracket=(previous,float(value));break
            previous=float(value)
        if bracket is None:raise ValueError(arm+': no modeled pad contact on carton')
        lo,hi=bracket
        for _ in range(20):
            mid=(lo+hi)/2;state[joint]=mid
            if model.check(state)[0]:lo=mid
            else:hi=mid
        state[joint]=hi
        for tip in tips:model.scene.allowed_collision_matrix.set_entry('weigh_carton',tip,True)
        if not model.check(state)[0]:
            model.check(state,contacts=True)
            raise ValueError(arm+': first modeled closing contact is not confined to the fingertip pads')
        result[joint]=hi
    return result


def shared_trajectories(problem, start, joint_cap, tcp_cap):
    problem.chains = {arm: Chain(problem.original_description, 'world', arm+'_tool0') for arm in ARMS}
    segments, targets = {}, {}
    for arm in ARMS:
        target = problem.chains[arm].forward(start); targets[arm] = target
        down = cartesian_entry(problem, arm, start, target, [start[j] for j in joint_names(arm)], HEIGHT)
        segments[arm] = dict(down, positions=down['positions'][::-1])
    envelope = speed_envelope(problem, ARMS, joint_cap, tcp_cap)
    u = np.linspace(0,1,201)
    duration = max(.01, *(float(abs(evaluate(s,u,1)).max())/joint_cap for s in segments.values()),
                   *(float(np.sqrt(abs(evaluate(s,u,2)).max()/problem.cfg['acceleration_limit_rad_s2'])) for s in segments.values()))
    # One shared time law, scaled only to meet the existing joint/TCP/acceleration bounds.
    for _ in range(8):
        trajectories = {}
        needed = duration
        for arm, segment in segments.items():
            q, v, a = (evaluate(segment,u,d) for d in range(3))
            points = [dict(time=round(float(t*duration)*1e9)/1e9, positions=x.tolist(),
                velocities=(y/duration).tolist(), accelerations=(z/duration**2).tolist()) for t,x,y,z in zip(u,q,v,a)]
            trajectory = retime(dict(points=points, waypoints=segment['positions']), arm, envelope)
            needed = max(needed, trajectory['duration_s'], trajectory['duration_s']*
                np.sqrt(float(interpolation_peaks(trajectory,2).max())/problem.cfg['acceleration_limit_rad_s2']))
            trajectories[arm] = trajectory
        if needed <= duration*(1+1e-10):
            if len({t['duration_s'] for t in trajectories.values()}) != 1:
                raise ValueError('Weigh lift lost its shared time law')
            return trajectories, segments, targets, duration
        duration = needed
    raise ValueError('Unable to represent the shared bounded lift')


def prepare(plan, output):
    output.mkdir(parents=True, exist_ok=False)
    evidence = json.loads((plan/'high-plan/evidence.json').read_text())
    entry = json.loads((plan/'entry-plan/result.json').read_text())
    if not entry.get('success') or entry.get('phase') != 'OFFLINE_OPEN_ENTRY_GEOMETRY_VALID':
        raise ValueError('Complete checked entry required before the lift')
    start = entry['final_positions']
    problem = HardwareProblem(output/'model', evidence['configuration'], REPO/'config/hardware_inventory.yaml')
    entry_bundle = json.loads((plan/'review-entry.json').read_text())
    joint_cap, tcp_cap = entry_bundle['joint_limit_rad_s'], entry_bundle['tcp_limit_m_s']
    binding = json.loads(Path(evidence['inputs']['object_pose']['path']).read_text())
    pose = np.asarray(binding['world_object_by_arm'][ARMS[0]])
    if not all(np.allclose(pose, value, atol=1e-8,rtol=0) for value in binding['world_object_by_arm'].values()):
        raise ValueError('One common carton pose required')
    scene = json.loads(Path(evidence['inputs']['contact_scene']['path']).read_text())
    trajectories, segments, targets, duration = shared_trajectories(problem,start,joint_cap,tcp_cap)
    proof, error = prove_group(problem,start,trajectories,joint_cap)
    if error: raise ValueError('Joint lift primary cell proof: '+error)
    model, support = moving_carton(problem,pose,scene,output/'carton-scene')
    grasp_joints=nominal_pad_contact(model,problem,start,support)
    maxima = {arm: dict(position_m=0.,angle_rad=0.) for arm in ARMS}
    polynomials = {arm:BPoly.from_derivatives([p['time'] for p in t['points']],
        [[p['positions'],p['velocities'],p['accelerations']] for p in t['points']])
        for arm,t in trajectories.items()}
    duration = trajectories[ARMS[0]]['duration_s']
    for phase in np.linspace(0,1,257):
        height = HEIGHT*float(quintic(phase)); state = dict(start,**grasp_joints)
        for arm in ARMS: state.update(zip(joint_names(arm), polynomials[arm](phase*duration)))
        for arm in ARMS:
            actual = problem.chains[arm].forward(state); wanted = targets[arm].copy(); wanted[2,3] += height
            pe = float(np.linalg.norm(actual[:3,3]-wanted[:3,3]))
            re = float(Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).magnitude())
            maxima[arm]['position_m'] = max(maxima[arm]['position_m'],pe)
            maxima[arm]['angle_rad'] = max(maxima[arm]['angle_rad'],re)
            if pe>1e-4 or re>1e-3: raise ValueError('Shared carton/tool lift pose error')
        # Only the explicitly intended separating support contact is admitted.
        for side in ('left','right'):
            model.scene.allowed_collision_matrix.set_entry('weigh_carton',side+'_table_plate',
                support['initial_shell_bottom_above_table_m']+height<=1e-9)
        if not model.check(dict(state, **{LIFT_JOINT:height}))[0]:
            model.check(dict(state, **{LIFT_JOINT:height}), contacts=True)
            raise ValueError(f'Moving carton collision at lift progress {phase:.6f}')
    end = dict(start)
    for arm,t in trajectories.items(): end.update(zip(joint_names(arm),t['points'][-1]['positions']))
    sources = [plan/'entry-plan/result.json',plan/'review-entry.json',
        Path(evidence['inputs']['object_pose']['path']),Path(evidence['inputs']['contact_scene']['path']),
        Path(__file__), REPO/'tools/prepare_carton_open_entry.py',
        REPO/'tools/carton_weigh_phase.py',REPO/'uwa_cell_tasks/uwa_cell_tasks/carton_weighing.py']
    report = dict(schema_version=1, success=True, phase='OFFLINE_WEIGH_LIFT_PREPARED',
        start=start,end=end,height_m=HEIGHT, duration_s=duration, robot_commands_sent=False,
        inputs={str(p.resolve()):file_hash(p) for p in sources}, support=support,
        joint_group_proof=proof, moving_carton_samples=257, tool_pose_error=maxima,
        nominal_contact_joints=grasp_joints,nominal_contact_is_measured_opening=False,
        force_base_to_world={arm:Chain(problem.original_description,'world',arm+'_base').forward({})[:3,:3].tolist() for arm in ARMS},
        limits=['Sampled task-object/coupling geometry, not a proof of real pad contact or mechanical synchronization.',
                'Full-opening whole-cell and independent-progress interarm proof retained; common commanded time law.',
                'Carton/gripper scene uses first nominal pad contact on the existing design shell; jaw angle and wall thickness are not measured.'])
    dump(output/'proof.json',report)
    preview = preview_model(problem,output)
    carton = dict(world_pose=pose.tolist(),shell_boxes=shell_boxes(scene))
    groups = [dict(arms=list(ARMS),start=start,trajectories=trajectories,duration_s=trajectories[ARMS[0]]['duration_s'],proof=proof)]
    bundle = write_bundle(output/'review.json','weigh',problem,start,groups,[],output/'proof.json',preview,carton,joint_cap,tcp_cap,REPO/'tools')
    check_boundaries(bundle,start,end,list(ARMS))
    print(json.dumps(dict(success=True,output=str(output),duration_s=duration,height_m=HEIGHT)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    try:
        prepare(args.plan.resolve(),args.output.resolve())
    except Exception as error:
        args.output.mkdir(parents=True,exist_ok=True)
        dump(args.output/'result.json',dict(success=False,phase='OFFLINE_WEIGH_LIFT_REJECTED',
            error=str(error),robot_commands_sent=False))
        raise

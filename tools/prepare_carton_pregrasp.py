#!/usr/bin/env python3
"""Offline pregrasp evidence from saved observations; no device/ROS commands.

The simulated contact design supplies only object-local wall points. All world
targets are rebuilt from the supplied camera pose and actual factory model.
Results intentionally contain no timed/executable hardware trajectory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'uwa_cell_tasks'))
from match_cooperative_handling.rigid_object import rigid
from uwa_cell_tasks.hardware_object_reference import MEMBERS


def fingerprint(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def nearest_winding(positions, initial, bounds):
    """Equivalent revolute endpoints nearest saved start, inside actual limits."""
    result = []
    for value, start, (lo, hi) in zip(positions, initial, bounds):
        choices = [value+2*np.pi*k for k in range(int(np.ceil((lo-value)/(2*np.pi))),
                                                 int(np.floor((hi-value)/(2*np.pi)))+1)]
        if not choices: raise ValueError('No equivalent endpoint inside joint limits')
        result.append(min(choices, key=lambda q: abs(q-start)))
    return result


def targets(description, contacts, world_object, pregrasp_m=.08):
    from uwa_cell_gazebo.charuco_views import Chain
    world_object = rigid(world_object)
    if world_object[2, 2] < np.cos(np.deg2rad(2)):
        raise ValueError('Wall pinch requires an upright supported carton (<=2deg)')
    if not np.isfinite(pregrasp_m) or not .05 <= pregrasp_m <= .3:
        raise ValueError('Pregrasp separation must be50–300mm')
    if set(contacts) != set(MEMBERS):
        raise ValueError('Exactly both right wall contacts required')
    result = {}
    for arm in MEMBERS:
        contact = contacts[arm]
        point = np.asarray(contact['point_object'], float)
        normal = np.asarray(contact['normal_object'], float)
        if point.shape != (3,) or normal.shape != (3,) or not np.isfinite([point, normal]).all():
            raise ValueError('Finite object-local wall point/normal required')
        if abs(normal[2]) > 1e-8 or abs(np.linalg.norm(normal)-1) > 1e-8:
            raise ValueError('Horizontal unit wall normal required')
        closing = world_object[:3, :3]@normal
        closing[2] = 0.; closing /= np.linalg.norm(closing)
        down = np.array([0., 0., -1.])
        rotation = np.column_stack([closing, np.cross(down, closing), down])
        base = np.eye(4); base[:3, :3] = rotation
        base[:3, 3] = world_object[:3, :3]@point+world_object[:3, 3]-rotation@np.array([0., 0., .145])
        tool_base = Chain(description, arm+'_tool0', arm+'_robotiq_85_base_link').forward({})
        entry = base@np.linalg.inv(tool_base)
        pre = entry.copy(); pre[2, 3] += pregrasp_m
        result[arm] = dict(tool0_pregrasp=pre.tolist(), theoretical_tool0_entry=entry.tolist(),
                           point_object_m=point.tolist(), world_contact_m=(world_object[:3, :3]@point+world_object[:3, 3]).tolist())
    return result


def prepare(args):
    from uwa_cell_calibration.model import CollisionModel
    from uwa_cell_control.parallel_scan import collision_signature
    from uwa_cell_motion.common import config, dump, joint_names
    from uwa_cell_motion.hardware_model import HardwareProblem
    from uwa_cell_motion.geometry import SphereModel
    from uwa_cell_motion.candidates import enumerate_candidates
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    observations = json.loads(args.observations.read_text())
    diagnostic = json.loads(args.object_pose.read_text())
    source_plan = json.loads(args.contact_design.read_text())
    scene = json.loads(args.contact_scene.read_text())
    T = rigid(diagnostic['T_world_object_candidate'])
    if scene['asset_id'] != 'carton_avocado_v1':
        raise ValueError('This contact design is specific to carton_avocado_v1')
    cfg = config(args.config)
    problem = HardwareProblem(out/'model', cfg, args.inventory, args.layout)
    # Preserve coupled-tool sweep allowances when adding the carton. There are
    # no arm/carton touch exemptions, and unknown fingers retain full sweeps.
    previous_srdf = ET.fromstring((out/'model/moveit/robot.srdf').read_text())
    root = ET.fromstring(problem.description)
    object_frames={'right_front':T,'right_rear':T}
    if diagnostic.get('binding_kind')=='per_arm_camera':
        from uwa_cell_tasks.hardware_registration import validate_per_arm_binding
        object_frames={a:rigid(t) for a,t in validate_per_arm_binding(problem.original_description,diagnostic).items()}
    # Check the union of the per-base representations in the nominal display
    # model. This preserves every carton obstacle instead of shifting the
    # model or dropping the second arm's measured camera/base binding.
    for index, object_frame in enumerate(object_frames.values()):
        suffix='' if index==0 else '_'+str(index)
        link = ET.SubElement(root, 'link', name='pregrasp_carton_static'+suffix)
        for shape in scene['shapes']:
            uri = shape['uri']
            from urllib.parse import urlparse, unquote
            path = Path(unquote(urlparse(uri).path))
            if fingerprint(path)['sha256'] != shape['sha256']:
                raise ValueError('Contact mesh hash mismatch: '+str(path))
            mesh = ET.SubElement(ET.SubElement(ET.SubElement(link, 'collision'), 'geometry'), 'mesh')
            mesh.set('filename', uri)
        joint = ET.SubElement(root, 'joint', name='pregrasp_carton_anchor'+suffix, type='fixed')
        ET.SubElement(joint, 'parent', link='world'); ET.SubElement(joint, 'child', link=link.get('name'))
        ET.SubElement(joint, 'origin', xyz=' '.join(map(str, object_frame[:3, 3])),
                      rpy=' '.join(map(str, Rotation.from_matrix(object_frame[:3, :3]).as_euler('xyz'))))
    problem.description = ET.tostring(root, encoding='unicode')
    problem.base_collision = problem.collision
    problem.collision = CollisionModel(problem.description, out/'carton-moveit')
    srdf = ET.fromstring((out/'carton-moveit/robot.srdf').read_text())
    for entry in previous_srdf.findall('disable_collisions'):
        problem.collision.scene.allowed_collision_matrix.set_entry(entry.get('link1'), entry.get('link2'), True)
        srdf.append(entry)
    (out/'carton-moveit/robot.srdf').write_text(ET.tostring(srdf, encoding='unicode'))
    problem.spheres = SphereModel(problem.description, problem.names, cfg['sphere_spacing_m'])
    problem.signature = collision_signature(problem.description)
    # RRT's input paths must name the augmented model, not the carton-free model.
    problem.directory = out
    (out/'moveit').mkdir()
    (out/'moveit/robot.urdf').write_text(problem.description)
    (out/'moveit/robot.srdf').write_text(ET.tostring(srdf, encoding='unicode'))
    start = {}
    for arm, names in problem.names.items():
        obs = observations['arms'][arm]
        minimal_snapshot = observations.get('protection_backend') == 'minimal'
        if not obs.get('samples') or (not minimal_snapshot and obs.get('stationary_observed') is not True):
            raise ValueError('Saved stationary observation missing: '+arm)
        sample = obs['samples'][-1]
        # A powered, stationary robot still supplies real encoders with its
        # program stopped. This is offline evidence only; the real runner
        # separately requires a playing program and live reverse connection.
        if not minimal_snapshot and (sample['robot_mode'] != 7 or sample['safety_mode'] != 1 or sample['runtime_state'] not in (1, 2)):
            raise ValueError('Saved native state unsuitable: '+arm)
        q = np.asarray(sample['actual_q'], float)
        if q.shape != (6,) or not np.isfinite(q).all(): raise ValueError('Invalid saved joints')
        start.update(zip(names[:6], q)); start.update({j: 0. for j in names[6:]})
    goal_frames = {a:targets(problem.original_description,source_plan['candidate']['contacts'],t,args.pregrasp_m)[a]
                   for a,t in object_frames.items()}
    open_meshes = None
    if not problem.check(dict(start=start,joint_names=[]),[]):
        from uwa_cell_tasks.hardware_carton_approach import open_carton_collision
        candidate, hashes = open_carton_collision(problem,problem.description,out/'open-carton-moveit')
        if candidate.check(start)[0]:
            problem.collision = candidate
            open_meshes = hashes
    selected=tuple(args.arm) if args.arm else MEMBERS
    goals = {}
    for arm in selected:
        pre = np.asarray(goal_frames[arm]['tool0_pregrasp'])
        goals[arm] = dict(frame_id='world', target_link=arm+'_tool0',
                          pose=dict(position=pre[:3, 3].tolist(), orientation_xyzw=Rotation.from_matrix(pre[:3, :3]).as_quat().tolist()))
    request = dict(start=start, goals=goals)
    # Recompute current targets from vetted task-posture seeds before random
    # multistart. A seed is a branch hint, never a saved executable endpoint.
    from uwa_cell_motion.carton_paths import solve_near
    from uwa_cell_gazebo.charuco_views import Chain
    problem.chains={r:Chain(problem.original_description,'world',r+'_tool0')for r in selected}
    seeded={};seed_errors={}
    for arm in selected:
        seed=source_plan['candidate'].get('preferred_ik_seeds',{}).get(arm)
        if seed is not None:
            try:seeded[arm]=solve_near(problem,arm,start,goal_frames[arm]['tool0_pregrasp'],seed).tolist()
            except ValueError as error:seed_errors[arm]=str(error)
    raw=None
    if len(seeded)==len(selected):
        raw=enumerate_candidates(problem,dict(start=start,goals=seeded),max_per_arm=24,budget_s=30.)
        raw['posture_seed_policy']='Fresh IK from previously vetted task branches; current endpoint/model validation retained'
    if raw is None or not raw['combinations']:
        raw=enumerate_candidates(problem,request,seeds=24,max_per_arm=24,budget_s=30.)
    raw['task_seed_errors']=seed_errors
    dump(out/'raw-cartesian-candidates.json', raw)
    # Random multistart can find a correct pose several turns away. Add the
    # closest limit-respecting equivalent endpoint, preserving raw evidence.
    # This is endpoint branch selection before planning, never live rebasing.
    alternatives = {}
    from uwa_cell_tasks.hardware_posture import branch_allowed,rank_postures
    required_branches=source_plan['candidate'].get('elbow_signs',{})
    for arm in selected:
        names = joint_names(arm)
        initial = [start[j] for j in names]; bounds = [problem.collision.bounds[j] for j in names]
        values = []
        from uwa_cell_gazebo.charuco_views import Chain
        chain = Chain(problem.original_description, 'world', arm+'_tool0')
        wanted = np.asarray(goal_frames[arm]['tool0_pregrasp'])
        for c in raw['candidates'][arm]:
            q = nearest_winding(c['positions'], initial, bounds)
            if not branch_allowed(q,required_branches.get(arm)):continue
            measured = chain.forward(dict(start, **dict(zip(names, q))))
            if (np.linalg.norm(measured[:3, 3]-wanted[:3, 3]) > 1e-4 or
                Rotation.from_matrix(measured[:3, :3]@wanted[:3, :3].T).magnitude() > 1e-4):
                raise ValueError('Equivalent winding changed the Cartesian target')
            values.append(dict(positions=q))
        if not values:
            dump(out/'failure.json', dict(executable=False, error=arm+': no Cartesian IK solution'))
            return dict(status='NO_IK_FOUND', output=str(out), executable=False)
        alternatives[arm] = dict(alternatives=values)
    candidates = enumerate_candidates(problem, dict(start=start, goals=alternatives), max_per_arm=12, budget_s=30.)
    candidates['combinations']=rank_postures(problem,start,candidates['combinations'])
    candidates['posture_policy']=dict(required_elbow_signs=required_branches,reason=source_plan['candidate'].get('posture_reason'),ranking='Task suitability, then Pareto fronts: joint reserves, scaled Jacobian minimum singular value, wrist/neighbor clearance, travel; shortest travel within each front')
    dump(out/'candidates.json', candidates)
    attempts = []; path = None
    path_budget=getattr(args,'path_budget_s',None)or cfg['planning_budget_s']
    start_valid = problem.check(dict(start=start, joint_names=[]), [])
    if start_valid:
        for combined in candidates['combinations'][:8]:
            normalized = problem.normalize(dict(start=start, goals=combined['goals']))
            a = [start[j] for j in normalized['joint_names']]; b = normalized['target']
            begun = time.monotonic(); deadline = begun+path_budget
            if problem.edge(normalized, a, b, deadline=deadline):
                path = [a, b]; kind = 'simultaneous_direct'
            else:
                path = problem.serial_direct(normalized, deadline); kind = 'serial_direct'
            if path is None and len(selected)==1:
                # A changed elbow branch may need a geometrically checked
                # upright intermediate, with every other arm held fixed.
                via=list(a);via[1:]=[-np.pi/2,0.,-np.pi/2,0.,0.]
                if problem.edge(normalized,a,via) and problem.edge(normalized,via,b):
                    path=[a,via,b];kind='single_arm_via_upright'
            if path is None and time.monotonic() < deadline:
                path, error = problem.rrt(normalized, seed=64, budget=deadline-time.monotonic())
                kind = 'rrt_detour'
            else:
                error = None if path is not None else 'DIRECT_SEARCH_BUDGET_EXHAUSTED'
            attempts.append(dict(candidate_ids=combined['candidate_ids'], path_found=path is not None,
                                 search_s=time.monotonic()-begun, error=error))
            if path is not None:
                # Replay each complete segment with the same full FCL/reserves.
                if not all(problem.edge(normalized, a, b) for a, b in zip(path, path[1:])):
                    raise ValueError('Independent final path replay failed')
                break
    evidence = dict(schema_version=1, artifact_type='offline_hardware_pregrasp_evidence',
        executable=False, hardware_plan=False, motion_ready=False, device_commands=[],
        status='GEOMETRIC_PATH_FOUND' if path is not None else 'NO_CHECKED_PATH_FOUND',
        saved_start_valid=start_valid, saved_start=start, selected=list(selected),world_object_candidate=T.tolist(),
        goals=goal_frames, attempts=attempts,
        open_right_grippers_required=open_meshes is not None,
        open_gripper_mesh_sha256=open_meshes,
        path=None if path is None else dict(kind=kind, joint_names=normalized['joint_names'], waypoints=path),
        model_signature=problem.signature, mesh_sha256=problem.spheres.geometry.assets,
        thresholds=problem.thresholds(), configuration=cfg,
        inputs={k:fingerprint(getattr(args,k)) for k in ('observations','object_pose','contact_design','contact_scene','config','inventory')},
        source=fingerprint(__file__),
        limits=['Single-image object pose and current OAK fit; no absolute accuracy qualification',
                'Historical stationary state, refresh and replan before any real motion',
                'Simulation contact design only; physical jaw/tool geometry requires alignment',
                'Only pregrasp geometry; no descent, gripping, lift, timing or stop qualification',
                'Bounded direct, serial and RRT search; failure is not infeasibility',
                'Sampled full FCL plus existing neighbor stopping reserves; no continuous proof'])
    dump(out/'evidence.json', evidence)
    return dict(status=evidence['status'], start_valid=start_valid,
                candidates={a:len(v) for a,v in candidates['candidates'].items()},
                valid_combinations=len(candidates['combinations']), output=str(out), executable=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('observations','object-pose','contact-design','contact-scene','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--inventory', type=Path, default=REPO/'config/hardware_inventory.yaml')
    parser.add_argument('--config', type=Path, default=REPO/'uwa_cell_motion/config/hardware_carton_supported_trend.yaml')
    parser.add_argument('--path-budget-s',type=float,help='Offline path-search budget per candidate only; no operating/safety/profile change')
    parser.add_argument('--layout', type=Path)
    parser.add_argument('--pregrasp-m', type=float, default=.08)
    parser.add_argument('--arm', choices=MEMBERS, action='append', help='Optional unloaded phase member; other arms remain measured obstacles')
    print(json.dumps(prepare(parser.parse_args()), indent=2))

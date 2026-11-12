"""Export the explicitly accepted preliminary OAK registration; offline only."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import cv2
import numpy as np
import yaml

from uwa_cell_description.calibration_profile import apply_layout, load_profile, rigid
from uwa_cell_gazebo.configuration import load_layout, nominal_layout_path, render_description
from uwa_cell_gazebo.charuco_views import Chain


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def reference(path):
    return dict(file=Path(path).name, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())


def brown_approximation(factory):
    """Fit only the simulator's limited Brown5 model, retain physical Rational14."""
    k = np.asarray(factory['camera_matrix_8000x6000'])
    d = np.asarray(factory['distortion'])
    u, v = np.meshgrid(np.linspace(0, 8000, 45), np.linspace(0, 6000, 35))
    points = np.c_[(u.ravel()-k[0,2])/k[0,0], (v.ravel()-k[1,2])/k[1,1], np.ones(u.size)]
    distorted = cv2.projectPoints(points, np.zeros(3), np.zeros(3), np.eye(3), d)[0].reshape(-1, 2)
    x, y = points[:, :2].T
    r = x*x + y*y
    a = np.empty((2*len(x), 5))
    a[::2] = np.c_[x*r, x*r*r, 2*x*y, r+2*x*x, x*r*r*r]
    a[1::2] = np.c_[y*r, y*r*r, r+2*y*y, 2*x*y, y*r*r*r]
    brown = np.linalg.lstsq(a, (distorted-points[:, :2]).ravel(), rcond=None)[0]
    # Evaluate on a different, denser grid, not only the approximation fit grid.
    u, v = np.meshgrid(np.linspace(0, 8000, 80), np.linspace(0, 6000, 60))
    check = np.c_[(u.ravel()-k[0,2])/k[0,0], (v.ravel()-k[1,2])/k[1,1], np.ones(u.size)]
    error = cv2.projectPoints(check, np.zeros(3), np.zeros(3), k, brown)[0] - cv2.projectPoints(check, np.zeros(3), np.zeros(3), k, d)[0]
    distances = np.linalg.norm(error.reshape(-1, 2), axis=1)
    return dict(distortion=brown.tolist(), model='plumb_bob',
        physical_model='rational_polynomial', physical_distortion=d.tolist(),
        approximation_only=True, check_grid=[80,60],
        rms_error_at_8000x6000_px=float(np.sqrt(np.mean(distances**2))),
        max_error_at_8000x6000_px=float(max(distances)))


def export(workspace, evaluation, parent, output, authorization):
    ws, evaluation, parent, output = map(Path, (workspace, evaluation, parent, output))
    previous = load_profile(parent)
    result = json.loads((evaluation/'result.json').read_text())
    protocol = json.loads((evaluation/'protocol.json').read_text())
    row = next(r for r in protocol['rows'] if r['role'] == 'fit')
    manifest_path = Path(row['manifest'])
    if reference(manifest_path)['sha256'] != row['manifest_sha256']:
        raise ValueError('Reference pose source changed since evaluation')
    manifest = json.loads(manifest_path.read_text())
    snapshot = manifest['telemetry_before']['arms']['right_front']
    if snapshot['source'] != 'live_joint_states':
        raise ValueError('OAK registration requires measured front joints')
    layout = apply_layout(load_layout(nominal_layout_path()), previous)
    with tempfile.TemporaryDirectory(prefix='uwa-oak-registration-') as directory:
        description = render_description(layout, Path(directory))[0]
    joints = dict(zip(snapshot['joint_names'], snapshot['positions']))
    world_base = Chain(description, 'world', 'right_front_base_link').forward({})
    base_tool = Chain(description, 'right_front_base_link', 'right_front_tool0').forward(joints)
    tool_camera = rigid(previous['robots']['right_front']['fit']['T_tool0_camera'])
    oak_front = rigid(result['T_oak_optical_right_front_optical'])
    base_oak = base_tool @ tool_camera @ np.linalg.inv(oak_front)
    world_oak = world_base @ base_oak
    # Old profile and its quality results remain byte-for-byte available.
    shutil.copytree(parent.parent, output)
    for source, name in [('result.json', 'oak_relative_result.json'), ('protocol.json', 'oak_acquisition_protocol.json')]:
        shutil.copy2(evaluation/source, output/name)
    factory_path = ws/'setup/calibration/oak_pose_20261112/oak_rgb_intrinsics.json'
    shutil.copy2(factory_path, output/'oak_factory_intrinsics.json')
    factory = json.loads(factory_path.read_text())
    save(output/'oak_reference_state.json', dict(schema=1, robot_id='right_front',
        snapshot=snapshot, source_manifest=str(manifest_path), source_manifest_sha256=row['manifest_sha256'],
        parent_profile=previous['profile_id'], parent_profile_sha256=previous['sha256'],
        anchor_warning='Model world/base mount is provisional; measured joint snapshot is not an initial pose or motion command'))
    registration = dict(schema=1, passed=False, diagnostic_only=True, camera_id=factory['device_id'],
        anchor_frame='right_front_base_link', world_frame='world', optical_frame='oak_overview_rgb_optical_frame',
        real_optical_frame='real_oak4_rgb_optical_frame', mount='world_fixed',
        quality_status='operator_accepted_preliminary', world_registration='provisional_model_anchor',
        transform_convention='T_A_B maps points from B into A',
        T_world_anchor_at_registration=world_base.tolist(), T_anchor_tool0=base_tool.tolist(),
        T_tool0_front_optical=tool_camera.tolist(), T_anchor_oak_optical=base_oak.tolist(),
        T_world_oak_optical=world_oak.tolist(),
        note='World pose frozen at registration; moving a table does not move the external tripod. No calibrated table/world/base pose claimed.')
    save(output/'oak_registration.json', registration)
    save(output/'oak_simulation_optics.json', brown_approximation(factory))
    k = np.asarray(factory['camera_matrix_8000x6000'])
    projection = np.c_[k, np.zeros(3)]
    (output/'oak4_camera_info.yaml').write_text(yaml.safe_dump(dict(image_width=8000,image_height=6000,
        camera_name='oak4_rgb_1479883285_focus116', distortion_model='rational_polynomial',
        camera_matrix=dict(rows=3,cols=3,data=k.ravel().tolist()),
        distortion_coefficients=dict(rows=1,cols=len(factory['distortion']),data=factory['distortion']),
        rectification_matrix=dict(rows=3,cols=3,data=np.eye(3).ravel().tolist()),
        projection_matrix=dict(rows=3,cols=4,data=projection.ravel().tolist()))))
    profile = json.loads(parent.read_text())
    profile.update(profile_id=output.name, previous_profile=previous['profile_id'],
                   created_at=datetime.now().astimezone().isoformat())
    overview = {key: reference(output/name) for key, name in dict(extrinsics='oak_registration.json',
        relative_fit='oak_relative_result.json', acquisition_protocol='oak_acquisition_protocol.json',
        factory_intrinsics='oak_factory_intrinsics.json', reference_state='oak_reference_state.json',
        simulation_optics='oak_simulation_optics.json', camera_info='oak4_camera_info.yaml').items()}
    overview['operator_acceptance'] = dict(extrinsics=dict(decision='accept_below_threshold',authorized_by='user',
        date='2026-11-12', authorization=authorization,
        source_sha256=overview['extrinsics']['sha256'], quality_report=overview['relative_fit']))
    profile['overview_camera'] = overview
    profile['not_calibrated'] = [v for v in profile['not_calibrated'] if v != 'oak_extrinsics']
    profile['not_calibrated'].append('oak_extrinsics_independent_hardware_accuracy')
    profile['application'] += ' Preliminary OAK/front-wrist extrinsics explicitly adopted by user for first attempts; world anchor remains provisional and camera stays world-fixed.'
    save(output/'profile.json', profile)
    return registration


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, default=Path.home()/'UWA_ws')
    p.add_argument('--evaluation', type=Path, required=True)
    p.add_argument('--parent', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--authorization', required=True)
    args = p.parse_args()
    print(json.dumps(export(args.workspace,args.evaluation,args.parent,args.output,args.authorization),indent=2))


if __name__ == '__main__':
    main()

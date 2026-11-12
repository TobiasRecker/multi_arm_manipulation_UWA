"""Validated, explicitly accepted external-camera registration and its provenance."""
import json

import numpy as np

R_SENSOR_OPTICAL = np.array([[0., 0., 1.], [-1., 0., 0.], [0., -1., 0.]])


def load_overview(directory, overview, robots):
    from .calibration_profile import read_artifact, operator_acceptance, rigid
    for key in ('extrinsics','relative_fit','acquisition_protocol','factory_intrinsics',
                'reference_state','simulation_optics','camera_info'):
        read_artifact(directory, overview[key])
    if not operator_acceptance(directory, overview, 'extrinsics'):
        raise ValueError('Preliminary OAK registration requires explicit per-artifact user acceptance')
    def read(key):
        return json.loads(read_artifact(directory, overview[key]).read_text())
    registration, relative, factory, state, simulation = map(read,
        ('extrinsics','relative_fit','factory_intrinsics','reference_state','simulation_optics'))
    if (registration.get('schema') != 1 or registration.get('mount') != 'world_fixed'
            or registration.get('anchor_frame') != 'right_front_base_link'
            or registration.get('optical_frame') != 'oak_overview_rgb_optical_frame'
            or registration.get('real_optical_frame') != 'real_oak4_rgb_optical_frame'
            or registration.get('world_frame') != 'world'
            or registration.get('world_registration') != 'provisional_model_anchor'
            or relative.get('diagnostic_only') is not True or relative.get('passed') is not False):
        raise ValueError('Unsupported OAK registration or concealed preliminary quality')
    if (registration['camera_id'] != factory['device_id'] or state['robot_id'] != 'right_front'
            or 'fit' not in robots['right_front']):
        raise ValueError('OAK registration camera/anchor identity mismatch')
    from .configuration import joint_names
    snapshot = state['snapshot']
    positions = np.asarray(snapshot['positions'], float)
    if (snapshot.get('source') != 'live_joint_states' or positions.shape != (6,)
            or snapshot['joint_names'] != joint_names('right_front') or not np.isfinite(positions).all()):
        raise ValueError('OAK registration requires six measured named anchor joints')
    world_base = rigid(registration['T_world_anchor_at_registration'])
    base_tool = rigid(registration['T_anchor_tool0'])
    tool_camera = rigid(registration['T_tool0_front_optical'])
    base_oak = rigid(registration['T_anchor_oak_optical'])
    world_oak = rigid(registration['T_world_oak_optical'])
    oak_front = rigid(relative['T_oak_optical_right_front_optical'])
    if (not np.allclose(tool_camera, rigid(robots['right_front']['fit']['T_tool0_camera']), atol=1e-10)
            or not np.allclose(base_tool @ tool_camera @ np.linalg.inv(oak_front), base_oak, atol=1e-10)
            or not np.allclose(world_base @ base_oak, world_oak, atol=1e-10)):
        raise ValueError('OAK registration transform derivation does not match its accepted sources')
    k, d = np.asarray(factory['camera_matrix_8000x6000'], float), np.asarray(factory['distortion'], float)
    brown = np.asarray(simulation['distortion'], float)
    if (k.shape != (3,3) or d.shape != (14,) or brown.shape != (5,)
            or not all(np.isfinite(v).all() for v in (k,d,brown))
            or not np.allclose(k[2], [0,0,1]) or k[0,0] <= 0 or k[1,1] <= 0
            or not 0 < k[0,2] < 8000 or not 0 < k[1,2] < 6000
            or factory.get('factory_calibration_lens_position') != 116
            or simulation.get('approximation_only') is not True
            or not np.array_equal(simulation['physical_distortion'], d)
            or not np.isfinite(simulation['max_error_at_8000x6000_px'])
            or not 0 <= simulation['max_error_at_8000x6000_px'] < 8):
        raise ValueError('Invalid physical OAK intrinsics or simulator approximation')
    overview.update(registration=registration, relative_result=relative, factory=factory,
                    simulation=simulation, quality_status='operator_accepted_preliminary')
    return overview

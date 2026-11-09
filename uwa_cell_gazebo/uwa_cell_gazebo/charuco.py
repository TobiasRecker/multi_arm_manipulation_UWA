"""Deterministic ChArUco assets and image-only board pose estimation.

Transform convention: T_A_B maps points from B into A. OpenCV's board origin
is the printed pattern's top-left corner, X right, Y down, Z into the paper.
No simulation poses or robot kinematics enter detect_pose().
"""
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation


def make_board(config, table):
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config['dictionary']))
    count = config['squares_x'] * config['squares_y'] // 2
    first = config['boards'][table]['marker_start']
    return cv2.aruco.CharucoBoard(
        (config['squares_x'], config['squares_y']), config['square_length'],
        config['marker_length'], dictionary, np.arange(first, first + count, dtype=np.int32))


def board_image(config, table):
    board = make_board(config, table)
    pixel = config['pixels_per_square']
    margin = round(config['margin'] / config['square_length'] * pixel)
    pattern = board.generateImage((config['squares_x'] * pixel, config['squares_y'] * pixel),
                                  marginSize=0, borderBits=1)
    return cv2.copyMakeBorder(pattern, margin, margin, margin, margin,
                              cv2.BORDER_CONSTANT, value=255)


def prepare_assets(config, directory):
    """Write generated images/meshes to launch-owned storage, never source files."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    width = config['squares_x'] * config['square_length'] + 2 * config['margin']
    height = config['squares_y'] * config['square_length'] + 2 * config['margin']
    for table in config['boards']:
        texture = f'{table}_charuco.png'
        if not cv2.imwrite(str(directory / texture), board_image(config, table)):
            raise RuntimeError(f'Could not write {texture}')
        # Texture top-left = table (-X,+Y); front faces upward (+Z).
        positions = f'{-width/2} {-height/2} 0 {width/2} {-height/2} 0 {width/2} {height/2} 0 {-width/2} {height/2} 0'
        mesh = directory / f'{table}_charuco.dae'
        mesh.write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
 <asset><created>2026-11-09T00:00:00Z</created><modified>2026-11-09T00:00:00Z</modified><unit meter="1" name="meter"/><up_axis>Z_UP</up_axis></asset>
 <library_images><image id="image"><init_from>{texture}</init_from></image></library_images>
 <library_effects><effect id="effect"><profile_COMMON>
  <newparam sid="surface"><surface type="2D"><init_from>image</init_from></surface></newparam>
  <newparam sid="sampler"><sampler2D><source>surface</source><minfilter>LINEAR</minfilter><magfilter>LINEAR</magfilter></sampler2D></newparam>
  <technique sid="common"><phong><emission><color>0 0 0 1</color></emission><ambient><color>1 1 1 1</color></ambient><diffuse><texture texture="sampler" texcoord="UVMap"/></diffuse><specular><color>0 0 0 1</color></specular><shininess><float>0</float></shininess></phong></technique>
 </profile_COMMON></effect></library_effects>
 <library_materials><material id="material"><instance_effect url="#effect"/></material></library_materials>
 <library_geometries><geometry id="board"><mesh>
  <source id="positions"><float_array id="positions-array" count="12">{positions}</float_array><technique_common><accessor source="#positions-array" count="4" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
  <source id="uv"><float_array id="uv-array" count="8">0 0 1 0 1 1 0 1</float_array><technique_common><accessor source="#uv-array" count="4" stride="2"><param name="S" type="float"/><param name="T" type="float"/></accessor></technique_common></source>
  <vertices id="vertices"><input semantic="POSITION" source="#positions"/></vertices>
  <triangles count="2" material="board_material"><input semantic="VERTEX" source="#vertices" offset="0"/><input semantic="TEXCOORD" source="#uv" offset="1" set="0"/><p>0 0 1 1 2 2 0 0 2 2 3 3</p></triangles>
 </mesh></geometry></library_geometries>
 <library_visual_scenes><visual_scene id="scene"><node id="node"><instance_geometry url="#board"><bind_material><technique_common><instance_material symbol="board_material" target="#material"><bind_vertex_input semantic="UVMap" input_semantic="TEXCOORD" input_set="0"/></instance_material></technique_common></bind_material></instance_geometry></node></visual_scene></library_visual_scenes>
 <scene><instance_visual_scene url="#scene"/></scene>
</COLLADA>
''')
        config['boards'][table]['mesh_file'] = str(mesh.resolve())


def transform(xyz, rpy):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_euler('xyz', rpy).as_matrix()
    result[:3, 3] = xyz
    return result


def table_board_transform(config, table):
    """Ground-truth pattern frame in <table>_table_top, separate from detector."""
    board = config['boards'][table]
    return transform(board['center_xyz'], [0, 0, board['yaw']]) @ transform(
        [-config['squares_x'] * config['square_length'] / 2,
         config['squares_y'] * config['square_length'] / 2, 0], [np.pi, 0, 0])


def pose_error(estimate, reference):
    return {'translation_m': float(np.linalg.norm(estimate[:3, 3] - reference[:3, 3])),
            'rotation_deg': float(np.degrees(Rotation.from_matrix(
                estimate[:3, :3] @ reference[:3, :3].T).magnitude()))}


def detect_pose(image, camera_matrix, distortion, config, table):
    board = make_board(config, table)
    parameters = cv2.aruco.CharucoParameters()
    parameters.cameraMatrix = np.asarray(camera_matrix, dtype=np.float64)
    parameters.distCoeffs = np.asarray(distortion, dtype=np.float64)
    detector_parameters = cv2.aruco.DetectorParameters()
    detector_parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.CharucoDetector(board, parameters, detector_parameters)
    corners, ids, marker_corners, marker_ids = detector.detectBoard(image)
    if ids is None or len(ids) < config['min_corners'] or board.checkCharucoCornersCollinear(ids):
        return None
    objects, pixels = board.matchImagePoints(corners, ids)
    # IPPE exposes the two planar candidates; select by cheirality and image error,
    # never by the known simulation pose. Refinement uses only image correspondences.
    success, rotations, translations, _ = cv2.solvePnPGeneric(
        objects, pixels, camera_matrix, distortion, flags=cv2.SOLVEPNP_IPPE)
    if not success:
        return None
    candidates = []
    for rvec, tvec in zip(rotations, translations):
        rotation = cv2.Rodrigues(rvec)[0]
        if np.any((objects.reshape(-1, 3) @ rotation.T + tvec.ravel())[:, 2] <= 0):
            continue
        projected = cv2.projectPoints(objects, rvec, tvec, camera_matrix, distortion)[0]
        rms = float(np.sqrt(np.mean(np.sum((projected - pixels) ** 2, axis=-1))))
        candidates.append((rms, rvec, tvec))
    if not candidates:
        return None
    _, rvec, tvec = min(candidates, key=lambda item: item[0])
    rvec, tvec = cv2.solvePnPRefineLM(objects, pixels, camera_matrix, distortion, rvec, tvec)
    pose = np.eye(4)
    pose[:3, :3], pose[:3, 3] = cv2.Rodrigues(rvec)[0], tvec.ravel()
    projected = cv2.projectPoints(objects, rvec, tvec, camera_matrix, distortion)[0]
    rms = float(np.sqrt(np.mean(np.sum((projected - pixels) ** 2, axis=-1))))
    annotated = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()
    cv2.aruco.drawDetectedMarkers(annotated, marker_corners, marker_ids)
    cv2.aruco.drawDetectedCornersCharuco(annotated, corners, ids)
    cv2.drawFrameAxes(annotated, camera_matrix, distortion, rvec, tvec,
                      config['square_length'] * 2, 2)
    return {'T_camera_board': pose, 'corners': int(len(ids)), 'reprojection_rms_px': rms,
            'annotated': annotated, 'corner_ids': ids.reshape(-1).tolist()}

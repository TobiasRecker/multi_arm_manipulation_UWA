"""Time-limited right-table camera reference for the supported carton program."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from tempfile import NamedTemporaryFile
import yaml


REPO = Path(__file__).resolve().parents[1]
LAYOUT = REPO / 'uwa_cell_description/config/cell_layout.yaml'
BASE_BINDINGS = LAYOUT.parent / 'calibration/hardware_20261118_base_fixed_v1/base_bindings.json'
LIFETIME = timedelta(hours=12)


def read_json(path):
    return json.loads(path.read_text())


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def timestamp(value):
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None:
        raise ValueError('Camera calibration timestamps must include an offset.')
    return stamp


def optics(source):
    native = source.get('intrinsics', source)
    return {key: native[key] for key in ('device_id', 'focus', 'image_size', 'K', 'D')}


def validation_sources():
    board = yaml.safe_load(LAYOUT.read_text())['charuco']
    definition = json.dumps(board, sort_keys=True, separators=(',', ':')).encode()
    return dict(board_definition=hashlib.sha256(definition).hexdigest(), base_bindings=sha256(BASE_BINDINGS))


def right_board_fit_ok(fit):
    markers = set(fit.get('fit_marker_ids', ()))
    check = set(fit.get('check_marker_ids', ()))
    return (fit['status'] == 'POSE_CANDIDATE' and fit.get('image_check_passed') is True
            and 0 <= fit['held_out_rms_px'] < 2.0 and len(markers | check) >= 12
            and bool(check) and not markers & check and (markers | check) <= set(range(50, 67)))


def measure_fixed_reference(capture, intrinsics, workspace, output):
    """Fit the right board at the current calibrated focus, keeping native pixels."""
    import cv2
    import importlib.util
    import os

    detector = workspace / 'src/oak_camera_calibration/tools/oak4_charuco.py'
    spec = importlib.util.spec_from_file_location('uwa_oak4_charuco', detector)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = module.freeze_config(workspace)
    camera = optics(read_json(intrinsics))
    photo = read_json(capture / 'metadata.json')
    if (photo.get('success') is not True or photo.get('mode') != 'standard'
            or photo.get('source') != 'fixed_focus_single_capture'
            or photo.get('device_id') != camera['device_id'] or photo['standard']['lens_position'] != camera['focus']):
        raise ValueError('The new right-board photo does not match the calibrated native camera.')
    source = capture / 'standard.png'
    image = cv2.imread(str(source))
    if image is None or list(image.shape[1::-1]) != camera['image_size']:
        raise ValueError('The new right-board image is not decodable at its calibrated native size.')
    board = module.Board(config['boards'], 'right')
    reduced = cv2.resize(image, None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA)
    hint = board.observe(reduced).get('roi')
    if hint:
        x, y, width, height = hint
        left, top = max(0, 4*x-width), max(0, 4*y-height)
        right = min(image.shape[1], 4*(x+width)+width)
        bottom = min(image.shape[0], 4*(y+height)+height)
        observation = board.observe(image, [left, top, right-left, bottom-top])
        fit = board.pose(observation, camera)
    else:
        fit = {'status': 'RIGHT_BOARD_NOT_FOUND'}
        observation = {}
    write_session(output / 'fixed-right-fit.json', dict(pose=fit, observation=observation,
                                                        source_photo=str(source)))
    if not right_board_fit_ok(fit):
        return None
    reference = output / 'fixed-right-reference'
    folder = reference / 'right/pose'
    folder.mkdir(parents=True)
    os.link(source, folder / 'standard.png')
    write_session(reference / 'metadata.json', photo)
    write_session(folder / 'metadata.json', photo)
    write_session(folder / 'intrinsics.json', camera)
    write_session(folder / 'pose.json', dict(board='right', pose=fit, observation=observation,
                                            source_config_sha256=config['sources_sha256']))
    return reference


def create_session(capture, intrinsics, *, requested_at):
    search = read_json(capture / 'metadata.json')
    folder = capture / 'right/pose'
    packet = read_json(folder / 'pose.json')
    meta = read_json(folder / 'metadata.json')
    camera = optics(read_json(intrinsics))
    if search.get('mode') == 'charuco':
        acquired = timestamp(search['camera_closed_at'])
    elif search.get('mode') == 'standard' and search.get('source') == 'fixed_focus_single_capture':
        # The worker records this bound immediately before a verified fresh exposure.
        acquired = timestamp(search['started_at'])
    else:
        raise ValueError('Expected a right-table search or checked fixed-focus capture.')
    fit = packet['pose']
    if (search.get('success') is not True or acquired < requested_at
            or search.get('device_id') != camera['device_id'] or packet.get('board') != 'right'
            or not right_board_fit_ok(fit)):
        raise ValueError('A fresh, checked right-table ChArUco pose with at least 12 markers is required.')
    if (optics(read_json(folder / 'intrinsics.json')) != camera or fit['image_size'] != camera['image_size']
            or meta.get('device_id') != camera['device_id'] or meta['standard']['lens_position'] != camera['focus']
            or meta.get('success') is not True or not (folder / 'standard.png').is_file()):
        raise ValueError('The ChArUco pose must use the carton program’s native camera optics.')
    if any(packet['source_config_sha256'].get(str(file.resolve())) != sha256(file)
           for file in (LAYOUT, BASE_BINDINGS)):
        raise ValueError('The ChArUco pose must use the current table definition and adopted base bindings.')
    session = dict(schema_version=1, board='right_table_board', valid_from=acquired.isoformat(),
                   valid_until=(acquired + LIFETIME).isoformat(), optics=camera, sources_sha256=validation_sources(),
                   T_camera_board=fit['T_camera_board'], held_out_rms_px=fit['held_out_rms_px'],
                   right_marker_count=len(set(fit['fit_marker_ids']) | set(fit['check_marker_ids'])), capture_directory=str(capture),
                   pose_sha256=sha256(folder / 'pose.json'))
    validate_session(session, intrinsics)
    return session


def validate_session(session, intrinsics, *, now=None, photo=None):
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(session, dict) or session.get('schema_version') != 1 or session.get('board') != 'right_table_board':
        raise ValueError('Calibrate the OAK4 for the right table before starting the carton program.')
    start = timestamp(session['valid_from'])
    end = timestamp(session['valid_until'])
    if end - start != LIFETIME or not start <= now < end:
        raise ValueError('The OAK4 camera calibration is outside its 12-hour window. Recalibrate the camera.')
    camera = optics(read_json(intrinsics))
    if session['optics'] != camera or session['sources_sha256'] != validation_sources():
        raise ValueError('The camera optics, table definition or base bindings changed. Recalibrate the camera.')
    pose = session['T_camera_board']
    if (len(pose) != 4 or any(len(row) != 4 or any(not math.isfinite(value) for value in row) for row in pose)
            or pose[3] != [0, 0, 0, 1] or pose[2][3] <= 0):
        raise ValueError('The stored OAK4 camera transform is invalid. Recalibrate the camera.')
    if photo is not None:
        if photo.get('device_id') != camera['device_id'] or photo['standard']['lens_position'] != camera['focus']:
            raise ValueError('The current carton photo uses a different camera or focus. Recalibrate the camera.')
        if not start <= timestamp(photo['started_at']) < end:
            raise ValueError('The carton photo is outside the OAK4 calibration window. Capture a new photo.')
    return session


def write_session(path, session):
    with NamedTemporaryFile(dir=path.parent, prefix='.camera-session-', delete=False, mode='w') as stream:
        temporary = Path(stream.name)
        try:
            json.dump(session, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

"""Persistent object scan sessions and published candidates for Program Library."""

from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from threading import Thread
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
PROGRAM = 'object-scan-v1'
IDENTIFIER = re.compile(r'[a-f0-9]{32}')
CAMERAS = ('oak4', 'oak_pro', 'wrist_left_front', 'wrist_left_rear',
           'wrist_right_front', 'wrist_right_rear')
FACES = ('+x', '-x', '+y', '-y', '+z', '-z')
BUSY = frozenset(('capturing', 'analyzing', 'assessing', 'publishing'))
GEOMETRY_BLOCKER = ('A checked grasp and presentation sequence needs a current cell-frame pose, verified contacts '
                    'and load, and complete collision-checked paths for the arms and carried object in Motion Review.')
MEDIA_TYPES = {'.jpg': 'image/jpeg', '.png': 'image/png', '.json': 'application/json',
               '.glb': 'model/gltf-binary', '.obj': 'text/plain', '.mtl': 'text/plain',
               '.step': 'application/step', '.stl': 'model/stl', '.zip': 'application/zip'}


def catalog():
    return dict(id=PROGRAM, kind='object_scan', title='Object scan', object='User-described object',
                description='Locate an object, review proposed grasps and camera views, then build an Asset Library candidate.',
                device='OAK4 · OAK Pro · wrist cameras', arms=[], demo_available=False, live_available=False,
                stages=[dict(id='capture', title='Capture the object on the table'),
                        dict(id='analyze', title='Review Gemini’s object and view proposals'),
                        dict(id='assess', title='Check coverage and identify missing views'),
                        dict(id='publish', title='Publish an asset candidate')])


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    temporary = path.with_name(f'.{path.name}.{uuid4().hex}.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n',
                             encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def revision(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def text_field(value, field, limit, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not 0 < len(value.strip()) <= limit:
        raise ValueError(f'Enter {field} (1–{limit} characters).')
    return value.strip()


def fields(payload, required=(), optional=()):
    if not isinstance(payload, dict) or set(required) - payload.keys() or payload.keys() - set(required) - set(optional):
        raise ValueError('Invalid object scan request fields.')


def camera_selection(value):
    if (not isinstance(value, list) or not 1 <= len(value) <= len(CAMERAS)
            or any(camera not in CAMERAS for camera in value) or len(set(value)) != len(value)):
        raise ValueError('Select one or more distinct scan cameras.')
    return value


def number(value, minimum, maximum):
    return type(value) in (float, int) and minimum <= value <= maximum and math.isfinite(value)


def dimensions(value):
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 3 or not all(number(n, 1, 5000) for n in value):
        raise ValueError('Enter three box dimensions in millimetres (each 1–5000 mm).')
    return value


def candidate_dimensions(data):
    if data['dimensions_mm']:
        return data['dimensions_mm'], 'operator dimensions'
    metric = data.get('metric_geometry') or {}
    size = (metric.get('obb') or {}).get('size_m')
    if isinstance(size, list) and len(size) == 3 and all(number(n, 0.001, 5) for n in size):
        return [round(n * 1000, 2) for n in size], 'provisional local RGB-D fit'
    return None, None


def lease(stack, path, message):
    handle = stack.enter_context(path.open('a'))
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError(message) from error


def scan_source(directory, name):
    path = (directory / name).resolve(strict=True)
    if not path.is_relative_to(directory) or not path.is_file():
        raise ValueError('The scan source is outside the session directory.')
    return path


class Scans:
    def __init__(self, directory, runs, *, workspace=WORKSPACE, perception=None, exporter=None):
        self.directory = directory.resolve()
        self.runs = runs
        self.workspace = workspace
        self.perception = perception
        self.exporter = exporter or self.export_box

    def _provider(self):
        if self.perception is None:
            import object_scan_perception

            return object_scan_perception
        return self.perception

    def create(self, payload):
        fields(payload, ('name', 'description', 'camera_ids', 'robot_count'), ('shape', 'dimensions_mm'))
        robot_count = payload['robot_count']
        if robot_count is not None and (type(robot_count) is not int or robot_count not in range(1, 5)):
            raise ValueError('Choose one to four robots, or ask Gemini.')
        shape = payload.get('shape', 'other')
        if shape not in ('box', 'other'):
            raise ValueError('Choose box or other for the object shape.')
        size = dimensions(payload.get('dimensions_mm'))
        if size is not None and shape != 'box':
            raise ValueError('Box dimensions apply to box-shaped objects.')
        identifier = uuid4().hex
        created = timestamp()
        data = dict(id=identifier, name=text_field(payload['name'], 'an object name', 100),
                    description=text_field(payload['description'], 'an object description', 2000),
                    camera_ids=camera_selection(payload['camera_ids']), robot_count=robot_count,
                    shape=shape, dimensions_mm=size, status='ready', created_at=created, updated_at=created,
                    captures=[], analysis=None, proposal=None, approval=None, coverage=None, textures=[],
                    asset=None, error=None)
        directory = self.directory / identifier
        directory.mkdir(parents=True, mode=0o700)
        write(directory / 'session.json', data)
        return self.presentation(data)

    def _directory(self, identifier):
        if not IDENTIFIER.fullmatch(identifier):
            raise FileNotFoundError('Scan not found.')
        directory = self.directory / identifier
        if not (directory / 'session.json').is_file():
            raise FileNotFoundError('Scan not found.')
        return directory

    def _save(self, directory, data):
        data['updated_at'] = timestamp()
        write(directory / 'session.json', data)

    def _read(self, directory):
        data = read(directory / 'session.json')
        if data['status'] not in BUSY:
            return data
        with ExitStack() as stack:
            try:
                lease(stack, directory / '.lock', 'This scan operation is still running.')
            except RuntimeError:
                return data
            return self._recover(directory)

    def _recover(self, directory):
        data = read(directory / 'session.json')
        if data['status'] in BUSY:
            state = data['status']
            data.update(status='error', error=f'The {state} step was interrupted. Retry it from the scan.')
            self._save(directory, data)
        return data

    def get(self, identifier):
        return self.presentation(self._read(self._directory(identifier)))

    def _sessions(self):
        for path in self.directory.glob('*/session.json'):
            if IDENTIFIER.fullmatch(path.parent.name):
                yield read(path)

    def list(self):
        sessions = sorted(self._sessions(), key=lambda data: data['updated_at'], reverse=True)
        return [self.presentation(data) for data in sessions]

    def assets(self):
        assets = [data['asset'] for data in self._sessions() if data['asset'] is not None]
        return sorted(assets, key=lambda asset: asset['updated_at'], reverse=True)

    @staticmethod
    def presentation(data):
        visible = {key: value for key, value in data.items() if key != 'artifacts'}
        return {**visible, 'captures': [{**group, 'files': [
            {key: photo[key] for key in ('camera', 'preview', 'url', 'error', 'width', 'height', 'display_rotation_deg')
             if key in photo} for photo in group['files']]} for group in data['captures']],
            'publish_available': bool(data['coverage']) and data['status'] not in BUSY}

    @staticmethod
    def _artifact_url(identifier, key):
        return f'/api/scans/{identifier}/files/{key}'

    def artifact(self, identifier, key):
        directory = self._directory(identifier)
        data = read(directory / 'session.json')
        path = data.get('artifacts', {}).get(key)
        if path is None:
            raise FileNotFoundError('Scan file not found.')
        source = scan_source(directory, path)
        return source, MEDIA_TYPES[source.suffix.lower()]

    def action(self, identifier, action, payload):
        handlers = dict(capture=self._capture, analyze=self._analyze, assess=self._assess, approve=self._approve,
                        texture=self._texture, dimensions=self._dimensions, publish=self._publish)
        if action not in handlers:
            raise FileNotFoundError('Scan action not found.')
        directory = self._directory(identifier)
        with ExitStack() as stack:
            lease(stack, directory / '.lock', 'Another operation is active for this scan.')
            data = self._recover(directory)
            operation = handlers[action](directory, data, payload, stack)
            if operation is None:
                data.update(status='ready', error=None)
                self._save(directory, data)
                return False, self.presentation(data)
            state, work = operation
            data.update(status=state, error=None)
            self._save(directory, data)
            result = self.presentation(data)
            worker_locks = stack.pop_all()
            try:
                Thread(target=self._work, args=(directory, data, work, worker_locks), daemon=True).start()
            except RuntimeError:
                worker_locks.close()
                raise
            return True, result

    def _work(self, directory, data, work, locks):
        with locks:
            try:
                updates = work()
                data.update(updates, status='ready', error=None)
            except Exception as error:
                data.update(status='error', error=str(error).strip()[:600] or type(error).__name__)
            self._save(directory, data)

    def _capture(self, directory, data, payload, stack):
        fields(payload, ('label',), ('camera_ids', 'notes'))
        label = text_field(payload['label'], 'a view label', 180)
        notes = text_field(payload.get('notes'), 'placement notes', 1000, optional=True)
        camera_ids = camera_selection(payload.get('camera_ids', data['camera_ids']))
        lease(stack, self.runs / '.run.lock', 'Another library program is running. Capture when it has finished.')
        group_id = uuid4().hex
        output = directory / 'captures' / group_id

        def work():
            overview = 'oak4' in camera_ids and not any(
                'rgbd_path' in photo for group in data['captures'] for photo in group['files'])
            captures = self._provider().capture(camera_ids, output, workspace=self.workspace, rgbd=overview)
            artifacts = dict(data.get('artifacts', {}))
            files = []
            for photo in captures:
                camera = photo['camera']
                record = {key: photo[key] for key in ('camera', 'image_sha256', 'preview_sha256', 'source',
                                                      'width', 'height', 'display_rotation_deg', 'error') if key in photo}
                for field in ('image', 'preview', 'metadata', 'rgbd'):
                    if photo.get(field):
                        path = Path(photo[field]).resolve(strict=True)
                        if not path.is_relative_to(directory):
                            raise ValueError('The camera returned a source outside the session.')
                        record[f'{field}_path'] = path.relative_to(directory).as_posix()
                        if field != 'rgbd':
                            key = f'{group_id}/{camera}/{field}{path.suffix.lower()}'
                            artifacts[key] = record[f'{field}_path']
                            record['url' if field == 'image' else field] = self._artifact_url(data['id'], key)
                files.append(record)
            if not any('image_path' in photo for photo in files):
                raise RuntimeError('No image was captured.')
            group = dict(id=group_id, label=label, notes=notes, camera_ids=camera_ids, at=timestamp(), files=files)
            return dict(captures=[*data['captures'], group], coverage=None, artifacts=artifacts)

        return 'capturing', work

    @staticmethod
    def _view_records(directory, data):
        records = []
        for group in data['captures']:
            photos = []
            for photo in group['files']:
                if 'image_path' not in photo:
                    continue
                source = {key: photo[key] for key in ('camera', 'image_sha256', 'preview_sha256', 'source',
                                                      'width', 'height', 'display_rotation_deg') if key in photo}
                for field in ('image', 'preview', 'metadata', 'rgbd'):
                    if photo.get(f'{field}_path'):
                        source[field] = str((directory / photo[f'{field}_path']).resolve(strict=True))
                photos.append(source)
            records.append(dict(label=group['label'], notes=group.get('notes'), captures=photos))
        return records

    @staticmethod
    def _gemini_consent(payload, optional=()):
        fields(payload, ('allow_gemini',), optional)
        if payload['allow_gemini'] is not True:
            raise ValueError('Confirm sending the selected scan views to Gemini via Antigravity.')

    def _analyze(self, directory, data, payload, stack):
        self._gemini_consent(payload, ('answer',))
        answer = payload.get('answer')
        answer = text_field(None if answer == '' else answer, 'an answer', 1200, optional=True)
        if not data['captures']:
            raise ValueError('Capture an overview first.')
        output = directory / 'analysis' / uuid4().hex

        def work():
            records = self._view_records(directory, data)
            previous = (data['proposal'] or {}).get('source_capture_id')
            position = next((i for i, group in enumerate(data['captures']) if answer and group['id'] == previous), -1)
            result = self._provider().investigate(data['description'], records[position]['captures'], output,
                                                  arm_count=data['robot_count'], answer=answer, workspace=self.workspace)
            proposal = dict(approach=result['approach'], presentation_views=result['presentation_views'],
                            source_capture_id=data['captures'][position]['id'], motion_status='blocked',
                            motion_blocker=GEOMETRY_BLOCKER)
            proposal['revision'] = revision(dict(proposal=proposal, analysis=result, answer=answer))
            metric = next((geometry for geometry in result['geometry'] if geometry.get('obb')), None)
            updates = dict(analysis=result, answer=answer, proposal=proposal, approval=None)
            if metric:
                updates['metric_geometry'] = {**metric, 'source_capture_id': proposal['source_capture_id']}
            return updates

        return 'analyzing', work

    def _approve(self, directory, data, payload, stack):
        fields(payload, ('revision',))
        proposal = data['proposal']
        if proposal is None or proposal['revision'] != payload['revision']:
            raise ValueError('Review the current scan proposal before approving it.')
        data['approval'] = dict(revision=proposal['revision'], at=timestamp(), scope='scan_sequence')

    def _assess(self, directory, data, payload, stack):
        self._gemini_consent(payload)
        if not data['captures']:
            raise ValueError('Capture at least one view first.')
        output = directory / 'coverage' / uuid4().hex

        def work():
            records = self._view_records(directory, data)
            family = 'cuboid' if data['shape'] == 'box' else None
            coverage = self._provider().assess(data['description'], records, output,
                                               family=family, workspace=self.workspace)
            return dict(coverage=coverage)

        return 'assessing', work

    def _dimensions(self, directory, data, payload, stack):
        fields(payload, ('dimensions_mm',))
        if data['shape'] != 'box':
            raise ValueError('Box dimensions apply to box-shaped objects.')
        data['dimensions_mm'] = dimensions(payload['dimensions_mm'])

    def _texture(self, directory, data, payload, stack):
        fields(payload, ('face', 'capture_id', 'camera', 'corners'))
        face = payload['face']
        if data['shape'] != 'box' or face not in FACES:
            raise ValueError('Select a face of a box-shaped object.')
        corners = payload['corners']
        if not isinstance(corners, list) or len(corners) != 4 or any(
                not isinstance(p, list) or len(p) != 2 or not all(number(n, 0, 1) for n in p) for p in corners):
            raise ValueError('Select four ordered corner pairs inside the image.')
        points = [tuple(p) for p in corners]
        turns = [(b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
                 for a, b, c in zip(points, points[1:] + points[:1], points[2:] + points[:2])]
        if not all(turn < -1e-8 for turn in turns):
            raise ValueError('Select four corners in outward-face order: lower left, lower right, upper right, upper left.')
        photo = self._photo(data, payload['capture_id'], payload['camera'])
        if photo is None:
            raise ValueError('Choose a photo captured for this scan.')
        assignment = dict(payload, image_sha256=photo['image_sha256'])
        data['textures'] = [item for item in data['textures'] if item['face'] != face] + [assignment]

    @staticmethod
    def _photo(data, capture_id, camera):
        return next((photo for group in data['captures'] if group['id'] == capture_id
                     for photo in group['files'] if photo['camera'] == camera and 'image_path' in photo), None)

    def _publish(self, directory, data, payload, stack):
        fields(payload)
        if not data['captures'] or data['coverage'] is None:
            raise ValueError('Assess the current captured views before publishing a draft.')
        generation = uuid4().hex
        output = directory / 'published' / generation

        def work():
            return self._build_asset(directory, data, output, generation)

        return 'publishing', work

    def _build_asset(self, directory, data, output, generation):
        output.mkdir(parents=True)
        artifacts = dict(data.get('artifacts', {}))
        files = []

        def register(path, label):
            path = scan_source(output, path)
            key = f'asset/{generation}/{path.relative_to(output).as_posix()}'
            artifacts[key] = path.relative_to(directory).as_posix()
            url = self._artifact_url(data['id'], key)
            files.append(dict(label=label, url=url))
            return url

        model = None
        size_mm, dimension_source = candidate_dimensions(data)
        if data['shape'] == 'box' and size_mm:
            textures = {}
            for item in data['textures']:
                photo = self._photo(data, item['capture_id'], item['camera'])
                size = photo['width'] - 1, photo['height'] - 1
                textures[item['face']] = dict(image=str(scan_source(directory, photo['image_path'])),
                                              image_sha256=item['image_sha256'], corners_px=[
                    [x * size[0], y * size[1]] for x, y in item['corners']])
            mesh = self.exporter(output / 'model', size_mm, textures)
            model = dict(shape='box', dimensions_mm=size_mm, dimension_source=dimension_source,
                         textured_faces=mesh['textured_faces'], missing_texture_faces=mesh['missing_texture_faces'],
                         status='draft', geometry_validated=False, url=None)
            for file in mesh['files']:
                path = file['path']
                url = register(f'model/{path}', file['name'])
                if path == 'model.glb':
                    model['url'] = url
            register('model/asset.json', 'Model manifest')
        photos = [photo for group in data['captures'] for photo in group['files'] if 'image_path' in photo]
        previous = data['asset']
        published = timestamp()
        asset = dict(id=data['id'], name=data['name'], description=data['description'], status='draft',
                     created_at=previous['created_at'] if previous else published, updated_at=published,
                     preview=photos[0].get('preview'), coverage=data['coverage'], model=model, files=files,
                     photo_count=len(photos), manipulation_approved=False)
        provenance = dict(asset=asset, scan_id=data['id'], robot_count=data['robot_count'],
                          capture_sets=[dict(id=group['id'], label=group['label'], notes=group.get('notes'), at=group['at'],
                                             files=[{key: photo[key] for key in ('camera', 'image_sha256', 'width',
                                                    'height', 'url', 'error') if key in photo}
                                                    for photo in group['files']]) for group in data['captures']],
                          analysis=data['analysis'], metric_geometry=data.get('metric_geometry'),
                          proposal=data['proposal'], approval=data['approval'],
                          texture_assignments=data['textures'])
        write(output / 'scan-manifest.json', provenance)
        register('scan-manifest.json', 'Scan manifest')
        return dict(asset=asset, artifacts=artifacts)

    def export_box(self, output, size, textures):
        python = self.workspace / '.venvs/oak-model/bin/python'
        if not python.is_file():
            raise RuntimeError('The workstation’s oak-model environment is required to export a box candidate.')
        result = subprocess.run([python, ROOT / 'tools/object_scan_asset.py', '--output', output],
                                input=json.dumps(dict(dimensions_mm=size, face_textures=textures)),
                                text=True, capture_output=True, timeout=120, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'Box export failed.')
        return json.loads(result.stdout)

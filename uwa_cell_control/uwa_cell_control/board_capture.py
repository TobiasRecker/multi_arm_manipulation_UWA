"""Mobile-board observations and camera-only three-camera datasets."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid

import cv2
import numpy as np
import yaml

from .wrist_camera import WristCamera
from .wrist_hd import NativeCapture, SSH, control_path

CAMERAS = ('right_front', 'right_rear', 'oak4')


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


class MobileBoard:
    def __init__(self, config):
        self.config = config
        self.ids = set(config['marker_ids'])
        dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config['dictionary']))
        self.board = cv2.aruco.CharucoBoard((config['squares_x'], config['squares_y']),
            config['square_length'], config['marker_length'], dictionary,
            np.asarray(config['marker_ids'], np.int32))
        self.board.setLegacyPattern(config.get('legacy_pattern', False))
        params = cv2.aruco.DetectorParameters()
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.CharucoDetector(self.board, cv2.aruco.CharucoParameters(), params)
        self.total = (config['squares_x'] - 1) * (config['squares_y'] - 1)

    def observe(self, image):
        if image is None or image.ndim != 3 or image.dtype != np.uint8:
            raise ValueError('Expected decoded uint8 BGR image')
        corners, ids, markers, marker_ids = self.detector.detectBoard(image)
        annotated = image.copy()
        seen = []
        if marker_ids is not None:
            selected = [i for i, value in enumerate(marker_ids.ravel()) if int(value) in self.ids]
            seen = [int(marker_ids[i, 0]) for i in selected]
            if selected:
                cv2.aruco.drawDetectedMarkers(annotated, [markers[i] for i in selected],
                                             marker_ids[selected])
        result = dict(board_id=self.config['board_id'], marker_ids=seen, corners=0,
            total_corners=self.total, corner_ids=[], object_points=[], image_points=[],
            image_size=[image.shape[1], image.shape[0]], full=False, usable=False,
            status='NOT SEEN', calibration_quality_validated=False)
        if ids is not None and len(ids) and np.isfinite(corners).all():
            objects, pixels = self.board.matchImagePoints(corners, ids)
            cv2.aruco.drawDetectedCornersCharuco(annotated, corners, ids)
            result.update(corners=len(ids), corner_ids=ids.ravel().astype(int).tolist(),
                object_points=objects.reshape(-1, 3).astype(float).tolist(),
                image_points=pixels.reshape(-1, 2).astype(float).tolist(),
                full=len(ids) == self.total,
                usable=len(ids) >= 12 and not self.board.checkCharucoCornersCollinear(ids))
        if result['full']:
            result['status'] = 'FULL BOARD'
        elif result['corners'] or seen:
            result['status'] = 'PARTIAL BOARD'
        return result, annotated


class OakPreview:
    """Owns only its SDK child. Stop waits for orderly device/lock release."""
    def __init__(self, workspace, camera, output, focus=116):
        self.ws, self.camera, self.output, self.focus = Path(workspace), camera, Path(output), focus
        self.child = self.log = None
        self.lock = threading.RLock()

    def start(self):
        with self.lock:
            if self.child is not None and self.child.poll() is None:
                return
            self.output.mkdir(parents=True, exist_ok=True)
            (self.output / 'frame.bin').unlink(missing_ok=True)
            self.log = (self.output / 'preview.log').open('a')
            self.child = subprocess.Popen([str(self.ws / 'setup/oak4/bin/oakctl'), 'run-script',
                str(self.ws / '.venvs/oak4/bin/python'), '-u',
                str(self.ws / 'src/oak_camera_calibration/tools/oak4_board_preview.py'),
                '--ip', self.camera['ip'], '--device-id', str(self.camera['device_id']),
                '--output', str(self.output), '--focus', str(self.focus),
                '--lock', str(self.ws / 'setup/oak4/photos/.capture.lock')],
                env={k: v for k, v in dict(os.environ, DEPTHAI_TELEMETRY='0',
                     OAKCTL_ANALYTICS='0').items() if k != 'PYTHONPATH'},
                stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)

    def stop(self):
        with self.lock:
            was_running = self.child is not None and self.child.poll() is None
            if self.child is not None and self.child.poll() is None:
                # oakctl execs the SDK worker; SIGTERM is handled by that worker.
                import signal
                os.killpg(self.child.pid, signal.SIGTERM)
                try:
                    self.child.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    raise RuntimeError('OAK preview did not release device; capture cancelled')
            if was_running:
                # oakctl's wrapper can exit before its SDK child has finished
                # device shutdown. Wait for the shared lock, never assume that
                # reaping the wrapper proves the device is released.
                deadline = time.monotonic() + 25
                with (self.ws / 'setup/oak4/photos/.capture.lock').open('a') as lock:
                    while True:
                        try:
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            fcntl.flock(lock, fcntl.LOCK_UN)
                            break
                        except BlockingIOError:
                            if time.monotonic() >= deadline:
                                raise RuntimeError('OAK SDK still owns capture lock; capture cancelled')
                            time.sleep(.1)
            if self.log:
                self.log.close()
                self.log = None

    def read(self):
        if self.child is None or self.child.poll() is not None:
            raise RuntimeError('OAK preview stopped/unavailable; see ' + str(self.output / 'preview.log'))
        header, jpeg = (self.output / 'frame.bin').read_bytes().split(b'\n', 1)
        return jpeg, json.loads(header)


class CaptureRig:
    def __init__(self, workspace, output=None):
        self.ws = Path(workspace).resolve()
        repo = self.ws / 'src/multi_arm_manipulation_UWA'
        self.inventory = yaml.safe_load((repo / 'config/hardware_inventory.yaml').read_text())
        self.board_config = yaml.safe_load((repo / 'uwa_cell_description/config/mobile_charuco_a4.yaml').read_text())
        self.optics = yaml.safe_load((repo / 'config/three_camera_capture.yaml').read_text())
        self.output = Path(output or self.ws / 'setup/calibration/three_camera_mobile')
        self.output.mkdir(parents=True, exist_ok=True)
        lock_root = self.ws / 'setup/calibration/three_camera_mobile'
        lock_root.mkdir(parents=True, exist_ok=True)
        self.instance_lock = (lock_root / '.rig.lock').open('a')
        try:
            fcntl.flock(self.instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('UWA Camera Capture is already running; use the existing window') from None
        self.session = self.output / (datetime.now().strftime('%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:8])
        self.session.mkdir()
        write_json(self.session / 'board.json', self.board_config)
        self.preview = OakPreview(self.ws, self.inventory['cameras']['oak4'], self.session / 'preview',
                                  self.optics['oak_manual_focus'])
        self.busy = threading.Lock()
        self.original_settings = {}
        self.fixed_settings = {}

    def native(self, name, output):
        ip = self.inventory['robots'][name]['ip']
        return NativeCapture(ip, SSH(ip, control_path(name, ip)), output,
            resources=self.ws / 'src/multi_arm_manipulation_UWA/uwa_cell_control/remote')

    def lock_focus(self):
        """Apply the repeatable acquisition focus profile; restore on close."""
        for name in CAMERAS[:2]:
            camera = self.wrist(name)
            original = camera.settings(refresh=True)
            if name not in self.original_settings:
                self.original_settings[name] = original
                write_json(self.session / 'original_wrist_settings.json', self.original_settings)
            target = self.optics['wrist_manual_focus'][name]
            if not original['focusAuto'] and original['focus'] == target:
                continue
            camera.request('/setcamerasettings?setManualValuesIfModeChanged=true',
                body={'cameraSettings': {'focusAuto': False, 'focus': target}})
            time.sleep(.5)
            actual = camera.settings(refresh=True)
            version = camera.request('/hello').get('version', '')
            if actual['lightingMode'] != original['lightingMode'] and version.startswith('UCC-1.11.1.'):
                camera.request('/setcamerasettings?setManualValuesIfModeChanged=true',
                    body={'cameraSettings': {'lightingMode': 1 - original['lightingMode']}})
                time.sleep(.3)
                actual = camera.settings(refresh=True)
            if actual['focusAuto'] or actual['focus'] != target:
                raise RuntimeError(name + ': could not confirm fixed focus')
            ignored = {'focusAuto', 'focus'}
            if original.get('exposureAuto'):
                ignored.update(('exposure', 'gain'))
            differences = [k for k in original if k not in ignored and original[k] != actual[k]]
            if differences:
                raise RuntimeError(name + ': focus lock changed other settings: ' + ', '.join(differences))
        self.fixed_settings = {name: self.wrist(name).settings(refresh=True) for name in CAMERAS[:2]}
        write_json(self.session / 'fixed_wrist_settings.json', self.fixed_settings)

    def restore_focus(self):
        results = {}
        for name, original in self.original_settings.items():
            if original['focusAuto'] or original['focus'] != self.optics['wrist_manual_focus'][name]:
                try:
                    results[name] = self.native(name, self.session / 'restore').restore_configuration(original)
                except Exception as error:
                    results[name] = {'error': str(error)}
        write_json(self.session / 'focus_restoration.json', results)
        errors = [name + ': ' + value['error'] for name, value in results.items() if 'error' in value]
        if errors:
            raise RuntimeError('; '.join(errors))

    def wrist(self, name):
        return WristCamera(self.inventory['robots'][name]['ip'])

    def capture_one(self, name, directory, native=True):
        directory.mkdir()
        started = utc()
        record = dict(camera=name, started_at=started, success=False)
        try:
            if name == 'oak4':
                path = self.ws / 'src/oak_camera_calibration/tools/oak4_photo_service.py'
                spec = importlib.util.spec_from_file_location('uwa_oak_photo', path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Single native 8K frame, no temporal averaging of a handheld board.
                result = module.PhotoCapture(self.ws).capture('standard', focus=self.preview.focus)
                source = Path(result['images']['standard'])
                image_path = directory / 'image.png'
                shutil.copy2(source, image_path)
                record.update(source='oak4_native_8000x6000_single', original=result,
                    camera_metadata=json.loads(Path(result['metadata']).read_text()))
            else:
                camera = self.wrist(name)
                identity = camera.request('/hello')
                settings = camera.settings(refresh=True)
                record.update(camera_identity=identity, settings_before=settings)
                expected = self.fixed_settings.get(name)
                if expected and (settings['focusAuto'] or settings['focus'] != expected['focus']):
                    raise RuntimeError('Session focus was changed externally; start a new session')
                if native:
                    result = self.native(name, directory / 'native').capture()
                    source = Path(result['directory']) / result['frames_metadata'][-1]['image']
                    record.update(source='wrist_native_2592x1944', native_burst=result)
                    shutil.copy2(source, directory / 'image.jpg')
                else:
                    camera.trigger()
                    (directory / 'image.jpg').write_bytes(camera.image())
                    record['source'] = 'wrist_http_vga_640x480'
                image_path = directory / 'image.jpg'
                after = camera.settings(refresh=True)
                record.update(camera_identity=identity, settings_before=settings, settings_after=after,
                    manual_focus=not settings['focusAuto'],
                    focus_unchanged=settings['focus'] == after['focus'] and settings['focusAuto'] == after['focusAuto'])
                if not record['focus_unchanged']:
                    raise RuntimeError('Wrist focus changed during capture; saved image is diagnostic only')
            image = cv2.imread(str(image_path))
            observation, annotated = MobileBoard(self.board_config).observe(image)
            scale = min(1., 1200 / annotated.shape[1])
            cv2.imwrite(str(directory / 'annotated.jpg'), cv2.resize(annotated, None, fx=scale, fy=scale))
            record.update(success=True, image=image_path.name, observation=observation,
                sha256=hashlib.sha256(image_path.read_bytes()).hexdigest())
        except Exception as error:
            record['error'] = str(error)
        record.update(finished_at=utc(), timestamp_kind='host request/completion window; not exposure synchronization')
        write_json(directory / 'record.json', record)
        return record

    def capture_all(self, native=True, resume_preview=False):
        if not self.busy.acquire(blocking=False):
            raise RuntimeError('Capture already running')
        directory = self.session / ('set_' + datetime.now().strftime('%H%M%S_%f'))
        directory.mkdir()
        report = dict(schema=1, started_at=utc(), cameras={}, board=self.board_config,
            hardware_synchronized=False, instruction='Hold board and cameras still during the entire acquisition',
            calibration_applied=False)
        report['optical_profiles'] = dict(wrist=self.fixed_settings, oak_manual_focus=self.preview.focus)
        try:
            self.preview.stop()
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {pool.submit(self.capture_one, name, directory / name, native): name for name in CAMERAS}
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        report['cameras'][name] = future.result()
                    except Exception as error:
                        report['cameras'][name] = dict(success=False, error=str(error))
        except Exception as error:
            report['error'] = str(error)
        finally:
            report.update(finished_at=utc(), directory=str(directory),
                all_captured=len(report['cameras']) == 3 and all(r['success'] for r in report['cameras'].values()))
            report['all_usable'] = report['all_captured'] and all(
                r['observation']['usable'] for r in report['cameras'].values())
            report['all_full'] = report['all_captured'] and all(
                r['observation']['full'] for r in report['cameras'].values())
            write_json(directory / 'manifest.json', report)
            self.busy.release()
            if resume_preview:
                self.preview.start()
        return report

"""Native camera sessions for the interactive six-camera board capture."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from .board_capture import CaptureRig, utc, write_json
from .oak4_capture_session import Oak4CaptureSession
from .session_photo_telemetry import SessionPhotoTelemetry
from .wrist_stream import WristStream


class ContinuousCaptureRig(CaptureRig):
    continuous = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preview = Oak4CaptureSession(self.ws, self.inventory['cameras']['oak4'],
                                          self.session / 'preview', self.preview.focus)
        self.streams = {'oak4': self.preview, 'oak_usb': self.usb}
        for name in self.wrist_cameras:
            self.streams[name] = WristStream(name, self.inventory['robots'][name]['ip'],
                                             self.session, self.optics['wrist_manual_focus'][name])
        self.observer = SessionPhotoTelemetry(self.ws, self.session, self.wrist_cameras,
                                              self.telemetry_source)
        self.on_frames_acquired = None
        self.requested_monotonic = None

    def start_streams(self):
        self.observer.start()
        # Open the OAKs once. Each wrist then hands over its own V4L2 device.
        self.preview.start()
        self.usb.start()
        with ThreadPoolExecutor(max_workers=len(self.wrist_cameras)) as pool:
            jobs = [pool.submit(self.streams[name].start) for name in self.wrist_cameras]
            for job in jobs:
                job.result()

    def stop_streams(self):
        errors = []
        with ThreadPoolExecutor(max_workers=len(self.streams)) as pool:
            jobs = {pool.submit(stream.stop): name for name, stream in self.streams.items()}
            for job in as_completed(jobs):
                try:
                    job.result()
                except Exception as error:
                    errors.append(f'{jobs[job]}: {error}')
        self.observer.stop()
        if errors:
            raise RuntimeError('; '.join(errors))

    def save_frame(self, name, directory, acquired):
        directory.mkdir()
        record = dict(camera=name, success=False, started_at=utc(), started_monotonic=time.monotonic(),
                      timestamp_kind='host request and frame confirmation plus device-specific metadata')
        try:
            path, metadata = self.streams[name].capture(directory, on_acquired=acquired)
            record.update(camera_metadata=metadata, image=path.name)
            if name in self.wrist_cameras:
                record.update(source='wrist_native_2592x1944_stream',
                              camera_identity=metadata['camera_identity'],
                              manual_focus=metadata['sensor_controls']['focus_auto'] == 0,
                              settings_before=metadata['settings'],
                              settings_source='fixed settings at native session entry')
            elif name == 'oak_usb':
                record.update(source='n100_usb_oak_native_4056x3040_single',
                              display_rotation_deg=180, raw_orientation='unaltered sensor coordinates')
            else:
                record['source'] = 'oak4_native_8000x6000_single'
            self.observe_photo(directory, path, record)
        except Exception as error:
            record['error'] = str(error)
        record.update(finished_at=utc(), finished_monotonic=time.monotonic())
        write_json(directory / 'record.json', record)
        return record

    def acquire_set(self, directory, report, native):
        if not native:
            raise ValueError('Continuous sessions capture native photos')
        report.update(acquisition_order='parallel requests on six running native streams',
                      instruction='Hold the board until all six frames have been acquired.')
        started = self.requested_monotonic if self.requested_monotonic is not None else time.monotonic()
        report['request_monotonic'] = started
        report['telemetry_before'] = self.observer.request('begin', directory)
        acquired_at = {}
        lock = threading.Lock()

        def end_audit():
            try:
                result = self.observer.request('end')
                report['telemetry_after'] = result.pop('endpoint_after')
                report['stationarity'] = result
            except Exception as error:
                report['telemetry_after'] = dict(arms={}, complete=False)
                report['stationarity'] = dict(stationarity_confirmed=False, error=str(error))

        def acquired(name):
            with lock:
                acquired_at.setdefault(name, time.monotonic())
                if len(acquired_at) != len(self.cameras) or 'all_frames_received_after_s' in report:
                    return
                elapsed = max(acquired_at.values()) - started
                report['all_frames_received_after_s'] = elapsed
            if self.on_frames_acquired:
                self.on_frames_acquired(elapsed)
            end_audit()

        try:
            with ThreadPoolExecutor(max_workers=len(self.cameras)) as pool:
                jobs = {pool.submit(self.save_frame, name, directory / name,
                                    lambda name=name: acquired(name)): name for name in self.cameras}
                for job in as_completed(jobs):
                    name = jobs[job]
                    try:
                        report['cameras'][name] = job.result()
                    except Exception as error:
                        report['cameras'][name] = dict(success=False, error=str(error))
        finally:
            if 'stationarity' not in report:
                end_audit()
            report['frame_confirmed_after_s'] = {name: stamp - started for name, stamp in acquired_at.items()}

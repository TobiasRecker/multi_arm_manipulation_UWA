"""Keep the existing read-only photo audit ready between multi-camera triggers."""
from collections import deque
from datetime import datetime, timezone
import multiprocessing
from pathlib import Path
import threading
import time


class SetSampleLog:
    """Write raw samples only while a photograph is being acquired."""

    def __init__(self):
        self.file = None
        self.lock = threading.Lock()
        self.recent = deque()

    def open(self, directory):
        with self.lock:
            self.file = (Path(directory) / 'joint_samples.jsonl').open('x')
            self.file.writelines(line for _, line in self.recent)

    def write(self, line):
        with self.lock:
            now = time.monotonic()
            self.recent.append((now, line))
            while self.recent and self.recent[0][0] < now - 1.:
                self.recent.popleft()
            if self.file is not None:
                self.file.write(line)

    def close(self):
        with self.lock:
            if self.file is not None:
                self.file.close()
                self.file = None


def endpoint(audit, source):
    now = time.monotonic()
    arms = {}
    for name, rows in audit.history.items():
        if rows and now - rows[-1][0] <= audit.freshness:
            received, q, qd = rows[-1]
            arms[name] = dict(joint_names=audit.names[name], positions=q.tolist(),
                              velocities=qd.tolist() if qd is not None else None,
                              received_monotonic=received)
    return dict(recorded_at=datetime.now(timezone.utc).isoformat(), arms=arms,
                complete=len(arms) == len(audit.names), source=source)


def observe(connection, workspace, directory, arms, source):
    from .capture_telemetry import CaptureMonitor
    from .capture_rtde import RtdeCaptureMonitor

    log = SetSampleLog()
    monitor = None
    try:
        factory = RtdeCaptureMonitor if source == 'rtde' else CaptureMonitor
        monitor = factory(workspace, directory, arms, sample_log=log)
        audit = monitor.audit
        while True:
            command, path = connection.recv()
            if command == 'stop':
                break
            try:
                disconnected = not monitor.thread.is_alive() or any(
                    not worker.is_alive() for worker in getattr(monitor, 'workers', ()))
                if command == 'begin':
                    if disconnected:
                        raise RuntimeError('; '.join(sorted(audit.violations)) or 'Photo telemetry disconnected')
                    if audit.armed:
                        raise RuntimeError('Photo telemetry is already recording a set')
                    # Let the existing monitor prove its settling interval from live history.
                    log.open(path)
                    monitor.wait_still()
                    with audit.lock:
                        value = endpoint(audit, source)
                elif command == 'end':
                    with audit.lock:
                        if not audit.armed:
                            raise RuntimeError('No photo telemetry window is active')
                        if disconnected:
                            audit.violations.add('Photo telemetry disconnected during acquisition')
                        audit.check_freshness(time.monotonic())
                        value = audit.summary()
                        value.update(endpoint_after=endpoint(audit, source),
                                     joint_samples='joint_samples.jsonl', telemetry_source=source,
                                     observer_isolation='separate read-only process')
                        if source == 'rtde':
                            value['timestamp_kind'] = 'controller output timestamp and host receipt'
                        audit.armed = False
                        audit.violations.clear()
                        audit.peaks = dict.fromkeys(audit.names, 0.)
                    log.close()
                else:
                    raise ValueError('Unknown photo telemetry operation')
                connection.send((True, value))
            except Exception as error:
                log.close()
                connection.send((False, str(error)))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        if monitor is not None:
            monitor.finish(save_report=False)
        connection.close()


class SessionPhotoTelemetry:
    def __init__(self, workspace, directory, arms, source):
        self.arguments = workspace, directory, arms, source
        self.child = self.channel = None

    def start(self):
        if self.child is not None:
            return
        context = multiprocessing.get_context('spawn')
        self.channel, child_channel = context.Pipe()
        self.child = context.Process(target=observe, args=(child_channel, *self.arguments), daemon=True)
        try:
            self.child.start()
        finally:
            child_channel.close()

    def request(self, command, directory=None):
        # A receipt can arrive on the last camera's thread. Only one RPC is
        # outstanding, and close/pause waits for the current set to finish.
        try:
            self.start()
            self.channel.send((command, directory))
            if not self.channel.poll(10):
                raise RuntimeError('Photo telemetry timed out')
            ok, value = self.channel.recv()
            if not ok:
                raise RuntimeError(value)
            return value
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.child is None:
            return
        try:
            if self.child.is_alive():
                try:
                    self.channel.send(('stop', None))
                except (OSError, EOFError):
                    pass
                self.child.join(5)
                if self.child.is_alive():
                    self.child.terminate()
                    self.child.join(2)
                if self.child.is_alive():
                    self.child.kill()
                    self.child.join()
        finally:
            self.channel.close()
            self.child = self.channel = None

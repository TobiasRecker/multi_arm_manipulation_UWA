"""Read-only continuous JointState audit during static object photographs.

Never starts drivers or sends commands. Images remain originals after a motion
violation; the audit denies their use as a confirmed stationary multi-view set.
"""
from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time

import numpy as np


class StationarityAudit:
    def __init__(self, names, *, freshness=.5, settle=.5, max_spread=.001, max_drift=.003):
        self.names = names
        self.freshness, self.settle = freshness, settle
        self.max_spread, self.max_drift = max_spread, max_drift
        self.history = {rid: deque() for rid in names}
        self.reference, self.violations = {}, set()
        self.peaks = {rid: 0. for rid in names}
        self.armed = False
        self.lock = threading.RLock()

    def receive(self, rid, positions, velocities, now):
        positions = np.asarray(positions, float)
        if positions.shape != (6,) or not np.isfinite(positions).all():
            return False
        with self.lock:
            rows = self.history[rid]
            rows.append((now, positions, velocities))
            while rows and rows[0][0] < now - max(2., 2 * self.settle):
                rows.popleft()
            if self.armed:
                delta = float(np.max(abs(positions - self.reference[rid])))
                self.peaks[rid] = max(self.peaks[rid], delta)
                if delta > self.max_drift:
                    self.violations.add(rid + ': motion during acquisition')
            return True

    def ready(self, now):
        with self.lock:
            for rid, rows in self.history.items():
                if not rows or now - rows[-1][0] > self.freshness:
                    return False
                window = [r for r in rows if r[0] >= now - self.settle - .1]
                if not window or window[-1][0] - window[0][0] < self.settle:
                    return False
                if any(b[0] - a[0] > self.freshness for a, b in zip(window, window[1:])):
                    return False
                if np.max(np.ptp([r[1] for r in window], axis=0)) > self.max_spread:
                    return False
                if any(v is not None and (not np.isfinite(v).all() or max(abs(np.asarray(v))) > .01)
                       for _, _, v in window):
                    return False
            return True

    def arm(self, now):
        with self.lock:
            if not self.ready(now):
                raise RuntimeError('All four arms must have fresh, settled telemetry before object photos')
            self.reference = {rid: rows[-1][1].copy() for rid, rows in self.history.items()}
            self.armed = True

    def check_freshness(self, now):
        with self.lock:
            if self.armed:
                for rid, rows in self.history.items():
                    if not rows or now - rows[-1][0] > self.freshness:
                        self.violations.add(rid + ': telemetry stale during acquisition')

    def summary(self):
        with self.lock:
            return dict(stationarity_confirmed=self.armed and not self.violations,
                        violations=sorted(self.violations), max_joint_drift_rad=dict(self.peaks),
                        reference_positions={rid: q.tolist() for rid, q in self.reference.items()},
                        limits=dict(freshness_s=self.freshness, settle_s=self.settle,
                                    settle_spread_rad=self.max_spread, acquisition_drift_rad=self.max_drift),
                        timestamp_kind='ROS JointState stamps and host monotonic receipt; not camera exposure synchronization')


class CaptureMonitor:
    def __init__(self, workspace, directory, arms):
        from match_ur_hardware.profiles import load_profiles
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.signals import SignalHandlerOptions
        import rclpy
        from sensor_msgs.msg import JointState
        from rclpy.qos import qos_profile_sensor_data
        self.profiles = load_profiles(Path(workspace) / 'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml')
        self.audit = StationarityAudit({rid: self.profiles[rid]['joint_names'] for rid in arms})
        self.directory = Path(directory)
        self.log = (self.directory / 'joint_samples.jsonl').open('w')
        self.context = Context()
        rclpy.init(args=[], context=self.context, domain_id=66, signal_handler_options=SignalHandlerOptions.NO)
        self.node = rclpy.create_node('uwa_object_photo_audit', context=self.context)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.subscriptions = [self.node.create_subscription(JointState, self.profiles[rid]['namespace'] + '/joint_states',
                              lambda msg, rid=rid: self.receive(rid, msg), qos_profile_sensor_data) for rid in arms]
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def receive(self, rid, msg):
        names = self.audit.names[rid]
        if len(msg.name) != len(msg.position) or len(set(msg.name)) != len(msg.name):
            return
        values = dict(zip(msg.name, msg.position))
        if not set(names) <= values.keys():
            return
        q = [values[j] for j in names]
        velocities = dict(zip(msg.name, msg.velocity)) if len(msg.velocity) == len(msg.name) else {}
        v = [velocities[j] for j in names] if velocities else None
        now = time.monotonic()
        if self.audit.receive(rid, q, v, now):
            record = dict(arm=rid, joint_names=names, positions=q, velocities=v, received_monotonic=now,
                          recorded_at=datetime.now(timezone.utc).isoformat(),
                          ros_stamp=dict(sec=msg.header.stamp.sec, nanosec=msg.header.stamp.nanosec))
            self.log.write(json.dumps(record, allow_nan=False) + '\n')

    def run(self):
        try:
            while not self.stopped.is_set():
                self.executor.spin_once(timeout_sec=.05)
                self.audit.check_freshness(time.monotonic())
        except Exception as error:
            self.audit.violations.add('telemetry observer failed: ' + str(error))

    def wait_still(self, timeout=5.):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.audit.ready(time.monotonic()):
                self.audit.arm(time.monotonic())
                return
            if not self.thread.is_alive():
                break
            time.sleep(.05)
        raise RuntimeError('Four-arm stationary telemetry unavailable; no object photos requested')

    def finish(self):
        self.audit.check_freshness(time.monotonic())
        self.stopped.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            self.audit.violations.add('telemetry observer did not stop')
        self.executor.shutdown(timeout_sec=1)
        self.node.destroy_node()
        self.context.try_shutdown()
        self.log.close()
        report = self.audit.summary()
        report['joint_samples'] = 'joint_samples.jsonl'
        (self.directory / 'stationarity.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        return report

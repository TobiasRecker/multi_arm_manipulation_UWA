"""Execution observations and user feedback for the cooperative task pilot.

No ROS or robot imports. Missing sensing is represented as unknown, never zero.
The append-only record separates model execution, measurements and user reports.
"""
import fcntl
import hashlib
import json
import math
from pathlib import Path
import time


EVENTS = ('missed_grasp', 'regrasp', 'object_lost', 'agent_intervention')
BACKENDS = ('kinematic_model', 'contact_simulation', 'hardware')
SOURCES = ('model', 'sensor', 'controller', 'agent', 'user')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


class Episode:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.manifest = json.loads((self.directory / 'episode.json').read_text())
        if self.manifest['sha256'] != digest({k: v for k, v in self.manifest.items() if k != 'sha256'}):
            raise ValueError('Episode manifest changed')

    @classmethod
    def create(cls, directory, *, backend, program_sha256, observable_events=(), metadata=None):
        if backend not in BACKENDS or set(observable_events) - set(EVENTS):
            raise ValueError('Unsupported backend or event detector')
        if backend == 'kinematic_model' and set(observable_events) - {'agent_intervention'}:
            raise ValueError('Kinematic model cannot detect physical grasp/drop events')
        if len(program_sha256) != 64 or any(c not in '0123456789abcdef' for c in program_sha256):
            raise ValueError('Expected program SHA256')
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=False)
        manifest = dict(schema_version=1, backend=backend, program_sha256=program_sha256,
                        observable_events=list(observable_events), metadata=metadata or {},
                        created_unix_s=time.time())
        manifest['sha256'] = digest(manifest)
        write(path / 'episode.json', manifest)
        (path / 'events.jsonl').touch(exist_ok=False)
        return cls(path)

    def records(self):
        previous = self.manifest['sha256']
        rows = []
        for line in (self.directory / 'events.jsonl').read_text().splitlines():
            row = json.loads(line)
            if row['previous_sha256'] != previous or row['sha256'] != digest({k: v for k, v in row.items() if k != 'sha256'}):
                raise ValueError('Episode event chain changed')
            rows.append(row)
            previous = row['sha256']
        return rows

    def append(self, kind, *, phase, source, model_time_s=None, details=None):
        if source not in SOURCES or not isinstance(phase, str) or not phase.strip():
            raise ValueError('Explicit source and phase required')
        if kind not in EVENTS + ('phase_start', 'phase_end', 'force_sample', 'feedback', 'run_end'):
            raise ValueError('Unknown event')
        if model_time_s is not None and (not math.isfinite(model_time_s) or model_time_s < 0):
            raise ValueError('Invalid model time')
        details = dict(details or {})
        if kind == 'agent_intervention' and source not in ('agent', 'user'):
            raise ValueError('Intervention must name agent or user origin')
        if kind == 'run_end':
            if details.get('status') not in ('MODEL_SEQUENCE_COMPLETE', 'DONE', 'FAILED', 'CANCELLED'):
                raise ValueError('Explicit terminal result required')
            if self.manifest['backend'] == 'kinematic_model' and details['status'] == 'DONE':
                raise ValueError('Kinematic completion is not physical task success')
            for key in ('processing_wall_s', 'execution_wall_s'):
                if key in details and (not math.isfinite(details[key]) or details[key] < 0):
                    raise ValueError('Invalid duration')
            if self.manifest['backend'] == 'kinematic_model' and details.get('execution_wall_s') is not None:
                raise ValueError('Kinematic compilation has no physical execution duration')
        if kind in EVENTS[:3]:
            if source not in ('sensor', 'controller', 'user') or (self.manifest['backend'] == 'kinematic_model' and source != 'user'):
                raise ValueError('Physical events need a detector or explicit user report')
            if source != 'user' and kind not in self.manifest['observable_events']:
                raise ValueError('Event detector not declared')
        if kind == 'feedback':
            if source != 'user' or not isinstance(details.get('text'), str) or not details['text'].strip():
                raise ValueError('Nonempty original user feedback required')
            details['text'] = details['text'].strip()
            details['status'] = 'RECORDED_FOR_REVIEW'
        if kind == 'force_sample':
            if self.manifest['backend'] == 'kinematic_model' or source != 'sensor':
                raise ValueError('Kinematic model has no force measurement')
            required = ('sensor_id', 'frame_id', 'reference_point', 'quantity', 'value_n', 'sequence', 'sample_time_s')
            if any(k not in details for k in required) or details['quantity'] != 'force_norm':
                raise ValueError('Force norm, sensor/frame/reference, sequence and source time required')
            if not all(isinstance(details[k], str) and details[k].strip() for k in required[:3]):
                raise ValueError('Force context must be named')
            if not isinstance(details['sequence'], int) or isinstance(details['sequence'], bool) or details['sequence'] < 0:
                raise ValueError('Invalid force sequence')
            if not math.isfinite(details['value_n']) or details['value_n'] < 0 or not math.isfinite(details['sample_time_s']):
                raise ValueError('Invalid force observation')
        json.dumps(details, allow_nan=False)
        with (self.directory / '.events.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            rows = self.records()
            if kind != 'feedback' and any(r['kind'] == 'run_end' for r in rows):
                raise ValueError('Execution is finished; only feedback can be appended')
            if kind not in ('feedback',) and model_time_s is not None:
                prior = [r['model_time_s'] for r in rows if r['kind'] != 'feedback' and r['model_time_s'] is not None]
                if prior and model_time_s < prior[-1] - 1e-9:
                    raise ValueError('Execution time must not move backwards')
            row = dict(index=len(rows), kind=kind, phase=phase, source=source,
                       model_time_s=model_time_s, received_unix_s=time.time(), details=details,
                       previous_sha256=rows[-1]['sha256'] if rows else self.manifest['sha256'])
            row['sha256'] = digest(row)
            with (self.directory / 'events.jsonl').open('a') as stream:
                stream.write(json.dumps(row, allow_nan=False) + '\n')
                stream.flush()
        return row

    def summary(self):
        rows = self.records()
        measured = {kind: sum(r['kind'] == kind and r['source'] != 'user' for r in rows)
                    if kind in self.manifest['observable_events'] else None for kind in EVENTS}
        reported = {kind: sum(r['kind'] == kind and r['source'] == 'user' for r in rows) for kind in EVENTS}
        forces = {}
        for row in rows:
            if row['kind'] != 'force_sample':
                continue
            d = row['details']
            key = (d['sensor_id'], d['frame_id'], d['reference_point'])
            forces.setdefault(key, []).append(d)
        peaks = []
        for (sensor, frame, point), values in forces.items():
            ordered = all(b['sequence'] > a['sequence'] and b['sample_time_s'] > a['sample_time_s']
                          for a, b in zip(values, values[1:]))
            consecutive = ordered and all(b['sequence'] == a['sequence'] + 1 for a, b in zip(values, values[1:]))
            peaks.append(dict(sensor_id=sensor, frame_id=frame, reference_point=point,
                              max_observed_force_n=max(v['value_n'] for v in values), samples=len(values),
                              consecutive_samples=consecutive,
                              coverage='observed samples only; full execution coverage not established'))
        end = next((r for r in reversed(rows) if r['kind'] == 'run_end'), None)
        result = dict(schema_version=1, backend=self.manifest['backend'],
                      episode_sha256=self.manifest['sha256'], last_event_sha256=rows[-1]['sha256'] if rows else None,
                      status=end['details']['status'] if end else 'RUNNING',
                      terminal_phase=end['phase'] if end else None,
                      terminal_details=end['details'] if end else None,
                      model_duration_s=end['model_time_s'] if end else None,
                      execution_wall_s=end['details'].get('execution_wall_s') if end else None,
                      processing_wall_s=end['details'].get('processing_wall_s') if end else None,
                      detected_events=measured, user_reported_events=reported,
                      force_channels=peaks, feedback=[r for r in rows if r['kind'] == 'feedback'],
                      phases=[r for r in rows if r['kind'] in ('phase_start', 'phase_end')])
        write(self.directory / 'summary.json', result)
        return result

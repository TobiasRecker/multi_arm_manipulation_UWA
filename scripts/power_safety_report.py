#!/usr/bin/env python3
"""Read existing UWA guard, carton workflow and motion review diagnostics."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import selectors
import socket
import sqlite3
import subprocess
import time

UNIT = 'uwa-hardware-motion.service'
ARM = re.compile(r'\b(?:left|right)_(?:front|rear)\b')
LATCH = re.compile(r'(STOP LATCHED|MONITOR WOULD STOP|MONITOR HELD CONDITION|HELD CONDITION):\s*(.*)')
NATIVE = re.compile(r'NATIVE STOP REQUESTED (\w+):\s*(.*)')
LOG_ROWS = 600
FILE_LIMIT = 4 * 1024 * 1024


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='milliseconds')


def compact(value, limit=450):
    return ' '.join(str(value or '').split())[:limit]


def source(name, status, detail):
    return dict(name=name, status=status, detail=detail)


def measurement(value, depth=0):
    if isinstance(value, (int, bool)) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if depth < 4 and isinstance(value, dict):
        return {compact(k,80):measurement(v,depth+1) for k,v in list(value.items())[:24]}
    if depth < 4 and isinstance(value, list):
        return [measurement(v,depth+1) for v in value[:10]]
    return compact(value,200)


def event(kind, origin, stamp, reason, arms=(), **extra):
    return dict(kind=kind, source=origin, at=utc(stamp), reason=compact(reason),
                arms=sorted(set(arms)), count=1, **extra)


def journal_rows(since, end, pattern=None):
    # Keep a bound even when journalctl takes time searching older entries or
    # a single journal record contains a large traceback.
    command = ['journalctl', '--user', '-u', UNIT, '--no-pager', '-q', '-o', 'json',
               '--all', '--output-fields=MESSAGE,_PID,_SYSTEMD_INVOCATION_ID',
               '--since', '@'+str(int(since)), '--until', '@'+str(math.ceil(end)),
               '-n', str(LOG_ROWS+1 if pattern else 1)]
    if pattern:
        command += ['--grep', pattern]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        try:
            raw = bytearray()
            deadline = time.monotonic()+3
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    if not selector.select(max(0., deadline-time.monotonic())):
                        raise ValueError('Journal query timed out')
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    raw.extend(chunk)
                    if len(raw) > 4 * 1024 * 1024:
                        raise ValueError('Journal byte limit reached')
                    if time.monotonic() > deadline:
                        raise ValueError('Journal query timed out')
            status = process.wait(timeout=max(.01, deadline-time.monotonic()))
        finally:
            if process.poll() is None:
                process.kill()
    if status and not (pattern and status == 1 and not raw.strip()):
        raise ValueError(compact(raw.decode(errors='replace'), 160) or f'journalctl exited {status}')
    rows = [json.loads(line) for line in raw.splitlines()]
    rows.sort(key=lambda row: int(row['__REALTIME_TIMESTAMP']))
    return rows[-LOG_ROWS:], len(rows) > LOG_ROWS


def native_reason(text):
    reason = text.split('; guard_fresh=', 1)[0]
    measurements = {}
    if reason.startswith('Blocked interlock: native hardware verification unavailable, age_s='):
        reason, value = reason.rsplit(', age_s=', 1)
        measurements['age_s'] = measurement(float(value))
    elif reason.startswith('Blocked interlock: manager_fresh='):
        fields = re.findall(r'(manager_fresh|hold_config_verified|held|controller_error|list_age_s|parameter_age_s)='
                            r'(.*?)(?=, (?:hold_config_verified|held|controller_error|list_age_s|parameter_age_s)=|$)', reason)
        for k,value in fields:
            if k.endswith('_s'):
                measurements[k] = measurement(float(value))
            else:
                measurements[k] = {'True':True, 'False':False, 'None':None}.get(value,compact(value))
        reason = 'Blocked interlock: ' + ', '.join(f'{k}={measurements[k]}' for k in
                 ('manager_fresh','hold_config_verified','held','controller_error') if k in measurements)
    if '; guard_fresh=' in text:
        measurements['guard_fresh'] = text.split('; guard_fresh=', 1)[1].split(';')[0] == 'True'
    if '; evidence=' in text:
        try:
            detail = ast.literal_eval(text.split('; evidence=', 1)[1][:4096])
            if isinstance(detail, dict):
                measurements['stationarity'] = measurement(detail)
        except (ValueError, SyntaxError, RecursionError):
            pass
    return reason, measurements


def guard_events(rows, issues):
    events, seen, native = [], set(), {}
    for row in sorted(rows, key=lambda row: int(row['__REALTIME_TIMESTAMP'])):
        stamp = int(row['__REALTIME_TIMESTAMP']) / 1e6
        msg = row.get('MESSAGE')
        if not isinstance(msg, str):
            issues.append('Unreadable journal message')
            continue
        process = (row.get('_BOOT_ID'), row.get('_SYSTEMD_INVOCATION_ID'), row.get('_PID'))
        if match := LATCH.search(msg):
            label, data = match.groups()
            kind = {'STOP LATCHED': 'Guard latch', 'HELD CONDITION': 'Condition while held',
                    'MONITOR WOULD STOP': 'Monitor observation',
                    'MONITOR HELD CONDITION': 'Monitor observation'}[label]
            try:
                causes = json.loads(data)
            except ValueError:
                issues.append('Malformed latch cause list')
                continue
            if not isinstance(causes, list):
                issues.append('Malformed latch cause list')
                continue
            for cause in causes or [dict(reason='Latch cause unavailable')]:
                if not isinstance(cause,dict) or not isinstance(cause.get('reason'),str):
                    issues.append('Unavailable latch cause')
                    continue
                reason = cause['reason']
                arms = tuple(sorted(cause.get('arms', [])))
                # Older services repeated the cumulative latch history when
                # another arm blocked. A fresh device observation has a new stamp.
                key = process, kind, arms, reason, cause.get('source_time_s', stamp)
                if key in seen:
                    continue
                seen.add(key)
                values = measurement({k:v for k,v in cause.items() if k not in ('source_time_s', 'reason', 'arms')})
                events.append(event(kind, UNIT, stamp, reason, arms, measurements=values))
        elif match := NATIVE.search(msg):
            arm, text = match.groups()
            try:
                reason, measurements = native_reason(text)
            except ValueError:
                reason, measurements = text, {}
            previous = native.get((process, arm, reason))
            if previous and 0 <= stamp-previous[0] <= 2:
                item = previous[1]
                item.setdefault('first_measurements',item['measurements'])
                item.update(count=item['count']+1, last_at=utc(stamp), measurements=measurements,
                            latest_message=compact(text))
            else:
                item = event('Native STOP request', UNIT, stamp, reason, [arm],
                             message=compact(text), measurements=measurements)
                events.append(item)
            native[(process, arm, reason)] = stamp, item
    return events


def read_guard(since, end, events):
    notes = []
    for pattern in ('STOP LATCHED|MONITOR WOULD STOP|HELD CONDITION', 'NATIVE STOP REQUESTED'):
        try:
            rows, clipped = journal_rows(since, end, pattern)
            events.extend(guard_events(rows, notes))
            if clipped:
                notes.append(f'{pattern} limited to newest {LOG_ROWS} records')
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
            notes.append(compact(exc))
    if notes:
        return source('Guard journal', 'partial', f'{UNIT}: '+'. '.join(dict.fromkeys(notes)))
    if not events:
        try:
            rows, _ = journal_rows(since, end)
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
            return source('Guard journal', 'unavailable', compact(exc))
        if not rows:
            return source('Guard journal', 'missing', f'No unit records accessible for {UNIT} in this period')
    return source('Guard journal', 'ok', f'{UNIT}, guard transitions and native STOP requests')


def read_json(path):
    with path.open('rb') as handle:
        data = handle.read(FILE_LIMIT+1)
    if len(data) > FILE_LIMIT:
        raise ValueError('file exceeds 4 MiB')
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError('invalid report')
    return value


def workflow_failure(record, result, failed_event):
    reason = compact(result.get('error') or record.get('error') or record.get('last_image_error') or record.get('phase'))
    arms = ARM.findall(reason)
    measures = {}
    evidence = result.get('alignment_evidence') or {}
    if reason.startswith('Device epoch changed'):
        reason = reason.partition(':')[0]
        clocks = evidence.get('clock_fault_events') or []
        if clocks:
            measures['clock_fault_events'] = measurement(clocks[-4:])
            arms.extend(x['arm'] for x in clocks if x.get('arm'))
        epochs = {arm:r['epoch'] for arm,r in evidence.get('native_records',{}).items() if 'epoch' in r}
        if epochs:
            measures['observed_native_epochs'] = measurement(epochs)
        if evidence.get('native_epoch_baseline'):
            measures['native_epoch_baseline'] = measurement(evidence['native_epoch_baseline'])
        if not clocks:
            measures['clock_fault_detail'] = 'Not recorded in this result'
    if 'time-aligned driver cache' in reason:
        for arm in arms:
            values = result.get('state_alignment', {}).get(arm, {})
            for field in ('difference_rad', 'conservative_difference_rad', 'uncertainty_rad'):
                if values.get(field):
                    measures['max_'+field] = max(map(abs, values[field]))
    stop = result.get('stop_result') or {}
    for key in ('resource_holds_confirmed', 'latches_confirmed', 'standstill_confirmed'):
        if key in stop:
            measures[key] = stop[key]
    motion = failed_event.get('native_motion') or {}
    durations = motion.get('observed_motion_s') or {}
    if motion.get('available') and durations:
        measures['observed_motion_s'] = measurement(durations)
    if motion.get('available') and any(isinstance(v,(int,float)) and v>0 for v in durations.values()):
        kind = 'Execution aborted after observed motion'
    elif any(seg.get('goal_send_monotonic_s_by_arm') for seg in result.get('segments', [])):
        kind = 'Execution aborted after goal submission'
    elif result.get('arm_commands') or result.get('finger_commands'):
        kind = 'Execution aborted · dispatch unverified'
    elif isinstance(result.get('arm_commands'), list) and not result.get('finger_commands'):
        kind = 'Blocked before phase command'
    else:
        kind = 'Workflow blocked'
    return kind, reason, arms, measures


def workflows(workspace, since, end, events):
    tasks = workspace/'setup/tasks'
    runs, covered = set(), set()
    if not tasks.is_dir():
        return source('Carton workflows', 'missing', str(tasks)), covered, runs
    # Inspect the original run directories. Skip nested evidence copies and
    # other simulations, large raw traces, point clouds and camera images.
    paths = set()
    scanned, issues = 0, []
    try:
        for group in tasks.iterdir():
            if not group.name.startswith('carton') or group.is_symlink() or not group.is_dir():
                continue
            direct = group/'workflow.json'
            if direct.is_file():
                paths.add(direct)
            for child in group.iterdir():
                scanned += 1
                if scanned > 16000:
                    break
                if child.is_dir() and not child.is_symlink():
                    path = child/'workflow.json'
                    if path.is_file():
                        paths.add(path)
            if scanned > 16000:
                issues.append('directory scan limit reached')
                break
        candidates = sorted(((p.stat().st_mtime, p) for p in paths if not p.is_symlink()), reverse=True)
    except OSError as exc:
        return source('Carton workflows', 'partial', compact(exc)), covered, runs
    candidates = [(mtime,p) for mtime,p in candidates if mtime >= since-1]
    if len(candidates)>128:
        issues.append('newest 128 workflow files only')
    for _, path in candidates[:128]:
        try:
            record = read_json(path)
            stamp = datetime.fromisoformat(record['updated_wall']).timestamp()
            if record.get('execute') is not True or not since <= stamp <= end:
                continue
            if not (record.get('error') or record.get('last_image_error')):
                continue
            failed_event = next((e for e in reversed(record.get('events', [])) if e.get('returncode')), {})
            phase = failed_event.get('phase', '')
            result = {}
            if re.fullmatch(r'[A-Za-z0-9_-]+', phase):
                file = path.parent/phase/'result.json'
                if file.is_file() and not file.is_symlink():
                    try:
                        result = read_json(file)
                    except (OSError, ValueError) as exc:
                        issues.append(f'{file.relative_to(tasks)}: {compact(exc,70)}')
            kind, reason, arms, values = workflow_failure(record, result, failed_event)
            reference = str(path.relative_to(workspace))
            events.append(event(kind,'Carton workflow',stamp,reason,arms,phase=phase or record.get('phase'),
                                reference=reference,measurements=values))
            runs.add(str(path.parent.resolve()))
            covered.update(key for key in (result.get('review_id'),record.get('contact_review') or
                          record.get('motion_review')) if key)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
            issues.append(f'{path.relative_to(tasks)}: {compact(exc,70)}')
    detail = f'{len(candidates[:128])} recent workflow files inspected under {tasks}/carton*'
    return source('Carton workflows','partial' if issues else ('ok' if paths else 'missing'),
                  detail+('. '+'. '.join(issues[:3]) if issues else '')), covered, runs


def reviews(directory, since, end, covered, runs, events):
    path = directory/'reviews.sqlite3'
    if not path.is_file():
        return source('Review decisions', 'missing', str(path))
    sql = """SELECT id, operation, status, reason, changed FROM tickets WHERE changed BETWEEN ? AND ?
             AND status IN ('failed','blocked','interrupted','revoked','replan','rejected','pending')
             ORDER BY changed DESC LIMIT 161"""
    try:
        # Opening an idle WAL database with mode=ro alone can create journals.
        # A live writer already maintains its own WAL and shared-memory index.
        wal = Path(str(path)+'-wal')
        live = wal.is_file() and wal.stat().st_size > 0
        if live and not Path(str(path)+'-shm').is_file():
            raise ValueError('live WAL shared-memory index unavailable')
        uri = path.resolve().as_uri() + ('?mode=ro' if live else '?mode=ro&immutable=1')
        with sqlite3.connect(uri, uri=True, timeout=.3) as db:
            deadline = time.monotonic()+1
            db.set_progress_handler(lambda: int(time.monotonic()>deadline), 1000)
            rows = db.execute(sql, (since,end)).fetchall()
        for rid, operation, status, reason, stamp in rows[:160]:
            if rid in covered or (status == 'blocked' and operation.split('/issue/')[0] in runs):
                continue
            kind = {'failed':'Workflow failed', 'blocked':'Workflow blocked', 'interrupted':'Review interrupted',
                    'revoked':'Review revoked', 'replan':'New plan requested', 'rejected':'Review rejected',
                    'pending':'Awaiting operator review'}[status]
            events.append(event(kind,'Review decisions',stamp,reason or kind,ARM.findall(reason or ''),reference=rid))
    except (OSError, ValueError, sqlite3.Error) as exc:
        return source('Review decisions','unavailable',compact(exc))
    return source('Review decisions','partial' if len(rows)>160 else 'ok',
                  f'{path}, '+('newest 160 tickets only' if len(rows)>160 else 'read-only'))


def build_report(workspace, mock_store=None, hours=24, now=None):
    end = time.time() if now is None else now
    since = end-hours*3600
    events, sources, covered, runs = [], [], set(), set()
    if mock_store is None:
        sources.append(read_guard(since, end, events))
        status, covered, runs = workflows(workspace, since, end, events)
        sources.append(status)
    directory = mock_store if mock_store is not None else Path.home()/'.local/state/uwa-motion-review'
    sources.append(reviews(directory,since,end,covered,runs,events))
    events.sort(key=lambda item: item.get('last_at',item['at']),reverse=True)
    counts = Counter((e['kind'],e['reason']) for e in events)
    raw_counts = Counter()
    for item in events:
        raw_counts[(item['kind'],item['reason'])] += item['count']
    grouped = [dict(kind=kind,reason=reason,episodes=count,records=raw_counts[(kind,reason)])
               for (kind,reason),count in counts.most_common()]
    lines = [f"{'Mock review' if mock_store else socket.gethostname()} · Last {hours:g} hours · UTC"]
    if grouped:
        lines += ['', 'Recorded causes']
        lines += [f"{g['episodes']} × {g['kind']} · {g['reason']}"+
                  (f" ({g['records']} requests)" if g['records']>g['episodes'] else '') for g in grouped[:12]]
        lines += ['', 'Latest records']
        for item in events[:8]:
            text = f"{item['at']}  {item['kind']} · {item['reason']}"
            if item['arms']:
                text += ' · '+', '.join(item['arms'])
            if item.get('measurements'):
                text += '\n  '+compact(json.dumps(item['measurements'],ensure_ascii=False),360)
            lines.append(text)
    else:
        lines.append('No matching events in the available sources.')
    lines += ['', 'Sources']+[f"{s['name']} · {s['status'].upper()} · {s['detail']}" for s in sources]
    if any(e['kind']=='Guard latch' for e in events):
        lines.append('Guard latch counts refer to individual reported causes and arm sets.')
    if any(e['kind']=='Native STOP request' for e in events):
        lines += ['', 'Native STOP retries from the same process and arm up to 2 s apart form one episode. '
                     'A request alone does not confirm a moving arm stopped.']
    # Keep the exported JSON within the GUI transport budget. The full-source
    # occurrence counts are calculated before trimming individual records.
    records, size = [], 0
    for item in events:
        size += len(json.dumps(item))
        if size > 520_000:
            break
        records.append(item)
    if len(records)<len(events):
        lines.append(f'Individual details include the newest {len(records)} of {len(events)} recorded episodes.')
    if len(grouped)>160:
        lines.append(f'Cause summary includes the 160 most frequent of {len(grouped)} causes.')
    return dict(schema_version=1, host=socket.gethostname(), mode='mock' if mock_store else 'host',
                generated_at=utc(end), since=utc(since), hours=hours, summary_text='\n'.join(lines),
                sources=sources, grouped=grouped[:160], events=records, episode_count=len(events),
                details_omitted=len(events)-len(records))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument('--workspace', type=Path)
    roots.add_argument('--mock-store', type=Path)
    parser.add_argument('--hours',type=float,default=24)
    args = parser.parse_args()
    if not math.isfinite(args.hours) or not 0 < args.hours <= 168:
        parser.error('--hours must be between 0 (exclusive) and 168')
    print(json.dumps(build_report(args.workspace,args.mock_store,args.hours),allow_nan=False))


if __name__ == '__main__':
    main()

"""Durable background review of saved UWA Camera Capture photos on ROSmini."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import fcntl
import hashlib
import json
import logging
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid

CAMERAS = ('right_front', 'right_rear', 'oak4', 'oak_usb', 'left_front', 'left_rear')
MODEL = 'gemini-4-hydrogen'
OUTPUT = 'gemini-charuco'


def state_dir(workspace):
    return Path(workspace) / 'setup/calibration/gemini_charuco_queue'


def connect(workspace):
    root = state_dir(workspace)
    root.mkdir(exist_ok=True, parents=True)
    db = sqlite3.connect(root / 'queue.sqlite3', timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS sessions(path TEXT PRIMARY KEY);
      CREATE TABLE IF NOT EXISTS manifests(path TEXT PRIMARY KEY, stamp INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS photos(
        id INTEGER PRIMARY KEY, set_dir TEXT NOT NULL, camera TEXT NOT NULL, sha TEXT NOT NULL,
        image TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
        attempts INTEGER NOT NULL DEFAULT 0, due REAL NOT NULL DEFAULT 0,
        detail TEXT, verdict TEXT, UNIQUE(set_dir, camera, sha));
    ''')
    return db


def register_session(workspace, session):
    session = Path(session).resolve(strict=True)
    if not (session / 'acquisition_profile.json').is_file() or not (session / 'board.json').is_file():
        raise ValueError('Expected a UWA Camera Capture session')
    with closing(connect(workspace)) as db, db:
        db.execute('INSERT OR IGNORE INTO sessions VALUES (?)', (str(session),))


def atomic_json(path, value):
    path.parent.mkdir(exist_ok=True, parents=True)
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def result_dir(job):
    return Path(job['set_dir']) / OUTPUT / job['camera'] / job['sha']


def write_status(db, directory):
    rows = db.execute('SELECT * FROM photos WHERE set_dir=? ORDER BY id', (str(directory),))
    cameras = {}
    for row in rows:
        item = dict(state=row['state'], sha256=row['sha'], attempts=row['attempts'])
        if row['detail']:
            item['detail'] = row['detail']
        if row['verdict']:
            item['verdict'] = row['verdict']
            item['review'] = str((result_dir(row) / 'review.json').relative_to(directory))
        cameras[row['camera']] = item
    atomic_json(Path(directory) / OUTPUT / 'status.json',
                dict(model=MODEL, updated_unix_s=time.time(), cameras=cameras))


def inspect_set(db, directory):
    if directory.resolve() != directory:
        return
    manifest = directory / 'manifest.json'
    complete = manifest.is_file() and not manifest.is_symlink()
    if complete:
        stamp = manifest.stat().st_mtime_ns
        known = db.execute('SELECT stamp FROM manifests WHERE path=?', (str(manifest),)).fetchone()
        if known and known[0] == stamp:
            return
        data = json.loads(manifest.read_text())
        board, records = data['board'], data['cameras']
    else:
        # A live session or an interrupted capture may already have finished
        # individual camera originals before the aggregate manifest is written.
        records = {}
        for name in CAMERAS:
            file = directory / name / 'record.json'
            if file.is_file() and file.resolve() == file:
                records[name] = json.loads(file.read_text())
        if not records:
            return
        board = json.loads((directory.parent / 'board.json').read_text())
    if not isinstance(board, dict) or not board.get('board_id'):
        raise ValueError('Missing board definition')
    jobs = []
    for name in CAMERAS:
        if name not in records:
            continue
        image = directory / name / ('image.png' if name in ('oak4', 'oak_usb') else 'image.jpg')
        if image.resolve() != image or not image.is_file():
            continue
        sha = records[name].get('sha256')
        if sha is None:
            with image.open('rb') as photo:
                sha = hashlib.file_digest(photo, 'sha256').hexdigest()
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            logging.error('Invalid recorded photo digest at %s', image)
            continue
        jobs.append((str(directory), name, sha, str(image)))
    if jobs and not (directory / OUTPUT / 'board.json').exists():
        atomic_json(directory / OUTPUT / 'board.json', board)
    with db:
        added = db.executemany('INSERT OR IGNORE INTO photos(set_dir,camera,sha,image) VALUES(?,?,?,?)', jobs).rowcount
        if complete:
            db.execute('INSERT OR REPLACE INTO manifests VALUES(?,?)', (str(manifest), stamp))
    if added or (jobs and not (directory / OUTPUT / 'status.json').exists()):
        write_status(db, directory)


def discover(db):
    for session, in db.execute('SELECT path FROM sessions'):
        for directory in sorted(Path(session).glob('set_*')):
            try:
                if directory.is_dir():
                    inspect_set(db, directory)
            except (OSError, ValueError, KeyError) as error:
                logging.debug('Set %s pending: %s', directory, error)


def checked_review(job):
    out = result_dir(job)
    file = out / 'review.json'
    if not file.is_file():
        return None
    review = json.loads(file.read_text())
    if review.get('status') != 'completed':
        return None
    report = review.get('final_report')
    if (review.get('source_sha256') != job['sha'] or review.get('model_id') != MODEL
            or review.get('verdict') not in ('confirmed', 'not_visible', 'uncertain')
            or not isinstance(report, str) or Path(report).name != report):
        raise ValueError('Invalid photo review receipt')
    evidence = json.loads((out / report).read_text())
    if evidence.get('image_sha256') != job['sha'] or evidence.get('camera') != job['camera']:
        raise ValueError('OpenCV evidence belongs to a different photo')
    return review['verdict']


def review_photo(workspace, job):
    out = result_dir(job)
    out.mkdir(parents=True, exist_ok=True)
    verdict = checked_review(job)
    if verdict:
        return verdict
    script = workspace / 'src/multi_arm_manipulation_UWA/tools/charuco_agent/review.py'
    args = [sys.executable, str(script), '--workspace', str(workspace),
            '--image', job['image'], '--board', str(Path(job['set_dir']) / OUTPUT / 'board.json'),
            '--camera', job['camera'], '--expect-sha256', job['sha'], '--out', str(out)]
    with (out / 'worker.log').open('ab') as log:
        proc = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=420)
    verdict = checked_review(job)
    if proc.returncode or not verdict:
        receipt = out / 'review.json'
        detail = json.loads(receipt.read_text()).get('error') if receipt.exists() else None
        raise RuntimeError(detail or f'Gemini worker exited with code {proc.returncode}. See worker.log')
    return verdict


def serve(workspace):
    with closing(connect(workspace)) as db, (state_dir(workspace) / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with db:
            db.execute("UPDATE photos SET state='queued' WHERE state='running'")
        active = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            while True:
                try:
                    discover(db)
                    for future, job in list(active.items()):
                        if not future.done():
                            continue
                        del active[future]
                        try:
                            verdict = future.result()
                            with db:
                                db.execute("UPDATE photos SET state='completed', detail=NULL, verdict=? WHERE id=?",
                                           (verdict, job['id']))
                        except Exception as error:
                            delay = min(1800, 30 * 2 ** min(job['attempts'], 6))
                            logging.warning('%s %s: %s', job['set_dir'], job['camera'], error)
                            with db:
                                db.execute("UPDATE photos SET state='retrying', due=?, detail=? WHERE id=?",
                                           (time.time() + delay, str(error)[:1200], job['id']))
                        write_status(db, job['set_dir'])
                    free = 2 - len(active)
                    rows = db.execute("""SELECT * FROM photos WHERE state IN ('queued','retrying') AND due<=?
                                         ORDER BY id LIMIT ?""", (time.time(), free)).fetchall()
                    for job in rows:
                        with db:
                            db.execute("UPDATE photos SET state='running', attempts=attempts+1 WHERE id=?", (job['id'],))
                        active[pool.submit(review_photo, workspace, dict(job))] = job
                        write_status(db, job['set_dir'])
                except (OSError, ValueError, sqlite3.Error) as error:
                    logging.exception('Could not update photo queue: %s', error)
                time.sleep(1.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('serve')
    sub.add_parser('register').add_argument('session', type=Path)
    sub.add_parser('status')
    opts = parser.parse_args()
    workspace = opts.workspace.resolve()
    if opts.command == 'register':
        register_session(workspace, opts.session)
    elif opts.command == 'serve':
        serve(workspace)
    else:
        with closing(connect(workspace)) as db:
            print(json.dumps(dict(db.execute('SELECT state, count(*) FROM photos GROUP BY state'))))


if __name__ == '__main__':
    main()

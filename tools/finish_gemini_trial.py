#!/usr/bin/env python3
"""Verify and package a Gemini result using the UWA offline checks."""

import argparse
import hashlib
from itertools import groupby
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from uuid import uuid4

from agent_trial import Trial


TOOLS = Path(__file__).resolve().parent
ENV = TOOLS.parent / "scripts/env.bash"
BOX_FIXTURE = TOOLS.parent.parents[1] / 'setup/research/offline-carton-sides-20261117/standard/smoothed/result.json'
sys.path.insert(0, str(TOOLS.parent/'uwa_cell_tasks'))
from uwa_cell_tasks.pilot_episode import digest as canonical_digest

TESTS = tuple(f"uwa_cell_tasks/test/{name}.py" for name in (
    "test_workpiece_paths", "test_box_drawing_cli", "test_pilot_episode",
))
TRAJECTORY_AUDIT = 'verify_box_drawing_pilot.py'
TASK_AUDITS = {
    'circles': None,
    'nikolaus': 'check_nikolaus_trial.py',
    'house-drill': 'check_house_drill_trial.py',
}
AUDIT_PATHS = {f'tools/{name}' for name in TASK_AUDITS.values() if name}
AUDIT_PATHS.update(f'tools/{name}' for name in (
    TRAJECTORY_AUDIT, 'finish_gemini_trial.py', 'finish_house_drill_trial.py',
))
AXIAL = {"axial_approach", "axial_feed", "axial_retract"}


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def check_three_circles(result):
    program = result['program']
    faces = ['y_max', 'z_min', 'y_min']
    require(result['source_sha256'] == hashlib.sha256(BOX_FIXTURE.read_bytes()).hexdigest(),
            'Wrong reference model for the three circles')
    require(program['surfaces'] == faces and program['velocity_rad_s'] == .1,
            'Expected y_max, z_min, y_min at the 0.1 rad/s limit')
    require(program['holding_arms'] == ['right_front', 'right_rear'] and program['working_arm'] == 'left_front',
            'Unexpected arm roles')
    require(not program.get('surface_paths') and not program.get('circle_drivers') and not program.get('face_drivers'),
            'Expected circles drawn by the working arm on a stationary carton')
    radii = program.get('face_radii_m', program.get('circle_radii_m', {}))
    for phase in result['phases']:
        require(phase.get('operation') not in AXIAL, 'Unexpected axial phase')
        if phase['drawing']:
            require(phase.get('driver', 'moving_tool') == 'moving_tool' and
                    phase.get('circle_radius_m', radii.get(phase['face'], program['circle_radius_m'])) == .022,
                    'Expected a 22 mm moving-tool circle')
    return 'Three 22 mm moving-tool circles with the assigned arm roles'


def viewer_summary(path, result):
    html = path.read_text()
    marker = re.search(r"\b(?:const|let)\s+data\s*=\s*(?=\{)", html)
    require(marker is not None, "Viewer does not contain embedded trajectory JSON")
    data, _ = json.JSONDecoder().raw_decode(html, marker.end())
    require(data['report_sha256'] == canonical_digest(result) and data['program'] == result['program'],
            "Viewer belongs to a different model result")
    phases = {p['id']: p for p in result['phases']}
    frames = data['frames']
    require(frames and [phase for phase, _ in groupby(frames, key=lambda f: f['phase'])] == list(phases),
            "Viewer does not cover the saved phases in order")
    previous = 0.
    feeds = set()
    for frame in frames:
        phase = phases[frame['phase']]
        now = frame['time_s']
        require(math.isfinite(now) and now >= previous, "Invalid viewer timeline")
        previous = now
        require(frame['drawing'] == phase['drawing'] and frame['face'] == phase['face'],
                f"Viewer drawing metadata differs in {frame['phase']}")
        operation = phase.get('operation')
        if operation in AXIAL:
            require(frame.get('operation') == operation and frame.get('site') == phase['site'],
                    f"Viewer axial metadata differs in {frame['phase']}")
        if operation == 'axial_feed':
            feeds.add(frame['site'])
        if frame['drawing'] or operation in AXIAL:
            tip = frame['tip']
            require(len(tip) == 3 and all(math.isfinite(x) for x in tip),
                    f"Invalid tool tip in viewer phase {frame['phase']}")
    require(abs(frames[0]['time_s']) < 1e-8 and
            abs(previous - data['duration_s']) < 1e-8 and
            abs(previous - sum(p['duration_s'] for p in phases.values())) < 1e-8,
            "Viewer duration differs from the model timeline")
    return f"{len(frames)} frames, {len(phases)} phases, {len(feeds)} axial sites"


def git(repo, *args, exits=(0,)):
    process = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    require(process.returncode in exits, process.stderr.decode(errors='replace').strip() or 'Git failed')
    return process.stdout


def changed_files(repo, baseline):
    def paths(*args):
        return os.fsdecode(git(repo, *args)).strip('\0').split('\0')

    tracked = paths('diff', '--name-only', '--no-renames', '-z', baseline, '--')
    added = paths('ls-files', '--others', '--exclude-standard', '-z')
    return sorted(set(tracked + added) - {''}), [p for p in added if p]


def protected(path):
    parts = Path(path).parts
    name = parts[-1]
    return (bool({'test', 'tests'} & set(parts)) or name.startswith('test_') or name.endswith('_test.py')
            or name == 'conftest.py' or path in AUDIT_PATHS)


def offline_env():
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    process = subprocess.run(['/bin/bash', '-c', 'source "$1" >&2 && exec /usr/bin/env -0',
                              'uwa-offline', str(ENV)], capture_output=True, env=env)
    require(process.returncode == 0, os.fsdecode(process.stderr).strip() or 'Could not load Lyrical environment')
    return dict(entry.split('=', 1) for entry in os.fsdecode(process.stdout).split('\0') if entry)


def run_check(argv, *, repo, env, log):
    with log.open('wb') as stream:
        process = subprocess.run(argv, cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT)
    require(process.returncode == 0, f"Exit {process.returncode}. See {log.name}")


def write_report(output, run, trial, checks, baseline, elapsed, case):
    passed = all(check['passed'] for check in checks)
    (output/'verification.json').write_text(json.dumps(dict(
        passed=passed, case=case, model_run=str(run), baseline=baseline, elapsed_s=elapsed, checks=checks,
    ), indent=2) + '\n')
    lines = [f'# Gemini-Trial · {case}', '', f"**{'PASS' if passed else 'FAIL'}** · Offline-Kinematikmodell",
             '', '| Prüfung | Status | Dauer | Befund |', '|---|---|---:|---|']
    for check in checks:
        detail = ' '.join(check['detail'].split()).replace('|', r'\|')
        lines.append(f"| {check['name']} | {'PASS' if check['passed'] else 'FAIL'} | "
                     f"{check['elapsed_s']:.2f} s | {detail} |")
    def link(label, path):
        return f"[{label}]({os.path.relpath(path, output)})"

    lines.extend(['', link('Modellergebnis', run/'result.json') + ' · ' + link('Viewer', run/'viewer.html')
                  + ' · ' + link('Posensuche', run/'presentation-search.json')
                  + ' · ' + link('Zeitprotokoll', trial/'events.jsonl') + ' · [Quelldiff](changes.patch)',
                  '', f'Startcommit `{baseline}`. Gebündelte Prüfung und Abgabe in {elapsed:.2f} s.'])
    for event in reversed(Trial(trial).events()):
        argv = event.get('argv', [])
        if event['kind'] == 'command_start' and any('box_drawing_pilot.py' in a for a in argv) and any(str(run) in a for a in argv):
            lines.extend(['', 'Protokollierter Offline-Aufruf. Für die Reproduktion einen neuen Ausgabeordner wählen.',
                          '', '```bash', f"cd -- {shlex.quote(event['cwd'])}", shlex.join(argv), '```'])
            break
    (output/'report.md').write_text('\n'.join(lines) + '\n')
    print(f"{'PASS' if passed else 'FAIL'} in {elapsed:.2f} s. Bericht: {output/'report.md'}", flush=True)
    return 0 if passed else 1


def verify(run, repo, trial, baseline, output, case):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    checks = []

    def check(name, action):
        begin = time.monotonic()
        try:
            detail = action()
            passed = True
        except (ValueError, OSError, KeyError, TypeError) as error:
            detail, passed = str(error), False
        checks.append(dict(name=name, passed=passed, elapsed_s=time.monotonic()-begin, detail=detail))
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}", flush=True)
        return passed

    def finish_report():
        return write_report(output, run, trial, checks, baseline, time.monotonic()-started, case)

    files, untracked = changed_files(repo, baseline)

    def patch():
        with (output/'changes.patch').open('wb') as out:
            out.write(git(repo, 'diff', '--binary', '--no-ext-diff', '--no-textconv', baseline, '--'))
            for path in untracked:
                out.write(git(repo, 'diff', '--binary', '--no-index', '--no-ext-diff', '--no-textconv',
                              '--', '/dev/null', path, exits=(0, 1)))
        return f'{len(files)} changed files from start commit'

    def check_test_sources():
        modified = [name for name in files if protected(name)]
        require(not modified, 'Modified tests or audit scripts: ' + ', '.join(modified))
        return 'Existing tests and audit scripts unchanged'

    check('Quelldiff', patch)
    tests_unchanged = check('Prüfquellen', check_test_sources)
    try:
        raw = (run/'result.json').read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        result = json.loads(raw)
        require(result['backend'] == 'kinematic_model' and result['executable'] is False,
                'Expected a file-only kinematic model result')
        require(result['status'] == 'MODEL_SEQUENCE_COMPLETE', 'Expected a complete model result')
        env = offline_env()
    except (OSError, ValueError, KeyError, TypeError) as error:
        checks.append(dict(name='Eingaben', passed=False, elapsed_s=0., detail=str(error)))
        return finish_report()

    def audit(script, name):
        target = output/f'{name}.json'
        log = output/f'{name}.log'
        cmd = [sys.executable, str(TOOLS/script), str(run), '--output', str(target)]
        run_check(cmd, repo=TOOLS.parent, env=env, log=log)
        evidence = json.loads(target.read_text())
        require(evidence['passed'] is True and evidence['result_sha256'] == digest, 'Audit result hash mismatch')
        return f"{evidence['duration_model_s']:.2f} s model time · [{target.name}]({target.name})"

    task_audit = TASK_AUDITS[case]
    if task_audit:
        check('Aufgabenaudit', lambda: audit(task_audit, f'{case}-audit'))
    else:
        check('Aufgabenaudit', lambda: check_three_circles(result))
    check('FK-, Zeit- und Episodenaudit', lambda: audit(TRAJECTORY_AUDIT, 'trajectory-audit'))
    check('Viewer', lambda: viewer_summary(run/'viewer.html', result))

    def hashes():
        files_to_check = result['implementation_sha256']
        require(bool(files_to_check), 'No implementation hashes in model result')
        for file, expected in files_to_check.items():
            require(hashlib.sha256(Path(file).read_bytes()).hexdigest() == expected,
                    f"Source changed since planning: {file}")
        return f"{len(files_to_check)} implementation hashes match"

    check('Quellstand der Bahn', hashes)
    if tests_unchanged and any(name.endswith('.py') for name in files):
        def regression():
            env['PYTHONPATH'] = os.pathsep.join(filter(None, (str(repo/'uwa_cell_tasks'), env.get('PYTHONPATH'))))
            log = output/'pytest.log'
            run_check([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *TESTS],
                      repo=repo, env=env, log=log)
            return log.read_text().splitlines()[-1]

        check('Gezielte Regression', regression)
    return finish_report()


def main(expected_case=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('run', help='Run folder name under trial/artifacts, e.g. run01')
    parser.add_argument('--review-output', type=Path, help='New directory for reviewing a run without editing its trace')
    args = parser.parse_args()
    try:
        session = args.session.resolve()
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}', args.run), 'Use a run folder name')
        metadata = json.loads((session/'observer.json').read_text())
        case = metadata['case']
        require(case in TASK_AUDITS, f'No offline audit configured for {case}')
        require(expected_case is None or case == expected_case, f'Expected a {expected_case} session')
        trial, repo = session/'trial', session/'repo'
        run = trial/'artifacts'/args.run
        require(run.is_dir() and run.resolve() == run, f'Run folder missing: {run}')
        if args.review_output:
            return verify(run, repo, trial, metadata['git_head'], args.review_output.resolve(), case)

        logger = Trial(trial)
        state = logger.state()
        require(not state['finished'], 'Trial already finished. Use --review-output to recheck it.')
        require(state['stage'] is None, f"End active stage {state['stage']} before verifying")
        previous_checks = sum(e['kind'] == 'stage_start' and e['stage'].startswith('verify') for e in logger.events())
        logger.start('verify' if not previous_checks else f'verify{previous_checks + 1:02d}')
        output = trial/'verification'/f'{args.run}-{uuid4().hex[:8]}'
        command = [sys.executable, str(Path(__file__).resolve()), str(session), args.run, '--review-output', str(output)]
        status = logger.run(command, label='verify-and-export', timeout=180., cwd=repo)
        logger.end('done' if status == 0 else 'failed', f'Prüfung und Abgabe unter {output}')
        if status == 0:
            logger.finish('complete', f'Alle Offline-Prüfungen bestanden. Bericht: {output}/report.md')
        return status
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'FAIL: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

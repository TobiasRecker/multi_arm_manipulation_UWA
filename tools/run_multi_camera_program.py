#!/usr/bin/env python3
"""Reusable serial observation-pose setup followed by native six-camera capture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from run_carton_program import Progress, logged_command, n100, offline_tool, SSH_OPTIONS, N100_HOST
from open_multi_camera_capture import open_window, active_window

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
PROGRAM = 'multi-camera-calibration-capture-v1'
DEFINITION = REPO / 'config/multi_camera_calibration.json'
CELL = 'src/multi_arm_manipulation_UWA'


def remote_location(relative):
    runtime = os.environ.get('UWA_MINIMAL_RUNTIME') if os.environ.get('UWA_PROTECTION_BACKEND')=='minimal' else None
    if runtime and not Path(runtime).is_absolute():
        raise ValueError('UWA_MINIMAL_RUNTIME must be an absolute N100 runtime path')
    return f'{N100_HOST}:{runtime or "uwa-ur-runtime"}/{relative}'


def upload(remote, local_file, log_path):
    return logged_command(['/usr/bin/scp',*SSH_OPTIONS,local_file,remote_location(remote)],log_path,100)


def download(remote, destination, log):
    return logged_command(['/usr/bin/scp', *SSH_OPTIONS, '-r',
        remote_location(remote), destination], log, 100)


def prepare_and_move(progress):
    out = progress.output
    definition = json.loads(DEFINITION.read_text())
    (out / 'program.json').write_text(json.dumps(definition, indent=2) + '\n')
    targets = REPO / definition['targets']
    (out / 'targets.yaml').write_bytes(targets.read_bytes())
    remote = 'setup/tasks/multi_camera_calibration/' + out.name
    helpers = ['observe_calibration_start.py', 'execute_calibration_observation_motion.py']
    progress.update('snapshot', 'Reading the current four-arm start and active N100 model. Arms must be unloaded, ready and the work area released.')
    logged_command(n100('mkdir -p -- "$1"', remote), out / 'remote-directory.log', 15)
    bindings = {}
    for name in helpers:
        path = REPO / 'tools' / name
        bindings[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        upload(remote + '/' + name, path, out / ('upload-' + name + '.log'))
    # Only the two run-scoped helpers are staged. No runtime/guard deployment.
    # Explicit positional pairs avoid shell interpolation of local paths.
    verify = '''test "$(sha256sum "$1/observe_calibration_start.py" | cut -d ' ' -f 1)" = "$2"
test "$(sha256sum "$1/execute_calibration_observation_motion.py" | cut -d ' ' -f 1)" = "$3"
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 "$1/observe_calibration_start.py" --output "$1/observation"
'''
    logged_command(n100(verify, remote, *bindings.values()), out / 'observe.log', 60)
    download(remote + '/observation', out, out / 'download-observation.log')
    observation = out / 'observation'
    snapshot = json.loads((observation / 'snapshot.json').read_text())
    progress.update('planning', 'Planning the four observation goals from this start on ROSmini, including the existing full-cell checks. Command cap: 0.09 rad/s.')
    logged_command(offline_tool('prepare_calibration_observation_motion.py',
        '--snapshot', observation / 'snapshot.json', '--context', observation / 'model-context.json',
        '--targets', out / 'targets.yaml', '--command-cap', definition['command_cap_rad_s'],
        '--output', out / 'plans'), out / 'planning.log', 240)
    sequence_path = out / 'plans/sequence.json'
    sequence = json.loads(sequence_path.read_text())
    if not sequence['segments']:
        return 'All four arms already match the observation goals; no trajectory was sent.'
    if active_window(WORKSPACE):
        raise RuntimeError('A capture window is active. Finish the capture session and close its window before repositioning the arms. No trajectory was sent.')
    digest = hashlib.sha256(sequence_path.read_bytes()).hexdigest()
    (out / 'execution-binding.json').write_text(json.dumps(dict(sequence_sha256=digest,
        helpers_sha256=bindings, area_session=snapshot['area_session']), indent=2) + '\n')
    logged_command(['/usr/bin/scp', *SSH_OPTIONS, '-r', out / 'plans',
        remote_location(remote+'/plans')], out / 'upload-plans.log', 100)
    progress.update('positioning', 'Moving the arms in order: left front, left rear, right front, right rear. Existing N100 protection remains active.')
    command = n100('''source src/multi_arm_manipulation_UWA/scripts/control_env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 "$1/execute_calibration_observation_motion.py" \
  --plans "$1/plans" --output "$1/execution" --sequence-sha256 "$2" --command-cap "$3" --area-session "$4"
''', remote, digest, definition['command_cap_rad_s'], snapshot['area_session'])
    try:
        logged_command(command, out / 'execution.log', max(120, sequence['total_duration_s'] * 5 + 120))
    finally:
        download(remote + '/execution', out, out / 'download-execution.log')
    result = json.loads((out / 'execution/sequence-result.json').read_text())
    if not result['complete']:
        raise RuntimeError('The observation sequence did not complete. Inspect the recorded arm result and Safety log.')
    return 'All four observation goals reached using freshly planned, checked serial trajectories.'


def run(mode, progress):
    motion = prepare_and_move(progress) if mode == 'setup' else 'Camera window only; no robot motion requested.'
    progress.update('capture_gui', 'Opening the six-camera capture window, or reusing its active session.')
    result = dict(open_window(), motion=motion,
        calibration='Capture setup ready. Record mobile-board views in the GUI; a joint calibration has not yet been solved or activated.')
    progress.update('complete', 'Capture window ready. Use CAPTURE ALL SIX for each stationary board view.', result=result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('setup', 'gui'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    progress = Progress(args.output)
    try:
        run(args.mode, progress)
    except Exception as error:
        phase = json.loads(progress.path.read_text()).get('phase', 'starting') if progress.path.exists() else 'starting'
        progress.update(phase, str(error), error=str(error))
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

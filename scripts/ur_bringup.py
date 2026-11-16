#!/usr/bin/env python3
"""Inspect or explicitly prepare the four physical UWA URs for ROS External Control."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
import fcntl
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import subprocess
import sys
import time

import yaml


ROBOT_IDS = ('left_front', 'left_rear', 'right_front', 'right_rear')
INVENTORY = Path(__file__).resolve().parents[1] / 'config/hardware_inventory.yaml'
SAFE = ('NORMAL', 'REDUCED')
ROBOT_MODES = frozenset(('NO_CONTROLLER', 'DISCONNECTED', 'CONFIRM_SAFETY', 'BOOTING',
                         'POWER_OFF', 'POWER_ON', 'IDLE', 'BACKDRIVE', 'RUNNING'))
TRANSIENT = ('BOOTING', 'POWER_ON')


class Blocked(RuntimeError):
    def __init__(self, code, message, action=None):
        super().__init__(message)
        self.code, self.action = code, action


@dataclass(frozen=True)
class Arm:
    id: str
    ip: str
    serial: str
    series: int
    port: int
    program: str
    reverse_port: int
    script_port: int


def load_arms(path):
    robots = yaml.safe_load(path.read_text())['robots']
    if set(robots) != set(ROBOT_IDS):
        raise ValueError('Das Hardwareinventar muss genau die vier UWA-Arm-IDs enthalten.')
    result = {}
    for rid in ROBOT_IDS:
        cfg = robots[rid]
        ip = str(ipaddress.IPv4Address(cfg['ip']))
        serial, version = str(cfg['serial_number']), str(cfg['polyscope_version'])
        program = cfg['external_control_program']
        port, base = cfg.get('dashboard_port', 29999), cfg['port_base']
        if (not re.fullmatch(r'[0-9]{8,16}', serial) or not re.fullmatch(r'[35]\.[0-9.]+', version)
                or not re.fullmatch(r'/programs/[A-Za-z0-9_-]+\.urp', program)
                or type(port) is not int or not 1 <= port <= 65535
                or type(base) is not int or not 1024 <= base <= 65531):
            raise ValueError(f'{rid}: ungültiger Dashboard-/ROS-Programmeintrag im Inventar.')
        result[rid] = Arm(rid, ip, serial, int(version[0]), port, program, base + 1, base + 2)
    ports = [p for a in result.values() for p in (a.reverse_port, a.script_port)]
    if (len(set(ports)) != len(ports) or len({a.ip for a in result.values()}) != len(result)
            or len({a.serial for a in result.values()}) != len(result)):
        raise ValueError('Doppelte Roboteradressen, Seriennummern oder Treiberports im Inventar.')
    return result


class Dashboard:
    def __init__(self, arm):
        self.arm = arm

    @contextmanager
    def connect(self):
        with socket.create_connection((self.arm.ip, self.arm.port), timeout=3) as sock:
            with sock.makefile('rb') as reader:
                self.sock, self.reader = sock, reader
                if not self.line().startswith('Connected: Universal Robots Dashboard Server'):
                    raise Blocked('unexpected_dashboard', 'Unbekannte Dashboard-Gegenstelle.')
                yield self

    def line(self):
        line = self.reader.readline(4097)
        if not line.endswith(b'\n') or len(line) > 4096:
            raise OSError('Dashboard-Verbindung geschlossen oder unvollständige Antwort')
        return line.decode('ascii', errors='replace').strip()

    def ask(self, command):
        # Loading also waits for PolyScope to load the associated installation.
        if command.startswith('load '):
            self.sock.settimeout(20)
        try:
            self.sock.sendall((command + '\n').encode('ascii'))
            return self.line()
        finally:
            self.sock.settimeout(3)


def field(reply, prefix, allowed=None):
    if not reply.lower().startswith(prefix.lower()):
        raise Blocked('invalid_readback', f'Unerwartete Dashboard-Antwort: {reply!r}')
    value = reply[len(prefix):].strip()
    if not value or (allowed is not None and value not in allowed):
        raise Blocked('invalid_readback', f'Unerwartete Dashboard-Antwort: {reply!r}')
    return value


@dataclass(frozen=True)
class State:
    mode: str
    safety: str
    remote: bool | None
    program: str | None
    playback: str
    playback_program: str | None
    program_saved: bool | None
    version: str


def inspect(dash, expected):
    serial = dash.ask('get serial number')
    if serial != expected.serial:
        raise Blocked('identity_mismatch', f'Seriennummer {serial!r}, erwartet {expected.serial}.',
                      'Zuordnung im Hardwareinventar und Verkabelung prüfen.')
    version = field(dash.ask('PolyscopeVersion'), 'URSoftware ')
    if not version.startswith(f'{expected.series}.'):
        raise Blocked('unsupported_polyscope', f'Unerwartete PolyScope-Version {version!r}.')
    mode = field(dash.ask('robotmode'), 'Robotmode:', ROBOT_MODES)
    safety_command = 'safetystatus' if expected.series == 5 else 'safetymode'
    safety = field(dash.ask(safety_command), safety_command + ':')
    remote = None
    if expected.series == 5:
        value = dash.ask('is in remote control').lower()
        if value not in ('true', 'false'):
            raise Blocked('invalid_readback', f'Remote-Control-Status nicht lesbar: {value!r}',
                          'Remote Control und Dashboard Server am Teach Pendant prüfen.')
        remote = value == 'true'
    playback_reply = dash.ask('programState')
    playback, _, playback_program = playback_reply.partition(' ')
    if playback not in ('PLAYING', 'PAUSED', 'STOPPED'):
        raise Blocked('invalid_readback', f'Ungültiger Programmzustand: {playback_reply!r}.')
    reply = dash.ask('get loaded program')
    program = None if reply.lower() == 'no program loaded' else field(reply, 'Loaded program:')
    playback_program = None if playback_program.strip() in ('', 'null') else playback_program.strip()
    saved = None
    if program is not None and playback == 'STOPPED' and mode in ('POWER_OFF', 'IDLE', 'RUNNING'):
        saved_reply = dash.ask('isProgramSaved').partition(' ')[0].lower()
        if saved_reply not in ('true', 'false'):
            raise Blocked('invalid_readback', 'Speicherstatus des geladenen Programms nicht lesbar.',
                          'Geladenes Programm am Teach Pendant prüfen.')
        saved = saved_reply == 'true'
    return State(mode, safety, remote, program, playback, playback_program, saved, version)


def endpoint(value):
    host, _, port = value.rpartition(':')
    host = host.strip('[]').removeprefix('::ffff:')
    return host, int(port) if port.isdecimal() else None


def transport(arm):
    """Read local Linux sockets; never connect to the driver's script sender."""
    try:
        ss = subprocess.run(['ss', '-Hntap'], capture_output=True, text=True,
                            timeout=3, check=True).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise Blocked('transport_status_unavailable', f'Lokaler ROS-Portstatus nicht lesbar: {error}.') from error
    listening = reverse = False
    for line in ss.splitlines():
        cols = line.split(None, 5)
        # Verify socket ownership rather than accepting a listener from a mock or
        # unrelated process. ROS node's Linux comm is limited to 15 characters.
        if len(cols) != 6 or not re.search(r'\("(?:ros2_control_no(?:de)?)",pid=', cols[5]):
            continue
        local_host, local_port = endpoint(cols[3])
        peer_host, _ = endpoint(cols[4])
        if cols[0] == 'LISTEN' and local_port == arm.script_port and local_host not in ('127.0.0.1', '::1'):
            listening = True
        if cols[0] == 'ESTAB' and local_port == arm.reverse_port and peer_host == arm.ip:
            reverse = True
    return listening, reverse


def launch_driver(arm, get_transport):
    """Start a missing local driver only; MATCH retains its per-arm launch lock."""
    repo = INVENTORY.parent.parent
    workspace = repo.parents[1]
    unit = f'uwa-ur-driver-{arm.id.replace("_", "-")}.service'
    action = (f'ROS-Umgebung und Treiberprotokoll prüfen: journalctl --user -u {unit}. '
              'Alternativ in UWA Arms → Hardware → Start drivers starten.')
    command = [
        'systemd-run', '--user', '--collect', f'--unit={unit}',
        f'--property=WorkingDirectory={workspace}', '--property=KillSignal=SIGINT',
        '/usr/bin/bash', '-c',
        'source "$1" && exec ros2 launch uwa_cell_control arms.launch.py '
        'mode:=hardware "arms:=$2" "inventory:=$3"',
        'uwa-ur-driver', str(repo/'scripts/control_env.bash'), arm.id, str(INVENTORY),
    ]
    if get_transport(arm)[0]:
        return
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError) as error:
        raise Blocked('ros_driver_start_failed', f'Lokaler Treiberstart fehlgeschlagen: {error}.', action) from error
    deadline = time.monotonic() + 25
    while True:
        if get_transport(arm)[0]:
            return
        if result.returncode or time.monotonic() >= deadline:
            detail = (result.stderr or result.stdout).strip().splitlines()
            message = (f' ({detail[-1]})' if result.returncode and detail else '')
            raise Blocked('ros_driver_start_failed',
                          f'ROS-Treiber lauscht nicht auf TCP {arm.script_port}{message}.', action)
        time.sleep(.5)


def running_target(arm, state):
    name = PurePosixPath(arm.program).name
    return (state.program == arm.program and state.playback == 'PLAYING'
            and state.playback_program in (arm.program, name))


def safety_check(state):
    if state.mode == 'CONFIRM_SAFETY':
        raise Blocked('confirm_safety', 'PolyScope verlangt eine Sicherheitsbestätigung.',
                      'Installation und Sicherheitskonfiguration vor Ort prüfen und ggf. am Teach Pendant bestätigen.')
    if state.safety in SAFE or (state.mode == 'BOOTING' and state.safety == 'UNDEFINED_SAFETY_MODE'):
        return
    safety = state.safety
    if 'EMERGENCY_STOP' in safety:
        action = 'Not-Halt und Ursache vor Ort prüfen; erst bei freier Zelle manuell zurücksetzen.'
    elif 'SAFEGUARD_STOP' in safety or 'ENABLING_STOP' in safety:
        action = 'Schutzeinrichtung bzw. Zustimmtaster vor Ort prüfen und nach Zellvorgabe freigeben.'
    elif safety == 'PROTECTIVE_STOP':
        action = 'Ursache am Teach Pendant prüfen und Schutzstopp vor Ort beheben und quittieren.'
    else:
        action = 'Sicherheitsmeldung und Log am Teach Pendant prüfen und den Zustand manuell beheben.'
    raise Blocked('safety_blocked', f'Sicherheitszustand {safety}.', action)


def next_step(arm, state, listening, reverse):
    safety_check(state)
    if state.mode in TRANSIENT:
        return 'wait'
    if state.mode not in ('POWER_OFF', 'IDLE', 'RUNNING'):
        raise Blocked('robot_mode_blocked', f'Robotermodus {state.mode}.',
                      'Controller, Initialisierung und Betriebsart am Teach Pendant prüfen.')
    if running_target(arm, state):
        if state.mode != 'RUNNING':
            raise Blocked('state_inconsistent', 'ROS-Programm spielt, aber der Roboter meldet nicht RUNNING.',
                          'Aktuellen Zustand am Teach Pendant prüfen.')
        return 'ready' if reverse else 'wait_ros'
    if state.playback != 'STOPPED':
        raise Blocked('program_in_use', f'Programm {state.program or state.playback_program or "unbekannt"} ist {state.playback}.',
                      'Laufendes oder pausiertes Programm am Teach Pendant prüfen; ggf. bewusst beenden und erneut aufrufen.')
    if state.remote is False:
        raise Blocked('local_control', 'Der UR ist in Local Control.',
                      'Am Teach Pendant Remote Control wählen; falls nicht verfügbar, Settings → System → Remote Control aktivieren.')
    if state.program_saved is False:
        raise Blocked('unsaved_program', 'Das geladene Programm hat ungespeicherte Änderungen.',
                      'Änderungen am Teach Pendant speichern oder bewusst verwerfen.')
    if state.program != arm.program:
        return 'load'
    if state.mode == 'POWER_OFF':
        return 'power on'
    if state.mode == 'IDLE':
        return 'brake release'
    if not listening:
        raise Blocked('ros_driver_missing', f'Der lokale UR-Treiber lauscht nicht auf TCP {arm.script_port}.',
                      'In UWA Arms für diesen Arm Hardware → Start drivers wählen und den Befehl erneut ausführen.')
    return 'play'


def write(dash, arm, step, log):
    command = f'load {PurePosixPath(arm.program).name}' if step == 'load' else step
    entry = {'command': command}
    log.append(entry)
    try:
        reply = dash.ask(command)
    except OSError as error:
        entry['error'] = str(error)
        raise Blocked('command_outcome_unknown', f'Keine eindeutige Antwort auf {command!r}: {error}.',
                      'Zustand mit --status und am Teach Pendant prüfen, bevor erneut vorbereitet wird.') from error
    entry['reply'] = reply
    expected = {'load': 'loading program:', 'power on': 'powering on',
                'brake release': 'brake releasing', 'play': 'starting program'}[step]
    if reply.lower().startswith(expected):
        return
    lower = reply.lower()
    if 'remote control' in lower:
        raise Blocked('local_control', f'{command!r} abgelehnt: {reply}',
                      'Remote Control am Teach Pendant wählen und erneut aufrufen.')
    if step == 'load':
        raise Blocked('load_rejected', f'{command!r} abgelehnt: {reply}',
                      'Am Teach Pendant Datei und zugehörige Installation prüfen; eine angezeigte Sicherheitsbestätigung vor Ort beurteilen.')
    raise Blocked('command_rejected', f'{command!r} abgelehnt: {reply}',
                  'Meldung und Sicherheitszustand am Teach Pendant prüfen.')


def wait_for(dash, arm, step, get_transport, report, *, seconds, clock=time.monotonic, sleep=time.sleep):
    end = clock() + seconds
    while True:
        state = inspect(dash, arm)
        report['state'] = asdict(state)
        safety_check(state)
        if step == 'load' and state.program == arm.program and state.playback == 'STOPPED':
            return
        if step == 'power on' and state.mode in ('IDLE', 'RUNNING'):
            return
        if step == 'brake release' and state.mode == 'RUNNING':
            return
        if step in ('play', 'wait_ros') and running_target(arm, state) and state.mode == 'RUNNING':
            if get_transport(arm)[1]:
                return
        if state.playback == 'PAUSED' or (state.playback == 'PLAYING' and not running_target(arm, state)):
            raise Blocked('program_in_use', 'Während der Vorbereitung hat sich die Programmausführung geändert.',
                          'Aktives Programm am Teach Pendant prüfen.')
        if state.remote is False and step != 'wait_ros':
            raise Blocked('local_control', 'Während der Vorbereitung wurde auf Local Control gewechselt.',
                          'Am Teach Pendant wieder Remote Control wählen.')
        if clock() >= end:
            if step in ('play', 'wait_ros'):
                _, linked = get_transport(arm)
                report['ros_reverse_connected'] = linked
                if not running_target(arm, state):
                    raise Blocked('play_not_confirmed', 'PolyScope meldet ros.urp nicht als laufend.',
                                  'Am Teach Pendant die Programmmeldung und den External-Control-Knoten prüfen.')
                raise Blocked('ros_not_connected', 'ros.urp läuft, aber keine bestätigte ROS-Reverse-Verbindung.',
                              f'ROS-Treiber und External-Control-Host/Port in der Installation prüfen (Script-Port {arm.script_port}).')
            raise Blocked('transition_timeout', f'Zielzustand nach {step!r} nicht bestätigt.',
                          'Letzten Zustand und Meldungen am Teach Pendant prüfen; der Befehl wird nicht wiederholt.')
        sleep(.25)


def run_arm(arm, apply, *, dashboard=Dashboard, get_transport=transport,
            transition_timeout=30, start_driver=None):
    report = {'arm': arm.id, 'ip': arm.ip, 'expected_serial': arm.serial, 'target': arm.program,
              'commands': [], 'state': None, 'ros_script_listener': None, 'ros_reverse_connected': None,
              'driver_start_attempted': False}
    try:
        with dashboard(arm).connect() as dash:
            for _ in range(8):
                state = inspect(dash, arm)
                report['state'] = asdict(state)
                # Classify controller-side/manual blockers regardless of local ROS availability.
                eligible = next_step(arm, state, True, False)
                listening, reverse = get_transport(arm)
                report.update(ros_script_listener=listening, ros_reverse_connected=reverse)
                if (apply and start_driver and not listening
                        and eligible in ('load', 'power on', 'brake release', 'play')):
                    if report['driver_start_attempted']:
                        raise Blocked('ros_driver_start_failed', 'Der ROS-Script-Port ist wieder ausgefallen.',
                                      'Lokales Treiberprotokoll prüfen und erneut mit --status abfragen.')
                    report['driver_start_attempted'] = True
                    start_driver(arm, get_transport)
                    continue  # Refresh robot state after the local launch.
                step = next_step(arm, state, listening, reverse)
                if step == 'ready':
                    return dict(report, code='ready', message='ROS-Programm läuft und Reverse-Verbindung ist aktiv.')
                if not apply:
                    msg = ('ros.urp läuft ohne bestätigte ROS-Reverse-Verbindung.' if step == 'wait_ros'
                           else f'Noch nicht bereit; nächster Schritt: {step}.')
                    action = (f'ROS-Treiber und External-Control-Host/Port prüfen (Script-Port {arm.script_port}).'
                              if step == 'wait_ros' else None)
                    return dict(report, code='needs_preparation', message=msg, manual_action=action)
                if step == 'wait':
                    end = time.monotonic() + transition_timeout
                    while state.mode in TRANSIENT and time.monotonic() < end:
                        time.sleep(.25)
                        state = inspect(dash, arm)
                        report['state'] = asdict(state)
                        safety_check(state)
                    if state.mode in TRANSIENT:
                        raise Blocked('transition_timeout', f'UR verbleibt in {state.mode}.',
                                      'Initialisierung am Teach Pendant prüfen.')
                    continue
                if step != 'wait_ros':
                    # The socket/driver check takes time. Re-read just before writing.
                    current = inspect(dash, arm)
                    report['state'] = asdict(current)
                    if next_step(arm, current, listening, reverse) != step:
                        continue
                    command = f'load {PurePosixPath(arm.program).name}' if step == 'load' else step
                    if any(record['command'] == command for record in report['commands']):
                        raise Blocked('state_changed', f'Zustand nach {command!r} erneut geändert.',
                                      'Teach Pendant prüfen; kein automatischer Wiederholungsversuch.')
                    write(dash, arm, step, report['commands'])
                wait_for(dash, arm, step, get_transport, report, seconds=transition_timeout)
    except Blocked as error:
        return dict(report, code=error.code, message=str(error), manual_action=error.action)
    except OSError as error:
        changed = bool(report['commands'])
        return dict(report, code='readback_lost' if changed else 'unreachable',
                    message=f'Dashboard nicht erreichbar oder Antwort ausgeblieben: {error}.',
                    manual_action=('Aktuellen Zustand am Teach Pendant prüfen; es wurde bereits ein Befehl gesendet.'
                                   if changed else 'Steuerung einschalten und Ethernet/Dashboard Server prüfen.'))
    return dict(report, code='transition_timeout', message='Zustand hat sich mehrfach geändert.',
                manual_action='Aktuellen Zustand am Teach Pendant prüfen und bei Bedarf erneut aufrufen.')


@contextmanager
def operation_lock():
    # Only one preparation process for this bench on the workstation.
    root = Path('/tmp') / f'uwa-ur-bringup-{os.getuid()}'
    root.mkdir(mode=0o700, exist_ok=True)
    st = root.lstat()
    if root.is_symlink() or not root.is_dir() or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise ValueError(f'Unsicheres Lock-Verzeichnis: {root}')
    with (root / 'apply.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Ein anderer UWA-UR-Start läuft bereits.') from error
        yield


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--status', action='store_true', help='Nur lesen (Standard).')
    mode.add_argument('--apply', action='store_true', help='Die ausgewählten realen URs vorbereiten und ros.urp starten.')
    parser.add_argument('--arm', action='append', choices=ROBOT_IDS, help='Wiederholbar; Standard: alle vier.')
    parser.add_argument('--json', action='store_true', help='Ergebnis als JSON für Skripte und Agenten.')
    args = parser.parse_args(argv)
    try:
        arms = load_arms(INVENTORY)
        selected = [arms[rid] for rid in ROBOT_IDS if not args.arm or rid in args.arm]
        with operation_lock() if args.apply else nullcontext():
            if args.apply:
                reports = []
                for arm in selected:
                    print(f'{arm.id}: Vorbereitung läuft …', file=sys.stderr, flush=True)
                    reports.append(run_arm(arm, True, start_driver=launch_driver))
                    if not args.json:
                        print_report(reports[-1])
                # Refresh arms that became ready before the last arm was handled.
                ready_arms = [arm for arm, result in zip(selected, reports) if result['code'] == 'ready']
                with ThreadPoolExecutor(max_workers=4) as pool:
                    refreshed = {r['arm']: r for r in pool.map(lambda arm: run_arm(arm, False), ready_arms)}
                for index, previous in enumerate(reports):
                    if current := refreshed.get(previous['arm']):
                        reports[index] = dict(current, commands=previous['commands'],
                                              driver_start_attempted=previous['driver_start_attempted'])
                        if not args.json and current['code'] != 'ready':
                            print_report(reports[index])
            else:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    reports = list(pool.map(lambda arm: run_arm(arm, False), selected))
                if not args.json:
                    for report in reports:
                        print_report(report)
        ready = all(report['code'] == 'ready' for report in reports)
        if args.json:
            print(json.dumps({'mode': 'apply' if args.apply else 'status', 'all_ready': ready,
                              'arms': {r['arm']: r for r in reports}}, ensure_ascii=False, indent=2))
        return 0 if ready else 1
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        if args.json:
            print(json.dumps({'all_ready': False, 'error': str(error)}, ensure_ascii=False))
        else:
            print(error, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Abgebrochen. Bereits gesendete Dashboard-Befehle bleiben wirksam; --status erneut ausführen.',
              file=sys.stderr)
        return 130


def print_report(report):
    print(f'{report["arm"]} ({report["ip"]}) [{report["code"]}]: {report["message"]}', flush=True)
    if report.get('manual_action'):
        print(f'  Nächster Schritt: {report["manual_action"]}', flush=True)


if __name__ == '__main__':
    sys.exit(main())

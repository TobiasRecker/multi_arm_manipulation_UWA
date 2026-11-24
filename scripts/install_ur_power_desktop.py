#!/usr/bin/env python3
"""Install the UWA Robot Power launcher for the current desktop user."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess


def desktop_quote(value):
    """Quote one Exec argument through Desktop Entry and argv parsing."""
    escaped = ''.join('\\'+char if char in '\\"\x60$' else char for char in str(value))
    escaped = (escaped.replace('\\', '\\\\').replace('\n', '\\n')
               .replace('\r', '\\r').replace('\t', '\\t').replace('%', '%%'))
    return '"'+escaped+'"'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n100', action='store_true', help='Set the desktop launcher to the N100 driver host')
    parser.add_argument('--minimal-runtime', type=Path, metavar='PATH',
                        help='Bind the launcher to this absolute N100 candidate path; also selects --n100')
    args = parser.parse_args(argv)
    if args.minimal_runtime is not None and not args.minimal_runtime.is_absolute():
        parser.error('--minimal-runtime must be an absolute N100 runtime path')
    root = Path(__file__).resolve().parents[1]
    data = Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')
    applications = data/'applications'
    icons = data/'icons/hicolor/scalable/apps'
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root/'assets/uwa-robot-power.svg', icons/'uwa-robot-power.svg')
    script = desktop_quote(root/'scripts/ur_power_gui.py')
    entry = applications/'uwa-robot-power.desktop'
    command = f'/usr/bin/python3 {script}'
    if args.n100 or args.minimal_runtime is not None:
        command += ' --n100'
    if args.minimal_runtime is not None:
        runtime = os.path.normpath(str(args.minimal_runtime))
        command = ('/usr/bin/env UWA_PROTECTION_BACKEND=minimal ' +
                   desktop_quote('UWA_MINIMAL_RUNTIME='+runtime) + ' ' + command +
                   ' --protection-backend minimal')
    entry.write_text('[Desktop Entry]\nType=Application\nName=UWA Robot Power\n'
                     'Comment=Put the four UR arms into standby or prepare them for ROS\n'
                     f'Exec={command}\n'
                     'Icon=uwa-robot-power\nTerminal=false\nCategories=Utility;\n'
                     'StartupNotify=true\nStartupWMClass=uwa-robot-power\nActions=SafetyLog;\n\n'
                     '[Desktop Action SafetyLog]\nName=Safety log\n'
                     f'Exec={command} --safety-log\n')
    if shutil.which('desktop-file-validate'):
        subprocess.run(['desktop-file-validate', str(entry)], check=True)
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(applications)], check=True)
    print(entry)


if __name__ == '__main__':
    main()

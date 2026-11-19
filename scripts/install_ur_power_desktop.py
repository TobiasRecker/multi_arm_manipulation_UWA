#!/usr/bin/env python3
"""Install the UWA Robot Power launcher for the current desktop user."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n100', action='store_true', help='Set the desktop launcher to the N100 driver host')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')
    applications = data/'applications'
    icons = data/'icons/hicolor/scalable/apps'
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root/'assets/uwa-robot-power.svg', icons/'uwa-robot-power.svg')
    script = str(root/'scripts/ur_power_gui.py')
    script = ''.join('\\'+x if x in '\\"\x60$' else x for x in script)
    # Percent is reserved for Desktop Entry field codes.
    script = script.replace('%', '%%')
    entry = applications/'uwa-robot-power.desktop'
    host_option = ' --n100' if args.n100 else ''
    entry.write_text('[Desktop Entry]\nType=Application\nName=UWA Robot Power\n'
                     'Comment=Put the four UR arms into standby or prepare them for ROS\n'
                     f'Exec=/usr/bin/python3 "{script}"{host_option}\n'
                     'Icon=uwa-robot-power\nTerminal=false\nCategories=Utility;\n'
                     'StartupNotify=true\nStartupWMClass=uwa-robot-power\nActions=SafetyLog;\n\n'
                     '[Desktop Action SafetyLog]\nName=Safety log\n'
                     f'Exec=/usr/bin/python3 "{script}"{host_option} --safety-log\n')
    if shutil.which('desktop-file-validate'):
        subprocess.run(['desktop-file-validate', str(entry)], check=True)
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(applications)], check=True)
    print(entry)


if __name__ == '__main__':
    main()

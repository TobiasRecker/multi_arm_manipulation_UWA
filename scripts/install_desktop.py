#!/usr/bin/env python3
"""Install the UWA Cell menu entry and icon for the current desktop user."""
import os
from pathlib import Path
import shutil
import subprocess


def exec_quote(value):
    # Desktop Entry Exec quoting is separate from shell quoting. No shell parses
    # this field: bash receives the script path as one literal argument.
    value = str(value).replace('%', '%%')
    for character in ('\\', '"', '`', '$'):
        value = value.replace(character, '\\' + character)
    return '"' + value + '"'


def main():
    repo = Path(__file__).resolve().parent.parent
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')).expanduser()
    applications = data / 'applications'
    icons = data / 'icons'
    source = repo / 'assets/uwa-cell.png'
    if not source.is_file():
        raise SystemExit(f'Application icon is missing: {source}')
    script = repo / 'scripts/desktop_cell.sh'
    command = '/usr/bin/bash ' + exec_quote(script)
    entry = f'''[Desktop Entry]
Version=1.0
Type=Application
Name=UWA Cell Simulation
Comment=Four UR arms in Gazebo with joint control and RViz
Comment[de]=Vier UR-Arme in Gazebo mit Gelenksteuerung und RViz
Exec={command} start
TryExec=/usr/bin/bash
Icon={icons / 'uwa-cell.png'}
Path={repo.parent.parent}
Terminal=false
StartupNotify=false
Categories=Science;Robotics;
Keywords=UWA;ROS;Gazebo;RViz;Roboter;Simulation;
Actions=RViz;Stop;

[Desktop Action RViz]
Name=Open RViz
Name[de]=RViz öffnen
Exec={command} rviz

[Desktop Action Stop]
Name=Stop simulation
Name[de]=Simulation beenden
Exec={command} stop
'''
    # Validate the concrete entry before changing the desktop profile.
    preview = repo / 'assets/uwa-cell.desktop'
    preview.write_text(entry)
    validator = shutil.which('desktop-file-validate')
    if validator:
        subprocess.run([validator, str(preview)], check=True)
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, icons / 'uwa-cell.png')
    target = applications / 'uwa-cell.desktop'
    shutil.copy2(preview, target)
    target.chmod(0o644)
    updater = shutil.which('update-desktop-database')
    if updater:
        subprocess.run([updater, str(applications)], check=True)
    print(f'Installed menu entry: {target}\nInstalled icon: {icons / "uwa-cell.png"}')


if __name__ == '__main__':
    main()

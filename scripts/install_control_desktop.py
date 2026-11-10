#!/usr/bin/env python3
"""Install the local UWA preparation GUI, reusing the existing cell artwork."""
import os
from pathlib import Path
import subprocess


def main():
    repo=Path(__file__).resolve().parents[1]
    target=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'applications'
    target.mkdir(parents=True,exist_ok=True)
    # Desktop Exec follows its own double-quote escaping rules, not shell quoting.
    script=str(repo/'scripts/control.sh').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
    entry=target/'uwa-control.desktop'
    entry.write_text('[Desktop Entry]\nType=Application\nName=UWA Arms\n'
        'Comment=Local preparation and controller status for the four UWA arms\n'
        f'Exec=/usr/bin/bash "{script}"\nIcon={repo}/assets/uwa-cell.png\n'
        'Terminal=false\nCategories=Education;\nStartupNotify=true\nStartupWMClass=uwa_control_gui\n'
        'Actions=RightRearHardware;\n\n[Desktop Action RightRearHardware]\n'
        'Name=Hardware · rear right\n'
        f'Exec=/usr/bin/bash "{script}" --mode hardware --arms right_rear\n')
    print(entry)
    try:subprocess.run(['update-desktop-database',str(target)],check=False,capture_output=True)
    except FileNotFoundError:pass


if __name__=='__main__':main()

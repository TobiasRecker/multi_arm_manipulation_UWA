#!/usr/bin/env python3
"""Install the local UWA preparation GUI, reusing the existing cell artwork."""
import os
from pathlib import Path
import shlex
import subprocess


def main():
    repo=Path(__file__).resolve().parents[1]
    target=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'applications'
    target.mkdir(parents=True,exist_ok=True)
    # Desktop Exec follows its own double-quote escaping rules, not shell quoting.
    script=str(repo/'scripts/control.sh').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
    entry=target/'uwa-control.desktop'
    entry.write_text('[Desktop Entry]\nType=Application\nName=UWA Arme\n'
        'Comment=Lokale Vorbereitung und Controllerstatus der vier UWA-Arme\n'
        f'Exec=/usr/bin/bash "{script}"\nIcon={repo}/assets/uwa-cell.png\n'
        'Terminal=false\nCategories=Education;Science;Robotics;\nStartupNotify=true\n')
    print(entry)
    try:subprocess.run(['update-desktop-database',str(target)],check=False,capture_output=True)
    except FileNotFoundError:pass


if __name__=='__main__':main()

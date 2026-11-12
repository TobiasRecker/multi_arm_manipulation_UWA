#!/usr/bin/env python3
"""Install a local start-menu entry for the camera-only acquisition GUI."""
import os
from pathlib import Path
import subprocess

repo = Path(__file__).resolve().parents[1]
target = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'applications'
target.mkdir(parents=True, exist_ok=True)
script = str(repo / 'scripts/camera_capture.sh').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
entry = target / 'uwa-camera-capture.desktop'
entry.write_text('[Desktop Entry]\nType=Application\nName=UWA Camera Capture\n'
    'Comment=Mobile ChArUco visibility and photos from two wrist cameras and OAK4\n'
    f'Exec=/usr/bin/bash "{script}"\nIcon=camera-photo\n'
    'Terminal=false\nCategories=Education;Graphics;\nStartupNotify=true\n')
subprocess.run(['update-desktop-database', str(target)], capture_output=True, check=False)
print(entry)

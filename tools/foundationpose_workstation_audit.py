#!/usr/bin/env python3
"""Record small system/environment metadata files without personal contents."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    home = Path('/home/ubuntu22')
    paths = [Path('/var/lib/dpkg/status'), Path('/etc/docker/daemon.json'),
             home / '.bashrc', home / '.profile', home / '.condarc']
    paths += sorted((home / 'miniconda3').glob('conda-meta/history'))
    paths += sorted((home / 'miniconda3/envs').glob('*/conda-meta/history'))
    hashes = {}
    for path in paths:
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    report = {'protected_file_hashes': hashes}
    for name, command in {
        'gpu': ['nvidia-smi', '--query-gpu=name,driver_version,memory.used,utilization.gpu', '--format=csv,noheader'],
        'disk': ['df', '-h', '/', '/media/ubuntu22/RAID1_L'],
        'load': ['uptime'],
    }.items():
        report[name] = subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()
    if args.compare:
        before = json.loads(args.compare.read_text())['protected_file_hashes']
        report['protected_files_changed'] = [path for path, value in before.items() if hashes.get(path) != value]
        report['protected_files_unchanged'] = not report['protected_files_changed']
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

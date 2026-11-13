#!/usr/bin/env python3
"""Fetch only the two official pretrained models and the mustard demo."""
import hashlib
import json
from pathlib import Path
import zipfile

import gdown

ROOT = Path('/media/ubuntu22/RAID1_L/uwa-foundationpose-ubuntu22')
FILES = [
    ('1477-st1s1TxXN6oqfM5ZnsQwd8BCzVg1', 'FoundationPose/weights/2023-10-28-18-33-37/config.yml'),
    ('1E9FPB5WFIBMLrOJqZLpoVOK4Mjzrrxhv', 'FoundationPose/weights/2023-10-28-18-33-37/model_best.pth'),
    ('1kQkQG-q_VvLRozv30hyeLB7P_jiEEqiE', 'FoundationPose/weights/2024-01-11-20-02-45/config.yml'),
    ('1Zdjnkn4EHOI5_k08apofwRgTjWpai4E4', 'FoundationPose/weights/2024-01-11-20-02-45/model_best.pth'),
    ('1AwV9sESDKMgXGUu2n1o0Pc4x2JGYdVB3', 'downloads/mustard0.zip'),
]


def main():
    manifest = []
    for file_id, relative in FILES:
        output = ROOT / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        if not output.exists():
            print(f'DOWNLOADING {relative}', flush=True)
            gdown.download(id=file_id, output=str(output), quiet=False,
                           use_cookies=False, timeout=(15, 90), retries=2)
        checksum = hashlib.file_digest(output.open('rb'), 'sha256').hexdigest()
        manifest.append({'google_drive_id': file_id, 'path': relative,
                         'size': output.stat().st_size, 'sha256': checksum})
        print(f'READY {relative} {output.stat().st_size}', flush=True)
    destination = ROOT / 'FoundationPose/demo_data'
    destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT / 'downloads/mustard0.zip') as archive:
        if sum(info.file_size for info in archive.infolist()) > 5 * 2**30:
            raise RuntimeError('Unexpectedly large demo archive')
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise RuntimeError('Unsafe archive member')
        archive.extractall(destination)
    (ROOT / 'logs/download-manifest.json').write_text(json.dumps(manifest, indent=2))
    print('DOWNLOAD COMPLETE', flush=True)


if __name__ == '__main__':
    main()

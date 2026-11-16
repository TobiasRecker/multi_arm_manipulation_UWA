#!/usr/bin/env bash
# Explicit remote compute only. No ROS, camera access or robot commands.
set -euo pipefail
case "${1:-status}" in
  status)
    ssh -o BatchMode=yes -o ConnectTimeout=10 uwa-ubuntu22 'bash -s' <<'REMOTE'
set -euo pipefail
root=/media/ubuntu22/RAID1_L/uwa-foundationpose-ubuntu22
printf 'GPU / CURRENT USE\n'
nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu --format=csv
printf '\nSYSTEM AND DATA DISK\n'
df -h / "$root"
printf '\nRECENT TEST REPORTS\n'
find "$root/results" -maxdepth 2 -name report.json -print | sort | tail -n 5
REMOTE
    ;;
  smoke|smoke-motion)
    frames=12
    if [[ "$1" == smoke-motion ]]; then frames=100; fi
    ssh -o BatchMode=yes -o ConnectTimeout=10 uwa-ubuntu22 "bash -s -- $frames" <<'REMOTE'
set -euo pipefail
root=/media/ubuntu22/RAID1_L/uwa-foundationpose-ubuntu22
source "$root/tools/foundationpose_titanpc_env.bash"
run_id="mustard_${1}_$(date -u +%Y%m%dT%H%M%SZ)_$$"
printf 'RUNNING: bounded RGB-D demo; output %s/results/%s\n' "$root" "$run_id"
flock -n "$root/gpu-test.lock" timeout --signal=TERM --kill-after=10s 10m \
  nice -n 10 python -u "$root/tools/foundationpose_smoke.py" \
  --scene "$root/FoundationPose/demo_data/mustard0" \
  --output "$root/results/$run_id" --frames "$1" --stride 3 \
  2>&1 | tee "$root/logs/$run_id.log"
printf 'DONE: %s/results/%s/report.json\n' "$root" "$run_id"
REMOTE
    ;;
  input)
    input_name="${2:-}"
    if [[ ! "$input_name" =~ ^[A-Za-z0-9_-]{1,80}$ ]]; then
      printf 'Input name must contain only letters, digits, underscore and dash.\n' >&2
      exit 2
    fi
    ssh -o BatchMode=yes -o ConnectTimeout=10 uwa-ubuntu22 "bash -s -- $input_name" <<'REMOTE'
set -euo pipefail
root=/media/ubuntu22/RAID1_L/uwa-foundationpose-ubuntu22
source "$root/tools/foundationpose_titanpc_env.bash"
scene="$root/inputs/$1"
python - "$scene" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
manifest=json.loads((root/'input.json').read_text())
if manifest.get('model',{}).get('scene_pose_used') is not False:
    raise ValueError('Model package does not exclude scene pose priors')
for name,digest in manifest['files'].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
        raise ValueError('Input payload hash mismatch: '+name)
print('INPUT VERIFIED: '+manifest['model']['asset_id'])
PY
run_id="${1}_$(date -u +%Y%m%dT%H%M%SZ)_$$"
printf 'RUNNING: saved UWA RGB-D input; output %s/results/%s\n' "$root" "$run_id"
flock -n "$root/gpu-test.lock" timeout --signal=TERM --kill-after=10s 10m \
  nice -n 10 python -u "$root/tools/foundationpose_smoke.py" \
  --scene "$scene" --output "$root/results/$run_id" --frames 8 --stride 1 \
  2>&1 | tee "$root/logs/$run_id.log"
printf 'DONE: %s/results/%s/report.json\n' "$root" "$run_id"
REMOTE
    ;;
  *) printf 'Usage: %s {status|smoke|smoke-motion|input INPUT_NAME}\n' "$0" >&2; exit 2 ;;
esac

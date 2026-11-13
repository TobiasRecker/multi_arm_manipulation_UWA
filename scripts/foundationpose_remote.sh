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
  smoke)
    ssh -o BatchMode=yes -o ConnectTimeout=10 uwa-ubuntu22 'bash -s' <<'REMOTE'
set -euo pipefail
root=/media/ubuntu22/RAID1_L/uwa-foundationpose-ubuntu22
source "$root/tools/foundationpose_titanpc_env.bash"
run_id="mustard_$(date -u +%Y%m%dT%H%M%SZ)_$$"
printf 'RUNNING: bounded RGB-D demo; output %s/results/%s\n' "$root" "$run_id"
flock -n "$root/gpu-test.lock" timeout --signal=TERM --kill-after=10s 10m \
  nice -n 10 python -u "$root/tools/foundationpose_smoke.py" \
  --scene "$root/FoundationPose/demo_data/mustard0" \
  --output "$root/results/$run_id" --frames 12 --stride 3 \
  2>&1 | tee "$root/logs/$run_id.log"
printf 'DONE: %s/results/%s/report.json\n' "$root" "$run_id"
REMOTE
    ;;
  *) printf 'Usage: %s {status|smoke}\n' "$0" >&2; exit 2 ;;
esac

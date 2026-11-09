#!/usr/bin/env bash
# Desktop entry point: keep repeated clicks idempotent and errors discoverable.
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/.." && pwd)"
workspace="$(cd -- "$repo_dir/../.." && pwd)"
mkdir -p "$workspace/setup/logs"
exec >>"$workspace/setup/logs/uwa-cell-app.log" 2>&1
trap 'code=$?; if command -v notify-send >/dev/null; then notify-send --app-name="UWA Cell" "UWA Cell konnte nicht gestartet werden" "Details: ~/UWA_ws/setup/logs/uwa-cell-app.log"; fi; exit "$code"' ERR
case "${1:-start}" in
  start)
    bash "$script_dir/cell.sh" start
    bash "$script_dir/cell.sh" scan
    bash "$script_dir/cell.sh" rviz
    python3 "$script_dir/show_cell_windows.py" --prefer gazebo
    ;;
  rviz|scan)
    bash "$script_dir/cell.sh" scan
    bash "$script_dir/cell.sh" rviz
    python3 "$script_dir/show_cell_windows.py" --prefer rviz
    ;;
  stop) bash "$script_dir/cell.sh" stop ;;
  *) echo "Unknown desktop action: $1" >&2; exit 2 ;;
esac

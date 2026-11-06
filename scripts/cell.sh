#!/usr/bin/env bash
# Manage only this cell's transient user service, never arbitrary ROS processes.
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
operation="${1:-status}"
if (($#)); then shift; fi
case "$operation" in
  start)
    if systemctl --user is-active --quiet uwa-cell-sim; then
      echo 'UWA cell is already running. Stop it before changing layout or options.'
      exit 0
    fi
    systemd-run --user --unit=uwa-cell-sim --collect \
      --property=TimeoutStopSec=25 --property=KillSignal=SIGINT --property=KillMode=mixed \
      --setenv="DISPLAY=${DISPLAY:-:0}" \
      --setenv="WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}" \
      --setenv="XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
      /usr/bin/bash "$script_dir/start_cell.sh" "$@"
    ;;
  stop) systemctl --user stop uwa-cell-sim ;;
  status) systemctl --user status uwa-cell-sim --no-pager ;;
  logs) journalctl --user -u uwa-cell-sim -f ;;
  *) echo "Usage: bash $0 {start [launch arguments...]|stop|status|logs}" >&2; exit 2 ;;
esac

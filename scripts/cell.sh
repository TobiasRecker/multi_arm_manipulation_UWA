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
  rviz)
    bash "$script_dir/cell.sh" twin
    if systemctl --user is-active --quiet uwa-cell-rviz; then
      echo 'UWA RViz is already running.'
      exit 0
    fi
    systemd-run --user --unit=uwa-cell-rviz --collect \
      --property=TimeoutStopSec=15 --property=KillSignal=SIGINT --property=KillMode=mixed \
      --setenv="DISPLAY=${DISPLAY:-:0}" \
      --setenv="WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}" \
      --setenv="XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
      /usr/bin/bash "$script_dir/start_rviz.sh"
    ;;
  twin)
    if systemctl --user is-active --quiet uwa-cell-hardware-overlay; then
      echo 'UWA measured hardware overlay is already running.'
      exit 0
    fi
    systemd-run --user --unit=uwa-cell-hardware-overlay --collect \
      --property=TimeoutStopSec=15 --property=KillSignal=SIGINT --property=KillMode=mixed \
      /usr/bin/bash "$script_dir/start_twin.sh" "$@"
    ;;
  scan)
    if systemctl --user is-active --quiet uwa-cell-scan; then
      echo 'UWA scan reference is already running.'
      exit 0
    fi
    systemd-run --user --unit=uwa-cell-scan --collect \
      --property=TimeoutStopSec=15 --property=KillSignal=SIGINT --property=KillMode=mixed \
      /usr/bin/bash "$script_dir/start_scan.sh" "$@"
    ;;
  stop)
    if systemctl --user is-active --quiet uwa-cell-hardware-overlay; then
      systemctl --user stop uwa-cell-hardware-overlay
    fi
    if systemctl --user is-active --quiet uwa-cell-overview-view; then
      systemctl --user stop uwa-cell-overview-view
    fi
    if systemctl --user is-active --quiet uwa-cell-overview; then
      systemctl --user stop uwa-cell-overview
    fi
    if systemctl --user is-active --quiet uwa-cell-scan; then
      systemctl --user stop uwa-cell-scan
    fi
    if systemctl --user is-active --quiet uwa-cell-rviz; then
      systemctl --user stop uwa-cell-rviz
    fi
    systemctl --user stop uwa-cell-sim
    ;;
  status) systemctl --user status uwa-cell-sim --no-pager ;;
  logs) journalctl --user -u uwa-cell-sim -f ;;
  *) echo "Usage: bash $0 {start [launch arguments...]|rviz|twin [launch arguments...]|scan [layout.yaml]|stop|status|logs}" >&2; exit 2 ;;
esac

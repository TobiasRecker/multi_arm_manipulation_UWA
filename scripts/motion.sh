#!/usr/bin/env bash
# Manage only the new simulation guard; never stop Gazebo or physical drivers.
set -eo pipefail
motion_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
operation="${1:-status}"
if (($#)); then shift; fi
case "$operation" in
  start)
    if systemctl --user is-active --quiet uwa-cell-motion; then
      echo 'SERVICE ACTIVE: inspect guard/supervisor status for CLEAR, STOPPED or STATE STALE';exit 0
    fi
    systemd-run --user --unit=uwa-cell-motion --collect \
      --property=TimeoutStopSec=15 --property=KillSignal=SIGINT --property=KillMode=mixed \
      /usr/bin/bash "$motion_dir/start_motion.sh" "$@"
    ;;
  stop)
    source "$motion_dir/env.bash"
    ros2 run uwa_cell_motion cell_motion stop
    systemctl --user stop uwa-cell-motion
    echo 'STOPPED: guard service ended; simulated arms remain resource-held'
    ;;
  status) systemctl --user status uwa-cell-motion --no-pager ;;
  logs) journalctl --user -u uwa-cell-motion -f ;;
  *) echo "Usage: bash $0 {start [layout:=...]|stop|status|logs}" >&2;exit 2 ;;
esac

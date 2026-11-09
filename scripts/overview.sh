#!/usr/bin/env bash
# Manage only the simulated static OAK, never the physical Ethernet camera.
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/env.bash"
case "${1:-view}" in
  run)
    exec ros2 run uwa_cell_gazebo oak_overview --ros-args -p use_sim_time:=true \
      -p "layout:=${2:-$script_dir/../uwa_cell_description/config/cell_layout.yaml}"
    ;;
  start)
    if systemctl --user is-active --quiet uwa-cell-overview; then
      echo 'Overview helper already running. Use reload after changing the layout.'
      exit 0
    fi
    systemd-run --user --unit=uwa-cell-overview --collect \
      --property=KillSignal=SIGINT --property=KillMode=mixed --property=TimeoutStopSec=15 \
      /usr/bin/bash "$script_dir/overview.sh" run "${2:-$script_dir/../uwa_cell_description/config/cell_layout.yaml}"
    ;;
  reload)
    exec ros2 service call /uwa_cell/oak_overview/reload std_srvs/srv/Trigger '{}'
    ;;
  view)
    if systemctl --user is-active --quiet uwa-cell-overview-view; then
      echo 'The overview image viewer is already open.'
      exit 0
    fi
    systemd-run --user --unit=uwa-cell-overview-view --collect \
      --property=KillSignal=SIGINT --property=KillMode=mixed --property=TimeoutStopSec=10 \
      --setenv="DISPLAY=${DISPLAY:-:0}" \
      /usr/bin/bash "$script_dir/overview.sh" view-run
    ;;
  view-run)
    exec ros2 run rqt_image_view rqt_image_view /uwa_cell/oak_overview/rgb/image_raw
    ;;
  coverage)
    shift
    exec ros2 run uwa_cell_gazebo overview_coverage "$@"
    ;;
  check)
    shift
    exec ros2 run uwa_cell_gazebo overview_check "$@"
    ;;
  *) echo "Usage: bash $0 {start [layout.yaml]|reload|view|coverage|check}" >&2; exit 2 ;;
esac

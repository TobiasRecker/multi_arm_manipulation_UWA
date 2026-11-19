#!/usr/bin/env bash
# Persistent ROS interfaces only. Never automatically activates/opens a gripper.
set -eo pipefail
gripper_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gripper_action="${1:-status}"
if (($#)); then shift; fi
case "$gripper_action" in
 monitor|enable)
  if systemctl --user is-active --quiet uwa-grippers.service; then
   echo 'Replacing own interface service; bounded active goals finish, targets remain unchanged.'
   systemctl --user stop uwa-grippers.service
  fi
  systemd-run --user --unit=uwa-grippers --collect --property=KillSignal=SIGINT \
   --property=MemoryLow=256M --property=MemorySwapMax=0 --property=CPUWeight=500 \
   --property=KillMode=mixed --property=TimeoutStopSec=45 \
   /usr/bin/bash "$gripper_script_dir/start_grippers.sh" "$gripper_action" "$@"
  ;;
 status) systemctl --user status uwa-grippers.service --no-pager ;;
 stop)
  systemctl --user stop uwa-grippers.service
  echo 'Interfaces stopped. Gripper targets retained; no open/reset/force-zero command sent.'
  ;;
 logs) journalctl --user -u uwa-grippers.service -n 60 --no-pager ;;
 *) echo "Usage: bash $0 {monitor|enable|status|stop|logs} [max_force_raw:=0 max_speed_raw:=32]" >&2; exit 2 ;;
esac

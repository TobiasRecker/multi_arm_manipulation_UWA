#!/usr/bin/env bash
# This entry never powers URs, releases brakes, loads programs or presses Play.
set -eo pipefail
hardware_motion_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
hardware_motion_action="${1:-status}"
if (($#)); then shift; fi
hardware_motion_unit=uwa-hardware-motion
case "$hardware_motion_action" in
 monitor|arm)
  if systemctl --user is-active --quiet "$hardware_motion_unit"; then
   hardware_motion_environment="$(systemctl --user show "$hardware_motion_unit" -p Environment --value)"
   if [[ "$hardware_motion_action" == arm && "$hardware_motion_environment" != *UWA_MOTION_ARMED=1* ]]; then
    systemctl --user stop "$hardware_motion_unit"
   else
    echo 'SERVICE ALREADY ACTIVE: inspect live MONITOR ONLY / STOPPING / STOPPED / STATE STALE status; no reset sent'; exit 0
   fi
  fi
  hardware_motion_armed=0
  if [[ "$hardware_motion_action" == arm ]]; then hardware_motion_armed=1; fi
  systemd-run --user --unit="$hardware_motion_unit" --collect \
   --setenv=UWA_MOTION_ARMED="$hardware_motion_armed" \
   --property="ExecStopPost=/usr/bin/bash $hardware_motion_dir/stop_hardware_motion.sh" \
   --property=KillSignal=SIGINT --property=KillMode=mixed --property=TimeoutStopSec=20 \
   /usr/bin/bash "$hardware_motion_dir/start_hardware_motion.sh" "$hardware_motion_action" "$@"
  ;;
 halt)
  source "$hardware_motion_dir/control_env.bash"
  ros2 run uwa_cell_motion cell_hardware_motion --mode hardware --inventory "$hardware_motion_dir/../config/hardware_inventory.yaml" stop
  ;;
 stop)
  hardware_motion_environment="$(systemctl --user show "$hardware_motion_unit" -p Environment --value 2>/dev/null || true)"
  if [[ "$hardware_motion_environment" == *UWA_MOTION_ARMED=1* ]]; then
   source "$hardware_motion_dir/control_env.bash"
   if ! ros2 run uwa_cell_motion cell_hardware_motion --mode hardware --inventory "$hardware_motion_dir/../config/hardware_inventory.yaml" stop; then
    echo 'STOP UNCONFIRMED: protection service remains running; inspect live state/native controls' >&2; exit 1
   fi
  fi
  systemctl --user stop "$hardware_motion_unit"
  echo 'SERVICE CLOSED: armed resource holds persist; a monitor service sends no stop commands'
  ;;
 status)
  echo 'PROCESS STATUS ONLY. Live decisions: /uwa_cell/collision_guard/decision and /uwa_cell/collision_supervisor/status in domain66.'
  systemctl --user status "$hardware_motion_unit" --no-pager
  ;;
 logs) journalctl --user -u "$hardware_motion_unit" -f ;;
 *) echo "Usage: bash $0 {monitor|arm|halt|stop|status|logs}" >&2;exit 2 ;;
esac

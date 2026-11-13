#!/usr/bin/env bash
# Camera/visual pose tools only. No robot preparation or motion.
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/env.bash"
for key in GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR; do unset "$key"; done
operation="${1:-help}"
asset_id="${2:-carton_avocado_v1}"
if [[ ! "$asset_id" =~ ^[a-z][a-z0-9_]*$ ]]; then echo 'Invalid asset ID' >&2; exit 2; fi
asset_path="$(ros2 pkg prefix --share uwa_cell_description)/assets/$asset_id"
reference="$UWA_WS/setup/tracking/models/$asset_id/reference.npz"
case "$operation" in
  prepare)
    exec ros2 run uwa_cell_tracking object_pose prepare --asset "$asset_path" --output "$reference"
    ;;
  oak|sim)
    if [[ ! -f "$reference" ]]; then
      ros2 run uwa_cell_tracking object_pose prepare --asset "$asset_path" --output "$reference"
    fi
    if [[ "$operation" == oak ]]; then
      export ROS_DOMAIN_ID=65
      exec ros2 launch uwa_cell_tracking oak_tracking.launch.py "reference:=$reference"
    else
      exec ros2 launch uwa_cell_tracking tracking.launch.py "reference:=$reference"
    fi
    ;;
  localize|track|stop)
    export ROS_DOMAIN_ID="${UWA_TRACKING_DOMAIN:-65}"
    service="$operation"
    if [[ "$service" == track ]]; then service=start; fi
    exec ros2 service call "/uwa_tracking/object_tracker/$service" std_srvs/srv/Trigger '{}'
    ;;
  view)
    export ROS_DOMAIN_ID="${UWA_TRACKING_DOMAIN:-65}"
    exec ros2 run rqt_image_view rqt_image_view /uwa_tracking/object_tracker/overlay
    ;;
  *) echo "Usage: bash $0 {prepare|oak|sim|localize|track|stop|view} [asset_id]" ;;
esac

#!/usr/bin/env bash
# Independent service-exit cleanup. Monitor closure never sends robot commands.
set -eo pipefail
if [[ "${UWA_MOTION_ARMED:-0}" != 1 ]]; then exit 0; fi
hardware_motion_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$hardware_motion_dir/control_env.bash"
echo 'ARMED SERVICE EXIT: requesting native program STOP on all four URs; this is not a standstill measurement'
exec ros2 run uwa_cell_motion cell_hardware_motion --mode hardware --inventory "$hardware_motion_dir/../config/hardware_inventory.yaml" native-stop

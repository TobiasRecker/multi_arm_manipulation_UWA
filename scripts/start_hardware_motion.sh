#!/usr/bin/env bash
set -eo pipefail
# Keep BLAS workers from competing with native-state and watchdog callbacks.
# This affects only this hardware service, never other simulations/agents.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
hardware_motion_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$hardware_motion_dir/control_env.bash"
hardware_motion_action="${1:-monitor}"
shift || true
case "$hardware_motion_action" in
 monitor) hardware_motion_armed=false ;;
 arm) hardware_motion_armed=true ;;
 *) echo 'Expected monitor or arm' >&2; exit 2 ;;
esac
exec ros2 launch uwa_cell_motion hardware_guard.launch.py mode:=hardware armed:="$hardware_motion_armed" inventory:="$hardware_motion_dir/../config/hardware_inventory.yaml" "$@"

#!/usr/bin/env bash
set -eo pipefail
gripper_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$gripper_script_dir/control_env.bash"
gripper_mode="${1:-monitor}"
if (($#)); then shift; fi
case "$gripper_mode" in
 monitor) gripper_actuation=false ;;
 enable) gripper_actuation=true ;;
 *) echo 'Expected monitor or enable' >&2; exit 2 ;;
esac
exec ros2 launch uwa_cell_gripper_control grippers.launch.py mode:=hardware actuate:="$gripper_actuation" "$@"

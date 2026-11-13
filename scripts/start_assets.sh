#!/usr/bin/env bash
# Separate static visual model; preserve the running cell and all arm states.
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/env.bash"
exec ros2 run uwa_cell_gazebo scene_assets --ros-args -p use_sim_time:=true "$@"

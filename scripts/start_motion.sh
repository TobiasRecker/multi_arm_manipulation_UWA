#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.bash"
export ROS_HOME="$UWA_WS/setup/ros-motion"
exec ros2 launch uwa_cell_motion guard.launch.py "$@"

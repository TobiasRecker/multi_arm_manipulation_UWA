#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.bash"
exec ros2 run rviz2 rviz2 \
  -d "$(ros2 pkg prefix --share uwa_cell_gazebo)/rviz/cell.rviz" \
  --ros-args -r __node:=uwa_cell_rviz -p use_sim_time:=true

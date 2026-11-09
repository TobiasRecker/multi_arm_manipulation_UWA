#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.bash"
layout="${1:-$(ros2 pkg prefix --share uwa_cell_description)/config/cell_layout.yaml}"
exec ros2 run uwa_cell_gazebo scan_reference \
  --ros-args -r __ns:=/uwa_cell -p use_sim_time:=true -p "layout:=$layout"
